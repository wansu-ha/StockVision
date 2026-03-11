/**
 * PriceChart — Lightweight Charts 다중 차트 타입 + 볼륨
 * 차트 타입 전환(캔들/속빈/하이킨/OHLC/라인), 기간 선택(1W~1Y), 드래그 패닝, 휠 줌
 */
import { useState, useRef, useEffect } from 'react'
import { createChart, ColorType, CandlestickSeries, BarSeries, LineSeries, HistogramSeries } from 'lightweight-charts'
import type { IChartApi } from 'lightweight-charts'
import { useQuery } from '@tanstack/react-query'
import { cloudBars } from '../../services/cloudClient'
import type { DailyBar } from '../../services/cloudClient'

// ─── 차트 타입 ───

type ChartType = 'candle' | 'hollow' | 'heikin' | 'ohlc' | 'line'

const CHART_TYPES: { id: ChartType; label: string }[] = [
  { id: 'candle', label: '캔들' },
  { id: 'hollow', label: '속빈' },
  { id: 'heikin', label: '하이킨' },
  { id: 'ohlc',   label: 'OHLC' },
  { id: 'line',   label: '라인' },
]

const PERIOD_OPTIONS = [
  { label: '1W', days: 7 },
  { label: '1M', days: 30 },
  { label: '3M', days: 90 },
  { label: '6M', days: 180 },
  { label: '1Y', days: 365 },
] as const

// ─── 하이킨 아시 변환 ───

function toHeikinAshi(bars: DailyBar[]) {
  if (bars.length === 0) return []
  const result: { time: string; open: number; high: number; low: number; close: number }[] = []
  let prevOpen = (bars[0].open + bars[0].close) / 2
  let prevClose = (bars[0].open + bars[0].high + bars[0].low + bars[0].close) / 4
  for (const b of bars) {
    const haClose = (b.open + b.high + b.low + b.close) / 4
    const haOpen = (prevOpen + prevClose) / 2
    result.push({
      time: b.date,
      open: haOpen,
      high: Math.max(b.high, haOpen, haClose),
      low: Math.min(b.low, haOpen, haClose),
      close: haClose,
    })
    prevOpen = haOpen
    prevClose = haClose
  }
  return result
}

// ─── 시리즈 생성 ───

type SeriesRef = ReturnType<IChartApi['addSeries']>

function createMainSeries(chart: IChartApi, type: ChartType): SeriesRef {
  switch (type) {
    case 'candle':
      return chart.addSeries(CandlestickSeries, {
        upColor: '#ef4444', downColor: '#3b82f6',
        borderUpColor: '#ef4444', borderDownColor: '#3b82f6',
        wickUpColor: '#ef4444', wickDownColor: '#3b82f6',
      })
    case 'hollow':
      return chart.addSeries(CandlestickSeries, {
        upColor: 'transparent', downColor: '#3b82f6',
        borderVisible: true,
        borderUpColor: '#ef4444', borderDownColor: '#3b82f6',
        wickUpColor: '#ef4444', wickDownColor: '#3b82f6',
      })
    case 'heikin':
      return chart.addSeries(CandlestickSeries, {
        upColor: '#ef4444', downColor: '#3b82f6',
        borderUpColor: '#ef4444', borderDownColor: '#3b82f6',
        wickUpColor: '#ef4444', wickDownColor: '#3b82f6',
      })
    case 'ohlc':
      return chart.addSeries(BarSeries, {
        upColor: '#ef4444', downColor: '#3b82f6',
      })
    case 'line':
      return chart.addSeries(LineSeries, {
        color: '#a78bfa', lineWidth: 2,
      })
  }
}

// ─── 데이터 변환 ───

function transformData(bars: DailyBar[], type: ChartType) {
  if (type === 'line') {
    return bars.map(c => ({ time: c.date, value: c.close }))
  }
  if (type === 'heikin') {
    return toHeikinAshi(bars)
  }
  return bars.map(c => ({ time: c.date, open: c.open, high: c.high, low: c.low, close: c.close }))
}

// ─── Component ───

interface PriceChartProps {
  symbol?: string
}

export default function PriceChart({ symbol }: PriceChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const mainSeriesRef = useRef<SeriesRef | null>(null)
  const volumeSeriesRef = useRef<SeriesRef | null>(null)
  const prevTypeRef = useRef<ChartType | null>(null)
  const [period, setPeriod] = useState<(typeof PERIOD_OPTIONS)[number]['label']>('3M')
  const [chartType, setChartType] = useState<ChartType>('candle')
  const [isZoomed, setIsZoomed] = useState(false)
  const dataLenRef = useRef(0)

  // 차트 생성 (한 번만) — 볼륨만 생성, 메인 시리즈는 데이터 useEffect에서
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
    // StrictMode 더블마운트 대응: 이전 차트의 시리즈 ref 초기화
    mainSeriesRef.current = null
    prevTypeRef.current = null

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

  // 데이터 또는 차트 타입 변경 시 업데이트
  useEffect(() => {
    if (!chartRef.current || !volumeSeriesRef.current) return

    const chart = chartRef.current
    const candles = bars ?? []
    dataLenRef.current = candles.length

    // 타입 변경 시 시리즈 교체
    const typeChanged = prevTypeRef.current !== chartType
    if (typeChanged) {
      if (mainSeriesRef.current) chart.removeSeries(mainSeriesRef.current)
      mainSeriesRef.current = createMainSeries(chart, chartType)
      prevTypeRef.current = chartType
    }

    if (!mainSeriesRef.current) {
      mainSeriesRef.current = createMainSeries(chart, chartType)
      prevTypeRef.current = chartType
    }

    if (candles.length === 0) {
      mainSeriesRef.current.setData([])
      volumeSeriesRef.current.setData([])
      return
    }

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    mainSeriesRef.current.setData(transformData(candles, chartType) as any)
    volumeSeriesRef.current.setData(candles.map(c => ({
      time: c.date, value: c.volume,
      color: c.close >= c.open ? 'rgba(239,68,68,0.3)' : 'rgba(59,130,246,0.3)',
    })))

    // 타입 변경만이면 줌 위치 유지, 데이터 변경이면 fitContent
    if (!typeChanged) {
      chart.timeScale().fitContent()
      setIsZoomed(false)
    }
  }, [bars, chartType])

  const handleReset = () => {
    chartRef.current?.timeScale().fitContent()
    setIsZoomed(false)
  }

  const btnClass = (active: boolean) =>
    `px-2.5 py-1 text-xs rounded-md transition ${active ? 'bg-indigo-600 text-white' : 'text-gray-500 hover:text-gray-300 hover:bg-gray-800'}`

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
      {/* 차트 타입 + 기간 선택 + 리셋 */}
      <div className="flex items-center justify-between px-4 pt-3 pb-1">
        <div className="flex items-center">
          <div className="flex items-center gap-1" role="group" aria-label="차트 타입">
            {CHART_TYPES.map(t => (
              <button key={t.id} onClick={() => setChartType(t.id)} aria-pressed={chartType === t.id} className={btnClass(chartType === t.id)}>
                {t.label}
              </button>
            ))}
          </div>
          <div className="w-px h-4 bg-gray-700 mx-2" />
          <div className="flex items-center gap-1" role="group" aria-label="차트 기간 선택">
            {PERIOD_OPTIONS.map(p => (
              <button key={p.label} onClick={() => setPeriod(p.label)} aria-pressed={period === p.label} className={btnClass(period === p.label)}>
                {p.label}
              </button>
            ))}
          </div>
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
