import { useQuery } from '@tanstack/react-query'
import cloudClient from '../services/cloudClient'
import type { DslSchema } from '../types/strategy'

export function useDslSchema() {
  return useQuery<DslSchema | null>({
    queryKey: ['dsl-schema'],
    queryFn: async () => {
      const res = await cloudClient.get('/dsl/schema')
      return res.data?.data ?? null
    },
    staleTime: Infinity,
  })
}
