"""
S.H.I.E.L.D. — Model Training Script
Trains three ML models on real SoLEXS + HEL1OS data:

  Model 1 — SoLEXS Flare Detector (XGBoost, GOES-labelled windows)
  Model 2 — Dual-instrument Classifier (SoLEXS + HEL1OS features)
  Model 3 — Flare Probability Forecaster (GOES catalog activity features)

Run:
  C:\\Users\\lalit\\AppData\\Local\\Python\\bin\\python.exe train_models.py
"""

import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

import sys, json, warnings, logging, time
warnings.filterwarnings('ignore')
sys.path.insert(0, r'd:\Project\SHIELD\SHIELD')

logging.basicConfig(
    level=logging.INFO,
    format='  %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(r'd:\Project\SHIELD\SHIELD\outputs\training_log.txt', mode='w'),
    ]
)
logger = logging.getLogger(__name__)

import numpy as np
import pandas as pd
import joblib
from pathlib import Path

from config.settings import PROJECT_ROOT, OUTPUT_DIR

MODEL_DIR = OUTPUT_DIR / 'models'
MODEL_DIR.mkdir(parents=True, exist_ok=True)

GOES_CSV   = PROJECT_ROOT / 'data' / 'goes_catalog.csv'
SCAN_CSV   = OUTPUT_DIR / 'scan_results.csv'
SOLEXS_DIR = r'E:\SoLEXS'
HEL1OS_DIR = r'E:\HEL1OS'

TRAIN_END  = '2025-03-31'   # chronological train/test split
SCAN_START = '2024-02-01'
SCAN_END   = '2026-06-27'

results = {}
t_total = time.time()


# ─────────────────────────────────────────────────────────────────────────────
# MODEL 1 — SoLEXS Flare Detector
# Slides 6-min windows over SoLEXS; labels from GOES catalog.
# ─────────────────────────────────────────────────────────────────────────────
print('\n' + '='*60)
print('MODEL 1 — SoLEXS Flare Detector')
print('='*60)
t0 = time.time()

from ml.detector import build_detection_dataset, train_detector, FEATURES as DET_FEATURES

DETECTOR_DS = OUTPUT_DIR / 'detector_dataset.csv'

if DETECTOR_DS.exists():
    print(f'  Loading cached detector dataset ({DETECTOR_DS.name})')
    det_ds = pd.read_csv(DETECTOR_DS, parse_dates=['win_start', 'win_end'])
else:
    print(f'  Building windowed dataset — {SCAN_START} to {SCAN_END}')
    det_ds = build_detection_dataset(
        catalog_csv = GOES_CSV,
        start       = SCAN_START,
        end         = SCAN_END,
        data_dir    = SOLEXS_DIR,
        out_csv     = DETECTOR_DS,
    )

print(f'  Dataset: {len(det_ds):,} windows, {int(det_ds["y"].sum())} positive flare windows')
if len(det_ds) > 100:
    det_res = train_detector(det_ds)
    model1  = det_res.pop('model')
    joblib.dump(model1, MODEL_DIR / 'detector_xgb.pkl')
    print(f'  AUC={det_res["roc_auc"]}  Precision={det_res["precision"]}  Recall={det_res["recall"]}')
    print(f'  Recall by class: {det_res["recall_by_class"]}')
    print(f'  Top features: {list(det_res["feature_importance"].items())[:3]}')
    results['model1_detector'] = det_res
    print(f'  Saved -> {MODEL_DIR}/detector_xgb.pkl  ({time.time()-t0:.0f}s)')
else:
    print('  Not enough windows — skipping')
    results['model1_detector'] = {'error': 'insufficient data'}


# ─────────────────────────────────────────────────────────────────────────────
# MODEL 2 — Dual-instrument Classifier (SoLEXS + HEL1OS)
# Positive: 175 real detections from scan_results.csv
# Negative: quiet windows mid-way between consecutive detections
# Features: SoLEXS shape + HEL1OS sigma + Neupert flag + hardness ratio
# ─────────────────────────────────────────────────────────────────────────────
print('\n' + '='*60)
print('MODEL 2 — Dual-instrument Classifier')
print('='*60)
t0 = time.time()

from core.ingest import load_instrument_window
from core.preprocess import align_timeseries, clean_flux_data
from core.physics_engine import run_physics_engine

def _extract_dual_features(c0, c1, label):
    """Load one 4-hour window around c0→c1, run physics, return feature dict."""
    try:
        s = load_instrument_window('solexs', c0, c1, SOLEXS_DIR)
        h = load_instrument_window('hel1os', c0, c1, HEL1OS_DIR)
        if s is None or h is None or s.empty or h.empty:
            return None
        aligned = align_timeseries(s, h)
        if aligned.empty or len(aligned) < 300:
            return None
        cleaned = clean_flux_data(aligned)
        phys    = run_physics_engine(cleaned, auto_calibrate=True)
        df      = phys.df

        sf = df['solexs_flux'].values
        hf = df['hel1os_flux'].values
        sd = df['solexs_derivative'].values if 'solexs_derivative' in df.columns else np.gradient(sf)

        base  = float(np.nanpercentile(sf, 10)) or 1.0
        hbase = float(np.nanpercentile(hf, 10)) or 1.0

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            hr = np.where(sf > 0, hf / sf, 0.0)

        feat = {
            'y':             label,
            'slx_peak':      float(np.nanmax(sf)),
            'slx_peak_bg':   float(np.nanmax(sf) / base),
            'slx_rise':      float(np.nanmax(sf) - np.nanmin(sf)),
            'slx_std':       float(np.nanstd(sf)),
            'slx_d1_max':    float(np.nanmax(sd)),
            'slx_d1_mean':   float(np.nanmean(sd[sd > 0])) if (sd > 0).any() else 0.0,
            'hls_peak':      float(np.nanmax(hf)),
            'hls_peak_bg':   float(np.nanmax(hf) / hbase),
            'hls_rise':      float(np.nanmax(hf) - np.nanmin(hf)),
            'hls_std':       float(np.nanstd(hf)),
            'hardness_peak': float(np.nanmax(hr)),
            'hardness_mean': float(np.nanmean(hr[np.isfinite(hr)])) if np.isfinite(hr).any() else 0.0,
            'neupert_ok':    float(bool(phys.hel1os_detections and
                                        phys.hel1os_detections[0].neupert_consistent)),
            'n_hls_detect':  float(len(phys.hel1os_detections)),
            'n_slx_detect':  float(len(phys.solexs_detections)),
        }
        return feat
    except Exception as e:
        logger.debug(f'    dual feature error {c0}: {e}')
        return None

DUAL_DS = OUTPUT_DIR / 'dual_dataset.csv'

if DUAL_DS.exists():
    print(f'  Loading cached dual dataset ({DUAL_DS.name})')
    dual_df = pd.read_csv(DUAL_DS)
else:
    scan = pd.read_csv(SCAN_CSV, parse_dates=['nowcast_time'])
    scan = scan.dropna(subset=['nowcast_time']).sort_values('nowcast_time').reset_index(drop=True)

    WIN = pd.Timedelta(hours=2)
    rows = []

    print(f'  Extracting features for {len(scan)} positive events...')
    for i, row in scan.iterrows():
        t = row['nowcast_time']
        feat = _extract_dual_features(t - WIN/2, t + WIN/2, label=1)
        if feat:
            rows.append(feat)
        if (i+1) % 25 == 0:
            print(f'    {i+1}/{len(scan)} events done, {len(rows)} features extracted')

    print(f'  Extracting {len(scan)} negative (quiet) windows...')
    for i in range(len(scan) - 1):
        t_mid = scan['nowcast_time'].iloc[i] + (scan['nowcast_time'].iloc[i+1] - scan['nowcast_time'].iloc[i]) / 2
        gap = (scan['nowcast_time'].iloc[i+1] - scan['nowcast_time'].iloc[i]).total_seconds() / 3600
        if gap < 3:
            continue
        feat = _extract_dual_features(t_mid - WIN/2, t_mid + WIN/2, label=0)
        if feat:
            rows.append(feat)
        if (i+1) % 25 == 0:
            print(f'    {i+1}/{len(scan)-1} negatives done, {len(rows)} total')

    dual_df = pd.DataFrame(rows)
    dual_df.to_csv(DUAL_DS, index=False)

DUAL_FEATS = [c for c in dual_df.columns if c != 'y']
print(f'  Dataset: {len(dual_df)} samples, {int(dual_df["y"].sum())} positive')

if len(dual_df) > 50 and dual_df['y'].nunique() > 1:
    from xgboost import XGBClassifier
    from sklearn.metrics import roc_auc_score, precision_score, recall_score

    dual_df = dual_df.dropna().sort_values('slx_peak').reset_index(drop=True)
    split   = int(len(dual_df) * 0.7)
    Xtr = dual_df[DUAL_FEATS].iloc[:split]
    ytr = dual_df['y'].iloc[:split]
    Xte = dual_df[DUAL_FEATS].iloc[split:]
    yte = dual_df['y'].iloc[split:]

    pos = max(int(ytr.sum()), 1); neg_c = max(int((ytr == 0).sum()), 1)
    m2  = XGBClassifier(n_estimators=300, max_depth=4, learning_rate=0.05,
                        subsample=0.8, eval_metric='logloss', random_state=42,
                        scale_pos_weight=neg_c / pos)
    m2.fit(Xtr, ytr)
    p2  = m2.predict_proba(Xte)[:, 1]
    pred2 = (p2 >= 0.5).astype(int)

    dual_res = {
        'n_train': len(Xtr), 'n_test': len(Xte),
        'roc_auc':   round(float(roc_auc_score(yte, p2)), 3) if yte.nunique() > 1 else None,
        'precision': round(float(precision_score(yte, pred2, zero_division=0)), 3),
        'recall':    round(float(recall_score(yte, pred2, zero_division=0)), 3),
        'top_features': {f: round(float(v), 3)
                         for f, v in sorted(zip(DUAL_FEATS, m2.feature_importances_),
                                            key=lambda kv: -kv[1])[:5]},
    }
    joblib.dump(m2, MODEL_DIR / 'dual_instrument_xgb.pkl')
    print(f'  AUC={dual_res["roc_auc"]}  Precision={dual_res["precision"]}  Recall={dual_res["recall"]}')
    print(f'  Top features: {dual_res["top_features"]}')
    results['model2_dual'] = dual_res
    print(f'  Saved -> {MODEL_DIR}/dual_instrument_xgb.pkl  ({time.time()-t0:.0f}s)')
else:
    print('  Not enough samples — skipping')
    results['model2_dual'] = {'error': 'insufficient data'}


# ─────────────────────────────────────────────────────────────────────────────
# MODEL 3 — Flare Probability Forecaster (GOES catalog only)
# Predicts P(M+ flare in next 24h) from recent activity features.
# ─────────────────────────────────────────────────────────────────────────────
print('\n' + '='*60)
print('MODEL 3 — Flare Probability Forecaster')
print('='*60)
t0 = time.time()

from ml.forecaster import train_forecaster

fc_res = train_forecaster(GOES_CSV, horizon_h=24.0)
m3     = fc_res.pop('model')
joblib.dump(m3, MODEL_DIR / 'forecaster_xgb.pkl')
print(f'  AUC={fc_res["roc_auc"]}')
print(f'  Brier: ML={fc_res["brier_ml"]}  Climatology={fc_res["brier_climatology"]}  Poisson={fc_res["brier_poisson"]}')
print(f'  Skill vs climatology: {fc_res["skill_vs_climatology"]}')
print(f'  Skill vs Poisson:     {fc_res["skill_vs_poisson"]}')
print(f'  Top features: {fc_res["top_features"]}')
results['model3_forecaster'] = fc_res
print(f'  Saved -> {MODEL_DIR}/forecaster_xgb.pkl  ({time.time()-t0:.0f}s)')


# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
total_min = (time.time() - t_total) / 60
print('\n' + '='*60)
print(f'ALL MODELS TRAINED in {total_min:.1f} min')
print('='*60)

out = OUTPUT_DIR / 'training_results.json'
out.write_text(json.dumps(results, indent=2, default=str))
print(f'Results -> {out}')

for name, r in results.items():
    if 'roc_auc' in r:
        print(f'  {name}: AUC={r["roc_auc"]}')
