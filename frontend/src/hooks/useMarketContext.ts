/** useMarketContext — 시장 컨텍스트 30s 폴링. */
import { useQuery } from '@tanstack/react-query'
import { cloudContext } from '../services/cloudClient'
import type { MarketContextData } from '../types/dashboard'

export function useMarketContext() {
  const { data, isLoading, error } = useQuery<MarketContextData | null>({
    queryKey: ['marketContext'],
    queryFn: () => cloudContext.get(),
    refetchInterval: 30_000,
    staleTime: 15_000,
    retry: 1,
  })

  return { context: data ?? null, isLoading, error }
}
