---
tags: [flare-catalog, validation, shield]
created: 2026-07-26
---

# Flare Catalog

Up: [[Home]] · See also: [[Physics Engine]], [[Validation and Benchmarking]]

`config/flare_catalog.py` — the 6 training/validation events, all from real
Aditya-L1 PRADAN data (Jan 2024 – Nov 2025).

## Data purity rule
All data sourced exclusively from ISRO PRADAN SoLEXS + HEL1OS files. December 2023
excluded (instruments still commissioning). External references (NOAA class labels,
published papers) used **only** to cross-check results, never to train.

## The six events

| Event ID | Peak class | Window | Active region | Tier | Notes |
|---|---|---|---|---|---|
| `FEB2024_X63` | X6.3 | 2024-02-20 → 25 | AR13590 | TIER 1 | Landmark early Aditya-L1 event; cross-validated vs Roy et al. 2025 |
| `MAR2024_X` | X-class | 2024-03-22 → 26 | AR13614 | TIER 2 | G4 storm; tests behaviour on a strong, well-observed event |
| `MAY2024_X87` | **X8.7** | 2024-05-05 → 16 | AR13663/64 | **CRITICAL** | Strongest event of the century; PRIMARY validation flare (14 May). Distinct from the Gannon G5 storm (10–11 May, driven by earlier CMEs) |
| `OCT2024_MULTI` | Multi-X | 2024-10-01 → 15 | Multiple | TIER 2 | Event cluster; tests rolling-baseline recalculation on back-to-back flares |
| `JAN2025_X18` | X1.8 | 2025-01-01 → 10 | AR13947 | TIER 2 | Smaller X-class; tests low-end sensitivity / false-negative rate |
| `NOV2025_X51` | X5.1 | 2025-11-07 → 16 | AR4274 | TIER 1 | Strong 2025 event near solar maximum; tests recent data |

## Helpers
`get_critical_events()`, `get_tier1_events()`, `get_tier2_events()`,
`get_event_by_id(id)`, `get_all_events()` (priority-sorted: CRITICAL → TIER 1 → TIER 2).

## Usage
```bash
python main.py --catalog              # print the table above
python main.py --event MAY2024_X87    # run the pipeline on the critical event
python main.py --all                  # run + aggregate all 6
```
Feeds [[Physics Engine|the pipeline]] (real data if `--prepare`d, else
[[Data Pipeline#Synthetic data|synthetic]]) and [[Validation and Benchmarking]].
