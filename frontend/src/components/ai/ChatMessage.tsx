/** AI 대화 메시지 — thinking 접기/펴기, DSL 코드 블록 */
import { useState } from 'react'

interface Props {
  role: 'user' | 'assistant'
  content: string
  thinking?: string
  dsl?: { script: string; valid: boolean }
  onApplyDsl?: (script: string) => void
}

export default function ChatMessage({ role, content, thinking, dsl, onApplyDsl }: Props) {
  const [showThinking, setShowThinking] = useState(false)

  if (role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="bg-indigo-600 text-white text-sm px-3 py-2 rounded-lg max-w-[80%]">
          {content}
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-1">
      {thinking && (
        <button
          type="button"
          onClick={() => setShowThinking(!showThinking)}
          className="text-xs text-gray-500 hover:text-gray-400 text-left"
        >
          {showThinking ? '▼' : '▶'} 사고 과정
        </button>
      )}
      {showThinking && thinking && (
        <div className="text-xs text-gray-500 bg-gray-800/50 rounded p-2 border-l-2 border-gray-600 whitespace-pre-wrap">
          {thinking}
        </div>
      )}
      <div className="bg-gray-800 text-gray-200 text-sm px-3 py-2 rounded-lg max-w-[90%]">
        <div className="whitespace-pre-wrap">{content}</div>
        {dsl && (
          <div className="mt-2">
            <div className={`font-mono text-xs p-2 rounded border ${dsl.valid ? 'border-green-700 bg-green-900/20' : 'border-red-700 bg-red-900/20'}`}>
              <pre className="whitespace-pre-wrap">{dsl.script}</pre>
            </div>
            {dsl.valid && onApplyDsl && (
              <button
                type="button"
                onClick={() => onApplyDsl(dsl.script)}
                className="mt-1 text-xs text-indigo-400 hover:text-indigo-300 underline"
              >
                에디터에 적용
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
