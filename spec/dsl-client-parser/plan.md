# DSL 클라이언트 파서 — 구현 계획

> 작성일: 2026-03-16 | 상태: 초안 | spec: `spec/dsl-client-parser/spec.md`

## 의존관계

```
D1 (TS 파서)            ─── 독립
D2 (DSL ↔ 폼 변환)     ─── D1 완료 후
D3 (ConditionEditor)    ─── D2 완료 후
D4 (에러 표시)          ─── D1 + D3 완료 후

→ D1 → D2 → D3 → D4 순차
```

## Step 1: TypeScript DSL 파서 (D1)

**파일**: `frontend/src/utils/dslParser.ts` (신규)

### 1.1 토큰 타입

```typescript
type TokenType =
  | 'KEYWORD'    // 매수, 매도
  | 'COLON'      // :
  | 'IDENT'      // rsi_14, macd.signal
  | 'NUMBER'     // 30, 50000.5
  | 'OP'         // >, >=, <, <=, ==, !=
  | 'AND' | 'OR'
  | 'NEWLINE' | 'EOF'

interface Token { type: TokenType; value: string; line: number; col: number }
```

### 1.2 Lexer

```typescript
function tokenize(input: string): Token[] {
  // 줄 단위 처리
  // "매수", "매도" → KEYWORD
  // 숫자 리터럴 (정수, 소수) → NUMBER
  // 식별자 (알파벳, 숫자, _, .) → IDENT
  // 연산자 (>, >=, <, <=, ==, !=) → OP
  // AND, OR → 해당 타입
}
```

### 1.3 Parser

```typescript
interface ParseResult {
  success: boolean
  buy?: ConditionGroup
  sell?: ConditionGroup
  errors: ParseError[]
}

interface ConditionGroup {
  operator: 'AND' | 'OR'
  conditions: ParsedCondition[]
}

interface ParsedCondition {
  field: string
  operator: string
  value: number
}

interface ParseError {
  line: number
  column: number
  message: string
}

function parseDsl(input: string): ParseResult {
  const tokens = tokenize(input)
  // "매수:" 이후 조건들 파싱
  // "매도:" 이후 조건들 파싱
  // 에러 수집 (부분 결과 반환)
}
```

**참고**: `sv_core/parsing/parser.py`의 구조를 참고하되, v1은 단순 조건만 지원.

**검증**:
- [ ] `parseDsl("매수: rsi_14 > 30 AND macd < 0\n매도: price < 50000")` → 올바른 구조
- [ ] 빈 문자열 → `{ success: true, buy: undefined, sell: undefined }`
- [ ] 문법 에러 → `errors` 배열에 위치 정보 포함
- [ ] 부분 파싱: 매수만 있고 매도 없어도 에러 아님

## Step 2: DSL ↔ 폼 변환 (D2)

**파일**: `frontend/src/utils/dslConverter.ts` (신규), `frontend/src/services/rules.ts` (수정)

### 2.1 dslToConditions

```typescript
import { parseDsl } from './dslParser'
import type { Condition } from '../types/rule'

interface ConvertResult {
  success: boolean
  buyConditions: Condition[]
  sellConditions: Condition[]
  operator: 'AND' | 'OR'
  errors: string[]
}

function dslToConditions(script: string): ConvertResult {
  const result = parseDsl(script)
  if (!result.success) {
    return { success: false, ..., errors: result.errors.map(e => e.message) }
  }
  // ParsedCondition → Condition 변환
  // field → type 추론 (rsi_14 → indicator, price → price, volume → volume)
}
```

### 2.2 conditionsToDsl 리팩토링

기존 `rules.ts`의 `conditionsToDsl()`는 유지하되 `dslConverter.ts`에서 import하여 round-trip 테스트 가능하게 구성.

**검증**:
- [ ] round-trip: `conditionsToDsl(dslToConditions(dsl))` ≈ 원본
- [ ] 변환 불가 DSL → `success: false` + 에러 메시지
- [ ] field 타입 추론 정확 (rsi → indicator, price → price)

## Step 3: ConditionEditor 모드 토글 (D3)

**파일**: `frontend/src/components/ConditionEditor.tsx` (수정), `frontend/src/components/DslEditor.tsx` (신규)

### 3.1 DslEditor 컴포넌트

```tsx
interface DslEditorProps {
  value: string
  onChange: (value: string) => void
  errors: ParseError[]
}

function DslEditor({ value, onChange, errors }: DslEditorProps) {
  return (
    <div>
      <textarea
        value={value}
        onChange={e => onChange(e.target.value)}
        className="w-full h-32 bg-gray-800 text-gray-100 font-mono text-sm ..."
        placeholder="매수: rsi_14 > 30 AND macd < 0&#10;매도: price < 50000"
      />
      {errors.map(err => (
        <p key={err.line} className="text-xs text-red-400">
          {err.line}줄: {err.message}
        </p>
      ))}
    </div>
  )
}
```

### 3.2 ConditionEditor에 모드 토글

```tsx
// ConditionEditor.tsx
const [mode, setMode] = useState<'form' | 'script'>('form')
const [dslText, setDslText] = useState('')

// 모드 전환 시 자동 변환
const switchMode = (newMode: 'form' | 'script') => {
  if (newMode === 'script') {
    setDslText(conditionsToDsl(conditions))
  } else {
    const result = dslToConditions(dslText)
    if (result.success) {
      onChange(result.buyConditions)  // 또는 적절한 콜백
    }
  }
  setMode(newMode)
}
```

**검증**:
- [ ] 폼 → 스크립트 전환 시 DSL 텍스트 생성
- [ ] 스크립트 → 폼 전환 시 조건 복원
- [ ] 변환 불가 시 모드 전환 차단 + 에러 표시

## Step 4: 에러 인라인 표시 (D4)

**파일**: `frontend/src/components/DslEditor.tsx` (수정)

### 4.1 디바운스 파싱

```typescript
const [errors, setErrors] = useState<ParseError[]>([])

useEffect(() => {
  const timer = setTimeout(() => {
    const result = parseDsl(value)
    setErrors(result.errors)
  }, 300)
  return () => clearTimeout(timer)
}, [value])
```

### 4.2 에러 메시지 한국어화

```typescript
const ERROR_MESSAGES: Record<string, string> = {
  'unexpected_token': '예상치 않은 토큰',
  'expected_operator': '연산자가 필요합니다 (>, <, == 등)',
  'expected_value': '값이 필요합니다',
  'unknown_keyword': '알 수 없는 키워드',
}
```

**검증**:
- [ ] 타이핑 중 300ms 디바운스 후 에러 표시
- [ ] 에러 위치 (줄, 열) 정확
- [ ] 에러 메시지 한국어

## 변경 파일 요약

| 파일 | Step | 변경 |
|------|------|------|
| `frontend/src/utils/dslParser.ts` | D1 | **신규** — lexer + parser |
| `frontend/src/utils/dslConverter.ts` | D2 | **신규** — 변환 함수 |
| `frontend/src/services/rules.ts` | D2 | conditionsToDsl 리팩토링 |
| `frontend/src/components/DslEditor.tsx` | D3, D4 | **신규** — 스크립트 편집 |
| `frontend/src/components/ConditionEditor.tsx` | D3 | 모드 토글 |
