import { useQuery } from '@tanstack/react-query'
import client from '../services/localClient'
import type { ConditionStatus } from '../types/condition-status'

export function useConditionStatus(ruleId: number | null) {
  return useQuery<ConditionStatus | null>({
    queryKey: ['condition-status', ruleId],
    queryFn: async () => {
      if (!ruleId) return null
      const res = await client.get(`/conditions/status/${ruleId}`)
      return res.data?.data ?? null
    },
    refetchInterval: 3000,
    enabled: !!ruleId,
  })
}

export function useAllConditionStatus() {
  return useQuery<Record<number, ConditionStatus>>({
    queryKey: ['condition-status-all'],
    queryFn: async () => {
      const res = await client.get('/conditions/status')
      return res.data?.data ?? {}
    },
    refetchInterval: 3000,
  })
}
