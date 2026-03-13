import { useEffect, useRef } from 'react'
import { create } from 'zustand'
import { useToastStore } from '../stores/toastStore'
import { getLocalSecret } from '../services/localClient'

const LOCAL_URL = import.meta.env.VITE_LOCAL_API_URL || 'http://localhost:4020'
const WS_URL = LOCAL_URL.replace(/^http/, 'ws') + '/ws'

// ── 알림 스토어 ──────────────────────────────────────────────

export interface Notification {
  id: number
  message: string
  type: 'info' | 'success' | 'error'
  read: boolean
  ts: string
  // 실시간 경고 전용 필드
  severity?: 'warning' | 'critical'
  alertType?: string
  title?: string
  symbol?: string | null
  action?: { label: string; route: string }
}

interface NotifStore {
  items: Notification[]
  unread: number
  unreadAlerts: number  // severity 있는 미확인 경고 수
  add: (msg: string, type: Notification['type'], extra?: Partial<Notification>) => void
  markAllRead: () => void
}

let _nid = 1

export const useNotifStore = create<NotifStore>((set) => ({
  items:  [],
  unread: 0,
  unreadAlerts: 0,
  add: (msg, type, extra) => {
    const item: Notification = {
      id:      _nid++,
      message: msg,
      type,
      read:    false,
      ts:      new Date().toLocaleTimeString('ko-KR'),
      ...extra,
    }
    set(s => ({
      items:        [item, ...s.items].slice(0, 50),
      unread:       s.unread + 1,
      unreadAlerts: item.severity ? s.unreadAlerts + 1 : s.unreadAlerts,
    }))
  },
  markAllRead: () =>
    set(s => ({ items: s.items.map(n => ({ ...n, read: true })), unread: 0, unreadAlerts: 0 })),
}))

// ── WS 연결 훅 ───────────────────────────────────────────────

export function useLocalBridgeWS() {
  const wsRef   = useRef<WebSocket | null>(null)
  const retries = useRef(0)
  const toast   = useToastStore.getState()
  const notif   = useNotifStore.getState()

  useEffect(() => {
    let timeout: ReturnType<typeof setTimeout>

    function connect() {
      const ws = new WebSocket(WS_URL)
      wsRef.current = ws

      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data)
          handleMessage(msg, toast, notif)
        } catch { /* JSON 파싱 오류 무시 */ }
      }

      ws.onclose = () => {
        if (retries.current < 3) {
          retries.current++
          timeout = setTimeout(connect, 3000 * retries.current)
        }
      }

      ws.onopen = () => {
        // AS-1: 첫 프레임으로 인증 전송 (query param 대체)
        ws.send(JSON.stringify({ type: 'auth', secret: getLocalSecret() }))
        retries.current = 0
      }
    }

    connect()
    return () => {
      clearTimeout(timeout)
      wsRef.current?.close()
    }
  }, [])
}

function handleMessage(
  msg: { type: string; data: Record<string, unknown> },
  toast: ReturnType<typeof useToastStore.getState>,
  notif: ReturnType<typeof useNotifStore.getState>,
) {
  switch (msg.type) {
    case 'execution': {
      const d = msg.data as {
        rule_id: number; symbol: string; side: string;
        status: string; order_id: string; message: string
      }
      const sideText = d.side === 'buy' ? '매수' : '매도'
      if (d.status === 'FILLED') {
        const text = `체결: ${sideText} ${d.symbol} — ${d.message}`
        toast.showToast(text, 'success')
        notif.add(text, 'success')
      } else if (d.status === 'FAILED') {
        const text = `주문 실패: ${sideText} ${d.symbol} — ${d.message}`
        toast.showToast(text, 'error')
        notif.add(text, 'error')
      } else {
        const text = `주문: ${sideText} ${d.symbol} [${d.status}] — ${d.message}`
        toast.showToast(text, 'info')
        notif.add(text, 'info')
      }
      break
    }
    case 'broker_disconnected':
      toast.showToast('증권사 연결이 끊어졌습니다', 'error')
      notif.add('증권사 연결 단절', 'error')
      break
    case 'alert': {
      const d = msg.data as {
        id: string; alert_type: string; severity: string
        symbol?: string | null; title: string; message: string; ts: string
        action?: { label: string; route: string }
      }
      const toastType: Notification['type'] = d.severity === 'critical' ? 'error' : 'info'
      toast.showToast(d.message, toastType, { persistent: d.severity === 'critical' })
      notif.add(d.message, toastType, {
        severity:  d.severity as 'warning' | 'critical',
        alertType: d.alert_type,
        title:     d.title,
        symbol:    d.symbol,
        action:    d.action,
      })
      // 브라우저 Web Notification
      if (typeof Notification !== 'undefined' && Notification.permission === 'granted') {
        new Notification(d.title, { body: d.message, tag: d.id })
      }
      break
    }
  }
}
