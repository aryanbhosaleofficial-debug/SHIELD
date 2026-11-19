"use client";

import React from "react";
import { Zap, ChevronRight } from "lucide-react";

export interface SpectralData {
  n_flares: number;
  peak_temperature_keV: number;
  peak_temperature_MK: number;
  spectral_index_at_peak: number | null;
  peak_hardness_ratio: number;
  hottest_flare_time: string;
}

interface VelcDataCardProps {
  spectral: SpectralData | null | undefined;
  onClick?: () => void;
}

/**
 * Wireframe slot is labelled "VELC / Spectral Data" — VELC (coronagraph) is
 * not yet integrated (roadmap), so this card surfaces the spectral
 * diagnostics SHIELD already derives from SoLEXS/HEL1OS (plasma temperature,
 * spectral index, hardness ratio) in the same panel position.
 */
export default function VelcDataCard({ spectral, onClick }: VelcDataCardProps) {
  // Temperature gauge: 0-100 MK clamp for the bar fill.
  const tempPct = spectral ? Math.min(100, (spectral.peak_temperature_MK / 100) * 100) : 0;

  return (
    <div
      className="rounded-xl border border-rose-500/20 bg-slate-900/50 p-3 h-full flex flex-col card-clickable hover:border-rose-500/40"
      onClick={onClick}
    >
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-[10px] font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
          <Zap className="w-3 h-3 text-rose-400" />
          VELC / Spectral
        </h3>
        {onClick && <ChevronRight className="w-3 h-3 text-slate-600" />}
      </div>

      {spectral ? (
        <div className="space-y-2.5 flex-1">
          <div>
            <div className="flex items-center justify-between text-[9px] text-slate-400 mb-1">
              <span>Plasma Temp</span>
              <span className="font-mono text-rose-400 font-bold">{spectral.peak_temperature_MK.toFixed(0)} MK</span>
            </div>
            <div className="h-1.5 rounded-full bg-slate-800 overflow-hidden">
              <div className="h-full rounded-full bg-gradient-to-r from-rose-600 to-rose-400" style={{ width: `${tempPct}%` }} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2 text-[9px]">
            <div>
              <div className="text-slate-500 uppercase">Spec. Index γ</div>
              <div className="font-mono text-amber-400 text-xs">
                {spectral.spectral_index_at_peak != null ? spectral.spectral_index_at_peak.toFixed(2) : "—"}
              </div>
            </div>
            <div>
              <div className="text-slate-500 uppercase">Hardness</div>
              <div className="font-mono text-orange-400 text-xs">{spectral.peak_hardness_ratio.toFixed(2)}</div>
            </div>
          </div>
          <div className="text-[9px] text-slate-500 border-t border-slate-800 pt-1.5">
            Peak: <span className="text-slate-300 font-mono">{spectral.hottest_flare_time}</span>
          </div>
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center text-center px-2">
          <p className="text-[10px] text-slate-500">No spectral flares analyzed in this window</p>
        </div>
      )}
    </div>
  );
}
