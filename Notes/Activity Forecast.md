---
tags: [forecast, poisson, layer-a, shield]
created: 2026-07-26
---

# Activity Forecast (Layer A)

Up: [[Home]] · See also: [[Physics Engine]], [[ML Layer]]

`core/forecast.py` — the honest "forecast from SoLEXS + HEL1OS" layer. **Not** AI,
no training — a transparent statistical flare-rate model, same family used by real
operational space-weather centres.

## What it does NOT claim
It does not predict a *specific* flare's onset time — that's [[Physics Engine|Layer
1]]'s job (minutes-scale anticipation). Layer A answers a different, honest question:

> Given how active the Sun has been (flare rate, trend), what is the **probability**
> of at least one significant flare in the next 6 / 24 hours?

## Model
Flares are treated as a **Poisson process** whose rate λ is estimated from recent
flare history with a weak climatological (Bayesian) prior — so the probability is
never exactly 0 and never overreacts to a single flare:

```
lambda = (k + a0) / (delta_h + b0)          [flares per hour]
P(>=1 flare in next T h) = 1 - exp(-lambda * T)
```

- `k` = flares observed in the lookback window (`FORECAST_LOOKBACK_H` = 24h default)
- `a0 = prior_rate_per_h (0.02) * prior_weight_h (24)` — prior pulls toward ~0.5
  significant flares/day when there's no recent activity
- `b0 = prior_weight_h` — prior strength ≈ 1 day of observation, so a real cluster
  still dominates

## Operational level (`_level`)
| Condition | Level |
|---|---|
| recent big flare, or P(24h) ≥ 0.75 | HIGH |
| P(24h) ≥ 0.50 | ELEVATED |
| P(24h) ≥ 0.25 | WATCH |
| else | LOW |

Horizons reported: `FORECAST_HORIZONS_H = (6, 24)` hours.

## Relationship to the ML forecaster
`ml/forecaster.py` and `ml/lstm_forecaster.py` (see [[ML Layer]]) attempt the *same*
"P(M+ flare in next 24h)" question with supervised learning on the GOES catalog —
built specifically to test whether ML beats this transparent Poisson baseline.
Compare skill against both this model and plain climatology.
