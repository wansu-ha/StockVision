import { useState, useEffect } from 'react'
import { ArrowUpIcon, ArrowDownIcon, MinusIcon } from '@heroicons/react/24/solid'
import { Card, CardBody, CardHeader, Chip, Button } from '@heroui/react'
import { useQuery } from '@tanstack/react-query'
import { stockApi } from '../services/api'
import type { Stock } from '../types'

interface LiveStockCardProps {
  stock: Stock
  onViewDetails?: (stock: Stock) => void
  className?: string
}

const LiveStockCard = ({ stock, onViewDetails, className = "" }: LiveStockCardProps) => {
  const [currentPrice, setCurrentPrice] = useState<number | null>(null)
  const [priceChange, setPriceChange] = useState<number>(0)
  const [priceChangePercent, setPriceChangePercent] = useState<number>(0)
  const [volume, setVolume] = useState<number | null>(null)

  // 최신 가격 데이터 가져오기
  const { data: priceData } = useQuery({
    queryKey: ['stock-prices', stock.symbol, 'latest'],
    queryFn: () => stockApi.getStockPrices(stock.symbol, 2), // 최근 2일 데이터
    refetchInterval: 300000, // 5분마다 갱신 (빈도 조정)
    enabled: !!stock.symbol,
    retry: 3, // 3번 재시도
    retryDelay: 1000, // 1초 후 재시도
    staleTime: 1 * 60 * 1000, // 1분간 데이터 신선도 유지 (실시간성 중요)
    gcTime: 3 * 60 * 1000, // 3분간 캐시 유지
  })

  // 가격 데이터 처리
  useEffect(() => {
    if (priceData?.data?.prices && priceData.data.prices.length >= 2) {
      const prices = priceData.data.prices
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
  }, [priceData])

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

  return (
    <div 
      className={`w-full cursor-pointer group ${className}`}
      onClick={() => onViewDetails?.(stock)}
    >
      <Card 
        className="w-full shadow-lg hover:shadow-xl hover:scale-[1.02] transition-all duration-300"
      >
      <CardHeader className="pb-4 p-6">
        <div className="flex items-center justify-between w-full">
          <div className="flex items-center space-x-3">
            <div className="w-12 h-12 bg-gradient-to-r from-blue-500 to-purple-600 rounded-xl flex items-center justify-center text-white font-bold text-lg group-hover:scale-110 transition-transform duration-200">
              {stock.symbol[0]}
            </div>
            <div>
              <h3 className="text-xl font-bold text-foreground group-hover:text-blue-600 transition-colors duration-200">{stock.symbol}</h3>
              <p className="text-sm text-default-500 group-hover:text-blue-500 transition-colors duration-200">{stock.name}</p>
            </div>
          </div>
          <Chip size="sm" variant="flat" color="primary">
            {stock.sector}
          </Chip>
        </div>
      </CardHeader>

      <CardBody className="pt-0 px-6 pb-6">
        <div className="space-y-4">
          {/* 현재가 및 변동률 */}
          <div className="text-center">
            <div className="text-3xl font-bold text-foreground mb-2">
              ${currentPrice?.toFixed(2) || 'N/A'}
            </div>
            <div className="flex items-center justify-center space-x-2">
              <IconComponent className={`w-4 h-4 text-${priceDisplay.color}`} />
              <span className={`text-${priceDisplay.color} font-medium`}>
                {priceDisplay.text}
              </span>
              <span className={`text-${priceDisplay.color} text-sm`}>
                ({priceChangePercent.toFixed(2)}%)
              </span>
            </div>
          </div>

          {/* 거래량 및 시가총액 */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div className="text-center">
              <p className="text-default-500">거래량</p>
              <p className="font-medium">
                {volume ? (volume / 1000000).toFixed(1) + 'M' : 'N/A'}
              </p>
            </div>
            <div className="text-center">
              <p className="text-default-500">시가총액</p>
              <p className="font-medium">
                {stock.market_cap ? (stock.market_cap / 1e9).toFixed(1) + 'B' : 'N/A'}
              </p>
            </div>
          </div>

          {/* 상세보기 버튼 */}
          <Button
            color="primary"
            variant="flat"
            className="w-full"
            onPress={() => onViewDetails?.(stock)}
          >
            📊 차트 & AI 분석 보기
          </Button>
        </div>
      </CardBody>
      </Card>
    </div>
  )
}

export default LiveStockCard
