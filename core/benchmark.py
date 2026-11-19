# =============================================================================
# S.H.I.E.L.D. — Benchmark & Calibration against the official GOES/SWPC catalog
# This is what turns "we detected 17 flares" into judge-grade credibility:
#
#   1. MATCH our detections to the official NOAA/GOES flare list
#        -> recall (did we catch the real flares?), by class (C / M / X)
#        -> precision / false alarms (did we cry wolf?)
#        -> onset-timing error vs the published peak
#   2. FALSE-ALARM RATE on quiet days (no cataloged flare) — the single most
#      important number for credibility.
#   3. COUNTS -> FLUX CALIBRATION: fit SoLEXS peak counts against the matched
#      GOES peak flux so we can finally report a TRUSTWORTHY B/C/M/X class.
#
# Pure data analysis — no AI. Built to run the moment a long archive + GOES
# catalog are available.
# =============================================================================

import logging
from pathlib import Path
from typing import Optional, Union, List, Dict

import numpy as np
import pandas as pd

from core.impact import class_to_flux

logger = logging.getLogger(__name__)


# =============================================================================
# GOES / SWPC catalog loader (flexible CSV)
# =============================================================================

# Common column-name aliases seen in SWPC / NOAA / HEK flare exports.
_PEAK_ALIASES = ('peak_time', 'peak', 'max_time', 'time_peak', 'event_peaktime',
                 'starttime', 'event_starttime')
_CLASS_ALIASES = ('goes_class', 'class', 'fl_goescls', 'flare_class', 'magnitude')


def load_goes_catalog(path: Union[str, Path]) -> pd.DataFrame:
    """
    Load an official flare list (CSV) into a normalized catalog:
        columns -> ['peak_time' (datetime), 'goes_class' (str), 'flux' (W/m^2)]

    Accepts the usual SWPC/NOAA/HEK column names. Download the GOES event list
    for your date range from SWPC and point this at it.
    """
    df = pd.read_csv(path)
    cols = {c.lower(): c for c in df.columns}

    peak_col = next((cols[a] for a in _PEAK_ALIASES if a in cols), None)
    class_col = next((cols[a] for a in _CLASS_ALIASES if a in cols), None)
    if peak_col is None or class_col is None:
        raise ValueError(
            f"Could not find peak-time/class columns in {list(df.columns)}. "
            f"Expected one of {_PEAK_ALIASES} and {_CLASS_ALIASES}.")

    out = pd.DataFrame({
        'peak_time': pd.to_datetime(df[peak_col], errors='coerce'),
        'goes_class': df[class_col].astype(str).str.strip().str.upper(),
    }).dropna(subset=['peak_time'])
    out['flux'] = out['goes_class'].map(class_to_flux)
    out['letter'] = out['goes_class'].str[0]
    out = out[out['letter'].isin(list('ABCMX'))].sort_values('peak_time').reset_index(drop=True)
    logger.info(f"  Loaded GOES catalog: {len(out)} flares "
                f"({out['letter'].value_counts().to_dict()})")
    return out


# =============================================================================
# Match detections <-> catalog
# =============================================================================

def match_to_catalog(
    detections: pd.DataFrame,
    catalog: pd.DataFrame,
    tol_min: float = 30.0,
    det_time_col: str = 'nowcast_time',
) -> Dict[str, pd.DataFrame]:
    """
    Greedy nearest-time matching between our detections and the GOES catalog.

    Returns dict of DataFrames:
        'matched'      : detection paired with its catalog flare (+ timing error)
        'missed'       : catalog flares we did NOT detect (false negatives)
        'false_alarms' : detections with no catalog flare nearby (false positives)
    """
    det = detections.copy()
    det[det_time_col] = pd.to_datetime(det[det_time_col])
    cat = catalog.copy()
    cat['peak_time'] = pd.to_datetime(cat['peak_time'])
    tol = pd.Timedelta(minutes=tol_min)

    used_cat = set()
    matched_rows, fa_rows = [], []
    for _, d in det.iterrows():
        dt = d[det_time_col]
        # nearest unused catalog flare within tolerance
        cand = cat[~cat.index.isin(used_cat)]
        if len(cand):
            diffs = (cand['peak_time'] - dt).abs()
            j = diffs.idxmin()
            if diffs.loc[j] <= tol:
                used_cat.add(j)
                matched_rows.append({
                    **d.to_dict(),
                    'goes_class': cat.loc[j, 'goes_class'],
                    'goes_letter': cat.loc[j, 'letter'],
                    'goes_flux': cat.loc[j, 'flux'],
                    'goes_peak_time': cat.loc[j, 'peak_time'],
                    'timing_error_s': (dt - cat.loc[j, 'peak_time']).total_seconds(),
                })
                continue
        fa_rows.append(d.to_dict())

    missed = cat[~cat.index.isin(used_cat)]
    return {
        'matched': pd.DataFrame(matched_rows),
        'missed': missed.reset_index(drop=True),
        'false_alarms': pd.DataFrame(fa_rows),
    }


# =============================================================================
# Benchmark report
# =============================================================================

def benchmark_report(
    detections: pd.DataFrame,
    catalog: pd.DataFrame,
    total_days: float,
    quiet_days: Optional[float] = None,
    tol_min: float = 30.0,
) -> Dict:
    """
    Full credibility report: recall overall + per class, precision, false-alarm
    rate (per 24h, ideally measured over quiet_days), and onset-timing stats.
    """
    m = match_to_catalog(detections, catalog, tol_min=tol_min)
    matched, missed, fa = m['matched'], m['missed'], m['false_alarms']

    n_cat = len(catalog)
    n_det = len(detections)
    n_match = len(matched)

    # Recall per class letter.
    recall_by_class = {}
    for letter in ('C', 'M', 'X'):
        total = int((catalog['letter'] == letter).sum())
        if total == 0:
            continue
        got = int((matched['goes_letter'] == letter).sum()) if len(matched) else 0
        recall_by_class[letter] = {'caught': got, 'total': total,
                                   'recall': round(got / total, 3)}

    fa_basis_days = quiet_days if quiet_days else total_days
    report = {
        'catalog_flares': n_cat,
        'detections': n_det,
        'matched': n_match,
        'recall_overall': round(n_match / n_cat, 3) if n_cat else None,
        'recall_by_class': recall_by_class,
        'precision': round(n_match / n_det, 3) if n_det else None,
        'false_alarms': int(len(fa)),
        'false_alarms_per_24h': round(len(fa) / fa_basis_days, 3) if fa_basis_days else None,
        'far_basis': 'quiet_days' if quiet_days else 'all_days',
        'timing_error_s': {
            'mean': round(float(matched['timing_error_s'].mean()), 1) if n_match else None,
            'median': round(float(matched['timing_error_s'].median()), 1) if n_match else None,
            'std': round(float(matched['timing_error_s'].std()), 1) if n_match > 1 else None,
        },
    }
    return report


# =============================================================================
# Counts -> flux calibration  (trustworthy B/C/M/X at last)
# =============================================================================

def calibrate_counts_to_flux(
    matched: pd.DataFrame,
    counts_col: str = 'peak_solexs',
) -> Dict:
    """
    Fit log10(GOES flux) = a * log10(SoLEXS peak counts) + b on matched flares.
    Returns the fit (a, b), R^2, and a `to_flux(counts)` / `to_class(counts)`
    so the rest of the system can report real GOES classes from SoLEXS counts.
    """
    d = matched.dropna(subset=[counts_col, 'goes_flux'])
    d = d[(d[counts_col] > 0) & (d['goes_flux'] > 0)]
    if len(d) < 3:
        return {'ok': False, 'reason': f'need >=3 matched flares, have {len(d)}'}

    x = np.log10(d[counts_col].to_numpy())
    y = np.log10(d['goes_flux'].to_numpy())
    a, b = np.polyfit(x, y, 1)
    yhat = a * x + b
    ss_res = float(np.sum((y - yhat) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

    def to_flux(counts: float) -> float:
        return float(10 ** (a * np.log10(max(counts, 1e-9)) + b))

    from core.physics_engine import _flux_to_class
    return {
        'ok': True, 'a': round(float(a), 4), 'b': round(float(b), 4),
        'r2': round(float(r2), 3), 'n': int(len(d)),
        'to_flux': to_flux,
        'to_class': lambda c: _flux_to_class(to_flux(c)),
    }
