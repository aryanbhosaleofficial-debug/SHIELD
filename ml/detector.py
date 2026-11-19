# =============================================================================
# S.H.I.E.L.D. — ML Flare Detector (catches the C/M flares the hard-X physics
# detector misses). Trained on SoLEXS SOFT X-ray (the band that defines GOES
# classes), labelled against the official GOES catalog.
#
# Approach: slide a window over the soft-X-ray light curve; for each window
# compute simple shape features; label = a GOES flare peaks in the window.
# Train XGBoost; evaluate on a HELD-OUT time period (chronological, no leakage)
# and report recall BY CLASS so we can compare to the physics detector
# (which got X 55% / M 10% / C 0.1%).
# =============================================================================

import logging
from pathlib import Path
from typing import Union, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

WIN_MIN = 6          # window length (minutes)
STEP_MIN = 3         # window step
BASE_MIN = 30        # rolling quiet-Sun baseline (minutes)

FEATURES = ['peak', 'peak_over_base', 'rise', 'mean', 'std',
            'd1_max', 'd2_max', 'frac_rise']


def _day_windows(flux: pd.Series, t: pd.Series) -> pd.DataFrame:
    """Compute per-window soft-X-ray shape features for one day (1s cadence)."""
    f = flux.to_numpy(dtype=float)
    n = len(f)
    if n < WIN_MIN * 60:
        return pd.DataFrame()
    base = pd.Series(f).rolling(BASE_MIN * 60, min_periods=60, center=False).median().to_numpy()
    base = np.where(np.isfinite(base) & (base > 0), base, np.nanmedian(f) or 1.0)
    sm = pd.Series(f).rolling(5, min_periods=1, center=True).mean().to_numpy()
    d1 = np.gradient(sm)
    d2 = np.gradient(d1)

    w, s = WIN_MIN * 60, STEP_MIN * 60
    rows = []
    for i in range(0, n - w, s):
        seg = f[i:i+w]; b = np.nanmedian(base[i:i+w]) or 1.0
        rows.append({
            'win_start': t.iloc[i], 'win_end': t.iloc[i+w-1],
            'peak': float(np.nanmax(seg)),
            'peak_over_base': float(np.nanmax(seg) / b),
            'rise': float(np.nanmax(seg) - np.nanmin(seg)),
            'mean': float(np.nanmean(seg)),
            'std': float(np.nanstd(seg)),
            'd1_max': float(np.nanmax(d1[i:i+w])),
            'd2_max': float(np.nanmax(d2[i:i+w])),
            'frac_rise': float((np.nanmax(seg) - np.nanmin(seg)) / b),
        })
    return pd.DataFrame(rows)


def build_detection_dataset(
    catalog_csv: Union[str, Path],
    start: str, end: str,
    data_dir: Optional[str] = None,
    out_csv: Optional[Union[str, Path]] = None,
) -> pd.DataFrame:
    """
    Build the windowed soft-X-ray training table over [start, end], one day at a
    time (bounded memory). Each window labelled with whether a GOES flare peaks
    in it (+ that flare's class letter).
    """
    from core.ingest import load_instrument_window
    cat = pd.read_csv(catalog_csv); cat['peak_time'] = pd.to_datetime(cat['peak_time'])

    days = pd.date_range(pd.Timestamp(start), pd.Timestamp(end), freq='D')
    all_rows = []
    for d in days:
        d0, d1 = d, d + pd.Timedelta(days=1)
        try:
            sol = load_instrument_window('solexs', d0, d1, data_dir)
        except Exception:
            continue
        if sol is None or sol.empty or 'flux' not in sol.columns:
            continue
        sol = sol.dropna(subset=['timestamp']).sort_values('timestamp')
        wins = _day_windows(sol['flux'], sol['timestamp'].reset_index(drop=True))
        if wins.empty:
            continue
        # label windows by catalog flares that day
        day_fl = cat[(cat['peak_time'] >= d0) & (cat['peak_time'] < d1)]
        wins['y'] = 0; wins['class'] = ''
        for _, fl in day_fl.iterrows():
            hit = (wins['win_start'] <= fl['peak_time']) & (wins['win_end'] >= fl['peak_time'])
            wins.loc[hit, 'y'] = 1
            wins.loc[hit, 'class'] = fl['letter']
        all_rows.append(wins)
        if len(all_rows) % 30 == 0:
            logger.info(f"  detector dataset: processed {len(all_rows)} days")

    if not all_rows:
        return pd.DataFrame()
    ds = pd.concat(all_rows, ignore_index=True)
    if out_csv:
        ds.to_csv(out_csv, index=False)
    return ds


def train_detector(dataset: pd.DataFrame, train_frac: float = 0.7) -> dict:
    """Train XGBoost flare detector on the windowed dataset; chronological split."""
    from xgboost import XGBClassifier
    from sklearn.metrics import roc_auc_score, precision_score, recall_score

    ds = dataset.dropna(subset=FEATURES).sort_values('win_start').reset_index(drop=True)
    split = int(len(ds) * train_frac)
    tr, te = ds.iloc[:split], ds.iloc[split:]
    Xtr, ytr = tr[FEATURES], tr['y']
    Xte, yte = te[FEATURES], te['y']

    # class imbalance: flares are rare windows -> weight positives
    pos = max(int(ytr.sum()), 1); neg = max(int((ytr == 0).sum()), 1)
    model = XGBClassifier(n_estimators=300, max_depth=4, learning_rate=0.05,
                          subsample=0.8, eval_metric='logloss', random_state=42,
                          scale_pos_weight=neg / pos)
    model.fit(Xtr, ytr)
    p = model.predict_proba(Xte)[:, 1]
    pred = (p >= 0.5).astype(int)

    # recall by GOES class on the test period (did we catch C/M/X flares?)
    te = te.copy(); te['pred'] = pred
    recall_by_class = {}
    for L in ('C', 'M', 'X'):
        sub = te[te['class'] == L]
        if len(sub):
            recall_by_class[L] = {'caught': int(sub['pred'].sum()), 'total': int(len(sub)),
                                  'recall': round(float(sub['pred'].mean()), 3)}
    return {
        'model': model, 'n_train': len(tr), 'n_test': len(te),
        'n_flare_windows_test': int(yte.sum()),
        'roc_auc': round(float(roc_auc_score(yte, p)), 3) if yte.nunique() > 1 else None,
        'precision': round(float(precision_score(yte, pred, zero_division=0)), 3),
        'recall': round(float(recall_score(yte, pred, zero_division=0)), 3),
        'recall_by_class': recall_by_class,
        'feature_importance': {f: round(float(v), 3)
                               for f, v in zip(FEATURES, model.feature_importances_)},
    }
