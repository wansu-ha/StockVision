export interface Stock {
  id: number
  symbol: string
  name: string
  sector: string
  industry: string
  market_cap: number | null
  created_at: string
  updated_at: string
}

export interface StockPrice {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

export interface TechnicalIndicator {
  date: string
  value: number
  indicator_type: string
  parameters: string
}

export interface StockSummary {
  symbol: string
  name: string
  sector: string
  industry: string
  latest_price: {
    date: string
    close: number
    volume: number
  } | null
  current_indicators: Record<string, number>
}

export interface ApiResponse<T> {
  success: boolean
  data: T
  count?: number
}
