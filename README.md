# S.H.I.E.L.D. Core Engine

**Solar Hazard Interception & Extra-orbital Logistics Dashboard**
*SoLEXS Forecasting + HEL1OS Nowcasting Engine*

> Team Suryastra · Bharatiya Antariksh Hackathon 2026 · Challenge #15

---

## Overview

An automated algorithmic pipeline that uses the combined time-series data from **SoLEXS** (soft X-ray) and **HEL1OS** (hard X-ray) aboard **Aditya-L1** to nowcast and forecast solar flares — validated on real telemetry from the ISRO PRADAN portal.

## Core Principle

The **Neupert Effect**: HEL1OS hard X-ray flux tracks the time-derivative of SoLEXS soft X-ray flux. S.H.I.E.L.D. watches the SoLEXS derivative to *anticipate*, then waits for the HEL1OS spike to *confirm*.

## Project Structure

```
SHIELD/
├── config/
│   ├── __init__.py
│   ├── settings.py          # Centralized thresholds, constants, paths
│   └── flare_catalog.py     # 6 validation flare events
├── core/
│   ├── __init__.py
│   ├── ingest.py            # FITS/ZIP file reader (PRADAN data)
│   ├── preprocess.py        # Time-axis alignment, cleaning
│   ├── physics_engine.py    # Layer 1 — derivative & sigma detection
│   ├── baseline.py          # Adaptive rolling baseline
│   ├── pipeline.py          # 4-stage state machine
│   ├── alert.py             # Alert generation
│   └── validator.py         # Validation metrics
├── ml/
│   ├── __init__.py
│   ├── features.py          # Feature engineering
│   ├── classifier.py        # Layer 2 — XGBoost (C/M/X)
│   ├── evaluate.py          # ML evaluation metrics
│   ├── sequences.py         # LSTM input preparation
│   ├── lstm_model.py        # Layer 3 — Keras LSTM
│   └── train_lstm.py        # LSTM training script
├── dashboard/
│   ├── index.html           # Main dashboard page
│   ├── css/styles.css       # UI styling
│   └── js/
│       ├── app.js           # Plotly charts & interactions
│       └── data_loader.js   # Data loading
├── data/
│   ├── raw/                 # Raw PRADAN FITS/ZIP files
│   └── processed/           # Cleaned, aligned DataFrames
├── outputs/                 # Pipeline results, plots, metrics
├── tests/                   # Test suite
├── main.py                  # CLI entry point
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# View flare catalog
python main.py --catalog

# Run on the critical X8.7 event
python main.py --event MAY2024_X87

# Run on all 6 events
python main.py --all

# Run validation suite
python main.py --validate

# Launch dashboard
python main.py --dashboard
```

## Three Algorithm Layers

| Layer | Method | Status |
|---|---|---|
| **Layer 1** — Physics Engine | Derivative + sigma detection | PRIMARY (zero training) |
| **Layer 2** — Severity Classifier | XGBoost (C/M/X) | SUPPORTING |
| **Layer 3** — Probability Forecast | LSTM (30-min horizon) | ASPIRATIONAL |

## Validation Dataset

6 flare events from Aditya-L1 PRADAN data (Jan 2024 — Nov 2025), ranging from X1.8 to X8.7.

## Data Source

All data from **ISRO PRADAN portal** — [pradan.issdc.gov.in/al1](https://pradan.issdc.gov.in/al1) (registration required).

---

*Built for the Sun. Built for India.*
*Team Suryastra · S.H.I.E.L.D. Core Engine*
