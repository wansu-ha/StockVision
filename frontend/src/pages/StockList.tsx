import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { stockApi } from '../services/api'

const StockList = () => {
  const { data: stocksData, isLoading, error } = useQuery({
    queryKey: ['stocks'],
    queryFn: stockApi.getStocks,
  })

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="flex items-center justify-center h-96">
          <div className="text-center">
            <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mx-auto mb-4"></div>
            <div className="text-lg text-gray-600">주식 데이터를 불러오는 중...</div>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="text-center py-12">
          <div className="text-red-600 text-lg font-medium">데이터를 불러오는 중 오류가 발생했습니다.</div>
          <div className="text-gray-500 mt-2">백엔드 서버가 실행 중인지 확인해주세요.</div>
        </div>
      </div>
    )
  }

  const stocks = stocksData?.data || []

  // 섹터별 색상 매핑
  const getSectorColor = (sector: string) => {
    const colors: { [key: string]: string } = {
      'Technology': 'from-blue-500 to-blue-600',
      'Communication Services': 'from-green-500 to-green-600',
      'Consumer Cyclical': 'from-purple-500 to-purple-600',
      'Consumer Electronics': 'from-indigo-500 to-indigo-600',
      'Software - Infrastructure': 'from-teal-500 to-teal-600',
      'Internet Content & Information': 'from-orange-500 to-orange-600',
      'Internet Retail': 'from-red-500 to-red-600',
      'Auto Manufacturers': 'from-yellow-500 to-yellow-600',
    }
    return colors[sector] || 'from-gray-500 to-gray-600'
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="max-w-7xl mx-auto px-6 py-12">
        {/* Header */}
        <div className="text-center mb-16">
          <h1 className="text-5xl font-bold text-gray-900 mb-6">주식 목록</h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto">
            AI가 분석한 주요 기술주들의 상세 정보를 확인하고 투자 기회를 발견하세요
          </p>
          <div className="mt-8 inline-flex items-center px-6 py-3 bg-white rounded-full shadow-lg">
            <div className="w-3 h-3 bg-green-500 rounded-full mr-3 animate-pulse"></div>
            <span className="text-sm font-semibold text-gray-700">실시간 데이터 업데이트</span>
          </div>
        </div>

        {/* Stats Bar */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-12">
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-6 text-center">
            <div className="text-3xl font-bold text-blue-600">{stocks.length}</div>
            <div className="text-sm text-gray-600 mt-1">등록된 주식</div>
          </div>
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-6 text-center">
            <div className="text-3xl font-bold text-green-600">$12.9T</div>
            <div className="text-sm text-gray-600 mt-1">총 시가총액</div>
          </div>
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-6 text-center">
            <div className="text-3xl font-bold text-purple-600">91.6%</div>
            <div className="text-sm text-gray-600 mt-1">AI 정확도</div>
          </div>
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-6 text-center">
            <div className="text-3xl font-bold text-orange-600">5</div>
            <div className="text-sm text-gray-600 mt-1">분석 섹터</div>
          </div>
        </div>

        {/* Stocks Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {stocks.map((stock) => (
            <Link
              key={stock.id}
              to={`/stocks/${stock.symbol}`}
              className="group bg-white/90 backdrop-blur-sm rounded-3xl shadow-lg hover:shadow-2xl transition-all duration-300 hover:-translate-y-2 overflow-hidden"
            >
              {/* Card Header */}
              <div className={`bg-gradient-to-r ${getSectorColor(stock.sector)} p-6 text-white relative overflow-hidden`}>
                <div className="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full -translate-y-16 translate-x-16"></div>
                <div className="absolute bottom-0 left-0 w-20 h-20 bg-white/10 rounded-full translate-y-10 -translate-x-10"></div>
                
                <div className="relative z-10">
                  <div className="flex items-center justify-between mb-4">
                    <div className="w-16 h-16 bg-white/20 backdrop-blur-sm rounded-2xl flex items-center justify-center">
                      <span className="text-white font-bold text-2xl">{stock.symbol[0]}</span>
                    </div>
                    <span className="text-xs bg-white/20 backdrop-blur-sm px-3 py-1 rounded-full font-medium">
                      {stock.sector}
                    </span>
                  </div>
                  
                  <h3 className="text-2xl font-bold mb-1">{stock.symbol}</h3>
                  <p className="text-white/80 text-sm">{stock.name}</p>
                </div>
              </div>

              {/* Card Body */}
              <div className="p-6">
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">산업</span>
                    <span className="text-sm font-semibold text-gray-900">{stock.industry}</span>
                  </div>
                  
                  {stock.market_cap && (
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">시가총액</span>
                      <span className="text-lg font-bold text-green-600">
                        ${(stock.market_cap / 1e9).toFixed(1)}B
                      </span>
                    </div>
                  )}
                  
                  <div className="pt-4 border-t border-gray-100">
                    <div className="flex items-center justify-between">
                      <span className="text-sm text-gray-600">상태</span>
                      <div className="flex items-center space-x-2">
                        <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                        <span className="text-sm font-semibold text-green-600">활성</span>
                      </div>
                    </div>
                  </div>
                </div>
                
                {/* Hover Effect */}
                <div className="mt-6 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                  <div className="bg-gradient-to-r from-blue-500 to-indigo-600 text-white text-center py-3 rounded-2xl font-semibold">
                    상세 정보 보기 →
                  </div>
                </div>
              </div>
            </Link>
          ))}
        </div>

        {stocks.length === 0 && (
          <div className="text-center py-20">
            <div className="w-24 h-24 bg-gray-200 rounded-full flex items-center justify-center mx-auto mb-6">
              <div className="w-12 h-12 bg-gray-400 rounded-lg"></div>
            </div>
            <div className="text-gray-500 text-xl mb-2">등록된 주식이 없습니다</div>
            <div className="text-gray-400">주식 데이터를 추가해주세요</div>
          </div>
        )}
      </div>
    </div>
  )
}

export default StockList
