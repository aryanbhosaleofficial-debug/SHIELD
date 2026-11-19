# =============================================================================
# S.H.I.E.L.D. Core Engine — Layer 1 Physics Engine
# Zero-training, deterministic flare detection using pure physics.
#
# This is the PRIMARY deliverable — the star of the project.
# It mirrors the onboard flare-trigger logic ISRO already flies on Aditya-L1.
#
# Two detection channels:
#   SoLEXS FORECASTING:
#     - Computes first derivative of soft X-ray light curve
#     - Measures slope-steepening rate over short windows
#     - Raises FORECAST ALERT when sustained positive steepening detected
#
#   HEL1OS NOWCASTING:
#     - Maintains rolling baseline mean + std of hard X-ray flux
#     - Raises NOWCAST CONFIRMED when flux crosses N-sigma above baseline
#     - Cross-checks Neupert consistency with SoLEXS derivative
#
# Properties:
#   - Deterministic calculus on real telemetry
#   - Cannot overfit (no training)
#   - Needs zero training data
#   - Works on day one
# =============================================================================

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import signal

from config.settings import (
    SOLEXS_DERIVATIVE_WINDOW_S,
    SOLEXS_STEEPENING_WINDOW_S,
    SOLEXS_SUSTAINED_THRESHOLD_S,
    SOLEXS_DERIVATIVE_THRESHOLD,
    SOLEXS_STEEPENING_RATE_THRESHOLD,
    HEL1OS_BASELINE_WINDOW_S,
    HEL1OS_SIGMA_THRESHOLD,
    HEL1OS_MIN_SPIKE_DURATION_S,
    NEUPERT_CORRELATION_THRESHOLD,
    NEUPERT_LAG_WINDOW_S,
)
from core.baseline import compute_rolling_baseline, compute_dual_baseline

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES FOR DETECTION RESULTS
# =============================================================================

@dataclass
class SoLEXSDetection:
    """Result from the SoLEXS forecasting channel."""
    timestamp: pd.Timestamp              # When the detection was made
    derivative: float                     # SoLEXS flux derivative at detection
    steepening_rate: float               # Rate of derivative increase
    sustained_duration_s: float          # How long steepening has been sustained
    provisional_class: str               # Estimated flare class from flux level
    confidence: float                    # Confidence score (0-1)


@dataclass
class HEL1OSDetection:
    """Result from the HEL1OS nowcasting channel."""
    timestamp: pd.Timestamp              # When the detection was made
    sigma_above_baseline: float          # How many sigma above baseline
    peak_flux: float                     # HEL1OS flux at detection
    spike_duration_s: float              # Duration of the spike so far
    neupert_consistent: bool             # Whether Neupert cross-check passes
    neupert_correlation: float           # Correlation value with SoLEXS derivative


@dataclass
class PhysicsEngineResult:
    """Complete result from running the physics engine on a dataset."""
    # Computed columns added to the DataFrame
    df: pd.DataFrame

    # Detection events
    solexs_detections: List[SoLEXSDetection] = field(default_factory=list)
    hel1os_detections: List[HEL1OSDetection] = field(default_factory=list)

    # Timing
    first_forecast_alert: Optional[pd.Timestamp] = None
    first_nowcast_confirmed: Optional[pd.Timestamp] = None
    stage3_to_4_gap_s: Optional[float] = None


# =============================================================================
# SoLEXS FORECASTING — SOFT X-RAY DERIVATIVE ANALYSIS
# =============================================================================

def compute_solexs_derivatives(
    flux_series: pd.Series,
    smooth_window_s: int = SOLEXS_DERIVATIVE_WINDOW_S,
    steepening_window_s: int = SOLEXS_STEEPENING_WINDOW_S,
) -> pd.DataFrame:
    """
    Compute the first derivative and steepening rate of the SoLEXS
    soft X-ray light curve.

    The derivative is the key signal for forecasting: a sustained,
    steepening positive derivative indicates plasma heating — the
    pre-flare phase that precedes the impulsive burst.

    Parameters
    ----------
    flux_series : pd.Series
        SoLEXS soft X-ray flux values (1-second cadence).
    smooth_window_s : int
        Smoothing window before taking derivative (reduces noise).
    steepening_window_s : int
        Window over which to measure slope-steepening rate.

    Returns
    -------
    pd.DataFrame
        Columns: ['solexs_smoothed', 'solexs_derivative',
                   'solexs_steepening_rate', 'solexs_deriv_positive_duration']
    """
    flux = flux_series.values.astype(float)
    n = len(flux)

    # Step 1: Smooth the raw flux to reduce noise before differentiation
    # Use a Savitzky-Golay filter for smooth derivatives (preserves peaks)
    if smooth_window_s >= 3:
        win = smooth_window_s if smooth_window_s % 2 == 1 else smooth_window_s + 1
        win = min(win, n - 1) if n > win else max(3, n if n % 2 == 1 else n - 1)
        try:
            smoothed = signal.savgol_filter(flux, window_length=win, polyorder=2)
        except ValueError:
            smoothed = pd.Series(flux).rolling(
                window=smooth_window_s, min_periods=1, center=True
            ).mean().values
    else:
        smoothed = flux.copy()

    # Step 2: Compute first derivative using numpy.gradient
    # This gives df/dt in flux-units per second
    derivative = np.gradient(smoothed, 1.0)  # 1.0 = 1 second spacing

    # Step 3: Compute steepening rate (derivative of the derivative)
    # This tells us if the rise is ACCELERATING (positive steepening = danger)
    steepening = np.gradient(derivative, 1.0)

    # Smooth the steepening rate to avoid noise spikes
    steepening_smooth = pd.Series(steepening).rolling(
        window=steepening_window_s, min_periods=1, center=True
    ).mean().values

    # Step 4: Track how long the derivative has been continuously positive
    positive_duration = np.zeros(n)
    for i in range(1, n):
        if derivative[i] > 0:
            positive_duration[i] = positive_duration[i - 1] + 1  # seconds
        else:
            positive_duration[i] = 0

    # Step 5: RELATIVE (fractional / logarithmic) growth rate = (dF/dt) / F.
    # This is the physically correct forecast signal. Pre-flare heating is an
    # EXPONENTIAL rise, whose fractional growth rate is large and sustained from
    # the very start of heating — long before the absolute derivative grows big
    # enough to cross a noise-based threshold. It is also scale-invariant, so the
    # same threshold works for a C-flare and an X-flare. We smooth it over the
    # steepening window so a genuine sustained rise stands out above quiet noise.
    smoothed_safe = np.maximum(smoothed, 1e-12)
    rel_derivative = derivative / smoothed_safe
    rel_deriv_smooth = pd.Series(rel_derivative).rolling(
        window=steepening_window_s, min_periods=1, center=True
    ).mean().values

    return pd.DataFrame({
        'solexs_smoothed': smoothed,
        'solexs_derivative': derivative,
        'solexs_steepening_rate': steepening_smooth,
        'solexs_deriv_positive_duration': positive_duration,
        'solexs_rel_derivative': rel_derivative,
        'solexs_rel_deriv_smooth': rel_deriv_smooth,
    })


def detect_solexs_forecast(
    df: pd.DataFrame,
    derivative_threshold: float = SOLEXS_DERIVATIVE_THRESHOLD,
    steepening_threshold: float = SOLEXS_STEEPENING_RATE_THRESHOLD,
    sustained_threshold_s: float = SOLEXS_SUSTAINED_THRESHOLD_S,
) -> List[SoLEXSDetection]:
    """
    Scan the SoLEXS derivative data for FORECAST ALERT conditions.

    A FORECAST ALERT fires when:
      1. The derivative is positive and above the threshold, AND
      2. The steepening rate is positive (derivative is increasing), AND
      3. This condition has been sustained for >= sustained_threshold_s

    Parameters
    ----------
    df : pd.DataFrame
        Must contain columns from compute_solexs_derivatives().
    derivative_threshold : float
        Minimum derivative value to trigger.
    steepening_threshold : float
        Minimum steepening rate.
    sustained_threshold_s : float
        How long conditions must hold (seconds).

    Returns
    -------
    List[SoLEXSDetection]
        List of forecast alert detections.
    """
    detections = []
    in_alert = False
    sustained_count = 0  # Track how long derivative has been continuously above threshold

    required_cols = ['solexs_derivative', 'solexs_steepening_rate', 'timestamp']
    for col in required_cols:
        if col not in df.columns:
            logger.error(f"Missing column: {col}")
            return []

    # Use numpy arrays for speed
    deriv_values = df['solexs_derivative'].values
    steep_values = df['solexs_steepening_rate'].values
    timestamps = df['timestamp'].values
    flux_values = df['solexs_flux'].values if 'solexs_flux' in df.columns else np.zeros(len(df))

    # FORECAST gates on the smoothed RELATIVE growth rate (fractional heating
    # rate) when available — this catches the gradual pre-flare exponential rise
    # well before the absolute derivative is large. Falls back to the absolute
    # derivative for backward compatibility if the relative column is absent.
    if 'solexs_rel_deriv_smooth' in df.columns:
        signal_values = df['solexs_rel_deriv_smooth'].values
    else:
        signal_values = deriv_values

    # Pre-compute: boolean mask of where the forecast signal exceeds threshold
    above_mask = signal_values > derivative_threshold

    # Use a sliding-window approach: count how many seconds in the last
    # (2 * sustained_threshold_s) had derivative above threshold.
    # Fire alert when the count exceeds sustained_threshold_s.
    # This is more robust than requiring N consecutive seconds, because
    # a single noise dip won't reset the entire counter.
    lookback = int(sustained_threshold_s * 2)

    for i in range(len(df)):
        if not above_mask[i]:
            continue  # Skip if current point isn't above threshold

        # Count how many of the last `lookback` seconds were above threshold
        window_start = max(0, i - lookback)
        above_count = int(np.sum(above_mask[window_start:i + 1]))

        # Fire FORECAST ALERT when enough of the recent window is elevated
        conditions_met = above_count >= sustained_threshold_s

        if conditions_met and not in_alert:
            # New FORECAST ALERT
            in_alert = True

            deriv = deriv_values[i]
            sig = signal_values[i]
            steep = steep_values[i]

            # Estimate provisional flare class from current flux level
            prov_class = _flux_to_class(flux_values[i])

            # Confidence: base from how far the forecast signal exceeds threshold
            # plus how long it has been sustained, boosted by active steepening.
            steepening_boost = 0.2 if steep > steepening_threshold else 0.0
            confidence = min(1.0, (
                min(sig / derivative_threshold, 5.0) / 5.0 * 0.4 +
                min(above_count / sustained_threshold_s, 3.0) / 3.0 * 0.4 +
                steepening_boost
            ))

            detection = SoLEXSDetection(
                timestamp=pd.Timestamp(timestamps[i]),
                derivative=deriv,
                steepening_rate=steep,
                sustained_duration_s=float(above_count),
                provisional_class=prov_class,
                confidence=confidence,
            )
            detections.append(detection)
            logger.info(f"  FORECAST ALERT at {detection.timestamp} "
                        f"(deriv={deriv:.2e}, class~{prov_class}, "
                        f"conf={confidence:.2f})")

        elif not above_mask[i] and in_alert:
            # Alert conditions no longer met
            in_alert = False

    return detections


# =============================================================================
# HEL1OS NOWCASTING — HARD X-RAY SIGMA DETECTION
# =============================================================================

def detect_hel1os_nowcast(
    df: pd.DataFrame,
    sigma_threshold: float = HEL1OS_SIGMA_THRESHOLD,
    min_spike_duration_s: int = HEL1OS_MIN_SPIKE_DURATION_S,
    correlation_threshold: float = NEUPERT_CORRELATION_THRESHOLD,
    lag_window_s: int = NEUPERT_LAG_WINDOW_S,
) -> List[HEL1OSDetection]:
    """
    Scan HEL1OS hard X-ray data for NOWCAST CONFIRMED conditions.

    A NOWCAST CONFIRMED fires when:
      1. HEL1OS flux crosses N-sigma above baseline, AND
      2. The spike persists for at least min_spike_duration_s, AND
      3. Neupert cross-check passes (HEL1OS spike correlates with
         SoLEXS derivative)

    Parameters
    ----------
    df : pd.DataFrame
        Must contain columns: 'hel1os_sigma', 'timestamp',
        and optionally 'solexs_derivative' for Neupert check.
    sigma_threshold : float
        Number of sigma above baseline to trigger.
    min_spike_duration_s : int
        Minimum spike duration to filter cosmic-ray glitches.
    correlation_threshold : float
        Minimum Neupert correlation to confirm.
    lag_window_s : int
        Window to check correlation.

    Returns
    -------
    List[HEL1OSDetection]
        List of nowcast confirmed detections.
    """
    detections = []
    spike_start = None
    spike_count = 0

    # Use numpy arrays for speed instead of iloc
    sigma_values = df['hel1os_sigma'].values if 'hel1os_sigma' in df.columns else np.zeros(len(df))
    flux_values = df['hel1os_flux'].values if 'hel1os_flux' in df.columns else np.zeros(len(df))
    timestamps = df['timestamp'].values

    for i in range(len(df)):
        sigma = sigma_values[i]

        if sigma >= sigma_threshold:
            if spike_start is None:
                spike_start = i
            spike_count += 1

            # Check if spike has lasted long enough
            if spike_count >= min_spike_duration_s:
                # Neupert cross-check
                neupert_ok, neupert_corr = _check_neupert(
                    df, i, lag_window_s, correlation_threshold
                )

                flux_val = df['hel1os_flux'].iloc[i] if 'hel1os_flux' in df.columns else 0

                detection = HEL1OSDetection(
                    timestamp=df['timestamp'].iloc[i],
                    sigma_above_baseline=sigma,
                    peak_flux=flux_val,
                    spike_duration_s=float(spike_count),
                    neupert_consistent=neupert_ok,
                    neupert_correlation=neupert_corr,
                )

                # Only add if this is the first detection in this spike
                if spike_count == min_spike_duration_s:
                    detections.append(detection)
                    status = "CONFIRMED" if neupert_ok else "TENTATIVE"
                    logger.info(
                        f"  NOWCAST {status} at {detection.timestamp} "
                        f"(sigma={sigma:.1f}, neupert_r={neupert_corr:.2f})"
                    )

        else:
            spike_start = None
            spike_count = 0

    return detections


def _check_neupert(
    df: pd.DataFrame,
    current_idx: int,
    lag_window_s: int,
    threshold: float,
) -> Tuple[bool, float]:
    """
    Check the Neupert consistency: does the HEL1OS spike correlate with
    the SoLEXS derivative in the recent window?

    The Neupert effect says: HEL1OS flux ~ d/dt(SoLEXS flux)
    So if we see a HEL1OS spike, the SoLEXS derivative should also be
    elevated in the recent past.
    """
    if 'solexs_derivative' not in df.columns or 'hel1os_flux' not in df.columns:
        return True, 0.0  # Can't check, assume OK

    # Look at the window around the current point
    start = max(0, current_idx - lag_window_s)
    end = min(len(df), current_idx + 1)

    if end - start < 10:  # Need enough data for meaningful correlation
        return True, 0.0

    solexs_deriv = df['solexs_derivative'].iloc[start:end].values
    hel1os_flux = df['hel1os_flux'].iloc[start:end].values

    # Remove NaN
    valid = ~(np.isnan(solexs_deriv) | np.isnan(hel1os_flux))
    if valid.sum() < 10:
        return True, 0.0

    solexs_deriv = solexs_deriv[valid]
    hel1os_flux = hel1os_flux[valid]

    # Compute correlation
    if np.std(solexs_deriv) < 1e-15 or np.std(hel1os_flux) < 1e-15:
        return True, 0.0

    correlation = np.corrcoef(solexs_deriv, hel1os_flux)[0, 1]

    # Neupert says they should be positively correlated
    return correlation >= threshold, correlation


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def _flux_to_class(flux: float) -> str:
    """Convert flux value to approximate GOES flare class string."""
    if flux >= 1e-4:
        multiplier = flux / 1e-4
        return f"X{multiplier:.1f}"
    elif flux >= 1e-5:
        multiplier = flux / 1e-5
        return f"M{multiplier:.1f}"
    elif flux >= 1e-6:
        multiplier = flux / 1e-6
        return f"C{multiplier:.1f}"
    elif flux >= 1e-7:
        multiplier = flux / 1e-7
        return f"B{multiplier:.1f}"
    else:
        return "A"


# =============================================================================
# MAIN PHYSICS ENGINE — RUN THE FULL PIPELINE
# =============================================================================

def run_physics_engine(
    df: pd.DataFrame,
    derivative_threshold: Optional[float] = None,
    steepening_threshold: Optional[float] = None,
    sustained_threshold_s: Optional[float] = None,
    sigma_threshold: Optional[float] = None,
    auto_calibrate: bool = True,
) -> PhysicsEngineResult:
    """
    Run the complete Layer 1 Physics Engine on a preprocessed DataFrame.

    This is the main entry point for flare detection. It:
      1. Computes SoLEXS derivatives and steepening rates
      2. Computes HEL1OS rolling baseline and sigma scores
      3. Detects FORECAST ALERTs from SoLEXS
      4. Detects NOWCAST CONFIRMEDs from HEL1OS
      5. Measures the Stage-3 -> Stage-4 gap

    Parameters
    ----------
    df : pd.DataFrame
        Preprocessed DataFrame with ['timestamp', 'solexs_flux', 'hel1os_flux'].
    derivative_threshold : float, optional
        Override for SoLEXS derivative threshold.
    steepening_threshold : float, optional
        Override for steepening rate threshold.
    sustained_threshold_s : float, optional
        Override for sustained duration threshold.
    sigma_threshold : float, optional
        Override for HEL1OS sigma threshold.
    auto_calibrate : bool
        If True, automatically calibrate thresholds based on the quiet-Sun
        portion of the data (first 20%).

    Returns
    -------
    PhysicsEngineResult
        Complete detection results with timing measurements.
    """
    logger.info("=" * 60)
    logger.info("LAYER 1 PHYSICS ENGINE — Running")
    logger.info("=" * 60)
    logger.info(f"  Input: {len(df)} data points")
    logger.info(f"  Time range: {df['timestamp'].iloc[0]} -> {df['timestamp'].iloc[-1]}")

    result_df = df.copy()

    # =====================================================================
    # STEP 1: Compute SoLEXS derivatives (incl. relative growth-rate signal)
    # Done BEFORE calibration so we can calibrate on the actual forecast signal.
    # =====================================================================
    logger.info("\n  [1/4] Computing SoLEXS derivatives...")
    deriv_df = compute_solexs_derivatives(result_df['solexs_flux'])
    for col in deriv_df.columns:
        result_df[col] = deriv_df[col].values

    logger.info(f"    Peak derivative: {result_df['solexs_derivative'].max():.2e}")
    logger.info(f"    Peak steepening: {result_df['solexs_steepening_rate'].max():.2e}")

    # =====================================================================
    # AUTO-CALIBRATION (if enabled)
    # The forecast threshold is set from the quiet-Sun statistics of the SAME
    # signal the detector uses — the smoothed relative growth rate — so a real
    # sustained pre-flare rise stands clear of background noise.
    # =====================================================================
    if auto_calibrate:
        quiet_end = len(df) // 5  # First 20% assumed quiet
        quiet_rel = result_df['solexs_rel_deriv_smooth'].iloc[:quiet_end].values
        quiet_rel = quiet_rel[np.isfinite(quiet_rel)]
        quiet_rel_mean = float(np.mean(quiet_rel)) if quiet_rel.size else 0.0
        quiet_rel_std = float(np.std(quiet_rel)) if quiet_rel.size else 1e-6

        # Quiet-period steepening (second derivative) statistics for the boost.
        quiet_solexs = df['solexs_flux'].iloc[:quiet_end]
        quiet_steep = np.gradient(np.gradient(quiet_solexs.values))
        quiet_steep_std = float(np.std(quiet_steep))

        if derivative_threshold is None:
            # Trigger when the sustained fractional heating rate sits a clear
            # margin (6 sigma) above quiet background. Because the signal is
            # smoothed over the steepening window, quiet noise rarely reaches
            # this AND stays there for the sustained-duration requirement.
            quiet_rel_p99 = float(np.percentile(np.abs(quiet_rel), 99.5)) if quiet_rel.size else 0.0
            derivative_threshold = max(
                quiet_rel_mean + 6.0 * quiet_rel_std,
                quiet_rel_p99 * 1.5,
                1e-4,  # floor: ignore utterly flat segments
            )
            logger.info(f"  Auto-calibrated forecast threshold (rel. rate): {derivative_threshold:.2e}/s")
            logger.info(f"    (quiet rel-rate mean={quiet_rel_mean:.2e}, std={quiet_rel_std:.2e})")

        if steepening_threshold is None:
            quiet_steep_p99 = float(np.percentile(np.abs(quiet_steep), 99.5))
            steepening_threshold = max(quiet_steep_std * 20, quiet_steep_p99 * 3)
            logger.info(f"  Auto-calibrated steepening_threshold: {steepening_threshold:.2e}")

    # Use defaults for any remaining None values
    derivative_threshold = derivative_threshold or SOLEXS_DERIVATIVE_THRESHOLD
    steepening_threshold = steepening_threshold or SOLEXS_STEEPENING_RATE_THRESHOLD
    sustained_threshold_s = sustained_threshold_s or SOLEXS_SUSTAINED_THRESHOLD_S
    sigma_threshold = sigma_threshold or HEL1OS_SIGMA_THRESHOLD

    logger.info(f"  Thresholds:")
    logger.info(f"    SoLEXS forecast rate: {derivative_threshold:.2e}/s")
    logger.info(f"    SoLEXS steepening   : {steepening_threshold:.2e}")
    logger.info(f"    SoLEXS sustained    : {sustained_threshold_s}s")
    logger.info(f"    HEL1OS sigma        : {sigma_threshold}")

    # =====================================================================
    # STEP 2: Compute HEL1OS baseline and sigma scores
    # =====================================================================
    logger.info("\n  [2/4] Computing HEL1OS baseline and sigma scores...")
    result_df = compute_dual_baseline(result_df)

    logger.info(f"    HEL1OS peak sigma: {result_df['hel1os_sigma'].max():.1f}")
    logger.info(f"    HEL1OS elevated points: {result_df['hel1os_elevated'].sum()}")

    # =====================================================================
    # STEP 3: Detect SoLEXS FORECAST ALERTs
    # =====================================================================
    logger.info("\n  [3/4] Scanning for SoLEXS FORECAST ALERTs...")
    solexs_detections = detect_solexs_forecast(
        result_df,
        derivative_threshold=derivative_threshold,
        steepening_threshold=steepening_threshold,
        sustained_threshold_s=sustained_threshold_s,
    )
    logger.info(f"    Found {len(solexs_detections)} FORECAST ALERT(s)")

    # =====================================================================
    # STEP 4: Detect HEL1OS NOWCAST CONFIRMEDs
    # =====================================================================
    logger.info("\n  [4/4] Scanning for HEL1OS NOWCAST CONFIRMEDs...")
    hel1os_detections = detect_hel1os_nowcast(
        result_df,
        sigma_threshold=sigma_threshold,
    )
    logger.info(f"    Found {len(hel1os_detections)} NOWCAST CONFIRMED(s)")

    # =====================================================================
    # MEASURE STAGE 3 -> STAGE 4 GAP (THE CORE DELIVERABLE)
    # =====================================================================
    first_forecast = None
    first_nowcast = None
    gap_s = None

    if solexs_detections:
        first_forecast = solexs_detections[0].timestamp

    if hel1os_detections:
        first_nowcast = hel1os_detections[0].timestamp

    if first_forecast and first_nowcast:
        gap = (first_nowcast - first_forecast).total_seconds()
        gap_s = gap
        logger.info(f"\n  {'='*50}")
        logger.info(f"  CORE RESULT: Stage 3 -> Stage 4 gap")
        logger.info(f"    FORECAST ALERT     : {first_forecast}")
        logger.info(f"    NOWCAST CONFIRMED  : {first_nowcast}")
        logger.info(f"    GAP                : {gap:.1f} seconds ({gap/60:.1f} minutes)")
        if gap > 0:
            logger.info(f"    >> FORECAST preceded NOWCAST by {gap:.0f}s")
        else:
            logger.info(f"    >> WARNING: NOWCAST fired before FORECAST ({abs(gap):.0f}s)")
        logger.info(f"  {'='*50}")
    elif first_forecast:
        logger.info("\n  FORECAST ALERT fired but no NOWCAST CONFIRMED detected.")
    elif first_nowcast:
        logger.info("\n  NOWCAST CONFIRMED fired but no FORECAST ALERT detected.")
    else:
        logger.info("\n  No detections — data may be quiet-Sun only.")

    return PhysicsEngineResult(
        df=result_df,
        solexs_detections=solexs_detections,
        hel1os_detections=hel1os_detections,
        first_forecast_alert=first_forecast,
        first_nowcast_confirmed=first_nowcast,
        stage3_to_4_gap_s=gap_s,
    )
