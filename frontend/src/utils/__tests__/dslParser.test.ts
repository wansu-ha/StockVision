import { describe, it, expect } from 'vitest'
import { parseDsl } from '../dslParser'

describe('parseDsl', () => {
  // ── 빈 입력 ──

  it('빈 문자열 → success, 에러 없음', () => {
    const r = parseDsl('')
    expect(r.success).toBe(true)
    expect(r.errors).toHaveLength(0)
    expect(r.buy).toBeUndefined()
    expect(r.sell).toBeUndefined()
  })

  it('공백만 → success', () => {
    expect(parseDsl('   \n  ').success).toBe(true)
  })

  // ── 매수 섹션 ──

  it('매수 단일 조건', () => {
    const r = parseDsl('매수: rsi_14 > 30')
    expect(r.success).toBe(true)
    expect(r.buy).toBeDefined()
    expect(r.buy!.conditions).toHaveLength(1)
    expect(r.buy!.conditions[0]).toEqual({ field: 'rsi_14', operator: '>', value: 30 })
  })

  it('매도 단일 조건', () => {
    const r = parseDsl('매도: price < 50000')
    expect(r.success).toBe(true)
    expect(r.sell).toBeDefined()
    expect(r.sell!.conditions[0]).toEqual({ field: 'price', operator: '<', value: 50000 })
  })

  // ── AND/OR ──

  it('AND 조건 2개', () => {
    const r = parseDsl('매수: rsi_14 > 30 AND macd < 0')
    expect(r.success).toBe(true)
    expect(r.buy!.operator).toBe('AND')
    expect(r.buy!.conditions).toHaveLength(2)
    expect(r.buy!.conditions[1].field).toBe('macd')
  })

  it('OR 조건 2개', () => {
    const r = parseDsl('매수: rsi_14 > 70 OR volume > 1000000')
    expect(r.success).toBe(true)
    expect(r.buy!.operator).toBe('OR')
    expect(r.buy!.conditions).toHaveLength(2)
  })

  it('AND 3개 조건', () => {
    const r = parseDsl('매수: a > 1 AND b < 2 AND c >= 3')
    expect(r.success).toBe(true)
    expect(r.buy!.conditions).toHaveLength(3)
  })

  // ── 매수 + 매도 동시 ──

  it('매수 + 매도 모두 파싱', () => {
    const r = parseDsl('매수: rsi_14 <= 30\n매도: rsi_14 >= 70')
    expect(r.success).toBe(true)
    expect(r.buy).toBeDefined()
    expect(r.sell).toBeDefined()
    expect(r.buy!.conditions[0].operator).toBe('<=')
    expect(r.sell!.conditions[0].operator).toBe('>=')
  })

  // ── 연산자 ──

  it.each([
    ['>', '>'],
    ['<', '<'],
    ['>=', '>='],
    ['<=', '<='],
    ['==', '=='],
    ['!=', '!='],
  ])('연산자 %s', (op) => {
    const r = parseDsl(`매수: x ${op} 10`)
    expect(r.success).toBe(true)
    expect(r.buy!.conditions[0].operator).toBe(op)
  })

  // ── 숫자 ──

  it('소수점 숫자', () => {
    const r = parseDsl('매수: ratio > 1.5')
    expect(r.success).toBe(true)
    expect(r.buy!.conditions[0].value).toBe(1.5)
  })

  it('음수', () => {
    const r = parseDsl('매수: change > -5')
    expect(r.success).toBe(true)
    expect(r.buy!.conditions[0].value).toBe(-5)
  })

  it('큰 숫자', () => {
    const r = parseDsl('매수: price > 100000')
    expect(r.success).toBe(true)
    expect(r.buy!.conditions[0].value).toBe(100000)
  })

  // ── 필드명 ──

  it('밑줄 포함 필드명', () => {
    const r = parseDsl('매수: avg_volume_20 > 500000')
    expect(r.success).toBe(true)
    expect(r.buy!.conditions[0].field).toBe('avg_volume_20')
  })

  it('점 포함 필드명', () => {
    const r = parseDsl('매수: indicator.rsi > 30')
    expect(r.success).toBe(true)
    expect(r.buy!.conditions[0].field).toBe('indicator.rsi')
  })

  // ── 에러 케이스 ──

  it('콜론 누락 → 에러', () => {
    const r = parseDsl('매수 rsi_14 > 30')
    expect(r.success).toBe(false)
    expect(r.errors.length).toBeGreaterThan(0)
    expect(r.errors[0].message).toContain(':')
  })

  it('연산자 누락 → 에러', () => {
    const r = parseDsl('매수: rsi_14 30')
    expect(r.success).toBe(false)
    expect(r.errors.some(e => e.message.includes('연산자'))).toBe(true)
  })

  it('값 누락 → 에러', () => {
    const r = parseDsl('매수: rsi_14 >')
    expect(r.success).toBe(false)
    expect(r.errors.some(e => e.message.includes('숫자'))).toBe(true)
  })

  it('알 수 없는 토큰', () => {
    const r = parseDsl('hello: x > 1')
    expect(r.success).toBe(false)
  })

  // ── 라인/컬럼 정보 ──

  it('에러에 라인 정보 포함', () => {
    const r = parseDsl('매수 rsi > 30')
    expect(r.errors[0].line).toBe(1)
    expect(r.errors[0].column).toBeGreaterThan(0)
  })

  // ── 엣지 케이스 ──

  it('빈 줄이 포함된 입력', () => {
    const r = parseDsl('매수: x > 1\n\n매도: y < 2')
    expect(r.success).toBe(true)
    expect(r.buy).toBeDefined()
    expect(r.sell).toBeDefined()
  })

  it('매수만 있고 매도 없음', () => {
    const r = parseDsl('매수: rsi > 30')
    expect(r.success).toBe(true)
    expect(r.buy).toBeDefined()
    expect(r.sell).toBeUndefined()
  })
})
