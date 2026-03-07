import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ArrowTrendingUpIcon,
  RocketLaunchIcon,
  BanknotesIcon,
  ChartPieIcon,
} from '@heroicons/react/24/outline'
import { Card, CardBody, CardHeader, Button } from '@heroui/react'
import StockSearch from '../components/StockSearch'
import type { StockMasterItem } from '../services/cloudClient'

const Dashboard = () => {
  const navigate = useNavigate()
  const [selectedStock, setSelectedStock] = useState<StockMasterItem | null>(null)

  const handleStockSelect = (stock: StockMasterItem) => {
    setSelectedStock(stock)
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
              AI 기반 시스템 매매 플랫폼 — 종목을 검색하고 전략을 설정하세요
            </p>

            {/* 종목 검색 */}
            <div className="max-w-2xl mx-auto mb-8">
              <StockSearch
                onStockSelect={handleStockSelect}
                placeholder="종목 코드 또는 회사명으로 검색..."
                className="w-full"
                enablePageTransition={true}
              />
              {selectedStock && (
                <div className="mt-4 flex items-center justify-center space-x-4">
                  <span className="text-sm text-gray-600">
                    선택된 종목: <strong>{selectedStock.symbol}</strong> - {selectedStock.name}
                  </span>
                  <Button
                    size="sm"
                    color="primary"
                    onPress={() => navigate(`/stocks/${selectedStock.symbol}`)}
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
                <span className="text-purple-800 font-medium">자동 매매</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 sm:px-8 lg:px-12 py-12">
        {/* Quick Actions */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <Card className="w-full shadow-lg hover:shadow-xl transition-shadow duration-300">
            <CardHeader className="pb-4 p-6">
              <h3 className="text-xl font-bold text-foreground">전략 빌더</h3>
            </CardHeader>
            <CardBody className="pt-0 space-y-6 px-6 pb-6">
              <p className="text-default-500 leading-relaxed">매수/매도 조건을 설정하고 자동 매매 전략을 만드세요</p>
              <button
                onClick={() => navigate('/strategy')}
                className="bg-blue-500 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-600 transition-all duration-200 transform hover:scale-105"
              >
                전략 만들기 →
              </button>
            </CardBody>
          </Card>

          <Card className="w-full shadow-lg hover:shadow-xl transition-shadow duration-300">
            <CardHeader className="pb-4 p-6">
              <h3 className="text-xl font-bold text-foreground">전략 목록</h3>
            </CardHeader>
            <CardBody className="pt-0 space-y-6 px-6 pb-6">
              <p className="text-default-500 leading-relaxed">저장된 전략을 관리하고 활성화/비활성화하세요</p>
              <button
                onClick={() => navigate('/strategies')}
                className="bg-green-500 text-white px-6 py-3 rounded-lg font-medium hover:bg-green-600 transition-all duration-200 transform hover:scale-105"
              >
                전략 관리 →
              </button>
            </CardBody>
          </Card>

          <Card className="w-full shadow-lg hover:shadow-xl transition-shadow duration-300">
            <CardHeader className="pb-4 p-6">
              <h3 className="text-xl font-bold text-foreground">실행 로그</h3>
            </CardHeader>
            <CardBody className="pt-0 space-y-6 px-6 pb-6">
              <p className="text-default-500 leading-relaxed">주문 체결 내역과 엔진 실행 로그를 확인하세요</p>
              <button
                onClick={() => navigate('/logs')}
                className="bg-purple-500 text-white px-6 py-3 rounded-lg font-medium hover:bg-purple-600 transition-all duration-200 transform hover:scale-105"
              >
                로그 보기 →
              </button>
            </CardBody>
          </Card>
        </div>
      </div>
    </div>
  )
}

export default Dashboard
