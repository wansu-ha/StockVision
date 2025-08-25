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

// AI 분석 관련 타입들
export interface MarketOverview {
  overall_sentiment: string
  sentiment_score: number
  market_trend: string
  key_factors: string[]
  risk_level: string
  investment_advice: string
  sector_outlook: Record<string, string>
  market_volatility: string
  liquidity_condition: string
  analysis_timestamp: string
}

export interface TechnicalAnalysis {
  trend_strength: string
  support_level: number
  resistance_level: number
  rsi_signal: string
  macd_signal: string
  volume_trend: string
  price_momentum: string
  volatility_level: string
}

export interface NewsAnalysis {
  recent_news: Array<{
    topic: string
    sentiment: string
    impact_level: string
    summary: string
  }>
  market_reaction: string
  sector_influence: string
  news_sentiment_score: number
}

export interface SentimentAnalysis {
  retail_sentiment: string
  institutional_sentiment: string
  analyst_rating: string
  price_target_consensus: number
  earnings_expectations: string
  short_interest: number
  options_flow: string
}

export interface InvestmentOpinion {
  recommendation: string
  confidence_level: string
  reasoning: string
  risk_reward_ratio: number
  time_horizon: string
}

export interface RiskAssessment {
  overall_risk: string
  volatility_risk: string
  liquidity_risk: string
  sector_risk?: string
  company_specific_risk?: string
  risk_factors: string[]
}

export interface PriceTarget {
  short_term_target: number
  medium_term_target: number
  long_term_target: number
  upside_potential: number
  downside_risk: number
}

export interface HoldingPeriod {
  recommended_period: string
  reasoning: string
  rebalancing_frequency: string
  exit_strategy: string
}

export interface StockAnalysis {
  stock_symbol: string
  stock_name: string
  analysis_timestamp: string
  technical_analysis: TechnicalAnalysis
  news_analysis: NewsAnalysis
  sentiment_analysis: SentimentAnalysis
  investment_opinion: InvestmentOpinion
  risk_assessment: RiskAssessment
  price_targets: {
    short_term: number
    medium_term: number
    long_term: number
  }
  holding_period: {
    recommended_period: string
    rebalancing_frequency: string
  }
}

export interface SectorAnalysis {
  sector_name: string
  overall_outlook: string
  growth_potential: string
  key_drivers: string[]
  risk_factors: string[]
  top_performers: string[]
  analysis_timestamp: string
}

export interface AIInsight {
  id: number
  title: string
  summary: string
  impact_level: string
  timestamp: string
  tags: string[]
}
