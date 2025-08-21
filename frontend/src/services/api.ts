import axios from 'axios'
import type { ApiResponse, Stock, StockPrice, TechnicalIndicator, StockSummary } from '../types'

const API_BASE_URL = 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
})

// 응답 인터셉터
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export const stockApi = {
  // 모든 주식 목록 조회
  getStocks: async (): Promise<ApiResponse<Stock[]>> => {
    const response = await api.get('/stocks/')
    return response.data
  },

  // 특정 주식 상세 정보
  getStock: async (symbol: string): Promise<ApiResponse<Stock>> => {
    const response = await api.get(`/stocks/${symbol}`)
    return response.data
  },

  // 주식 가격 데이터
  getStockPrices: async (symbol: string, days: number = 30): Promise<ApiResponse<{ symbol: string; name: string; prices: StockPrice[] }>> => {
    const response = await api.get(`/stocks/${symbol}/prices?days=${days}`)
    return response.data
  },

  // 기술적 지표
  getStockIndicators: async (symbol: string, days: number = 30, indicatorType?: string): Promise<ApiResponse<{ symbol: string; name: string; indicators: Record<string, TechnicalIndicator[]> }>> => {
    const url = indicatorType 
      ? `/stocks/${symbol}/indicators?days=${days}&indicator_type=${indicatorType}`
      : `/stocks/${symbol}/indicators?days=${days}`
    const response = await api.get(url)
    return response.data
  },

  // 주식 요약 정보
  getStockSummary: async (symbol: string): Promise<ApiResponse<StockSummary>> => {
    const response = await api.get(`/stocks/${symbol}/summary`)
    return response.data
  },
}

export default api
