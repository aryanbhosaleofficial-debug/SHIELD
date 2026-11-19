# =============================================================================
# S.H.I.E.L.D. Core Engine — Main Entry Point
# Solar Hazard Interception & Extra-orbital Logistics Dashboard
#
# Team Suryastra · Bharatiya Antariksh Hackathon 2026 · Challenge #15
#
# An automated pipeline that reads Aditya-L1's soft X-ray (SoLEXS) and hard
# X-ray (HEL1OS) time-series, anticipates a flare from the steepening soft
# X-ray derivative, and confirms it from the hard X-ray impulsive spike.
# =============================================================================
"""
S.H.I.E.L.D. Core Engine
=========================

Usage:
    python main.py --event MAY2024_X87       Run pipeline on a specific flare event
    python main.py --all                     Run pipeline on all 6 validation events
    python main.py --validate                Run full validation suite
    python main.py --dashboard               Launch the Plotly dashboard
"""

import argparse
import sys
from pathlib import Path

# Ensure project root is on the path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import PROJECT_ROOT as PROJ_ROOT, STAGES
from config.flare_catalog import FLARE_CATALOG, get_event_by_id, get_all_events


def print_banner():
    """Display the S.H.I.E.L.D. startup banner."""
    banner = """
    +===============================================================+
    |                                                               |
    |   S.H.I.E.L.D. CORE ENGINE                                   |
    |                                                               |
    |   Solar Hazard Interception &                                 |
    |   Extra-orbital Logistics Dashboard                           |
    |                                                               |
    |   SoLEXS Forecasting  +  HEL1OS Nowcasting Engine            |
    |                                                               |
    |   Team Suryastra  -  Challenge #15                            |
    |   Bharatiya Antariksh Hackathon 2026                          |
    |                                                               |
    +===============================================================+
    """
    print(banner)


def print_catalog():
    """Print the flare event catalog."""
    print("\n  [CATALOG] Flare Event Catalog")
    print("  " + "=" * 60)
    for event in get_all_events():
        tier_icon = {"CRITICAL": "[!!!]", "TIER 1": "[!!]", "TIER 2": "[!]"}.get(event.tier, "[ ]")
        print(f"  {tier_icon} {event.event_id:<20} {event.peak_class:<10} {event.tier}")
        print(f"       {event.window_start.strftime('%Y-%m-%d')} -> "
              f"{event.window_end.strftime('%Y-%m-%d')}  |  {event.active_region}")
    print()


def main():
    """Main entry point for the S.H.I.E.L.D. Core Engine."""
    parser = argparse.ArgumentParser(
        description="S.H.I.E.L.D. Core Engine — Solar Flare Forecasting & Nowcasting",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--event", type=str,
        help="Run pipeline on a specific flare event (e.g., MAY2024_X87)",
    )
    group.add_argument(
        "--all", action="store_true",
        help="Run pipeline on all 6 validation events",
    )
    group.add_argument(
        "--validate", action="store_true",
        help="Run full validation suite with metrics",
    )
    group.add_argument(
        "--dashboard", action="store_true",
        help="Launch the interactive Plotly dashboard",
    )
    group.add_argument(
        "--catalog", action="store_true",
        help="Print the flare event catalog",
    )
    group.add_argument(
        "--prepare", type=str, metavar="DIR",
        help="Index a fresh raw-data folder (run this after swapping in new data, "
             "e.g. --prepare E:\\pradan_batch2)",
    )
    group.add_argument(
        "--make-demo", type=str, metavar="EVENT",
        help="Build a demo bundle from the prepared real data for an event "
             "(e.g. --make-demo FEB2024_X63) -> outputs/demo_<event>/",
    )
    group.add_argument(
        "--scan", action="store_true",
        help="Continuously scan the prepared archive for ALL flares "
             "(use --from/--to to set the range; defaults to 2024-01-01..today)",
    )
    parser.add_argument("--from", dest="scan_from", type=str, default="2024-01-01",
                        help="Scan start date (YYYY-MM-DD). Default 2024-01-01.")
    parser.add_argument("--to", dest="scan_to", type=str, default=None,
                        help="Scan end date (YYYY-MM-DD). Default today.")

    args = parser.parse_args()
    print_banner()

    if args.catalog:
        print_catalog()
        return

    if args.prepare:
        print(f"  [PREPARE] Indexing new data batch: {args.prepare}")
        from core.datastore import prepare_batch
        try:
            summary = prepare_batch(args.prepare)
        except FileNotFoundError as e:
            print(f"  [ERROR] {e}")
            sys.exit(1)
        print(f"  [OK] Indexed {summary['files_indexed']} files "
              f"({summary['manifest_entries']} time-spans).")
        print(f"       Parquet store built: {summary['parquet_built']}")
        print(f"  [NEXT] Process events with real data, e.g.:")
        print(f"         python main.py --event MAY2024_X87   (reads the indexed batch)")
        return

    if args.scan:
        import datetime as _dt
        scan_to = args.scan_to or _dt.date.today().isoformat()
        print(f"  [SCAN] Sweeping {args.scan_from} -> {scan_to} for all flares...")
        from core.datastore import get_active_data_dir
        if get_active_data_dir() is None:
            print("  [ERROR] No prepared data. Run 'python main.py --prepare <folder>' first.")
            sys.exit(1)
        from core.scan import scan_continuous
        res = scan_continuous(args.scan_from, scan_to)
        print(f"  [DONE] {res['flares_detected']} flares over {res['days_scanned']} days")
        print(f"         False alarms: {res['false_alarms_per_24h']} per 24h "
              f"(PRD target < 1)")
        if res.get('mean_gap_min') is not None:
            print(f"         Mean forecast lead: {res['mean_gap_min']} min")
        print(f"         Full list: {res.get('csv', 'outputs/scan_results.csv')}")
        return

    if args.make_demo:
        print(f"  [DEMO] Building demo bundle from data for: {args.make_demo}")
        from make_demo import make_demo
        try:
            out = make_demo(args.make_demo)
        except ValueError as e:
            print(f"  [ERROR] {e}")
            sys.exit(1)
        print(f"  [OK] Demo bundle written to: {out}")
        return

    if args.event:
        event = get_event_by_id(args.event)
        if event is None:
            print(f"  [ERROR] Unknown event: {args.event}")
            print(f"  Available events: {[e.event_id for e in FLARE_CATALOG]}")
            sys.exit(1)
        print(f"  [TARGET] Running pipeline on: {event.event_id} ({event.peak_class})")
        from core.datastore import get_active_data_dir
        active = get_active_data_dir()
        if active is not None:
            print(f"  [DATA] Using prepared real data from: {active}")
            from core.pipeline import run_on_real_event
            result = run_on_real_event(event.event_id, str(active))
            if not result.alert_log.alerts:
                print("  [WARN] No real data overlapped this event's dates - "
                      "falling back to synthetic so you still see output.")
                from core.pipeline import run_on_synthetic_event
                result = run_on_synthetic_event(event.event_id)
        else:
            print("  [DATA] No prepared batch found - using synthetic data. "
                  "Run 'python main.py --prepare <folder>' to use real data.")
            from core.pipeline import run_on_synthetic_event
            result = run_on_synthetic_event(event.event_id)
        result.print_report()
        return

    if args.all:
        print("  [ALL] Running pipeline on all 6 validation events...")
        from core.validator import run_validation
        report = run_validation()
        report.print_report()
        return

    if args.validate:
        print("  [VALIDATE] Running full validation suite...")
        from core.validator import run_validation
        report = run_validation()
        report.print_report()
        return

    if args.dashboard:
        print("  [DASHBOARD] Exporting pipeline data for the dashboard...")
        from dashboard_export import export_dashboard_data
        out = export_dashboard_data()
        print(f"  [OK] Dashboard data written to: {out}")
        print(f"  [NEXT] cd dashboard && npm install && npm run dev")
        return

    # Default: print catalog and usage
    print_catalog()
    parser.print_help()


if __name__ == "__main__":
    main()
