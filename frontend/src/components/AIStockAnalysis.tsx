import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, CardBody, CardHeader, Chip, Divider } from '@heroui/react'
import { 
  ChartBarIcon, 
  NewspaperIcon, 
  UserGroupIcon, 
  LightBulbIcon,
  ExclamationTriangleIcon,
  ClockIcon
} from '@heroicons/react/24/outline'
import { aiAnalysisApi } from '../services/api'
import type { StockAnalysis } from '../types'

interface AIStockAnalysisProps {
  symbol: string
}

const AIStockAnalysis: React.FC<AIStockAnalysisProps> = ({ symbol }) => {
  const { data: analysisData, isLoading, error } = useQuery({
    queryKey: ['stock-analysis', symbol],
    queryFn: () => aiAnalysisApi.getStockAnalysis(symbol),
    refetchInterval: 600000, // 10분마다 새로고침
  })

  if (isLoading) {
    return (
      <Card className="w-full shadow-lg">
        <CardBody className="p-6">
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
            <span className="ml-3 text-gray-600">AI가 {symbol}을 분석하고 있습니다...</span>
          </div>
        </CardBody>
      </Card>
    )
  }

  if (error || !analysisData?.data) {
    return (
      <Card className="w-full shadow-lg">
        <CardBody className="p-6">
          <div className="text-center py-8">
            <ExclamationTriangleIcon className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <div className="text-red-600 font-medium">AI 분석을 불러올 수 없습니다</div>
            <div className="text-sm text-gray-500 mt-2">잠시 후 다시 시도해주세요</div>
          </div>
        </CardBody>
      </Card>
    )
  }

  const analysis: StockAnalysis = analysisData.data

  const getSentimentColor = (sentiment: string | undefined) => {
    if (!sentiment) return 'default'
    if (sentiment.includes('긍정') || sentiment.includes('매수')) return 'success'
    if (sentiment.includes('중립') || sentiment.includes('보통')) return 'warning'
    if (sentiment.includes('부정') || sentiment.includes('매도')) return 'danger'
    return 'default'
  }



  const getRiskColor = (risk: string) => {
    switch (risk) {
      case '낮음':
        return 'success'
      case '보통':
        return 'warning'
      case '높음':
        return 'danger'
      default:
        return 'default'
    }
  }

  return (
    <Card className="w-full shadow-lg">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
              <LightBulbIcon className="w-6 h-6 text-white" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-gray-900">{analysis.stock_name} AI 분석</h3>
              <p className="text-sm text-gray-600">종합적인 투자 분석 및 전략 제안</p>
            </div>
          </div>
          <div className="flex items-center space-x-2 text-sm text-gray-500">
            <ClockIcon className="w-4 h-4" />
            <span>{new Date(analysis.analysis_timestamp).toLocaleString('ko-KR')}</span>
          </div>
        </div>
      </CardHeader>
      
      <CardBody className="pt-0">
        {/* 투자 의견 요약 */}
        <div className="mb-6 p-4 bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg border border-blue-200">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-lg font-semibold text-blue-900">투자 의견</h4>
            <Chip 
              color={getSentimentColor(analysis.investment_opinion.recommendation)}
              variant="flat"
              size="lg"
            >
              {analysis.investment_opinion.recommendation}
            </Chip>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-3">
            <div className="text-center">
              <div className="text-sm text-blue-700 mb-1">신뢰도</div>
              <div className="text-lg font-bold text-blue-900">{analysis.investment_opinion.confidence_level}</div>
            </div>
            <div className="text-center">
              <div className="text-sm text-blue-700 mb-1">리스크/수익률</div>
              <div className="text-lg font-bold text-blue-900">{analysis.investment_opinion.risk_reward_ratio}</div>
            </div>
            <div className="text-center">
              <div className="text-sm text-blue-700 mb-1">투자 기간</div>
              <div className="text-sm font-bold text-blue-900">{analysis.investment_opinion.time_horizon}</div>
            </div>
          </div>
          
          <div className="text-sm text-blue-800 bg-white p-3 rounded border">
            {analysis.investment_opinion.reasoning}
          </div>
        </div>

        {/* 기술적 분석 */}
        <div className="mb-6">
          <h4 className="text-lg font-semibold text-gray-800 mb-3 flex items-center">
            <ChartBarIcon className="w-5 h-5 mr-2" />
            기술적 분석
          </h4>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <div className="text-sm text-gray-600 mb-1">추세 강도</div>
              <Chip 
                color={getSentimentColor(analysis.technical_analysis?.trend_strength)}
                variant="flat"
                size="sm"
              >
                {analysis.technical_analysis?.trend_strength || 'N/A'}
              </Chip>
            </div>
            
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <div className="text-sm text-gray-600 mb-1">RSI 신호</div>
              <Chip 
                color={getSentimentColor(analysis.technical_analysis?.rsi_signal)}
                variant="flat"
                size="sm"
              >
                {analysis.technical_analysis?.rsi_signal || 'N/A'}
              </Chip>
            </div>
            
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <div className="text-sm text-gray-600 mb-1">MACD 신호</div>
              <Chip 
                color={getSentimentColor(analysis.technical_analysis?.macd_signal)}
                variant="flat"
                size="sm"
              >
                {analysis.technical_analysis?.macd_signal || 'N/A'}
              </Chip>
            </div>
            
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <div className="text-sm text-gray-600 mb-1">거래량</div>
              <Chip 
                color={getSentimentColor(analysis.technical_analysis?.volume_trend)}
                variant="flat"
                size="sm"
              >
                {analysis.technical_analysis?.volume_trend || 'N/A'}
              </Chip>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-3 bg-blue-50 rounded-lg">
              <div className="text-sm text-blue-700 mb-1">지지선</div>
              <div className="text-lg font-bold text-blue-900">${analysis.technical_analysis?.support_level || 'N/A'}</div>
            </div>
            <div className="p-3 bg-red-50 rounded-lg">
              <div className="text-sm text-red-700 mb-1">저항선</div>
              <div className="text-lg font-bold text-red-900">${analysis.technical_analysis?.resistance_level || 'N/A'}</div>
            </div>
          </div>
        </div>

        <Divider />

        {/* 뉴스 분석 */}
        <div className="mb-6">
          <h4 className="text-lg font-semibold text-gray-800 mb-3 flex items-center">
            <NewspaperIcon className="w-5 h-5 mr-2" />
            뉴스 및 시장 동향
          </h4>
          
          <div className="space-y-3">
            {analysis.news_analysis?.recent_news?.map((news, index) => (
              <div key={index} className="p-4 bg-gray-50 rounded-lg border-l-4 border-blue-500">
                <div className="flex items-start justify-between mb-2">
                  <div className="text-sm font-medium text-gray-900">{news.topic}</div>
                  <div className="flex items-center space-x-2">
                    <Chip 
                      color={getSentimentColor(news.sentiment)}
                      variant="flat"
                      size="sm"
                    >
                      {news.sentiment}
                    </Chip>
                    <Chip 
                      color={news.impact_level === '높음' ? 'danger' : news.impact_level === '보통' ? 'warning' : 'success'}
                      variant="flat"
                      size="sm"
                    >
                      {news.impact_level}
                    </Chip>
                  </div>
                </div>
                <div className="text-sm text-gray-700">{news.summary}</div>
              </div>
            ))}
          </div>
          
          <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <div className="text-sm text-gray-600 mb-1">시장 반응</div>
              <Chip 
                color={getSentimentColor(analysis.news_analysis.market_reaction)}
                variant="flat"
                size="sm"
              >
                {analysis.news_analysis.market_reaction}
              </Chip>
            </div>
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <div className="text-sm text-gray-600 mb-1">섹터 영향</div>
              <div className="text-sm font-bold text-gray-900">{analysis.news_analysis.sector_influence}</div>
            </div>
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <div className="text-sm text-gray-600 mb-1">뉴스 심리 점수</div>
              <div className="text-lg font-bold text-gray-900">
                {Math.round(analysis.news_analysis.news_sentiment_score * 100)}%
              </div>
            </div>
          </div>
        </div>

        <Divider />

        {/* 투자자 심리 */}
        <div className="mb-6">
          <h4 className="text-lg font-semibold text-gray-800 mb-3 flex items-center">
            <UserGroupIcon className="w-5 h-5 mr-2" />
            투자자 심리 분석
          </h4>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div className="p-3 bg-gray-50 rounded-lg">
              <div className="text-sm text-gray-600 mb-1">개인 투자자</div>
              <Chip 
                color={getSentimentColor(analysis.sentiment_analysis?.retail_sentiment)}
                variant="flat"
                size="sm"
              >
                {analysis.sentiment_analysis?.retail_sentiment || 'N/A'}
              </Chip>
            </div>
            
            <div className="p-3 bg-gray-50 rounded-lg">
              <div className="text-sm text-gray-600 mb-1">기관 투자자</div>
              <Chip 
                color={getSentimentColor(analysis.sentiment_analysis?.institutional_sentiment)}
                variant="flat"
                size="sm"
              >
                {analysis.sentiment_analysis?.institutional_sentiment || 'N/A'}
              </Chip>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <div className="text-sm text-gray-600 mb-1">애널리스트 평가</div>
              <Chip 
                color={getSentimentColor(analysis.sentiment_analysis?.analyst_rating)}
                variant="flat"
                size="sm"
              >
                {analysis.sentiment_analysis?.analyst_rating || 'N/A'}
              </Chip>
            </div>
            
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <div className="text-sm text-gray-600 mb-1">목표가 합의</div>
              <div className="text-lg font-bold text-gray-900">${analysis.sentiment_analysis?.price_target_consensus || 'N/A'}</div>
            </div>
            
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <div className="text-sm text-gray-600 mb-1">실적 전망</div>
              <Chip 
                color={getSentimentColor(analysis.sentiment_analysis?.earnings_expectations)}
                variant="flat"
                size="sm"
              >
                {analysis.sentiment_analysis?.earnings_expectations || 'N/A'}
              </Chip>
            </div>
          </div>
        </div>

        <Divider />

        {/* 가격 목표 및 리스크 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h4 className="text-lg font-semibold text-gray-800 mb-3">가격 목표</h4>
            <div className="space-y-3">
              <div className="flex justify-between items-center p-3 bg-green-50 rounded-lg">
                <span className="text-sm text-green-700">단기 목표</span>
                <span className="font-bold text-green-900">${analysis.price_targets?.short_term || 'N/A'}</span>
              </div>
              <div className="flex justify-between items-center p-3 bg-yellow-50 rounded-lg">
                <span className="text-sm text-yellow-700">중기 목표</span>
                <span className="font-bold text-yellow-900">${analysis.price_targets?.medium_term || 'N/A'}</span>
              </div>
              <div className="flex justify-between items-center p-3 bg-blue-50 rounded-lg">
                <span className="text-sm text-blue-700">장기 목표</span>
                <span className="font-bold text-blue-900">${analysis.price_targets?.long_term || 'N/A'}</span>
              </div>
            </div>
            
            <div className="mt-4 grid grid-cols-2 gap-3">
              <div className="text-center p-3 bg-green-50 rounded-lg">
                <div className="text-sm text-green-700 mb-1">상승 잠재력</div>
                <div className="text-lg font-bold text-green-900">+{analysis.price_targets?.short_term ? Math.round(((analysis.price_targets.short_term - 150) / 150) * 100) : 'N/A'}%</div>
              </div>
              <div className="text-center p-3 bg-red-50 rounded-lg">
                <div className="text-sm text-red-700 mb-1">하락 리스크</div>
                <div className="text-lg font-bold text-red-900">-{analysis.price_targets?.short_term ? Math.round(((150 - analysis.price_targets.short_term) / 150) * 100) : 'N/A'}%</div>
              </div>
            </div>
          </div>
          
          <div>
            <h4 className="text-lg font-semibold text-gray-800 mb-3">리스크 평가</h4>
            <div className="space-y-3">
              {Object.entries(analysis.risk_assessment).filter(([key]) => key !== 'risk_factors').map(([key, value]) => (
                <div key={key} className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                  <span className="text-sm text-gray-700 capitalize">
                    {key.replace('_', ' ')}
                  </span>
                  <Chip 
                    color={getRiskColor(value)}
                    variant="flat"
                    size="sm"
                  >
                    {value}
                  </Chip>
                </div>
              ))}
            </div>
            
            <div className="mt-4">
              <div className="text-sm text-gray-700 mb-2">주요 리스크 요인:</div>
              <div className="space-y-1">
                {analysis.risk_assessment?.risk_factors?.map((factor, index) => (
                  <div key={index} className="flex items-center space-x-2 text-sm text-gray-600">
                    <div className="w-1.5 h-1.5 bg-red-500 rounded-full"></div>
                    <span>{factor}</span>
                  </div>
                )) || (
                  <div className="text-sm text-gray-500">리스크 요인 정보가 없습니다</div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* 보유 기간 권장 */}
        <Divider />
        <div className="mt-6">
          <h4 className="text-lg font-semibold text-gray-800 mb-3">보유 기간 권장</h4>
          <div className="p-4 bg-blue-50 rounded-lg border border-blue-200">
            <div className="flex items-start space-x-3">
              <LightBulbIcon className="w-5 h-5 text-blue-600 mt-0.5" />
              <div className="flex-1">
                <div className="flex items-center space-x-3 mb-2">
                  <span className="text-sm font-medium text-blue-900">권장 기간:</span>
                  <Chip 
                    color="primary"
                    variant="flat"
                    size="sm"
                  >
                    {analysis.holding_period.recommended_period}
                  </Chip>
                </div>
                <div className="text-sm text-blue-800 mb-2">AI 분석 기반 권장사항</div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-blue-700 font-medium">리밸런싱:</span>
                    <span className="text-blue-800 ml-2">{analysis.holding_period.rebalancing_frequency}</span>
                  </div>
                  <div>
                    <span className="text-blue-700 font-medium">매도 전략:</span>
                    <span className="text-blue-800 ml-2">정기적인 포트폴리오 점검 권장</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </CardBody>
    </Card>
  )
}

export default AIStockAnalysis
