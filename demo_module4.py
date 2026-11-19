# =============================================================================
# S.H.I.E.L.D. Module 4 — Pipeline & Validation Demo
# Runs the full four-stage pipeline on a synthetic X8.7 flare,
# then runs the validation suite across all 6 catalog events.
#
# Usage: python demo_module4.py
# =============================================================================

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.pipeline import run_on_synthetic_event, run_pipeline
from core.validator import run_validation
from core.synthetic import generate_flare_event

logging.basicConfig(level=logging.INFO, format='  %(message)s')


def main():
    print()
    print("  +===============================================================+")
    print("  |   S.H.I.E.L.D. MODULE 4 DEMO                                 |")
    print("  |   Four-Stage Detection Pipeline & Validation                  |")
    print("  +===============================================================+")

    # ---- Part 1: Single Event Pipeline ----
    print()
    print("  " + "=" * 60)
    print("  PART 1: Single Event — May 2024 X8.7 (CRITICAL)")
    print("  " + "=" * 60)

    result = run_on_synthetic_event("MAY2024_X87")
    result.print_report()

    # ---- Part 2: Full Validation Suite ----
    print()
    print("  " + "=" * 60)
    print("  PART 2: Full Validation Suite — All 6 Events")
    print("  " + "=" * 60)

    report = run_validation()
    report.print_report()

    # Export results
    df = report.to_dataframe()
    output_path = Path("outputs/validation_results.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"  Results exported to: {output_path}")

    print()
    print("  +===============================================================+")
    print("  |   MODULE 4 DEMO COMPLETE                                      |")
    print("  |   Four-stage pipeline and validation verified.                |")
    print("  +===============================================================+")
    print()


if __name__ == "__main__":
    main()
