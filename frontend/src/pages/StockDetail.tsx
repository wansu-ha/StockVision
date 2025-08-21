import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { stockApi } from '../services/api'
import StockChart from '../components/StockChart'
import VolumeChart from '../components/VolumeChart'

const StockDetail = () => {
  const { symbol } = useParams<{ symbol: string }>()

  const { data: stockData, isLoading: stockLoading, error: stockError } = useQuery({
    queryKey: ['stock', symbol],
    queryFn: () => stockApi.getStock(symbol!),
    enabled: !!symbol,
  })

  const { data: pricesData, isLoading: pricesLoading } = useQuery({
    queryKey: ['stock-prices', symbol],
    queryFn: () => stockApi.getStockPrices(symbol!, 30),
    enabled: !!symbol,
  })

  if (stockLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    )
  }

  if (stockError || !stockData) {
    return (
      <div className="text-center py-12">
        <div className="text-red-600 text-lg font-medium">주식 정보를 불러올 수 없습니다.</div>
        <div className="text-gray-500 mt-2">심볼: {symbol}</div>
      </div>
    )
  }

  const stock = stockData.data
  const prices = pricesData?.data?.prices || []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center space-x-4">
          <div className="w-16 h-16 bg-primary-100 rounded-lg flex items-center justify-center">
            <span className="text-primary-600 font-bold text-2xl">{stock.symbol[0]}</span>
          </div>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">{stock.symbol}</h1>
            <p className="text-xl text-gray-600">{stock.name}</p>
            <div className="flex items-center space-x-4 mt-2 text-sm text-gray-500">
              <span>{stock.sector}</span>
              <span>•</span>
              <span>{stock.industry}</span>
              {stock.market_cap && (
                <>
                  <span>•</span>
                  <span className="font-medium">${(stock.market_cap / 1e9).toFixed(1)}B</span>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Price Chart */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">가격 차트</h2>
        <StockChart prices={prices} symbol={stock.symbol} />
        <VolumeChart prices={prices} symbol={stock.symbol} />
      </div>

      {/* Recent Prices */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-medium text-gray-900">최근 가격 데이터</h2>
        </div>
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
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {pricesLoading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-4 text-center">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600 mx-auto"></div>
                  </td>
                </tr>
              ) : prices.length > 0 ? (
                prices.slice(0, 10).map((price, index) => (
                  <tr key={index} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{price.date}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${price.open.toFixed(2)}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${price.high.toFixed(2)}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${price.low.toFixed(2)}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">${price.close.toFixed(2)}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{price.volume.toLocaleString()}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} className="px-6 py-4 text-center text-gray-500">
                    가격 데이터가 없습니다.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export default StockDetail
