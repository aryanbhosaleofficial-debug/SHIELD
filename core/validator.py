# =============================================================================
# S.H.I.E.L.D. Core Engine — Validation Suite
# Runs the pipeline on all 6 catalog events and computes validation metrics.
#
# Three tiers of evidence (from PRD):
#   1. PRIMARY   — May 2024 X8.7: measure Stage 3->4 gap
#   2. SECONDARY — Feb 2024 X6.3: cross-validate onset timing
#   3. MULTI     — All 6 events: robustness + false-positive rate
# =============================================================================

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from config.flare_catalog import get_all_events, FlareEvent
from config.settings import MAX_FALSE_POSITIVES_PER_24H, ONSET_TIMING_TOLERANCE_S
from core.pipeline import run_all_events, run_on_synthetic_event, PipelineResult

logger = logging.getLogger(__name__)


# =============================================================================
# VALIDATION METRICS
# =============================================================================

class ValidationReport:
    """Comprehensive validation results across all events."""

    def __init__(self):
        self.event_results: Dict[str, PipelineResult] = {}
        self.gaps: Dict[str, Optional[float]] = {}
        self.forecast_success: Dict[str, bool] = {}
        self.nowcast_success: Dict[str, bool] = {}

        # Aggregate metrics
        self.total_events: int = 0
        self.forecast_rate: float = 0.0
        self.nowcast_rate: float = 0.0
        self.mean_gap_s: Optional[float] = None
        self.std_gap_s: Optional[float] = None

        # Quiet-Sun false-positive measurement (None until run)
        self.false_positives_24h: Optional[int] = None

    def add_result(self, event_id: str, result: PipelineResult):
        """Add a pipeline result to the validation report."""
        self.event_results[event_id] = result
        self.gaps[event_id] = result.stage3_to_4_gap_s
        self.forecast_success[event_id] = result.forecast_fired
        self.nowcast_success[event_id] = result.nowcast_fired
        self.total_events += 1

    def compute_aggregate_metrics(self):
        """Compute summary statistics across all events."""
        if self.total_events == 0:
            return

        self.forecast_rate = sum(self.forecast_success.values()) / self.total_events
        self.nowcast_rate = sum(self.nowcast_success.values()) / self.total_events

        valid_gaps = [g for g in self.gaps.values() if g is not None]
        if valid_gaps:
            self.mean_gap_s = np.mean(valid_gaps)
            self.std_gap_s = np.std(valid_gaps) if len(valid_gaps) > 1 else 0.0

    def print_report(self):
        """Print the full validation report."""
        self.compute_aggregate_metrics()

        print()
        print("  +===============================================================+")
        print("  |   S.H.I.E.L.D. VALIDATION REPORT                             |")
        print("  |   Multi-Event Analysis                                        |")
        print("  +===============================================================+")
        print()

        # Per-event results table
        print("  Per-Event Results:")
        print("  " + "-" * 70)
        print(f"  {'Event':<20} {'Class':<8} {'Tier':<10} {'Forecast':<10} "
              f"{'Nowcast':<10} {'Gap (s)':<10}")
        print("  " + "-" * 70)

        for event in get_all_events():
            eid = event.event_id
            if eid not in self.event_results:
                continue

            r = self.event_results[eid]
            forecast = "YES" if r.forecast_fired else "NO"
            nowcast = "YES" if r.nowcast_fired else "NO"
            gap_str = f"{r.stage3_to_4_gap_s:.1f}" if r.stage3_to_4_gap_s is not None else "--"

            print(f"  {eid:<20} {event.peak_class:<8} {event.tier:<10} "
                  f"{forecast:<10} {nowcast:<10} {gap_str:<10}")

        print("  " + "-" * 70)
        print()

        # Aggregate metrics
        print("  Aggregate Metrics:")
        print(f"    Events processed   : {self.total_events}")
        print(f"    Forecast rate      : {self.forecast_rate*100:.0f}% "
              f"({sum(self.forecast_success.values())}/{self.total_events})")
        print(f"    Nowcast rate        : {self.nowcast_rate*100:.0f}% "
              f"({sum(self.nowcast_success.values())}/{self.total_events})")

        if self.mean_gap_s is not None:
            print(f"    Mean Stage 3->4 gap: {self.mean_gap_s:.1f}s "
                  f"(+/- {self.std_gap_s:.1f}s)")
            print(f"                       : {self.mean_gap_s/60:.1f} min "
                  f"(+/- {self.std_gap_s/60:.1f} min)")
        else:
            print(f"    Mean Stage 3->4 gap: -- (no valid gaps)")

        # Validation targets from PRD
        print()
        print("  Validation Targets (from PRD):")
        print("  " + "-" * 55)

        # Target 1: Forecast before peak on X8.7
        x87 = self.event_results.get("MAY2024_X87")
        if x87:
            status = "PASS" if x87.forecast_fired else "FAIL"
            print(f"    [{status}] Forecast-before-peak on X8.7")

        # Target 2: Stage 3->4 gap measured
        gaps_measured = sum(1 for g in self.gaps.values() if g is not None)
        print(f"    [{'PASS' if gaps_measured > 0 else 'FAIL'}] "
              f"Stage 3->4 gap measured ({gaps_measured}/{self.total_events} events)")

        # Target 3: False-positive rate (measured on 24h of quiet Sun)
        if self.false_positives_24h is not None:
            fp_ok = self.false_positives_24h <= MAX_FALSE_POSITIVES_PER_24H
            print(f"    [{'PASS' if fp_ok else 'FAIL'}] False-positive rate: "
                  f"{self.false_positives_24h} forecast alert(s) in 24h quiet Sun "
                  f"(target <= {MAX_FALSE_POSITIVES_PER_24H})")
        else:
            print(f"    [INFO] False-positive analysis not run")

        print()
        print("  " + "=" * 60)

    def to_dataframe(self) -> pd.DataFrame:
        """Export results as a DataFrame."""
        rows = []
        for event in get_all_events():
            eid = event.event_id
            if eid not in self.event_results:
                continue
            r = self.event_results[eid]
            rows.append({
                'event_id': eid,
                'peak_class': event.peak_class,
                'tier': event.tier,
                'forecast_fired': r.forecast_fired,
                'nowcast_fired': r.nowcast_fired,
                'stage3_to_4_gap_s': r.stage3_to_4_gap_s,
                'max_stage': r.max_stage_reached,
            })
        return pd.DataFrame(rows)


# =============================================================================
# VALIDATION RUNNER
# =============================================================================

def measure_false_positives(duration_s: int = 24 * 3600) -> int:
    """
    Measure the forecast false-positive count on synthetic quiet-Sun data.

    Runs the physics engine on `duration_s` seconds of quiet Sun (no flare) and
    counts how many FORECAST alerts fire. The PRD target is <= 1 per 24h.
    """
    from core.synthetic import generate_quiet_sun
    from core.preprocess import align_timeseries, clean_flux_data
    from core.physics_engine import run_physics_engine

    quiet = generate_quiet_sun(duration_s=duration_s, cadence_s=1)
    aligned = align_timeseries(quiet['solexs'], quiet['hel1os'])
    cleaned = clean_flux_data(aligned)
    result = run_physics_engine(cleaned, auto_calibrate=True)
    return len(result.solexs_detections)


def run_validation(measure_fp: bool = True, export: bool = True) -> ValidationReport:
    """
    Run the complete validation suite on all 6 catalog events.

    Parameters
    ----------
    measure_fp : bool
        Also measure the quiet-Sun false-positive rate (24h).
    export : bool
        Write the per-event results to outputs/validation_results.csv.

    Returns
    -------
    ValidationReport
        Comprehensive validation results.
    """
    report = ValidationReport()

    logger.info("\n" + "=" * 60)
    logger.info("  S.H.I.E.L.D. VALIDATION SUITE")
    logger.info("  Running pipeline on all 6 catalog events...")
    logger.info("=" * 60)

    all_results = run_all_events()

    for event_id, result in all_results.items():
        report.add_result(event_id, result)

    if measure_fp:
        logger.info("\n  Measuring false-positive rate on 24h quiet Sun...")
        try:
            report.false_positives_24h = measure_false_positives()
        except Exception as e:
            logger.warning(f"  False-positive measurement failed: {e}")

    if export:
        from config.settings import OUTPUT_DIR
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out_path = OUTPUT_DIR / "validation_results.csv"
        report.to_dataframe().to_csv(out_path, index=False)
        logger.info(f"  Validation results exported to: {out_path}")

    return report


def run_primary_validation() -> PipelineResult:
    """
    Run PRIMARY validation: May 2024 X8.7 flare only.
    This is the single most important validation target.
    """
    logger.info("\n  PRIMARY VALIDATION: May 2024 X8.7 flare")
    return run_on_synthetic_event("MAY2024_X87")
