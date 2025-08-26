import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, CardBody, CardHeader, Chip, Progress } from '@heroui/react'
import { 
  ChartBarIcon, 
  ArrowTrendingUpIcon, 
  ArrowTrendingDownIcon, 
  ExclamationTriangleIcon,
  LightBulbIcon,
  ClockIcon
} from '@heroicons/react/24/outline'
import { aiAnalysisApi } from '../services/api'
import type { MarketOverview } from '../types'

const AIMarketOverview: React.FC = () => {
  const { data: marketData, isLoading, error } = useQuery({
    queryKey: ['market-overview'],
    queryFn: aiAnalysisApi.getMarketOverview,
    refetchInterval: 300000, // 5분마다 새로고침
    retry: 3, // 3번 재시도
    retryDelay: 1000, // 1초 후 재시도
    staleTime: 10 * 60 * 1000, // 10분간 데이터 신선도 유지
    gcTime: 15 * 60 * 1000, // 15분간 캐시 유지
  })

  if (isLoading) {
    return (
      <Card className="w-full shadow-lg">
        <CardBody className="p-6">
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
            <span className="ml-3 text-gray-600">AI가 시장을 분석하고 있습니다...</span>
          </div>
        </CardBody>
      </Card>
    )
  }

  if (error || !marketData?.data) {
    return (
      <Card className="w-full shadow-lg">
        <CardBody className="p-6">
          <div className="text-center py-8">
            <ExclamationTriangleIcon className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <div className="text-red-600 font-medium">시장 분석을 불러올 수 없습니다</div>
            <div className="text-sm text-gray-500 mt-2">잠시 후 다시 시도해주세요</div>
          </div>
        </CardBody>
      </Card>
    )
  }

  const market: MarketOverview = marketData.data

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case '긍정적':
        return 'success'
      case '중립적':
        return 'warning'
      case '부정적':
        return 'danger'
      default:
        return 'default'
    }
  }

  const getSentimentIcon = (sentiment: string) => {
    switch (sentiment) {
      case '긍정적':
        return <ArrowTrendingUpIcon className="w-5 h-5 text-green-600" />
      case '중립적':
        return <ChartBarIcon className="w-5 h-5 text-yellow-600" />
      case '부정적':
        return <ArrowTrendingDownIcon className="w-5 h-5 text-red-600" />
      default:
        return <ChartBarIcon className="w-5 h-5 text-gray-600" />
    }
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
              <h3 className="text-xl font-bold text-gray-900">AI 시장 분석</h3>
              <p className="text-sm text-gray-600">실시간 시장 동향 및 투자 전략</p>
            </div>
          </div>
          <div className="flex items-center space-x-2 text-sm text-gray-500">
            <ClockIcon className="w-4 h-4" />
            <span>{new Date(market.analysis_timestamp).toLocaleString('ko-KR')}</span>
          </div>
        </div>
      </CardHeader>
      
      <CardBody className="pt-0">
        {/* 시장 심리 요약 */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-lg font-semibold text-gray-800">시장 심리</h4>
            <Chip 
              color={getSentimentColor(market.overall_sentiment)}
              variant="flat"
              size="sm"
            >
              {market.overall_sentiment}
            </Chip>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="flex items-center justify-center mb-2">
                {getSentimentIcon(market.overall_sentiment)}
              </div>
              <div className="text-2xl font-bold text-gray-900">
                {Math.round(market.sentiment_score * 100)}%
              </div>
              <div className="text-sm text-gray-600">긍정도</div>
            </div>
            
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-2xl font-bold text-gray-900">{market.market_trend}</div>
              <div className="text-sm text-gray-600">시장 추세</div>
            </div>
            
            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-2xl font-bold text-gray-900">{market.market_volatility}</div>
              <div className="text-sm text-gray-600">변동성</div>
            </div>
          </div>
          
          <Progress 
            value={market.sentiment_score * 100} 
            color={getSentimentColor(market.overall_sentiment)}
            className="w-full"
            aria-label={`시장 심리 점수: ${Math.round(market.sentiment_score * 100)}%`}
          />
        </div>

        {/* 주요 요인 */}
        <div className="mb-6">
          <h4 className="text-lg font-semibold text-gray-800 mb-3">주요 시장 요인</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {market.key_factors.map((factor, index) => (
              <div key={index} className="flex items-center space-x-2 p-3 bg-blue-50 rounded-lg">
                <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                <span className="text-sm text-blue-800">{factor}</span>
              </div>
            ))}
          </div>
        </div>

        {/* 섹터별 전망 */}
        <div className="mb-6">
          <h4 className="text-lg font-semibold text-gray-800 mb-3">섹터별 전망</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {market.sector_outlook && Object.entries(market.sector_outlook).map(([sector, outlook]) => (
              <div key={sector} className="text-center p-3 bg-gray-50 rounded-lg">
                <div className="text-sm font-medium text-gray-900 capitalize">{sector}</div>
                <Chip 
                  color={getSentimentColor(outlook)}
                  variant="flat"
                  size="sm"
                  className="mt-2"
                >
                  {outlook}
                </Chip>
              </div>
            ))}
          </div>
        </div>

        {/* 투자 조언 및 리스크 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <h4 className="text-lg font-semibold text-gray-800 mb-3">투자 조언</h4>
            <div className="p-4 bg-green-50 rounded-lg border border-green-200">
              <div className="flex items-start space-x-3">
                <LightBulbIcon className="w-5 h-5 text-green-600 mt-0.5" />
                <div>
                  <div className="text-sm text-green-800 font-medium">{market.investment_advice}</div>
                  <div className="text-xs text-green-600 mt-1">
                    AI 분석 기반 투자 전략 제안
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <div>
            <h4 className="text-lg font-semibold text-gray-800 mb-3">리스크 평가</h4>
            <div className="p-4 bg-red-50 rounded-lg border border-red-200">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-red-800 font-medium">전체 리스크</span>
                <Chip 
                  color={getRiskColor(market.risk_level)}
                  variant="flat"
                  size="sm"
                >
                  {market.risk_level}
                </Chip>
              </div>
              <div className="text-xs text-red-600">
                유동성: {market.liquidity_condition}
              </div>
            </div>
          </div>
        </div>
      </CardBody>
    </Card>
  )
}

export default AIMarketOverview
