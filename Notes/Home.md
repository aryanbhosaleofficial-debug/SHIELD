---
tags: [moc, shield]
created: 2026-07-26
---

# S.H.I.E.L.D. Core Engine — Notes

> [!abstract] What this is
> **S**olar **H**azard **I**nterception & **E**xtra-orbital **L**ogistics **D**ashboard.
> An automated pipeline that fuses Aditya-L1's **SoLEXS** (soft X-ray) and **HEL1OS**
> (hard X-ray) telemetry to *forecast* (anticipate) and *nowcast* (confirm) solar
> flares, validated against real ISRO PRADAN data.
> Team Suryastra · Bharatiya Antariksh Hackathon 2026 · Challenge #15.

## Core principle — the Neupert Effect
HEL1OS hard X-ray flux tracks the time-derivative of SoLEXS soft X-ray flux.
S.H.I.E.L.D. watches the SoLEXS derivative to **anticipate**, then waits for the
HEL1OS spike to **confirm**. See [[Physics Engine]].

## Map of Content

- [[Architecture]] — project layout, tech stack, CLI (`main.py`)
- [[Physics Engine]] — Layer 1: the four-stage detection pipeline (zero-training)
- [[Data Pipeline]] — ingest, out-of-core datastore, preprocessing, synthetic data
- [[Flare Catalog]] — the 6 validation events from real Aditya-L1 data
- [[Activity Forecast]] — Layer A: transparent Poisson flare-rate model
- [[ML Layer]] — Layer 2/3: XGBoost detector/severity + LSTM probability forecaster
- [[Impact Assessment]] — flare class → NOAA R/S/G advisory mapping
- [[Validation and Benchmarking]] — GOES catalog matching, false-alarm rate, scan
- [[Extensions]] — SUIT UV imagery + spectral feature extraction (v2.0)
- [[Dashboard]] — the Next.js visualization app

## Three (four) algorithm layers

| Layer | Method | Training | Status |
|---|---|---|---|
| **Layer 1** — Physics Engine | Derivative + sigma detection | None | PRIMARY |
| **Layer A** — Activity Forecast | Poisson process (Bayesian-smoothed rate) | None | SUPPORTING |
| **Layer 2** — Severity/Detector | XGBoost (C/M/X) | GOES catalog | SUPPORTING |
| **Layer 3** — Probability Forecast | LSTM (24h horizon, PyTorch) | GOES catalog | ASPIRATIONAL |

## Data honesty rules
- All primary data from **ISRO PRADAN** exclusively — external catalogs (GOES/NOAA,
  published papers) are used only to *cross-check*, never to train Layer 1.
- December 2023 excluded — instruments still commissioning.
- Every derived/estimated quantity (SUIT features, spectral temperature, S/G-scale
  impacts without ASPEX/MAG) is explicitly labelled "estimate"/"proxy" in code
  comments — see [[Extensions]], [[Impact Assessment]].

## Open questions / TODO
- [ ] `README.md` project-structure diagram is stale vs. actual `core/`/`ml/`
  contents — these notes describe the current code, not the README.
- [ ] No `PRD.md` found at repo root, though comments reference "PRD Section 07"
  and `build_prd.py` exists — locate or regenerate the canonical PRD.
