# =============================================================================
# S.H.I.E.L.D. Core Engine — Synthetic Data Generator
# Generates realistic SoLEXS + HEL1OS time-series data that follows the
# Neupert effect physics, so we can test the full pipeline without needing
# real PRADAN data.
#
# Physics modeled:
#   - Quiet Sun baseline with noise
#   - Pre-flare gradual heating (SoLEXS rises first)
#   - Impulsive phase (HEL1OS spike follows, Neupert relation)
#   - Gradual decay
# =============================================================================

import logging
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd

from config.settings import PROCESSED_DATA_DIR

logger = logging.getLogger(__name__)


def generate_quiet_sun(
    duration_s: int = 3600,
    cadence_s: int = 1,
    start_time: Optional[datetime] = None,
) -> dict:
    """
    Generate quiet-Sun baseline data for both instruments.

    Parameters
    ----------
    duration_s : int
        Duration in seconds (default: 1 hour).
    cadence_s : int
        Time cadence in seconds.
    start_time : datetime, optional
        Start time for the time axis.

    Returns
    -------
    dict
        {'solexs': DataFrame, 'hel1os': DataFrame}
    """
    if start_time is None:
        start_time = datetime(2024, 5, 14, 10, 0, 0)

    n_points = duration_s // cadence_s
    times = [start_time + timedelta(seconds=i * cadence_s) for i in range(n_points)]

    # Quiet Sun flux levels (approximate GOES-scale values)
    solexs_base = 1e-7   # ~B-class quiet background
    hel1os_base = 5e-3   # Low hard X-ray counts

    solexs_flux = solexs_base * (1 + 0.02 * np.random.randn(n_points))
    hel1os_flux = hel1os_base * (1 + 0.05 * np.random.randn(n_points))

    # Ensure no negatives
    solexs_flux = np.maximum(solexs_flux, 1e-9)
    hel1os_flux = np.maximum(hel1os_flux, 1e-5)

    return {
        'solexs': pd.DataFrame({'timestamp': times, 'flux': solexs_flux}),
        'hel1os': pd.DataFrame({'timestamp': times, 'flux': hel1os_flux}),
    }


def generate_flare_event(
    peak_class: str = "X8.7",
    preflare_duration_s: int = 600,
    impulsive_duration_s: int = 120,
    gradual_decay_s: int = 1800,
    quiet_before_s: int = 1800,
    quiet_after_s: int = 1200,
    cadence_s: int = 1,
    start_time: Optional[datetime] = None,
    neupert_lag_s: int = 45,
    noise_level: float = 0.03,
) -> dict:
    """
    Generate a synthetic solar flare event with realistic Neupert-effect
    physics for both SoLEXS and HEL1OS.

    The flare has four phases:
      1. Quiet Sun baseline
      2. Pre-flare heating (SoLEXS rises, HEL1OS quiet)
      3. Impulsive phase (HEL1OS spikes, SoLEXS near peak)
      4. Gradual decay

    Parameters
    ----------
    peak_class : str
        GOES flare class (e.g., "X8.7", "M5.0", "C3.2").
    preflare_duration_s : int
        Duration of pre-flare heating phase (seconds).
    impulsive_duration_s : int
        Duration of impulsive phase (seconds).
    gradual_decay_s : int
        Duration of gradual decay (seconds).
    quiet_before_s : int
        Quiet-Sun baseline before the flare.
    quiet_after_s : int
        Quiet-Sun baseline after the flare.
    cadence_s : int
        Time cadence in seconds.
    start_time : datetime, optional
        Start time. Defaults to May 14, 2024 10:00 UTC.
    neupert_lag_s : int
        Lag between SoLEXS derivative peak and HEL1OS peak.
    noise_level : float
        Fractional noise level.

    Returns
    -------
    dict
        {
            'solexs': DataFrame,
            'hel1os': DataFrame,
            'metadata': dict with timing info,
        }
    """
    if start_time is None:
        start_time = datetime(2024, 5, 14, 10, 0, 0)

    # Parse flare class to peak flux (GOES scale, W/m^2)
    peak_flux = _class_to_flux(peak_class)

    # Build total time array
    total_s = quiet_before_s + preflare_duration_s + impulsive_duration_s + gradual_decay_s + quiet_after_s
    n_points = total_s // cadence_s
    t = np.arange(n_points) * cadence_s  # seconds from start
    times = [start_time + timedelta(seconds=float(ti)) for ti in t]

    # --- Phase boundaries (seconds from start) ---
    t_quiet_end = quiet_before_s
    t_preflare_end = t_quiet_end + preflare_duration_s
    t_impulsive_end = t_preflare_end + impulsive_duration_s
    t_decay_end = t_impulsive_end + gradual_decay_s

    # Key timing for metadata
    preflare_start_time = start_time + timedelta(seconds=t_quiet_end)
    impulsive_start_time = start_time + timedelta(seconds=t_preflare_end)
    peak_time = start_time + timedelta(seconds=t_preflare_end + impulsive_duration_s * 0.3)

    # =========================================================================
    # SoLEXS (SOFT X-RAY) — thermal emission
    # Rises during pre-flare heating, peaks during/after impulsive phase,
    # decays slowly.
    # =========================================================================
    solexs_base = 1e-7  # B-class quiet level
    solexs_flux = np.full(n_points, solexs_base)

    for i, ti in enumerate(t):
        if ti < t_quiet_end:
            # Phase 1: Quiet Sun
            solexs_flux[i] = solexs_base

        elif ti < t_preflare_end:
            # Phase 2: Pre-flare heating — gradual exponential rise
            phase_frac = (ti - t_quiet_end) / preflare_duration_s
            # Exponential steepening — the derivative increases over time
            solexs_flux[i] = solexs_base * np.exp(
                phase_frac * np.log(peak_flux / solexs_base) * 0.4
            )

        elif ti < t_impulsive_end:
            # Phase 3: Impulsive — rapid rise to peak
            phase_frac = (ti - t_preflare_end) / impulsive_duration_s
            pre_level = solexs_base * np.exp(
                np.log(peak_flux / solexs_base) * 0.4
            )
            # Smooth rise to peak using a sigmoid-like curve
            rise = 0.5 * (1 + np.tanh(6 * (phase_frac - 0.3)))
            solexs_flux[i] = pre_level + (peak_flux - pre_level) * rise

        elif ti < t_decay_end:
            # Phase 4: Gradual decay — exponential cooling
            phase_frac = (ti - t_impulsive_end) / gradual_decay_s
            solexs_flux[i] = peak_flux * np.exp(-2.5 * phase_frac) + solexs_base

        else:
            # Phase 5: Back to quiet
            solexs_flux[i] = solexs_base

    # =========================================================================
    # HEL1OS (HARD X-RAY) — non-thermal emission
    # Neupert effect: HEL1OS flux ~ d/dt(SoLEXS flux)
    # Sharp impulsive spike, minimal pre-flare signal.
    # =========================================================================
    hel1os_base = 5e-3  # quiet hard X-ray counts
    hel1os_flux = np.full(n_points, hel1os_base)

    # Compute the SoLEXS derivative (this IS the Neupert relation)
    solexs_deriv = np.gradient(solexs_flux, cadence_s)

    # HEL1OS tracks the positive derivative, shifted by the Neupert lag
    lag_samples = neupert_lag_s // cadence_s
    for i in range(n_points):
        # Shift derivative by lag
        source_idx = i - lag_samples
        if 0 <= source_idx < n_points:
            deriv_val = max(solexs_deriv[source_idx], 0)
            # Scale: HEL1OS counts proportional to derivative
            hel1os_flux[i] = hel1os_base + deriv_val * 1e6
        else:
            hel1os_flux[i] = hel1os_base

    # Add an extra sharp impulsive spike at the impulsive onset
    for i, ti in enumerate(t):
        if t_preflare_end <= ti < t_impulsive_end:
            phase_frac = (ti - t_preflare_end) / impulsive_duration_s
            # Sharp Gaussian-like spike centered at ~30% into impulsive phase
            spike = peak_flux * 50 * np.exp(-0.5 * ((phase_frac - 0.3) / 0.08) ** 2)
            hel1os_flux[i] += spike

    # =========================================================================
    # ADD NOISE
    # =========================================================================
    solexs_flux *= (1 + noise_level * np.random.randn(n_points))
    hel1os_flux *= (1 + noise_level * 2 * np.random.randn(n_points))

    # Ensure no negatives
    solexs_flux = np.maximum(solexs_flux, 1e-9)
    hel1os_flux = np.maximum(hel1os_flux, 1e-5)

    # =========================================================================
    # BUILD OUTPUT
    # =========================================================================
    metadata = {
        'event_start': start_time,
        'preflare_start': preflare_start_time,
        'impulsive_start': impulsive_start_time,
        'peak_time': peak_time,
        'peak_class': peak_class,
        'peak_flux': peak_flux,
        'neupert_lag_s': neupert_lag_s,
        'total_duration_s': total_s,
        'n_points': n_points,
    }

    logger.info(f"Generated synthetic {peak_class} flare event:")
    logger.info(f"  Pre-flare start : {preflare_start_time}")
    logger.info(f"  Impulsive start : {impulsive_start_time}")
    logger.info(f"  Peak time       : {peak_time}")
    logger.info(f"  Neupert lag     : {neupert_lag_s}s")
    logger.info(f"  Total duration  : {total_s}s ({total_s/60:.0f} min)")

    return {
        'solexs': pd.DataFrame({'timestamp': times, 'flux': solexs_flux}),
        'hel1os': pd.DataFrame({'timestamp': times, 'flux': hel1os_flux}),
        'metadata': metadata,
    }


def _class_to_flux(flare_class: str) -> float:
    """
    Convert GOES flare class string to peak flux in W/m^2.

    Examples:
        'X8.7' -> 8.7e-4
        'M5.0' -> 5.0e-5
        'C3.2' -> 3.2e-6
    """
    class_letter = flare_class[0].upper()
    try:
        multiplier = float(flare_class[1:])
    except ValueError:
        multiplier = 1.0

    base_flux = {
        'A': 1e-8,
        'B': 1e-7,
        'C': 1e-6,
        'M': 1e-5,
        'X': 1e-4,
    }

    if class_letter not in base_flux:
        logger.warning(f"Unknown flare class '{class_letter}', defaulting to M-class")
        return 1e-5 * multiplier

    return base_flux[class_letter] * multiplier


def generate_catalog_events(save: bool = True) -> dict:
    """
    Generate synthetic data for all 6 events in the validation catalog.

    Returns
    -------
    dict
        {event_id: {'solexs': DataFrame, 'hel1os': DataFrame, 'metadata': dict}}
    """
    from config.flare_catalog import FLARE_CATALOG

    all_events = {}

    for event in FLARE_CATALOG:
        logger.info(f"\n--- Generating: {event.event_id} ({event.peak_class}) ---")

        # Parse the peak class — handle "Multi-X" and "X-class" generics
        peak_class = event.peak_class
        if peak_class in ("X-class", "Multi-X"):
            peak_class = "X2.0"  # Use a representative value

        # Use event window start as the baseline start
        start_time = datetime.combine(event.window_start, datetime.min.time())
        # Place the flare midway through the window
        window_days = (event.window_end - event.window_start).days
        flare_offset = timedelta(days=window_days // 2, hours=12)
        flare_start = start_time + flare_offset

        data = generate_flare_event(
            peak_class=peak_class,
            start_time=flare_start,
            preflare_duration_s=480,
            impulsive_duration_s=90,
            gradual_decay_s=1500,
            quiet_before_s=1800,
            quiet_after_s=1200,
        )

        if save:
            # Save individual instrument CSVs
            solexs_path = PROCESSED_DATA_DIR / f"{event.event_id}_solexs_synthetic.csv"
            hel1os_path = PROCESSED_DATA_DIR / f"{event.event_id}_hel1os_synthetic.csv"
            data['solexs'].to_csv(solexs_path, index=False)
            data['hel1os'].to_csv(hel1os_path, index=False)
            logger.info(f"  Saved to {solexs_path.name} and {hel1os_path.name}")

        all_events[event.event_id] = data

    return all_events
