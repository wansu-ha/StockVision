/** 실시간 시세 테이블 */
import type { PriceQuote } from '../types/dashboard'

interface Props {
  quotes: PriceQuote[]
}

export default function PriceTable({ quotes }: Props) {
  if (quotes.length === 0) {
    return (
      <div className="text-center text-gray-400 py-8">
        시세 데이터를 수신 중입니다...
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 text-gray-500">
            <th className="text-left py-2 px-3 font-medium">종목</th>
            <th className="text-right py-2 px-3 font-medium">현재가</th>
            <th className="text-right py-2 px-3 font-medium">변동률</th>
            <th className="text-right py-2 px-3 font-medium">거래량</th>
          </tr>
        </thead>
        <tbody>
          {quotes.map((q) => (
            <tr key={q.symbol} className="border-b border-gray-50 hover:bg-gray-50">
              <td className="py-2 px-3">
                <div className="font-medium text-gray-900">{q.name}</div>
                <div className="text-xs text-gray-400">{q.symbol}</div>
              </td>
              <td className="text-right py-2 px-3 font-mono">
                {q.price.toLocaleString()}
              </td>
              <td className={`text-right py-2 px-3 font-mono ${q.changePercent > 0 ? 'text-red-500' : q.changePercent < 0 ? 'text-blue-500' : 'text-gray-500'}`}>
                {q.changePercent > 0 ? '+' : ''}{q.changePercent.toFixed(2)}%
              </td>
              <td className="text-right py-2 px-3 font-mono text-gray-500">
                {q.volume.toLocaleString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
