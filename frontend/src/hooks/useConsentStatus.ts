import { useQuery } from '@tanstack/react-query'
import { legalApi } from '../services/cloudClient'

export interface ConsentItem {
  agreed_version: string | null
  agreed_at: string | null
  latest_version: string
  up_to_date: boolean
}

export interface ConsentStatus {
  terms: ConsentItem
  privacy: ConsentItem
  disclaimer: ConsentItem
}

export function useConsentStatus(enabled = true) {
  return useQuery<ConsentStatus>({
    queryKey: ['consentStatus'],
    queryFn: async () => {
      const res = await legalApi.getConsentStatus()
      return res.data
    },
    staleTime: 5 * 60_000,
    enabled,
  })
}
