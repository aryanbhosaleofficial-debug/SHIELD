# =============================================================================
# S.H.I.E.L.D. — Continuous Flare Scan (out-of-core)
# Sweeps a long time range (e.g. Jan 2024 -> present) in overlapping chunks,
# runs the Layer 1 physics engine on each chunk, and reports EVERY flare it
# finds plus a false-alarm count — without ever loading the whole archive into
# memory.
#
# Two value props this proves to judges:
#   1. The engine finds flares it was never told about (generalisation).
#   2. Over a long quiet baseline it stays under the PRD false-positive target.
#
# The physics core is zero-training, so this is pure live detection across the
# whole record — no learning from history, just the same calculus run on every
# window.
# =============================================================================

import logging
from typing import Optional, Union, List, Dict
from pathlib import Path

import numpy as np
import pandas as pd

from core.preprocess import align_timeseries, clean_flux_data
from core.physics_engine import run_physics_engine, _flux_to_class

logger = logging.getLogger(__name__)

# Per-chunk window. A flare (pre-flare + impulsive + decay) fits comfortably in
# a few hours; a 24h chunk also gives plenty of quiet baseline for the engine's
# auto-calibration. Overlap stops a flare on a chunk boundary being missed.
DEFAULT_CHUNK_HOURS = 24
DEFAULT_OVERLAP_HOURS = 2
# Two detections within this many minutes are treated as the same flare
# (de-duplicates flares seen in the overlap between adjacent chunks).
DEDUP_MINUTES = 30
# A FORECAST with no NOWCAST within this window counts as a false alarm.
FORECAST_FOLLOWUP_MIN = 60


def _detect_in_window(
    solexs_df: pd.DataFrame,
    hel1os_df: pd.DataFrame,
) -> Dict:
    """
    Run align + clean + physics on one already-loaded chunk.
    Returns {'flares': [...], 'forecasts': [...]} for this window, or empty.
    """
    if len(solexs_df) == 0 or len(hel1os_df) == 0:
        return {'flares': [], 'forecasts': []}

    aligned = align_timeseries(solexs_df, hel1os_df)
    if aligned.empty or len(aligned) < 600:  # need ~10 min to say anything
        return {'flares': [], 'forecasts': []}
    cleaned = clean_flux_data(aligned)

    physics = run_physics_engine(cleaned, auto_calibrate=True)

    nowcasts = physics.hel1os_detections
    forecasts = physics.solexs_detections

    pdf = physics.df
    pts = pdf['timestamp'].values
    sflux = pdf['solexs_flux'].values

    flares = []
    for nd in nowcasts:
        # the most recent forecast at/just before this nowcast -> lead time
        prior = [sd for sd in forecasts if sd.timestamp <= nd.timestamp]
        f = prior[-1] if prior else None
        gap = (nd.timestamp - f.timestamp).total_seconds() if f else None
        # Peak class = magnitude from the highest SoLEXS flux around this flare
        # (+/- 30 min), which reflects the real flare size, not the early
        # forecast-time level.
        nt = np.datetime64(pd.Timestamp(nd.timestamp))
        win_mask = (pts >= nt - np.timedelta64(30, 'm')) & (pts <= nt + np.timedelta64(30, 'm'))
        peak_flux = float(np.nanmax(sflux[win_mask])) if win_mask.any() else 0.0
        # Real SoLEXS L1 data is in COUNTS, not GOES W/m^2 flux, so a GOES class
        # is only meaningful once a counts->flux calibration is applied. Report
        # the GOES class only when the value is in plausible flux range; otherwise
        # report the raw peak counts and let HEL1OS sigma indicate strength.
        is_flux = 0 < peak_flux < 1e-2
        flares.append({
            'nowcast_time': pd.Timestamp(nd.timestamp),
            'forecast_time': pd.Timestamp(f.timestamp) if f else None,
            'gap_s': round(gap, 1) if gap is not None else None,
            'peak_class': _flux_to_class(peak_flux) if is_flux else 'n/a (counts)',
            'peak_solexs': round(peak_flux, 1),
            'hel1os_sigma': round(float(nd.sigma_above_baseline), 1),
            'neupert_ok': bool(nd.neupert_consistent),
        })

    # forecasts with no nowcast within the follow-up window -> false alarms
    nowcast_times = [pd.Timestamp(nd.timestamp) for nd in nowcasts]
    forecast_rows = []
    for sd in forecasts:
        ft = pd.Timestamp(sd.timestamp)
        followed = any(0 <= (nt - ft).total_seconds() <= FORECAST_FOLLOWUP_MIN * 60
                       for nt in nowcast_times)
        forecast_rows.append({'forecast_time': ft, 'followed_by_nowcast': followed})

    return {'flares': flares, 'forecasts': forecast_rows}


def _dedup(flares: List[Dict]) -> List[Dict]:
    """Drop flares within DEDUP_MINUTES of an already-kept one (overlap dupes)."""
    kept: List[Dict] = []
    last_time = None
    for fl in sorted(flares, key=lambda x: x['nowcast_time']):
        t = fl['nowcast_time']
        if last_time is not None and (t - last_time).total_seconds() < DEDUP_MINUTES * 60:
            continue
        kept.append(fl)
        last_time = t
    return kept


def scan_dataframe(
    solexs_df: pd.DataFrame,
    hel1os_df: pd.DataFrame,
    chunk_hours: int = DEFAULT_CHUNK_HOURS,
    overlap_hours: int = DEFAULT_OVERLAP_HOURS,
) -> Dict:
    """
    Scan an already-loaded pair of instrument frames in overlapping chunks.
    Useful for testing and for modest in-memory ranges. Returns a result dict
    (see scan_continuous). For huge archives use scan_continuous instead.
    """
    s = solexs_df.copy(); s['timestamp'] = pd.to_datetime(s['timestamp'])
    h = hel1os_df.copy(); h['timestamp'] = pd.to_datetime(h['timestamp'])
    t0 = min(s['timestamp'].min(), h['timestamp'].min())
    t1 = max(s['timestamp'].max(), h['timestamp'].max())

    step = pd.Timedelta(hours=chunk_hours - overlap_hours)
    win = pd.Timedelta(hours=chunk_hours)

    all_flares, all_forecasts = [], []
    n_chunks = 0
    cur = t0
    while cur < t1:
        c0, c1 = cur, cur + win
        s_chunk = s[(s['timestamp'] >= c0) & (s['timestamp'] < c1)]
        h_chunk = h[(h['timestamp'] >= c0) & (h['timestamp'] < c1)]
        out = _detect_in_window(s_chunk, h_chunk)
        all_flares.extend(out['flares'])
        all_forecasts.extend(out['forecasts'])
        n_chunks += 1
        cur = cur + step

    return _summarize(all_flares, all_forecasts, t0, t1, n_chunks)


def scan_continuous(
    start: Union[str, pd.Timestamp],
    end: Union[str, pd.Timestamp],
    data_dir: Optional[Union[str, Path]] = None,
    chunk_hours: int = DEFAULT_CHUNK_HOURS,
    overlap_hours: int = DEFAULT_OVERLAP_HOURS,
    export_csv: bool = True,
) -> Dict:
    """
    Out-of-core scan of [start, end] over the prepared real data. Each chunk is
    loaded on demand from the datastore (Parquet query or manifest-pruned raw
    reads), so peak memory is one chunk regardless of total archive size.

    Parameters
    ----------
    start, end : timestamp-like
        Range to sweep (e.g. '2024-01-01' to today).
    data_dir : str or Path, optional
        Raw folder. Defaults to the active prepared batch.
    chunk_hours, overlap_hours : int
        Chunk window and overlap.
    export_csv : bool
        Write detected flares to outputs/scan_results.csv.
    """
    from core.ingest import load_instrument_window
    from core.datastore import get_active_data_dir
    from config.settings import OUTPUT_DIR

    if data_dir is None:
        active = get_active_data_dir()
        data_dir = str(active) if active else None

    start = pd.Timestamp(start)
    end = pd.Timestamp(end)
    step = pd.Timedelta(hours=chunk_hours - overlap_hours)
    win = pd.Timedelta(hours=chunk_hours)

    logger.info(f"Continuous scan {start.date()} -> {end.date()} "
                f"({chunk_hours}h chunks, {overlap_hours}h overlap)")

    all_flares, all_forecasts = [], []
    n_chunks = 0
    cur = start
    while cur < end:
        c0, c1 = cur, min(cur + win, end)
        try:
            s_chunk = load_instrument_window('solexs', c0, c1, data_dir)
            h_chunk = load_instrument_window('hel1os', c0, c1, data_dir)
            out = _detect_in_window(s_chunk, h_chunk)
            if out['flares']:
                logger.info(f"  {c0.date()}: {len(out['flares'])} flare(s) detected")
            all_flares.extend(out['flares'])
            all_forecasts.extend(out['forecasts'])
        except Exception as e:
            logger.warning(f"  chunk {c0} failed: {e}")
        n_chunks += 1
        cur = cur + step

    result = _summarize(all_flares, all_forecasts, start, end, n_chunks)

    if export_csv:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out_path = OUTPUT_DIR / "scan_results.csv"
        pd.DataFrame(result['flares']).to_csv(out_path, index=False)
        result['csv'] = str(out_path)
        logger.info(f"  Scan results -> {out_path}")

    return result


def _process_chunk_worker(args):
    """Top-level picklable worker for ProcessPoolExecutor parallel scan."""
    import os
    os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
    os.environ.setdefault('OMP_NUM_THREADS', '1')
    os.environ.setdefault('MKL_NUM_THREADS', '1')

    c0_str, c1_str, data_dir = args
    try:
        import warnings, sys
        warnings.filterwarnings('ignore')
        sys.path.insert(0, r'd:\Project\SHIELD\SHIELD')

        import pandas as pd
        import core.datastore as _ds
        from pathlib import Path
        from core.ingest import load_instrument_window
        from core.scan import _detect_in_window

        if data_dir:
            _ds.set_active_data_dir(Path(data_dir))

        c0, c1 = pd.Timestamp(c0_str), pd.Timestamp(c1_str)
        s_chunk = load_instrument_window('solexs', c0, c1, data_dir)
        h_chunk = load_instrument_window('hel1os', c0, c1, data_dir)
        return _detect_in_window(s_chunk, h_chunk)
    except Exception as e:
        return {'flares': [], 'forecasts': [], '_err': str(e)}


def scan_continuous_parallel(
    start: Union[str, pd.Timestamp],
    end: Union[str, pd.Timestamp],
    data_dir: Optional[Union[str, Path]] = None,
    chunk_hours: int = DEFAULT_CHUNK_HOURS,
    overlap_hours: int = DEFAULT_OVERLAP_HOURS,
    export_csv: bool = True,
    workers: int = 6,
) -> Dict:
    """
    Parallel out-of-core scan using ProcessPoolExecutor.
    Same semantics as scan_continuous but distributes chunks across `workers`
    CPU cores — typically 6-8x faster on a 16-core machine.
    """
    from concurrent.futures import ProcessPoolExecutor, as_completed
    from core.datastore import get_active_data_dir
    from config.settings import OUTPUT_DIR

    if data_dir is None:
        active = get_active_data_dir()
        data_dir = str(active) if active else None

    start = pd.Timestamp(start)
    end = pd.Timestamp(end)
    step = pd.Timedelta(hours=chunk_hours - overlap_hours)
    win = pd.Timedelta(hours=chunk_hours)

    chunks = []
    cur = start
    while cur < end:
        c0, c1 = cur, min(cur + win, end)
        chunks.append((str(c0), str(c1), data_dir))
        cur += step

    total = len(chunks)
    print(f"Parallel scan: {total} chunks across {workers} workers", flush=True)

    all_flares: List[Dict] = []
    all_forecasts: List[Dict] = []
    done = 0
    errors = 0

    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_process_chunk_worker, args): args[0] for args in chunks}
        for fut in as_completed(futures):
            done += 1
            try:
                out = fut.result()
                if '_err' in out:
                    errors += 1
                all_flares.extend(out.get('flares', []))
                all_forecasts.extend(out.get('forecasts', []))
            except Exception as e:
                errors += 1
                logger.warning(f"chunk failed: {e}")

            if done % 100 == 0 or done == total:
                pct = done / total * 100
                print(f"  {done}/{total} ({pct:.0f}%) | flares={len(all_flares)} errors={errors}",
                      flush=True)

    result = _summarize(all_flares, all_forecasts, start, end, total)

    if export_csv:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out_path = OUTPUT_DIR / "scan_results.csv"
        pd.DataFrame(result['flares']).to_csv(out_path, index=False)
        result['csv'] = str(out_path)
        print(f"  Results -> {out_path}", flush=True)

    return result


def _summarize(flares, forecasts, t0, t1, n_chunks) -> Dict:
    """Build the final scan summary with de-duplicated flares + false-alarm rate."""
    flares = _dedup(flares)
    days = max((t1 - t0).total_seconds() / 86400.0, 1e-9)

    n_forecasts = len(forecasts)
    # collapse false alarms that fall in the same dedup window
    fa_times = sorted(pd.Timestamp(f['forecast_time']) for f in forecasts
                      if not f['followed_by_nowcast'])
    fa_dedup, last = 0, None
    for t in fa_times:
        if last is None or (t - last).total_seconds() >= DEDUP_MINUTES * 60:
            fa_dedup += 1
            last = t

    gaps = [f['gap_s'] for f in flares if f['gap_s'] is not None]
    summary = {
        'range': [str(t0), str(t1)],
        'days_scanned': round(days, 1),
        'chunks': n_chunks,
        'flares_detected': len(flares),
        'forecasts_issued': n_forecasts,
        'false_alarms': fa_dedup,
        'false_alarms_per_24h': round(fa_dedup / days, 3),
        'mean_gap_s': round(float(np.mean(gaps)), 1) if gaps else None,
        'mean_gap_min': round(float(np.mean(gaps)) / 60.0, 2) if gaps else None,
        'flares': flares,
    }
    logger.info(f"  Scan complete: {len(flares)} flares over {days:.0f} days, "
                f"{summary['false_alarms_per_24h']} false alarms/24h")
    return summary
