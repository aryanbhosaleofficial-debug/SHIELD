---
tags: [ml, xgboost, lstm, shield]
created: 2026-07-26
---

# ML Layer (Layer 2 / Layer 3)

Up: [[Home]] · See also: [[Physics Engine]], [[Activity Forecast]], [[Validation and Benchmarking]]

Supervised models layered *on top of* the zero-training [[Physics Engine]] — trained
and evaluated only where there's enough labelled data (the GOES catalog), always
with chronological (no-leakage) train/test splits, and always reported against a
transparent baseline. Lives in `ml/`.

## `detector.py` — catches what the physics engine misses
The hard-X-ray physics detector's recall by class was measured at **X 55% / M 10% /
C 0.1%** — it's tuned for confident, high-energy confirmation and structurally misses
smaller flares. `detector.py` slides a window over the **soft**-X-ray light curve
(the band that actually defines GOES class) and trains XGBoost to catch those:

- Window: `WIN_MIN` = 6 min, step `STEP_MIN` = 3 min, quiet-Sun baseline
  `BASE_MIN` = 30 min (rolling median).
- Features (`FEATURES`): `peak`, `peak_over_base`, `rise`, `mean`, `std`, `d1_max`,
  `d2_max`, `frac_rise` — simple shape descriptors, not raw signal.
- Label = a GOES-catalog flare peaks within the window.

## `severity.py` — classify a detected flare's class (C/M/X)
Given a flare already *detected* (matched to the GOES catalog via
[[Validation and Benchmarking|benchmark.py]]), predicts which class band it's in.
- Features: `peak_solexs_log`, `hel1os_sigma_log`, `gap_s` (stage3→4 gap),
  `neupert_ok`.
- Honest caveats called out in the code: small labelled set (only flares both
  detected *and* matched), strong class imbalance (few C-class reach the hard-X
  detector) — reported via stratified cross-validation, not a single split.

## `forecaster.py` — XGBoost probability forecaster (Layer 3)
Same question as [[Activity Forecast|the Poisson model]] — P(M+ flare in next 24h) —
but supervised, trained on the full official GOES catalog (8k+ flares):
- `build_dataset(catalog, step_h=3, horizon_h=24)` samples every 3h and computes
  leakage-free features from *only* prior activity: flare counts in trailing 6/12/24/
  48h windows, M+ counts in 24/48h, hours since last flare / last M+ flare, max flux
  in the last 24h (log), rate, hour of day.
- Label: does an M+ flare peak within the next `horizon_h`?

## `lstm_forecaster.py` — sequence model (PyTorch)
Same features and labels as `forecaster.py`, but fed as a **sequence** of
`SEQ_LEN` = 8 past steps (8 × 3h = 24h of history) into an LSTM, so it can learn
temporal build-up patterns an XGBoost snapshot can't. Chronological 70/30 split,
standardized on train stats only. Directly comparable to the XGBoost forecaster —
both report `roc_auc_score` / `brier_score_loss`.

## Design philosophy across this layer
Every model here exists to be compared against a non-ML baseline, not to replace
one: `detector` vs. the physics engine's own recall, `forecaster`/`lstm_forecaster`
vs. the Poisson [[Activity Forecast]] and plain climatology. None of this touches the
zero-training [[Physics Engine]] — it's purely supporting/aspirational per
[[Home#Three (four) algorithm layers|the layer table]].
