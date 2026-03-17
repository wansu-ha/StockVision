/**
 * DSL 파서 — 매매 규칙 DSL 문자열을 구조화된 데이터로 파싱.
 *
 * 지원 문법:
 *   매수: rsi_14 > 30 AND macd < 0
 *   매도: price < 50000
 */

export type TokenType =
  | 'KEYWORD' | 'COLON' | 'IDENT' | 'NUMBER'
  | 'OP' | 'AND' | 'OR' | 'NEWLINE' | 'EOF'

export interface Token {
  type: TokenType
  value: string
  line: number
  col: number
}

export interface ParseError {
  line: number
  column: number
  message: string
}

export interface ParsedCondition {
  field: string
  operator: string
  value: number
}

export interface ConditionGroup {
  operator: 'AND' | 'OR'
  conditions: ParsedCondition[]
}

export interface ParseResult {
  success: boolean
  buy?: ConditionGroup
  sell?: ConditionGroup
  errors: ParseError[]
}

function tokenize(input: string): Token[] {
  const tokens: Token[] = []
  const lines = input.split('\n')

  for (let lineIdx = 0; lineIdx < lines.length; lineIdx++) {
    const line = lines[lineIdx]
    let col = 0

    while (col < line.length) {
      // 공백 스킵
      if (/\s/.test(line[col])) {
        col++
        continue
      }

      // 키워드: 매수, 매도
      if (line.substring(col).startsWith('매수')) {
        tokens.push({ type: 'KEYWORD', value: '매수', line: lineIdx + 1, col: col + 1 })
        col += 2
        continue
      }
      if (line.substring(col).startsWith('매도')) {
        tokens.push({ type: 'KEYWORD', value: '매도', line: lineIdx + 1, col: col + 1 })
        col += 2
        continue
      }

      // 콜론
      if (line[col] === ':') {
        tokens.push({ type: 'COLON', value: ':', line: lineIdx + 1, col: col + 1 })
        col++
        continue
      }

      // 연산자 (>= 를 > 보다 먼저 확인)
      const ops = ['>=', '<=', '!=', '==', '>', '<']
      let matched = false
      for (const op of ops) {
        if (line.substring(col, col + op.length) === op) {
          tokens.push({ type: 'OP', value: op, line: lineIdx + 1, col: col + 1 })
          col += op.length
          matched = true
          break
        }
      }
      if (matched) continue

      // 숫자 (정수, 소수, 음수)
      const numMatch = line.substring(col).match(/^-?\d+(\.\d+)?/)
      if (numMatch) {
        tokens.push({ type: 'NUMBER', value: numMatch[0], line: lineIdx + 1, col: col + 1 })
        col += numMatch[0].length
        continue
      }

      // 식별자 (AND, OR, 또는 필드명)
      const identMatch = line.substring(col).match(/^[a-zA-Z_][a-zA-Z0-9_.]*/)
      if (identMatch) {
        const val = identMatch[0]
        if (val === 'AND') {
          tokens.push({ type: 'AND', value: 'AND', line: lineIdx + 1, col: col + 1 })
        } else if (val === 'OR') {
          tokens.push({ type: 'OR', value: 'OR', line: lineIdx + 1, col: col + 1 })
        } else {
          tokens.push({ type: 'IDENT', value: val, line: lineIdx + 1, col: col + 1 })
        }
        col += val.length
        continue
      }

      // 알 수 없는 문자 — 스킵
      col++
    }

    if (lineIdx < lines.length - 1) {
      tokens.push({ type: 'NEWLINE', value: '\n', line: lineIdx + 1, col: line.length + 1 })
    }
  }

  tokens.push({ type: 'EOF', value: '', line: lines.length, col: 0 })
  return tokens
}

export function parseDsl(input: string): ParseResult {
  if (!input.trim()) {
    return { success: true, errors: [] }
  }

  const tokens = tokenize(input)
  const errors: ParseError[] = []
  let pos = 0
  let buy: ConditionGroup | undefined
  let sell: ConditionGroup | undefined

  function peek(): Token {
    return tokens[pos] || { type: 'EOF', value: '', line: 0, col: 0 }
  }

  function advance(): Token {
    return tokens[pos++]
  }

  function skipNewlines() {
    while (peek().type === 'NEWLINE') advance()
  }

  function parseCondition(): ParsedCondition | undefined {
    const fieldToken = peek()
    if (fieldToken.type !== 'IDENT') {
      if (fieldToken.type !== 'EOF' && fieldToken.type !== 'NEWLINE' && fieldToken.type !== 'KEYWORD') {
        errors.push({
          line: fieldToken.line,
          column: fieldToken.col,
          message: `필드명이 필요합니다 ('${fieldToken.value}' 발견)`,
        })
      }
      return undefined
    }
    advance()

    const opToken = peek()
    if (opToken.type !== 'OP') {
      errors.push({
        line: opToken.line,
        column: opToken.col,
        message: '연산자가 필요합니다 (>, <, ==, >=, <=, !=)',
      })
      return undefined
    }
    advance()

    const valToken = peek()
    if (valToken.type !== 'NUMBER') {
      errors.push({
        line: valToken.line,
        column: valToken.col,
        message: '숫자 값이 필요합니다',
      })
      return undefined
    }
    advance()

    return {
      field: fieldToken.value,
      operator: opToken.value,
      value: parseFloat(valToken.value),
    }
  }

  function parseConditionGroup(): ConditionGroup | undefined {
    const conditions: ParsedCondition[] = []
    let groupOp: 'AND' | 'OR' = 'AND'

    const first = parseCondition()
    if (!first) return undefined
    conditions.push(first)

    while (peek().type === 'AND' || peek().type === 'OR') {
      const opToken = advance()
      groupOp = opToken.value as 'AND' | 'OR'
      const next = parseCondition()
      if (!next) break
      conditions.push(next)
    }

    return { operator: groupOp, conditions }
  }

  // 섹션 파싱
  while (pos < tokens.length && peek().type !== 'EOF') {
    skipNewlines()
    const current = peek()

    if (current.type === 'KEYWORD') {
      const keyword = advance()

      // 콜론 기대
      if (peek().type === 'COLON') {
        advance()
      } else {
        errors.push({
          line: keyword.line,
          column: keyword.col + keyword.value.length,
          message: "':' 가 필요합니다",
        })
      }

      const group = parseConditionGroup()
      if (keyword.value === '매수') {
        buy = group
      } else if (keyword.value === '매도') {
        sell = group
      }
    } else if (current.type === 'EOF') {
      break
    } else {
      errors.push({
        line: current.line,
        column: current.col,
        message: `예상치 않은 토큰: '${current.value}'`,
      })
      advance()
    }
  }

  return {
    success: errors.length === 0,
    buy,
    sell,
    errors,
  }
}
