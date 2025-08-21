import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import type { StockPrice } from '../types';

interface StockChartProps {
  prices: StockPrice[];
  symbol: string;
}

const StockChart: React.FC<StockChartProps> = ({ prices, symbol }) => {
  if (!prices || prices.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 bg-gray-50 rounded-lg">
        <p className="text-gray-500">차트 데이터가 없습니다.</p>
      </div>
    );
  }

  // 차트 데이터 포맷팅
  const chartData = prices.map(price => ({
    date: new Date(price.date).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' }),
    종가: price.close,
    시가: price.open,
    고가: price.high,
    저가: price.low,
    거래량: price.volume
  }));

  return (
    <div className="w-full h-96 bg-white rounded-lg shadow-sm border p-4">
      <h3 className="text-lg font-semibold text-gray-800 mb-4">
        {symbol} 가격 차트
      </h3>
      

      
      <ResponsiveContainer width="100%" height={400}>
        <LineChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis 
            dataKey="date" 
            stroke="#666"
            fontSize={12}
          />
          <YAxis 
            stroke="#666"
            fontSize={12}
            domain={['dataMin - 5', 'dataMax + 5']}
            tickFormatter={(value) => `$${value}`}
          />
          <Tooltip 
            contentStyle={{
              backgroundColor: 'white',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
              boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
            }}
            formatter={(value: number, name: string) => [
              `$${value.toFixed(2)}`, 
              name
            ]}
            labelFormatter={(label) => `날짜: ${label}`}
          />
          <Legend />
          
          {/* 종가 라인 */}
          <Line 
            type="monotone" 
            dataKey="종가" 
            stroke="#3b82f6" 
            strokeWidth={2}
            dot={{ fill: '#3b82f6', strokeWidth: 2, r: 4 }}
            activeDot={{ r: 6, stroke: '#3b82f6', strokeWidth: 2 }}
          />
          
          {/* 시가 라인 */}
          <Line 
            type="monotone" 
            dataKey="시가" 
            stroke="#10b981" 
            strokeWidth={1.5}
            strokeDasharray="3 3"
            dot={{ fill: '#10b981', r: 3 }}
          />
          
          {/* 고가 라인 */}
          <Line 
            type="monotone" 
            dataKey="고가" 
            stroke="#f59e0b" 
            strokeWidth={1.5}
            strokeDasharray="3 3"
            dot={{ fill: '#f59e0b', r: 3 }}
          />
          
          {/* 저가 라인 */}
          <Line 
            type="monotone" 
            dataKey="저가" 
            stroke="#ef4444" 
            strokeWidth={1.5}
            strokeDasharray="3 3"
            dot={{ fill: '#ef4444', r: 3 }}
          />
        </LineChart>
      </ResponsiveContainer>
      
      <div className="mt-4 text-sm text-gray-600 text-center">
        <span className="inline-block w-3 h-3 bg-blue-500 rounded-full mr-2"></span>
        <span className="mr-4">종가</span>
        <span className="inline-block w-3 h-3 bg-green-500 rounded-full mr-2"></span>
        <span className="mr-4">시가</span>
        <span className="inline-block w-3 h-3 bg-yellow-500 rounded-full mr-2"></span>
        <span className="mr-4">고가</span>
        <span className="inline-block w-3 h-3 bg-red-500 rounded-full mr-2"></span>
        <span>저가</span>
      </div>
    </div>
  );
};

export default StockChart;
