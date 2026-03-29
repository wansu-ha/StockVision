/** AI 대화 패널 — 전략 빌더 코파일럿 + 기본 비서 */
import { useState, useRef, useEffect } from 'react'
import { useAIChat } from '../../hooks/useAIChat'
import ChatMessage from './ChatMessage'
import StatusIndicator from './StatusIndicator'
import CreditBar from './CreditBar'

interface Props {
  currentDsl?: string | null
  onApplyDsl?: (script: string) => void
}

export default function AIChatPanel({ currentDsl, onApplyDsl }: Props) {
  const [mode, setMode] = useState<'builder' | 'assistant'>('builder')
  const [input, setInput] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const chat = useAIChat(mode)

  // 자동 스크롤
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chat.messages])

  const handleSend = async () => {
    if (!input.trim() || chat.streaming) return
    const msg = input.trim()
    setInput('')
    await chat.send(msg, currentDsl)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex flex-col h-full bg-gray-900 border border-gray-800 rounded-xl">
      {/* 헤더: 모드 전환 */}
      <div className="flex items-center gap-2 p-3 border-b border-gray-800">
        <div className="flex rounded-lg overflow-hidden border border-gray-700 text-xs">
          <button
            type="button"
            onClick={() => setMode('builder')}
            className={`px-3 py-1 transition-colors ${mode === 'builder' ? 'bg-indigo-600 text-white' : 'bg-gray-800 text-gray-400'}`}
          >
            전략 빌더
          </button>
          <button
            type="button"
            onClick={() => setMode('assistant')}
            className={`px-3 py-1 transition-colors ${mode === 'assistant' ? 'bg-indigo-600 text-white' : 'bg-gray-800 text-gray-400'}`}
          >
            도움말
          </button>
        </div>
        <span className="text-xs text-gray-500 ml-auto">
          {mode === 'builder' ? 'Sonnet' : 'Haiku'}
        </span>
      </div>

      {/* 메시지 영역 */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3 min-h-0">
        {chat.messages.length === 0 && (
          <div className="text-center text-gray-500 text-sm py-8">
            {mode === 'builder'
              ? '전략을 자연어로 설명해보세요\n예: "골든크로스 매수, 3% 손절 전략 만들어줘"'
              : '무엇이든 물어보세요\n예: "RSI가 뭐예요?"'}
          </div>
        )}
        {chat.messages.map((msg, i) => (
          <ChatMessage
            key={i}
            role={msg.role}
            content={msg.content}
            thinking={msg.thinking}
            dsl={msg.dsl}
            onApplyDsl={onApplyDsl}
          />
        ))}
        {chat.streaming && <StatusIndicator status={chat.status} />}
        <div ref={messagesEndRef} />
      </div>

      {/* 크레딧 바 */}
      <CreditBar />

      {/* 입력 */}
      <div className="p-3 border-t border-gray-800">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={chat.streaming}
            placeholder={mode === 'builder' ? '전략 요청...' : '질문...'}
            className="flex-1 bg-gray-800 text-gray-100 text-sm px-3 py-2 rounded-lg border border-gray-700 focus:border-indigo-500 focus:outline-none resize-none"
            rows={1}
          />
          <button
            type="button"
            onClick={handleSend}
            disabled={chat.streaming || !input.trim()}
            className="bg-indigo-600 text-white px-3 py-2 rounded-lg hover:bg-indigo-700 disabled:opacity-50 text-sm"
          >
            전송
          </button>
        </div>
      </div>
    </div>
  )
}
