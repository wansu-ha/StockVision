/**
 * v2 DSL 파서 (프론트엔드용 — 간이 파싱)
 *
 * 전체 AST 파싱이 아닌, 카드 UI에 필요한 정보만 추출:
 * - 상수 선언 목록 (이름, 값)
 * - 커스텀 함수 선언 목록 (이름, 우변 원문)
 * - 규칙 목록 (조건 텍스트, 행동 텍스트)
 * - 파싱 오류 목록
 */

export interface DslConstant {
  name: string
  value: string | number
  type: 'number' | 'string'
}

export interface DslCustomFunction {
  name: string
  body: string  // 우변 원문
}

export interface DslParseError {
  line: number
  column: number
  message: string
}

export interface DslRule {
  condition: string
  action: string
  side: '매수' | '매도'
  quantity: string  // "100%", "50%", "전량", "나머지"
}

export interface DslParseResult {
  constants: DslConstant[]
  customFunctions: DslCustomFunction[]
  rules: DslRule[]
  errors: DslParseError[]
  isV2: boolean
}

export function parseDslV2(script: string, _schema?: unknown): DslParseResult {
  const lines = script.split('\n')
    .map(l => l.replace(/--.*$/, '').trim())  // 주석 제거

  const constants: DslConstant[] = []
  const customFunctions: DslCustomFunction[] = []
  const rules: DslRule[] = []
  const errors: DslParseError[] = []
  const isV2 = script.includes('→') || script.includes('->')

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    if (line.length === 0) continue

    // 상수/커스텀함수: 이름 = 값 (화살표 없는 = 만)
    const constMatch = line.match(/^(\S+)\s*=\s*(.+)$/)
    if (constMatch && !line.includes('→') && !line.includes('->')) {
      const [, name, rawValue] = constMatch
      const trimmed = rawValue.trim()
      if (trimmed.startsWith('"') && trimmed.endsWith('"')) {
        constants.push({ name, value: trimmed.slice(1, -1), type: 'string' })
      } else {
        const num = parseFloat(trimmed)
        if (!isNaN(num)) {
          constants.push({ name, value: num, type: 'number' })
        } else {
          customFunctions.push({ name, body: trimmed })
        }
      }
      continue
    }

    // 규칙: 조건 → 행동
    const arrowIdx = line.includes('→') ? line.indexOf('→') : line.indexOf('->')
    if (arrowIdx !== -1) {
      const arrowLen = line[arrowIdx] === '→' ? 1 : 2
      const condition = line.slice(0, arrowIdx).trim()
      const actionStr = line.slice(arrowIdx + arrowLen).trim()
      const side = actionStr.startsWith('매수') ? '매수' : '매도'
      const quantity = actionStr.replace(/^매[수도]\s*/, '').trim()
      rules.push({ condition, action: actionStr, side, quantity })
      continue
    }

    // 인식 불가 줄
    errors.push({ line: i + 1, column: 0, message: `인식할 수 없는 구문: ${line}` })
  }

  return { constants, customFunctions, rules, errors, isV2 }
}

export function serializeDslV2(constants: DslConstant[], rules: DslRule[]): string {
  const lines: string[] = []

  for (const c of constants) {
    if (c.type === 'string') {
      lines.push(`${c.name} = "${c.value}"`)
    } else {
      lines.push(`${c.name} = ${c.value}`)
    }
  }

  if (constants.length > 0) lines.push('')

  for (const r of rules) {
    lines.push(`${r.condition} → ${r.action}`)
  }

  return lines.join('\n')
}
