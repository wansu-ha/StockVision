import { describe, it, expect } from 'vitest'
import { parseDslV2, serializeDslV2 } from '../dslParserV2'

describe('parseDslV2', () => {
  it('빈 문자열', () => {
    const r = parseDslV2('')
    expect(r.constants).toHaveLength(0)
    expect(r.rules).toHaveLength(0)
    expect(r.isV2).toBe(false)
  })

  it('상수 파싱', () => {
    const r = parseDslV2('기간 = 14\n손절 = -2\nRSI(기간) < 30 → 매수 100%')
    expect(r.constants).toHaveLength(2)
    expect(r.constants[0]).toEqual({ name: '기간', value: 14, type: 'number' })
    expect(r.constants[1]).toEqual({ name: '손절', value: -2, type: 'number' })
  })

  it('문자열 상수', () => {
    const r = parseDslV2('tf = "1d"\nRSI(14) < 30 → 매수 100%')
    expect(r.constants[0]).toEqual({ name: 'tf', value: '1d', type: 'string' })
  })

  it('규칙 파싱 — 매수', () => {
    const r = parseDslV2('RSI(14) < 30 → 매수 100%')
    expect(r.rules).toHaveLength(1)
    expect(r.rules[0].side).toBe('매수')
    expect(r.rules[0].quantity).toBe('100%')
    expect(r.isV2).toBe(true)
  })

  it('규칙 파싱 — 매도 전량', () => {
    const r = parseDslV2('수익률 <= -2 → 매도 전량')
    expect(r.rules[0].side).toBe('매도')
    expect(r.rules[0].quantity).toBe('전량')
  })

  it('규칙 파싱 — 매도 50%', () => {
    const r = parseDslV2('수익률 >= 3 → 매도 50%')
    expect(r.rules[0].quantity).toBe('50%')
  })

  it('ASCII 화살표', () => {
    const r = parseDslV2('RSI(14) < 30 -> 매수 100%')
    expect(r.rules).toHaveLength(1)
    expect(r.isV2).toBe(true)
  })

  it('주석 무시', () => {
    const r = parseDslV2('-- 주석\nRSI(14) < 30 → 매수 100%')
    expect(r.rules).toHaveLength(1)
  })

  it('여러 규칙', () => {
    const r = parseDslV2('수익률 <= -2 → 매도 전량\nRSI(14) < 30 → 매수 50%\n수익률 >= 5 → 매도 전량')
    expect(r.rules).toHaveLength(3)
  })

  it('종합 예시', () => {
    const script = `기간 = 14
손절 = -2

-- 규칙
MA(20) <= MA(60) AND 보유수량 > 0 → 매도 전량
RSI(기간) < 30 AND 골든크로스 AND 보유수량 == 0 → 매수 100%
수익률 <= 손절 → 매도 전량`
    const r = parseDslV2(script)
    expect(r.constants).toHaveLength(2)
    expect(r.rules).toHaveLength(3)
  })
})

describe('customFunctions', () => {
  it('과매도 = RSI(14) <= 30 → customFunctions에 포함', () => {
    const r = parseDslV2('과매도 = RSI(14) <= 30')
    expect(r.customFunctions).toHaveLength(1)
    expect(r.customFunctions[0]).toEqual({ name: '과매도', body: 'RSI(14) <= 30' })
    expect(r.constants).toHaveLength(0)
  })

  it('과매도() = RSI(14) <= 30 → customFunctions에 포함', () => {
    const r = parseDslV2('과매도() = RSI(14) <= 30')
    expect(r.customFunctions).toHaveLength(1)
    expect(r.customFunctions[0]).toEqual({ name: '과매도()', body: 'RSI(14) <= 30' })
  })

  it('음수 상수 손절 = -3 → 상수로 남음 (parseFloat 성공)', () => {
    const r = parseDslV2('손절 = -3')
    expect(r.constants).toHaveLength(1)
    expect(r.constants[0]).toEqual({ name: '손절', value: -3, type: 'number' })
    expect(r.customFunctions).toHaveLength(0)
  })
})

describe('errors', () => {
  it('인식 못 하는 줄 → errors에 포함', () => {
    const r = parseDslV2('이상한줄입니다')
    expect(r.errors).toHaveLength(1)
    expect(r.errors[0].line).toBe(1)
    expect(r.errors[0].message).toContain('이상한줄입니다')
  })

  it('정상 파싱 시 errors 빈 배열', () => {
    const r = parseDslV2('기간 = 14\nRSI(기간) < 30 → 매수 100%')
    expect(r.errors).toHaveLength(0)
  })
})

describe('serializeDslV2', () => {
  it('상수 + 규칙 직렬화', () => {
    const result = serializeDslV2(
      [{ name: '기간', value: 14, type: 'number' }],
      [{ condition: 'RSI(기간) < 30', action: '매수 100%', side: '매수', quantity: '100%' }],
    )
    expect(result).toContain('기간 = 14')
    expect(result).toContain('RSI(기간) < 30 → 매수 100%')
  })
})
