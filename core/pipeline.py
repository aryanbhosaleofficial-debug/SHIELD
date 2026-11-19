# =============================================================================
# S.H.I.E.L.D. Core Engine — Four-Stage Detection Pipeline
# The state machine that moves a flare through four stages:
#
#   Stage 1: QUIET SUN       — baseline, all clear
#   Stage 2: PRE-FLARE       — SoLEXS derivative rising, WATCH issued
#   Stage 3: FORECAST ALERT  — sustained steepening, flare anticipated
#   Stage 4: NOWCAST CONFIRM — HEL1OS spike, flare onset confirmed
#
# The transition from Stage 3 to Stage 4 is THE quantity we measure.
# =============================================================================

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from config.settings import (
    SOLEXS_DERIVATIVE_THRESHOLD,
    SOLEXS_STEEPENING_RATE_THRESHOLD,
    SOLEXS_SUSTAINED_THRESHOLD_S,
    HEL1OS_SIGMA_THRESHOLD,
    STAGES,
)
from config.flare_catalog import FlareEvent, get_event_by_id, get_all_events
from core.synthetic import generate_flare_event
from core.preprocess import preprocess_event
from core.physics_engine import run_physics_engine, PhysicsEngineResult
from core.alert import (
    Alert, AlertLevel, AlertLog, create_alert,
)

logger = logging.getLogger(__name__)


# =============================================================================
# PIPELINE RESULT
# =============================================================================

class PipelineResult:
    """Complete result from running the four-stage pipeline on one event."""

    def __init__(self, event_id: str):
        self.event_id = event_id
        self.alert_log = AlertLog(event_id=event_id)
        self.physics_result: Optional[PhysicsEngineResult] = None
        self.processed_df: Optional[pd.DataFrame] = None
        self.stage_timeline: List[Dict] = []

        # Core metrics
        self.forecast_fired: bool = False
        self.nowcast_fired: bool = False
        self.stage3_to_4_gap_s: Optional[float] = None
        self.max_stage_reached: int = 1
        self.false_positive_count: int = 0

    def print_report(self):
        """Print a formatted report of the pipeline results."""
        print()
        print(f"  +{'='*59}+")
        print(f"  |  PIPELINE REPORT: {self.event_id:<39}|")
        print(f"  +{'='*59}+")
        print()

        # Stage timeline
        print(f"  Stage Timeline:")
        for entry in self.stage_timeline:
            stage = entry['stage']
            ts = entry['timestamp']
            info = STAGES.get(stage, {})
            name = info.get('name', f'STAGE {stage}')
            status = info.get('status', '')
            print(f"    Stage {stage} ({name}): {ts}")
        print()

        # Core metrics
        print(f"  Core Metrics:")
        print(f"    Max stage reached  : {self.max_stage_reached}")
        print(f"    FORECAST fired     : {'YES' if self.forecast_fired else 'NO'}")
        print(f"    NOWCAST fired      : {'YES' if self.nowcast_fired else 'NO'}")

        if self.stage3_to_4_gap_s is not None:
            gap = self.stage3_to_4_gap_s
            direction = "FORECAST preceded NOWCAST" if gap > 0 else "Nearly simultaneous" if gap == 0 else "NOWCAST preceded FORECAST"
            print(f"    Stage 3->4 gap     : {gap:.1f}s ({gap/60:.1f} min)")
            print(f"    Direction          : {direction}")

        # Alert summary
        self.alert_log.print_summary()
        print()


# =============================================================================
# PIPELINE EXECUTION
# =============================================================================

def run_pipeline(
    solexs_df: pd.DataFrame,
    hel1os_df: pd.DataFrame,
    event_id: str = "unknown",
    save_processed: bool = True,
) -> PipelineResult:
    """
    Run the complete four-stage detection pipeline on a pair of
    instrument DataFrames.

    Steps:
      1. Preprocess (align + clean)
      2. Run Layer 1 Physics Engine
      3. Walk through data and assign stages
      4. Generate alerts at each stage transition
      5. Measure Stage 3->4 gap

    Parameters
    ----------
    solexs_df : pd.DataFrame
        Raw SoLEXS data with ['timestamp', 'flux'].
    hel1os_df : pd.DataFrame
        Raw HEL1OS data with ['timestamp', 'flux'].
    event_id : str
        Event identifier.
    save_processed : bool
        Whether to save processed data to disk.

    Returns
    -------
    PipelineResult
        Complete pipeline results with alerts and metrics.
    """
    result = PipelineResult(event_id=event_id)

    logger.info(f"\n{'#'*60}")
    logger.info(f"  PIPELINE: {event_id}")
    logger.info(f"{'#'*60}")

    # --- Step 1: Preprocess ---
    logger.info("\n  [PIPELINE 1/3] Preprocessing...")
    processed = preprocess_event(
        solexs_df, hel1os_df,
        event_id=event_id,
        save=save_processed,
    )

    if processed.empty:
        logger.error(f"  Preprocessing produced no data for {event_id}")
        return result

    result.processed_df = processed

    # --- Step 2: Run Physics Engine ---
    logger.info("\n  [PIPELINE 2/3] Running Physics Engine...")
    physics = run_physics_engine(processed, auto_calibrate=True)
    result.physics_result = physics

    # --- Step 3: Build stage timeline and alerts ---
    logger.info("\n  [PIPELINE 3/3] Building stage timeline...")
    alert_count = 0

    # Stage 1: ALL CLEAR at start
    alert_count += 1
    alert = create_alert(
        level=AlertLevel.ALL_CLEAR,
        timestamp=processed['timestamp'].iloc[0],
        trigger_source='pipeline',
        event_id=event_id,
        alert_count=alert_count,
        provisional_class="--",
        confidence=1.0,
    )
    result.alert_log.add_alert(alert)
    result.stage_timeline.append({
        'stage': 1, 'timestamp': processed['timestamp'].iloc[0]
    })

    # Stage 2: WATCH — first sign of sustained pre-flare heating. Uses the SAME
    # relative growth-rate signal as the FORECAST stage but at a lower threshold,
    # so WATCH (stage 2) always precedes FORECAST (stage 3).
    watch_col = ('solexs_rel_deriv_smooth'
                 if 'solexs_rel_deriv_smooth' in physics.df.columns
                 else 'solexs_derivative')
    if watch_col in physics.df.columns:
        watch_signal = physics.df[watch_col].values
        deriv_values = physics.df['solexs_derivative'].values
        timestamps = physics.df['timestamp'].values

        # Calibrate the watch threshold from the quiet portion of the same
        # signal, at ~3 sigma (vs ~6 sigma for FORECAST) so it triggers earlier.
        quiet_end = len(physics.df) // 5
        quiet_sig = watch_signal[:quiet_end]
        quiet_sig = quiet_sig[np.isfinite(quiet_sig)]
        q_mean = float(np.mean(quiet_sig)) if quiet_sig.size else 0.0
        q_std = float(np.std(quiet_sig)) if quiet_sig.size else 1e-6
        watch_threshold = max(q_mean + 3.0 * q_std, 5e-5)

        # Find first sustained positive signal above watch threshold
        above_watch = watch_signal > watch_threshold
        for i in range(len(physics.df)):
            if above_watch[i]:
                window_start = max(0, i - 30)
                if np.sum(above_watch[window_start:i+1]) >= 15:  # 15 of last 30s
                    alert_count += 1
                    watch_flux = physics.df['solexs_flux'].iloc[i]
                    alert = create_alert(
                        level=AlertLevel.WATCH,
                        timestamp=pd.Timestamp(timestamps[i]),
                        trigger_source='solexs',
                        event_id=event_id,
                        alert_count=alert_count,
                        provisional_class="--",
                        confidence=0.3,
                        solexs_flux=float(watch_flux),
                        solexs_derivative=float(deriv_values[i]),
                    )
                    result.alert_log.add_alert(alert)
                    result.stage_timeline.append({
                        'stage': 2, 'timestamp': pd.Timestamp(timestamps[i])
                    })
                    break

    # Stage 3: FORECAST ALERT — from physics engine detections
    if physics.solexs_detections:
        det = physics.solexs_detections[0]  # First detection
        alert_count += 1
        alert = create_alert(
            level=AlertLevel.FORECAST_ALERT,
            timestamp=det.timestamp,
            trigger_source='solexs',
            event_id=event_id,
            alert_count=alert_count,
            provisional_class=det.provisional_class,
            confidence=det.confidence,
            solexs_derivative=det.derivative,
            sustained_duration_s=det.sustained_duration_s,
        )
        result.alert_log.add_alert(alert)
        result.stage_timeline.append({
            'stage': 3, 'timestamp': det.timestamp
        })
        result.forecast_fired = True

    # Stage 4: NOWCAST CONFIRMED — from physics engine detections
    if physics.hel1os_detections:
        det = physics.hel1os_detections[0]  # First detection
        alert_count += 1
        alert = create_alert(
            level=AlertLevel.NOWCAST_CONFIRMED,
            timestamp=det.timestamp,
            trigger_source='hel1os',
            event_id=event_id,
            alert_count=alert_count,
            provisional_class="--",
            confidence=0.9 if det.neupert_consistent else 0.6,
            hel1os_flux=det.peak_flux,
            hel1os_sigma=det.sigma_above_baseline,
            neupert_correlation=det.neupert_correlation,
        )
        result.alert_log.add_alert(alert)
        result.stage_timeline.append({
            'stage': 4, 'timestamp': det.timestamp
        })
        result.nowcast_fired = True

    # --- Compute final metrics ---
    result.max_stage_reached = result.alert_log.get_current_stage()
    result.stage3_to_4_gap_s = result.alert_log.stage3_to_4_gap_s

    return result


# =============================================================================
# RUN ON CATALOG EVENTS (SYNTHETIC)
# =============================================================================

def run_on_synthetic_event(event_id: str) -> PipelineResult:
    """
    Generate synthetic data for a catalog event and run the pipeline.

    Parameters
    ----------
    event_id : str
        Event ID from the flare catalog.

    Returns
    -------
    PipelineResult
    """
    from config.flare_catalog import get_event_by_id
    from datetime import timedelta

    event = get_event_by_id(event_id)
    if event is None:
        raise ValueError(f"Unknown event: {event_id}")

    # Parse peak class for synthetic generation
    peak_class = event.peak_class
    if peak_class in ("X-class", "Multi-X"):
        peak_class = "X2.0"

    # Place flare midway through the event window
    window_days = (event.window_end - event.window_start).days
    from datetime import datetime
    flare_start = datetime.combine(event.window_start, datetime.min.time()) + \
                  timedelta(days=window_days // 2, hours=12)

    data = generate_flare_event(
        peak_class=peak_class,
        start_time=flare_start,
        preflare_duration_s=480,
        impulsive_duration_s=90,
        gradual_decay_s=1500,
        quiet_before_s=1800,
        quiet_after_s=1200,
    )

    return run_pipeline(
        solexs_df=data['solexs'],
        hel1os_df=data['hel1os'],
        event_id=event_id,
        save_processed=True,
    )


def run_on_real_event(
    event_id: str,
    data_dir: Optional[str] = None,
) -> PipelineResult:
    """
    Run the pipeline on REAL PRADAN data for one catalog event.

    Loads only the event's time window out of the prepared raw folder
    (out-of-core, via the datastore), then runs the same four-stage pipeline as
    the synthetic path. Requires the folder to have been prepared first
    (datastore.prepare_batch / `python main.py --prepare DIR`).

    Parameters
    ----------
    event_id : str
        Catalog event id whose date window selects the data to read.
    data_dir : str, optional
        Raw folder. Defaults to the currently-prepared active batch.

    Returns
    -------
    PipelineResult — empty (no alerts) if no real data overlaps the window.
    """
    from core.ingest import load_event_data
    from core.datastore import get_active_data_dir

    if data_dir is None:
        active = get_active_data_dir()
        data_dir = str(active) if active else None

    data = load_event_data(event_id, data_dir)
    solexs_df, hel1os_df = data['solexs'], data['hel1os']

    if len(solexs_df) == 0 or len(hel1os_df) == 0:
        logger.warning(
            f"  No real data found for {event_id} in {data_dir}. "
            f"Check the folder was prepared and covers this event's dates."
        )
        return PipelineResult(event_id=event_id)

    return run_pipeline(
        solexs_df=solexs_df,
        hel1os_df=hel1os_df,
        event_id=event_id,
        save_processed=True,
    )


def run_all_events() -> Dict[str, PipelineResult]:
    """
    Run the pipeline on all 6 catalog events (synthetic data).

    Returns
    -------
    dict
        {event_id: PipelineResult}
    """
    results = {}

    for event in get_all_events():
        logger.info(f"\n{'='*60}")
        logger.info(f"  Event: {event.event_id} ({event.peak_class}) — {event.tier}")
        logger.info(f"{'='*60}")

        try:
            result = run_on_synthetic_event(event.event_id)
            results[event.event_id] = result
        except Exception as e:
            logger.error(f"  Error processing {event.event_id}: {e}")

    return results
