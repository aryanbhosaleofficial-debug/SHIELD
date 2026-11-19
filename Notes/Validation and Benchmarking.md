---
tags:
  - validation
  - benchmark
  - shield
created: 2026-07-26
aliases:
  - Benchmark
  - Validation
---

# Validation & Benchmarking

Up: [[Home]] · See also: [[Flare Catalog]], [[Physics Engine]], [[ML Layer]]

## `core/validator.py`
Runs the full [[Physics Engine|four-stage pipeline]] on all 6
[[Flare Catalog|catalog events]] and aggregates metrics (called by
`python main.py --all` / `--validate`).

## `core/benchmark.py` — credibility against the official record
Pure data analysis, no AI. What turns "we detected 17 flares" into judge-grade
credibility:

1. **Match** our detections to the official NOAA/GOES flare list
   (`load_goes_catalog` accepts common SWPC/NOAA/HEK column-name variants) →
   recall by class (C/M/X), precision/false-alarm rate, onset-timing error vs. the
   published peak.
2. **False-alarm rate on quiet days** (no cataloged flare) — called out as *the*
   single most important credibility number. Target: [[Physics Engine#Validation
   targets (from `config/settings.py`)|< 1 per 24h]].
3. **Counts → flux calibration** — fits SoLEXS peak counts against the matched GOES
   peak flux, so the system can finally report a *trustworthy* B/C/M/X class instead
   of a provisional one.

## `core/scan.py` — continuous out-of-core sweep
Sweeps a long time range (e.g. 2024-01-01 → present) in overlapping chunks, running
Layer 1 on each without ever loading the whole archive into memory:

- `DEFAULT_CHUNK_HOURS` = 24, `DEFAULT_OVERLAP_HOURS` = 2 (flares fit comfortably in
  a chunk; overlap stops a flare on a boundary from being missed).
- `DEDUP_MINUTES` = 30 — detections within this window across adjacent, overlapping
  chunks are treated as the same flare.
- `FORECAST_FOLLOWUP_MIN` = 60 — a FORECAST alert with no NOWCAST within 60 minutes
  counts as a false alarm.

Proves two things to judges: (1) the engine finds flares it was never told about
(generalization beyond the 6-event catalog), and (2) over a long quiet baseline it
stays under the PRD false-positive target. Pure live detection — no learning from
history, same calculus run on every window.

```bash
python main.py --scan --from 2024-01-01 --to 2025-12-31
# reports: flares_detected, false_alarms_per_24h (target < 1), mean_gap_min,
#          full list -> outputs/scan_results.csv
```

## Relationship to [[ML Layer]]
`ml/severity.py`'s training set is built directly from `benchmark.py`'s
GOES-matched detections (`match_to_catalog`) — the ML layer only ever trains on
flares this validation pipeline has already confirmed are real.
