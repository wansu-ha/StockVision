import { create } from 'zustand'

export type ToastType = 'success' | 'error' | 'info'

interface ToastOptions {
  /** true이면 자동으로 닫히지 않음 (critical 경고용) */
  persistent?: boolean
}

interface Toast {
  id: number
  message: string
  type: ToastType
  persistent?: boolean
}

interface ToastStore {
  toasts: Toast[]
  showToast: (message: string, type?: ToastType, options?: ToastOptions) => void
  removeToast: (id: number) => void
}

let nextId = 1

export const useToastStore = create<ToastStore>((set) => ({
  toasts: [],
  showToast: (message, type = 'info', options) => {
    const id = nextId++
    set((state) => ({ toasts: [...state.toasts, { id, message, type, persistent: options?.persistent }] }))
    if (!options?.persistent) {
      setTimeout(() => {
        set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) }))
      }, 4000)
    }
  },
  removeToast: (id) => {
    set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) }))
  },
}))
