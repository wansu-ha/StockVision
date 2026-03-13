/** 토스트 알림 상태 관리 (Zustand) */
import { create } from 'zustand'
import type { AlertItem, AlertType } from '../types/ui'

let _id = 0

interface AlertStore {
  alerts: AlertItem[]
  add: (message: string, type?: AlertType) => void
  remove: (id: number) => void
  clear: () => void
}

export const useAlertStore = create<AlertStore>((set) => ({
  alerts: [],
  add: (message, type = 'info') => {
    const item: AlertItem = { id: ++_id, type, message, timestamp: Date.now() }
    set((s) => ({ alerts: [...s.alerts, item].slice(-10) }))
    // 5초 후 자동 삭제
    setTimeout(() => {
      set((s) => ({ alerts: s.alerts.filter((a) => a.id !== item.id) }))
    }, 5000)
  },
  remove: (id) => set((s) => ({ alerts: s.alerts.filter((a) => a.id !== id) })),
  clear: () => set({ alerts: [] }),
}))
