import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  MagnifyingGlassIcon,
  FunnelIcon,
  ArrowUpIcon,
  ArrowDownIcon,
  MinusIcon
} from '@heroicons/react/24/outline'
import { Card, CardBody, CardHeader, Button, Chip, Dropdown, DropdownTrigger, DropdownMenu, DropdownItem } from '@heroui/react'
import { stockApi } from '../services/api'
import StockSearch from '../components/StockSearch'
import type { Stock } from '../types'

const StockList = () => {
  const navigate = useNavigate()
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedSector, setSelectedSector] = useState<string>('all')
  const [sortBy, setSortBy] = useState<'symbol' | 'name' | 'market_cap' | 'sector'>('symbol')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc')

  const { data: stocksData, isLoading, error } = useQuery({
    queryKey: ['stocks'],
    queryFn: stockApi.getStocks,
    retry: 3, // 3번 재시도
    retryDelay: 1000, // 1초 후 재시도
    staleTime: 5 * 60 * 1000, // 5분간 데이터 신선도 유지
    gcTime: 10 * 60 * 1000, // 10분간 캐시 유지
  })

  const stocks = useMemo(() => stocksData?.data || [], [stocksData?.data])

  // 섹터 목록 추출
  const sectors = useMemo(() => {
    const sectorSet = new Set(stocks.map(stock => stock.sector))
    return Array.from(sectorSet).sort()
  }, [stocks])

  // 필터링 및 정렬된 주식 목록
  const filteredAndSortedStocks = useMemo(() => {
    const filtered = stocks.filter(stock => {
      const matchesSearch = !searchTerm || 
        stock.symbol.toLowerCase().includes(searchTerm.toLowerCase()) ||
        stock.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        stock.sector.toLowerCase().includes(searchTerm.toLowerCase()) ||
        stock.industry.toLowerCase().includes(searchTerm.toLowerCase())
      
      const matchesSector = selectedSector === 'all' || stock.sector === selectedSector
      
      return matchesSearch && matchesSector
    })

    // 정렬
    const sorted = [...filtered].sort((a, b) => {
      let aValue: string | number = a[sortBy] as string | number
      let bValue: string | number = b[sortBy] as string | number

      if (sortBy === 'market_cap') {
        aValue = (aValue as number) || 0
        bValue = (bValue as number) || 0
      } else {
        aValue = (aValue as string)?.toString().toLowerCase() || ''
        bValue = (bValue as string)?.toString().toLowerCase() || ''
      }

      if (aValue < bValue) return sortOrder === 'asc' ? -1 : 1
      if (aValue > bValue) return sortOrder === 'asc' ? 1 : -1
      return 0
    })

    return sorted
  }, [stocks, searchTerm, selectedSector, sortBy, sortOrder])

  const handleStockClick = (stock: Stock) => {
    navigate(`/stocks/${stock.symbol}`)
  }

  const handleSort = (field: typeof sortBy) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(field)
      setSortOrder('asc')
    }
  }

  const getSortIcon = (field: typeof sortBy) => {
    if (sortBy !== field) return <MinusIcon className="w-4 h-4 text-gray-400" />
    
    return sortOrder === 'asc' 
      ? <ArrowUpIcon className="w-4 h-4 text-blue-500" />
      : <ArrowDownIcon className="w-4 h-4 text-blue-500" />
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 bg-blue-500 rounded-full mx-auto mb-6 flex items-center justify-center animate-pulse">
            <MagnifyingGlassIcon className="w-6 h-6 text-white" />
          </div>
          <div className="text-gray-700 text-xl font-medium">주식 데이터를 불러오는 중...</div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 bg-red-500 rounded-full mx-auto mb-6 flex items-center justify-center">
            <MagnifyingGlassIcon className="w-6 h-6 text-white" />
          </div>
          <div className="text-gray-700 text-xl font-medium">데이터를 불러오는 중 오류가 발생했습니다</div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-12 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">주식 목록</h1>
          <p className="text-lg text-gray-600">등록된 모든 주식의 실시간 정보를 확인하세요</p>
        </div>

        {/* 검색 및 필터 */}
        <Card className="mb-8 shadow-lg">
          <CardBody className="p-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* 검색 */}
              <div className="lg:col-span-2">
                <StockSearch
                  onStockSelect={(stock) => setSearchTerm(stock.symbol)}
                  placeholder="주식 심볼, 회사명, 섹터로 검색..."
                />
              </div>

              {/* 섹터 필터 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  섹터별 필터
                </label>
                <Dropdown>
                  <DropdownTrigger>
                    <Button 
                      variant="bordered" 
                      className="w-full justify-between"
                    >
                      {selectedSector === 'all' ? '모든 섹터' : selectedSector}
                      <FunnelIcon className="w-4 h-4" />
                    </Button>
                  </DropdownTrigger>
                                     <DropdownMenu
                     selectedKeys={[selectedSector]}
                     onSelectionChange={(keys) => {
                       const selected = Array.from(keys)[0] as string
                       setSelectedSector(selected || 'all')
                     }}
                   >
                    <DropdownItem key="all">모든 섹터</DropdownItem>
                    {sectors.map((sector) => (
                      <DropdownItem key={sector}>{sector}</DropdownItem>
                    ))}
                  </DropdownMenu>
                </Dropdown>
              </div>
            </div>

            {/* 검색 결과 요약 */}
            <div className="mt-4 flex items-center justify-between text-sm text-gray-600">
              <span>
                총 {filteredAndSortedStocks.length}개 주식 (전체 {stocks.length}개)
              </span>
              {searchTerm && (
                <span>
                  "{searchTerm}" 검색 결과
                </span>
              )}
            </div>
          </CardBody>
        </Card>

        {/* 주식 목록 테이블 */}
        <Card className="shadow-lg">
          <CardHeader className="pb-6 p-6">
            <h2 className="text-2xl font-bold text-foreground">주식 정보</h2>
          </CardHeader>
          <CardBody className="pt-0 px-6 pb-6">
            <div className="overflow-x-auto">
              <table className="min-w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th 
                      className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                      onClick={() => handleSort('symbol')}
                    >
                      <div className="flex items-center space-x-2">
                        <span>주식</span>
                        {getSortIcon('symbol')}
                      </div>
                    </th>
                    <th 
                      className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                      onClick={() => handleSort('name')}
                    >
                      <div className="flex items-center space-x-2">
                        <span>회사명</span>
                        {getSortIcon('name')}
                      </div>
                    </th>
                    <th 
                      className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                      onClick={() => handleSort('sector')}
                    >
                      <div className="flex items-center space-x-2">
                        <span>섹터</span>
                        {getSortIcon('sector')}
                      </div>
                    </th>
                    <th 
                      className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                      onClick={() => handleSort('market_cap')}
                    >
                      <div className="flex items-center space-x-2">
                        <span>시가총액</span>
                        {getSortIcon('market_cap')}
                      </div>
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      산업
                    </th>
                    <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      상태
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {filteredAndSortedStocks.length > 0 ? (
                    filteredAndSortedStocks.map((stock) => (
                      <tr 
                        key={stock.id} 
                        className="hover:bg-gray-50 transition-colors cursor-pointer"
                        onClick={() => handleStockClick(stock)}
                      >
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center text-white font-bold text-sm">
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
                          <Chip size="sm" variant="flat" color="primary">
                            {stock.sector}
                          </Chip>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm font-medium text-gray-900">
                            {stock.market_cap ? `$${(stock.market_cap / 1e9).toFixed(1)}B` : 'N/A'}
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm text-gray-600">{stock.industry}</div>
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
                      <td colSpan={6} className="px-6 py-12 text-center text-gray-500">
                        <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                          <MagnifyingGlassIcon className="w-8 h-8 text-gray-400" />
                        </div>
                        <div className="text-lg font-medium">검색 결과가 없습니다</div>
                        <div className="text-sm">검색어나 필터를 변경해보세요</div>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </CardBody>
        </Card>
      </div>
    </div>
  )
}

export default StockList
