/**
 * 레거시 백엔드(:8000) 서비스 — TODO stub
 *
 * Phase 3 전환으로 localhost:8000 의존을 제거.
 * 각 API는 빈 데이터를 반환하며, 클라우드/로컬 서버 마이그레이션 후 삭제 예정.
 */
import type { ApiResponse, Stock, StockPrice, TechnicalIndicator, StockSummary } from '../types'
import type {
  VirtualAccount, AccountSummary, VirtualPosition, VirtualTrade,
  StockScore, BacktestResult, BacktestResultSummary, AutoTradingRule,
  CreateAccountRequest, PlaceOrderRequest, RunBacktestRequest,
  CreateRuleRequest, UpdateRuleRequest,
} from '../types/trading'

const STUB_WARN = (name: string) => console.warn(`[stub] ${name}: 레거시 백엔드 제거됨`)

const emptyResponse = <T>(data: T): ApiResponse<T> => ({ success: true, data, count: 0 })

export const stockApi = {
  getStocks: async (): Promise<ApiResponse<Stock[]>> => { STUB_WARN('stockApi.getStocks'); return emptyResponse([]) },
  getStock: async (_symbol: string): Promise<ApiResponse<Stock>> => { STUB_WARN('stockApi.getStock'); return emptyResponse({} as Stock) },
  getStockPrices: async (_symbol: string, _days = 30): Promise<ApiResponse<{ symbol: string; name: string; prices: StockPrice[] }>> => { STUB_WARN('stockApi.getStockPrices'); return emptyResponse({ symbol: '', name: '', prices: [] }) },
  getStockIndicators: async (_symbol: string, _days = 30, _indicatorType?: string): Promise<ApiResponse<{ symbol: string; name: string; indicators: Record<string, TechnicalIndicator[]> }>> => { STUB_WARN('stockApi.getStockIndicators'); return emptyResponse({ symbol: '', name: '', indicators: {} }) },
  getStockSummary: async (_symbol: string): Promise<ApiResponse<StockSummary>> => { STUB_WARN('stockApi.getStockSummary'); return emptyResponse({} as StockSummary) },
}

export const aiAnalysisApi = {
  getMarketOverview: async () => { STUB_WARN('aiAnalysisApi.getMarketOverview'); return { success: true, data: null } },
  getStockAnalysis: async (_symbol: string) => { STUB_WARN('aiAnalysisApi.getStockAnalysis'); return { success: true, data: null } },
  getSectorAnalysis: async (_sector: string) => { STUB_WARN('aiAnalysisApi.getSectorAnalysis'); return { success: true, data: null } },
  getLatestInsights: async () => { STUB_WARN('aiAnalysisApi.getLatestInsights'); return { success: true, data: null } },
}

export const tradingApi = {
  createAccount: async (_data: CreateAccountRequest): Promise<ApiResponse<VirtualAccount>> => { STUB_WARN('tradingApi.createAccount'); return emptyResponse({} as VirtualAccount) },
  getAccounts: async (): Promise<ApiResponse<VirtualAccount[]>> => { STUB_WARN('tradingApi.getAccounts'); return emptyResponse([]) },
  getAccountDetail: async (_accountId: number): Promise<ApiResponse<AccountSummary>> => { STUB_WARN('tradingApi.getAccountDetail'); return emptyResponse({} as AccountSummary) },
  placeOrder: async (_data: PlaceOrderRequest): Promise<ApiResponse<VirtualTrade>> => { STUB_WARN('tradingApi.placeOrder'); return emptyResponse({} as VirtualTrade) },
  getPositions: async (_accountId: number): Promise<ApiResponse<VirtualPosition[]>> => { STUB_WARN('tradingApi.getPositions'); return emptyResponse([]) },
  getTradeHistory: async (_accountId: number, _limit = 50): Promise<ApiResponse<VirtualTrade[]>> => { STUB_WARN('tradingApi.getTradeHistory'); return emptyResponse([]) },
  calculateScores: async (): Promise<ApiResponse<StockScore[]>> => { STUB_WARN('tradingApi.calculateScores'); return emptyResponse([]) },
  getScores: async (_limit = 20): Promise<ApiResponse<StockScore[]>> => { STUB_WARN('tradingApi.getScores'); return emptyResponse([]) },
  runBacktest: async (_data: RunBacktestRequest): Promise<ApiResponse<BacktestResult>> => { STUB_WARN('tradingApi.runBacktest'); return emptyResponse({} as BacktestResult) },
  getBacktestResult: async (_resultId: number): Promise<ApiResponse<BacktestResult>> => { STUB_WARN('tradingApi.getBacktestResult'); return emptyResponse({} as BacktestResult) },
  getBacktestResults: async (_limit = 20): Promise<ApiResponse<BacktestResultSummary[]>> => { STUB_WARN('tradingApi.getBacktestResults'); return emptyResponse([]) },
  createRule: async (_data: CreateRuleRequest): Promise<ApiResponse<AutoTradingRule>> => { STUB_WARN('tradingApi.createRule'); return emptyResponse({} as AutoTradingRule) },
  getRules: async (): Promise<ApiResponse<AutoTradingRule[]>> => { STUB_WARN('tradingApi.getRules'); return emptyResponse([]) },
  updateRule: async (_ruleId: number, _data: UpdateRuleRequest): Promise<ApiResponse<AutoTradingRule>> => { STUB_WARN('tradingApi.updateRule'); return emptyResponse({} as AutoTradingRule) },
  deleteRule: async (_ruleId: number): Promise<ApiResponse<{ id: number; deleted: boolean }>> => { STUB_WARN('tradingApi.deleteRule'); return emptyResponse({ id: 0, deleted: false }) },
}

export const healthApi = {
  checkHealth: async () => { STUB_WARN('healthApi.checkHealth'); return { status: 'stub' } },
  getApiInfo: async () => { STUB_WARN('healthApi.getApiInfo'); return {} },
}
