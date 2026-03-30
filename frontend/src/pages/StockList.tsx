import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useMemo } from 'react'
import {
  MagnifyingGlassIcon,
  TrashIcon,
} from '@heroicons/react/24/outline'
import { Card, CardBody, CardHeader, Chip } from '@heroui/react'
import { cloudWatchlist, cloudStocks } from '../services/cloudClient'
import type { StockMasterItem } from '../services/cloudClient'
import StockSearch from '../components/StockSearch'

const StockList = () => {
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { data: watchlist = [], isLoading } = useQuery({
    queryKey: ['watchlist'],
    queryFn: cloudWatchlist.list,
    staleTime: 30_000,
  })

  // 관심종목에 대한 종목 상세 정보 (symbol → name/market)
  const { data: stockDetails = [] } = useQuery({
    queryKey: ['watchlist-details', watchlist.map(w => w.symbol).join(',')],
    queryFn: async () => {
      const results: StockMasterItem[] = []
      for (const item of watchlist) {
        const stock = await cloudStocks.get(item.symbol)
        if (stock) results.push(stock)
      }
      return results
    },
    enabled: watchlist.length > 0,
    staleTime: 5 * 60_000,
  })

  const addMut = useMutation({
    mutationFn: (symbol: string) => cloudWatchlist.add(symbol),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['watchlist'] }),
  })

  const removeMut = useMutation({
    mutationFn: (symbol: string) => cloudWatchlist.remove(symbol),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['watchlist'] }),
  })

  const handleAddStock = (stock: StockMasterItem) => {
    if (!watchlist.some(w => w.symbol === stock.symbol)) {
      addMut.mutate(stock.symbol)
    }
  }

  const detailMap = new Map(stockDetails.map(s => [s.symbol, s]))

  const watchlistSet = useMemo(
    () => new Set(watchlist.map(w => w.symbol)),
    [watchlist]
  )

  const handleToggleWatchlist = (symbol: string, add: boolean) => {
    if (add) {
      addMut.mutate(symbol)
    } else {
      removeMut.mutate(symbol)
    }
  }

  return (
    <div>
      <div className="max-w-4xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-100 mb-2">관심종목</h1>
          <p className="text-gray-400">종목을 검색하여 관심목록에 추가하세요</p>
        </div>

        {/* 종목 추가 검색 */}
        <div className="mb-8">
          <StockSearch
            onStockSelect={handleAddStock}
            placeholder="종목 코드 또는 회사명 검색 → 클릭하여 추가"
            enablePageTransition={false}
            watchlistSet={watchlistSet}
            onToggleWatchlist={handleToggleWatchlist}
          />
          {addMut.isError && (
            <p className="text-red-500 text-sm mt-2">추가 실패 — 이미 등록된 종목일 수 있습니다</p>
          )}
        </div>

        {/* 관심종목 목록 */}
        <Card className="shadow-lg">
          <CardHeader className="p-6 pb-4">
            <div className="flex items-center justify-between w-full">
              <h2 className="text-xl font-bold">내 관심종목</h2>
              <span className="text-sm text-gray-500">{watchlist.length}개</span>
            </div>
          </CardHeader>
          <CardBody className="pt-0 px-6 pb-6">
            {isLoading ? (
              <div className="text-center py-12 text-gray-500">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-3" />
                불러오는 중...
              </div>
            ) : watchlist.length === 0 ? (
              <div className="text-center py-12 text-gray-500">
                <MagnifyingGlassIcon className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                <p className="text-lg font-medium">관심종목이 없습니다</p>
                <p className="text-sm mt-1">위 검색창에서 종목을 검색하여 추가하세요</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-800">
                {watchlist.map((item) => {
                  const detail = detailMap.get(item.symbol)
                  return (
                    <div
                      key={item.symbol}
                      className="flex items-center justify-between py-3 group"
                    >
                      <div
                        className="flex items-center space-x-3 cursor-pointer flex-1 min-w-0"
                        onClick={() => navigate(`/stocks/${item.symbol}`)}
                      >
                        <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center text-white font-bold text-sm shrink-0">
                          {item.symbol[0]}
                        </div>
                        <div className="min-w-0">
                          <div className="font-medium text-gray-100 group-hover:text-indigo-400 transition-colors">
                            {item.symbol}
                          </div>
                          <div className="text-sm text-gray-500 truncate">
                            {detail?.name ?? '...'}
                          </div>
                        </div>
                        {detail?.market && (
                          <Chip size="sm" variant="flat" color="primary">{detail.market}</Chip>
                        )}
                      </div>
                      <button
                        onClick={() => removeMut.mutate(item.symbol)}
                        disabled={removeMut.isPending}
                        className="p-2 text-gray-500 hover:text-red-400 hover:bg-red-900/20 rounded-lg transition-colors shrink-0"
                        title="관심종목에서 제거"
                      >
                        <TrashIcon className="w-4 h-4" />
                      </button>
                    </div>
                  )
                })}
              </div>
            )}
          </CardBody>
        </Card>
      </div>
    </div>
  )
}

export default StockList
