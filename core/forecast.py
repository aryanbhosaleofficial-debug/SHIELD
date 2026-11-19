# =============================================================================
# S.H.I.E.L.D. — Layer A: Activity Forecast (hours ahead, PROBABILISTIC)
# The honest "forecast from SoLEXS + HEL1OS" layer.
#
# It does NOT claim to predict a specific flare's onset time. Instead it answers
# the operationally useful question:
#
#     "Given how active the Sun has been (flare rate, trend), what is the
#      PROBABILITY of at least one significant flare in the next 6 / 24 hours?"
#
# Model: flares are treated as a Poisson process whose rate lambda is estimated
# from the recent flare history with a weak climatological prior (Bayesian
# smoothing so the probability is never 0 and never overreacts to one flare):
#
#     lambda = (k + a0) / (delta_h + b0)          [flares per hour]
#     P(>=1 flare in next T h) = 1 - exp(-lambda * T)
#
# This is transparent, physically grounded, and honestly probabilistic — the
# same family of model operational space-weather centres use for flare-rate
# forecasts. No black-box ML trained on a handful of events.
# =============================================================================

import logging
from typing import Optional, Union, Sequence

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Weak climatological prior on the flare rate (per hour). Pulls the estimate
# toward ~0.5 significant flares/day when there is no recent activity, with the
# strength of ~1 day of observation so a real cluster still dominates.
_PRIOR_RATE_PER_H = 0.02      # ~0.5/day baseline
_PRIOR_WEIGHT_H = 24.0        # equivalent to 1 day of prior observation
_A0 = _PRIOR_RATE_PER_H * _PRIOR_WEIGHT_H
_B0 = _PRIOR_WEIGHT_H

DEFAULT_LOOKBACK_H = 24
DEFAULT_HORIZONS_H = (6, 24)


def _level(p24: float, recent_big: bool) -> str:
    """Map a 24h probability (+ recent strong flare) to an operational level."""
    if recent_big or p24 >= 0.75:
        return "HIGH"
    if p24 >= 0.50:
        return "ELEVATED"
    if p24 >= 0.25:
        return "WATCH"
    return "LOW"


def forecast_at(
    flare_times: Sequence[Union[str, pd.Timestamp]],
    now: Union[str, pd.Timestamp],
    lookback_h: float = DEFAULT_LOOKBACK_H,
    horizons_h: Sequence[int] = DEFAULT_HORIZONS_H,
    big_flare_times: Optional[Sequence[Union[str, pd.Timestamp]]] = None,
) -> dict:
    """
    Probabilistic activity forecast at time `now`, using ONLY flares before `now`.

    Parameters
    ----------
    flare_times : all detected flare timestamps (the activity history).
    now : the forecast issue time.
    lookback_h : how far back to estimate the recent rate.
    horizons_h : forecast horizons (hours).
    big_flare_times : optional subset of strong (e.g. high-sigma) flares; a recent
        one bumps the alert level.

    Returns dict: rate_per_h, n_recent, p_<T>h per horizon, level.
    """
    now = pd.Timestamp(now)
    ft = pd.to_datetime(pd.Series(list(flare_times))) if len(flare_times) else pd.Series([], dtype='datetime64[ns]')
    past = ft[(ft <= now) & (ft > now - pd.Timedelta(hours=lookback_h))]
    k = int(len(past))

    # Bayesian-smoothed Poisson rate (flares/hour).
    rate = (k + _A0) / (lookback_h + _B0)

    out = {
        'time': str(now),
        'n_recent': k,
        'rate_per_h': round(rate, 4),
        'rate_per_day': round(rate * 24, 3),
    }
    for T in horizons_h:
        out[f'p_{T}h'] = round(1.0 - float(np.exp(-rate * T)), 3)

    recent_big = False
    if big_flare_times is not None and len(big_flare_times):
        bf = pd.to_datetime(pd.Series(list(big_flare_times)))
        recent_big = bool(((bf <= now) & (bf > now - pd.Timedelta(hours=lookback_h))).any())
    out['level'] = _level(out.get('p_24h', 0.0), recent_big)
    return out


def rolling_forecast(
    flare_times: Sequence[Union[str, pd.Timestamp]],
    start: Union[str, pd.Timestamp],
    end: Union[str, pd.Timestamp],
    step_h: float = 1.0,
    lookback_h: float = DEFAULT_LOOKBACK_H,
    horizons_h: Sequence[int] = DEFAULT_HORIZONS_H,
    big_flare_times: Optional[Sequence] = None,
) -> pd.DataFrame:
    """Walk the forecast across [start, end] at step_h, using only past flares."""
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    times = pd.date_range(start, end, freq=f'{int(step_h*60)}min')
    rows = [forecast_at(flare_times, t, lookback_h, horizons_h, big_flare_times)
            for t in times]
    return pd.DataFrame(rows)


def event_forecast_summary(
    flare_times: Sequence[Union[str, pd.Timestamp]],
    start: Union[str, pd.Timestamp],
    end: Union[str, pd.Timestamp],
    lookback_h: float = DEFAULT_LOOKBACK_H,
) -> Optional[dict]:
    """
    Peak activity-forecast reached during an event window (the highest alert the
    Layer-A Poisson model issued). Honest situational-awareness number — NOT a
    skillful prediction. Returns None if there are no flares.
    """
    if not len(flare_times):
        return None
    rf = rolling_forecast(flare_times, start, end, step_h=1.0, lookback_h=lookback_h)
    if rf.empty:
        return None
    i = int(rf['p_24h'].astype(float).idxmax())
    row = rf.iloc[i]
    return {
        'peak_p_6h': float(row.get('p_6h', 0.0)),
        'peak_p_24h': float(row.get('p_24h', 0.0)),
        'peak_level': str(row.get('level', 'LOW')),
        'peak_time': str(row.get('time', '')),
        'note': 'situational awareness (Poisson activity rate) — not a skillful per-flare forecast',
    }


def validate_forecast(
    flare_times: Sequence[Union[str, pd.Timestamp]],
    start: Union[str, pd.Timestamp],
    end: Union[str, pd.Timestamp],
    horizon_h: int = 24,
    step_h: float = 1.0,
    lookback_h: float = DEFAULT_LOOKBACK_H,
) -> dict:
    """
    Walk-forward reliability check: at each step, compare the predicted
    probability of >=1 flare in the next `horizon_h` to what ACTUALLY happened.

    Returns Brier score (lower=better), a climatology-baseline Brier, the skill
    score, and a reliability table (predicted-prob bin -> observed frequency).
    """
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    ft = pd.to_datetime(pd.Series(list(flare_times)))
    times = pd.date_range(start, end - pd.Timedelta(hours=horizon_h), freq=f'{int(step_h*60)}min')

    preds, actuals = [], []
    for t in times:
        p = forecast_at(flare_times, t, lookback_h, (horizon_h,))[f'p_{horizon_h}h']
        occurred = bool(((ft > t) & (ft <= t + pd.Timedelta(hours=horizon_h))).any())
        preds.append(p)
        actuals.append(1.0 if occurred else 0.0)

    preds, actuals = np.array(preds), np.array(actuals)
    if len(preds) == 0:
        return {}
    base_rate = actuals.mean()
    brier = float(np.mean((preds - actuals) ** 2))
    brier_clim = float(np.mean((base_rate - actuals) ** 2))
    skill = 1.0 - brier / brier_clim if brier_clim > 0 else 0.0

    # Reliability: bin predictions into deciles, observed frequency per bin.
    bins = np.linspace(0, 1, 6)
    idx = np.clip(np.digitize(preds, bins) - 1, 0, len(bins) - 2)
    reliability = []
    for b in range(len(bins) - 1):
        m = idx == b
        if m.any():
            reliability.append({
                'pred_range': f"{bins[b]:.1f}-{bins[b+1]:.1f}",
                'mean_pred': round(float(preds[m].mean()), 3),
                'observed_freq': round(float(actuals[m].mean()), 3),
                'n': int(m.sum()),
            })

    return {
        'horizon_h': horizon_h,
        'n_forecasts': len(preds),
        'base_rate': round(float(base_rate), 3),
        'brier': round(brier, 4),
        'brier_climatology': round(brier_clim, 4),
        'skill_score': round(float(skill), 3),
        'reliability': reliability,
    }
