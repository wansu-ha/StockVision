import { useMutation, useQueryClient } from '@tanstack/react-query'
import { cloudWatchlist } from '../services/cloudClient'
import type { WatchlistItem } from '../services/cloudClient'

export function useWatchlistToggle() {
  const qc = useQueryClient()

  return useMutation({
    mutationFn: async ({ symbol, add }: { symbol: string; add: boolean }) => {
      if (add) {
        return cloudWatchlist.add(symbol)
      } else {
        return cloudWatchlist.remove(symbol)
      }
    },
    onMutate: async ({ symbol, add }) => {
      await qc.cancelQueries({ queryKey: ['watchlist'] })

      const prev = qc.getQueryData<WatchlistItem[]>(['watchlist'])

      qc.setQueryData<WatchlistItem[]>(['watchlist'], old => {
        if (!old) return old
        if (add) {
          return [...old, { id: Date.now(), symbol, added_at: new Date().toISOString() }]
        } else {
          return old.filter(item => item.symbol !== symbol)
        }
      })

      return { prev }
    },
    onError: (_err, _vars, context) => {
      if (context?.prev) {
        qc.setQueryData(['watchlist'], context.prev)
      }
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['watchlist'] })
    },
  })
}
