# =============================================================================
# S.H.I.E.L.D. — Dashboard Data Exporter
# Runs the REAL pipeline on every catalog event and writes a compact JSON file
# that the Next.js dashboard loads. This replaces the dashboard's old mock
# sine-wave data with genuine SoLEXS/HEL1OS light curves, detection stages,
# alert logs, the Stage 3->4 gap, and the Layer 3 escalation probability.
#
# Output: dashboard/public/shield_data.json
# Run:    python dashboard_export.py        (or: python main.py --dashboard)
# =============================================================================

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import numpy as np

from config.settings import PROJECT_ROOT
from config.flare_catalog import get_all_events
from core.pipeline import run_on_synthetic_event

logger = logging.getLogger(__name__)

OUTPUT_JSON = PROJECT_ROOT / "dashboard" / "public" / "shield_data.json"

# Downsample the per-second light curves so the JSON stays small (~hundreds of
# points per event) while preserving the flare shape.
SERIES_STEP_S = 15


def _series(df, step_s: int = SERIES_STEP_S) -> dict:
    """Downsample one event's light curves to minutes-from-start arrays."""
    sub = df.iloc[::step_s]
    t0 = df['timestamp'].iloc[0]
    minutes = ((sub['timestamp'] - t0).dt.total_seconds() / 60.0).round(2).tolist()

    def col(name):
        if name in sub.columns:
            return [round(float(v), 12) if np.isfinite(v) else None for v in sub[name].values]
        return []

    return {
        't_min': minutes,
        'solexs': col('solexs_flux'),
        'hel1os': col('hel1os_flux'),
        'solexs_deriv': col('solexs_derivative'),
    }


def _alerts(result) -> List[dict]:
    """Flatten the alert log into display rows."""
    rows = []
    for a in result.alert_log.alerts:
        rows.append({
            'time': str(a.timestamp).split(' ')[-1],   # HH:MM:SS
            'level': a.status,
            'stage': int(a.level),
            'provisional_class': a.provisional_class,
            'confidence': round(float(a.confidence), 2),
            'source': a.trigger_source,
        })
    return rows


def _impact_for(ev, result) -> dict:
    """Impact assessment + safety advisories for this event's flare."""
    from core.impact import assess_impact
    sig = max((d.sigma_above_baseline for d in result.physics_result.hel1os_detections),
              default=0.0)
    return assess_impact(ev.peak_class, hel1os_sigma=sig)


# Cached spectral summary (written by core.spectral.run_full_extraction).
_SPECTRAL_SUMMARY: Optional[dict] = None


def _spectral_for(event_id: str) -> Optional[dict]:
    """Hottest flare's spectral diagnostics for this event, if extracted."""
    global _SPECTRAL_SUMMARY
    if _SPECTRAL_SUMMARY is None:
        path = PROJECT_ROOT / "outputs" / "spectral" / "ALL_events_spectral_summary.json"
        try:
            _SPECTRAL_SUMMARY = json.loads(path.read_text())
        except Exception:
            _SPECTRAL_SUMMARY = {}
    ev = _SPECTRAL_SUMMARY.get(event_id)
    if not ev or not ev.get('flares'):
        return None
    flares = ev['flares']

    def _finite(x):
        try:
            return x if (x is not None and np.isfinite(float(x))) else None
        except (TypeError, ValueError):
            return None

    # Representative flare = the most energetic (highest hard/soft hardness) one,
    # which carries both a real temperature AND a real spectral index. Fall back
    # to the hottest if none registered hard X-rays.
    hard = [f for f in flares if (f.get('peak_hardness_ratio') or 0.0) > 0]
    rep = (max(hard, key=lambda f: f.get('peak_hardness_ratio') or 0.0) if hard
           else max(flares, key=lambda f: f.get('slx_peak_kt_keV_est') or 0.0))
    # Hottest temperature seen anywhere in the event (the headline number).
    kt = max((float(f.get('slx_peak_kt_keV_est') or 0.0) for f in flares), default=0.0)

    return {
        'n_flares': ev.get('n_flares', len(flares)),
        'peak_temperature_keV': round(kt, 2),
        'peak_temperature_MK': round(kt * 11.6, 1),    # 1 keV ~ 11.6 MK
        'spectral_index_at_peak': (round(float(_finite(rep.get('hls_spectral_index_at_peak'))), 2)
                                   if _finite(rep.get('hls_spectral_index_at_peak')) is not None else None),
        'peak_hardness_ratio': round(float(rep.get('peak_hardness_ratio') or 0.0), 2),
        'hottest_flare_time': rep.get('flare_time'),
    }


def _activity_forecast_for(event_id: str, window_start, window_end) -> Optional[dict]:
    """
    Layer A — physics/statistics activity forecast (Poisson), NO AI. Peak flare
    probability reached during this event, from its detected flare history.
    """
    from core.forecast import event_forecast_summary
    if _SPECTRAL_SUMMARY is None:
        _spectral_for(event_id)   # populates the cache
    ev = (_SPECTRAL_SUMMARY or {}).get(event_id) or {}
    flare_times = [f.get('flare_time') for f in ev.get('flares', []) if f.get('flare_time')]
    if not flare_times:
        return None
    return event_forecast_summary(flare_times, window_start, window_end)


def export_dashboard_data() -> Path:
    """Build and write dashboard/public/shield_data.json. Returns the path."""
    logger.info("Exporting dashboard data (running real pipeline on all events)...")

    events_out = []
    gaps = []
    for ev in get_all_events():
        result = run_on_synthetic_event(ev.event_id)
        if result.processed_df is None or result.processed_df.empty:
            logger.warning(f"  {ev.event_id}: no processed data, skipped")
            continue

        gap = result.stage3_to_4_gap_s
        if gap is not None:
            gaps.append(gap)

        # Stage positions as minutes-from-start, for chart markers.
        # 'time' = HH:MM:SS for compact display; 'iso' = full UTC datetime
        # (needed for any real date math, e.g. live-playback virtual clock).
        series_t0 = result.physics_result.df['timestamp'].iloc[0]
        stages_out = [{
            'stage': s['stage'],
            'time': str(s['timestamp']).split(' ')[-1],
            'iso': str(s['timestamp']).replace(' ', 'T'),
            'at_min': round((s['timestamp'] - series_t0).total_seconds() / 60.0, 2),
        } for s in result.stage_timeline]

        # Provisional class comes from the first FORECAST alert if present.
        prov = next((a.provisional_class for a in result.alert_log.alerts
                     if a.level == 3 and a.provisional_class not in ('--', '')), ev.peak_class)

        events_out.append({
            'event_id': ev.event_id,
            'peak_class': ev.peak_class,
            'tier': ev.tier,
            'active_region': ev.active_region,
            'forecast_fired': bool(result.forecast_fired),
            'nowcast_fired': bool(result.nowcast_fired),
            'gap_s': round(float(gap), 1) if gap is not None else None,
            'max_stage': int(result.max_stage_reached),
            'provisional_class': prov,
            'activity_forecast': _activity_forecast_for(ev.event_id, ev.window_start, ev.window_end),
            'series': _series(result.physics_result.df),
            'stages': stages_out,
            'alerts': _alerts(result),
            'impact': _impact_for(ev, result),
            'spectral': _spectral_for(ev.event_id),
        })
        logger.info(f"  {ev.event_id}: gap={gap}s, alerts={len(result.alert_log.alerts)}")

    summary = {
        'n_events': len(events_out),
        'forecast_rate': round(sum(e['forecast_fired'] for e in events_out) / max(len(events_out), 1), 3),
        'nowcast_rate': round(sum(e['nowcast_fired'] for e in events_out) / max(len(events_out), 1), 3),
        'mean_gap_s': round(float(np.mean(gaps)), 1) if gaps else None,
        'mean_gap_min': round(float(np.mean(gaps)) / 60.0, 2) if gaps else None,
    }

    payload = {
        'generated_at': datetime.utcnow().isoformat() + 'Z',
        'summary': summary,
        'events': events_out,
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2))
    logger.info(f"  Wrote {OUTPUT_JSON} ({len(events_out)} events)")
    return OUTPUT_JSON


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='  %(message)s')
    export_dashboard_data()
