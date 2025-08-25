import { useParams, useNavigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { 
  ArrowLeftIcon, 
  ArrowUpIcon, 
  ArrowDownIcon, 
  MinusIcon,
  ChartBarIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon
} from '@heroicons/react/24/outline'
import { Card, CardBody, CardHeader, Chip, Button } from '@heroui/react'
import { stockApi } from '../services/api'
import StockChart from '../components/StockChart'
import VolumeChart from '../components/VolumeChart'
import AIStockAnalysis from '../components/AIStockAnalysis'
import type { TechnicalIndicator } from '../types'

const StockDetail = () => {
  const { symbol } = useParams<{ symbol: string }>()
  const navigate = useNavigate()
  const [currentPrice, setCurrentPrice] = useState<number | null>(null)
  const [priceChange, setPriceChange] = useState<number>(0)
  const [priceChangePercent, setPriceChangePercent] = useState<number>(0)
  const [volume, setVolume] = useState<number | null>(null)

  const { data: stockData, isLoading: stockLoading, error: stockError } = useQuery({
    queryKey: ['stock', symbol],
    queryFn: () => stockApi.getStock(symbol!),
    enabled: !!symbol,
  })

  const { data: pricesData, isLoading: pricesLoading } = useQuery({
    queryKey: ['stock-prices', symbol],
    queryFn: () => stockApi.getStockPrices(symbol!, 30),
    enabled: !!symbol,
    refetchInterval: 300000, // 5분마다 갱신 (빈도 조정)
  })

  const { data: indicatorsData } = useQuery({
    queryKey: ['stock-indicators', symbol],
    queryFn: () => stockApi.getStockIndicators(symbol!, 30),
    enabled: !!symbol,
  })

  // 실시간 가격 데이터 처리
  useEffect(() => {
    if (pricesData?.data?.prices && pricesData.data.prices.length >= 2) {
      const prices = pricesData.data.prices
      const latestPrice = prices[prices.length - 1]
      const previousPrice = prices[prices.length - 2]

      if (latestPrice && previousPrice) {
        const current = latestPrice.close
        const previous = previousPrice.close
        const change = current - previous
        const changePercent = (change / previous) * 100

        setCurrentPrice(current)
        setPriceChange(change)
        setPriceChangePercent(changePercent)
        setVolume(latestPrice.volume)
      }
    }
  }, [pricesData])

  if (stockLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 bg-blue-500 rounded-full mx-auto mb-6 flex items-center justify-center animate-pulse">
            <ChartBarIcon className="w-6 h-6 text-white" />
          </div>
          <div className="text-gray-700 text-xl font-medium">주식 정보를 불러오는 중...</div>
        </div>
      </div>
    )
  }

  if (stockError || !stockData) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 bg-red-500 rounded-full mx-auto mb-6 flex items-center justify-center">
            <ChartBarIcon className="w-6 h-6 text-white" />
          </div>
          <div className="text-gray-700 text-xl font-medium">주식 정보를 불러올 수 없습니다</div>
          <div className="text-gray-500 mt-2">심볼: {symbol}</div>
          <Button 
            color="primary" 
            variant="flat" 
            className="mt-4"
            onPress={() => navigate('/stocks')}
          >
            주식 목록으로 돌아가기
          </Button>
        </div>
      </div>
    )
  }

  const stock = stockData.data
  const prices = pricesData?.data?.prices || []
  const indicators = indicatorsData?.data?.indicators || {}

  // 가격 변동에 따른 색상 및 아이콘
  const getPriceDisplay = () => {
    if (currentPrice === null) return { color: 'default', icon: MinusIcon, text: 'N/A' }
    
    if (priceChange > 0) {
      return { color: 'success', icon: ArrowUpIcon, text: `+$${priceChange.toFixed(2)}` }
    } else if (priceChange < 0) {
      return { color: 'danger', icon: ArrowDownIcon, text: `-$${Math.abs(priceChange).toFixed(2)}` }
    } else {
      return { color: 'default', icon: MinusIcon, text: '$0.00' }
    }
  }

  const priceDisplay = getPriceDisplay()
  const IconComponent = priceDisplay.icon

  // 기술적 지표 데이터
  const latestIndicators = Object.keys(indicators).reduce((acc, key) => {
    const indicatorArray = indicators[key]
    if (indicatorArray && indicatorArray.length > 0) {
      acc[key] = indicatorArray[indicatorArray.length - 1]
    }
    return acc
  }, {} as Record<string, TechnicalIndicator>)

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-12 py-8">
        {/* 뒤로가기 버튼 */}
        <Button
          variant="light"
          color="primary"
          startContent={<ArrowLeftIcon className="w-4 h-4" />}
          className="mb-6"
          onPress={() => navigate('/stocks')}
        >
          주식 목록으로 돌아가기
        </Button>

        {/* Header */}
        <Card className="mb-8 shadow-lg">
          <CardBody className="p-8">
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between">
              <div className="flex items-center space-x-6 mb-6 lg:mb-0">
                <div className="w-20 h-20 bg-gradient-to-r from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center">
                  <span className="text-white font-bold text-3xl">{stock.symbol[0]}</span>
                </div>
                <div>
                  <h1 className="text-4xl font-bold text-gray-900 mb-2">{stock.symbol}</h1>
                  <p className="text-2xl text-gray-600 mb-3">{stock.name}</p>
                  <div className="flex items-center space-x-4 text-sm">
                    <Chip size="sm" variant="flat" color="primary">{stock.sector}</Chip>
                    <Chip size="sm" variant="flat" color="secondary">{stock.industry}</Chip>
                    {stock.market_cap && (
                      <Chip size="sm" variant="flat" color="success">
                        ${(stock.market_cap / 1e9).toFixed(1)}B
                      </Chip>
                    )}
                  </div>
                </div>
              </div>

              {/* 실시간 가격 정보 */}
              <div className="text-right">
                <div className="text-5xl font-bold text-gray-900 mb-2">
                  ${currentPrice?.toFixed(2) || 'N/A'}
                </div>
                <div className="flex items-center justify-center lg:justify-end space-x-2 mb-2">
                  <IconComponent className={`w-5 h-5 text-${priceDisplay.color}`} />
                  <span className={`text-xl font-medium text-${priceDisplay.color}`}>
                    {priceDisplay.text}
                  </span>
                  <span className={`text-lg text-${priceDisplay.color}`}>
                    ({priceChangePercent.toFixed(2)}%)
                  </span>
                </div>
                <div className="text-sm text-gray-500">
                  거래량: {volume ? (volume / 1000000).toFixed(1) + 'M' : 'N/A'}
                </div>
              </div>
            </div>
          </CardBody>
        </Card>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* 차트 섹션 */}
          <div className="lg:col-span-2 space-y-8">
            {/* 가격 차트 */}
            <Card className="shadow-lg">
              <CardHeader className="pb-4 p-6">
                <h2 className="text-xl font-bold text-foreground">가격 차트 (30일)</h2>
              </CardHeader>
              <CardBody className="pt-0 px-6 pb-6">
                <StockChart prices={prices} symbol={stock.symbol} />
              </CardBody>
            </Card>

            {/* 거래량 차트 */}
            <Card className="shadow-lg">
              <CardHeader className="pb-4 p-6">
                <h2 className="text-xl font-bold text-foreground">거래량 차트</h2>
              </CardHeader>
              <CardBody className="pt-0 px-6 pb-6">
                <VolumeChart prices={prices} symbol={stock.symbol} />
              </CardBody>
            </Card>
          </div>

          {/* 사이드바 */}
          <div className="space-y-6">
            {/* 기술적 지표 */}
            <Card className="shadow-lg">
              <CardHeader className="pb-4 p-6">
                <h3 className="text-lg font-bold text-foreground">기술적 지표</h3>
              </CardHeader>
              <CardBody className="pt-0 px-6 pb-6">
                <div className="space-y-4">
                  {Object.keys(latestIndicators).map((indicatorKey) => {
                    const indicator = latestIndicators[indicatorKey]
                    if (!indicator) return null

                    const value = indicator.value
                    let color = 'default'
                    let icon = MinusIcon

                    // RSI 특별 처리
                    if (indicatorKey === 'rsi') {
                      if (value > 70) {
                        color = 'danger'
                        icon = ArrowTrendingDownIcon
                      } else if (value < 30) {
                        color = 'success'
                        icon = ArrowTrendingUpIcon
                      }
                    }

                    const IconComponent = icon

                    return (
                      <div key={indicatorKey} className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <IconComponent className={`w-4 h-4 text-${color}`} />
                          <span className="text-sm font-medium text-gray-700 capitalize">
                            {indicatorKey.toUpperCase()}
                          </span>
                        </div>
                        <span className={`text-sm font-bold text-${color}`}>
                          {typeof value === 'number' ? value.toFixed(2) : value}
                        </span>
                      </div>
                    )
                  })}
                </div>
              </CardBody>
            </Card>

            {/* 최근 가격 데이터 */}
            <Card className="shadow-lg">
              <CardHeader className="pb-4 p-6">
                <h3 className="text-lg font-bold text-foreground">최근 가격 데이터</h3>
              </CardHeader>
              <CardBody className="pt-0 px-6 pb-6">
                <div className="space-y-3">
                  {pricesLoading ? (
                    <div className="text-center py-4">
                      <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500 mx-auto"></div>
                    </div>
                  ) : prices.length > 0 ? (
                    prices.slice(0, 5).map((price, index) => (
                      <div key={index} className="flex items-center justify-between text-sm">
                        <span className="text-gray-600">{price.date}</span>
                        <div className="flex items-center space-x-4">
                          <span className="text-gray-900">${price.close.toFixed(2)}</span>
                          <span className="text-gray-500">
                            {price.volume > 1000000 
                              ? (price.volume / 1000000).toFixed(1) + 'M'
                              : (price.volume / 1000).toFixed(0) + 'K'
                            }
                          </span>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="text-center py-4 text-gray-500">
                      가격 데이터가 없습니다
                    </div>
                  )}
                </div>
              </CardBody>
            </Card>
          </div>
        </div>

        {/* 상세 가격 테이블 */}
        <Card className="mt-8 shadow-lg">
          <CardHeader className="pb-4 p-6">
            <h2 className="text-xl font-bold text-foreground">상세 가격 데이터</h2>
          </CardHeader>
          <CardBody className="pt-0 px-6 pb-6">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">날짜</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">시가</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">고가</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">저가</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">종가</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">거래량</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">변동률</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {pricesLoading ? (
                    <tr>
                      <td colSpan={7} className="px-6 py-4 text-center">
                        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500 mx-auto"></div>
                      </td>
                    </tr>
                  ) : prices.length > 0 ? (
                    prices.map((price, index) => {
                      const prevPrice = index > 0 ? prices[index - 1].close : price.close
                      const changePercent = ((price.close - prevPrice) / prevPrice) * 100
                      const isPositive = changePercent >= 0

                      return (
                        <tr key={index} className="hover:bg-gray-50">
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{price.date}</td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${price.open.toFixed(2)}</td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${price.high.toFixed(2)}</td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${price.low.toFixed(2)}</td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${price.close.toFixed(2)}</td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                            {price.volume > 1000000 
                              ? (price.volume / 1000000).toFixed(1) + 'M'
                              : (price.volume / 1000).toFixed(0) + 'K'
                            }
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm">
                            <span className={`font-medium ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
                              {isPositive ? '+' : ''}{changePercent.toFixed(2)}%
                            </span>
                          </td>
                        </tr>
                      )
                    })
                  ) : (
                    <tr>
                      <td colSpan={7} className="px-6 py-4 text-center text-gray-500">
                        가격 데이터가 없습니다
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </CardBody>
        </Card>

        {/* AI 주식 분석 */}
        <div className="mt-8">
          <AIStockAnalysis symbol={symbol!} />
        </div>
      </div>
    </div>
  )
}

export default StockDetail
