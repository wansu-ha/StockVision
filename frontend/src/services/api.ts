import axios from 'axios'
import type { ApiResponse, Stock, StockPrice, TechnicalIndicator, StockSummary } from '../types'

const API_BASE_URL = 'http://localhost:8000/api/v1'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
})

// 응답 인터셉터
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.code === 'ECONNABORTED') {
      console.error('API 타임아웃:', error.message)
      console.error('요청 URL:', error.config?.url)
      console.error('요청 메서드:', error.config?.method)
    } else if (error.response) {
      console.error('API 응답 오류:', error.response.status, error.response.data)
    } else if (error.request) {
      console.error('API 요청 실패:', error.message)
    } else {
      console.error('API 오류:', error.message)
    }
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

// AI 분석 API
export const aiAnalysisApi = {
  // 전반적인 시장 분석
  getMarketOverview: async () => {
    const response = await api.get('/ai-analysis/market-overview')
    return response.data
  },

  // 개별 주식 AI 분석
  getStockAnalysis: async (symbol: string) => {
    const response = await api.get(`/ai-analysis/stocks/${symbol}/analysis`)
    return response.data
  },

  // 섹터별 AI 분석
  getSectorAnalysis: async (sector: string) => {
    const response = await api.get(`/ai-analysis/sectors/${sector}/analysis`)
    return response.data
  },

  // 최신 AI 인사이트
  getLatestInsights: async () => {
    const response = await api.get('/ai-analysis/ai-insights/latest')
    return response.data
  },
}

// 백엔드 서버 상태 확인
export const healthApi = {
  checkHealth: async () => {
    const response = await axios.get('http://localhost:8000/health')
    return response.data
  },
  
  getApiInfo: async () => {
    const response = await axios.get('http://localhost:8000/api-info')
    return response.data
  }
}

export default api
