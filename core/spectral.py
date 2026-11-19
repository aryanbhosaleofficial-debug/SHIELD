# =============================================================================
# S.H.I.E.L.D. — Spectral Feature Extractor (SoLEXS .pi + HEL1OS band lightcurves)
# Goes beyond the single-band lightcurve to extract the full physics feature set
# from the RICH data already inside the PRADAN zips:
#
#   SoLEXS .pi  : time-resolved spectra (1 spectrum/sec, 340 energy channels)
#                 -> per-second energy sub-band count rates
#                 -> plasma TEMPERATURE (filter/band-ratio method, GOES-style)
#                 -> EMISSION-MEASURE proxy
#   HEL1OS LC   : per-detector (CZT1/2, CdTe1/2) lightcurves ALREADY split into
#                 energy sub-bands (e.g. 20-40, 40-60, 60-80, 80-150 keV)
#                 -> per-detector / per-band count rate
#                 -> SPECTRAL INDEX (power-law slope across the hard bands)
#
# HONESTY:
#   * SoLEXS L1 .pi carries no response matrix (no EBOUNDS), so channel->keV uses
#     an approximate linear gain and TEMPERATURE is a band-RATIO estimate (the
#     same principle GOES uses), not a full XSPEC fit. Clearly labelled "est".
#   * EMISSION MEASURE is a proxy (∝ soft thermal counts), labelled "proxy".
#   * Dead-time correction needs the DEADC/hk telemetry; CTR here is the L1 count
#     rate as delivered. Flagged where relevant.
# =============================================================================

import io
import re
import gzip
import zipfile
import logging
from pathlib import Path
from typing import Optional, Union, List, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# --- SoLEXS approximate energy calibration (no EBOUNDS in L1 .pi) -------------
# 340 channels span ~0-30 keV (active signal sits in the 2-22 keV science band).
SOLEXS_GAIN_KEV_PER_CH = 30.0 / 340.0          # ~0.088 keV/channel
SOLEXS_BANDS_KEV = {                            # standard soft-X sub-bands
    'soft': (2.0, 6.0),
    'mid':  (6.0, 12.0),
    'hard': (12.0, 22.0),
}
# Representative band energies for the temperature ratio (geometric centres).
_E_SOFT, _E_MID = 4.0, 9.0

_BAND_RE = re.compile(r'BAND_([\d.]+)KEV_TO_([\d.]+)KEV', re.I)
_HLS_DETS = ('czt1', 'czt2', 'cdte1', 'cdte2')

# HEL1OS dead-time per detected event. The L1 product carries no DEADC keyword,
# so this is a representative CZT/CdTe value (~few microseconds); it only matters
# at the very high count rates near saturation. Documented assumption — refine
# if ISRO publishes the exact DEADC / live-time telemetry.
HEL1OS_DEADTIME_S = 5e-6


def deadtime_correct(rate: np.ndarray, tau: float = HEL1OS_DEADTIME_S
                     ) -> Tuple[np.ndarray, np.ndarray]:
    """
    Non-paralyzable dead-time correction:

        true_rate = observed_rate / (1 - observed_rate * tau)

    Returns (corrected_rate, correction_factor). The factor grows >1 only when
    the detector is near saturation (very high observed rate), which is exactly
    where the raw count rate under-reports the true flux.
    """
    r = np.asarray(rate, dtype=float)
    busy = np.clip(r * tau, 0.0, 0.95)        # fraction of time detector is busy
    factor = 1.0 / (1.0 - busy)
    return r * factor, factor


# =============================================================================
# SoLEXS — time-resolved spectra -> sub-bands + temperature + emission measure
# =============================================================================

def _ch_for_kev(e0: float, e1: float) -> Tuple[int, int]:
    return (max(0, int(e0 / SOLEXS_GAIN_KEV_PER_CH)),
            int(e1 / SOLEXS_GAIN_KEV_PER_CH))


def read_solexs_spectra(zip_path: Union[str, Path]) -> Optional[pd.DataFrame]:
    """
    Read one SoLEXS day-zip's time-resolved .pi spectra into per-second band
    count rates. Returns df[timestamp, slx_total, slx_soft, slx_mid, slx_hard]
    or None if no .pi present.
    """
    from astropy.io import fits
    zf = zipfile.ZipFile(zip_path)
    pin = [n for n in zf.namelist() if n.endswith('.pi.gz') or n.endswith('.pi')]
    if not pin:
        return None
    raw = zf.read(pin[0])
    if pin[0].endswith('.gz'):
        raw = gzip.decompress(raw)
    with fits.open(io.BytesIO(raw)) as hdul:
        spec = hdul['SPECTRUM'].data
        tstart = np.asarray(spec['TSTART'], dtype='f8')
        counts = np.nan_to_num(np.asarray(spec['COUNTS'], dtype='f8'))  # (N, 340)

    out = {'timestamp': pd.to_datetime(tstart, unit='s'),
           'slx_total': counts.sum(axis=1)}
    for name, (e0, e1) in SOLEXS_BANDS_KEV.items():
        c0, c1 = _ch_for_kev(e0, e1)
        out[f'slx_{name}'] = counts[:, c0:c1].sum(axis=1)
    return pd.DataFrame(out)


def solexs_temperature_em(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add estimated plasma temperature and emission-measure proxy from the SoLEXS
    sub-bands using the filter/band-ratio method:

        C_band ~ exp(-E/kT)  =>  kT_est = (E_mid - E_soft) / ln(C_soft / C_mid)

    Temperature rises when the spectrum hardens (mid/soft ratio grows) — this is
    the physically-grounded heating signal. Emission measure is proxied by the
    soft thermal counts.
    """
    soft = df['slx_soft'].clip(lower=1.0).to_numpy()
    mid = df['slx_mid'].clip(lower=1.0).to_numpy()
    with np.errstate(divide='ignore', invalid='ignore'):
        denom = np.log(soft / mid)
        kt = np.where(denom > 1e-6, (_E_MID - _E_SOFT) / denom, np.nan)
    # Physical clamp: 1-50 MK (~0.1-4.3 keV is typical flare soft-X plasma)
    df['slx_kt_keV_est'] = np.clip(kt, 0.0, 8.0)
    df['slx_em_proxy'] = df['slx_soft']  # ∝ thermal emission measure
    return df


# =============================================================================
# HEL1OS — per-detector, per-sub-band lightcurves -> bands + spectral index
# =============================================================================

def read_hel1os_bands(zip_path: Union[str, Path]) -> Optional[pd.DataFrame]:
    """
    Read one HEL1OS zip's per-detector band lightcurves. Returns a per-second
    DataFrame with one column per (detector, band) count rate, e.g.
    'czt1_20-40', plus 'hls_total'. Bands are parsed from each HDU's name.
    """
    from astropy.io import fits
    zf = zipfile.ZipFile(zip_path)
    frames: List[pd.DataFrame] = []

    for m in zf.namelist():
        fn = m.split('/')[-1].lower()
        det = next((d for d in _HLS_DETS if fn == f'lightcurve_{d}.fits'), None)
        if det is None:
            continue
        with fits.open(io.BytesIO(zf.read(m))) as hdul:
            for hd in hdul[1:]:
                mobj = _BAND_RE.search(hd.name or '')
                if mobj is None or hd.data is None or 'CTR' not in hd.data.names:
                    continue
                e0, e1 = float(mobj.group(1)), float(mobj.group(2))
                ts = pd.to_datetime(np.asarray(hd.data['ISOT']), errors='coerce')
                ctr = np.asarray(hd.data['CTR'], dtype='f8')
                col = f'{det}_{e0:.0f}-{e1:.0f}'
                frames.append(pd.DataFrame({'timestamp': ts, col: ctr})
                              .dropna(subset=['timestamp']))

    if not frames:
        return None

    # Merge all (detector, band) series on the 1-second timeline.
    merged = frames[0]
    for f in frames[1:]:
        merged = merged.merge(f, on='timestamp', how='outer')
    merged = merged.sort_values('timestamp').reset_index(drop=True)

    # Total hard-X flux: prefer each detector's full-band column (e.g. 18-160),
    # else sum the narrow bands.
    full_cols = [c for c in merged.columns if c.endswith('-160') or c.endswith('-150')]
    band_cols = [c for c in merged.columns if c != 'timestamp']
    merged['hls_total'] = (merged[full_cols].sum(axis=1) if full_cols
                           else merged[band_cols].sum(axis=1))
    return merged


# CZT science sub-bands and their representative (geometric-centre) energies.
_CZT_BANDS = [('20-40', 28.3), ('40-60', 49.0), ('60-80', 69.3), ('80-150', 109.5)]


def hel1os_spectral_index(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add the non-thermal power-law SPECTRAL INDEX (gamma) from the slope of
    log(count-rate) vs log(energy) across the CZT hard sub-bands, summed over
    both CZT detectors. Harder (flatter) spectra -> smaller gamma -> more
    energetic electrons. NaN when there is too little hard-X signal to fit.
    """
    energies, series = [], []
    for band, e_rep in _CZT_BANDS:
        cols = [c for c in df.columns if c.endswith(band) and c.startswith('czt')]
        if not cols:
            continue
        energies.append(e_rep)
        series.append(df[cols].sum(axis=1).to_numpy())
    if len(series) < 2:
        df['hls_spectral_index'] = np.nan
        return df

    E = np.log(np.array(energies))                      # (B,)
    C = np.vstack(series).T.astype(float)               # (N, B) count rates
    # Power-law fit per row: log C = -gamma*log E + b  =>  slope via least squares.
    mask = C > 0
    logC = np.where(mask, np.log(np.clip(C, 1e-9, None)), np.nan)
    # Need >=2 valid bands per row.
    valid = mask.sum(axis=1) >= 2

    gamma = np.full(len(df), np.nan)
    # Per-row power-law slope using only finite bands (event windows are short,
    # so this loop stays cheap).
    idx = np.where(valid)[0]
    for i in idx:
        row = logC[i]
        fin = np.isfinite(row)
        if fin.sum() < 2:
            continue
        e = E[fin] - E[fin].mean()
        c = row[fin] - row[fin].mean()
        denom = np.sum(e * e)
        if denom > 0:
            gamma[i] = -np.sum(e * c) / denom            # negative slope = gamma
    df['hls_spectral_index'] = gamma
    return df


# =============================================================================
# WINDOW EXTRACTOR — fuse SoLEXS + HEL1OS, derivatives, cross-instrument features
# =============================================================================

def _zip_paths(instrument: str, start, end, data_dir) -> List[Path]:
    """Unique raw zip paths overlapping the window for one instrument."""
    from core.datastore import select_files
    targets = select_files(instrument, pd.Timestamp(start), pd.Timestamp(end), data_dir)
    seen, out = set(), []
    for p, _member in targets:
        if p not in seen and str(p).lower().endswith('.zip'):
            seen.add(p)
            out.append(Path(p))
    return out


def _read_concat(reader, paths, start, end) -> Optional[pd.DataFrame]:
    frames = []
    for p in paths:
        try:
            d = reader(p)
        except Exception as e:
            logger.warning(f"  spectral read failed {Path(p).name}: {e}")
            continue
        if d is not None and not d.empty:
            frames.append(d)
    if not frames:
        return None
    df = pd.concat(frames, ignore_index=True)
    # Force a common nanosecond resolution (SoLEXS .pi parses to [s], HEL1OS
    # ISOT strings to [us]); merge_asof requires identical datetime dtypes.
    df['timestamp'] = pd.to_datetime(df['timestamp']).astype('datetime64[ns]')
    df = df[(df['timestamp'] >= pd.Timestamp(start)) & (df['timestamp'] <= pd.Timestamp(end))]
    return (df.dropna(subset=['timestamp']).drop_duplicates('timestamp')
              .sort_values('timestamp').reset_index(drop=True))


def _roll_baseline(x: pd.Series, win_s: int = 600) -> pd.Series:
    """Quiet-Sun rolling baseline (median is robust to flare spikes)."""
    return x.rolling(win_s, min_periods=max(10, win_s // 10), center=False).median()


def extract_event_features(
    start: Union[str, pd.Timestamp],
    end: Union[str, pd.Timestamp],
    data_dir: Optional[Union[str, Path]] = None,
) -> Tuple[pd.DataFrame, dict]:
    """
    Build the full per-second spectral feature frame for [start, end] and a
    per-event summary dict. Reads only the window's files (manifest pruning).

    Per-second columns include:
      SoLEXS  : slx_total/soft/mid/hard, slx_bgsub, slx_dF, slx_d2F,
                slx_kt_keV_est, slx_em_proxy
      HEL1OS  : per (det,band) CTR, hls_total, hls_bgsub, hls_spectral_index
      Fused   : hardness_ratio, neupert_resid, joint_sigma
    """
    start, end = pd.Timestamp(start), pd.Timestamp(end)

    slx = _read_concat(read_solexs_spectra, _zip_paths('solexs', start, end, data_dir), start, end)
    hls = _read_concat(read_hel1os_bands, _zip_paths('hel1os', start, end, data_dir), start, end)
    if slx is None or hls is None:
        logger.warning("  spectral: missing SoLEXS or HEL1OS data in window")
        return pd.DataFrame(), {}

    slx = solexs_temperature_em(slx)
    hls = hel1os_spectral_index(hls)

    # Merge to a common 1-second timeline (asof to tolerate sub-second offsets).
    df = pd.merge_asof(slx.sort_values('timestamp'), hls.sort_values('timestamp'),
                       on='timestamp', direction='nearest',
                       tolerance=pd.Timedelta('1s'))

    # Dead-time correction for HEL1OS (important near saturation): recover the
    # true hard-X count rate the detector under-reports when it is very busy.
    corr, factor = deadtime_correct(df['hls_total'].to_numpy())
    df['hls_total_dtcorr'] = corr
    df['hls_deadtime_factor'] = factor
    df['hls_saturated'] = factor > 1.10          # >10% lost -> flag saturation

    # Background subtraction (rolling quiet-Sun median).
    df['slx_bgsub'] = (df['slx_total'] - _roll_baseline(df['slx_total'])).clip(lower=0)
    df['hls_bgsub'] = (df['hls_total'] - _roll_baseline(df['hls_total'])).clip(lower=0)

    # SoLEXS derivatives (rise rate + curvature).
    s = df['slx_total'].rolling(5, min_periods=1, center=True).mean()
    df['slx_dF'] = np.gradient(s.to_numpy())
    df['slx_d2F'] = np.gradient(df['slx_dF'].to_numpy())

    # --- Cross-instrument fused features ---
    df['hardness_ratio'] = df['hls_total'] / df['slx_total'].clip(lower=1.0)
    # Neupert residual: HEL1OS hard-X flux should track d/dt(SoLEXS). Residual is
    # the normalised difference of the two (z-scored) — small = physically consistent.
    a = _z(df['hls_total']); b = _z(df['slx_dF'])
    df['neupert_resid'] = (a - b)
    # Joint significance: min of the two instruments' sigma-above-baseline, so an
    # event only scores high when BOTH light up (kills single-instrument noise).
    df['slx_sigma'] = _sigma(df['slx_total'])
    df['hls_sigma'] = _sigma(df['hls_total'])
    df['joint_sigma'] = np.minimum(df['slx_sigma'], df['hls_sigma'])

    summary = _event_summary(df, start, end)
    return df, summary


def _z(x: pd.Series) -> np.ndarray:
    v = x.to_numpy(dtype=float)
    sd = np.nanstd(v)
    return (v - np.nanmean(v)) / sd if sd > 0 else np.zeros_like(v)


def _sigma(x: pd.Series, win_s: int = 600) -> np.ndarray:
    """Sigma above a rolling baseline (robust)."""
    base = x.rolling(win_s, min_periods=max(10, win_s // 10), center=False).median()
    std = x.rolling(win_s, min_periods=max(10, win_s // 10), center=False).std().clip(lower=1e-6)
    return ((x - base) / std).fillna(0).to_numpy()


def _event_summary(df: pd.DataFrame, start, end) -> dict:
    """Per-event peak/timing + cross-correlation lag between HEL1OS and SoLEXS."""
    if df.empty:
        return {}
    t = df['timestamp']
    slx = df['slx_total'].to_numpy()
    hls = df['hls_total'].to_numpy()
    peak_i = int(np.nanargmax(slx))
    t_peak = t.iloc[peak_i]
    # Spectral index sampled at the hard-X peak (where the fit is best-constrained),
    # which is far more meaningful than the noisy per-second min.
    hls_peak_i = int(np.nanargmax(hls)) if np.isfinite(hls).any() else peak_i
    si = df['hls_spectral_index'].to_numpy()
    si_at_peak = float(si[hls_peak_i]) if np.isfinite(si[hls_peak_i]) else float(np.nanmedian(si))

    # decay time: peak -> back to half peak
    half = slx[peak_i] * 0.5
    decay_s = None
    for j in range(peak_i, len(slx)):
        if slx[j] < half:
            decay_s = (t.iloc[j] - t_peak).total_seconds()
            break

    # Cross-correlation lag: shift HEL1OS vs SoLEXS-derivative to max correlation.
    lag_s = _xcorr_lag(df['slx_dF'].to_numpy(), hls, max_lag=180)

    return {
        'window': [str(start), str(end)],
        'slx_peak_total': float(np.nanmax(slx)),
        'slx_peak_time': str(t_peak),
        'slx_peak_kt_keV_est': float(np.nanmax(df['slx_kt_keV_est'].to_numpy())),
        'hls_peak_total': float(np.nanmax(hls)),
        'hls_peak_sigma': float(np.nanmax(df['hls_sigma'].to_numpy())),
        'hls_spectral_index_at_peak': si_at_peak,
        'decay_to_half_s': decay_s,
        'xcorr_lag_hls_vs_dslx_s': lag_s,
        'peak_hardness_ratio': float(np.nanmax(df['hardness_ratio'].to_numpy())),
        'peak_joint_sigma': float(np.nanmax(df['joint_sigma'].to_numpy())),
        'peak_deadtime_factor': float(np.nanmax(df['hls_deadtime_factor'].to_numpy())),
        'saturated': bool(df['hls_saturated'].any()),
    }


def extract_flares_spectral(
    event_id: str,
    data_dir: Optional[Union[str, Path]] = None,
    pad_min: int = 30,
    flare_times: Optional[List[Union[str, pd.Timestamp]]] = None,
    out_dir: Optional[Union[str, Path]] = None,
) -> dict:
    """
    Pipeline step: extract the full spectral feature table around EACH flare in
    an event, and save it as the shareable "proper" filtered data.

    Strategy (out-of-core safe): detect flares cheaply on the single-band
    lightcurves first (core.scan), THEN read the heavy per-second spectra only in
    a +/- pad_min window around each flare — never the whole multi-day archive.

    Parameters
    ----------
    event_id : str
        Catalog event id (defines the search window).
    data_dir : str or Path, optional
        Raw folder (defaults to the active prepared batch).
    pad_min : int
        Minutes of context to extract on each side of a flare.
    flare_times : list, optional
        Skip detection and use these flare times directly (faster).
    out_dir : str or Path, optional
        Where to write the feature CSVs (default outputs/spectral/<EVENT>/).

    Returns a summary dict with one entry per flare (+ the written file paths).
    """
    from config.flare_catalog import get_event_by_id
    from config.settings import OUTPUT_DIR

    ev = get_event_by_id(event_id)
    if ev is None:
        raise ValueError(f"Unknown event '{event_id}'")

    # 1) Get flare times (detect if not supplied).
    if flare_times is None:
        from core.scan import scan_continuous
        scan = scan_continuous(ev.window_start, ev.window_end,
                               data_dir=data_dir, export_csv=False)
        flare_times = [f['nowcast_time'] for f in scan['flares']]
        logger.info(f"  {event_id}: detected {len(flare_times)} flare(s) to extract")

    out_dir = Path(out_dir) if out_dir else (OUTPUT_DIR / "spectral" / event_id)
    out_dir.mkdir(parents=True, exist_ok=True)

    pad = pd.Timedelta(minutes=pad_min)
    flares_out, files = [], []
    for t in sorted(pd.Timestamp(x) for x in flare_times):
        df, summ = extract_event_features(t - pad, t + pad, data_dir)
        if df.empty:
            continue
        tag = pd.Timestamp(t).strftime('%Y%m%d_%H%M%S')
        fpath = out_dir / f"{event_id}_flare_{tag}_features.csv"
        df.to_csv(fpath, index=False)
        files.append(str(fpath))
        summ['flare_time'] = str(t)
        flares_out.append(summ)
        logger.info(f"  spectral features -> {fpath.name} "
                    f"({len(df)} rows, peak kT~{summ.get('slx_peak_kt_keV_est', float('nan')):.1f} keV)")

    import json
    summary = {'event_id': event_id, 'n_flares': len(flares_out), 'flares': flares_out,
               'files': files}
    (out_dir / f"{event_id}_spectral_summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def compute_tier0_history(flares: List[dict]) -> List[dict]:
    """
    Tier-0 (24h) context features, derived from the accumulated flare history
    (not the raw time series). For each flare, looking only at flares BEFORE it:

      flare_count_24h / 48h       - activity level
      time_since_last_flare_h     - quiescence before this one
      energy_proxy_24h            - summed peak soft counts in the last 24h
      hardness_trend              - slope of peak hardness over recent flares

    `flares` is the list of per-flare summary dicts (each with 'flare_time',
    'slx_peak_total', 'peak_hardness_ratio', 'hls_peak_sigma').
    """
    rows = sorted(flares, key=lambda f: pd.Timestamp(f['flare_time']))
    out = []
    for i, f in enumerate(rows):
        t = pd.Timestamp(f['flare_time'])
        prior = rows[:i]
        last24 = [p for p in prior if (t - pd.Timestamp(p['flare_time'])) <= pd.Timedelta(hours=24)]
        last48 = [p for p in prior if (t - pd.Timestamp(p['flare_time'])) <= pd.Timedelta(hours=48)]
        since = ((t - pd.Timestamp(prior[-1]['flare_time'])).total_seconds() / 3600.0
                 if prior else None)
        energy24 = float(sum(p.get('slx_peak_total', 0.0) for p in last24))
        # hardness trend: slope of peak hardness across the last up-to-5 flares
        recent = (prior + [f])[-5:]
        hard = [p.get('peak_hardness_ratio', 0.0) for p in recent]
        trend = float(np.polyfit(range(len(hard)), hard, 1)[0]) if len(hard) >= 2 else 0.0
        tier0 = {
            'flare_count_24h': len(last24),
            'flare_count_48h': len(last48),
            'time_since_last_flare_h': round(since, 2) if since is not None else None,
            'energy_proxy_24h': round(energy24, 1),
            'hardness_trend': round(trend, 4),
        }
        out.append({**f, 'tier0': tier0})
    return out


def run_full_extraction(
    event_ids: List[str],
    data_dir: Optional[Union[str, Path]] = None,
    flare_times_map: Optional[dict] = None,
    pad_min: int = 20,
    copy_to_filtered: bool = True,
) -> dict:
    """
    PIPELINE ENTRY: for each event, detect flares then extract the full spectral
    feature table around each, add Tier-0 24h history, and (optionally) copy the
    feature CSVs into data/processed/filtered_csv/ as the shareable "proper"
    filtered data. Writes outputs/spectral/<EVENT>/ and a combined summary.

    Parameters
    ----------
    event_ids : list of str
    data_dir : raw folder (defaults to active batch)
    flare_times_map : {event_id: [times]} to skip detection (faster), else scans
    pad_min : context window per flare (minutes)
    copy_to_filtered : also drop the feature CSVs into filtered_csv/ for sharing
    """
    import json
    import shutil
    from config.settings import OUTPUT_DIR
    from core.datastore import FILTERED_CSV_DIR

    flare_times_map = flare_times_map or {}
    all_out = {}
    for ev in event_ids:
        ft = flare_times_map.get(ev)
        summ = extract_flares_spectral(ev, data_dir=data_dir, pad_min=pad_min,
                                       flare_times=ft)
        summ['flares'] = compute_tier0_history(summ['flares']) if summ['flares'] else []
        all_out[ev] = summ

        if copy_to_filtered:
            FILTERED_CSV_DIR.mkdir(parents=True, exist_ok=True)
            for fp in summ.get('files', []):
                try:
                    shutil.copy2(fp, FILTERED_CSV_DIR / Path(fp).name)
                except Exception as e:
                    logger.warning(f"  copy to filtered_csv failed: {e}")

    combined = OUTPUT_DIR / "spectral" / "ALL_events_spectral_summary.json"
    combined.parent.mkdir(parents=True, exist_ok=True)
    combined.write_text(json.dumps(
        {ev: {'n_flares': s['n_flares'], 'flares': s['flares']} for ev, s in all_out.items()},
        indent=2, default=str))
    logger.info(f"  Full extraction done: "
                f"{sum(s['n_flares'] for s in all_out.values())} flares -> {combined}")
    return all_out


def _xcorr_lag(a: np.ndarray, b: np.ndarray, max_lag: int = 180) -> Optional[float]:
    """Lag (seconds) of b relative to a that maximises correlation; +ve = b later."""
    a = np.nan_to_num(a); b = np.nan_to_num(b)
    if np.std(a) == 0 or np.std(b) == 0:
        return None
    a = (a - a.mean()) / a.std()
    b = (b - b.mean()) / b.std()
    best_lag, best = 0, -np.inf
    for lag in range(-max_lag, max_lag + 1):
        if lag < 0:
            c = np.corrcoef(a[-lag:], b[:lag])[0, 1] if len(a) + lag > 10 else np.nan
        elif lag > 0:
            c = np.corrcoef(a[:-lag], b[lag:])[0, 1] if len(a) - lag > 10 else np.nan
        else:
            c = np.corrcoef(a, b)[0, 1]
        if np.isfinite(c) and c > best:
            best, best_lag = c, lag
    return float(best_lag)
