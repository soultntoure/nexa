import type { ChartData, ChartOptions } from 'chart.js'

export interface ChartSpec {
  title: string
  chart_type: 'bar' | 'line' | 'pie'
  x_key: string
  series: { key: string; label: string }[]
  rows: Record<string, unknown>[]
  meta: { reason: string; confidence: number; source: string }
}

export interface ChartJsConfig {
  type: 'bar' | 'line' | 'pie'
  data: ChartData
  options: ChartOptions
}

const PALETTE = [
  '#e53935', '#1e88e5', '#43a047', '#fb8c00',
  '#8e24aa', '#00acc1', '#6d4c41', '#546e7a',
]

export function toChartJsConfig(spec: ChartSpec): ChartJsConfig {
  const labels = spec.rows.map(r => String(r[spec.x_key]))

  const datasets = spec.series.map((s, i) => ({
    label: s.label,
    data: spec.rows.map(r => Number(r[s.key]) || 0),
    backgroundColor: spec.chart_type === 'pie'
      ? spec.rows.map((_, ri) => PALETTE[ri % PALETTE.length])
      : PALETTE[i % PALETTE.length],
    borderColor: spec.chart_type === 'line' ? PALETTE[i % PALETTE.length] : undefined,
    borderWidth: spec.chart_type === 'line' ? 2 : 0,
    fill: false,
    tension: 0.3,
  }))

  const options: ChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      title: { display: true, text: spec.title, font: { size: 13 } },
      legend: { display: spec.series.length > 1 || spec.chart_type === 'pie' },
      tooltip: { enabled: true },
    },
    scales: spec.chart_type === 'pie' ? {} : {
      x: { ticks: { maxRotation: 45 } },
      y: { beginAtZero: true },
    },
  }

  return { type: spec.chart_type, data: { labels, datasets }, options }
}
