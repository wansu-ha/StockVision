import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { MagnifyingGlassIcon, XMarkIcon, ArrowRightIcon } from '@heroicons/react/24/outline'
import { Card, CardBody, Input, Button, Chip } from '@heroui/react'
import { cloudStocks } from '../services/cloudClient'
import type { StockMasterItem } from '../services/cloudClient'

interface StockSearchProps {
  onStockSelect?: (stock: StockMasterItem) => void
  placeholder?: string
  className?: string
  enablePageTransition?: boolean
}

const StockSearch = ({
  onStockSelect,
  placeholder = "종목 코드 또는 회사명으로 검색...",
  className = "",
  enablePageTransition = true
}: StockSearchProps) => {
  const [searchTerm, setSearchTerm] = useState('')
  const [results, setResults] = useState<StockMasterItem[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [showResults, setShowResults] = useState(false)
  const [selectedStock, setSelectedStock] = useState<StockMasterItem | null>(null)
  const searchRef = useRef<HTMLDivElement>(null)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const navigate = useNavigate()

  // 서버 검색 (디바운스)
  const doSearch = useCallback((query: string) => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    if (!query.trim()) {
      setResults([])
      setShowResults(false)
      return
    }
    setIsSearching(true)
    debounceRef.current = setTimeout(async () => {
      try {
        const items = await cloudStocks.search(query, 10)
        setResults(items)
      } catch {
        setResults([])
      } finally {
        setIsSearching(false)
      }
    }, 300)
  }, [])

  const handleSearchChange = (value: string) => {
    setSearchTerm(value)
    setShowResults(value.length > 0)
    doSearch(value)
  }

  const handleStockSelect = (stock: StockMasterItem) => {
    setSelectedStock(stock)
    setSearchTerm(stock.symbol)
    setShowResults(false)
    onStockSelect?.(stock)

    if (enablePageTransition) {
      setTimeout(() => {
        navigate(`/stocks/${stock.symbol}`, { replace: false })
      }, 150)
    }
  }

  const clearSearch = () => {
    setSearchTerm('')
    setShowResults(false)
    setSelectedStock(null)
    setResults([])
  }

  // 외부 클릭 시 닫기
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setShowResults(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  return (
    <div className={`relative ${className}`} ref={searchRef}>
      <Card className="w-full shadow-lg">
        <CardBody className="p-4">
          <Input
            type="text"
            placeholder={placeholder}
            value={searchTerm}
            onChange={(e) => handleSearchChange(e.target.value)}
            size="lg"
            variant="bordered"
            startContent={<MagnifyingGlassIcon className="h-5 w-5 text-gray-400" />}
            endContent={
              searchTerm && (
                <Button isIconOnly size="sm" variant="light" onPress={clearSearch} className="text-gray-400 hover:text-gray-600">
                  <XMarkIcon className="h-4 w-4" />
                </Button>
              )
            }
          />

          {/* 검색 결과 */}
          {showResults && (
            <div className="mt-3 bg-white border border-gray-200 rounded-lg shadow-xl max-h-96 overflow-y-auto">
              {isSearching ? (
                <div className="p-4 text-center text-gray-500">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500 mx-auto mb-2" />
                  검색 중...
                </div>
              ) : results.length > 0 ? (
                <div className="py-2">
                  {results.map((stock) => (
                    <div
                      key={stock.symbol}
                      className="px-4 py-3 hover:bg-blue-50 cursor-pointer border-b border-gray-100 last:border-b-0 transition-all duration-200 group"
                      onClick={() => handleStockSelect(stock)}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                          <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center text-white font-bold text-sm">
                            {stock.symbol[0]}
                          </div>
                          <div>
                            <div className="font-medium text-gray-900 group-hover:text-blue-600 transition-colors">
                              {stock.symbol}
                            </div>
                            <div className="text-sm text-gray-600">{stock.name}</div>
                          </div>
                        </div>
                        <div className="flex items-center space-x-2">
                          {stock.market && (
                            <Chip size="sm" variant="flat" color="primary">{stock.market}</Chip>
                          )}
                          <ArrowRightIcon className="h-4 w-4 text-gray-400 group-hover:text-blue-500 group-hover:translate-x-1 transition-all" />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : searchTerm.length > 0 ? (
                <div className="p-4 text-center text-gray-500">
                  <MagnifyingGlassIcon className="h-8 w-8 text-gray-300 mx-auto mb-2" />
                  <div>검색 결과가 없습니다</div>
                  <div className="text-sm">다른 키워드로 검색해보세요</div>
                </div>
              ) : null}
            </div>
          )}

          {/* 선택된 종목 */}
          {selectedStock && !showResults && (
            <div className="mt-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center text-white font-bold text-xs">
                    {selectedStock.symbol[0]}
                  </div>
                  <div>
                    <div className="font-medium text-blue-900">{selectedStock.symbol}</div>
                    <div className="text-sm text-blue-700">{selectedStock.name}</div>
                  </div>
                </div>
                {selectedStock.market && (
                  <Chip size="sm" variant="flat" color="primary">{selectedStock.market}</Chip>
                )}
              </div>
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  )
}

export default StockSearch
