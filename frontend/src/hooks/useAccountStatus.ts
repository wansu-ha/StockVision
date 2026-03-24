/** useAccountStatus — 로컬 서버 상태 5s 폴링.
 *
 * engine/broker/server 상태를 반환.
 * 계좌 잔고/보유종목은 로컬 서버 API 미구현 → null.
 */
import { useQuery } from '@tanstack/react-query'
import { localStatus } from '../services/localClient'
import { useAuth } from '../context/AuthContext'

export interface BrokerCredentials {
  kiwoom: { app_key: string | null; secret_key: string | null }
  kis: { app_key: string | null; app_secret: string | null }
}

export interface LocalStatusData {
  server: { uptime: number }
  broker: { connected: boolean; has_credentials: boolean; reason?: string; credentials?: BrokerCredentials; is_mock?: boolean }
  strategy_engine: {
    running: boolean
    kill_switch: boolean
    loss_lock: boolean
    trading_enabled: boolean
  }
}

export function useAccountStatus() {
  const { localReady } = useAuth()
  const { data, isLoading, error } = useQuery<LocalStatusData | null>({
    queryKey: ['localStatus'],
    queryFn: () => localStatus.get(),
    refetchInterval: 5_000,
    staleTime: 3_000,
    retry: 1,
    enabled: localReady,
  })

  return {
    engineRunning: data?.strategy_engine?.running ?? false,
    brokerConnected: data?.broker?.connected ?? false,
    killSwitch: data?.strategy_engine?.kill_switch ?? false,
    lossLock: data?.strategy_engine?.loss_lock ?? false,
    tradingEnabled: data?.strategy_engine?.trading_enabled ?? false,
    credentials: data?.broker?.credentials ?? null,
    isMock: data?.broker?.is_mock ?? null,
    isLoading,
    error,
    raw: data,
  }
}
