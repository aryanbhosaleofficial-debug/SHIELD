---
tags: [extensions, suit, spectral, shield]
created: 2026-07-26
aliases: [SHIELD 2.0]
---

# Extensions (S.H.I.E.L.D. 2.0)

Up: [[Home]] · See also: [[Physics Engine]], [[Impact Assessment]]

Proof-of-concept modules that go beyond the core SoLEXS/HEL1OS lightcurve pipeline —
the only Aditya-L1 payload paths available to *advance* forecasting further.

## `core/suit.py` — SUIT UV image feature extractor
**Question**: do active-region UV features rise *before* a flare, in a way the
precursor X-rays don't show?

- SUIT produces millions of full-disk images — this does **not** process them all;
  it samples a small set around known flare dates.
- Per image, extracts simple, interpretable features (deliberately no deep
  learning): mean/max brightness, bright-region **area**, number of active
  regions, and a **complexity** proxy (bright-pixel fraction + edge activity).
- Bright-region threshold: `BRIGHT_SIGMA` = 4.0σ above the solar-disk median;
  `MIN_REGION_PX` = 25 (filters noise/cosmic-ray specks).
- Reads gzip-aware FITS via `astropy.io.fits`.

## `core/spectral.py` — spectral feature extractor
Goes beyond the single-band lightcurve to extract the richer physics feature set
already inside the PRADAN zips:

- **SoLEXS `.pi`** (time-resolved spectra, 1/sec, 340 energy channels) →
  per-second energy sub-band count rates → plasma **temperature** (filter/band-ratio
  method, GOES-style) → **emission-measure** proxy.
  Sub-bands (`SOLEXS_BANDS_KEV`): soft 2–6 keV, mid 6–12 keV, hard 12–22 keV.
  Gain: `SOLEXS_GAIN_KEV_PER_CH` ≈ 0.088 keV/channel (approximate — L1 `.pi` has no
  EBOUNDS response matrix).
- **HEL1OS lightcurves** (already split into energy sub-bands per detector:
  CZT1/2, CdTe1/2) → per-detector/per-band count rate → **spectral index**
  (power-law slope across hard bands).

### Honesty labels in the code
- SoLEXS temperature is a band-**ratio estimate** (same principle GOES uses), not a
  full XSPEC fit — labelled "est".
- Emission measure is a **proxy** (∝ soft thermal counts), labelled "proxy".
- Dead-time correction needs DEADC/hk telemetry not yet ingested; count rates are
  flagged where relevant as the raw L1 rate.

## Status
Both are explicitly proof-of-concept / v2.0, separate from the validated core
pipeline in [[Physics Engine]] — treat outputs as exploratory signal, not inputs to
the validated Stage 1–4 alert logic unless/until cross-validated the same way
[[Validation and Benchmarking|the core pipeline]] is.
