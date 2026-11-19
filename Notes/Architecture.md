---
tags: [architecture, shield]
created: 2026-07-26
---

# Architecture

Up: [[Home]]

## Tech stack
- **Python** core: numpy, pandas, scipy (signal), pyarrow (Parquet), astropy (FITS)
- **ML**: XGBoost (detector/severity), PyTorch (LSTM forecaster) — see [[ML Layer]]
- **Dashboard**: Next.js (App Router) + TypeScript — see [[Dashboard]]
- **Data**: ISRO PRADAN FITS/ZIP telemetry, out-of-core Parquet store

## Project layout (actual, not the README's)

```
SHIELD/
  config/
    settings.py        # all thresholds/constants/paths — see individual notes for values
    flare_catalog.py    # the 6 validation events — see [[Flare Catalog]]
  core/
    ingest.py            # FITS/ZIP reader (PRADAN data)
    datastore.py          # out-of-core: time manifest + Parquet store — see [[Data Pipeline]]
    preprocess.py          # alignment, cleaning, synthetic-aware
    synthetic.py            # synthetic flare generator (demo/test data)
    physics_engine.py        # Layer 1 — see [[Physics Engine]]
    baseline.py                # rolling baseline mean/std for HEL1OS
    pipeline.py                  # four-stage state machine, ties Layer 1 to alerts
    alert.py                      # Alert / AlertLevel / AlertLog
    forecast.py                    # Layer A Poisson model — see [[Activity Forecast]]
    impact.py                       # NOAA R/S/G advisory mapping — see [[Impact Assessment]]
    validator.py                     # runs all 6 catalog events, aggregate metrics
    benchmark.py                      # match vs GOES/SWPC catalog — see [[Validation and Benchmarking]]
    scan.py                            # continuous out-of-core sweep for all flares
    suit.py                             # SUIT UV image features (v2.0) — see [[Extensions]]
    spectral.py                          # SoLEXS/HEL1OS spectral features (v2.0)
  ml/
    features.py        # shared feature engineering
    detector.py          # XGBoost: catches C/M flares the physics engine misses
    severity.py            # XGBoost: classify detected flare into C/M/X
    forecaster.py            # XGBoost: P(M+ flare in next 24h) from recent activity
    lstm_forecaster.py         # PyTorch LSTM version of the same forecast — see [[ML Layer]]
  dashboard/            # Next.js app (App Router) — see [[Dashboard]]
  data/
    raw/                # raw PRADAN FITS/ZIP files (input)
    processed/           # manifest + Parquet store + filtered CSVs (generated)
  outputs/              # pipeline results, plots, metrics, demo bundles
  tests/
  main.py               # CLI entry point
  dashboard_export.py    # pipeline results -> dashboard/public/shield_data.json
  make_demo.py             # builds a demo bundle for one event
  build_prd.py, build_pptx.py, build_report.py, build_submission_pdf.py
                            # submission-artifact generators (PPTX/PDF), not core logic
```

## CLI (`main.py`)

```bash
python main.py --catalog                 # print the flare event catalog
python main.py --event MAY2024_X87        # run pipeline on one event (real data if prepared, else synthetic)
python main.py --all / --validate         # run + validate all 6 catalog events
python main.py --prepare <folder>         # index a raw PRADAN data folder (out-of-core)
python main.py --scan --from Y --to Y     # continuous sweep for all flares over a date range
python main.py --make-demo <EVENT>        # build a demo bundle -> outputs/demo_<event>/
python main.py --dashboard                # export pipeline data -> dashboard/public/shield_data.json
```

`--event` auto-falls-back to synthetic data if no real data has been `--prepare`d or
if the prepared batch doesn't cover that event's window — see [[Data Pipeline]].

## Related
- [[Physics Engine]]
- [[Data Pipeline]]
- [[ML Layer]]
- [[Dashboard]]
