"use client";

import React, { useState } from "react";
import { Clock } from "lucide-react";
import type { FlareSeries, StageMark } from "./FlareChart";

const STAGE_NAMES: Record<number, string> = {
  1: "QUIET SUN",
  2: "PRE-FLARE HEATING",
  3: "FORECAST ALERT",
  4: "NOWCAST CONFIRMED",
};

const STAGE_COLORS: Record<number, string> = {
  1: "#10b981",
  2: "#eab308",
  3: "#f97316",
  4: "#ef4444",
};

interface FluxSidebarProps {
  series: FlareSeries;
  stages: StageMark[];
  maxStage: number;
}

function lastNonNull(arr: (number | null)[]): number | null {
  for (let i = arr.length - 1; i >= 0; i--) {
    if (arr[i] != null) return arr[i] as number;
  }
  return null;
}

export default function FluxSidebar({ series, stages, maxStage }: FluxSidebarProps) {
  const [tz, setTz] = useState<"UTC" | "IST">("UTC");

  const latestSolexs = lastNonNull(series.solexs);
  const latestHel1os = lastNonNull(series.hel1os);

  const eventTime = (() => {
    if (!stages.length) return null;
    const s0 = stages[0];
    const epoch = Date.parse((s0.iso ?? s0.time) + "Z");
    if (isNaN(epoch)) return null;
    const windowStart = epoch - s0.at_min * 60_000;
    const lastT = series.t_min[series.t_min.length - 1] ?? 0;
    return new Date(windowStart + lastT * 60_000);
  })();

  const fmt = (d: Date, zone: "UTC" | "IST") => {
    const t = zone === "IST" ? new Date(d.getTime() + 5.5 * 3_600_000) : d;
    const pad = (n: number) => String(n).padStart(2, "0");
    return `${t.getUTCFullYear()}-${pad(t.getUTCMonth() + 1)}-${pad(t.getUTCDate())} ` +
           `${pad(t.getUTCHours())}:${pad(t.getUTCMinutes())}:${pad(t.getUTCSeconds())}`;
  };

  return (
    <div className="h-full rounded-xl border border-slate-800 bg-slate-900/50 p-4 shadow-xl flex flex-col">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2 mb-3">
        <Clock className="w-3.5 h-3.5 text-emerald-400" />
        Flux &amp; Time
      </h3>

      {/* Current flux readout */}
      <div className="space-y-2 mb-4">
        <div className="rounded-lg border border-blue-500/20 bg-blue-500/5 px-2.5 py-1.5">
          <div className="text-[10px] text-blue-400 uppercase tracking-wider font-semibold">SoLEXS</div>
          <div className="text-sm font-mono text-slate-100">
            {latestSolexs != null ? latestSolexs.toExponential(2) : "—"}
          </div>
        </div>
        <div className="rounded-lg border border-red-500/20 bg-red-500/5 px-2.5 py-1.5">
          <div className="text-[10px] text-red-400 uppercase tracking-wider font-semibold">HEL1OS</div>
          <div className="text-sm font-mono text-slate-100">
            {latestHel1os != null ? latestHel1os.toExponential(2) : "—"}
          </div>
        </div>
      </div>

      {/* UTC / IST toggle */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-1">
          <span className="text-[10px] text-slate-500 uppercase tracking-wider">Window End</span>
          <button
            onClick={() => setTz((z) => (z === "UTC" ? "IST" : "UTC"))}
            className="text-[10px] font-bold px-1.5 py-0.5 rounded border border-slate-700 text-slate-400 hover:text-emerald-400 hover:border-emerald-500/40"
          >
            {tz}
          </button>
        </div>
        <div className="text-xs font-mono text-emerald-400">
          {eventTime ? `${fmt(eventTime, tz)} ${tz}` : "—"}
        </div>
      </div>

      {/* 4-stage vertical indicator */}
      <div className="flex-1 flex flex-col gap-1.5 justify-end">
        {[4, 3, 2, 1].map((s) => {
          const reached = s <= maxStage;
          return (
            <div
              key={s}
              className="flex items-center gap-2 rounded-md px-2 py-1.5 border transition-all"
              style={{
                borderColor: reached ? STAGE_COLORS[s] + "55" : "#1e293b",
                backgroundColor: reached ? STAGE_COLORS[s] + "14" : "transparent",
                opacity: reached ? 1 : 0.35,
              }}
            >
              <span
                className="w-2 h-2 rounded-full shrink-0"
                style={{ backgroundColor: reached ? STAGE_COLORS[s] : "#475569" }}
              />
              <span className="text-[10px] font-mono font-bold" style={{ color: reached ? STAGE_COLORS[s] : "#64748b" }}>
                S{s}
              </span>
              <span className="text-[9px] text-slate-400 uppercase tracking-tight truncate">
                {STAGE_NAMES[s]}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
