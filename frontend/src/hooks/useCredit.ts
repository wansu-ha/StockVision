/** AI 크레딧 잔량 조회 훅 */
import { useQuery } from '@tanstack/react-query'
import { cloudAI } from '../services/cloudClient'

export function useCredit() {
  return useQuery({
    queryKey: ['ai-credit'],
    queryFn: () => cloudAI.credit(),
    refetchInterval: 60_000, // 1분마다 갱신
  })
}
