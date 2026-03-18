/**
 * PriceChart — Lightweight Charts 다중 차트 타입 + 볼륨 + 이벤트 마커
 * 차트 타입 전환(캔들/속빈/하이킨/OHLC/라인), 기간 선택(1W~1Y), 드래그 패닝, 휠 줌
 * 체결 로그 기반 매수/매도/실패 마커 표시
 */
import { useState, useRef, useEffect, useCallback } from 'react'
import { createChart, ColorType, CandlestickSeries, BarSeries, LineSeries, HistogramSeries, createSeriesMarkers } from 'lightweight-charts'
import type { IChartApi } from 'lightweight-charts'
import { useQuery } from '@tanstack/react-query'
import { cloudBars } from '../../services/cloudClient'
import type { DailyBar } from '../../services/cloudClient'
import { localLogs, localBars } from '../../services/localClient'
import type { MinuteBar } from '../../services/localClient'

// ─── 차트 타입 ───

type ChartType = 'candle' | 'hollow' | 'heikin' | 'ohlc' | 'line'

const CHART_TYPES: { id: ChartType; label: string }[] = [
  { id: 'candle', label: '캔들' },
  { id: 'hollow', label: '속빈' },
  { id: 'heikin', label: '하이킨' },
  { id: 'ohlc',   label: 'OHLC' },
  { id: 'line',   label: '라인' },
]

// 해상도 옵션 — source: 'local' = 로컬 분봉 DB, 'cloud' = 클라우드 일봉+
type Resolution = '1m' | '5m' | '15m' | '1h' | '1d' | '1w' | '1mo'
interface ResolutionOption {
  id: Resolution
  label: string
  source: 'local' | 'cloud'
}
const RESOLUTION_OPTIONS: ResolutionOption[] = [
  { id: '1m',  label: '1분',  source: 'local' },
  { id: '5m',  label: '5분',  source: 'local' },
  { id: '15m', label: '15분', source: 'local' },
  { id: '1h',  label: '1시간', source: 'local' },
  { id: '1d',  label: '일',   source: 'cloud' },
  { id: '1w',  label: '주',   source: 'cloud' },
  { id: '1mo', label: '월',   source: 'cloud' },
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

// ─── 이벤트 마커 변환 ───

interface FillLog {
  ts: string
  meta: { side: string; status: string; qty?: number }
}

function buildMarkers(logs: FillLog[], startDate: string) {
  // 체결 건만 표시 (실패는 로그 화면에서 확인)
  const filled = logs.filter(l => l.ts && l.meta && l.meta.status === 'FILLED' && l.ts.slice(0, 10) >= startDate)

  // 같은 날짜+방향 중복 합치기
  const grouped = new Map<string, { count: number; buy: boolean }>()
  for (const l of filled) {
    const day = l.ts.slice(0, 10)
    const buy = l.meta.side === 'BUY'
    const key = `${day}-${buy ? 'B' : 'S'}`
    const prev = grouped.get(key)
    if (prev) {
      prev.count++
    } else {
      grouped.set(key, { count: 1, buy })
    }
  }

  return Array.from(grouped.entries())
    .map(([key, { count, buy }]) => ({
      time: key.slice(0, 10),
      position: buy ? 'belowBar' as const : 'aboveBar' as const,
      shape: buy ? 'arrowUp' as const : 'arrowDown' as const,
      color: buy ? '#3b82f6' : '#ef4444',
      size: 0.5 as const,
      text: count > 1 ? `${buy ? '매수' : '매도'}×${count}` : (buy ? '매수' : '매도'),
    }))
    .sort((a, b) => a.time < b.time ? -1 : a.time > b.time ? 1 : 0)
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
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const markersRef = useRef<any>(null)
  const prevTypeRef = useRef<ChartType | null>(null)
  const [period, setPeriod] = useState<(typeof PERIOD_OPTIONS)[number]['label']>('3M')
  const [chartType, setChartType] = useState<ChartType>('candle')
  const [resolution, setResolution] = useState<Resolution>('1d')
  const [isZoomed, setIsZoomed] = useState(false)
  const dataLenRef = useRef(0)
  // lazy load: 로드된 범위 추적 + 추가 로드된 과거 데이터
  const loadedRangeRef = useRef<{ start: string } | null>(null)
  const lazyDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const isFetchingMoreRef = useRef(false)
  const [extraBars, setExtraBars] = useState<DailyBar[]>([])

  const resOption = RESOLUTION_OPTIONS.find(r => r.id === resolution)!
  const isIntraday = resOption.source === 'local'

  // 해상도/종목/기간 변경 시 lazy load 상태 리셋
  useEffect(() => {
    loadedRangeRef.current = null
    setExtraBars([])
  }, [resolution, symbol, period])

  // lazy load: 좌측 스크롤 → 과거 데이터 추가 요청
  const fetchMoreBars = useCallback(async (newStart: string, currentStart: string) => {
    if (!symbol || isFetchingMoreRef.current) return
    isFetchingMoreRef.current = true
    try {
      let older: DailyBar[]
      if (isIntraday) {
        const raw = await localBars.get(symbol, resolution, newStart, currentStart)
        older = raw.map(b => ({ date: b.time, open: b.open, high: b.high, low: b.low, close: b.close, volume: b.volume }))
      } else {
        older = await cloudBars.get(symbol, newStart, currentStart, resolution)
      }
      if (older.length === 0) return
      setExtraBars(prev => {
        const existing = new Set(prev.map(b => b.date))
        const unique = older.filter(b => !existing.has(b.date))
        return [...unique, ...prev]
      })
      if (loadedRangeRef.current) {
        loadedRangeRef.current.start = newStart
      }
    } finally {
      isFetchingMoreRef.current = false
    }
  }, [symbol, resolution, isIntraday])

  // ref로 최신 fetchMoreBars 접근 (chart effect는 [] deps)
  const fetchMoreRef = useRef(fetchMoreBars)
  fetchMoreRef.current = fetchMoreBars

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
    markersRef.current = null

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

    // lazy load: 좌측 끝 도달 감지 → 과거 데이터 요청
    chart.timeScale().subscribeVisibleTimeRangeChange((range) => {
      if (!range) return
      const from = String(range.from) // date string 또는 timestamp
      const loaded = loadedRangeRef.current
      if (!loaded) return
      // 보이는 범위의 시작이 로드된 범위의 시작 근처이면 더 요청
      if (from <= loaded.start) {
        if (lazyDebounceRef.current) clearTimeout(lazyDebounceRef.current)
        lazyDebounceRef.current = setTimeout(() => {
          // 30일분 추가 로드
          const d = new Date(loaded.start)
          d.setDate(d.getDate() - 30)
          const newStart = d.toISOString().slice(0, 10)
          fetchMoreRef.current(newStart, loaded.start)
        }, 250)
      }
    })

    const ro = new ResizeObserver(() => {
      if (containerRef.current) chart.applyOptions({ width: containerRef.current.clientWidth })
    })
    ro.observe(containerRef.current)

    return () => { ro.disconnect(); chart.remove() }
  }, [])

  // 분봉 해상도일 때 시간축에 시/분 표시
  useEffect(() => {
    chartRef.current?.timeScale().applyOptions({ timeVisible: isIntraday })
  }, [isIntraday])

  // 기간에 따른 시작일 계산
  const days = PERIOD_OPTIONS.find(p => p.label === period)!.days
  const startDate = new Date()
  startDate.setDate(startDate.getDate() - days)
  const startStr = startDate.toISOString().slice(0, 10)

  // 클라우드 일봉/주봉/월봉
  const { data: cloudData } = useQuery<DailyBar[]>({
    queryKey: ['bars', symbol, startStr, resolution],
    queryFn: () => symbol ? cloudBars.get(symbol, startStr, undefined, resolution) : Promise.resolve([]),
    staleTime: 5 * 60_000,
    enabled: !!symbol && !isIntraday,
    retry: 1,
  })

  // 로컬 분봉 (1m/5m/15m/1h)
  const { data: localData } = useQuery<MinuteBar[]>({
    queryKey: ['localBars', symbol, resolution, startStr],
    queryFn: () => symbol ? localBars.get(symbol, resolution, startStr) : Promise.resolve([]),
    staleTime: 30_000,
    enabled: !!symbol && isIntraday,
    retry: 1,
  })

  // 통합 데이터: DailyBar 형식으로 정규화 + lazy load 데이터 병합
  const baseBars: DailyBar[] | undefined = isIntraday
    ? localData?.map(b => ({ date: b.time, open: b.open, high: b.high, low: b.low, close: b.close, volume: b.volume }))
    : cloudData
  const bars: DailyBar[] | undefined = baseBars && extraBars.length > 0
    ? (() => {
        const baseSet = new Set(baseBars.map(b => b.date))
        const unique = extraBars.filter(b => !baseSet.has(b.date))
        return [...unique, ...baseBars]
      })()
    : baseBars

  // 체결 로그 fetch (마커용)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const { data: fillLogData } = useQuery<any>({
    queryKey: ['fillLogs', symbol],
    queryFn: () => symbol
      ? localLogs.get({ log_type: 'FILL', symbol, limit: 200 } as never)
      : Promise.resolve([]),
    enabled: !!symbol,
    refetchInterval: 30_000,
  })
  // 데이터 또는 차트 타입 변경 시 업데이트
  useEffect(() => {
    if (!chartRef.current || !volumeSeriesRef.current) return

    const chart = chartRef.current
    const candles = bars ?? []
    dataLenRef.current = candles.length

    // 로드된 범위 추적 (lazy load 기준)
    if (candles.length > 0 && !loadedRangeRef.current) {
      loadedRangeRef.current = { start: candles[0].date }
    }

    const isLazyAppend = extraBars.length > 0

    // fillLogData 파싱 (useEffect 내부에서 — 의존성 안정성)
    const fillLogs: FillLog[] = Array.isArray(fillLogData)
      ? fillLogData
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      : ((fillLogData as any)?.items ?? [])

    // 타입 변경 시 시리즈 교체
    const typeChanged = prevTypeRef.current !== chartType
    if (typeChanged) {
      if (mainSeriesRef.current) chart.removeSeries(mainSeriesRef.current)
      mainSeriesRef.current = createMainSeries(chart, chartType)
      prevTypeRef.current = chartType
      markersRef.current = null
    }

    if (!mainSeriesRef.current) {
      mainSeriesRef.current = createMainSeries(chart, chartType)
      prevTypeRef.current = chartType
      markersRef.current = null
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

    // 이벤트 마커 설정
    const markers = buildMarkers(fillLogs, startStr)
    if (markers.length > 0) {
      if (!markersRef.current) {
        markersRef.current = createSeriesMarkers(mainSeriesRef.current, markers)
      } else {
        markersRef.current.setMarkers(markers)
      }
    } else if (markersRef.current) {
      markersRef.current.setMarkers([])
    }

    // lazy load 추가분이면 스크롤 위치 유지, 아니면 fitContent
    if (!typeChanged && !isLazyAppend) {
      chart.timeScale().fitContent()
      setIsZoomed(false)
    }
  }, [bars, chartType, fillLogData, startStr, extraBars])

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
          <div className="flex items-center gap-1" role="group" aria-label="해상도">
            {RESOLUTION_OPTIONS.map(r => (
              <button key={r.id} onClick={() => setResolution(r.id)} aria-pressed={resolution === r.id} className={btnClass(resolution === r.id)}>
                {r.label}
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
