"use client";

import React from "react";
import { Zap, ShieldAlert, ChevronRight, Radio, Satellite, Plane, User, BatteryCharging } from "lucide-react";

export interface ActivityForecast {
  peak_p_6h: number;
  peak_p_24h: number;
  peak_level: string;
  peak_time: string;
}

export interface ImpactDomain {
  level: string;
  impact: string;
  advisory: string;
  basis: string;
}

export interface ImpactData {
  flare_class: string;
  r_scale: number;
  domains: Record<string, ImpactDomain>;
}

const DOMAIN_TITLES: Record<string, string> = {
  radio_blackout: "Radio",
  gps_navigation: "GPS/Nav",
  aviation: "Aviation",
  satellite: "Satellites",
  astronaut_radiation: "Radiation",
  power_grid: "Power Grid",
};

const DOMAIN_ICONS: Record<string, React.ReactNode> = {
  radio_blackout: <Radio className="w-3 h-3" />,
  gps_navigation: <Satellite className="w-3 h-3" />,
  aviation: <Plane className="w-3 h-3" />,
  satellite: <Satellite className="w-3 h-3" />,
  astronaut_radiation: <User className="w-3 h-3" />,
  power_grid: <BatteryCharging className="w-3 h-3" />,
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

interface ForecastPanelProps {
  activityForecast: ActivityForecast | null | undefined;
  impact: ImpactData | null | undefined;
  onForecastClick?: () => void;
  onDomainClick?: (key: string) => void;
}

export default function ForecastPanel({ activityForecast, impact, onForecastClick, onDomainClick }: ForecastPanelProps) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 shadow-xl">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-orange-400" />
          Forecast &amp; Impact
          {impact && (
            <span className="ml-2 text-xs font-mono text-orange-300">
              Radio Blackout R{impact.r_scale}
            </span>
          )}
        </h2>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Forecast gauges — Layer A Poisson activity rate */}
        <div
          className={`lg:col-span-1 rounded-lg border border-yellow-500/20 bg-yellow-500/5 p-3 ${onForecastClick ? "card-clickable hover:border-yellow-500/40" : ""}`}
          onClick={onForecastClick}
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-yellow-400 flex items-center gap-1">
              <Zap className="w-3 h-3" /> Activity Forecast
            </span>
            {onForecastClick && <ChevronRight className="w-3 h-3 text-slate-600" />}
          </div>
          {activityForecast ? (
            <>
              <div className="grid grid-cols-2 gap-2 mb-2">
                <div className="text-center rounded-md bg-slate-950/40 py-1.5">
                  <div className="text-lg font-black text-yellow-400">{(activityForecast.peak_p_6h * 100).toFixed(0)}%</div>
                  <div className="text-[8px] text-slate-500 uppercase">6h</div>
                </div>
                <div className="text-center rounded-md bg-slate-950/40 py-1.5">
                  <div className="text-lg font-black text-orange-400">{(activityForecast.peak_p_24h * 100).toFixed(0)}%</div>
                  <div className="text-[8px] text-slate-500 uppercase">24h</div>
                </div>
              </div>
              <span className={`inline-block px-2 py-0.5 rounded-full border text-[9px] font-bold ${levelBadgeColor(activityForecast.peak_level)}`}>
                {activityForecast.peak_level}
              </span>
              <p className="text-[9px] text-slate-500 mt-2 italic">Poisson activity rate — situational awareness, not a per-flare prediction.</p>
            </>
          ) : (
            <p className="text-[10px] text-slate-500">No activity forecast computed for this event.</p>
          )}
        </div>

        {/* Impact domains grid */}
        <div className="lg:col-span-2 grid grid-cols-2 md:grid-cols-3 gap-2">
          {impact ? (
            Object.entries(impact.domains).map(([key, d]) => (
              <div
                key={key}
                className={`rounded-lg border p-2 card-clickable ${levelColor(d.level)}`}
                onClick={() => onDomainClick?.(key)}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-[9px] font-semibold uppercase tracking-wider text-slate-200 flex items-center gap-1">
                    {DOMAIN_ICONS[key]}
                    {DOMAIN_TITLES[key] ?? key}
                  </span>
                  <span className="text-[9px] font-bold">{d.level}</span>
                </div>
                <p className="text-[9px] text-slate-300 line-clamp-2">{d.impact}</p>
              </div>
            ))
          ) : (
            <div className="col-span-3 flex items-center justify-center py-6">
              <p className="text-[10px] text-slate-500">No impact assessment for this event.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
