# =============================================================================
# S.H.I.E.L.D. Module 3 — Layer 1 Physics Engine Demo
# Generates a synthetic X8.7 flare, preprocesses it, and runs the full
# physics engine to detect FORECAST ALERT and NOWCAST CONFIRMED.
#
# This demonstrates the CORE DELIVERABLE: measuring the Stage 3 -> Stage 4 gap.
#
# Usage: python demo_module3.py
# =============================================================================

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.synthetic import generate_flare_event
from core.preprocess import preprocess_event
from core.physics_engine import run_physics_engine

logging.basicConfig(level=logging.INFO, format='  %(message)s')


def main():
    print()
    print("  +===============================================================+")
    print("  |   S.H.I.E.L.D. MODULE 3 DEMO — Layer 1 Physics Engine        |")
    print("  |   Zero-training, deterministic flare detection                |")
    print("  +===============================================================+")
    print()

    # ---- Step 1: Generate synthetic X8.7 flare ----
    print("  [STEP 1] Generating synthetic X8.7 flare...")
    data = generate_flare_event(
        peak_class="X8.7",
        preflare_duration_s=480,
        impulsive_duration_s=90,
        gradual_decay_s=1500,
        quiet_before_s=1800,
        quiet_after_s=1200,
        neupert_lag_s=45,
    )
    meta = data['metadata']
    print(f"    Ground truth:")
    print(f"      Pre-flare start  : {meta['preflare_start']}")
    print(f"      Impulsive start  : {meta['impulsive_start']}")
    print(f"      Neupert lag      : {meta['neupert_lag_s']}s")
    print()

    # ---- Step 2: Preprocess ----
    print("  [STEP 2] Preprocessing (align + clean)...")
    processed = preprocess_event(
        data['solexs'], data['hel1os'],
        event_id="MODULE3_DEMO",
        save=False,
    )
    print()

    # ---- Step 3: Run Physics Engine ----
    print("  [STEP 3] Running Layer 1 Physics Engine...")
    print()
    result = run_physics_engine(processed, auto_calibrate=True)

    # ---- Summary ----
    print()
    print("  +===============================================================+")
    print("  |   DETECTION SUMMARY                                           |")
    print("  +===============================================================+")
    print()
    print(f"  FORECAST ALERTs (SoLEXS):  {len(result.solexs_detections)}")
    for d in result.solexs_detections:
        print(f"    - {d.timestamp} | deriv={d.derivative:.2e} | "
              f"class~{d.provisional_class} | conf={d.confidence:.2f}")

    print()
    print(f"  NOWCAST CONFIRMEDs (HEL1OS): {len(result.hel1os_detections)}")
    for d in result.hel1os_detections:
        neupert = "YES" if d.neupert_consistent else "NO"
        print(f"    - {d.timestamp} | sigma={d.sigma_above_baseline:.1f} | "
              f"neupert={neupert} (r={d.neupert_correlation:.2f})")

    print()
    if result.stage3_to_4_gap_s is not None:
        gap = result.stage3_to_4_gap_s
        print(f"  *** CORE RESULT ***")
        print(f"  Stage 3 -> Stage 4 gap: {gap:.1f}s ({gap/60:.1f} minutes)")
        if gap > 0:
            print(f"  FORECAST preceded NOWCAST by {gap:.0f} seconds")
            print(f"  -> The physics engine ANTICIPATED the flare!")
        else:
            print(f"  NOWCAST fired {abs(gap):.0f}s before FORECAST")
    else:
        print("  No Stage 3->4 gap measured (missing detections)")

    print()

    # ---- Compare with ground truth ----
    print("  --- Ground Truth Comparison ---")
    if result.first_forecast_alert and meta['preflare_start']:
        offset = (result.first_forecast_alert - meta['preflare_start']).total_seconds()
        print(f"  Forecast alert fired {offset:.0f}s after true pre-flare start")

    if result.first_nowcast_confirmed and meta['impulsive_start']:
        offset = (result.first_nowcast_confirmed - meta['impulsive_start']).total_seconds()
        print(f"  Nowcast confirmed {offset:.0f}s after true impulsive onset")

    print()
    print("  +===============================================================+")
    print("  |   MODULE 3 DEMO COMPLETE                                      |")
    print("  |   Layer 1 Physics Engine verified.                            |")
    print("  +===============================================================+")
    print()


if __name__ == "__main__":
    main()
