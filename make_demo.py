# =============================================================================
# S.H.I.E.L.D. — Demo Generator From Real Data
# Runs EVERY module on a real (prepared) event and writes a folder of
# demonstration files built from THAT data — so the demos reflect your actual
# fed data instead of synthetic test data.
#
# Usage:
#   python main.py --prepare E:\feb2024_folder     # index your real data first
#   python make_demo.py FEB2024_X63                 # build demos from it
#   # -> outputs/demo_FEB2024_X63/  (reports + CSVs + dashboard JSON)
#
# If no real batch is prepared, it falls back to synthetic data so you can see
# the format now. Each module is isolated: if one step has no data, the others
# still produce their files.
# =============================================================================

import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from config.settings import OUTPUT_DIR
from config.flare_catalog import get_event_by_id

logger = logging.getLogger(__name__)


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")
    logger.info(f"  wrote {path.name}")


def make_demo(event_id: str, prefer_real: bool = True) -> Path:
    """
    Build a demonstration bundle for one event from real prepared data
    (or synthetic if none is prepared). Returns the output folder path.
    """
    event = get_event_by_id(event_id)
    if event is None:
        raise ValueError(f"Unknown event '{event_id}'. "
                         f"Run 'python main.py --catalog' to see valid ids.")

    # --- Pick the data source: real (prepared) or synthetic fallback ---
    from core.datastore import get_active_data_dir
    from core.pipeline import run_on_real_event, run_on_synthetic_event

    source = "synthetic"
    result = None
    active = get_active_data_dir() if prefer_real else None
    if active is not None:
        logger.info(f"  Using REAL prepared data: {active}")
        result = run_on_real_event(event_id, str(active))
        if result.alert_log.alerts:
            source = f"real ({active})"
        else:
            logger.warning("  Real data produced no detections — using synthetic fallback.")
            result = None
    if result is None:
        result = run_on_synthetic_event(event_id)

    out_dir = OUTPUT_DIR / f"demo_{event_id}"
    out_dir.mkdir(parents=True, exist_ok=True)

    df = result.processed_df
    physics = result.physics_result

    # --- 00 summary ---
    gap = result.stage3_to_4_gap_s
    summary = [
        "S.H.I.E.L.D. — DEMO BUNDLE",
        "=" * 50,
        f"Event        : {event_id} ({event.peak_class})",
        f"Active region: {event.active_region}",
        f"Data source  : {source}",
        f"Generated    : {datetime.utcnow().isoformat()}Z",
        "",
        f"Forecast fired : {result.forecast_fired}",
        f"Nowcast fired  : {result.nowcast_fired}",
        f"Max stage      : {result.max_stage_reached}",
        f"Stage 3->4 gap : {f'{gap:.1f}s ({gap/60:.1f} min)' if gap is not None else 'n/a'}",
        "",
        "Files in this bundle:",
        "  01_ingestion.txt   - Module 2: data loaded & cleaned",
        "  02_physics.txt     - Module 3: derivative / sigma detections",
        "  03_pipeline.txt    - Module 4: four-stage timeline + alerts",
        "  04_features.csv    - Module 5: physics features (no AI)",
        "  05_activity_forecast.txt - Layer A: Poisson activity probability",
        "  06_impact.txt      - impact assessment + safety advisories",
        "  07_spectral.txt    - spectral diagnostics (temperature etc.)",
        "  light_curve.csv    - the processed light curves",
        "  event_data.json    - dashboard-ready JSON for this event",
    ]
    _write(out_dir / "00_summary.txt", "\n".join(summary))

    # --- 01 ingestion (Module 2) ---
    try:
        n = len(df)
        dur = (df['timestamp'].iloc[-1] - df['timestamp'].iloc[0]).total_seconds()
        sol_nan = df['solexs_flux'].isna().mean() * 100 if 'solexs_flux' in df else 100
        hel_nan = df['hel1os_flux'].isna().mean() * 100 if 'hel1os_flux' in df else 100
        txt = [
            "MODULE 2 — DATA INGESTION & PREPROCESSING",
            "-" * 45,
            f"Rows (1s cadence) : {n}",
            f"Time range        : {df['timestamp'].iloc[0]} -> {df['timestamp'].iloc[-1]}",
            f"Duration          : {dur:.0f} s ({dur/3600:.2f} h)",
            f"SoLEXS missing    : {sol_nan:.2f}%",
            f"HEL1OS missing    : {hel_nan:.2f}%",
        ]
        _write(out_dir / "01_ingestion.txt", "\n".join(txt))
    except Exception as e:
        _write(out_dir / "01_ingestion.txt", f"ingestion summary failed: {e}")

    # --- 02 physics (Module 3) ---
    try:
        pdf = physics.df
        txt = [
            "MODULE 3 — LAYER 1 PHYSICS ENGINE",
            "-" * 45,
            f"Peak SoLEXS derivative : {pdf['solexs_derivative'].max():.3e}",
            f"Peak HEL1OS sigma      : {pdf['hel1os_sigma'].max():.2f}" if 'hel1os_sigma' in pdf else "",
            f"SoLEXS forecast detections : {len(physics.solexs_detections)}",
            f"HEL1OS nowcast detections  : {len(physics.hel1os_detections)}",
            f"First FORECAST : {physics.first_forecast_alert}",
            f"First NOWCAST  : {physics.first_nowcast_confirmed}",
        ]
        _write(out_dir / "02_physics.txt", "\n".join(t for t in txt if t))
    except Exception as e:
        _write(out_dir / "02_physics.txt", f"physics summary failed: {e}")

    # --- 03 pipeline (Module 4) ---
    try:
        lines = ["MODULE 4 — FOUR-STAGE DETECTION PIPELINE", "-" * 45, "Stage timeline:"]
        for s in result.stage_timeline:
            lines.append(f"  Stage {s['stage']} @ {s['timestamp']}")
        lines.append("")
        lines.append("Alerts:")
        for a in result.alert_log.alerts:
            lines.append(f"  [{a.status}] {a.timestamp} conf={a.confidence:.2f} src={a.trigger_source}")
        _write(out_dir / "03_pipeline.txt", "\n".join(lines))
    except Exception as e:
        _write(out_dir / "03_pipeline.txt", f"pipeline summary failed: {e}")

    # --- 04 features (Module 5) ---
    try:
        from ml.features import extract_features
        feats = extract_features(df, event_id)
        pd.DataFrame([feats]).to_csv(out_dir / "04_features.csv", index=False)
        logger.info("  wrote 04_features.csv")
    except Exception as e:
        _write(out_dir / "04_features.txt", f"feature extraction failed: {e}")

    # --- 05 Layer A: activity forecast (Poisson, NO AI) ---
    try:
        from core.forecast import event_forecast_summary
        flare_times = [d.timestamp for d in result.physics_result.hel1os_detections]
        fc = event_forecast_summary(flare_times, event.window_start, event.window_end)
        if fc:
            txt = [
                "MODULE 5 — LAYER A ACTIVITY FORECAST (Poisson, no AI)",
                "-" * 45,
                f"Flares in history  : {len(flare_times)}",
                f"Peak P(flare 6h)   : {fc['peak_p_6h']:.2f}",
                f"Peak P(flare 24h)  : {fc['peak_p_24h']:.2f}",
                f"Peak alert level   : {fc['peak_level']}",
                f"Reached at         : {fc['peak_time']}",
                "",
                "Transparent Poisson rate model (recent flare rate -> probability).",
                "Situational awareness only; NOT a skillful per-flare prediction.",
            ]
        else:
            txt = ["MODULE 5 — LAYER A ACTIVITY FORECAST",
                   "No flares in history to estimate an activity rate."]
        _write(out_dir / "05_activity_forecast.txt", "\n".join(txt))
    except Exception as e:
        _write(out_dir / "05_activity_forecast.txt", f"activity forecast skipped: {e}")

    # --- 06 impact assessment + safety advisories (Module: Impact Engine) ---
    try:
        from core.impact import assess_impact, format_impact_report
        sig = max((d.sigma_above_baseline for d in result.physics_result.hel1os_detections),
                  default=0.0)
        assessment = assess_impact(event.peak_class, hel1os_sigma=sig)
        _write(out_dir / "06_impact.txt", format_impact_report(assessment))
    except Exception as e:
        _write(out_dir / "06_impact.txt", f"impact assessment failed: {e}")

    # --- 07 spectral feature extraction (temperature / spectral index / fused) ---
    # Reuses the flares already detected above (no re-scan); reads the heavy
    # per-second spectra only in a window around each flare. Real data only.
    try:
        if source.startswith("real"):
            from core.spectral import extract_flares_spectral
            from core.datastore import get_active_data_dir
            flare_times = [d.timestamp for d in result.physics_result.hel1os_detections]
            if flare_times:
                spec = extract_flares_spectral(
                    event_id, data_dir=str(get_active_data_dir()),
                    flare_times=flare_times, out_dir=out_dir / "spectral",
                )
                lines = ["MODULE 7 — SPECTRAL FEATURE EXTRACTION", "-" * 45,
                         f"Flares extracted : {spec['n_flares']}", ""]
                for fl in spec['flares']:
                    lines.append(f"  {fl.get('flare_time','?')}")
                    lines.append(f"     peak temperature : {fl.get('slx_peak_kt_keV_est', float('nan')):.2f} keV est")
                    lines.append(f"     spectral index   : {fl.get('hls_spectral_index_at_peak', float('nan')):.2f}")
                    lines.append(f"     peak hardness    : {fl.get('peak_hardness_ratio', float('nan')):.2f}")
                    lines.append(f"     xcorr lag (HXR vs dSXR): {fl.get('xcorr_lag_hls_vs_dslx_s')} s")
                lines += ["", "Full per-second feature tables in: spectral/"]
                _write(out_dir / "07_spectral.txt", "\n".join(lines))
            else:
                _write(out_dir / "07_spectral.txt",
                       "MODULE 7 — SPECTRAL\nNo flares detected to extract spectra for.")
        else:
            _write(out_dir / "07_spectral.txt",
                   "MODULE 7 — SPECTRAL\nSkipped (needs real prepared data; synthetic run).")
    except Exception as e:
        _write(out_dir / "07_spectral.txt", f"spectral extraction skipped: {e}")

    # --- light curve CSV + per-event JSON ---
    try:
        cols = [c for c in ['timestamp', 'solexs_flux', 'hel1os_flux',
                            'solexs_derivative', 'hel1os_sigma'] if c in physics.df.columns]
        physics.df[cols].to_csv(out_dir / "light_curve.csv", index=False)
        logger.info("  wrote light_curve.csv")
    except Exception as e:
        logger.warning(f"  light_curve.csv failed: {e}")

    try:
        event_json = {
            'event_id': event_id,
            'peak_class': event.peak_class,
            'source': source,
            'gap_s': round(float(gap), 1) if gap is not None else None,
            'stages': [{'stage': s['stage'], 'time': str(s['timestamp'])}
                       for s in result.stage_timeline],
        }
        (out_dir / "event_data.json").write_text(json.dumps(event_json, indent=2))
        logger.info("  wrote event_data.json")
    except Exception as e:
        logger.warning(f"  event_data.json failed: {e}")

    logger.info(f"Demo bundle ready: {out_dir}")
    return out_dir


def main():
    logging.basicConfig(level=logging.INFO, format='  %(message)s')
    event_id = sys.argv[1] if len(sys.argv) > 1 else "FEB2024_X63"
    print()
    print("  +===============================================================+")
    print("  |   S.H.I.E.L.D. — DEMO GENERATOR FROM DATA                    |")
    print("  +===============================================================+")
    out = make_demo(event_id)
    print()
    print(f"  Demo bundle written to: {out}")
    for f in sorted(out.iterdir()):
        print(f"    - {f.name}")
    print()


if __name__ == "__main__":
    main()
