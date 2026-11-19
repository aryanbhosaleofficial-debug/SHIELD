"use client";

import dynamic from 'next/dynamic';
import React from 'react';
import type { FlareSeries, StageMark } from './FlareChart';

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false });

interface SolexsChartProps {
  series: FlareSeries;
  stages: StageMark[];
}

export default function SolexsChart({ series, stages }: SolexsChartProps) {
  const forecast = stages.find((s) => s.stage === 3);

  const shapes = [];
  const annotations = [];
  if (forecast) {
    shapes.push({
      type: 'line' as const,
      x0: forecast.at_min, x1: forecast.at_min, yref: 'paper' as const, y0: 0, y1: 1,
      line: { color: '#f97316', width: 2, dash: 'dash' as const },
    });
    annotations.push({
      x: forecast.at_min, y: 1, yref: 'paper' as const, text: 'S3 SLOPE STEEPENING',
      showarrow: false, font: { color: '#f97316', size: 9 }, yanchor: 'bottom' as const,
    });
  }

  // Derivative scaled for visual overlay against the log flux axis.
  const derivVals = series.solexs_deriv.filter((v): v is number => v != null);
  const derivMax = derivVals.length ? Math.max(...derivVals.map(Math.abs)) : 1;
  const fluxVals = series.solexs.filter((v): v is number => v != null);
  const fluxMax = fluxVals.length ? Math.max(...fluxVals) : 1;
  const derivScaled = series.solexs_deriv.map((v) =>
    v == null ? null : (v / (derivMax || 1)) * fluxMax * 0.4
  );

  return (
    <div className="w-full h-full min-h-[260px]">
      <Plot
        data={[
          {
            x: series.t_min,
            y: series.solexs,
            type: 'scatter',
            mode: 'lines',
            name: 'SoLEXS Flux',
            line: { color: '#3b82f6', width: 2 },
            fill: 'tozeroy',
            fillcolor: 'rgba(59, 130, 246, 0.12)',
          },
          {
            x: series.t_min,
            y: derivScaled,
            type: 'scatter',
            mode: 'lines',
            name: 'd/dt (slope, scaled)',
            line: { color: '#60a5fa', width: 1, dash: 'dot' },
            opacity: 0.6,
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
          yaxis: { showgrid: true, gridcolor: '#1f2937', title: 'SoLEXS (W/m²)', type: 'log' },
          legend: { orientation: 'h', y: -0.28, font: { size: 9 } },
        }}
        useResizeHandler={true}
        style={{ width: '100%', height: '100%' }}
        config={{ responsive: true, displayModeBar: false }}
      />
    </div>
  );
}
