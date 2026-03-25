import { describe, it, expect } from 'vitest'
import { dslToConditions } from '../dslConverter'

describe('dslToConditions', () => {
  it('빈 문자열 → 빈 배열', () => {
    const r = dslToConditions('')
    expect(r.success).toBe(true)
    expect(r.buyConditions).toHaveLength(0)
    expect(r.sellConditions).toHaveLength(0)
  })

  it('매수 조건 변환', () => {
    const r = dslToConditions('매수: rsi_14 > 30')
    expect(r.success).toBe(true)
    expect(r.buyConditions).toHaveLength(1)
    expect(r.buyConditions[0]).toEqual({
      variable: 'rsi_14',
      operator: '>',
      value: 30,
    })
  })

  it('매수 + 매도 동시 변환', () => {
    const r = dslToConditions('매수: a > 1\n매도: b < 2')
    expect(r.buyConditions).toHaveLength(1)
    expect(r.sellConditions).toHaveLength(1)
    expect(r.buyConditions[0].variable).toBe('a')
    expect(r.sellConditions[0].variable).toBe('b')
  })

  it('AND 연산자 기본값', () => {
    const r = dslToConditions('매수: a > 1 AND b < 2')
    expect(r.operator).toBe('AND')
  })

  it('OR이 있으면 operator=OR', () => {
    const r = dslToConditions('매수: a > 1 OR b < 2')
    expect(r.operator).toBe('OR')
  })

  it('매도에 OR이 있어도 operator=OR', () => {
    const r = dslToConditions('매수: a > 1\n매도: x > 10 OR y < 5')
    expect(r.operator).toBe('OR')
  })

  it('에러 시 부분 복원', () => {
    const r = dslToConditions('매수: rsi > 30\n매도 missing_colon')
    // 매수는 파싱 성공
    expect(r.buyConditions).toHaveLength(1)
    // 에러 있음
    expect(r.errors.length).toBeGreaterThan(0)
  })

  it('field → variable 매핑', () => {
    const r = dslToConditions('매수: avg_volume_20 >= 500000')
    expect(r.buyConditions[0].variable).toBe('avg_volume_20')
    expect(r.buyConditions[0].operator).toBe('>=')
    expect(r.buyConditions[0].value).toBe(500000)
  })
})
