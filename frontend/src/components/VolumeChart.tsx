import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import type { StockPrice } from '../types';

interface VolumeChartProps {
  prices: StockPrice[];
  symbol: string;
}

const VolumeChart: React.FC<VolumeChartProps> = ({ prices, symbol }) => {
  if (!prices || prices.length === 0) {
    return null;
  }

  // 거래량 데이터 포맷팅
  const volumeData = prices.map(price => ({
    date: new Date(price.date).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' }),
    거래량: price.volume
  }));

  return (
    <div className="w-full h-48 bg-white rounded-lg shadow-sm border p-4 mt-4">
      <h4 className="text-md font-medium text-gray-700 mb-3">
        {symbol} 거래량
      </h4>
      

      
      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={volumeData} margin={{ top: 10, right: 20, left: 20, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis 
            dataKey="date" 
            stroke="#666"
            fontSize={11}
          />
          <YAxis 
            stroke="#666"
            fontSize={11}
            tickFormatter={(value: number) => value >= 1000000 ? `${(value / 10000).toFixed(0)}만` : value.toLocaleString('ko-KR')}
          />
          <Tooltip 
            contentStyle={{
              backgroundColor: 'white',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
              boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
            }}
            formatter={(value: number) => [
              `${value.toLocaleString()}`, 
              '거래량'
            ]}
            labelFormatter={(label: string) => `날짜: ${label}`}
          />
          
          <Bar 
            dataKey="거래량" 
            fill="#8b5cf6" 
            radius={[2, 2, 0, 0]}
            opacity={0.8}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
};

export default VolumeChart;
