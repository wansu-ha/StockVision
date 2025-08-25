import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ChartBarIcon,
  ArrowTrendingUpIcon,
  CpuChipIcon,
  ExclamationTriangleIcon,
  RocketLaunchIcon,
  BanknotesIcon,
  ChartPieIcon,
  MagnifyingGlassIcon
} from '@heroicons/react/24/outline'
import { Card, CardBody, CardHeader, Chip, Button } from '@heroui/react'
import { stockApi } from '../services/api'
import StockSearch from '../components/StockSearch'
import LiveStockCard from '../components/LiveStockCard'
import AIMarketOverview from '../components/AIMarketOverview'
import type { Stock } from '../types'

const Dashboard = () => {
  const navigate = useNavigate()
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedStock, setSelectedStock] = useState<Stock | null>(null)
  


  const { data: stocksData, isLoading, error } = useQuery({
    queryKey: ['stocks'],
    queryFn: stockApi.getStocks,
  })

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 bg-blue-500 rounded-full mx-auto mb-6 flex items-center justify-center animate-pulse">
            <CpuChipIcon className="w-6 h-6 text-white" />
          </div>
          <div className="text-gray-700 text-xl font-medium">AI가 데이터를 분석하고 있습니다...</div>
          <div className="text-gray-500 mt-2">잠시만 기다려주세요</div>
        </div>
      </div>
    )
  }

  if (error) {
    console.error('Dashboard error:', error)
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 bg-red-500 rounded-full mx-auto mb-6 flex items-center justify-center">
            <ExclamationTriangleIcon className="w-6 h-6 text-white" />
          </div>
          <div className="text-gray-700 text-xl font-medium">데이터를 불러오는 중 오류가 발생했습니다</div>
          <div className="text-red-500 mt-2">백엔드 서버가 실행 중인지 확인해주세요</div>
        </div>
      </div>
    )
  }

  const stocks = stocksData?.data || []

  const marketStats = {
    totalValue: 12920000000000,
    dailyChange: 2.34,
    weeklyChange: 5.67,
    monthlyChange: 12.45
  }

  // 검색된 주식 필터링
  const filteredStocks = stocks.filter(stock => {
    if (!searchTerm) return stocks.slice(0, 6) // 검색어가 없으면 처음 6개
    
    const term = searchTerm.toLowerCase()
    return (
      stock.symbol.toLowerCase().includes(term) ||
      stock.name.toLowerCase().includes(term) ||
      stock.sector.toLowerCase().includes(term) ||
      stock.industry.toLowerCase().includes(term)
    )
  }).slice(0, 6)

  const handleStockSelect = (stock: Stock) => {
    setSelectedStock(stock)
    setSearchTerm(stock.symbol)
  }

  const handleViewDetails = (stock: Stock) => {
    navigate(`/stocks/${stock.symbol}`)
  }

  const handleQuickSearch = () => {
    if (selectedStock) {
      navigate(`/stocks/${selectedStock.symbol}`)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      {/* Hero Header */}
      <div className="bg-white shadow-lg border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="text-center">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-r from-blue-600 to-purple-600 rounded-3xl mb-8 shadow-xl transform hover:scale-105 transition-transform duration-200">
              <RocketLaunchIcon className="w-8 h-8 text-white" />
            </div>
            
            <h1 className="text-5xl font-bold bg-gradient-to-r from-gray-900 via-blue-800 to-purple-800 bg-clip-text text-transparent mb-6">
              StockVision
            </h1>
            
            <p className="text-xl text-gray-600 max-w-3xl mx-auto leading-relaxed mb-8">
              AI 기반 주식 동향 예측과 가상 거래로 스마트한 투자 결정을 내리세요
            </p>

            {/* 주식 검색 */}
            <div className="max-w-2xl mx-auto mb-8">
              <StockSearch
                onStockSelect={handleStockSelect}
                placeholder="주식 심볼, 회사명, 섹터로 검색..."
                className="w-full"
                enablePageTransition={true}
              />
              {selectedStock && (
                <div className="mt-4 flex items-center justify-center space-x-4">
                  <span className="text-sm text-gray-600">
                    선택된 주식: <strong>{selectedStock.symbol}</strong> - {selectedStock.name}
                  </span>
                  <Button
                    size="sm"
                    color="primary"
                    onPress={handleQuickSearch}
                  >
                    상세 정보 보기
                  </Button>
                </div>
              )}
            </div>
            
            <div className="flex items-center justify-center space-x-6">
              <div className="flex items-center space-x-2 bg-blue-50 px-4 py-2 rounded-full">
                <ChartPieIcon className="w-5 h-5 text-blue-600" />
                <span className="text-blue-800 font-medium">실시간 분석</span>
              </div>
              <div className="flex items-center space-x-2 bg-green-50 px-4 py-2 rounded-full">
                <ArrowTrendingUpIcon className="w-5 h-5 text-green-600" />
                <span className="text-green-800 font-medium">AI 예측</span>
              </div>
              <div className="flex items-center space-x-2 bg-purple-50 px-4 py-2 rounded-full">
                <BanknotesIcon className="w-5 h-5 text-purple-600" />
                <span className="text-purple-800 font-medium">가상 거래</span>
              </div>
            </div>
            

          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-12 py-12">
        {/* Market Overview Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 mb-16">
          <Card className="w-full shadow-lg hover:shadow-xl transition-shadow duration-300">
            <CardHeader className="flex gap-4 p-6 pb-4">
              <div className="flex flex-col w-full space-y-3">
                <p className="text-small text-default-500 font-medium">총 시가총액</p>
                <p className="text-3xl font-bold text-foreground">${(marketStats.totalValue / 1e12).toFixed(2)}T</p>
              </div>
              <Chip color="success" variant="flat" size="sm" className="self-start">+{marketStats.dailyChange}%</Chip>
            </CardHeader>
          </Card>

          <Card className="w-full shadow-lg hover:shadow-xl transition-shadow duration-300">
            <CardHeader className="flex gap-4 p-6 pb-4">
              <div className="flex flex-col w-full space-y-3">
                <p className="text-small text-default-500 font-medium">등록된 주식</p>
                <p className="text-3xl font-bold text-foreground">{stocks.length}개</p>
              </div>
            </CardHeader>
            <CardBody className="pt-0 px-6 pb-6">
              <p className="text-small text-default-400">실시간 모니터링</p>
            </CardBody>
          </Card>

          <Card className="w-full shadow-lg hover:shadow-xl transition-shadow duration-300">
            <CardHeader className="flex gap-4 p-6 pb-4">
              <div className="flex flex-col w-full space-y-3">
                <p className="text-small text-default-500 font-medium">AI 예측 정확도</p>
                <p className="text-3xl font-bold text-foreground">91.6%</p>
              </div>
              <Chip color="secondary" variant="flat" size="sm" className="self-start">Random Forest</Chip>
            </CardHeader>
          </Card>

          <Card className="w-full shadow-lg hover:shadow-xl transition-shadow duration-300">
            <CardHeader className="flex gap-4 p-6 pb-4">
              <div className="flex flex-col w-full space-y-3">
                <p className="text-small text-default-500 font-medium">가상 거래</p>
                <p className="text-3xl font-bold text-foreground">활성</p>
              </div>
            </CardHeader>
            <CardBody className="pt-0 px-6 pb-6">
              <p className="text-small text-default-400">초기 자본 1억원</p>
            </CardBody>
          </Card>
        </div>

        {/* AI 시장 분석 */}
        <div className="mb-12">
          <AIMarketOverview />
        </div>

        {/* 실시간 주식 모니터링 */}
        <Card className="mb-12 shadow-lg">
          <CardHeader className="pb-6 p-6">
            <div className="flex flex-col space-y-3">
              <h2 className="text-2xl font-bold text-foreground">실시간 주식 모니터링</h2>
              <p className="text-default-500 text-medium">
                {searchTerm ? `"${searchTerm}" 검색 결과` : '주요 기술주들의 실시간 현황'}
              </p>
            </div>
          </CardHeader>
          <CardBody className="pt-0 px-6 pb-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredStocks.map((stock) => (
                <LiveStockCard
                  key={stock.id}
                  stock={stock}
                  onViewDetails={handleViewDetails}
                />
              ))}
            </div>
            {filteredStocks.length === 0 && (
              <div className="text-center py-12 text-gray-500">
                <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <MagnifyingGlassIcon className="w-8 h-8 text-gray-400" />
                </div>
                <div className="text-lg font-medium">검색 결과가 없습니다</div>
                <div className="text-sm">다른 키워드로 검색해보세요</div>
              </div>
            )}
          </CardBody>
        </Card>

        {/* Recent Stocks Section */}
        <Card className="mb-12 shadow-lg">
          <CardHeader className="pb-6 p-6">
            <div className="flex flex-col space-y-3">
              <h2 className="text-2xl font-bold text-foreground">최근 등록된 주식</h2>
              <p className="text-default-500 text-medium">AI가 분석한 주요 기술주들의 현황</p>
            </div>
          </CardHeader>
          <CardBody className="pt-0 px-6 pb-6">
          
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">주식</th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">회사명</th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">섹터</th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">시가총액</th>
                  <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">상태</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {stocks.length > 0 ? (
                  stocks.slice(0, 5).map((stock) => (
                    <tr key={stock.id} className="hover:bg-gray-50 transition-colors cursor-pointer" onClick={() => handleViewDetails(stock)}>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center text-white font-bold text-sm">
                            {stock.symbol[0]}
                          </div>
                          <div className="ml-3">
                            <div className="text-sm font-medium text-gray-900">{stock.symbol}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-gray-900">{stock.name}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                          {stock.sector}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">
                          ${stock.market_cap ? (stock.market_cap / 1e9).toFixed(1) : 'N/A'}B
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          <div className="w-2 h-2 bg-green-400 rounded-full mr-2"></div>
                          활성
                        </span>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={5} className="px-6 py-12 text-center text-gray-500">
                      <div className="w-10 h-10 bg-gray-200 rounded-full flex items-center justify-center mx-auto mb-4">
                        <ChartBarIcon className="w-5 h-5 text-gray-400" />
                      </div>
                      <div className="text-sm">주식 데이터가 없습니다</div>
                      <div className="text-xs">데이터를 추가해주세요</div>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          </CardBody>
        </Card>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <Card className="w-full shadow-lg hover:shadow-xl transition-shadow duration-300">
            <CardHeader className="pb-4 p-6">
              <h3 className="text-xl font-bold text-foreground">AI 예측 시작</h3>
            </CardHeader>
            <CardBody className="pt-0 space-y-6 px-6 pb-6">
              <p className="text-default-500 leading-relaxed">머신러닝 모델로 주가 예측을 시작하고 투자 기회를 발견하세요</p>
              <button className="bg-blue-500 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-600 transition-all duration-200 transform hover:scale-105">
                예측 시작 →
              </button>
            </CardBody>
          </Card>

          <Card className="w-full shadow-lg hover:shadow-xl transition-shadow duration-300">
            <CardHeader className="pb-4 p-6">
              <h3 className="text-xl font-bold text-foreground">가상 거래</h3>
            </CardHeader>
            <CardBody className="pt-0 space-y-6 px-6 pb-6">
              <p className="text-default-500 leading-relaxed">리스크 없는 가상 환경에서 투자 전략을 연습하고 검증하세요</p>
              <button className="bg-green-500 text-white px-6 py-3 rounded-lg font-medium hover:bg-green-600 transition-all duration-200 transform hover:scale-105">
                거래 시작 →
              </button>
            </CardBody>
          </Card>

          <Card className="w-full shadow-lg hover:shadow-xl transition-shadow duration-300">
            <CardHeader className="pb-4 p-6">
              <h3 className="text-xl font-bold text-foreground">백테스팅</h3>
            </CardHeader>
            <CardBody className="pt-0 space-y-6 px-6 pb-6">
              <p className="text-default-500 leading-relaxed">과거 데이터로 투자 전략을 검증하고 성과를 분석하세요</p>
              <button className="bg-purple-500 text-white px-6 py-3 rounded-lg font-medium hover:bg-purple-600 transition-all duration-200 transform hover:scale-105">
                분석 시작 →
              </button>
            </CardBody>
          </Card>
        </div>
      </div>
    </div>
  )
}

export default Dashboard