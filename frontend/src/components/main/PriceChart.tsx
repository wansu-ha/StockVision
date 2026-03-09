/**
 * PriceChart — Lightweight Charts 캔들스틱 + 볼륨
 * 기간 선택(1W~1Y), 드래그 패닝, 휠 줌
 */
import { useState, useRef, useEffect } from 'react'
import { createChart, ColorType, CandlestickSeries, HistogramSeries } from 'lightweight-charts'
import type { IChartApi } from 'lightweight-charts'
import { useQuery } from '@tanstack/react-query'
import { cloudBars } from '../../services/cloudClient'
import type { DailyBar } from '../../services/cloudClient'

const PERIOD_OPTIONS = [
  { label: '1W', days: 7 },
  { label: '1M', days: 30 },
  { label: '3M', days: 90 },
  { label: '6M', days: 180 },
  { label: '1Y', days: 365 },
] as const

// ─── Component ───

interface PriceChartProps {
  symbol?: string
}

export default function PriceChart({ symbol }: PriceChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const candleSeriesRef = useRef<ReturnType<IChartApi['addSeries']> | null>(null)
  const volumeSeriesRef = useRef<ReturnType<IChartApi['addSeries']> | null>(null)
  const [period, setPeriod] = useState<(typeof PERIOD_OPTIONS)[number]['label']>('3M')
  const [isZoomed, setIsZoomed] = useState(false)
  const dataLenRef = useRef(0)

  // 차트 생성 (한 번만)
  useEffect(() => {
    if (!containerRef.current) return

    const chart = createChart(containerRef.current, {
      layout: { background: { type: ColorType.Solid, color: '#111827' }, textColor: '#9ca3af' },
      grid: { vertLines: { color: '#1f2937' }, horzLines: { color: '#1f2937' } },
      crosshair: { mode: 0 },
      rightPriceScale: { borderColor: '#374151' },
      timeScale: { borderColor: '#374151', timeVisible: false },
      handleScroll: { mouseWheel: true, pressedMouseMove: true },
      handleScale: { mouseWheel: true, pinch: true },
      height: 300,
    })
    chartRef.current = chart

    candleSeriesRef.current = chart.addSeries(CandlestickSeries, {
      upColor: '#ef4444', downColor: '#3b82f6',
      borderUpColor: '#ef4444', borderDownColor: '#3b82f6',
      wickUpColor: '#ef4444', wickDownColor: '#3b82f6',
    })

    volumeSeriesRef.current = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
    })
    chart.priceScale('volume').applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } })

    // 줌/스크롤 감지 → "전체 보기" 버튼 표시
    chart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
      if (!range || dataLenRef.current === 0) return
      setIsZoomed(range.to - range.from < dataLenRef.current - 1)
    })

    const ro = new ResizeObserver(() => {
      if (containerRef.current) chart.applyOptions({ width: containerRef.current.clientWidth })
    })
    ro.observe(containerRef.current)

    return () => { ro.disconnect(); chart.remove() }
  }, [])

  // 기간에 따른 시작일 계산
  const days = PERIOD_OPTIONS.find(p => p.label === period)!.days
  const startDate = new Date()
  startDate.setDate(startDate.getDate() - days)
  const startStr = startDate.toISOString().slice(0, 10)

  const { data: bars } = useQuery<DailyBar[]>({
    queryKey: ['bars', symbol, startStr],
    queryFn: () => symbol ? cloudBars.get(symbol, startStr) : Promise.resolve([]),
    enabled: !!symbol,
    retry: 1,
  })

  // 데이터 변경 시 차트 업데이트
  useEffect(() => {
    if (!candleSeriesRef.current || !volumeSeriesRef.current || !chartRef.current) return

    const candles = bars ?? []
    dataLenRef.current = candles.length
    if (candles.length === 0) {
      candleSeriesRef.current.setData([])
      volumeSeriesRef.current.setData([])
      return
    }

    candleSeriesRef.current.setData(candles.map(c => ({ time: c.date, open: c.open, high: c.high, low: c.low, close: c.close })))
    volumeSeriesRef.current.setData(candles.map(c => ({
      time: c.date, value: c.volume,
      color: c.close >= c.open ? 'rgba(239,68,68,0.3)' : 'rgba(59,130,246,0.3)',
    })))

    chartRef.current.timeScale().fitContent()
    setIsZoomed(false)
  }, [bars])

  const handleReset = () => {
    chartRef.current?.timeScale().fitContent()
    setIsZoomed(false)
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
      {/* 기간 선택 + 리셋 */}
      <div className="flex items-center justify-between px-4 pt-3 pb-1">
        <div className="flex items-center gap-1" role="group" aria-label="차트 기간 선택">
          {PERIOD_OPTIONS.map(p => (
            <button
              key={p.label}
              onClick={() => setPeriod(p.label)}
              aria-pressed={period === p.label}
              className={`px-2.5 py-1 text-xs rounded-md transition ${
                period === p.label
                  ? 'bg-indigo-600 text-white'
                  : 'text-gray-500 hover:text-gray-300 hover:bg-gray-800'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          {isZoomed && (
            <button onClick={handleReset} className="text-xs text-indigo-400 hover:text-indigo-300 transition">
              전체 보기
            </button>
          )}
          <span className="text-[10px] text-gray-600">드래그로 이동 · 휠로 줌</span>
        </div>
      </div>
      <div className="px-4 pb-4">
        <div ref={containerRef} />
      </div>
    </div>
  )
}
