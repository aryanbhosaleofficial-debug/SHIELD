---
tags: [physics-engine, layer1, shield]
created: 2026-07-26
---

# Physics Engine (Layer 1)

Up: [[Home]] · See also: [[Data Pipeline]], [[Activity Forecast]], [[Flare Catalog]]

`core/physics_engine.py` + `core/pipeline.py` — **zero-training, deterministic**
flare detection. This mirrors the onboard flare-trigger logic ISRO already flies
on Aditya-L1, and is the primary deliverable of the project.

## Why zero-training matters
- Deterministic calculus on real telemetry — cannot overfit.
- Needs zero training data — works on day one, before any labelled flare history exists.

## Two detection channels

### SoLEXS forecasting (soft X-ray, anticipatory)
- Computes the first derivative of the soft X-ray light curve
  (`compute_solexs_derivatives`, smoothed over `SOLEXS_DERIVATIVE_WINDOW_S` = 5s).
- Measures slope-steepening rate over a `SOLEXS_STEEPENING_WINDOW_S` = 60s window.
- Raises **FORECAST ALERT** when steepening is sustained for
  `SOLEXS_SUSTAINED_THRESHOLD_S` = 60s above `SOLEXS_DERIVATIVE_THRESHOLD` = 0.05.

### HEL1OS nowcasting (hard X-ray, confirmatory)
- Maintains a rolling baseline mean + std over `HEL1OS_BASELINE_WINDOW_S` = 600s
  (`core/baseline.py`).
- Raises **NOWCAST CONFIRMED** when flux crosses `HEL1OS_SIGMA_THRESHOLD` = 5σ above
  baseline, sustained ≥ `HEL1OS_MIN_SPIKE_DURATION_S` = 15s (filters cosmic-ray glitches).
- Cross-checks **Neupert consistency**: correlation between HEL1OS flux and
  d/dt(SoLEXS) ≥ `NEUPERT_CORRELATION_THRESHOLD` = 0.5 within a
  `NEUPERT_LAG_WINDOW_S` = 120s lag window.

## Four-stage pipeline (`core/pipeline.py`)

| Stage | Name | Trigger | Alert level |
|---|---|---|---|
| 1 | QUIET SUN | start of window | ALL_CLEAR |
| 2 | PRE-FLARE HEATING | SoLEXS relative-derivative signal > ~3σ over quiet baseline, sustained 15 of last 30s | WATCH |
| 3 | FORECAST ALERT | SoLEXS engine detection (sustained steepening) | FORECAST_ALERT |
| 4 | NOWCAST CONFIRMED | HEL1OS engine detection (sigma spike + Neupert check) | NOWCAST_CONFIRMED |

Stage 2 (WATCH) reuses the *same* relative growth-rate signal as Stage 3 but at a
looser, quiet-baseline-calibrated threshold (~3σ vs ~6σ), so WATCH always fires
before FORECAST by construction.

**The Stage 3→4 gap (`stage3_to_4_gap_s`) is the headline metric** — how much lead
time the forecast channel gives before the flare is confirmed. Positive = forecast
preceded nowcast (the system worked as designed).

## Alerts (`core/alert.py`)
`Alert` dataclass carries full context per detection: timestamp, `AlertLevel` (1-4),
trigger source (`solexs`/`hel1os`/`pipeline`), provisional class, confidence, and the
raw measurements (flux, derivative, sigma, Neupert correlation). `AlertLog` is the
chronological log for one event and computes `stage3_to_4_gap_s` /
`get_current_stage()`.

## Running it
```bash
python main.py --event MAY2024_X87   # real data if --prepare'd, else synthetic
python main.py --all                  # all 6 catalog events, see [[Flare Catalog]]
```
`PipelineResult.print_report()` prints the stage timeline, forecast/nowcast fired
flags, the 3→4 gap, and the alert summary.

## Validation targets (from `config/settings.py`)
- False positives: < 1 per 24h of quiet-Sun data (`MAX_FALSE_POSITIVES_PER_24H`).
- Onset-timing accuracy: within ~5 minutes of published analysis
  (`ONSET_TIMING_TOLERANCE_S` = 300). Checked in [[Validation and Benchmarking]].
