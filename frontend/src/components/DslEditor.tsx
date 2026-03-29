/** DSL 텍스트 에디터 — 문법 오류 실시간 표시 + 자동완성 (v2 파서 기반) */
import { useState, useEffect, useRef, useCallback } from 'react'
import { parseDslV2, type DslParseError } from '../utils/dslParserV2'
import { useDslSchema } from '../hooks/useDslSchema'

interface DslEditorProps {
  value: string
  onChange: (value: string) => void
  /** 외부에서 오류를 주입할 경우 내부 파싱을 건너뜀 */
  errors?: DslParseError[]
}

interface Suggestion {
  label: string
  detail: string
  insert: string
}

export default function DslEditor({ value, onChange, errors: externalErrors }: DslEditorProps) {
  const [internalErrors, setInternalErrors] = useState<DslParseError[]>([])
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  const [selectedIdx, setSelectedIdx] = useState(0)
  const [cursorToken, setCursorToken] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const displayErrors = externalErrors ?? internalErrors
  const { data: schema } = useDslSchema()

  // 디바운스 검증 (300ms)
  useEffect(() => {
    if (externalErrors) return
    const timer = setTimeout(() => {
      const result = parseDslV2(value)
      setInternalErrors(result.errors)
    }, 300)
    return () => clearTimeout(timer)
  }, [value, externalErrors])

  // 커서 위치에서 현재 토큰 추출
  const extractToken = useCallback((text: string, pos: number): string => {
    let start = pos
    while (start > 0 && /[\w가-힣_]/.test(text[start - 1])) start--
    return text.slice(start, pos)
  }, [])

  // 자동완성 후보 계산
  const updateSuggestions = useCallback((token: string) => {
    if (!schema || token.length < 2) {
      setSuggestions([])
      return
    }
    const lower = token.toLowerCase()
    const items: Suggestion[] = []

    // 필드
    for (const f of schema.fields) {
      if (f.toLowerCase().startsWith(lower) || f.startsWith(token)) {
        items.push({ label: f, detail: '필드', insert: f })
      }
    }
    // 함수
    for (const [name, spec] of Object.entries(schema.functions)) {
      if (name.toLowerCase().startsWith(lower) || name.startsWith(token)) {
        const args = spec.min_args === spec.max_args
          ? `인자 ${spec.min_args}개`
          : `인자 ${spec.min_args}~${spec.max_args}개`
        items.push({
          label: name,
          detail: `함수 (${args}) → ${spec.return_type}`,
          insert: `${name}(`,
        })
      }
    }
    // 패턴
    for (const [name, spec] of Object.entries(schema.patterns)) {
      if (name.toLowerCase().startsWith(lower) || name.startsWith(token)) {
        items.push({ label: name, detail: `패턴: ${spec.definition}`, insert: name })
      }
    }

    setSuggestions(items.slice(0, 8))
    setSelectedIdx(0)
  }, [schema])

  // 텍스트 변경 시 자동완성 트리거 (디바운스 150ms)
  const autocompleteTimer = useRef<ReturnType<typeof setTimeout>>()
  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newValue = e.target.value
    onChange(newValue)
    clearTimeout(autocompleteTimer.current)
    autocompleteTimer.current = setTimeout(() => {
      const pos = e.target.selectionStart ?? 0
      const token = extractToken(newValue, pos)
      setCursorToken(token)
      updateSuggestions(token)
    }, 150)
  }

  // 자동완성 선택 적용
  const applySuggestion = (suggestion: Suggestion) => {
    const ta = textareaRef.current
    if (!ta) return
    const pos = ta.selectionStart ?? 0
    const tokenStart = pos - cursorToken.length
    const before = value.slice(0, tokenStart)
    const after = value.slice(pos)
    const newValue = before + suggestion.insert + after
    onChange(newValue)
    setSuggestions([])
    // 커서 위치 복원
    const newPos = tokenStart + suggestion.insert.length
    requestAnimationFrame(() => {
      ta.focus()
      ta.setSelectionRange(newPos, newPos)
    })
  }

  // 키보드 네비게이션
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (suggestions.length === 0) return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setSelectedIdx(i => Math.min(i + 1, suggestions.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setSelectedIdx(i => Math.max(i - 1, 0))
    } else if (e.key === 'Tab' || e.key === 'Enter') {
      if (suggestions.length > 0) {
        e.preventDefault()
        applySuggestion(suggestions[selectedIdx])
      }
    } else if (e.key === 'Escape') {
      setSuggestions([])
    }
  }

  return (
    <div className="relative space-y-2">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        onBlur={() => setTimeout(() => setSuggestions([]), 150)}
        className="w-full h-32 bg-gray-800 text-gray-100 font-mono text-sm p-3 rounded-lg border border-gray-600 focus:border-blue-500 focus:outline-none resize-y"
        placeholder={"RSI(14) < 30 AND 보유수량 == 0 → 매수 100%\n수익률 >= 5 → 매도 전량"}
        spellCheck={false}
      />

      {/* 자동완성 드롭다운 */}
      {suggestions.length > 0 && (
        <div className="absolute z-50 left-3 mt-0 w-72 bg-gray-900 border border-gray-600 rounded-lg shadow-xl overflow-hidden">
          {suggestions.map((s, i) => (
            <button
              key={s.label}
              type="button"
              onMouseDown={e => { e.preventDefault(); applySuggestion(s) }}
              className={`w-full text-left px-3 py-1.5 text-sm flex justify-between items-center
                ${i === selectedIdx ? 'bg-indigo-600 text-white' : 'text-gray-300 hover:bg-gray-800'}`}
            >
              <span className="font-mono">{s.label}</span>
              <span className="text-xs opacity-60 ml-2 truncate">{s.detail}</span>
            </button>
          ))}
        </div>
      )}

      {displayErrors.length > 0 && (
        <div className="space-y-1">
          {displayErrors.map((err, i) => (
            <p key={i} className="text-xs text-red-400">
              {err.line}줄 {err.column}열: {err.message}
            </p>
          ))}
        </div>
      )}
    </div>
  )
}
