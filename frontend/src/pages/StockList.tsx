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
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="text-red-600 text-lg font-medium">데이터를 불러오는 중 오류가 발생했습니다.</div>
        <div className="text-gray-500 mt-2">백엔드 서버가 실행 중인지 확인해주세요.</div>
      </div>
    )
  }

  const stocks = stocksData?.data || []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">주식 목록</h1>
        <p className="mt-2 text-gray-600">등록된 모든 주식 정보를 확인하세요</p>
      </div>

      {/* Stocks Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {stocks.map((stock) => (
          <Link
            key={stock.id}
            to={`/stocks/${stock.symbol}`}
            className="bg-white rounded-lg shadow hover:shadow-md transition-shadow duration-200"
          >
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="w-12 h-12 bg-primary-100 rounded-lg flex items-center justify-center">
                  <span className="text-primary-600 font-bold text-lg">{stock.symbol[0]}</span>
                </div>
                <span className="text-sm font-medium text-gray-500">{stock.sector}</span>
              </div>
              
              <h3 className="text-lg font-semibold text-gray-900 mb-2">{stock.symbol}</h3>
              <p className="text-gray-600 mb-3">{stock.name}</p>
              
              <div className="flex items-center justify-between text-sm text-gray-500">
                <span>{stock.industry}</span>
                {stock.market_cap && (
                  <span className="font-medium">
                    ${(stock.market_cap / 1e9).toFixed(1)}B
                  </span>
                )}
              </div>
            </div>
          </Link>
        ))}
      </div>

      {stocks.length === 0 && (
        <div className="text-center py-12">
          <div className="text-gray-500 text-lg">등록된 주식이 없습니다.</div>
        </div>
      )}
    </div>
  )
}

export default StockList
