/** DSL 텍스트 에디터 — 문법 오류 실시간 표시 (v2 파서 기반) */
import { useState, useEffect } from 'react'
import { parseDslV2, type DslParseError } from '../utils/dslParserV2'

interface DslEditorProps {
  value: string
  onChange: (value: string) => void
  /** 외부에서 오류를 주입할 경우 내부 파싱을 건너뜀 */
  errors?: DslParseError[]
}

export default function DslEditor({ value, onChange, errors: externalErrors }: DslEditorProps) {
  const [internalErrors, setInternalErrors] = useState<DslParseError[]>([])
  const displayErrors = externalErrors ?? internalErrors

  useEffect(() => {
    if (externalErrors) return
    const timer = setTimeout(() => {
      const result = parseDslV2(value)
      setInternalErrors(result.errors)
    }, 300)
    return () => clearTimeout(timer)
  }, [value, externalErrors])

  return (
    <div className="space-y-2">
      <textarea
        value={value}
        onChange={e => onChange(e.target.value)}
        className="w-full h-32 bg-gray-800 text-gray-100 font-mono text-sm p-3 rounded-lg border border-gray-600 focus:border-blue-500 focus:outline-none resize-y"
        placeholder={"RSI(14) < 30 AND 보유수량 == 0 → 매수 100%\n수익률 >= 5 → 매도 전량"}
        spellCheck={false}
      />
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
