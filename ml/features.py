# =============================================================================
# S.H.I.E.L.D. Core Engine — Feature Engineering
# Extracts physics-based features from preprocessed SoLEXS + HEL1OS data
# for the XGBoost severity classifier (Layer 2).
#
# Features engineered (from PRD):
#   - Peak flux (SoLEXS and HEL1OS)
#   - Rise rate (how fast flux increases)
#   - Derivative shape (peak derivative, derivative integral)
#   - Duration (time above threshold)
#   - Hardness ratio (HEL1OS / SoLEXS ratio — spectral hardness)
# =============================================================================

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from config.settings import HEL1OS_BASELINE_WINDOW_S

logger = logging.getLogger(__name__)


# =============================================================================
# FEATURE EXTRACTION — SINGLE EVENT
# =============================================================================

def extract_features(
    df: pd.DataFrame,
    event_id: str = "unknown",
) -> Dict[str, float]:
    """
    Extract a feature vector from a preprocessed event DataFrame.

    These features characterize the flare's intensity, temporal profile,
    and spectral properties for severity classification.

    Parameters
    ----------
    df : pd.DataFrame
        Preprocessed DataFrame with columns:
        ['timestamp', 'solexs_flux', 'hel1os_flux']
        and optionally physics engine columns.
    event_id : str
        Event identifier for logging.

    Returns
    -------
    dict
        Feature dictionary with named features.
    """
    features = {}
    features['event_id'] = event_id

    solexs = df['solexs_flux'].values.astype(float)
    hel1os = df['hel1os_flux'].values.astype(float)
    n = len(df)

    # -----------------------------------------------------------------
    # 1. PEAK FLUX
    # -----------------------------------------------------------------
    features['solexs_peak_flux'] = float(np.nanmax(solexs))
    features['hel1os_peak_flux'] = float(np.nanmax(hel1os))
    features['solexs_mean_flux'] = float(np.nanmean(solexs))
    features['hel1os_mean_flux'] = float(np.nanmean(hel1os))

    # Log-scale peaks (flux spans many decades)
    features['solexs_peak_log'] = float(np.log10(max(np.nanmax(solexs), 1e-15)))
    features['hel1os_peak_log'] = float(np.log10(max(np.nanmax(hel1os), 1e-15)))

    # -----------------------------------------------------------------
    # 2. RISE RATE
    # -----------------------------------------------------------------
    # How fast does SoLEXS flux rise from baseline to peak?
    peak_idx = int(np.nanargmax(solexs))
    baseline_level = float(np.nanpercentile(solexs, 10))  # 10th percentile as baseline

    # Find where flux first exceeds 2x baseline (start of rise)
    rise_start = 0
    for i in range(peak_idx):
        if solexs[i] > baseline_level * 2:
            rise_start = i
            break

    rise_duration = max(peak_idx - rise_start, 1)  # seconds
    flux_rise = features['solexs_peak_flux'] - baseline_level

    features['solexs_rise_rate'] = float(flux_rise / rise_duration)
    features['solexs_rise_duration_s'] = float(rise_duration)
    features['solexs_baseline'] = float(baseline_level)
    features['solexs_peak_to_baseline_ratio'] = float(
        features['solexs_peak_flux'] / max(baseline_level, 1e-15)
    )

    # HEL1OS rise rate
    hel1os_peak_idx = int(np.nanargmax(hel1os))
    hel1os_baseline = float(np.nanpercentile(hel1os, 10))
    hel1os_rise_start = 0
    for i in range(hel1os_peak_idx):
        if hel1os[i] > hel1os_baseline * 2:
            hel1os_rise_start = i
            break

    hel1os_rise_dur = max(hel1os_peak_idx - hel1os_rise_start, 1)
    features['hel1os_rise_rate'] = float(
        (features['hel1os_peak_flux'] - hel1os_baseline) / hel1os_rise_dur
    )
    features['hel1os_rise_duration_s'] = float(hel1os_rise_dur)

    # -----------------------------------------------------------------
    # 3. DERIVATIVE SHAPE
    # -----------------------------------------------------------------
    solexs_deriv = np.gradient(solexs, 1.0)

    features['solexs_deriv_peak'] = float(np.nanmax(solexs_deriv))
    features['solexs_deriv_mean_positive'] = float(
        np.nanmean(solexs_deriv[solexs_deriv > 0]) if np.any(solexs_deriv > 0) else 0
    )

    # Integral of positive derivative (total energy input during rise)
    positive_deriv = np.where(solexs_deriv > 0, solexs_deriv, 0)
    features['solexs_deriv_integral'] = float(np.sum(positive_deriv))

    # Shape: ratio of peak derivative to mean positive derivative
    if features['solexs_deriv_mean_positive'] > 0:
        features['solexs_deriv_peakiness'] = float(
            features['solexs_deriv_peak'] / features['solexs_deriv_mean_positive']
        )
    else:
        features['solexs_deriv_peakiness'] = 0.0

    # -----------------------------------------------------------------
    # 4. DURATION
    # -----------------------------------------------------------------
    # Time above 50% of peak (FWHM-like measure)
    half_peak = features['solexs_peak_flux'] * 0.5
    above_half = solexs > half_peak
    features['solexs_duration_above_half_peak_s'] = float(np.sum(above_half))

    # Time above 10% of peak
    tenth_peak = features['solexs_peak_flux'] * 0.1
    above_tenth = solexs > tenth_peak
    features['solexs_duration_above_tenth_peak_s'] = float(np.sum(above_tenth))

    # Impulsive duration for HEL1OS (time above 50% of HEL1OS peak)
    hel1os_half = features['hel1os_peak_flux'] * 0.5
    features['hel1os_impulsive_duration_s'] = float(np.sum(hel1os > hel1os_half))

    # -----------------------------------------------------------------
    # 5. HARDNESS RATIO
    # -----------------------------------------------------------------
    # Ratio of HEL1OS (hard) to SoLEXS (soft) — higher = harder spectrum
    # Compute at peak and as a time-averaged ratio
    if solexs[peak_idx] > 0:
        features['hardness_at_peak'] = float(hel1os[peak_idx] / solexs[peak_idx])
    else:
        features['hardness_at_peak'] = 0.0

    # Time-averaged hardness during elevated period
    elevated_mask = solexs > (baseline_level * 3)
    if np.any(elevated_mask):
        s_elevated = solexs[elevated_mask]
        h_elevated = hel1os[elevated_mask]
        safe_s = np.where(s_elevated > 0, s_elevated, 1e-15)
        features['hardness_mean'] = float(np.nanmean(h_elevated / safe_s))
    else:
        features['hardness_mean'] = 0.0

    # -----------------------------------------------------------------
    # 6. TEMPORAL ASYMMETRY
    # -----------------------------------------------------------------
    # Rise time vs decay time (impulsive flares have fast rise, slow decay)
    if peak_idx > 0 and peak_idx < n - 1:
        rise_time = peak_idx - rise_start
        # Find where flux decays to 50% of peak after peak
        decay_end = n - 1
        for i in range(peak_idx, n):
            if solexs[i] < half_peak:
                decay_end = i
                break
        decay_time = decay_end - peak_idx
        features['temporal_asymmetry'] = float(
            decay_time / max(rise_time, 1)
        )
    else:
        features['temporal_asymmetry'] = 1.0

    # -----------------------------------------------------------------
    # 7. ENERGY PROXY
    # -----------------------------------------------------------------
    # Total integrated flux (proxy for total energy)
    features['solexs_total_flux'] = float(np.nansum(solexs))
    features['hel1os_total_flux'] = float(np.nansum(hel1os))

    logger.info(f"  Extracted {len(features)} features for {event_id}")
    return features


# =============================================================================
# FEATURE EXTRACTION — MULTIPLE EVENTS
# =============================================================================

def extract_features_batch(
    events_data: Dict[str, pd.DataFrame],
    labels: Optional[Dict[str, str]] = None,
) -> pd.DataFrame:
    """
    Extract features from multiple events and return as a DataFrame.

    Parameters
    ----------
    events_data : dict
        {event_id: preprocessed_DataFrame}
    labels : dict, optional
        {event_id: flare_class} for supervised learning.

    Returns
    -------
    pd.DataFrame
        Feature matrix with one row per event.
    """
    feature_rows = []

    for event_id, df in events_data.items():
        features = extract_features(df, event_id)

        # Add label if provided
        if labels and event_id in labels:
            features['flare_class'] = labels[event_id]

        feature_rows.append(features)

    feature_df = pd.DataFrame(feature_rows)
    logger.info(f"  Extracted features for {len(feature_df)} events")
    return feature_df


def get_feature_columns() -> List[str]:
    """Return the list of numeric feature column names (excludes event_id and label)."""
    return [
        'solexs_peak_flux', 'hel1os_peak_flux',
        'solexs_mean_flux', 'hel1os_mean_flux',
        'solexs_peak_log', 'hel1os_peak_log',
        'solexs_rise_rate', 'solexs_rise_duration_s',
        'solexs_baseline', 'solexs_peak_to_baseline_ratio',
        'hel1os_rise_rate', 'hel1os_rise_duration_s',
        'solexs_deriv_peak', 'solexs_deriv_mean_positive',
        'solexs_deriv_integral', 'solexs_deriv_peakiness',
        'solexs_duration_above_half_peak_s',
        'solexs_duration_above_tenth_peak_s',
        'hel1os_impulsive_duration_s',
        'hardness_at_peak', 'hardness_mean',
        'temporal_asymmetry',
        'solexs_total_flux', 'hel1os_total_flux',
    ]
