# =============================================================================
# S.H.I.E.L.D. Core Engine — Adaptive Rolling Baseline
# Maintains a continuously updated baseline (mean + std) for both instruments.
#
# The baseline is the "normal" quiet-Sun level. Flare detection works by
# measuring how far the current flux deviates from this baseline.
#
# Key design:
#   - Uses a rolling window (not a fixed reference) so it adapts to
#     slow drifts in instrument sensitivity and orbital changes.
#   - Excludes elevated periods from the baseline to prevent a flare
#     from "raising the bar" for the next detection.
# =============================================================================

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from config.settings import HEL1OS_BASELINE_WINDOW_S, HEL1OS_SIGMA_THRESHOLD

logger = logging.getLogger(__name__)


@dataclass
class BaselineState:
    """Tracks the rolling baseline statistics for one instrument channel."""

    window_s: int                          # Rolling window size in seconds
    mean: float = 0.0                      # Current baseline mean
    std: float = 0.0                       # Current baseline standard deviation
    n_samples: int = 0                     # Number of samples in current window
    buffer: list = field(default_factory=list)  # Circular buffer of recent values
    max_buffer: int = 0                    # Max buffer size (set from window_s)
    is_initialized: bool = False           # Whether we have enough data

    def __post_init__(self):
        self.max_buffer = self.window_s     # 1 sample per second at 1s cadence


def compute_rolling_baseline(
    flux_series: pd.Series,
    window_s: int = HEL1OS_BASELINE_WINDOW_S,
    exclude_elevated: bool = True,
    sigma_exclude: float = 3.0,
) -> pd.DataFrame:
    """
    Compute an adaptive rolling baseline (mean + std) for a flux time-series.

    The baseline represents the quiet-Sun level. Points that are significantly
    elevated (likely flare activity) are excluded from the baseline calculation
    so that a flare doesn't corrupt the reference level.

    Parameters
    ----------
    flux_series : pd.Series
        Flux values (1-second cadence assumed).
    window_s : int
        Rolling window size in seconds.
    exclude_elevated : bool
        If True, exclude points > sigma_exclude*std above the mean from
        the baseline computation (prevents flare contamination).
    sigma_exclude : float
        Number of sigma above mean to flag as "elevated" for exclusion.

    Returns
    -------
    pd.DataFrame
        Columns: ['baseline_mean', 'baseline_std', 'sigma_above_baseline',
                   'is_elevated']
    """
    n = len(flux_series)
    flux = flux_series.values.astype(float)

    baseline_mean = np.full(n, np.nan)
    baseline_std = np.full(n, np.nan)
    sigma_above = np.full(n, 0.0)
    is_elevated = np.full(n, False)

    if exclude_elevated:
        # Two-pass approach:
        # Pass 1: Simple rolling stats to identify elevated regions
        # Pass 2: Recompute baseline excluding elevated regions

        # Pass 1: Simple rolling mean/std
        simple_mean = pd.Series(flux).rolling(
            window=window_s, min_periods=window_s // 4, center=False
        ).mean().values

        simple_std = pd.Series(flux).rolling(
            window=window_s, min_periods=window_s // 4, center=False
        ).std().values

        # Identify elevated points
        for i in range(n):
            if not np.isnan(simple_mean[i]) and simple_std[i] > 0:
                sigma_above[i] = (flux[i] - simple_mean[i]) / simple_std[i]
                is_elevated[i] = sigma_above[i] > sigma_exclude

        # Pass 2: Recompute baseline excluding elevated points
        quiet_flux = flux.copy()
        quiet_flux[is_elevated] = np.nan

        quiet_series = pd.Series(quiet_flux)
        baseline_mean = quiet_series.rolling(
            window=window_s, min_periods=window_s // 4, center=False
        ).mean().values

        baseline_std = quiet_series.rolling(
            window=window_s, min_periods=window_s // 4, center=False
        ).std().values

        # Recompute sigma above the clean baseline
        for i in range(n):
            if not np.isnan(baseline_mean[i]) and baseline_std[i] > 0:
                sigma_above[i] = (flux[i] - baseline_mean[i]) / baseline_std[i]
            else:
                sigma_above[i] = 0.0

    else:
        # Simple rolling stats without exclusion
        series = pd.Series(flux)
        baseline_mean = series.rolling(
            window=window_s, min_periods=window_s // 4, center=False
        ).mean().values

        baseline_std = series.rolling(
            window=window_s, min_periods=window_s // 4, center=False
        ).std().values

        for i in range(n):
            if not np.isnan(baseline_mean[i]) and baseline_std[i] > 0:
                sigma_above[i] = (flux[i] - baseline_mean[i]) / baseline_std[i]

    # Fill initial NaN baseline with first valid values
    first_valid_mean = next((v for v in baseline_mean if not np.isnan(v)), 0)
    first_valid_std = next((v for v in baseline_std if not np.isnan(v)), 1)
    baseline_mean = np.where(np.isnan(baseline_mean), first_valid_mean, baseline_mean)
    baseline_std = np.where(np.isnan(baseline_std), first_valid_std, baseline_std)

    # Ensure std is never zero (avoid division errors downstream)
    baseline_std = np.maximum(baseline_std, 1e-15)

    return pd.DataFrame({
        'baseline_mean': baseline_mean,
        'baseline_std': baseline_std,
        'sigma_above_baseline': sigma_above,
        'is_elevated': is_elevated,
    })


def compute_dual_baseline(
    df: pd.DataFrame,
    solexs_window_s: int = HEL1OS_BASELINE_WINDOW_S,
    hel1os_window_s: int = HEL1OS_BASELINE_WINDOW_S,
) -> pd.DataFrame:
    """
    Compute rolling baselines for both SoLEXS and HEL1OS simultaneously.

    Parameters
    ----------
    df : pd.DataFrame
        Preprocessed DataFrame with 'solexs_flux' and 'hel1os_flux' columns.
    solexs_window_s : int
        Baseline window for SoLEXS (seconds).
    hel1os_window_s : int
        Baseline window for HEL1OS (seconds).

    Returns
    -------
    pd.DataFrame
        Original DataFrame with added baseline columns for both instruments.
    """
    result = df.copy()

    # SoLEXS baseline
    if 'solexs_flux' in result.columns:
        solexs_bl = compute_rolling_baseline(
            result['solexs_flux'],
            window_s=solexs_window_s,
            exclude_elevated=True,
        )
        result['solexs_baseline_mean'] = solexs_bl['baseline_mean']
        result['solexs_baseline_std'] = solexs_bl['baseline_std']
        result['solexs_sigma'] = solexs_bl['sigma_above_baseline']
        result['solexs_elevated'] = solexs_bl['is_elevated']

    # HEL1OS baseline
    if 'hel1os_flux' in result.columns:
        hel1os_bl = compute_rolling_baseline(
            result['hel1os_flux'],
            window_s=hel1os_window_s,
            exclude_elevated=True,
        )
        result['hel1os_baseline_mean'] = hel1os_bl['baseline_mean']
        result['hel1os_baseline_std'] = hel1os_bl['baseline_std']
        result['hel1os_sigma'] = hel1os_bl['sigma_above_baseline']
        result['hel1os_elevated'] = hel1os_bl['is_elevated']

    logger.info("Computed dual baselines for SoLEXS and HEL1OS")
    return result
