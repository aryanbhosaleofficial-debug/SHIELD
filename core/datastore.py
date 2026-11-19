# =============================================================================
# S.H.I.E.L.D. Core Engine — Out-of-Core Data Store
# Scales ingestion from MB to 100s of GB.
#
# The naive approach ("load every raw file, concat into one DataFrame, filter")
# cannot survive 100 GB — it OOMs long before the physics engine runs. This
# module adds two out-of-core strategies that keep peak memory bounded to a few
# files at a time regardless of total corpus size:
#
#   1. TIME MANIFEST + FILE PRUNING
#      Cheaply probe each raw file's [t_min, t_max] from FITS headers (no table
#      load) and persist it. Event windows are only a few days, so a query opens
#      ONLY the files that overlap the window instead of the whole corpus.
#
#   2. PARQUET COLUMN STORE
#      Convert raw -> date-partitioned Parquet once, streaming file-by-file. Then
#      query with partition + row-group predicate pushdown, reading only the
#      relevant slice off disk. Repeated queries (the 6-event validation loop,
#      the dashboard) become near-instant and never materialize the full corpus.
#
# Both degrade gracefully: if pyarrow is absent, manifest pruning still works on
# the raw files; if even header probing fails, we fall back to a full scan.
# =============================================================================

import re
import json
import logging
import zipfile
from pathlib import Path
from datetime import datetime
from typing import Optional, Union, List, Tuple

import numpy as np
import pandas as pd

from config.settings import RAW_DATA_DIR, PROCESSED_DATA_DIR, COMMISSIONING_CUTOFF

logger = logging.getLogger(__name__)

# Where the manifest and Parquet partitions live.
MANIFEST_PATH = PROCESSED_DATA_DIR / "_manifest.json"
PARQUET_STORE_DIR = PROCESSED_DATA_DIR / "parquet_store"
# Human-friendly filtered CSVs (one per instrument) for sharing with teammates.
FILTERED_CSV_DIR = PROCESSED_DATA_DIR / "filtered_csv"
# Remembers which raw folder was last prepared, so --event can read real data.
ACTIVE_BATCH_PATH = PROCESSED_DATA_DIR / "_active_batch.txt"

# Rows per batch when streaming a large file/table into Parquet. Caps peak RAM.
STREAM_BATCH_ROWS = 2_000_000

DATA_EXTENSIONS = ('.fits', '.fit', '.fts', '.cdf')


def reset_store() -> None:
    """
    Forget everything about the previous data batch: delete the time manifest,
    the Parquet store, and the active-batch pointer. Call this when you SWAP the
    raw data (e.g. delete the old event and drop in a new one) so nothing stale
    is carried over.
    """
    import shutil
    if MANIFEST_PATH.exists():
        MANIFEST_PATH.unlink()
        logger.info(f"  Removed manifest: {MANIFEST_PATH}")
    if PARQUET_STORE_DIR.exists():
        shutil.rmtree(PARQUET_STORE_DIR)
        logger.info(f"  Removed Parquet store: {PARQUET_STORE_DIR}")
    if ACTIVE_BATCH_PATH.exists():
        ACTIVE_BATCH_PATH.unlink()
    logger.info("  Data store reset — ready for a fresh batch.")


def set_active_data_dir(data_dir: Union[str, Path]) -> None:
    """Record which raw folder is currently prepared (used by --event)."""
    ACTIVE_BATCH_PATH.parent.mkdir(parents=True, exist_ok=True)
    ACTIVE_BATCH_PATH.write_text(str(Path(data_dir).resolve()))


def get_active_data_dir() -> Optional[Path]:
    """Return the currently-prepared raw folder, or None if none/missing."""
    if not ACTIVE_BATCH_PATH.exists():
        return None
    p = Path(ACTIVE_BATCH_PATH.read_text().strip())
    return p if p.exists() else None


def _have_pyarrow() -> bool:
    try:
        import pyarrow  # noqa: F401
        return True
    except ImportError:
        return False


# =============================================================================
# CHEAP TIME-BOUNDS PROBING  (read headers, never the full table)
# =============================================================================

def _bounds_from_header(header) -> Optional[Tuple[pd.Timestamp, pd.Timestamp]]:
    """
    Derive [t_min, t_max] from FITS header keywords without touching table data.

    Tries TSTART/TSTOP (seconds from MJDREF) first, then DATE-OBS/DATE-END
    string keywords. Returns None if the header carries no usable time span.
    """
    from core.ingest import _convert_time  # lazy: avoids import cycle

    # --- TSTART / TSTOP in seconds since MJDREF (X-ray FITS convention) ---
    tstart = header.get('TSTART', None)
    tstop = header.get('TSTOP', header.get('TEND', None))
    if tstart is not None and tstop is not None:
        try:
            idx = _convert_time(np.array([float(tstart), float(tstop)]), header)
            return pd.Timestamp(idx[0]), pd.Timestamp(idx[1])
        except Exception:
            pass

    # --- ISO date string keywords ---
    date_obs = header.get('DATE-OBS', header.get('DATE_OBS', None))
    date_end = header.get('DATE-END', header.get('DATE_END', date_obs))
    if date_obs is not None:
        try:
            t0 = pd.Timestamp(date_obs)
            t1 = pd.Timestamp(date_end) if date_end is not None else t0
            return min(t0, t1), max(t0, t1)
        except Exception:
            pass

    return None


def probe_time_bounds(filepath: Union[str, Path]) -> List[dict]:
    """
    Return cheap time-bounds records for a raw file without loading flux data.

    For a plain FITS/CDF file this is one record; for a ZIP it is one record per
    FITS member. Each record:
        {'member': <name or None>, 't_min': ISO str, 't_max': ISO str}

    FITS headers sit at the start of each HDU, so astropy reads only a few KB
    per file even for multi-GB tables — this is what makes pruning affordable.
    """
    filepath = Path(filepath)
    suffix = filepath.suffix.lower()

    if suffix == '.zip':
        return _probe_zip(filepath)
    if suffix == '.cdf':
        return _probe_cdf(filepath)
    return _probe_fits_path(filepath)


def _probe_fits_stream(stream, member: Optional[str]) -> Optional[dict]:
    from astropy.io import fits
    try:
        with fits.open(stream, memmap=False) as hdul:
            for hdu in hdul:
                b = _bounds_from_header(hdu.header)
                if b is not None:
                    return {'member': member,
                            't_min': b[0].isoformat(), 't_max': b[1].isoformat()}
    except Exception as e:
        logger.debug(f"  header probe failed for {member or 'file'}: {e}")
    return None


def _probe_fits_path(filepath: Path) -> List[dict]:
    rec = _probe_fits_stream(str(filepath), None)
    return [rec] if rec else []


def _probe_zip(zip_path: Path) -> List[dict]:
    out = []
    with zipfile.ZipFile(zip_path, 'r') as zf:
        members = [m for m in zf.namelist()
                   if m.lower().endswith(('.fits', '.fit', '.fts'))]
        for name in members:
            with zf.open(name) as fh:
                rec = _probe_fits_stream(fh, name)
                if rec:
                    out.append(rec)
    return out


def _probe_cdf(filepath: Path) -> List[dict]:
    try:
        import cdflib
    except ImportError:
        return []
    try:
        cdf = cdflib.CDF(str(filepath))
        info = cdf.cdf_info()
        names = list(getattr(info, 'zVariables', [])) + list(getattr(info, 'rVariables', []))
        tvar = next((v for v in names if 'EPOCH' in v.upper() or 'TIME' in v.upper()), None)
        if tvar is None:
            return []
        raw = cdf.varget(tvar)
        ts = pd.DatetimeIndex(cdflib.cdfepoch.to_datetime([raw[0], raw[-1]]))
        return [{'member': None, 't_min': ts.min().isoformat(), 't_max': ts.max().isoformat()}]
    except Exception:
        return []


# =============================================================================
# MANIFEST  (persisted file -> time-bounds index, incremental)
# =============================================================================

def _instrument_of(name: str) -> Optional[str]:
    low = name.lower()
    # Real ISRO PRADAN naming: SoLEXS zips are "AL1_SLX_...", HEL1OS are "HLS_...".
    if 'slx' in low or 'solexs' in low:
        return 'solexs'
    if 'hls' in low or 'hel1os' in low or 'hel1' in low:
        return 'hel1os'
    return None


# Real PRADAN zip-name patterns (the date/time is in the filename itself, so we
# can index 30k+ files instantly without opening any of them).
#   SoLEXS : AL1_SLX_L1_20240220_v1.0.zip        -> whole-day file
#   HEL1OS : HLS_20240514_000006_43180sec_lev1_V111.zip -> start + duration
_SLX_RE = re.compile(r'AL1_SLX_L1_(\d{8})_v(\d+)\.(\d+)', re.I)
_HLS_RE = re.compile(r'HLS_(\d{8})_(\d{6})_(\d+)sec.*?_V(\d+)', re.I)


def parse_raw_filename(name: str) -> Optional[dict]:
    """
    Derive instrument + time span + version from a PRADAN zip filename, with no
    file I/O. Returns None for names that don't match the known patterns (those
    fall back to opening the file header).

    'data_key' groups reprocessed versions of the SAME data so we can keep only
    the highest version (e.g. SoLEXS v1.0 vs v1.1; HEL1OS V111 vs V211 vs V311).
    """
    base = Path(name).name
    m = _SLX_RE.search(base)
    if m:
        d = pd.Timestamp(datetime.strptime(m.group(1), '%Y%m%d'))
        return {
            'instrument': 'solexs',
            't_min': d,
            't_max': d + pd.Timedelta(hours=23, minutes=59, seconds=59),
            'version': (int(m.group(2)), int(m.group(3))),
            'data_key': f"solexs_{m.group(1)}",
        }
    m = _HLS_RE.search(base)
    if m:
        start = pd.Timestamp(datetime.strptime(m.group(1) + m.group(2), '%Y%m%d%H%M%S'))
        return {
            'instrument': 'hel1os',
            't_min': start,
            't_max': start + pd.Timedelta(seconds=int(m.group(3))),
            'version': (int(m.group(4)),),
            'data_key': f"hel1os_{m.group(1)}_{m.group(2)}_{m.group(3)}",
        }
    return None


def _dedup_versions(rows: List[dict]) -> List[dict]:
    """Keep only the highest-version file per data_key; pass through the rest."""
    best: dict = {}
    passthrough: List[dict] = []
    for r in rows:
        key = r.get('data_key')
        if not key:
            passthrough.append(r)
            continue
        ver = tuple(r.get('version') or (0,))
        if key not in best or ver > tuple(best[key].get('version') or (0,)):
            best[key] = r
    return list(best.values()) + passthrough


def _list_raw_files(data_dir: Path,
                    exclude: Optional[List[str]] = None) -> List[Path]:
    # Recursive: PRADAN data is delivered in per-instrument subfolders
    # (e.g. F:\SoLEXS\*.zip, F:\HEL1OS\*.zip), so pointing --prepare at the
    # parent must still find everything underneath.
    #
    # `exclude` drops any file whose path contains one of the given (case-
    # insensitive) substrings — used to skip whole subfolders, e.g. a huge
    # '2026' streaming folder or the 'Dec 2023' commissioning data.
    files: List[Path] = []
    for ext in DATA_EXTENSIONS + ('.zip',):
        files.extend(data_dir.rglob(f"*{ext}"))
    files = sorted(set(files))
    if exclude:
        toks = [t.lower() for t in exclude]
        files = [f for f in files
                 if not any(t in str(f).lower() for t in toks)]
    return files


def build_manifest(
    data_dir: Optional[Union[str, Path]] = None,
    rebuild: bool = False,
    exclude: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Probe time bounds for every raw file and persist a manifest. Incremental:
    files already recorded (matched by path + size + mtime) are skipped, so
    re-running after adding a few files only probes the new ones.

    Returns
    -------
    pd.DataFrame with columns:
        ['path', 'member', 'instrument', 't_min', 't_max', 'size', 'mtime']
    """
    data_dir = Path(data_dir) if data_dir else RAW_DATA_DIR

    existing: dict = {}
    if MANIFEST_PATH.exists() and not rebuild:
        try:
            for row in json.loads(MANIFEST_PATH.read_text()):
                existing[(row['path'], row.get('size'), row.get('mtime'))] = row
        except Exception:
            existing = {}

    rows: List[dict] = []
    files = _list_raw_files(data_dir, exclude=exclude)
    scanned_paths = {str(fp) for fp in files}
    logger.info(f"Building manifest for {len(files)} raw files in {data_dir}")

    # Incremental across folders: keep previously-indexed files that live OUTSIDE
    # this data_dir (e.g. SoLEXS already indexed when we now add HEL1OS), as long
    # as they still exist on disk. Without this, indexing a second instrument
    # folder would wipe the first.
    if not rebuild:
        carried = 0
        for (p, _s, _mt), row in existing.items():
            if p not in scanned_paths and Path(p).exists():
                rows.append(row)
                carried += 1
        if carried:
            logger.info(f"  Carried over {carried} previously-indexed files "
                        f"from other folders")

    for fp in files:
        try:
            stat = fp.stat()
        except OSError:
            continue
        key = (str(fp), stat.st_size, int(stat.st_mtime))
        if key in existing:
            rows.append(existing[key])
            continue

        # Fast path: get instrument + time span straight from the filename.
        parsed = parse_raw_filename(fp.name)
        if parsed is not None:
            rows.append({
                'path': str(fp),
                'member': None,
                'instrument': parsed['instrument'],
                't_min': parsed['t_min'].isoformat(),
                't_max': parsed['t_max'].isoformat(),
                'version': list(parsed['version']),
                'data_key': parsed['data_key'],
                'size': stat.st_size,
                'mtime': int(stat.st_mtime),
            })
            continue

        # Fallback: open the file and read time bounds from FITS/CDF headers.
        instrument = _instrument_of(fp.name)
        for rec in probe_time_bounds(fp):
            rows.append({
                'path': str(fp),
                'member': rec['member'],
                'instrument': instrument,
                't_min': rec['t_min'],
                't_max': rec['t_max'],
                'version': None,
                'data_key': None,
                'size': stat.st_size,
                'mtime': int(stat.st_mtime),
            })

    # Keep only the highest reprocessing version of each piece of data.
    before = len(rows)
    rows = _dedup_versions(rows)
    deduped = before - len(rows)

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(rows, indent=2))
    logger.info(f"  Manifest written: {len(rows)} entries -> {MANIFEST_PATH}"
                + (f" ({deduped} duplicate versions dropped)" if deduped else ""))
    return pd.DataFrame(rows)


def load_manifest() -> Optional[pd.DataFrame]:
    if not MANIFEST_PATH.exists():
        return None
    try:
        df = pd.DataFrame(json.loads(MANIFEST_PATH.read_text()))
        if df.empty:
            return df
        df['t_min'] = pd.to_datetime(df['t_min'])
        df['t_max'] = pd.to_datetime(df['t_max'])
        return df
    except Exception as e:
        logger.warning(f"Could not read manifest: {e}")
        return None


def select_files(
    instrument: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
    data_dir: Optional[Union[str, Path]] = None,
) -> List[Tuple[str, Optional[str]]]:
    """
    Return [(path, member)] for files whose time span overlaps [start, end] for
    the given instrument. Builds the manifest on first use. This is the pruning
    step that makes a 100 GB corpus tractable: only overlapping files are read.
    """
    manifest = load_manifest()
    if manifest is None or manifest.empty:
        manifest = build_manifest(data_dir)
        if not manifest.empty:
            manifest['t_min'] = pd.to_datetime(manifest['t_min'])
            manifest['t_max'] = pd.to_datetime(manifest['t_max'])

    if manifest is None or manifest.empty:
        return []

    inst = instrument.lower()
    overlap = (manifest['t_min'] <= end) & (manifest['t_max'] >= start)

    # Prefer files explicitly named for this instrument (e.g. "*solexs*").
    hits = manifest[(manifest['instrument'] == inst) & overlap]
    if len(hits) == 0:
        # Only when NO file is tagged for this instrument do we fall back to
        # instrument-unknown files. This prevents OTHER Aditya-L1 instruments
        # (MAG / ASPEX / PAPA), which carry no solexs/hel1os tag, from being
        # read as SoLEXS/HEL1OS flux when the real SoLEXS/HEL1OS files ARE named.
        hits = manifest[manifest['instrument'].isna() & overlap]

    # Self-healing: drop any manifest entries whose file was deleted since the
    # manifest was built (e.g. after a batch swap without a reset). This keeps
    # the window load from trying to open files that no longer exist.
    targets = [(p, m) for p, m in zip(hits['path'], hits['member'])
               if Path(p).exists()]
    missing = len(hits) - len(targets)
    logger.info(f"  Pruning: {len(targets)}/{len(manifest)} files overlap "
                f"{inst.upper()} window {start.date()}..{end.date()}"
                + (f" ({missing} stale entries skipped)" if missing else ""))
    return targets


# =============================================================================
# PARQUET COLUMN STORE  (out-of-core, partitioned, predicate pushdown)
# =============================================================================

def _store_dir(instrument: str) -> Path:
    return PARQUET_STORE_DIR / f"instrument={instrument.lower()}"


def build_parquet_store(
    data_dir: Optional[Union[str, Path]] = None,
    instruments: Tuple[str, ...] = ('solexs', 'hel1os'),
    rebuild: bool = False,
) -> None:
    """
    Convert raw files into a date-partitioned Parquet store, streaming one raw
    file at a time so peak memory stays bounded no matter the corpus size.

    Layout:
        parquet_store/instrument=solexs/date=2024-05-10/part-<n>.parquet

    Date partitioning lets queries skip whole days; row-group statistics inside
    each file let pyarrow skip non-matching row groups. Together they give true
    out-of-core windowed reads.
    """
    if not _have_pyarrow():
        logger.warning("pyarrow not installed — Parquet store unavailable; "
                       "queries will fall back to pruned raw reads. "
                       "Install with: pip install pyarrow")
        return

    import pyarrow as pa
    import pyarrow.parquet as pq
    from core.ingest import read_fits_file, read_zip_archive, read_cdf_file

    data_dir = Path(data_dir) if data_dir else RAW_DATA_DIR
    cutoff = pd.Timestamp(COMMISSIONING_CUTOFF)

    for instrument in instruments:
        out_root = _store_dir(instrument)
        if out_root.exists() and rebuild:
            import shutil
            shutil.rmtree(out_root)
        out_root.mkdir(parents=True, exist_ok=True)

        files = [f for f in _list_raw_files(data_dir)
                 if _instrument_of(f.name) in (instrument, None)]
        logger.info(f"Building Parquet store for {instrument.upper()} "
                    f"from {len(files)} files")

        part_counter = 0
        for fp in files:
            suffix = fp.suffix.lower()
            try:
                if suffix == '.zip':
                    df = read_zip_archive(fp)
                elif suffix == '.cdf':
                    df = read_cdf_file(fp)
                else:
                    df = read_fits_file(fp)
            except Exception as e:
                logger.warning(f"  skip {fp.name}: {e}")
                continue

            if df is None or df.empty:
                continue

            df = df[['timestamp', 'flux']].copy()
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df[df['timestamp'] >= cutoff]
            if df.empty:
                continue
            df['date'] = df['timestamp'].dt.strftime('%Y-%m-%d')

            # Stream out in date-partitioned batches.
            for date_val, grp in df.groupby('date', sort=True):
                part_dir = out_root / f"date={date_val}"
                part_dir.mkdir(parents=True, exist_ok=True)
                table = pa.Table.from_pandas(
                    grp[['timestamp', 'flux']].reset_index(drop=True),
                    preserve_index=False,
                )
                pq.write_table(table, part_dir / f"part-{part_counter:06d}.parquet")
                part_counter += 1

        logger.info(f"  {instrument.upper()} store: {part_counter} partitions "
                    f"-> {out_root}")


def query_window(
    instrument: str,
    start: Union[str, datetime, pd.Timestamp],
    end: Union[str, datetime, pd.Timestamp],
) -> Optional[pd.DataFrame]:
    """
    Read [start, end] for one instrument out of the Parquet store using
    partition + row-group predicate pushdown. Returns None if the store is
    unavailable so callers can fall back to pruned raw reads.
    """
    if not _have_pyarrow():
        return None
    out_root = _store_dir(instrument)
    if not out_root.exists():
        return None

    import pyarrow.dataset as ds

    start = pd.Timestamp(start)
    end = pd.Timestamp(end)

    dataset = ds.dataset(out_root, format='parquet', partitioning='hive')
    ts = ds.field('timestamp')
    table = dataset.to_table(filter=(ts >= pa_ts(start)) & (ts <= pa_ts(end)))
    df = table.to_pandas()
    if df.empty:
        return df
    df = df.sort_values('timestamp').reset_index(drop=True)
    logger.info(f"  Parquet query {instrument.upper()} "
                f"{start} -> {end}: {len(df)} rows (out-of-core)")
    return df


def pa_ts(ts: pd.Timestamp):
    """Convert a pandas Timestamp to a pyarrow scalar for filter expressions."""
    import pyarrow as pa
    return pa.scalar(ts.to_pydatetime(), type=pa.timestamp('ns'))


# =============================================================================
# SHAREABLE FILTERED EXPORT  (clean CSV per instrument, for teammates)
# =============================================================================

def export_filtered_csv(
    data_dir: Optional[Union[str, Path]] = None,
    event_ids: Optional[List[str]] = None,
    instruments: Tuple[str, ...] = ('solexs', 'hel1os'),
) -> List[Path]:
    """
    Write clean, human-friendly CSVs (timestamp, flux) into
    data/processed/filtered_csv/, ONE PER EVENT PER INSTRUMENT, e.g.:

        FEB2024_X63_solexs_filtered.csv
        FEB2024_X63_hel1os_filtered.csv

    This is the Excel-openable version of the filtered data — the files you hand
    to a teammate. Per-event (not one giant mixed file) so each event is shareable
    on its own, and so the export reads ONLY that event's files via manifest
    pruning (never the whole archive).

    Parameters
    ----------
    data_dir : str or Path, optional
        Raw folder. Defaults to the active prepared batch.
    event_ids : list of str, optional
        Restrict to these catalog events. Default: every catalog event that has
        data in the current manifest.
    instruments : tuple
        Which instruments to export.

    Returns the list of CSV paths written.
    """
    from config.flare_catalog import get_all_events
    from core.ingest import load_instrument_window

    data_dir = Path(data_dir) if data_dir else (get_active_data_dir() or RAW_DATA_DIR)
    FILTERED_CSV_DIR.mkdir(parents=True, exist_ok=True)
    written: List[Path] = []

    events = get_all_events()
    if event_ids:
        wanted = set(event_ids)
        events = [e for e in events if e.event_id in wanted]

    for ev in events:
        for instrument in instruments:
            try:
                df = load_instrument_window(
                    instrument, ev.window_start, ev.window_end, data_dir)
            except Exception as e:
                logger.warning(f"  {ev.event_id}/{instrument}: load failed ({e})")
                continue
            if df is None or df.empty:
                continue

            df = df.copy()
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = (df.dropna(subset=['timestamp'])
                    .drop_duplicates('timestamp')
                    .sort_values('timestamp')
                    .reset_index(drop=True))

            out_path = FILTERED_CSV_DIR / f"{ev.event_id}_{instrument}_filtered.csv"
            df.to_csv(out_path, index=False)
            written.append(out_path)
            logger.info(f"  Filtered CSV: {ev.event_id} {instrument.upper()} "
                        f"-> {out_path.name} ({len(df):,} rows)")

    return written


# =============================================================================
# ONE-CALL BATCH PREPARATION  (the swap-and-refeed entry point)
# =============================================================================

def prepare_batch(
    data_dir: Union[str, Path],
    build_parquet: bool = True,
    exclude: Optional[List[str]] = None,
    export_csv: bool = True,
    csv_event_ids: Optional[List[str]] = None,
) -> dict:
    """
    Prepare a freshly-supplied raw-data folder for querying. This is the single
    step to run each time you swap in a new batch of data:

        1. reset_store()           — forget the previous batch entirely
        2. build_manifest(dir)     — cheaply index every file's time span
        3. build_parquet_store(dir)— (optional) build the out-of-core column store

    Safe to run on 100+ GB: step 2 only reads file headers, step 3 streams one
    file at a time. Returns a small summary dict.

    Parameters
    ----------
    data_dir : str or Path
        Folder holding the new raw .fits/.zip/.cdf files.
    build_parquet : bool
        Also build the Parquet store (needs pyarrow). If False, queries still
        work via manifest-pruned raw reads, just a little slower on repeats.
    """
    data_dir = Path(data_dir)
    if not data_dir.exists():
        raise FileNotFoundError(f"Data folder not found: {data_dir}")

    logger.info(f"Preparing new data batch from: {data_dir}")
    reset_store()
    manifest = build_manifest(data_dir, rebuild=True, exclude=exclude)
    if build_parquet:
        build_parquet_store(data_dir, rebuild=True)
    set_active_data_dir(data_dir)

    # Drop human-friendly per-event filtered CSVs so you can hand the cleaned
    # data straight to a teammate. Reads only each event's pruned files.
    csv_paths = []
    if export_csv:
        try:
            csv_paths = export_filtered_csv(data_dir, event_ids=csv_event_ids)
        except Exception as e:
            logger.warning(f"  filtered CSV export skipped: {e}")

    summary = {
        'data_dir': str(data_dir),
        'files_indexed': int(manifest['path'].nunique()) if not manifest.empty else 0,
        'manifest_entries': int(len(manifest)),
        'parquet_built': bool(build_parquet and _have_pyarrow()),
        'filtered_csv': [str(p) for p in csv_paths],
    }
    logger.info(f"  Batch ready: {summary['files_indexed']} files indexed "
                f"({summary['manifest_entries']} entries)")
    return summary
