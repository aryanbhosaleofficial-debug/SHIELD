"use client";

import dynamic from 'next/dynamic';
import React from 'react';
import type { FlareSeries, StageMark } from './FlareChart';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface Hel1osChartProps {
  series: FlareSeries;
  stages: StageMark[];
}

/** Simple rolling mean/std for a visual baseline band (client-side, not a detection signal). */
function rollingBand(vals: (number | null)[], window = 15) {
  const mean: (number | null)[] = [];
  const upper: (number | null)[] = [];
  const lower: (number | null)[] = [];
  for (let i = 0; i < vals.length; i++) {
    const lo = Math.max(0, i - window);
    const slice = vals.slice(lo, i + 1).filter((v): v is number => v != null);
    if (!slice.length) { mean.push(null); upper.push(null); lower.push(null); continue; }
    const m = slice.reduce((a, b) => a + b, 0) / slice.length;
    const variance = slice.reduce((a, b) => a + (b - m) ** 2, 0) / slice.length;
    const sd = Math.sqrt(variance);
    mean.push(m);
    upper.push(m + 3 * sd);
    lower.push(Math.max(m - 3 * sd, 0.0001));
  }
  return { mean, upper, lower };
}

export default function Hel1osChart({ series, stages }: Hel1osChartProps) {
  const nowcast = stages.find((s) => s.stage === 4);
  const { upper, lower } = rollingBand(series.hel1os);

  const shapes = [];
  const annotations = [];
  if (nowcast) {
    shapes.push({
      type: 'line' as const,
      x0: nowcast.at_min, x1: nowcast.at_min, yref: 'paper' as const, y0: 0, y1: 1,
      line: { color: '#ef4444', width: 2, dash: 'dash' as const },
    });
    annotations.push({
      x: nowcast.at_min, y: 1, yref: 'paper' as const, text: 'S4 3σ SPIKE',
      showarrow: false, font: { color: '#ef4444', size: 9 }, yanchor: 'bottom' as const,
    });
  }

  return (
    <div className="w-full h-full min-h-[260px]">
      <Plot
        data={[
          {
            x: series.t_min,
            y: upper,
            type: 'scatter',
            mode: 'lines',
            name: '3σ band',
            line: { color: 'rgba(239,68,68,0.0)', width: 0 },
            showlegend: false,
            hoverinfo: 'skip',
          },
          {
            x: series.t_min,
            y: lower,
            type: 'scatter',
            mode: 'lines',
            name: '3σ baseline band',
            line: { color: 'rgba(239,68,68,0.0)', width: 0 },
            fill: 'tonexty',
            fillcolor: 'rgba(239, 68, 68, 0.08)',
          },
          {
            x: series.t_min,
            y: series.hel1os,
            type: 'scatter',
            mode: 'lines',
            name: 'HEL1OS Flux',
            line: { color: '#ef4444', width: 2 },
          },
        ]}
        layout={{
          autosize: true,
          paper_bgcolor: 'transparent',
          plot_bgcolor: 'transparent',
          margin: { t: 16, r: 16, b: 36, l: 46 },
          font: { color: '#9ca3af', size: 10 },
          shapes,
          annotations,
          xaxis: { showgrid: true, gridcolor: '#1f2937', title: 'Minutes from start' },
          yaxis: { showgrid: true, gridcolor: '#1f2937', title: 'HEL1OS (counts)', type: 'log' },
          legend: { orientation: 'h', y: -0.28, font: { size: 9 } },
        }}
        useResizeHandler={true}
        style={{ width: '100%', height: '100%' }}
        config={{ responsive: true, displayModeBar: false }}
      />
    </div>
  );
}
