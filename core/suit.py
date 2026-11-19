# =============================================================================
# S.H.I.E.L.D. 2.0 (EXTENSION) — SUIT UV image feature extractor
# PROOF-OF-CONCEPT to test whether active-region UV features rise BEFORE a flare
# (the precursor X-rays don't have). This is the only Aditya-L1 path to advance
# forecasting.
#
# IMPORTANT (honesty + scale): SUIT produces millions of full-disk image files.
# We do NOT process them all. We sample a small set around known flare dates and
# ask one question: is there a measurable pre-flare rise in active-region UV
# brightness / area / complexity?
#
# Per image we extract simple, interpretable features (no deep learning needed):
#   mean / max brightness, bright-region AREA, number of active regions,
#   and a "complexity" proxy (bright-pixel fraction + edge activity).
# =============================================================================

import io
import gzip
import zipfile
import logging
from pathlib import Path
from typing import Optional, Union, List

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Bright-region threshold = this many sigma above the solar-disk median.
BRIGHT_SIGMA = 4.0
MIN_REGION_PX = 25          # ignore tiny specks (noise / cosmic rays)


def _read_fits_image(raw: bytes):
    """Return (2D image array, header) from raw FITS bytes (gz-aware)."""
    from astropy.io import fits
    if raw[:2] == b'\x1f\x8b':
        raw = gzip.decompress(raw)
    with fits.open(io.BytesIO(raw)) as hdul:
        for hdu in hdul:
            data = getattr(hdu, 'data', None)
            if data is not None and getattr(data, 'ndim', 0) >= 2:
                img = np.asarray(data, dtype=float)
                while img.ndim > 2:        # collapse any leading axes
                    img = img[0]
                return img, hdu.header
    return None, None


def suit_image_features(img: np.ndarray) -> dict:
    """
    Extract interpretable active-region features from one full-disk UV image.
    Robust to the unknown exact SUIT scaling — everything is relative to the
    solar disk's own statistics.
    """
    from scipy import ndimage

    finite = img[np.isfinite(img)]
    if finite.size == 0:
        return {}
    # Solar disk = pixels above a low floor (exclude the black background).
    disk = img > (np.nanpercentile(finite, 20))
    disk_vals = img[disk]
    if disk_vals.size < 100:
        return {}
    med = float(np.nanmedian(disk_vals))
    std = float(np.nanstd(disk_vals)) or 1.0

    # Bright (active) regions = pixels well above the quiet-disk level.
    bright = disk & (img > med + BRIGHT_SIGMA * std)
    labels, n = ndimage.label(bright)
    if n:
        sizes = ndimage.sum(np.ones_like(labels), labels, range(1, n + 1))
        big = sizes[sizes >= MIN_REGION_PX]
    else:
        big = np.array([])

    bright_area = int(bright.sum())
    return {
        'disk_median': med,
        'disk_max': float(np.nanmax(disk_vals)),
        'max_over_median': float(np.nanmax(disk_vals) / med) if med else 0.0,
        'bright_area_px': bright_area,
        'bright_frac': bright_area / float(disk.sum()),
        'n_active_regions': int(len(big)),
        'largest_region_px': int(big.max()) if big.size else 0,
        'brightness_std': std,
    }


def _iter_image_members(path: Path):
    """Yield (name, raw_bytes) for FITS images in a file or zip."""
    suf = path.suffix.lower()
    if suf == '.zip':
        with zipfile.ZipFile(path) as zf:
            for m in zf.namelist():
                if m.lower().endswith(('.fits', '.fits.gz', '.fit', '.fts')):
                    yield m, zf.read(m)
    elif suf in ('.fits', '.fit', '.fts', '.gz'):
        yield path.name, path.read_bytes()


def _timestamp_from_header(header) -> Optional[pd.Timestamp]:
    for k in ('DATE-OBS', 'DATE_OBS', 'T_OBS', 'DATEOBS'):
        if header is not None and k in header:
            try:
                return pd.Timestamp(header[k])
            except Exception:
                pass
    return None


def process_suit_folder(
    folder: Union[str, Path],
    limit: Optional[int] = None,
    out_csv: Optional[Union[str, Path]] = None,
) -> pd.DataFrame:
    """
    Extract per-image active-region features for every SUIT file in `folder`
    (FITS or zipped FITS). Returns a time-sorted DataFrame. Use `limit` to test
    on a small batch first.
    """
    folder = Path(folder)
    files: List[Path] = []
    for ext in ('*.fits', '*.fits.gz', '*.fit', '*.fts', '*.zip', '*.gz'):
        files.extend(folder.rglob(ext))
    files = sorted(set(files))
    if limit:
        files = files[:limit]
    logger.info(f"SUIT: processing {len(files)} files from {folder}")

    rows = []
    for i, fp in enumerate(files):
        try:
            for name, raw in _iter_image_members(fp):
                img, hdr = _read_fits_image(raw)
                if img is None:
                    continue
                feats = suit_image_features(img)
                if not feats:
                    continue
                feats['timestamp'] = _timestamp_from_header(hdr)
                feats['filter'] = (hdr.get('FILTER') or hdr.get('FTR_NAME')
                                   if hdr is not None else None)
                feats['file'] = name
                rows.append(feats)
        except Exception as e:
            logger.warning(f"  SUIT skip {fp.name}: {e}")
        if (i + 1) % 100 == 0:
            logger.info(f"  ...{i+1}/{len(files)} files")

    df = pd.DataFrame(rows)
    if not df.empty and 'timestamp' in df.columns:
        df = df.sort_values('timestamp').reset_index(drop=True)
    if out_csv and not df.empty:
        df.to_csv(out_csv, index=False)
    return df


# =============================================================================
# THE EXPERIMENT — does the active region brighten BEFORE a flare?
# =============================================================================

def preflare_trend(
    suit_df: pd.DataFrame,
    flare_time: Union[str, pd.Timestamp],
    hours_before: float = 48.0,
    feature: str = 'bright_area_px',
) -> dict:
    """
    Test for a pre-flare rise: fit a trend to a SUIT feature over the window
    BEFORE the flare. A clear positive slope = the active region was building up
    (a real precursor X-rays don't provide).

    Returns the slope, % change, and the per-point series for plotting.
    """
    if suit_df.empty or 'timestamp' not in suit_df or feature not in suit_df:
        return {'ok': False, 'reason': 'no SUIT data / feature'}
    ft = pd.Timestamp(flare_time)
    w = suit_df[(suit_df['timestamp'] >= ft - pd.Timedelta(hours=hours_before)) &
                (suit_df['timestamp'] <= ft)].dropna(subset=[feature, 'timestamp'])
    if len(w) < 4:
        return {'ok': False, 'reason': f'only {len(w)} images in pre-flare window'}

    hrs = (w['timestamp'] - w['timestamp'].iloc[0]).dt.total_seconds().to_numpy() / 3600.0
    y = w[feature].to_numpy(dtype=float)
    slope = float(np.polyfit(hrs, y, 1)[0])              # feature units per hour
    start, end = float(np.mean(y[:max(1, len(y)//4)])), float(np.mean(y[-max(1, len(y)//4):]))
    pct = (end - start) / start * 100.0 if start else 0.0
    return {
        'ok': True, 'flare_time': str(ft), 'feature': feature,
        'n_images': int(len(w)), 'hours_covered': round(float(hrs[-1]), 1),
        'slope_per_h': round(slope, 4),
        'pct_change': round(pct, 1),
        'rising': bool(slope > 0 and pct > 10),
        'series': [{'t': str(t), 'v': float(v)} for t, v in zip(w['timestamp'], y)],
    }


# =============================================================================
# TARGETED DOWNLOAD HELPERS — deal with the 10-20 TB archive problem.
#
# Strategy: you never need all of SUIT. You only need images that fall within
# ±WINDOW_H hours of your 6 known flares, in ONE filter. That shrinks the
# download from 20 TB to a few GB of genuinely useful data. Process each batch,
# extract 8 numbers per image, delete the raw FITS immediately. Net disk: ~0.
# =============================================================================

# The 6 priority flares from the SHIELD validation set (same as PRD).
PRIORITY_FLARES = [
    {"label": "Feb 2024 X6.3",  "peak": "2024-02-22 22:34:00", "ar": "AR13590"},
    {"label": "Mar 2024 X-cls", "peak": "2024-03-23 01:08:00", "ar": "AR13614"},
    {"label": "May 2024 X8.7",  "peak": "2024-05-14 16:51:00", "ar": "AR13663"},
    {"label": "Oct 2024 multi", "peak": "2024-10-03 12:00:00", "ar": "MULTI"},
    {"label": "Jan 2025 X1.8",  "peak": "2025-01-07 00:39:00", "ar": "AR13947"},
    {"label": "Nov 2025 X5.1",  "peak": "2025-11-14 02:00:00", "ar": "AR4274"},
]

# Best SUIT filter for active-region tracking (NB = narrow-band Ca II / Mg).
RECOMMENDED_FILTER = "0933NB04"

# Pre-flare window to grab on each side of the peak.
WINDOW_H = 48


def download_targets(
    flares: Optional[list] = None,
    window_h: float = WINDOW_H,
    filter_name: str = RECOMMENDED_FILTER,
    cadence_min: int = 30,
) -> list:
    """
    Print and return the PRADAN SUIT download targets for your priority flares.
    Instead of downloading 20 TB, you download only these narrow time windows
    in a single filter — typically a few GB total.

    Usage:
        from core.suit import download_targets
        targets = download_targets()
        # Then on PRADAN, filter SUIT by each target's start/end + filter.
    """
    flares = flares or PRIORITY_FLARES
    targets = []
    total_images_est = 0

    print("=" * 70)
    print("SUIT TARGETED DOWNLOAD PLAN")
    print(f"Filter : {filter_name}  |  Window: +/-{window_h}h  |  Cadence ~{cadence_min} min")
    print(f"Source : PRADAN -> SUIT -> L1 -> filter '{filter_name}'")
    print("=" * 70)

    for f in flares:
        peak = pd.Timestamp(f["peak"])
        start = peak - pd.Timedelta(hours=window_h)
        end   = peak + pd.Timedelta(hours=2)          # a little after for decay
        n_est = int((end - start).total_seconds() / 60 / cadence_min)
        size_gb = round(n_est * 33 / 1024, 1)         # 33 MB per SUIT image
        total_images_est += n_est
        targets.append({
            "label":      f["label"],
            "ar":         f["ar"],
            "peak":       str(peak),
            "start":      str(start.date()),
            "end":        str(end.date()),
            "filter":     filter_name,
            "images_est": n_est,
            "size_gb_est": size_gb,
        })
        print(f"\n  {f['label']} ({f['ar']})")
        print(f"    Peak   : {peak}")
        print(f"    Pull   : {start.strftime('%Y-%m-%d %H:%M')} -> {end.strftime('%Y-%m-%d %H:%M')}")
        print(f"    Filter : {filter_name}")
        print(f"    ~{n_est} images  (~{size_gb} GB before processing)")

    total_gb = round(total_images_est * 33 / 1024, 1)
    print("\n" + "=" * 70)
    print(f"TOTAL ESTIMATE : ~{total_images_est} images  (~{total_gb} GB to download)")
    print(f"AFTER PROCESS  : ~{round(total_images_est * 8 * 8 / 1e6, 1)} MB (CSV features only)")
    print("TIP: Process each batch with process_suit_streaming() to auto-delete")
    print("     raw FITS after extraction. Disk footprint stays near zero.")
    print("=" * 70)
    return targets


def process_suit_streaming(
    folder: Union[str, Path],
    out_csv: Union[str, Path],
    delete_after: bool = False,
    batch_size: int = 200,
    filter_name: Optional[str] = None,
    start_time: Optional[Union[str, pd.Timestamp]] = None,
    end_time:   Optional[Union[str, pd.Timestamp]] = None,
) -> pd.DataFrame:
    """
    Memory-safe streaming processor for large SUIT folders.

    Processes files in batches of `batch_size`, appends features to `out_csv`
    incrementally (so you never lose work if it crashes), and optionally deletes
    raw FITS after each batch to keep disk usage near zero.

    Args:
        folder      : path holding the downloaded SUIT FITS files
        out_csv     : output CSV (appended to, safe to resume)
        delete_after: if True, delete each raw file after extracting features
        batch_size  : files per batch (200 = ~6.6 GB in RAM briefly, then freed)
        filter_name : only process files whose name contains this string
        start_time  : skip files timestamped before this
        end_time    : skip files timestamped after this
    """
    folder = Path(folder)
    out_csv = Path(out_csv)
    t0_filter = pd.Timestamp(start_time) if start_time else None
    t1_filter = pd.Timestamp(end_time)   if end_time   else None

    # Collect all candidate files
    files: List[Path] = []
    for ext in ('*.fits', '*.fits.gz', '*.fit', '*.fts'):
        files.extend(folder.rglob(ext))
    files = sorted(set(files))

    if filter_name:
        files = [f for f in files if filter_name in f.name]

    logger.info(f"SUIT streaming: {len(files)} files in {folder}")

    # Check for already-processed files so we can resume
    already = set()
    if out_csv.exists():
        try:
            done = pd.read_csv(out_csv, usecols=['file'])
            already = set(done['file'].tolist())
            logger.info(f"  resuming: {len(already)} files already done")
        except Exception:
            pass

    files = [f for f in files if f.name not in already]
    logger.info(f"  remaining: {len(files)} files to process")

    total_rows = 0
    first_write = not out_csv.exists()

    for batch_start in range(0, len(files), batch_size):
        batch = files[batch_start: batch_start + batch_size]
        rows = []

        for fp in batch:
            try:
                raw = fp.read_bytes()
                img, hdr = _read_fits_image(raw)
                del raw                             # free ~33 MB immediately
                if img is None:
                    continue
                ts = _timestamp_from_header(hdr)
                # time-window filter
                if t0_filter and ts and ts < t0_filter:
                    continue
                if t1_filter and ts and ts > t1_filter:
                    continue
                feats = suit_image_features(img)
                del img                             # free image array
                if not feats:
                    continue
                feats['timestamp'] = ts
                feats['filter']    = (hdr.get('FILTER') or hdr.get('FTR_NAME')
                                      if hdr is not None else None)
                feats['file'] = fp.name
                rows.append(feats)
                if delete_after:
                    fp.unlink(missing_ok=True)
            except Exception as e:
                logger.warning(f"  skip {fp.name}: {e}")

        if rows:
            batch_df = pd.DataFrame(rows)
            batch_df.to_csv(out_csv, mode='a', header=first_write, index=False)
            first_write = False
            total_rows += len(batch_df)

        done_n = batch_start + len(batch)
        logger.info(f"  batch {done_n}/{len(files)+batch_start} done | {total_rows} rows saved")
        print(f"  {done_n}/{len(files)+batch_start} files processed | {total_rows} rows -> {out_csv.name}")

    if total_rows == 0:
        return pd.DataFrame()

    result = pd.read_csv(out_csv)
    if 'timestamp' in result.columns:
        result['timestamp'] = pd.to_datetime(result['timestamp'])
        result = result.sort_values('timestamp').reset_index(drop=True)
        result.to_csv(out_csv, index=False)
    logger.info(f"SUIT streaming done: {total_rows} rows -> {out_csv}")
    return result


def build_suit_forecast_dataset(
    suit_df: pd.DataFrame, catalog: pd.DataFrame,
    step_h: float = 6.0, horizon_h: float = 24.0,
) -> pd.DataFrame:
    """
    Build a supervised table from SUIT features: features at time t (resampled to
    step_h) -> label = M+ flare within next horizon_h. For the ML SUIT forecaster
    once enough image coverage exists. Needs continuous SUIT coverage, not just
    snapshots around one flare.
    """
    if suit_df.empty:
        return pd.DataFrame()
    from core.impact import class_to_flux
    cat = catalog.copy(); cat['peak_time'] = pd.to_datetime(cat['peak_time'])
    cat['flux'] = cat['goes_class'].map(class_to_flux)
    s = suit_df.dropna(subset=['timestamp']).set_index('timestamp').sort_index()
    feat_cols = [c for c in ['max_over_median', 'bright_area_px', 'bright_frac',
                             'n_active_regions', 'largest_region_px'] if c in s.columns]
    agg = s[feat_cols].resample(f'{int(step_h*60)}min').mean().dropna()
    mtimes = cat.loc[cat['flux'] >= 1e-5, 'peak_time']
    rows = []
    for t, r in agg.iterrows():
        hi = t + pd.Timedelta(hours=horizon_h)
        y = int(((mtimes > t) & (mtimes <= hi)).any())
        rows.append({**r.to_dict(), 'time': t, 'y': y})
    return pd.DataFrame(rows)

