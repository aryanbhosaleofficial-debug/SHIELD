"use client";

import React from "react";
import { Sun, BadgeCheck } from "lucide-react";

interface SuitImageCardProps {
  label: string;
  /** Real SUIT image URL (in /public). When present, shows the real frame. */
  src?: string;
  filter?: string;
  wavelengthNm?: number;
  time?: string;
  /** Info-mode text when there's no image to show. */
  note?: string;
}

/**
 * SUIT (Solar Ultraviolet Imaging Telescope) near-UV solar image card.
 * When `src` is set it renders a REAL Aditya-L1 SUIT frame (rendered from a
 * Level-1 FITS pulled from PRADAN). Otherwise it shows an honest placeholder.
 */
export default function SuitImageCard({ label, src, filter, wavelengthNm, time, note }: SuitImageCardProps) {
  if (src) {
    return (
      <div className="relative rounded-xl border border-orange-500/30 bg-slate-900/50 overflow-hidden flex flex-col">
        <div className="relative aspect-square overflow-hidden bg-black">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={src} alt={`Real SUIT ${filter ?? ""} solar image`} className="w-full h-full object-cover" />
          <span className="absolute top-1.5 left-1.5 inline-flex items-center gap-1 px-1.5 py-0.5 rounded-full border border-emerald-500/50 bg-black/60 backdrop-blur-sm">
            <BadgeCheck className="w-3 h-3 text-emerald-400" />
            <span className="text-[8px] font-bold uppercase tracking-widest text-emerald-400">Real</span>
          </span>
        </div>
        <div className="px-2 py-1.5">
          <div className="text-[10px] font-bold text-orange-300 uppercase tracking-wider">{label}</div>
          <div className="text-[9px] text-slate-400 font-mono">
            {wavelengthNm ? `${wavelengthNm} nm` : ""}{filter ? ` · ${filter}` : ""}
          </div>
          {time && <div className="text-[9px] text-slate-500 font-mono">{time}</div>}
        </div>
      </div>
    );
  }

  if (note) {
    return (
      <div className="rounded-xl border border-orange-500/15 bg-slate-900/40 p-3 flex flex-col items-center justify-center text-center aspect-square">
        <Sun className="w-7 h-7 text-orange-500/40 mb-2" />
        <div className="text-[10px] font-bold uppercase tracking-wider text-orange-400/70">{label}</div>
        <div className="text-[9px] text-slate-500 mt-1 leading-snug">{note}</div>
      </div>
    );
  }

  return (
    <div className="relative rounded-xl border border-orange-500/20 bg-slate-900/50 p-3 flex flex-col items-center justify-center aspect-square overflow-hidden">
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="relative">
          <Sun className="w-10 h-10 text-orange-500/30" />
          <div className="absolute inset-0 bg-orange-500/10 blur-xl rounded-full animate-pulse" />
        </div>
      </div>
      <div className="relative z-10 text-center mt-12">
        <div className="text-[10px] font-bold uppercase tracking-wider text-orange-400/70">{label}</div>
        <div className="text-[9px] text-slate-500 mt-1">No SUIT coverage</div>
        <div className="text-[9px] text-slate-600">this window</div>
      </div>
    </div>
  );
}
