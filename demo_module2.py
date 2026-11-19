# =============================================================================
# S.H.I.E.L.D. Module 2 — Data Ingestion Demo
# Generates synthetic flare data and runs the full preprocessing pipeline.
# Run this to verify Module 2 is working.
#
# Usage: python demo_module2.py
# =============================================================================

import sys
import logging
from pathlib import Path

# Setup project root
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import PROCESSED_DATA_DIR
from core.synthetic import generate_flare_event
from core.preprocess import preprocess_event

# Setup logging so you can see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='  %(message)s',
)


def main():
    print()
    print("  +===============================================================+")
    print("  |   S.H.I.E.L.D. MODULE 2 DEMO — Data Ingestion Pipeline       |")
    print("  +===============================================================+")
    print()

    # ---- Step 1: Generate synthetic X8.7 flare data ----
    print("  [STEP 1] Generating synthetic X8.7 flare (May 2024)...")
    print("           Physics: Neupert effect — SoLEXS heats first,")
    print("           HEL1OS spike follows at magnetic reconnection.")
    print()

    data = generate_flare_event(
        peak_class="X8.7",
        preflare_duration_s=480,    # 8 min pre-flare heating
        impulsive_duration_s=90,    # 90 sec impulsive phase
        gradual_decay_s=1500,       # 25 min gradual decay
        quiet_before_s=1800,        # 30 min quiet baseline
        quiet_after_s=1200,         # 20 min quiet after
        neupert_lag_s=45,           # 45s Neupert lag
    )

    solexs_df = data['solexs']
    hel1os_df = data['hel1os']
    meta = data['metadata']

    print()
    print("  --- Synthetic Data Summary ---")
    print(f"  SoLEXS: {len(solexs_df)} data points")
    print(f"    Time range : {solexs_df['timestamp'].iloc[0]} -> {solexs_df['timestamp'].iloc[-1]}")
    print(f"    Flux range : {solexs_df['flux'].min():.2e} -> {solexs_df['flux'].max():.2e} W/m2")
    print()
    print(f"  HEL1OS: {len(hel1os_df)} data points")
    print(f"    Time range : {hel1os_df['timestamp'].iloc[0]} -> {hel1os_df['timestamp'].iloc[-1]}")
    print(f"    Flux range : {hel1os_df['flux'].min():.2e} -> {hel1os_df['flux'].max():.2e}")
    print()
    print(f"  Flare Timing:")
    print(f"    Pre-flare start  : {meta['preflare_start']}")
    print(f"    Impulsive start  : {meta['impulsive_start']}")
    print(f"    Peak time        : {meta['peak_time']}")
    print(f"    Neupert lag      : {meta['neupert_lag_s']}s")
    print()

    # ---- Step 2: Run preprocessing pipeline ----
    print("  [STEP 2] Running preprocessing pipeline...")
    print("           - Aligning SoLEXS + HEL1OS on common time axis (merge_asof)")
    print("           - Cleaning: removing negatives, outliers, interpolating gaps")
    print("           - Saving processed data to disk")
    print()

    processed = preprocess_event(
        solexs_df=solexs_df,
        hel1os_df=hel1os_df,
        event_id="MAY2024_X87_synthetic",
        save=True,
    )

    print()
    print("  --- Processed Data Summary ---")
    print(f"  Total rows    : {len(processed)}")
    print(f"  Columns       : {list(processed.columns)}")
    print(f"  Time range    : {processed['timestamp'].iloc[0]} -> {processed['timestamp'].iloc[-1]}")
    print(f"  SoLEXS valid  : {processed['solexs_valid'].sum()}/{len(processed)} "
          f"({processed['solexs_valid'].mean()*100:.1f}%)")
    print(f"  HEL1OS valid  : {processed['hel1os_valid'].sum()}/{len(processed)} "
          f"({processed['hel1os_valid'].mean()*100:.1f}%)")
    print()

    # ---- Step 3: Show a data sample ----
    print("  --- Sample Data (around impulsive phase) ---")
    # Find the peak flux region
    peak_idx = processed['solexs_flux'].idxmax()
    start_show = max(0, peak_idx - 5)
    end_show = min(len(processed), peak_idx + 6)
    sample = processed.iloc[start_show:end_show][
        ['timestamp', 'solexs_flux', 'hel1os_flux']
    ]
    print(sample.to_string(index=False))
    print()

    # ---- Step 4: Verify output file ----
    output_file = PROCESSED_DATA_DIR / "MAY2024_X87_synthetic_processed.csv"
    if output_file.exists():
        size_kb = output_file.stat().st_size / 1024
        print(f"  [OK] Output saved: {output_file}")
        print(f"       File size: {size_kb:.1f} KB")
    else:
        print(f"  [ERROR] Output file not found!")

    print()
    print("  +===============================================================+")
    print("  |   MODULE 2 DEMO COMPLETE                                      |")
    print("  |   Data ingestion and preprocessing pipeline verified.          |")
    print("  +===============================================================+")
    print()


if __name__ == "__main__":
    main()
