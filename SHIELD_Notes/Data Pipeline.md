---
tags: [data-pipeline, ingest, shield]
created: 2026-07-26
---

# Data Pipeline

Up: [[Home]] · See also: [[Physics Engine]], [[Architecture]]

## Ingest (`core/ingest.py`)
Reads raw PRADAN FITS/ZIP files for SoLEXS and HEL1OS into DataFrames with
`['timestamp', 'flux']`. `load_event_data(event_id, data_dir)` pulls just the time
window for one [[Flare Catalog|catalog event]] out of a prepared batch.

## Out-of-core datastore (`core/datastore.py`)
The naive approach — load every raw file, concat into one DataFrame — OOMs long
before the physics engine runs once the corpus reaches 100s of GB. Two strategies
keep peak memory bounded to a few files at a time regardless of total corpus size:

1. **Time manifest + file pruning** — cheaply probes each raw file's `[t_min, t_max]`
   from FITS headers (no full table load) and persists it (`_manifest.json`). A
   query for an event's few-day window opens only the overlapping files.
2. **Parquet column store** — converts raw → date-partitioned Parquet once,
   streaming file-by-file (`STREAM_BATCH_ROWS` = 2,000,000 rows/batch cap). Repeated
   queries (the 6-event validation loop, the dashboard) then use partition +
   row-group predicate pushdown and never materialize the full corpus.

Both degrade gracefully: no `pyarrow` → manifest pruning still works directly on raw
files; header probing failure → falls back to a full scan.

Key paths (under `data/processed/`): `_manifest.json`, `parquet_store/`,
`filtered_csv/` (human-friendly per-instrument CSVs), `_active_batch.txt` (which raw
folder is currently "prepared" — read by `--event` and `--scan`).

`reset_store()` wipes all of the above — use when swapping in a new raw data batch
so nothing stale carries over.

Prepare a batch via CLI:
```bash
python main.py --prepare E:\pradan_batch2
```

## Preprocessing (`core/preprocess.py`)
`align_timeseries` + `clean_flux_data` — aligns SoLEXS and HEL1OS onto a common
1-second cadence (`RESAMPLE_CADENCE_S`), interpolates gaps up to
`MAX_GAP_INTERPOLATE_S` = 10s, drops the Dec-2023 commissioning period
(`COMMISSIONING_CUTOFF`). `preprocess_event()` wraps this for one event, optionally
persisting the processed DataFrame.

## Synthetic data (`core/synthetic.py`)
`generate_flare_event(peak_class, start_time, preflare_duration_s,
impulsive_duration_s, gradual_decay_s, quiet_before_s, quiet_after_s)` — builds a
plausible SoLEXS+HEL1OS pair for a target GOES class when real data isn't prepared
yet. Used automatically by `run_on_synthetic_event()` and as the CLI's fallback when
`--prepare` hasn't been run, or when the prepared batch doesn't cover the requested
event's dates (see [[Architecture#CLI (`main.py`)|CLI]]).

## Flow

```
raw PRADAN FITS/ZIP  --ingest.py-->  DataFrames
        |
        v (once, via --prepare)
  datastore.py: time manifest + Parquet store  (out-of-core)
        |
        v (per event query)
  preprocess.py: align + clean
        |
        v
  physics_engine.py / pipeline.py  --> see [[Physics Engine]]
```
