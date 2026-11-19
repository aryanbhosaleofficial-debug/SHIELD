---
tags: [dashboard, nextjs, frontend, shield]
created: 2026-07-26
---

# Dashboard

Up: [[Home]] · See also: [[Architecture]], [[Physics Engine]]

`dashboard/` — a Next.js (App Router, TypeScript) app that visualizes pipeline
output. Note: this supersedes the plain HTML/CSS/JS dashboard described in the repo
`README.md` — the actual app is a full Next.js project.

## Data flow
```
python main.py --dashboard
  -> dashboard_export.py: runs/collects pipeline results
  -> writes dashboard/public/shield_data.json
cd dashboard && npm install && npm run dev   # http://localhost:3000
```
The dashboard reads the exported static JSON — it does not call the Python pipeline
live.

## Structure (`dashboard/src/`)
- `app/layout.tsx`, `app/page.tsx`, `app/globals.css` — shell + main page
- `components/`
  - `FlareChart.tsx` — overview flare timeline
  - `SolexsChart.tsx` / `Hel1osChart.tsx` — per-instrument light curves
  - `ForecastPanel.tsx` — FORECAST/NOWCAST stage + [[Activity Forecast|Layer A
    probability]] display
  - `FluxSidebar.tsx` — live flux readout
  - `DetailModal.tsx` — drill-down on a selected event/alert
  - `SuitImageCard.tsx` — [[Extensions#`core/suit.py` — SUIT UV image feature
    extractor|SUIT]] imagery preview
  - `VelcDataCard.tsx` / `VelcSpectrogramCard.tsx` — VELC-related data views

`public/` also ships pre-rendered assets referenced by these cards:
`suit_may2024.png`, `suit_nb06.png`, `suit_nb07.png`, `velc_real.png`.

## `dashboard/generate_dashboard_pdf.py`
A separate script for exporting a PDF snapshot of the dashboard (submission
artifact) — distinct from `main.py`'s `--dashboard` (which just prepares the JSON
the live app reads).

## Notes for AI assistants working in this subfolder
`dashboard/AGENTS.md` / `CLAUDE.md` flag that this Next.js version has breaking API
changes vs. training-data assumptions — check `node_modules/next/dist/docs/` before
writing Next.js code here.
