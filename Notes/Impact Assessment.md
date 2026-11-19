---
tags: [impact, noaa, safety, shield]
created: 2026-07-26
---

# Impact Assessment

Up: [[Home]] · See also: [[Physics Engine]], [[Extensions]]

`core/impact.py` — turns a detected flare class into concrete Earth/space impacts
and per-domain safety advisories, following NOAA's R-S-G space-weather scales
(PRD §07).

## Honesty split
- **R-scale (Radio Blackout)** and GPS/aviation impacts follow *directly* from the
  soft X-ray flare class — these are real, standard NOAA mappings. Fully computed.
- **S-scale (Radiation Storm)** — astronaut/satellite dose — and **G-scale
  (Geomagnetic Storm)** — power-grid GIC — depend on particle (ASPEX) and magnetic
  (MAG) instrument data, which the core does **not** yet ingest. These are returned
  as flare-based *estimates*, explicitly flagged "needs ASPEX/MAG (Phase 2)".

## Class ↔ flux
```
class_to_flux("X8.7") -> 8.7e-4 W/m²      # letter base * multiplier
```
Base fluxes (`_CLASS_BASE`, W/m²): A=1e-8, B=1e-7, C=1e-6, M=1e-5, X=1e-4.

## R-scale (Radio Blackout) thresholds
| Flux (W/m²) | Class | R-scale |
|---|---|---|
| ≥ 2e-3 | X20+ | R5 |
| ≥ 1e-3 | X10 | R4 |
| ≥ 1e-4 | X1 | R3 |
| ≥ 5e-5 | M5 | R2 |
| ≥ 1e-5 | M1 | R1 |
| below | — | R0 |

## Why this matters for the pitch
This is what turns a raw "X8.7 detected" alert into an operationally meaningful
advisory (HF radio blackout risk, GPS degradation, aviation reroute guidance) — the
"Logistics" half of S.H.I.E.L.D.'s name. See [[Extensions]] for the roadmap toward
covering S/G scales properly with ASPEX/MAG data.
