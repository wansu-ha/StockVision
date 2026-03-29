/** AI 대화 SSE 훅 */
import { useCallback, useRef, useState } from 'react'
import { cloudAI } from '../services/cloudClient'
import type { AIChatRequest, SSEEvent } from '../types/ai'

interface Message {
  role: 'user' | 'assistant'
  content: string
  thinking?: string
  dsl?: { script: string; valid: boolean }
  timestamp: string
}

interface UseAIChatReturn {
  messages: Message[]
  streaming: boolean
  status: string
  send: (message: string, currentDsl?: string | null) => Promise<void>
  conversationId: string | null
  setConversationId: (id: string | null) => void
}

export function useAIChat(mode: 'builder' | 'assistant' = 'builder'): UseAIChatReturn {
  const [messages, setMessages] = useState<Message[]>([])
  const [streaming, setStreaming] = useState(false)
  const [status, setStatus] = useState('')
  const [conversationId, setConversationId] = useState<string | null>(null)
  const thinkingRef = useRef('')
  const responseRef = useRef('')

  const send = useCallback(async (message: string, currentDsl?: string | null) => {
    setStreaming(true)
    setStatus('')
    thinkingRef.current = ''
    responseRef.current = ''

    // 사용자 메시지 추가
    const userMsg: Message = { role: 'user', content: message, timestamp: new Date().toISOString() }
    setMessages(prev => [...prev, userMsg])

    // 어시스턴트 메시지 플레이스홀더
    const assistantMsg: Message = { role: 'assistant', content: '', timestamp: new Date().toISOString() }
    setMessages(prev => [...prev, assistantMsg])

    const params: AIChatRequest = {
      conversation_id: conversationId,
      message,
      current_dsl: currentDsl,
      mode,
      thinking: false,
    }

    try {
      await cloudAI.chatStream(params, (event: SSEEvent) => {
        switch (event.event) {
          case 'status':
            setStatus((event.data as { message: string }).message)
            break
          case 'thinking':
            thinkingRef.current += (event.data as { content: string }).content
            break
          case 'token':
            responseRef.current += (event.data as { content: string }).content
            setMessages(prev => {
              const updated = [...prev]
              const last = updated[updated.length - 1]
              if (last?.role === 'assistant') {
                updated[updated.length - 1] = { ...last, content: responseRef.current, thinking: thinkingRef.current || undefined }
              }
              return updated
            })
            break
          case 'dsl':
            setMessages(prev => {
              const updated = [...prev]
              const last = updated[updated.length - 1]
              if (last?.role === 'assistant') {
                updated[updated.length - 1] = { ...last, dsl: event.data as { script: string; valid: boolean } }
              }
              return updated
            })
            break
          case 'done': {
            const done = event.data as { conversation_id: string }
            setConversationId(done.conversation_id)
            break
          }
          case 'error':
            setStatus((event.data as { message: string }).message)
            break
        }
      })
    } catch {
      setStatus('연결 오류')
    } finally {
      setStreaming(false)
      setStatus('')
    }
  }, [conversationId, mode])

  return { messages, streaming, status, send, conversationId, setConversationId }
}
