# =============================================================================
# S.H.I.E.L.D. Core Engine — Data Ingestion
# Reads SoLEXS and HEL1OS FITS/ZIP files from the ISRO PRADAN portal.
#
# PRADAN data comes as:
#   - Individual .fits files, OR
#   - .zip archives containing multiple .fits files
#
# This module handles both formats and extracts time-series flux data
# into clean pandas DataFrames.
# =============================================================================

import os
import zipfile
import io
import logging
import tempfile
from pathlib import Path
from typing import Optional, Union, List
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
from astropy.io import fits
from astropy.time import Time

from config.settings import RAW_DATA_DIR, COMMISSIONING_CUTOFF

logger = logging.getLogger(__name__)

# =============================================================================
# PERFORMANCE CONFIGURATION
# =============================================================================
# Large PRADAN deliveries (hundreds of MB of zipped FITS/CDF) are dominated by
# decompression + table parsing. Both release the GIL inside zlib/numpy/astropy,
# so a thread pool gives near-linear speedup without process-spawn overhead.
# Override with the SHIELD_MAX_WORKERS environment variable.
_DEFAULT_WORKERS = min(8, (os.cpu_count() or 2))
MAX_WORKERS = int(os.environ.get("SHIELD_MAX_WORKERS", _DEFAULT_WORKERS))

# Above this size, ZIP members are spilled to a temp file so astropy can
# memory-map the FITS instead of holding the whole decompressed copy in RAM.
MEMMAP_SPILL_BYTES = 32 * 1024 * 1024  # 32 MB

# Parsed per-instrument frames are cached in-process so repeated small-corpus
# loads do not re-decompress and re-parse the same raw files. At 100+ GB this
# cache is a liability, so frames above CACHE_MAX_ROWS are never cached — the
# windowed/out-of-core path (load_instrument_window) is used there instead.
_INSTRUMENT_CACHE: dict = {}
CACHE_MAX_ROWS = int(os.environ.get("SHIELD_CACHE_MAX_ROWS", 5_000_000))


def clear_cache() -> None:
    """Drop all cached parsed instrument data (call after raw files change)."""
    _INSTRUMENT_CACHE.clear()
    logger.info("Instrument data cache cleared.")


# =============================================================================
# FITS FILE READING
# =============================================================================

def read_fits_file(filepath: Union[str, Path]) -> pd.DataFrame:
    """
    Read a single FITS file and extract time-series flux data.

    PRADAN FITS files typically have:
      - Primary HDU: metadata/header
      - Extension HDU(s): binary table with time and flux columns

    Parameters
    ----------
    filepath : str or Path
        Path to the .fits file.

    Returns
    -------
    pd.DataFrame
        DataFrame with columns ['timestamp', 'flux'] at minimum.
        Additional columns depend on the instrument data available.
    """
    filepath = Path(filepath)
    logger.info(f"Reading FITS file: {filepath.name}")

    records = []

    with fits.open(filepath) as hdul:
        # Log HDU structure for debugging
        logger.debug(f"  HDUs in {filepath.name}: {len(hdul)}")
        for i, hdu in enumerate(hdul):
            logger.debug(f"    HDU[{i}]: {hdu.name} — {type(hdu).__name__}")

        # Try to find the binary table extension with flux data
        for hdu in hdul:
            if isinstance(hdu, (fits.BinTableHDU, fits.TableHDU)):
                df = _extract_table_data(hdu, filepath.name)
                if df is not None and len(df) > 0:
                    records.append(df)

        # If no table found, try reading image data as a spectrum
        if not records:
            for hdu in hdul:
                if isinstance(hdu, fits.ImageHDU) and hdu.data is not None:
                    df = _extract_image_data(hdu, filepath.name)
                    if df is not None and len(df) > 0:
                        records.append(df)

    if not records:
        logger.warning(f"  No usable data found in {filepath.name}")
        return pd.DataFrame()

    result = pd.concat(records, ignore_index=True)
    logger.info(f"  Extracted {len(result)} rows from {filepath.name}")
    return result


def _extract_table_data(hdu, filename: str) -> Optional[pd.DataFrame]:
    """
    Extract time-series data from a FITS binary table HDU.

    Tries multiple common column name conventions used in PRADAN data.
    """
    columns = [col.name.upper() for col in hdu.columns]
    data = hdu.data

    if data is None or len(data) == 0:
        return None

    # --- Find the time column ---
    time_col = None
    time_values = None

    # Common time column names in solar X-ray FITS files
    time_candidates = ['TIME', 'TIME_S', 'TSTART', 'MJD', 'DATE-OBS',
                       'TIMESTAMP', 'UT', 'SECONDS', 'SEC']

    for candidate in time_candidates:
        if candidate in columns:
            idx = columns.index(candidate)
            original_name = hdu.columns[idx].name
            time_col = original_name
            time_values = data[original_name]
            break

    if time_col is None:
        logger.debug(f"  No time column found in {filename} (cols: {columns})")
        return None

    # --- Find flux/counts column ---
    flux_col = None
    flux_values = None

    flux_candidates = ['FLUX', 'RATE', 'COUNTS', 'COUNT_RATE', 'COUNTRATE',
                       'INTENSITY', 'SPECTRUM', 'CHANNEL', 'COUNTS_S',
                       'FLUX_KEV', 'PHOTON_FLUX', 'NET_RATE']

    for candidate in flux_candidates:
        if candidate in columns:
            idx = columns.index(candidate)
            original_name = hdu.columns[idx].name
            flux_col = original_name
            flux_values = data[original_name]
            break

    if flux_col is None:
        # If no named flux column, take the first non-time numeric column
        for col_obj in hdu.columns:
            if col_obj.name != time_col:
                try:
                    test = np.array(data[col_obj.name], dtype=float)
                    if len(test.shape) <= 1:  # 1D data
                        flux_col = col_obj.name
                        flux_values = data[col_obj.name]
                        break
                except (ValueError, TypeError):
                    continue

    if flux_col is None:
        logger.debug(f"  No flux column found in {filename}")
        return None

    # --- Convert time to pandas timestamps ---
    timestamps = _convert_time(time_values, hdu.header)

    # --- Handle multi-dimensional flux (e.g., energy channels) ---
    # asarray avoids copying when the column is already a float ndarray.
    flux_array = np.asarray(flux_values, dtype=float)
    if flux_array.ndim > 1:
        # Sum across energy channels for a broadband light curve
        flux_array = np.nansum(flux_array, axis=1)

    df = pd.DataFrame({
        'timestamp': timestamps,
        'flux': flux_array,
    })

    # Add energy info if available
    for energy_col in ['ENERGY', 'E_MIN', 'E_MAX', 'CHANNEL']:
        if energy_col in columns:
            idx = columns.index(energy_col)
            original_name = hdu.columns[idx].name
            vals = data[original_name]
            if len(np.array(vals).shape) <= 1:
                df[energy_col.lower()] = np.array(vals, dtype=float)

    # Store source metadata
    df.attrs['source_file'] = filename
    df.attrs['time_col'] = time_col
    df.attrs['flux_col'] = flux_col

    return df


def _extract_image_data(hdu, filename: str) -> Optional[pd.DataFrame]:
    """
    Extract data from an image HDU (sometimes used for spectra).
    """
    data = hdu.data
    if data is None:
        return None

    # For 1D spectra stored as image data
    if len(data.shape) == 1:
        header = hdu.header
        n_points = len(data)

        # Try to construct a time axis from header keywords
        tstart = header.get('TSTART', 0)
        tstep = header.get('TIMEDEL', header.get('CDELT1', 1.0))

        times = tstart + np.arange(n_points) * tstep
        timestamps = _convert_time(times, header)

        return pd.DataFrame({
            'timestamp': timestamps,
            'flux': data.astype(float),
        })

    return None


# =============================================================================
# CDF FILE READING
# =============================================================================

def read_cdf_file(filepath: Union[str, Path]) -> pd.DataFrame:
    """
    Read a single CDF (Common Data Format) file and extract time-series flux.

    Some Aditya-L1 / PRADAN auxiliary products and many heliophysics datasets
    ship as CDF rather than FITS. Reading is done with ``cdflib`` (pure-Python,
    no NASA CDF C-library required), which memory-maps the file and decodes
    epoch variables natively.

    Parameters
    ----------
    filepath : str or Path
        Path to the .cdf file.

    Returns
    -------
    pd.DataFrame
        DataFrame with ['timestamp', 'flux'] columns, or empty on failure.
    """
    filepath = Path(filepath)
    logger.info(f"Reading CDF file: {filepath.name}")

    try:
        import cdflib
    except ImportError:
        logger.error(
            "cdflib is not installed — cannot read CDF files. "
            "Install it with: pip install cdflib"
        )
        return pd.DataFrame()

    cdf = cdflib.CDF(str(filepath))
    info = cdf.cdf_info()
    var_names = list(getattr(info, "zVariables", [])) + list(getattr(info, "rVariables", []))
    upper = {v.upper(): v for v in var_names}

    # --- Locate the time/epoch variable ---
    time_candidates = ['EPOCH', 'TIME', 'EPOCH_TIME', 'TIMESTAMP', 'TT2000', 'TIME_UTC']
    time_var = next((upper[c] for c in time_candidates if c in upper), None)
    if time_var is None:
        # Fall back to any variable whose name contains EPOCH/TIME
        time_var = next((v for v in var_names
                         if 'EPOCH' in v.upper() or 'TIME' in v.upper()), None)
    if time_var is None:
        logger.warning(f"  No time variable found in {filepath.name} ({var_names})")
        return pd.DataFrame()

    # --- Locate the flux/counts variable ---
    flux_candidates = ['FLUX', 'RATE', 'COUNTS', 'COUNT_RATE', 'COUNTRATE',
                       'INTENSITY', 'SPECTRUM', 'NET_RATE', 'PHOTON_FLUX']
    flux_var = next((upper[c] for c in flux_candidates if c in upper), None)
    if flux_var is None:
        flux_var = next((v for v in var_names if v != time_var), None)
    if flux_var is None:
        logger.warning(f"  No flux variable found in {filepath.name}")
        return pd.DataFrame()

    raw_time = cdf.varget(time_var)
    # cdflib decodes CDF_EPOCH/EPOCH16/TT2000 to nanosecond-precision datetimes.
    try:
        timestamps = pd.DatetimeIndex(cdflib.cdfepoch.to_datetime(raw_time))
    except Exception:
        timestamps = _convert_time(raw_time, {})

    flux_array = np.asarray(cdf.varget(flux_var), dtype=float)
    if flux_array.ndim > 1:
        flux_array = np.nansum(flux_array, axis=1)

    df = pd.DataFrame({'timestamp': timestamps, 'flux': flux_array})
    df.attrs['source_file'] = filepath.name
    logger.info(f"  Extracted {len(df)} rows from {filepath.name}")
    return df


def _convert_time(time_values, header) -> pd.DatetimeIndex:
    """
    Convert FITS time values to pandas DatetimeIndex.

    Handles multiple time systems:
      - MJD (Modified Julian Date)
      - Seconds since a reference time (MJDREF or DATE-REF)
      - ISO date strings
    """
    time_array = np.array(time_values)

    # Check if values are strings (ISO dates)
    if time_array.dtype.kind in ('U', 'S', 'O'):
        try:
            return pd.to_datetime(time_array)
        except Exception:
            pass

    # Numeric times — determine the reference
    time_array = time_array.astype(float)

    # Check for MJDREF (common in X-ray astronomy FITS)
    mjdref = header.get('MJDREFI', 0) + header.get('MJDREFF', 0.0)
    if mjdref == 0:
        mjdref = header.get('MJDREF', 0.0)

    if mjdref > 0:
        # Time is in seconds since MJDREF
        mjd_times = mjdref + time_array / 86400.0
        astropy_times = Time(mjd_times, format='mjd', scale='utc')
        return pd.DatetimeIndex(astropy_times.datetime64)

    # Check for DATE-REF or DATE-OBS as reference
    date_ref = header.get('DATE-REF', header.get('DATE-OBS', None))
    if date_ref:
        try:
            ref_time = pd.Timestamp(date_ref)
            return pd.DatetimeIndex(
                ref_time + pd.to_timedelta(time_array, unit='s')
            )
        except Exception:
            pass

    # If values are large enough to be MJD directly
    if np.nanmin(time_array) > 40000:  # Plausible MJD range
        astropy_times = Time(time_array, format='mjd', scale='utc')
        return pd.DatetimeIndex(astropy_times.datetime64)

    # Fallback: treat as seconds from epoch start
    logger.warning("Could not determine time reference; using raw seconds.")
    return pd.DatetimeIndex(
        pd.Timestamp('2024-01-01') + pd.to_timedelta(time_array, unit='s')
    )


# =============================================================================
# ZIP ARCHIVE HANDLING
# =============================================================================

def _is_lightcurve_member(name: str) -> bool:
    """
    True only for the LIGHT-CURVE files inside a PRADAN zip — not spectra, GTI,
    housekeeping or event lists (which would otherwise be misread as flux).

      SoLEXS : .../SDD2/AL1_SOLEXS_..._L1.lc.gz   (gzipped FITS light curve)
      HEL1OS : .../czt/lightcurve_czt1.fits, .../cdte/lightcurve_cdte1.fits
    """
    low = name.lower()
    base = low.rsplit('/', 1)[-1]
    if low.endswith('.lc') or low.endswith('.lc.gz'):
        return True
    if base.startswith('lightcurve_') and base.endswith(('.fits', '.fit', '.fts')):
        return True
    return False


def _read_fits_bytes(raw: bytes, member_name: str) -> List[pd.DataFrame]:
    """
    Parse FITS bytes (a single ZIP member) into a list of DataFrames.

    Handles gzipped members (PRADAN SoLEXS light curves ship as ``*.lc.gz``).
    Large members are spilled to a temp file so astropy can memory-map them
    instead of decoding the entire table into RAM at once; small members are
    parsed straight from memory to avoid disk round-trips.
    """
    frames: List[pd.DataFrame] = []
    spill_path = None
    try:
        if member_name.lower().endswith('.gz'):
            import gzip
            raw = gzip.decompress(raw)
        if len(raw) >= MEMMAP_SPILL_BYTES:
            fd, spill_path = tempfile.mkstemp(suffix='.fits')
            with os.fdopen(fd, 'wb') as tmp:
                tmp.write(raw)
            source = spill_path
            open_kwargs = {'memmap': True}
        else:
            source = io.BytesIO(raw)
            open_kwargs = {'memmap': False}

        with fits.open(source, **open_kwargs) as hdul:
            for hdu in hdul:
                if isinstance(hdu, (fits.BinTableHDU, fits.TableHDU)):
                    df = _extract_table_data(hdu, member_name)
                    if df is not None and len(df) > 0:
                        frames.append(df)
    except Exception as e:
        logger.warning(f"  Error reading {member_name}: {e}")
    finally:
        if spill_path is not None:
            try:
                os.unlink(spill_path)
            except OSError:
                pass
    return frames


def read_zip_archive(zip_path: Union[str, Path]) -> pd.DataFrame:
    """
    Read all FITS/CDF files from a ZIP archive, decompressing and parsing
    members in parallel.

    PRADAN often delivers data as .zip files containing many .fits (or .cdf)
    files. Member decompression (zlib) and table parsing (numpy/astropy) both
    release the GIL, so a thread pool processes them concurrently — the main
    speedup for large (100s of MB) archives.

    Parameters
    ----------
    zip_path : str or Path
        Path to the .zip archive.

    Returns
    -------
    pd.DataFrame
        Combined DataFrame from all data files in the archive,
        sorted by timestamp.
    """
    zip_path = Path(zip_path)
    logger.info(f"Reading ZIP archive: {zip_path.name}")

    all_data: List[pd.DataFrame] = []

    with zipfile.ZipFile(zip_path, 'r') as zf:
        names = zf.namelist()
        # Prefer the light-curve files (the flux time-series we actually want).
        members = sorted(f for f in names if _is_lightcurve_member(f))
        if not members:
            # Generic fallback for archives without PRADAN light-curve naming.
            members = sorted(f for f in names
                             if f.lower().endswith(('.fits', '.fit', '.fts')))
    logger.info(f"  Found {len(members)} light-curve file(s) in archive")

    # A single ZipFile handle is not safe for concurrent reads, so each worker
    # opens its own handle on the same archive. Both decompression (zlib) and
    # parsing then run in parallel, and peak memory stays bounded by the worker
    # count rather than the full uncompressed archive size.
    def _read_member(name: str) -> List[pd.DataFrame]:
        with zipfile.ZipFile(zip_path, 'r') as zf_local:
            raw = zf_local.read(name)
        return _read_fits_bytes(raw, name)

    workers = max(1, min(MAX_WORKERS, len(members)))
    if workers > 1:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for frames in pool.map(_read_member, members):
                all_data.extend(frames)
    else:
        for name in members:
            all_data.extend(_read_member(name))

    if not all_data:
        logger.warning(f"  No data extracted from {zip_path.name}")
        return pd.DataFrame()

    result = pd.concat(all_data, ignore_index=True)
    result = result.sort_values('timestamp').reset_index(drop=True)

    # HEL1OS ships 4 detector light curves (czt1/czt2/cdte1/cdte2) that share the
    # same time grid. Summing them per timestamp gives the total hard X-ray count
    # rate (the right quantity for the impulsive-spike nowcast) and removes the
    # duplicate-timestamp rows. Harmless for SoLEXS (single light curve, no dupes).
    if result['timestamp'].duplicated().any():
        n_before = len(result)
        result = result.groupby('timestamp', as_index=False)['flux'].sum()
        logger.info(f"  Summed {n_before} detector rows -> {len(result)} timestamps")

    logger.info(f"  Total rows from archive: {len(result)}")
    return result


# =============================================================================
# HIGH-LEVEL INGESTION
# =============================================================================

def _read_any(filepath: Path) -> pd.DataFrame:
    """Dispatch a single raw file to the right reader by extension."""
    suffix = filepath.suffix.lower()
    if suffix == '.zip':
        return read_zip_archive(filepath)
    if suffix == '.cdf':
        return read_cdf_file(filepath)
    return read_fits_file(filepath)


def load_instrument_data(
    instrument: str,
    data_dir: Optional[Union[str, Path]] = None,
    use_cache: bool = True,
) -> pd.DataFrame:
    """
    Load all data for a given instrument (solexs or hel1os) from the
    raw data directory.

    Scans for .fits, .fit, .fts, .cdf, and .zip files matching the instrument
    name and parses them in parallel. Results are cached in-process so repeated
    calls (e.g. the 6-event validation loop) do not re-parse the raw files.

    Parameters
    ----------
    instrument : str
        Either 'solexs' or 'hel1os' (case-insensitive).
    data_dir : str or Path, optional
        Directory to scan. Defaults to config.RAW_DATA_DIR.
    use_cache : bool
        Reuse a previously parsed result for the same (instrument, dir).
        Set False to force a fresh read. See also :func:`clear_cache`.

    Returns
    -------
    pd.DataFrame
        Combined, time-sorted DataFrame for the instrument.
    """
    instrument = instrument.lower()
    if instrument not in ('solexs', 'hel1os'):
        raise ValueError(f"Unknown instrument: {instrument}. Use 'solexs' or 'hel1os'.")

    data_dir = Path(data_dir) if data_dir else RAW_DATA_DIR

    cache_key = (instrument, str(data_dir.resolve()))
    if use_cache and cache_key in _INSTRUMENT_CACHE:
        cached = _INSTRUMENT_CACHE[cache_key]
        logger.info(f"  Using cached {instrument.upper()} data ({len(cached)} rows)")
        return cached.copy()

    logger.info(f"Loading {instrument.upper()} data from {data_dir}")

    # Find matching files (FITS, CDF, and ZIP)
    patterns = [f"*{instrument}*", f"*{instrument.upper()}*"]
    extensions = ['.fits', '.fit', '.fts', '.cdf', '.zip']

    found_files = []
    for pattern in patterns:
        for ext in extensions:
            found_files.extend(data_dir.glob(f"{pattern}{ext}"))

    # Also scan without instrument name — just grab all data files
    if not found_files:
        for ext in extensions:
            found_files.extend(data_dir.glob(f"*{ext}"))

    found_files = sorted(set(found_files))
    logger.info(f"  Found {len(found_files)} files")

    def _load_one(filepath: Path) -> Optional[pd.DataFrame]:
        try:
            df = _read_any(filepath)
            if len(df) > 0:
                df['instrument'] = instrument.upper()
                return df
        except Exception as e:
            logger.warning(f"  Error processing {filepath.name}: {e}")
        return None

    # Each top-level file is parsed on its own thread. ZIP archives further
    # parallelize their members internally, so we keep this pool modest to avoid
    # oversubscription while still overlapping I/O across files.
    all_data = []
    workers = max(1, min(MAX_WORKERS, len(found_files)))
    if workers > 1:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for df in pool.map(_load_one, found_files):
                if df is not None:
                    all_data.append(df)
    else:
        for filepath in found_files:
            df = _load_one(filepath)
            if df is not None:
                all_data.append(df)

    if not all_data:
        logger.warning(f"  No {instrument.upper()} data loaded")
        return pd.DataFrame()

    result = pd.concat(all_data, ignore_index=True)
    result = result.sort_values('timestamp').reset_index(drop=True)

    # Apply commissioning cutoff
    cutoff = pd.Timestamp(COMMISSIONING_CUTOFF)
    before = len(result)
    result = result[result['timestamp'] >= cutoff].reset_index(drop=True)
    excluded = before - len(result)
    if excluded > 0:
        logger.info(f"  Excluded {excluded} rows before commissioning cutoff ({COMMISSIONING_CUTOFF})")

    logger.info(f"  Loaded {len(result)} rows for {instrument.upper()}")

    if use_cache and len(result) <= CACHE_MAX_ROWS:
        _INSTRUMENT_CACHE[cache_key] = result
        return result.copy()
    if use_cache:
        logger.info(f"  Result exceeds CACHE_MAX_ROWS ({CACHE_MAX_ROWS}); "
                    f"not cached — prefer load_instrument_window for large corpora")
    return result


def _read_target(filepath: Path, member: Optional[str]) -> pd.DataFrame:
    """Read a single FITS member (or whole file) given a (path, member) pair."""
    if member is None:
        return _read_any(filepath)
    # A specific member inside a ZIP — decompress and parse just that one.
    with zipfile.ZipFile(filepath, 'r') as zf:
        raw = zf.read(member)
    frames = _read_fits_bytes(raw, member)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def load_instrument_window(
    instrument: str,
    start: Union[str, pd.Timestamp],
    end: Union[str, pd.Timestamp],
    data_dir: Optional[Union[str, Path]] = None,
) -> pd.DataFrame:
    """
    Load one instrument's data for ONLY the [start, end] window — without
    reading the full corpus. This is the out-of-core entry point that scales
    to 100s of GB.

    Strategy (fastest first):
      1. Query the Parquet column store with predicate pushdown (out-of-core).
      2. Otherwise use the time manifest to open ONLY the raw files whose span
         overlaps the window, parse them in parallel, then slice.

    Parameters
    ----------
    instrument : str
        'solexs' or 'hel1os'.
    start, end : timestamp-like
        Inclusive window bounds.
    data_dir : str or Path, optional
        Raw data directory. Defaults to config.RAW_DATA_DIR.
    """
    from core import datastore

    instrument = instrument.lower()
    start = pd.Timestamp(start)
    end = pd.Timestamp(end)
    data_dir = Path(data_dir) if data_dir else RAW_DATA_DIR

    # --- 1. Parquet store (out-of-core, predicate pushdown) ---
    parquet = datastore.query_window(instrument, start, end)
    if parquet is not None:
        return parquet

    # --- 2. Manifest-pruned raw reads (open only overlapping files) ---
    targets = datastore.select_files(instrument, start, end, data_dir)
    if not targets:
        logger.warning(f"  No {instrument.upper()} files overlap {start}..{end}")
        return pd.DataFrame(columns=['timestamp', 'flux'])

    frames = []
    workers = max(1, min(MAX_WORKERS, len(targets)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for df in pool.map(lambda t: _read_target(Path(t[0]), t[1]), targets):
            if df is not None and len(df) > 0:
                # Slice to the window per-file so we never accumulate the corpus.
                df = df[(df['timestamp'] >= start) & (df['timestamp'] <= end)]
                if len(df) > 0:
                    frames.append(df)

    if not frames:
        return pd.DataFrame(columns=['timestamp', 'flux'])

    result = pd.concat(frames, ignore_index=True)
    result = result.sort_values('timestamp').reset_index(drop=True)
    logger.info(f"  {instrument.upper()} window load: {len(result)} rows "
                f"from {len(targets)} pruned files")
    return result


def load_event_data(
    event_id: str,
    data_dir: Optional[Union[str, Path]] = None,
) -> dict:
    """
    Load both SoLEXS and HEL1OS data for a specific flare event window.

    Uses time-based file pruning (and the Parquet store when built), so only the
    raw data overlapping the event window is read — the corpus as a whole is
    never materialized. This is what lets the pipeline scale from MB to 100+ GB.

    Parameters
    ----------
    event_id : str
        Event ID from the flare catalog (e.g., 'MAY2024_X87').
    data_dir : str or Path, optional
        Directory to scan. Defaults to config.RAW_DATA_DIR.

    Returns
    -------
    dict
        {'solexs': DataFrame, 'hel1os': DataFrame, 'event': FlareEvent}
    """
    from config.flare_catalog import get_event_by_id

    event = get_event_by_id(event_id)
    if event is None:
        raise ValueError(f"Unknown event: {event_id}")

    data_dir = Path(data_dir) if data_dir else RAW_DATA_DIR
    start = pd.Timestamp(event.window_start)
    end = pd.Timestamp(event.window_end)
    logger.info(f"Loading data for event: {event.event_id} ({event.peak_class})")
    logger.info(f"  Event window: {start} -> {end}")

    # Window-only loads, SoLEXS and HEL1OS in parallel.
    with ThreadPoolExecutor(max_workers=2) as pool:
        solexs_future = pool.submit(load_instrument_window, 'solexs', start, end, data_dir)
        hel1os_future = pool.submit(load_instrument_window, 'hel1os', start, end, data_dir)
        solexs_df = solexs_future.result()
        hel1os_df = hel1os_future.result()

    logger.info(f"  SoLEXS rows: {len(solexs_df)}")
    logger.info(f"  HEL1OS rows: {len(hel1os_df)}")

    return {
        'solexs': solexs_df,
        'hel1os': hel1os_df,
        'event': event,
    }
