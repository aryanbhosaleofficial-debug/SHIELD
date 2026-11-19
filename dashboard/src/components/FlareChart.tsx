"use client";

import dynamic from 'next/dynamic';
import React from 'react';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

export interface FlareSeries {
  t_min: number[];
  solexs: (number | null)[];
  hel1os: (number | null)[];
  solexs_deriv: (number | null)[];
}

export interface StageMark {
  stage: number;
  time: string;
  iso?: string;
  at_min: number;
}

interface FlareChartProps {
  series: FlareSeries;
  stages: StageMark[];
  isLive?: boolean;
  fixedXMax?: number;
}

function stageShape(at: number, color: string) {
  return {
    type: 'line' as const,
    x0: at, x1: at, yref: 'paper' as const, y0: 0, y1: 1,
    line: { color, width: 2, dash: 'dash' as const },
  };
}

export default function FlareChart({ series, stages, isLive, fixedXMax }: FlareChartProps) {
  const forecast = stages.find((s) => s.stage === 3);
  const nowcast  = stages.find((s) => s.stage === 4);

  const shapes: ReturnType<typeof stageShape>[] = [];
  const annotations: object[] = [];
  if (forecast) {
    shapes.push(stageShape(forecast.at_min, '#f97316'));
    annotations.push({
      x: forecast.at_min, y: 1, yref: 'paper' as const, text: 'FORECAST',
      showarrow: false, font: { color: '#f97316', size: 10 }, yanchor: 'bottom' as const,
    });
  }
  if (nowcast) {
    shapes.push(stageShape(nowcast.at_min, '#ef4444'));
    annotations.push({
      x: nowcast.at_min, y: 1, yref: 'paper' as const, text: 'NOWCAST',
      showarrow: false, font: { color: '#ef4444', size: 10 }, yanchor: 'bottom' as const,
    });
  }

  const xRange: [number, number] | undefined = fixedXMax != null ? [0, fixedXMax] : undefined;

  return (
    <div className="relative w-full h-full min-h-[400px]">
      {isLive && (
        <div className="absolute top-3 right-3 z-10 flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-red-500/20 border border-red-500/40 backdrop-blur-sm">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500" />
          </span>
          <span className="text-[10px] font-bold text-red-400 uppercase tracking-widest">Live</span>
        </div>
      )}
      <Plot
        data={[
          {
            x: series.t_min,
            y: series.solexs,
            type: 'scatter',
            mode: 'lines',
            name: 'SoLEXS (Soft X-ray)',
            line: { color: '#3b82f6', width: 2 },
            fill: 'tozeroy',
            fillcolor: 'rgba(59, 130, 246, 0.1)',
          },
          {
            x: series.t_min,
            y: series.hel1os,
            type: 'scatter',
            mode: 'lines',
            name: 'HEL1OS (Hard X-ray)',
            line: { color: '#ef4444', width: 2 },
            yaxis: 'y2',
          },
        ]}
        layout={{
          autosize: true,
          paper_bgcolor: 'transparent',
          plot_bgcolor: 'transparent',
          margin: { t: 20, r: 50, b: 40, l: 50 },
          font: { color: '#9ca3af' },
          shapes,
          annotations,
          xaxis: {
            showgrid: true,
            gridcolor: '#1f2937',
            title: 'Time (minutes from window start)',
            range: xRange,
          },
          yaxis:  { showgrid: true, gridcolor: '#1f2937', title: 'Flux (SoLEXS, W/m²)', type: 'log' },
          yaxis2: { overlaying: 'y', side: 'right', title: 'Flux (HEL1OS)', showgrid: false, type: 'log' },
          legend: { orientation: 'h', y: -0.2 },
        }}
        useResizeHandler={true}
        style={{ width: '100%', height: '100%' }}
        config={{ responsive: true, displayModeBar: false }}
      />
    </div>
  );
}
