import { useEffect, useRef } from 'react'
import {
  CandlestickSeries,
  ColorType,
  createChart,
  type CandlestickData,
  type UTCTimestamp,
} from 'lightweight-charts'

import type { ReplayCandle } from '../types/replay'

interface ChartRendererProps {
  candles: ReplayCandle[]
}

function toSeriesData(candle: ReplayCandle): CandlestickData<UTCTimestamp> {
  return {
    time: Math.floor(new Date(candle.open_time).getTime() / 1000) as UTCTimestamp,
    open: Number(candle.open),
    high: Number(candle.high),
    low: Number(candle.low),
    close: Number(candle.close),
  }
}

export function ChartRenderer({ candles }: ChartRendererProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const chart = createChart(container, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: '#0f172a' },
        textColor: '#cbd5e1',
      },
      grid: {
        vertLines: { color: '#1e293b' },
        horzLines: { color: '#1e293b' },
      },
      rightPriceScale: { borderColor: '#334155' },
      timeScale: { borderColor: '#334155', timeVisible: true, secondsVisible: false },
    })

    const series = chart.addSeries(CandlestickSeries, {
      upColor: '#22c55e',
      downColor: '#ef4444',
      borderVisible: false,
      wickUpColor: '#22c55e',
      wickDownColor: '#ef4444',
    })

    series.setData(candles.map(toSeriesData))
    chart.timeScale().fitContent()

    return () => chart.remove()
  }, [candles])

  return <div className="chart" ref={containerRef} aria-label="Replay candlestick chart" />
}
