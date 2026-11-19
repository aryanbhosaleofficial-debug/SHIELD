# =============================================================================
# S.H.I.E.L.D. — ML Flare Severity Classifier
# Given a DETECTED flare's measured features, predict its GOES class band
# (C / M / X). Labels come from matching our detections to the official GOES
# catalog; features are what the detector/physics already measured.
#
# Honest: small labelled set (only flares we both detected AND matched), strong
# class imbalance (few C reach the hard-X detector). Reported with stratified
# cross-validation, not a single optimistic split.
# =============================================================================

import logging
from pathlib import Path
from typing import Union

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

FEATURES = ['peak_solexs_log', 'hel1os_sigma_log', 'gap_s', 'neupert_ok']


def _build_labelled(scan_csv: Union[str, Path], catalog_csv: Union[str, Path]) -> pd.DataFrame:
    from core.benchmark import load_goes_catalog, match_to_catalog
    det = pd.read_csv(scan_csv)
    det['nowcast_time'] = pd.to_datetime(det['nowcast_time'])
    cat = load_goes_catalog(catalog_csv)
    m = match_to_catalog(det, cat, tol_min=30)
    df = m['matched'].copy()
    if df.empty:
        return df
    df['peak_solexs_log'] = np.log10(df['peak_solexs'].clip(lower=1.0).astype(float))
    df['hel1os_sigma_log'] = np.log10(df['hel1os_sigma'].clip(lower=1.0).astype(float))
    df['gap_s'] = pd.to_numeric(df.get('gap_s'), errors='coerce').fillna(0.0)
    df['neupert_ok'] = df.get('neupert_ok', False).astype(int)
    df['label'] = df['goes_letter']     # C / M / X
    return df


def train_severity(scan_csv: Union[str, Path], catalog_csv: Union[str, Path]) -> dict:
    """Train + stratified-CV evaluate the C/M/X severity classifier (XGBoost)."""
    from xgboost import XGBClassifier
    from sklearn.metrics import accuracy_score, confusion_matrix

    df = _build_labelled(scan_csv, catalog_csv)
    if df.empty:
        return {'ok': False, 'reason': 'no matched flares'}

    # drop ultra-rare classes that can't be cross-validated, keep C/M/X
    counts = df['label'].value_counts()
    keep = counts[counts >= 3].index
    df = df[df['label'].isin(keep)].reset_index(drop=True)
    classes = sorted(df['label'].unique())
    cls_to_i = {c: i for i, c in enumerate(classes)}
    X = df[FEATURES].to_numpy(dtype=float)
    y = df['label'].map(cls_to_i).to_numpy()

    # Manual stratified k-fold (avoid sklearn.ensemble/model_selection DLLs)
    rng = np.random.RandomState(42)
    k = 5
    folds = [[] for _ in range(k)]
    for c in np.unique(y):
        idx = np.where(y == c)[0]; rng.shuffle(idx)
        for j, ix in enumerate(idx):
            folds[j % k].append(ix)

    accs, all_true, all_pred = [], [], []
    for f in range(k):
        te = np.array(folds[f]); tr = np.array([i for g in range(k) if g != f for i in folds[g]])
        if len(te) == 0 or len(tr) == 0:
            continue
        model = XGBClassifier(n_estimators=150, max_depth=3, learning_rate=0.1,
                              subsample=0.9, eval_metric='mlogloss', random_state=42,
                              num_class=len(classes), objective='multi:softprob')
        model.fit(X[tr], y[tr])
        pred = model.predict(X[te])
        accs.append(accuracy_score(y[te], pred))
        all_true += list(y[te]); all_pred += list(pred)

    # final model on all data (for deployment)
    final = XGBClassifier(n_estimators=150, max_depth=3, learning_rate=0.1,
                          subsample=0.9, eval_metric='mlogloss', random_state=42,
                          num_class=len(classes), objective='multi:softprob')
    final.fit(X, y)
    cm = confusion_matrix(all_true, all_pred).tolist() if all_true else []

    # majority-class baseline
    base = float(df['label'].value_counts(normalize=True).max())
    return {
        'ok': True, 'model': final, 'classes': classes,
        'n_samples': int(len(df)), 'class_counts': counts.to_dict(),
        'cv_accuracy_mean': round(float(np.mean(accs)), 3) if accs else None,
        'cv_accuracy_std': round(float(np.std(accs)), 3) if accs else None,
        'majority_baseline': round(base, 3),
        'confusion_matrix': cm, 'confusion_labels': classes,
        'feature_importance': {f: round(float(v), 3)
                               for f, v in zip(FEATURES, final.feature_importances_)},
    }
