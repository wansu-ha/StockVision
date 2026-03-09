/** useAccountBalance — 브로커 잔고/보유종목 + 미체결 주문 폴링.
 *
 * 브로커 연결 상태일 때만 활성화 (enabled).
 */
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '../context/AuthContext'
import { localAccount } from '../services/localClient'
import type { AccountBalance, OpenOrder } from '../services/localClient'

export function useAccountBalance(brokerConnected: boolean) {
  const { localReady } = useAuth()

  const balanceQuery = useQuery<AccountBalance | null>({
    queryKey: ['accountBalance'],
    queryFn: () => localAccount.balance(),
    refetchInterval: 30_000,
    enabled: localReady && brokerConnected,
    retry: 1,
  })

  const ordersQuery = useQuery<OpenOrder[]>({
    queryKey: ['openOrders'],
    queryFn: () => localAccount.orders(),
    refetchInterval: 15_000,
    enabled: localReady && brokerConnected,
    retry: 1,
  })

  return {
    balance: balanceQuery.data ?? null,
    openOrders: ordersQuery.data ?? [],
    isLoading: balanceQuery.isLoading || ordersQuery.isLoading,
  }
}
