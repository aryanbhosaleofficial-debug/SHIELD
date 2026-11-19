"use client";

import React from "react";
import { Telescope, BadgeCheck } from "lucide-react";

/**
 * Real VELC (Visible Emission Line Coronagraph) spectrogram from Aditya-L1.
 * The image at /velc_real.png is rendered from an actual VS1 Level-1 FITS
 * file pulled from ISRO PRADAN — not simulated. This is the differentiator:
 * no GOES-based project can show real Indian coronagraph data.
 */
export default function VelcSpectrogramCard() {
  return (
    <div className="rounded-xl border border-rose-500/25 bg-slate-900/50 p-4 shadow-xl">
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-300 flex items-center gap-2">
          <Telescope className="w-4 h-4 text-rose-400" />
          VELC — Coronal Spectroscopy
          <span className="ml-1 text-[11px] font-normal text-slate-500">
            Visible Emission Line Coronagraph
          </span>
        </h2>
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-emerald-500/40 bg-emerald-500/10">
          <BadgeCheck className="w-3.5 h-3.5 text-emerald-400" />
          <span className="text-[10px] font-bold uppercase tracking-widest text-emerald-400">
            Real Aditya-L1 Data
          </span>
        </span>
      </div>

      {/* The real spectrogram */}
      <div className="rounded-lg overflow-hidden border border-slate-800 bg-black">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/velc_real.png"
          alt="Real VELC VS1 coronal spectrogram from Aditya-L1"
          className="w-full h-[150px] object-cover"
        />
      </div>

      {/* Metadata strip */}
      <div className="mt-3 grid grid-cols-2 md:grid-cols-5 gap-2 text-[10px] font-mono">
        {[
          ["Detector", "VS1"],
          ["Date-Obs", "2026-06-27"],
          ["Time UTC", "11:59:02"],
          ["Gain", "High"],
          ["Level", "L1 · 320×2160"],
        ].map(([k, v]) => (
          <div key={k} className="rounded-md border border-slate-800 bg-slate-950/40 px-2 py-1.5">
            <div className="text-slate-500 uppercase tracking-wider text-[8px]">{k}</div>
            <div className="text-rose-300">{v}</div>
          </div>
        ))}
      </div>

      <p className="mt-2.5 text-[11px] text-slate-400 leading-relaxed">
        Bright bands are <span className="text-rose-300">coronal emission lines</span> dispersed across
        the VELC slit, imaging the inner corona at the L1 vantage point.
        <span className="text-slate-500"> Roadmap: </span>
        CME detection from VELC feeds geomagnetic-storm (G-scale) forecasting — completing the
        Sun-to-Earth hazard chain.
      </p>
    </div>
  );
}
