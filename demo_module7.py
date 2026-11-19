# =============================================================================
# S.H.I.E.L.D. Module 7 — Dashboard Data Demo
# Runs the real pipeline on all 6 events and exports the JSON the Next.js
# dashboard reads. This is the Python side of Module 7; the front-end lives in
# dashboard/ and is launched separately with npm.
#
# Usage:
#   python demo_module7.py            # generates dashboard/public/shield_data.json
#   cd dashboard && npm install && npm run dev   # then open http://localhost:3000
# =============================================================================

import sys
import json
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dashboard_export import export_dashboard_data

logging.basicConfig(level=logging.INFO, format='  %(message)s')


def main():
    print()
    print("  +===============================================================+")
    print("  |   S.H.I.E.L.D. MODULE 7 DEMO                                 |")
    print("  |   Dashboard data export (real pipeline -> JSON)              |")
    print("  +===============================================================+")
    print()

    out = export_dashboard_data()
    data = json.loads(out.read_text())

    print()
    print(f"  Exported {len(data['events'])} events to:")
    print(f"    {out}")
    print()
    print("  Summary (real pipeline output):")
    s = data['summary']
    print(f"    Forecast rate    : {s['forecast_rate']*100:.0f}%")
    print(f"    Nowcast rate     : {s['nowcast_rate']*100:.0f}%")
    print(f"    Mean Stage3->4   : {s['mean_gap_s']}s ({s['mean_gap_min']} min)")
    print()
    print("  Per-event lead time (forecast before nowcast):")
    for e in data['events']:
        gap = e['gap_s']
        gmin = f"{gap/60:.1f} min" if gap is not None else "--"
        print(f"    {e['event_id']:<16}{e['peak_class']:<10}{gmin}")
    print()
    print("  Next step: launch the front-end")
    print("    cd dashboard && npm install && npm run dev")
    print("    then open http://localhost:3000")
    print()
    print("  +===============================================================+")
    print("  |   MODULE 7 DEMO COMPLETE                                      |")
    print("  +===============================================================+")
    print()


if __name__ == "__main__":
    main()
