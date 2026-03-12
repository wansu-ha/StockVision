/**
 * 원격 WS 연결 — 상태 수신, 명령 전송.
 *
 * 클라우드 /ws/remote에 연결하여 실시간 상태를 수신하고,
 * kill/arm 명령을 전송한다.
 */
import { useState, useEffect, useRef, useCallback } from 'react'
import { decrypt, loadDeviceKey, getStoredDeviceId } from '../utils/e2eCrypto'
import type { RemoteState } from '../types'

const CLOUD_URL = import.meta.env.VITE_CLOUD_API_URL || 'http://localhost:4010'

function getWsUrl(): string {
  return CLOUD_URL.replace('https://', 'wss://').replace('http://', 'ws://') + '/ws/remote'
}

interface UseRemoteControlReturn {
  state: RemoteState | null
  connected: boolean
  sendKill: (mode: 'stop_new' | 'stop_all') => void
  sendArm: () => void
}

export function useRemoteControl(enabled: boolean): UseRemoteControlReturn {
  const [state, setState] = useState<RemoteState | null>(null)
  const [connected, setConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const deviceIdRef = useRef<string | null>(null)
  const keyRef = useRef<string | null>(null)

  useEffect(() => {
    if (!enabled) return

    let cancelled = false

    const connect = async () => {
      // 디바이스 키 로드
      const deviceId = await getStoredDeviceId()
      if (!deviceId) return
      deviceIdRef.current = deviceId
      const key = await loadDeviceKey(deviceId)
      keyRef.current = key

      const jwt = sessionStorage.getItem('sv_jwt')
      if (!jwt) return

      const ws = new WebSocket(getWsUrl())
      wsRef.current = ws

      ws.onopen = () => {
        // 첫 메시지: auth
        ws.send(JSON.stringify({
          type: 'auth',
          payload: { token: jwt, device_id: deviceId },
        }))
        setConnected(true)
      }

      ws.onmessage = async (event) => {
        try {
          const msg = JSON.parse(event.data)
          if (msg.type === 'state') {
            let payload = msg.payload || {}

            // E2E 복호화
            if (msg.encrypted_for && deviceId && key) {
              const encrypted = msg.encrypted_for[deviceId]
              if (encrypted) {
                try {
                  const decrypted = await decrypt(encrypted, key) as Record<string, unknown>
                  payload = { ...payload, ...decrypted }
                } catch {
                  // 복호화 실패 — 평문 데이터만 사용
                }
              }
            }

            setState(payload as RemoteState)
          } else if (msg.type === 'command_ack') {
            // ACK 수신 — 상태는 다음 state 메시지에서 갱신
          } else if (msg.type === 'command_queued') {
            // 오프라인 큐에 저장됨
          }
        } catch {
          // JSON 파싱 실패
        }
      }

      ws.onclose = () => {
        if (!cancelled) {
          setConnected(false)
          // 재연결 (5초 후)
          setTimeout(() => {
            if (!cancelled) connect()
          }, 5000)
        }
      }

      ws.onerror = () => {
        ws.close()
      }
    }

    connect()

    return () => {
      cancelled = true
      wsRef.current?.close()
    }
  }, [enabled])

  const sendCommand = useCallback((action: string, extra: Record<string, unknown> = {}) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'command',
        id: crypto.randomUUID?.() || Date.now().toString(),
        payload: { action, ...extra },
      }))
    }
  }, [])

  const sendKill = useCallback((mode: 'stop_new' | 'stop_all') => {
    sendCommand('kill', { mode })
  }, [sendCommand])

  const sendArm = useCallback(() => {
    sendCommand('arm')
  }, [sendCommand])

  return { state, connected, sendKill, sendArm }
}
