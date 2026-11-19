"use client";

import React, { useEffect, useCallback } from "react";
import { X } from "lucide-react";

interface DetailModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  accentColor?: string;
  children: React.ReactNode;
}

/**
 * Full-screen glassmorphism overlay that slides in from the right.
 * Close via × button, Escape key, or backdrop click.
 */
export default function DetailModal({
  open,
  onClose,
  title,
  subtitle,
  accentColor = "#3b82f6",
  children,
}: DetailModalProps) {
  const handleKey = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    },
    [onClose]
  );

  useEffect(() => {
    if (open) {
      document.addEventListener("keydown", handleKey);
      document.body.style.overflow = "hidden";
    }
    return () => {
      document.removeEventListener("keydown", handleKey);
      document.body.style.overflow = "";
    };
  }, [open, handleKey]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-stretch justify-end">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm animate-fade-in"
        onClick={onClose}
      />

      {/* Panel */}
      <div className="relative w-full max-w-3xl bg-slate-950/95 border-l border-slate-700/50 backdrop-blur-xl shadow-2xl animate-slide-in-right overflow-y-auto">
        {/* Accent top bar */}
        <div
          className="h-1 w-full"
          style={{ background: `linear-gradient(90deg, ${accentColor}, transparent)` }}
        />

        {/* Header */}
        <div className="sticky top-0 z-10 bg-slate-950/90 backdrop-blur-md border-b border-slate-800/50 px-6 py-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold tracking-wide text-slate-100">{title}</h2>
            {subtitle && (
              <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg border border-slate-700 bg-slate-800/50 hover:bg-slate-700 transition-colors group"
            aria-label="Close detail panel"
          >
            <X className="w-4 h-4 text-slate-400 group-hover:text-white transition-colors" />
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-6 space-y-6">{children}</div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Reusable sub-components for detail views                           */
/* ------------------------------------------------------------------ */

export function DetailSection({
  title,
  children,
  accent,
}: {
  title: string;
  children: React.ReactNode;
  accent?: string;
}) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4 space-y-3 backdrop-blur-sm">
      <h3
        className="text-xs font-semibold uppercase tracking-wider"
        style={{ color: accent || "#94a3b8" }}
      >
        {title}
      </h3>
      {children}
    </div>
  );
}

export function DetailStat({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string;
  sub?: string;
  accent?: string;
}) {
  return (
    <div className="rounded-lg border border-slate-700/50 bg-slate-800/40 p-3">
      <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">
        {label}
      </div>
      <div
        className="text-xl font-bold mt-1"
        style={{ color: accent || "#f1f5f9" }}
      >
        {value}
      </div>
      {sub && <div className="text-xs text-slate-500 mt-0.5">{sub}</div>}
    </div>
  );
}

export function DetailTable({
  headers,
  rows,
}: {
  headers: string[];
  rows: (string | number)[][];
}) {
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-800">
      <table className="w-full text-xs">
        <thead>
          <tr className="bg-slate-800/60">
            {headers.map((h, i) => (
              <th
                key={i}
                className="px-3 py-2 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-400"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, ri) => (
            <tr
              key={ri}
              className="border-t border-slate-800/50 hover:bg-slate-800/30 transition-colors"
            >
              {row.map((cell, ci) => (
                <td key={ci} className="px-3 py-2 text-slate-300 font-mono">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
