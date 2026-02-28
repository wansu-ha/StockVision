// 가상 거래 관련 타입 정의

export interface VirtualAccount {
  id: number
  name: string
  initial_balance: number
  current_balance: number
  total_profit_loss: number
  total_trades: number
  win_trades: number
  created_at: string
}

export interface AccountSummary {
  account_id: number
  name: string
  initial_balance: number
  current_balance: number
  total_position_value: number
  total_assets: number
  total_return_rate: number
  total_profit_loss: number
  total_trades: number
  win_trades: number
  win_rate: number
  positions: number
}

export interface VirtualPosition {
  id: number
  stock_id: number
  symbol: string
  quantity: number
  avg_price: number
  current_price: number | null
  unrealized_pnl: number
}

export interface VirtualTrade {
  id: number
  symbol: string
  trade_type: 'BUY' | 'SELL'
  quantity: number
  price: number
  total_amount: number
  commission: number
  tax: number
  realized_pnl: number | null
  timestamp: string
}

export interface StockScore {
  id: number
  stock_id: number
  symbol: string
  rsi_score: number
  macd_score: number
  bollinger_score: number
  ema_score: number
  prediction_score: number
  total_score: number
  signal: 'BUY' | 'SELL' | 'HOLD'
  date: string
}

export interface BacktestResult {
  id: number
  strategy_name: string
  start_date: string
  end_date: string
  initial_balance: number
  final_balance: number
  total_return: number
  sharpe_ratio: number
  max_drawdown: number
  win_rate: number
  total_trades: number
  win_trades: number
  strategy_type: string
  trade_details: BacktestTrade[]
  parameters: Record<string, number>
  created_at: string
}

export interface BacktestTrade {
  date: string
  symbol: string
  type: string
  quantity: number
  price: number
  total_amount: number
  commission: number
  tax: number
  realized_pnl: number | null
}

export interface BacktestResultSummary {
  id: number
  strategy_name: string
  start_date: string
  end_date: string
  total_return: number
  win_rate: number
  sharpe_ratio: number
  max_drawdown: number
  total_trades: number
  created_at: string
}

export interface AutoTradingRule {
  id: number
  name: string
  strategy_type: string
  account_id: number | null
  is_active: boolean
  buy_score_threshold: number
  max_position_count: number
  budget_ratio: number
  schedule_buy: string | null
  schedule_sell: string | null
  last_executed_at: string | null
  parameters: Record<string, unknown>
  created_at: string
  updated_at: string
}

// 요청 타입
export interface CreateAccountRequest {
  name: string
  initial_balance?: number
}

export interface PlaceOrderRequest {
  account_id: number
  stock_id: number
  symbol: string
  trade_type: 'BUY' | 'SELL'
  quantity: number
  price: number
}

export interface RunBacktestRequest {
  strategy_name?: string
  start_date: string
  end_date: string
  initial_balance?: number
  buy_threshold?: number
  sell_threshold?: number
  max_positions?: number
  budget_ratio?: number
}

export interface CreateRuleRequest {
  name: string
  strategy_type?: string
  account_id?: number
  buy_score_threshold?: number
  max_position_count?: number
  budget_ratio?: number
  schedule_buy?: string
  schedule_sell?: string
  parameters?: Record<string, unknown>
}

export interface UpdateRuleRequest {
  name?: string
  is_active?: boolean
  buy_score_threshold?: number
  max_position_count?: number
  budget_ratio?: number
  schedule_buy?: string
  schedule_sell?: string
  parameters?: Record<string, unknown>
}
