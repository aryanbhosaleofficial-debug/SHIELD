"use client";

import React, { useEffect, useState } from "react";
import { Activity, ShieldAlert, Zap, Server, Sun, ChevronRight, Clock, Thermometer, Radio, Plane, Satellite, User, BatteryCharging } from "lucide-react";
import FlareChart, { FlareSeries, StageMark } from "../components/FlareChart";
import DetailModal, { DetailSection, DetailStat, DetailTable } from "../components/DetailModal";
import SolexsChart from "../components/SolexsChart";
import Hel1osChart from "../components/Hel1osChart";
import FluxSidebar from "../components/FluxSidebar";
import SuitImageCard from "../components/SuitImageCard";
import VelcDataCard from "../components/VelcDataCard";
import VelcSpectrogramCard from "../components/VelcSpectrogramCard";
import ForecastPanel from "../components/ForecastPanel";

/* ================================================================== */
/* Type definitions                                                   */
/* ================================================================== */

interface AlertRow {
  time: string;
  level: string;
  stage: number;
  provisional_class: string;
  confidence: number;
  source: string;
}

interface EventData {
  event_id: string;
  peak_class: string;
  tier: string;
  active_region: string;
  forecast_fired: boolean;
  nowcast_fired: boolean;
  gap_s: number | null;
  max_stage: number;
  provisional_class: string;
  activity_forecast?: ActivityForecast | null;
  series: FlareSeries;
  stages: StageMark[];
  alerts: AlertRow[];
  impact?: ImpactData;
  spectral?: SpectralData | null;
}

interface ActivityForecast {
  peak_p_6h: number;
  peak_p_24h: number;
  peak_level: string;
  peak_time: string;
}

interface SpectralData {
  n_flares: number;
  peak_temperature_keV: number;
  peak_temperature_MK: number;
  spectral_index_at_peak: number | null;
  peak_hardness_ratio: number;
  hottest_flare_time: string;
}

interface ImpactDomain {
  level: string;
  impact: string;
  advisory: string;
  basis: string;
}

interface ImpactData {
  flare_class: string;
  r_scale: number;
  domains: Record<string, ImpactDomain>;
}

const DOMAIN_TITLES: Record<string, string> = {
  radio_blackout: "Radio Blackout",
  gps_navigation: "GPS / Navigation",
  aviation: "Aviation",
  satellite: "Satellites",
  astronaut_radiation: "Astronaut Radiation",
  power_grid: "Power Grid",
};

const DOMAIN_ICONS: Record<string, React.ReactNode> = {
  radio_blackout: <Radio className="w-4 h-4" />,
  gps_navigation: <Satellite className="w-4 h-4" />,
  aviation: <Plane className="w-4 h-4" />,
  satellite: <Satellite className="w-4 h-4" />,
  astronaut_radiation: <User className="w-4 h-4" />,
  power_grid: <BatteryCharging className="w-4 h-4" />,
};

function levelColor(level: string): string {
  const l = level.toUpperCase();
  if (l === "HIGH" || l === "ELEVATED" || l === "R4" || l === "R5") return "text-red-400 border-red-500/30 bg-red-500/10";
  if (l === "WATCH" || l === "MODERATE" || l === "R3" || l === "R2") return "text-orange-400 border-orange-500/30 bg-orange-500/10";
  if (l === "LOW" || l === "R0" || l === "R1") return "text-emerald-400 border-emerald-500/30 bg-emerald-500/10";
  return "text-slate-300 border-slate-700 bg-slate-800/40";
}

function levelBadgeColor(level: string): string {
  const l = level.toUpperCase();
  if (l === "HIGH" || l === "ELEVATED" || l.startsWith("R3") || l.startsWith("R4") || l.startsWith("R5"))
    return "bg-red-500/20 text-red-400 border-red-500/30";
  if (l === "WATCH" || l === "MODERATE" || l.startsWith("R2"))
    return "bg-orange-500/20 text-orange-400 border-orange-500/30";
  return "bg-emerald-500/20 text-emerald-400 border-emerald-500/30";
}

interface ShieldData {
  generated_at: string;
  summary: {
    n_events: number;
    forecast_rate: number;
    nowcast_rate: number;
    mean_gap_s: number | null;
    mean_gap_min: number | null;
  };
  events: EventData[];
}

const STAGE_NAMES: Record<number, string> = {
  1: "QUIET SUN",
  2: "PRE-FLARE HEATING",
  3: "FORECAST ALERT",
  4: "NOWCAST CONFIRMED",
};

const STAGE_COLORS: Record<number, string> = {
  1: "text-emerald-400",
  2: "text-yellow-400",
  3: "text-orange-400",
  4: "text-red-400",
};

const STAGE_BG: Record<number, string> = {
  1: "bg-emerald-500/10 border-emerald-500/30",
  2: "bg-yellow-500/10 border-yellow-500/30",
  3: "bg-orange-500/10 border-orange-500/30",
  4: "bg-red-500/10 border-red-500/30",
};

/* Detail panel type — which section the user clicked */
type DetailPanelType =
  | "stage"
  | "speed"
  | "probability"
  | "class"
  | "chart"
  | "alerts"
  | "impact"
  | "spectral"
  | "impact_domain"
  | null;

/* ================================================================== */
/* Main Page Component                                                */
/* ================================================================== */

export default function Home() {
  const [data, setData] = useState<ShieldData | null>(null);
  const [selected, setSelected] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  /* Detail panel state */
  const [detailOpen, setDetailOpen] = useState<DetailPanelType>(null);
  const [detailDomainKey, setDetailDomainKey] = useState<string>("");

  /* Live playback state */
  const [liveMode, setLiveMode] = useState(false);
  const [liveIdx, setLiveIdx] = useState(0);

  /* Reset live mode when event changes */
  useEffect(() => {
    setLiveIdx(0);
    setLiveMode(false);
  }, [selected]);

  /* Live playback interval — advance 3 data points every 100ms, loop when done */
  /* Uses `data` + `selected` so it runs before `event` is derived below */
  useEffect(() => {
    if (!liveMode || !data) return;
    const ev = data.events.find(e => e.event_id === selected);
    if (!ev) return;
    const total = ev.series.t_min.length;
    const id = setInterval(() => {
      setLiveIdx(prev => {
        const next = prev + 3;
        return next >= total ? 0 : next;
      });
    }, 100);
    return () => clearInterval(id);
  }, [liveMode, selected, data]);

  useEffect(() => {
    fetch("/shield_data.json")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((d: ShieldData) => {
        setData(d);
        if (d.events.length) setSelected(d.events[0].event_id);
      })
      .catch((e) => setError(String(e)));
  }, []);

  const event = data?.events.find((e) => e.event_id === selected) ?? null;
  const gapMin = event?.gap_s != null ? (event.gap_s / 60).toFixed(1) : "--";

  /* Sliced series for live playback */
  const displaySeries: FlareSeries | undefined = liveMode && event
    ? {
        t_min: event.series.t_min.slice(0, Math.max(liveIdx, 1)),
        solexs: event.series.solexs.slice(0, Math.max(liveIdx, 1)),
        hel1os: event.series.hel1os.slice(0, Math.max(liveIdx, 1)),
        solexs_deriv: event.series.solexs_deriv.slice(0, Math.max(liveIdx, 1)),
      }
    : event?.series;

  const displayStages = liveMode && event
    ? event.stages.filter(s => s.at_min <= (event.series.t_min[liveIdx] ?? 0))
    : event?.stages ?? [];

  const fullXMax = event?.series.t_min[event.series.t_min.length - 1];

  /* Virtual UTC time shown while playing back */
  const virtualTime: Date | null = (() => {
    if (!liveMode || !event?.stages.length) return null;
    const s = event.stages[0];
    const epoch = Date.parse((s.iso ?? s.time) + 'Z');
    if (isNaN(epoch)) return null;
    const windowStart = epoch - s.at_min * 60_000;
    return new Date(windowStart + (event.series.t_min[liveIdx] ?? 0) * 60_000);
  })();

  const livePct = event
    ? Math.min(100, Math.round((liveIdx / Math.max(event.series.t_min.length - 1, 1)) * 100))
    : 0;

  const openDetail = (type: DetailPanelType) => setDetailOpen(type);
  const openDomainDetail = (key: string) => {
    setDetailDomainKey(key);
    setDetailOpen("impact_domain");
  };
  const closeDetail = () => {
    setDetailOpen(null);
    setDetailDomainKey("");
  };

  return (
    <div className="min-h-screen shield-bg text-slate-100 font-sans selection:bg-blue-500/30">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-slate-800 bg-slate-950/80 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="relative">
              <Sun className="w-8 h-8 text-orange-500" />
              <div className="absolute inset-0 bg-orange-500 blur-md opacity-40 animate-pulse"></div>
            </div>
            <div>
              <h1 className="text-xl font-bold tracking-widest text-slate-100">S.H.I.E.L.D.</h1>
              <p className="text-[10px] uppercase tracking-widest text-slate-400 font-medium">
                ISRO Aditya-L1 · Solar Flare Early Warning
              </p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            {/* Live clock */}
            <LiveClock />

            {/* Event selector */}
            {data && (
              <select
                value={selected}
                onChange={(e) => setSelected(e.target.value)}
                className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-blue-500"
              >
                {data.events.map((e) => (
                  <option key={e.event_id} value={e.event_id}>
                    {e.event_id} ({e.peak_class})
                  </option>
                ))}
              </select>
            )}
            <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-500/10 rounded-full border border-emerald-500/20">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">
                System Online
              </span>
            </div>
          </div>
        </div>

        {/* Credibility strip — real validated numbers, not marketing copy */}
        <div className="border-t border-slate-800/60 bg-slate-950/60">
          <div className="max-w-7xl mx-auto px-4 py-1.5 flex flex-wrap items-center gap-x-6 gap-y-1 text-[10px] font-mono text-slate-500">
            <span><span className="text-slate-300 font-bold">877</span> days scanned</span>
            <span className="text-slate-700">·</span>
            <span><span className="text-slate-300 font-bold">175</span> real flares detected</span>
            <span className="text-slate-700">·</span>
            <span><span className="text-emerald-400 font-bold">95.9%</span> precision</span>
            <span className="text-slate-700">·</span>
            <span><span className="text-blue-400 font-bold">0.33</span> false alarms / 24h</span>
            <span className="text-slate-700">·</span>
            <span className="text-slate-600 italic">benchmarked vs 8,149 real GOES flares</span>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8 space-y-6">
        {error && (
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">
            Could not load <code>/shield_data.json</code> ({error}). Run{" "}
            <code className="text-red-200">python dashboard_export.py</code> first.
          </div>
        )}
        {!data && !error && (
          <div className="flex flex-col items-center justify-center py-24 gap-3">
            <div className="relative w-10 h-10">
              <div className="absolute inset-0 rounded-full border-2 border-slate-800" />
              <div className="absolute inset-0 rounded-full border-2 border-orange-500 border-t-transparent animate-spin" />
            </div>
            <p className="text-slate-400 text-sm">Loading real pipeline data…</p>
          </div>
        )}

        {event && (
          <>
            {/* ============================================================ */}
            {/* KPI Cards — all clickable                                    */}
            {/* ============================================================ */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <KPICard
                title="Algorithm State"
                value={`Stage ${event.max_stage}`}
                subtitle={STAGE_NAMES[event.max_stage] ?? ""}
                icon={<Activity className="w-5 h-5 text-blue-400" />}
                gradient="from-blue-500/20 to-blue-900/5"
                border="border-blue-500/20"
                onClick={() => openDetail("stage")}
                delayMs={0}
              />
              <KPICard
                title="Detection Speed"
                value={`${gapMin} min`}
                subtitle="Onset → confirmed"
                icon={<ShieldAlert className="w-5 h-5 text-orange-400" />}
                gradient="from-orange-500/20 to-orange-900/5"
                border="border-orange-500/20"
                alert={event.gap_s != null && event.gap_s > 0}
                onClick={() => openDetail("speed")}
                delayMs={60}
              />
              <KPICard
                title="Flare Probability (24h)"
                value={event.activity_forecast != null
                  ? `${(event.activity_forecast.peak_p_24h * 100).toFixed(0)}%` : "N/A"}
                subtitle={event.activity_forecast != null
                  ? `Layer A · ${event.activity_forecast.peak_level} (Poisson, no AI)`
                  : "Activity forecast"}
                icon={<Zap className="w-5 h-5 text-yellow-400" />}
                gradient="from-yellow-500/20 to-yellow-900/5"
                border="border-yellow-500/20"
                onClick={() => openDetail("probability")}
                delayMs={120}
              />
              <KPICard
                title="Observed Class"
                value={event.peak_class}
                subtitle={`AR ${event.active_region} · ${event.tier}`}
                icon={<Server className="w-5 h-5 text-purple-400" />}
                gradient="from-purple-500/20 to-purple-900/5"
                border="border-purple-500/20"
                onClick={() => openDetail("class")}
                delayMs={180}
              />
            </div>

            {/* ============================================================ */}
            {/* Charts & Logs — clickable                                    */}
            {/* ============================================================ */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-rise-in" style={{ animationDelay: '220ms' }}>
              <div
                className="col-span-1 lg:col-span-2 relative group rounded-xl border border-slate-800 bg-slate-900/50 p-4 shadow-2xl overflow-hidden backdrop-blur-sm hover:border-blue-500/40"
              >
                <div className="flex items-center justify-between mb-3">
                  <h2
                    className="text-sm font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2 cursor-pointer"
                    onClick={() => openDetail("chart")}
                  >
                    <Activity className="w-4 h-4 text-blue-400" />
                    Flux Monitoring — {event.event_id}
                    <ChevronRight className="w-4 h-4 text-slate-600 group-hover:text-blue-400 transition-colors" />
                  </h2>
                  <div className="flex items-center gap-3">
                    {virtualTime && (
                      <div className="font-mono text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded px-2 py-0.5">
                        {virtualTime.toISOString().replace('T', ' ').slice(0, 19)} UTC
                      </div>
                    )}
                    <button
                      onClick={() => setLiveMode(m => !m)}
                      className={`flex items-center gap-1.5 px-3 py-1 rounded-full border text-xs font-bold uppercase tracking-wider transition-all ${
                        liveMode
                          ? 'bg-red-500/20 border-red-500/40 text-red-400 hover:bg-red-500/30'
                          : 'bg-slate-800 border-slate-700 text-slate-400 hover:border-blue-500/40 hover:text-blue-400'
                      }`}
                    >
                      {liveMode ? (
                        <>
                          <span className="relative flex h-2 w-2">
                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
                            <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500" />
                          </span>
                          Stop
                        </>
                      ) : (
                        <>▶ Live</>
                      )}
                    </button>
                  </div>
                </div>

                {/* Live progress bar */}
                {liveMode && (
                  <div className="mb-2 h-1 rounded-full bg-slate-800 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-blue-500 to-red-500 transition-all duration-100"
                      style={{ width: `${livePct}%` }}
                    />
                  </div>
                )}

                <div className="h-[400px] w-full bg-slate-950/50 rounded-lg border border-slate-800/50">
                  <FlareChart
                    series={displaySeries ?? event.series}
                    stages={displayStages}
                    isLive={liveMode}
                    fixedXMax={liveMode ? fullXMax : undefined}
                  />
                </div>
              </div>

              {/* Alert log */}
              <div
                className="col-span-1 rounded-xl border border-slate-800 bg-slate-900/50 p-4 shadow-xl flex flex-col card-clickable hover:border-slate-600"
                onClick={() => openDetail("alerts")}
              >
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
                    <Server className="w-4 h-4 text-slate-400" />
                    Alert Log
                  </h2>
                  <ChevronRight className="w-4 h-4 text-slate-600 group-hover:text-slate-300 transition-colors" />
                </div>
                <div className="flex-1 overflow-y-auto space-y-3 font-mono text-xs">
                  {event.alerts.map((a, i) => (
                    <LogEntry key={i} time={a.time} stage={a.stage} msg={`${a.level} (conf ${a.confidence})`} />
                  ))}
                </div>
              </div>
            </div>

            {/* ============================================================ */}
            {/* SoLEXS / HEL1OS standalone charts — split row                 */}
            {/* ============================================================ */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 animate-rise-in" style={{ animationDelay: '280ms' }}>
              <div
                className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 shadow-xl card-clickable hover:border-blue-500/40"
                onClick={() => openDetail("chart")}
              >
                <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2 flex items-center gap-2">
                  <Activity className="w-3.5 h-3.5 text-blue-400" />
                  SoLEXS — Soft X-ray
                </h2>
                <div className="h-[260px] w-full bg-slate-950/50 rounded-lg border border-slate-800/50">
                  <SolexsChart series={event.series} stages={event.stages} />
                </div>
              </div>
              <div
                className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 shadow-xl card-clickable hover:border-red-500/40"
                onClick={() => openDetail("chart")}
              >
                <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-300 mb-2 flex items-center gap-2">
                  <Activity className="w-3.5 h-3.5 text-red-400" />
                  HEL1OS — Hard X-ray
                </h2>
                <div className="h-[260px] w-full bg-slate-950/50 rounded-lg border border-slate-800/50">
                  <Hel1osChart series={event.series} stages={event.stages} />
                </div>
              </div>
            </div>

            {/* ============================================================ */}
            {/* Real VELC coronal spectrogram — Aditya-L1 instrument data     */}
            {/* ============================================================ */}
            <div className="animate-rise-in" style={{ animationDelay: '320ms' }}>
              <VelcSpectrogramCard />
            </div>

            {/* ============================================================ */}
            {/* Flux & Time | SUIT x3 | VELC/Spectral — bottom info row       */}
            {/* ============================================================ */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4 animate-rise-in" style={{ animationDelay: '380ms' }}>
              <div className="col-span-2 md:col-span-1 row-span-2 md:row-span-1">
                <FluxSidebar series={event.series} stages={event.stages} maxStage={event.max_stage} />
              </div>
              <SuitImageCard label="SUIT · May 2024" src="/suit_may2024.png" filter="NB07 · X8.7 storm period" time="2024-05-15 23:03 UTC" />
              <SuitImageCard label="SUIT · NB07" src="/suit_nb07.png" wavelengthNm={388} filter="Ca II near-UV" time="2026-06-29 22:11 UTC" />
              <SuitImageCard label="SUIT · NB06" src="/suit_nb06.png" wavelengthNm={300} filter="mid-UV" time="2026-06-29 22:33 UTC" />
              <VelcDataCard spectral={event.spectral} onClick={() => openDetail("spectral")} />
            </div>

            {/* ============================================================ */}
            {/* Forecast & Impact — combined panel, each domain clickable     */}
            {/* ============================================================ */}
            <div className="animate-rise-in" style={{ animationDelay: '400ms' }}>
              <ForecastPanel
                activityForecast={event.activity_forecast}
                impact={event.impact}
                onForecastClick={() => openDetail("probability")}
                onDomainClick={openDomainDetail}
              />
            </div>
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/60 mt-12">
        <div className="max-w-7xl mx-auto px-4 py-6 flex flex-col md:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <Sun className="w-3.5 h-3.5 text-orange-500/60" />
            <span>S.H.I.E.L.D. · Team Suryastra · Bharatiya Antariksh Hackathon 2026 · Challenge #15</span>
          </div>
          <div className="text-[11px] text-slate-600 italic">
            Built on real ISRO Aditya-L1 SoLEXS + HEL1OS data — no simulated flares.
          </div>
        </div>
      </footer>

      {/* ================================================================ */}
      {/* DETAIL MODALS — one per clickable section                        */}
      {/* ================================================================ */}

      {/* --- 1. Algorithm Stage Detail --- */}
      <DetailModal
        open={detailOpen === "stage"}
        onClose={closeDetail}
        title="Algorithm State Detail"
        subtitle={event ? `Event ${event.event_id} — ${event.peak_class}` : ""}
        accentColor="#3b82f6"
      >
        {event && (
          <>
            <DetailSection title="Current State" accent="#3b82f6">
              <div className="flex items-center gap-4">
                <div className={`text-5xl font-black ${STAGE_COLORS[event.max_stage]}`}>
                  S{event.max_stage}
                </div>
                <div>
                  <div className="text-lg font-bold text-slate-100">{STAGE_NAMES[event.max_stage]}</div>
                  <div className="text-sm text-slate-400 mt-1">
                    {event.forecast_fired && event.nowcast_fired
                      ? "Both forecast and nowcast have fired — flare confirmed."
                      : event.forecast_fired
                      ? "Forecast has fired — awaiting HEL1OS confirmation."
                      : "Monitoring solar activity — no alerts triggered."}
                  </div>
                </div>
              </div>
            </DetailSection>

            <DetailSection title="4-Stage Pipeline Progression" accent="#3b82f6">
              <div className="space-y-3">
                {[1, 2, 3, 4].map((s) => {
                  const stageData = event.stages.find((st) => st.stage === s);
                  const reached = s <= event.max_stage;
                  return (
                    <div
                      key={s}
                      className={`flex items-center gap-4 p-3 rounded-lg border transition-all ${
                        reached ? STAGE_BG[s] : "bg-slate-800/20 border-slate-800/50 opacity-40"
                      }`}
                    >
                      <div className={`text-2xl font-black ${reached ? STAGE_COLORS[s] : "text-slate-600"}`}>
                        S{s}
                      </div>
                      <div className="flex-1">
                        <div className={`text-sm font-semibold ${reached ? "text-slate-100" : "text-slate-500"}`}>
                          {STAGE_NAMES[s]}
                        </div>
                        <div className="text-xs text-slate-400">
                          {s === 1 && "Baseline monitoring — all sensors nominal."}
                          {s === 2 && "SoLEXS derivative rising — pre-flare heating detected."}
                          {s === 3 && "Sustained slope steepening — forecast alert issued."}
                          {s === 4 && "HEL1OS 3σ spike — flare nowcast confirmed."}
                        </div>
                      </div>
                      <div className="text-right">
                        {stageData ? (
                          <>
                            <div className="text-sm font-mono text-slate-200">{stageData.time}</div>
                            <div className="text-xs text-slate-500">+{stageData.at_min.toFixed(1)} min</div>
                          </>
                        ) : (
                          <div className="text-xs text-slate-600">Not reached</div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </DetailSection>

            <DetailSection title="Detection Summary" accent="#3b82f6">
              <div className="grid grid-cols-2 gap-3">
                <DetailStat label="Forecast Fired" value={event.forecast_fired ? "YES ✓" : "NO"} accent={event.forecast_fired ? "#10b981" : "#ef4444"} />
                <DetailStat label="Nowcast Fired" value={event.nowcast_fired ? "YES ✓" : "NO"} accent={event.nowcast_fired ? "#10b981" : "#ef4444"} />
                <DetailStat label="Provisional Class" value={event.provisional_class} sub="At Stage 3 trigger" accent="#f97316" />
                <DetailStat label="True Peak Class" value={event.peak_class} sub={`Active Region ${event.active_region}`} accent="#a855f7" />
              </div>
            </DetailSection>
          </>
        )}
      </DetailModal>

      {/* --- 2. Detection Speed Detail --- */}
      <DetailModal
        open={detailOpen === "speed"}
        onClose={closeDetail}
        title="Detection Speed Analysis"
        subtitle={event ? `Onset → confirmed gap for ${event.event_id}` : ""}
        accentColor="#f97316"
      >
        {event && (
          <>
            <DetailSection title="Detection Speed Measurement" accent="#f97316">
              <div className="flex items-center gap-6">
                <div className="text-5xl font-black text-orange-400">{gapMin}<span className="text-2xl text-orange-300"> min</span></div>
                <div className="text-sm text-slate-300">
                  <p>Time between <span className="text-orange-400 font-semibold">Stage 3 (pre-flare heating flagged)</span> and <span className="text-red-400 font-semibold">Stage 4 (Nowcast Confirmed)</span>.</p>
                  <p className="mt-2 text-slate-400">Honest framing: real flares are impulsive — soft and hard X-rays rise within seconds of each other, so this is <em>not</em> a minutes-ahead warning window. It measures how fast SHIELD goes from first sign of heating to a cross-validated (Neupert), confirmed detection.</p>
                </div>
              </div>
            </DetailSection>

            <DetailSection title="Stage Timestamps" accent="#f97316">
              <div className="grid grid-cols-2 gap-3">
                {event.stages.filter(s => s.stage >= 3).map((s) => (
                  <DetailStat
                    key={s.stage}
                    label={`Stage ${s.stage} — ${STAGE_NAMES[s.stage]}`}
                    value={s.time}
                    sub={`+${s.at_min.toFixed(1)} min from window start`}
                    accent={s.stage === 3 ? "#f97316" : "#ef4444"}
                  />
                ))}
              </div>
            </DetailSection>

            {data && (
              <DetailSection title="Cross-Event Comparison" accent="#f97316">
                <DetailTable
                  headers={["Event", "Class", "Gap (sec)", "Gap (min)", "Detected?", "Confirmed?"]}
                  rows={data.events.map((e) => [
                    e.event_id,
                    e.peak_class,
                    e.gap_s != null ? e.gap_s.toFixed(0) : "—",
                    e.gap_s != null ? (e.gap_s / 60).toFixed(1) : "—",
                    e.forecast_fired ? "✓" : "✗",
                    e.nowcast_fired ? "✓" : "✗",
                  ])}
                />
                {data.summary.mean_gap_min != null && (
                  <div className="mt-3 text-xs text-slate-400">
                    Mean detection speed across all events: <span className="text-orange-400 font-semibold">{data.summary.mean_gap_min.toFixed(2)} min</span> ({data.summary.mean_gap_s?.toFixed(1)}s)
                  </div>
                )}
              </DetailSection>
            )}

            <DetailSection title="Neupert Effect Explanation" accent="#f97316">
              <div className="text-sm text-slate-300 space-y-2">
                <p><span className="text-orange-400 font-semibold">The Neupert Effect</span> is the physical principle behind cross-validated detection:</p>
                <p className="text-slate-400">HEL1OS hard X-ray flux tracks the <em>time-derivative</em> of SoLEXS soft X-ray flux. SHIELD flags the SoLEXS derivative rising (Stage 3), then confirms against the HEL1OS spike (Stage 4) — two independent instruments agreeing, which suppresses false alarms.</p>
                <p className="text-slate-400">In real data the two rises are essentially concurrent (seconds apart), not separated by a fixed advance-warning window. SHIELD's strength here is fast, validated <em>detection</em> — true hours/days-ahead forecasting needs SUIT UV imaging (see Roadmap).</p>
              </div>
            </DetailSection>
          </>
        )}
      </DetailModal>

      {/* --- 3. Flare Probability Detail --- */}
      <DetailModal
        open={detailOpen === "probability"}
        onClose={closeDetail}
        title="Flare Probability Forecast"
        subtitle="Layer A — Poisson Activity Rate (no AI)"
        accentColor="#eab308"
      >
        {event && (
          <>
            {event.activity_forecast ? (
              <>
                <DetailSection title="Probability Estimates" accent="#eab308">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="rounded-xl border border-yellow-500/30 bg-yellow-500/10 p-4 text-center">
                      <div className="text-xs text-yellow-400 uppercase tracking-wider font-semibold mb-2">6-Hour Horizon</div>
                      <div className="text-4xl font-black text-yellow-400">{(event.activity_forecast.peak_p_6h * 100).toFixed(0)}%</div>
                      <div className="text-xs text-slate-400 mt-1">P(≥1 flare in next 6h)</div>
                    </div>
                    <div className="rounded-xl border border-orange-500/30 bg-orange-500/10 p-4 text-center">
                      <div className="text-xs text-orange-400 uppercase tracking-wider font-semibold mb-2">24-Hour Horizon</div>
                      <div className="text-4xl font-black text-orange-400">{(event.activity_forecast.peak_p_24h * 100).toFixed(0)}%</div>
                      <div className="text-xs text-slate-400 mt-1">P(≥1 flare in next 24h)</div>
                    </div>
                  </div>
                </DetailSection>

                <DetailSection title="Activity Level" accent="#eab308">
                  <div className="flex items-center gap-4">
                    <span className={`px-4 py-2 rounded-full border text-sm font-bold ${levelBadgeColor(event.activity_forecast.peak_level)}`}>
                      {event.activity_forecast.peak_level}
                    </span>
                    <div className="text-sm text-slate-300">
                      Peak forecast issued at <span className="text-yellow-400 font-mono">{event.activity_forecast.peak_time}</span>
                    </div>
                  </div>
                </DetailSection>

                <DetailSection title="Model Details" accent="#eab308">
                  <div className="text-sm text-slate-300 space-y-2">
                    <p>Flares are modelled as a <span className="text-yellow-400 font-semibold">Poisson process</span> with Bayesian smoothing:</p>
                    <div className="bg-slate-800/60 rounded-lg p-3 font-mono text-xs text-slate-300 border border-slate-700/50">
                      λ = (k + α₀) / (Δh + β₀)  &nbsp;&nbsp;[flares/hour]<br/>
                      P(≥1 in T hours) = 1 − exp(−λ × T)
                    </div>
                    <p className="text-xs text-slate-500 italic">Situational awareness only — this is transparent, physics-based probabilistic forecasting, not a skillful per-flare prediction.</p>
                  </div>
                </DetailSection>
              </>
            ) : (
              <DetailSection title="No Forecast Available" accent="#eab308">
                <p className="text-sm text-slate-400">No activity forecast was computed for this event. This can happen when there are no spectral flare detections in the event window to estimate the flare rate from.</p>
              </DetailSection>
            )}
          </>
        )}
      </DetailModal>

      {/* --- 4. Observed Class Detail --- */}
      <DetailModal
        open={detailOpen === "class"}
        onClose={closeDetail}
        title="Flare Classification Detail"
        subtitle={event ? `${event.peak_class} flare from ${event.active_region}` : ""}
        accentColor="#a855f7"
      >
        {event && (
          <>
            <DetailSection title="Flare Parameters" accent="#a855f7">
              <div className="grid grid-cols-2 gap-3">
                <DetailStat label="Peak GOES Class" value={event.peak_class} accent="#a855f7" sub="Observed peak soft X-ray flux" />
                <DetailStat label="Severity Tier" value={event.tier} accent={event.tier === "CRITICAL" ? "#ef4444" : "#f97316"} sub="Operational severity classification" />
                <DetailStat label="Active Region" value={event.active_region} accent="#3b82f6" sub="NOAA active region number" />
                <DetailStat label="Provisional (at Stage 3)" value={event.provisional_class} accent="#f97316" sub="Estimated class when forecast fired" />
              </div>
            </DetailSection>

            <DetailSection title="GOES X-ray Classification Scale" accent="#a855f7">
              <DetailTable
                headers={["Class", "Flux Range (W/m²)", "Impact", "Frequency"]}
                rows={[
                  ["A", "< 10⁻⁷", "Negligible", "Very common"],
                  ["B", "10⁻⁷ – 10⁻⁶", "Negligible", "Common"],
                  ["C", "10⁻⁶ – 10⁻⁵", "Minor radio blackouts", "Moderate"],
                  ["M", "10⁻⁵ – 10⁻⁴", "Radio blackouts, radiation storms", "Less common"],
                  ["X", "> 10⁻⁴", "Severe to extreme impacts", "Rare"],
                ]}
              />
              <div className="mt-3 text-xs text-slate-400">
                This event was class <span className="text-purple-400 font-bold">{event.peak_class}</span> — {
                  event.peak_class.startsWith("X") ? "an extremely powerful flare with potential for widespread impacts." :
                  event.peak_class.startsWith("M") ? "a moderate flare with possible radio blackouts." :
                  "a minor event."
                }
              </div>
            </DetailSection>

            {data && data.events.length > 1 && (
              <DetailSection title="All Events in Catalog" accent="#a855f7">
                <DetailTable
                  headers={["Event ID", "Peak Class", "Tier", "Active Region", "Max Stage"]}
                  rows={data.events.map((e) => [
                    e.event_id,
                    e.peak_class,
                    e.tier,
                    e.active_region,
                    `Stage ${e.max_stage}`,
                  ])}
                />
              </DetailSection>
            )}
          </>
        )}
      </DetailModal>

      {/* --- 5. Chart Detail (full analysis) --- */}
      <DetailModal
        open={detailOpen === "chart"}
        onClose={closeDetail}
        title="Flux Monitoring — Full Analysis"
        subtitle={event ? `${event.event_id} (${event.peak_class}) — SoLEXS + HEL1OS light curves` : ""}
        accentColor="#3b82f6"
      >
        {event && (
          <>
            <DetailSection title="Combined Light Curve" accent="#3b82f6">
              <div className="h-[500px] w-full bg-slate-950/50 rounded-lg border border-slate-800/50">
                <FlareChart series={event.series} stages={event.stages} />
              </div>
            </DetailSection>

            <DetailSection title="Time Series Statistics" accent="#3b82f6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <DetailStat
                  label="Data Points"
                  value={String(event.series.t_min.length)}
                  sub="Downsampled from 1s cadence"
                  accent="#3b82f6"
                />
                <DetailStat
                  label="Window Duration"
                  value={`${event.series.t_min[event.series.t_min.length - 1]?.toFixed(1) ?? "?"} min`}
                  sub="Total observation window"
                  accent="#3b82f6"
                />
                <DetailStat
                  label="SoLEXS Peak"
                  value={(() => {
                    const vals = event.series.solexs.filter((v): v is number => v != null);
                    return vals.length ? vals.reduce((a, b) => Math.max(a, b), 0).toExponential(2) : "—";
                  })()}
                  sub="W/m² (soft X-ray)"
                  accent="#3b82f6"
                />
                <DetailStat
                  label="HEL1OS Peak"
                  value={(() => {
                    const vals = event.series.hel1os.filter((v): v is number => v != null);
                    return vals.length ? vals.reduce((a, b) => Math.max(a, b), 0).toExponential(2) : "—";
                  })()}
                  sub="Counts (hard X-ray)"
                  accent="#ef4444"
                />
              </div>
            </DetailSection>

            <DetailSection title="Stage Markers on Chart" accent="#3b82f6">
              <DetailTable
                headers={["Stage", "Name", "Time", "Minutes from Start", "Trigger Source"]}
                rows={event.stages.map((s) => {
                  const alert = event.alerts.find(a => a.stage === s.stage);
                  return [
                    `S${s.stage}`,
                    STAGE_NAMES[s.stage],
                    s.time,
                    s.at_min.toFixed(2),
                    alert?.source ?? "—",
                  ];
                })}
              />
            </DetailSection>

            <DetailSection title="Instruments" accent="#3b82f6">
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg border border-blue-500/30 bg-blue-500/10 p-3">
                  <div className="text-xs font-bold text-blue-400 uppercase tracking-wider">SoLEXS</div>
                  <div className="text-sm text-slate-300 mt-1">Solar Low-Energy X-ray Spectrometer</div>
                  <div className="text-xs text-slate-400 mt-1">Measures soft X-ray flux (1–30 keV). Used for forecasting via derivative analysis.</div>
                </div>
                <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3">
                  <div className="text-xs font-bold text-red-400 uppercase tracking-wider">HEL1OS</div>
                  <div className="text-sm text-slate-300 mt-1">High Energy L1 Orbiting X-ray Spectrometer</div>
                  <div className="text-xs text-slate-400 mt-1">Measures hard X-ray flux (10–150 keV). Used for nowcasting via 3σ spike detection.</div>
                </div>
              </div>
            </DetailSection>
          </>
        )}
      </DetailModal>

      {/* --- 6. Alert Log Detail --- */}
      <DetailModal
        open={detailOpen === "alerts"}
        onClose={closeDetail}
        title="Complete Alert Log"
        subtitle={event ? `All ${event.alerts.length} alerts for ${event.event_id}` : ""}
        accentColor="#94a3b8"
      >
        {event && (
          <>
            <DetailSection title="Alert Timeline" accent="#94a3b8">
              <div className="space-y-2">
                {event.alerts.map((a, i) => (
                  <div key={i} className={`rounded-lg border p-3 ${STAGE_BG[a.stage] ?? "bg-slate-800/40 border-slate-700"}`}>
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-3">
                        <span className={`text-lg font-black ${STAGE_COLORS[a.stage] ?? "text-slate-400"}`}>S{a.stage}</span>
                        <span className="text-sm font-semibold text-slate-100">{a.level}</span>
                      </div>
                      <span className="text-sm font-mono text-slate-300">{a.time}</span>
                    </div>
                    <div className="grid grid-cols-3 gap-2 mt-2">
                      <div>
                        <div className="text-[10px] text-slate-400 uppercase">Provisional Class</div>
                        <div className="text-xs text-slate-200 font-mono">{a.provisional_class}</div>
                      </div>
                      <div>
                        <div className="text-[10px] text-slate-400 uppercase">Confidence</div>
                        <div className="text-xs text-slate-200 font-mono">{(a.confidence * 100).toFixed(0)}%</div>
                        <div className="mt-1 h-1.5 rounded-full bg-slate-700 overflow-hidden">
                          <div
                            className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-emerald-400 transition-all"
                            style={{ width: `${a.confidence * 100}%` }}
                          />
                        </div>
                      </div>
                      <div>
                        <div className="text-[10px] text-slate-400 uppercase">Trigger Source</div>
                        <div className="text-xs text-slate-200 font-mono">{a.source}</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </DetailSection>

            <DetailSection title="Alert Summary Table" accent="#94a3b8">
              <DetailTable
                headers={["Time", "Stage", "Level", "Provisional Class", "Confidence", "Source"]}
                rows={event.alerts.map((a) => [
                  a.time,
                  `S${a.stage}`,
                  a.level,
                  a.provisional_class,
                  `${(a.confidence * 100).toFixed(0)}%`,
                  a.source,
                ])}
              />
            </DetailSection>
          </>
        )}
      </DetailModal>

      {/* --- 7. Spectral Diagnostics Detail --- */}
      <DetailModal
        open={detailOpen === "spectral"}
        onClose={closeDetail}
        title="Spectral Diagnostics — Deep Dive"
        subtitle={event?.spectral ? `${event.spectral.n_flares} flare(s) analyzed from SoLEXS/HEL1OS spectra` : ""}
        accentColor="#f43f5e"
      >
        {event?.spectral && (
          <>
            <DetailSection title="Key Measurements" accent="#f43f5e">
              <div className="grid grid-cols-2 gap-3">
                <DetailStat label="Plasma Temperature" value={`${event.spectral.peak_temperature_MK.toFixed(0)} MK`} sub={`${event.spectral.peak_temperature_keV.toFixed(1)} keV (1 keV ≈ 11.6 MK)`} accent="#f43f5e" />
                <DetailStat label="Spectral Index (γ)" value={event.spectral.spectral_index_at_peak != null ? event.spectral.spectral_index_at_peak.toFixed(2) : "—"} sub="HEL1OS power-law fit at flare peak" accent="#f59e0b" />
                <DetailStat label="Hardness Ratio" value={event.spectral.peak_hardness_ratio.toFixed(3)} sub="Hard X-ray / Soft X-ray intensity" accent="#f97316" />
                <DetailStat label="Hottest Flare" value={event.spectral.hottest_flare_time} sub="Timestamp of peak temperature" accent="#f1f5f9" />
              </div>
            </DetailSection>

            <DetailSection title="What These Measurements Mean" accent="#f43f5e">
              <div className="space-y-3 text-sm text-slate-300">
                <div className="rounded-lg border border-rose-500/20 bg-rose-500/5 p-3">
                  <div className="font-semibold text-rose-400 mb-1 flex items-center gap-2"><Thermometer className="w-4 h-4" /> Plasma Temperature</div>
                  <p className="text-slate-400">The temperature of the coronal plasma during the flare, estimated from the SoLEXS soft X-ray spectrum. Temperatures above ~15 MK indicate intense reconnection events.</p>
                </div>
                <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3">
                  <div className="font-semibold text-amber-400 mb-1">Spectral Index (γ)</div>
                  <p className="text-slate-400">The power-law slope of the HEL1OS hard X-ray spectrum. Lower values (harder spectrum, γ &lt; 4) indicate more efficient particle acceleration — a sign of a more impulsive, energetic flare.</p>
                </div>
                <div className="rounded-lg border border-orange-500/20 bg-orange-500/5 p-3">
                  <div className="font-semibold text-orange-400 mb-1">Hardness Ratio</div>
                  <p className="text-slate-400">Ratio of hard-to-soft X-ray intensity. Higher ratios indicate a larger fraction of non-thermal emission (accelerated particles) vs. thermal plasma — correlates with SEP (Solar Energetic Particle) events.</p>
                </div>
              </div>
            </DetailSection>

            <DetailSection title="Flare Statistics" accent="#f43f5e">
              <div className="text-sm text-slate-400">
                <p>Total flares analyzed in this event window: <span className="text-rose-400 font-bold">{event.spectral.n_flares}</span></p>
                <p className="mt-1">The representative flare shown is selected as the one with the highest hardness ratio (most energetic particle acceleration), falling back to the hottest thermal flare if no hard X-ray detection was registered.</p>
              </div>
            </DetailSection>
          </>
        )}
      </DetailModal>

      {/* --- 8. Individual Impact Domain Detail --- */}
      <DetailModal
        open={detailOpen === "impact_domain"}
        onClose={closeDetail}
        title={`Impact Detail — ${DOMAIN_TITLES[detailDomainKey] ?? detailDomainKey}`}
        subtitle={event?.impact ? `Based on ${event.impact.flare_class} flare (R${event.impact.r_scale} scale)` : ""}
        accentColor={(() => {
          const d = event?.impact?.domains[detailDomainKey];
          if (!d) return "#f97316";
          const l = d.level.toUpperCase();
          if (l.includes("HIGH") || l.includes("ELEVATED") || l >= "R3") return "#ef4444";
          if (l.includes("WATCH") || l.includes("MODERATE")) return "#f97316";
          return "#10b981";
        })()}
      >
        {event?.impact?.domains[detailDomainKey] && (() => {
          const d = event.impact!.domains[detailDomainKey];
          return (
            <>
              <DetailSection title="Threat Level" accent="#f97316">
                <div className="flex items-center gap-4">
                  <span className={`px-5 py-3 rounded-xl border text-lg font-black ${levelBadgeColor(d.level)}`}>
                    {d.level}
                  </span>
                  <div className="text-sm text-slate-300">
                    Severity level for <span className="font-semibold text-slate-100">{DOMAIN_TITLES[detailDomainKey]}</span> based on {event.impact!.flare_class} flare classification.
                  </div>
                </div>
              </DetailSection>

              <DetailSection title="Expected Impact" accent="#ef4444">
                <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-4">
                  <p className="text-sm text-slate-200">{d.impact}</p>
                </div>
              </DetailSection>

              <DetailSection title="Recommended Action" accent="#10b981">
                <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-4">
                  <p className="text-sm text-slate-200">{d.advisory}</p>
                </div>
              </DetailSection>

              <DetailSection title="Assessment Basis" accent="#94a3b8">
                <p className="text-sm text-slate-400">{d.basis}</p>
              </DetailSection>

              {/* Show all domains for comparison */}
              <DetailSection title="All Impact Domains — Comparison" accent="#94a3b8">
                <DetailTable
                  headers={["Domain", "Level", "Impact Summary"]}
                  rows={Object.entries(event.impact!.domains).map(([k, dom]) => [
                    DOMAIN_TITLES[k] ?? k,
                    dom.level,
                    dom.impact.slice(0, 80) + (dom.impact.length > 80 ? "…" : ""),
                  ])}
                />
              </DetailSection>
            </>
          );
        })()}
      </DetailModal>
    </div>
  );
}

/* ================================================================== */
/* Sub-components                                                     */
/* ================================================================== */

function LiveClock() {
  // Start null so server and first client render match (no hydration mismatch);
  // the real time is filled in only after mount.
  const [now, setNow] = useState<Date | null>(null);
  useEffect(() => {
    setNow(new Date());
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);
  const pad = (n: number) => String(n).padStart(2, '0');
  const fmtUtc = (d: Date) =>
    `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())} ` +
    `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:${pad(d.getUTCSeconds())} UTC`;
  const fmtIst = (d: Date) => {
    const ist = new Date(d.getTime() + 5.5 * 3_600_000);
    return `${pad(ist.getUTCHours())}:${pad(ist.getUTCMinutes())}:${pad(ist.getUTCSeconds())} IST`;
  };
  return (
    <div className="hidden md:flex flex-col items-end font-mono text-xs leading-tight select-none">
      <span className="text-blue-400">{now ? fmtUtc(now) : "————-——-—— ——:——:—— UTC"}</span>
      <span className="text-orange-400">{now ? fmtIst(now) : "——:——:—— IST"}</span>
    </div>
  );
}

interface KPICardProps {
  title: string;
  value: string;
  subtitle: string;
  icon: React.ReactNode;
  gradient: string;
  border: string;
  alert?: boolean;
  onClick?: () => void;
  delayMs?: number;
}

function KPICard({ title, value, subtitle, icon, gradient, border, alert, onClick, delayMs }: KPICardProps) {
  return (
    <div
      className={`relative overflow-hidden rounded-xl border ${border} bg-gradient-to-br ${gradient} p-5 backdrop-blur-md shadow-lg card-clickable group animate-rise-in`}
      style={delayMs != null ? { animationDelay: `${delayMs}ms` } : undefined}
      onClick={onClick}
    >
      {alert && (
        <div className="absolute top-0 right-0 p-3">
          <span className="flex h-3 w-3 relative">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-orange-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3 w-3 bg-orange-500"></span>
          </span>
        </div>
      )}
      <div className="flex items-center gap-3 mb-2">
        <div className="p-2 bg-slate-950/50 rounded-lg border border-slate-800/50 shadow-inner">{icon}</div>
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{title}</h3>
      </div>
      <div className="mt-4 flex items-end justify-between">
        <div>
          <div className="text-2xl font-bold tracking-tight text-slate-100">{value}</div>
          <div className="text-xs text-slate-500 mt-1">{subtitle}</div>
        </div>
        <ChevronRight className="w-4 h-4 text-slate-600 group-hover:text-slate-300 transition-colors mb-1" />
      </div>
    </div>
  );
}

function LogEntry({ time, stage, msg }: { time: string; stage: number; msg: string }) {
  return (
    <div className="flex items-start gap-2 pb-2 border-b border-slate-800/50 last:border-0">
      <span className="text-slate-500 shrink-0">[{time}]</span>
      <span className={`${STAGE_COLORS[stage] ?? "text-slate-400"} font-semibold shrink-0`}>S{stage}</span>
      <span className="text-slate-300">{msg}</span>
    </div>
  );
}
