import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { MagnifyingGlassIcon, XMarkIcon, ArrowRightIcon } from '@heroicons/react/24/outline'
import { Card, CardBody, Input, Button, Chip } from '@heroui/react'
import { useQuery } from '@tanstack/react-query'
import { stockApi } from '../services/api'
import type { Stock } from '../types'

interface StockSearchProps {
  onStockSelect?: (stock: Stock) => void
  placeholder?: string
  className?: string
  enablePageTransition?: boolean
}

const StockSearch = ({ 
  onStockSelect, 
  placeholder = "주식 심볼, 회사명, 섹터로 검색...", 
  className = "",
  enablePageTransition = true
}: StockSearchProps) => {
  const [searchTerm, setSearchTerm] = useState('')
  const [isSearching, setIsSearching] = useState(false)
  const [showResults, setShowResults] = useState(false)
  const [selectedStock, setSelectedStock] = useState<Stock | null>(null)
  const searchRef = useRef<HTMLDivElement>(null)
  const resultsRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()

  // 모든 주식 데이터 가져오기
  const { data: stocksData } = useQuery({
    queryKey: ['stocks'],
    queryFn: stockApi.getStocks,
    retry: 3, // 3번 재시도
    retryDelay: 1000, // 1초 후 재시도
    staleTime: 5 * 60 * 1000, // 5분간 데이터 신선도 유지
    gcTime: 10 * 60 * 1000, // 10분간 캐시 유지
  })

  const stocks = stocksData?.data || []

  // 검색 결과 필터링
  const filteredStocks = stocks.filter(stock => {
    if (!searchTerm) return false
    
    const term = searchTerm.toLowerCase()
    return (
      stock.symbol.toLowerCase().includes(term) ||
      stock.name.toLowerCase().includes(term) ||
      stock.sector.toLowerCase().includes(term) ||
      stock.industry.toLowerCase().includes(term)
    )
  }).slice(0, 10) // 최대 10개 결과만 표시

  // 검색어 변경 핸들러
  const handleSearchChange = (value: string) => {
    setSearchTerm(value)
    setIsSearching(true)
    setShowResults(value.length > 0)
    
    // 디바운싱
    setTimeout(() => setIsSearching(false), 300)
  }

  // 주식 선택 핸들러
  const handleStockSelect = async (stock: Stock) => {
    setSelectedStock(stock)
    setSearchTerm(stock.symbol)
    setShowResults(false)
    
    // onStockSelect 콜백 실행
    onStockSelect?.(stock)
    
    // 페이지 전환 활성화된 경우 상세 페이지로 이동
    if (enablePageTransition) {
      // 부드러운 전환을 위한 약간의 지연
      setTimeout(() => {
        navigate(`/stocks/${stock.symbol}`, { 
          state: { stock },
          replace: false
        })
      }, 150)
    }
  }

  // 검색어 초기화
  const clearSearch = () => {
    setSearchTerm('')
    setShowResults(false)
    setSelectedStock(null)
  }

  // 외부 클릭 시 결과 숨기기
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setShowResults(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // 검색 결과가 표시될 때 스크롤 위치 조정
  useEffect(() => {
    if (showResults && resultsRef.current) {
      // 검색 결과가 화면에 완전히 보이도록 스크롤 조정
      const searchRect = searchRef.current?.getBoundingClientRect()
      const resultsRect = resultsRef.current?.getBoundingClientRect()
      
      if (searchRect && resultsRect) {
        const viewportHeight = window.innerHeight
        const resultsBottom = resultsRect.bottom
        
        // 검색 결과가 화면 아래쪽으로 넘어가는 경우
        if (resultsBottom > viewportHeight) {
          const scrollAmount = resultsBottom - viewportHeight + 20 // 20px 여유 공간
          window.scrollBy({
            top: scrollAmount,
            behavior: 'smooth'
          })
        }
      }
    }
  }, [showResults, filteredStocks])

  return (
    <div className={`relative ${className}`} ref={searchRef}>
      <Card className="w-full shadow-lg">
        <CardBody className="p-4">
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <MagnifyingGlassIcon className="h-5 w-5 text-gray-400" />
            </div>
            
            <Input
              type="text"
              placeholder={placeholder}
              value={searchTerm}
              onChange={(e) => handleSearchChange(e.target.value)}
              className="pl-10 pr-10"
              size="lg"
              variant="bordered"
              startContent={
                <MagnifyingGlassIcon className="h-5 w-5 text-gray-400" />
              }
              endContent={
                searchTerm && (
                  <Button
                    isIconOnly
                    size="sm"
                    variant="light"
                    onPress={clearSearch}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    <XMarkIcon className="h-4 w-4" />
                  </Button>
                )
              }
            />
          </div>

          {/* 검색 결과 - 검색창 바로 아래에 자연스럽게 표시 */}
          {showResults && (
            <div 
              ref={resultsRef}
              className="mt-3 bg-white border border-gray-200 rounded-lg shadow-xl max-h-96 overflow-y-auto"
            >
              {isSearching ? (
                <div className="p-4 text-center text-gray-500">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500 mx-auto mb-2"></div>
                  검색 중...
                </div>
              ) : filteredStocks.length > 0 ? (
                <div className="py-2">
                  {filteredStocks.map((stock) => (
                    <div
                      key={stock.id}
                      className="px-4 py-3 hover:bg-blue-50 cursor-pointer border-b border-gray-100 last:border-b-0 transition-all duration-200 hover:shadow-sm group"
                      onClick={() => handleStockSelect(stock)}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                          <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center text-white font-bold text-sm">
                            {stock.symbol[0]}
                          </div>
                          <div>
                            <div className="font-medium text-gray-900 group-hover:text-blue-600 transition-colors duration-200">
                              {stock.symbol}
                            </div>
                            <div className="text-sm text-gray-600">{stock.name}</div>
                          </div>
                        </div>
                        <div className="flex items-center space-x-2">
                          <div className="text-right">
                            <Chip size="sm" variant="flat" color="primary">
                              {stock.sector}
                            </Chip>
                            {stock.market_cap && (
                              <div className="text-xs text-gray-500 mt-1">
                                ${(stock.market_cap / 1e9).toFixed(1)}B
                              </div>
                            )}
                          </div>
                          <ArrowRightIcon className="h-4 w-4 text-gray-400 group-hover:text-blue-500 group-hover:translate-x-1 transition-all duration-200" />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : searchTerm.length > 0 ? (
                <div className="p-4 text-center text-gray-500">
                  <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-2">
                    <MagnifyingGlassIcon className="h-6 w-6 text-gray-400" />
                  </div>
                  <div>검색 결과가 없습니다</div>
                  <div className="text-sm">다른 키워드로 검색해보세요</div>
                </div>
              ) : null}
            </div>
          )}

          {/* 선택된 주식 정보 표시 */}
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
                <div className="text-right">
                  <Chip size="sm" variant="flat" color="primary">
                    {selectedStock.sector}
                  </Chip>
                </div>
              </div>
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  )
}

export default StockSearch
