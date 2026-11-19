# =============================================================================
# S.H.I.E.L.D. — LSTM Flare Probability Forecaster (PyTorch)
# A recurrent (sequence) model: reads a SEQUENCE of recent activity-feature
# steps and predicts P(M+ flare within the next 24 h). Unlike XGBoost (which
# sees one snapshot), the LSTM can learn temporal build-up patterns.
#
# Honest: same chronological train/test split and the same labels as the
# XGBoost forecaster, so the two are directly comparable.
# =============================================================================

import logging
from pathlib import Path
from typing import Union

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

SEQ_LEN = 8          # number of past steps fed to the LSTM (8 x 3h = 24h history)


def _make_sequences(ds: pd.DataFrame, features, seq_len=SEQ_LEN):
    """Turn the time-ordered feature table into (sequence, label) pairs."""
    X = ds[features].to_numpy(dtype=np.float32)
    y = ds['y'].to_numpy(dtype=np.float32)
    seqs, labels = [], []
    for i in range(seq_len, len(ds)):
        seqs.append(X[i - seq_len:i])
        labels.append(y[i])
    return np.array(seqs, dtype=np.float32), np.array(labels, dtype=np.float32)


def train_lstm_forecaster(catalog_csv: Union[str, Path], horizon_h: float = 24.0,
                          epochs: int = 40) -> dict:
    """Train + chronologically evaluate the LSTM forecaster; compare to XGBoost."""
    import torch
    import torch.nn as nn
    from sklearn.metrics import roc_auc_score, brier_score_loss
    from ml.forecaster import build_dataset, FEATURES

    torch.manual_seed(42); np.random.seed(42)
    cat = pd.read_csv(catalog_csv)
    ds = build_dataset(cat, horizon_h=horizon_h).dropna().reset_index(drop=True)

    X, y = _make_sequences(ds, FEATURES)
    split = int(len(X) * 0.70)
    Xtr, Xte, ytr, yte = X[:split], X[split:], y[:split], y[split:]

    # standardize features using train stats only
    mu = Xtr.reshape(-1, Xtr.shape[-1]).mean(0)
    sd = Xtr.reshape(-1, Xtr.shape[-1]).std(0) + 1e-6
    Xtr = (Xtr - mu) / sd; Xte = (Xte - mu) / sd

    dev = torch.device('cpu')
    Xtr_t = torch.tensor(Xtr, device=dev); ytr_t = torch.tensor(ytr, device=dev)
    Xte_t = torch.tensor(Xte, device=dev)

    class LSTMNet(nn.Module):
        def __init__(self, n_feat, hidden=32):
            super().__init__()
            self.lstm = nn.LSTM(n_feat, hidden, batch_first=True)
            self.head = nn.Sequential(nn.Linear(hidden, 16), nn.ReLU(), nn.Linear(16, 1))
        def forward(self, x):
            out, _ = self.lstm(x)
            return self.head(out[:, -1, :]).squeeze(-1)

    model = LSTMNet(Xtr.shape[-1])
    # class imbalance weight
    pos = float(ytr.sum()); neg = float(len(ytr) - pos)
    pos_weight = torch.tensor([neg / max(pos, 1)])
    loss_fn = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    opt = torch.optim.Adam(model.parameters(), lr=0.01)

    bs = 128
    for ep in range(epochs):
        model.train(); perm = torch.randperm(len(Xtr_t))
        for i in range(0, len(Xtr_t), bs):
            idx = perm[i:i + bs]
            opt.zero_grad()
            loss = loss_fn(model(Xtr_t[idx]), ytr_t[idx])
            loss.backward(); opt.step()

    model.eval()
    with torch.no_grad():
        p = torch.sigmoid(model(Xte_t)).cpu().numpy()

    auc = roc_auc_score(yte, p) if len(np.unique(yte)) > 1 else float('nan')
    brier = brier_score_loss(yte, p)
    base = float(ytr.mean())
    brier_clim = brier_score_loss(yte, np.full(len(yte), base))

    # XGBoost reference on identical task
    from ml.forecaster import train_forecaster
    xgb = train_forecaster(catalog_csv, horizon_h=horizon_h)

    return {
        'model': model, 'mu': mu, 'sd': sd, 'seq_len': SEQ_LEN,
        'n_train': len(Xtr), 'n_test': len(Xte),
        'lstm_roc_auc': round(float(auc), 3),
        'lstm_brier': round(float(brier), 4),
        'lstm_skill_vs_clim': round(float(1 - brier / brier_clim), 3) if brier_clim else None,
        'xgboost_roc_auc': xgb['roc_auc'],
        'winner': 'LSTM' if auc > xgb['roc_auc'] else 'XGBoost',
    }
