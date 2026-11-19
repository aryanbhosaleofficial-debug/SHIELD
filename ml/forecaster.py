# =============================================================================
# S.H.I.E.L.D. — ML Flare Probability Forecaster (Layer 3 / Tier-0)
# Supervised model: given the recent flare-activity state, predict the
# probability of an M+ flare in the next 24h. Trained on the official GOES
# catalog (8k+ flares) — finally enough data to ask whether ML beats the
# transparent Poisson baseline (core/forecast.py).
#
# Honest by design: chronological train/test split (no leakage), and we report
# skill vs BOTH a climatology baseline and the Poisson model.
# =============================================================================

import logging
from pathlib import Path
from typing import Optional, Union

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# GOES flux thresholds (W/m^2)
_M_FLUX = 1e-5      # M-class
_C_FLUX = 1e-6


def _flux(cls: str) -> float:
    from core.impact import class_to_flux
    f = class_to_flux(cls)
    return f if f else 0.0


def build_dataset(catalog: pd.DataFrame, step_h: float = 3.0,
                  horizon_h: float = 24.0) -> pd.DataFrame:
    """
    Turn the flare catalog into a supervised table sampled every `step_h` hours.

    Features (recent activity only, no leakage):
        n_6h, n_12h, n_24h, n_48h        flare counts in trailing windows
        nM_24h, nM_48h                   M+ flare counts
        hrs_since_last, hrs_since_lastM  recency
        max_flux_24h_log                 strongest recent flare (log10)
        rate_24h                         flares/hour
        hour_of_day
    Label:
        y = 1 if an M+ flare peaks within the next `horizon_h`.
    """
    cat = catalog.copy()
    cat['peak_time'] = pd.to_datetime(cat['peak_time'])
    cat['flux'] = cat['goes_class'].map(_flux)
    cat = cat.sort_values('peak_time').reset_index(drop=True)
    times = cat['peak_time'].values.astype('datetime64[ns]')
    fluxes = cat['flux'].values

    t0 = cat['peak_time'].min().ceil('h')
    t1 = cat['peak_time'].max().floor('h') - pd.Timedelta(hours=horizon_h)
    grid = pd.date_range(t0, t1, freq=f'{int(step_h*60)}min')

    rows = []
    for t in grid:
        tnp = np.datetime64(t)
        past = times <= tnp
        def cnt(h):
            lo = tnp - np.timedelta64(int(h*3600), 's')
            return int(np.sum((times > lo) & (times <= tnp)))
        def cntM(h):
            lo = tnp - np.timedelta64(int(h*3600), 's')
            return int(np.sum((times > lo) & (times <= tnp) & (fluxes >= _M_FLUX)))
        last_idx = np.where(past)[0]
        hrs_since = ((tnp - times[last_idx[-1]]) / np.timedelta64(1, 'h')) if last_idx.size else 999.0
        mpast = np.where(past & (fluxes >= _M_FLUX))[0]
        hrs_sinceM = ((tnp - times[mpast[-1]]) / np.timedelta64(1, 'h')) if mpast.size else 999.0
        lo24 = tnp - np.timedelta64(24*3600, 's')
        m24 = (times > lo24) & (times <= tnp)
        maxf = float(np.max(fluxes[m24])) if m24.any() else 1e-9
        # label: any M+ in (t, t+horizon]
        hi = tnp + np.timedelta64(int(horizon_h*3600), 's')
        y = int(np.any((times > tnp) & (times <= hi) & (fluxes >= _M_FLUX)))
        rows.append({
            'time': t, 'n_6h': cnt(6), 'n_12h': cnt(12), 'n_24h': cnt(24), 'n_48h': cnt(48),
            'nM_24h': cntM(24), 'nM_48h': cntM(48),
            'hrs_since_last': min(hrs_since, 999.0), 'hrs_since_lastM': min(hrs_sinceM, 999.0),
            'max_flux_24h_log': np.log10(max(maxf, 1e-9)), 'rate_24h': cnt(24) / 24.0,
            'hour_of_day': t.hour, 'y': y,
        })
    return pd.DataFrame(rows)


FEATURES = ['n_6h', 'n_12h', 'n_24h', 'n_48h', 'nM_24h', 'nM_48h',
            'hrs_since_last', 'hrs_since_lastM', 'max_flux_24h_log',
            'rate_24h', 'hour_of_day']


def train_forecaster(catalog_csv: Union[str, Path], horizon_h: float = 24.0) -> dict:
    """Train + chronologically evaluate the ML forecaster. Returns metrics + model."""
    from xgboost import XGBClassifier
    from sklearn.metrics import roc_auc_score, brier_score_loss

    cat = pd.read_csv(catalog_csv)
    ds = build_dataset(cat, horizon_h=horizon_h)
    ds = ds.dropna().reset_index(drop=True)

    # chronological split: first 70% train, last 30% test (no leakage)
    split = int(len(ds) * 0.70)
    tr, te = ds.iloc[:split], ds.iloc[split:]
    Xtr, ytr = tr[FEATURES], tr['y']
    Xte, yte = te[FEATURES], te['y']

    # XGBoost (sklearn's ensemble DLLs are blocked by Application Control policy
    # on this machine; XGBoost is the available gradient-booster).
    model = XGBClassifier(n_estimators=200, max_depth=3, learning_rate=0.05,
                          subsample=0.8, eval_metric='logloss', random_state=42)
    model.fit(Xtr, ytr)
    p = model.predict_proba(Xte)[:, 1]

    # baselines
    base_rate = float(ytr.mean())
    brier_ml = brier_score_loss(yte, p)
    brier_clim = brier_score_loss(yte, np.full(len(yte), base_rate))
    # Poisson baseline on the same test times
    from core.forecast import forecast_at
    flare_times = pd.to_datetime(cat['peak_time']).tolist()
    p_pois = np.array([forecast_at(flare_times, t, horizons_h=(int(horizon_h),))[f'p_{int(horizon_h)}h']
                       for t in te['time']])
    brier_pois = brier_score_loss(yte, p_pois)

    auc = roc_auc_score(yte, p) if yte.nunique() > 1 else float('nan')
    skill_vs_clim = 1 - brier_ml / brier_clim if brier_clim > 0 else 0.0
    skill_vs_pois = 1 - brier_ml / brier_pois if brier_pois > 0 else 0.0

    importance = dict(sorted(zip(FEATURES, model.feature_importances_),
                             key=lambda kv: -kv[1]))
    return {
        'model': model, 'n_train': len(tr), 'n_test': len(te),
        'test_base_rate': round(base_rate, 3),
        'roc_auc': round(float(auc), 3),
        'brier_ml': round(float(brier_ml), 4),
        'brier_climatology': round(float(brier_clim), 4),
        'brier_poisson': round(float(brier_pois), 4),
        'skill_vs_climatology': round(float(skill_vs_clim), 3),
        'skill_vs_poisson': round(float(skill_vs_pois), 3),
        'top_features': {k: round(float(v), 3) for k, v in list(importance.items())[:5]},
    }
