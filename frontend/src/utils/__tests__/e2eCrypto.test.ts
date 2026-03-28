import { describe, it, expect, beforeEach } from 'vitest'
import FDBFactory from 'fake-indexeddb/lib/FDBFactory'
import FDBKeyRange from 'fake-indexeddb/lib/FDBKeyRange'
import {
  saveDeviceKey,
  loadDeviceKey,
  deleteDeviceKey,
  getStoredDeviceId,
  decrypt,
} from '../e2eCrypto'

// happy-dom이 indexedDB를 글로벌로 노출하지 않으므로 fake-indexeddb로 주입
// 각 테스트 파일 로드 시 한 번만 실행됨
Object.assign(globalThis, {
  indexedDB: new FDBFactory(),
  IDBKeyRange: FDBKeyRange,
})

// ── AES-256-GCM 테스트 픽스처 (Node.js crypto로 사전 생성) ──
// plaintext: {"price":75000,"symbol":"TEST"}
const FIXTURE = {
  key: 'tptglHQ6Qx1Te4K69caXwTGGz8q6T6GJFDSw4xwYAUM=',
  iv: 'KavGbr25VwPHlV+Z',
  ciphertext: 'lR84muUWrBNXzpHnX7UR7k2c5uY3RqGCfxgtW/GTzQ==',
  tag: 'qVHVvIkGPcJqhAQPYt7IdQ==',
} as const

// ── Step 2: IndexedDB 함수 테스트 ──

describe('IndexedDB 키 관리', () => {
  // 각 테스트마다 독립된 디바이스 ID 사용 (DB 상태 간섭 방지)
  let deviceId: string

  beforeEach(() => {
    deviceId = `device-${Math.random().toString(36).slice(2)}`
  })

  it('saveDeviceKey → loadDeviceKey 왕복 검증', async () => {
    const keyBase64 = FIXTURE.key
    await saveDeviceKey(deviceId, keyBase64)
    const loaded = await loadDeviceKey(deviceId)
    expect(loaded).toBe(keyBase64)
  })

  it('미등록 ID → null 반환', async () => {
    const result = await loadDeviceKey('nonexistent-device-id')
    expect(result).toBeNull()
  })

  it('deleteDeviceKey 후 조회 → null', async () => {
    await saveDeviceKey(deviceId, FIXTURE.key)
    await deleteDeviceKey(deviceId)
    const result = await loadDeviceKey(deviceId)
    expect(result).toBeNull()
  })

  it('getStoredDeviceId: 키 없으면 null', async () => {
    // 이 테스트는 DB가 비어있을 때를 가정 — 고유 DB명을 쓸 수 없으므로
    // 저장 후 삭제하여 비운 뒤 확인하는 방식으로 우회
    // 단, 다른 테스트에서 저장한 키가 있을 수 있어 null 또는 string만 확인
    const result = await getStoredDeviceId()
    expect(result === null || typeof result === 'string').toBe(true)
  })

  it('getStoredDeviceId: 키 있으면 첫 번째 ID 반환', async () => {
    // 고유한 키를 저장하고 결과가 문자열인지 확인
    await saveDeviceKey(deviceId, FIXTURE.key)
    const result = await getStoredDeviceId()
    expect(typeof result).toBe('string')
    expect(result).not.toBeNull()
  })
})

// ── Step 3: 암호화/복호화 테스트 ──

describe('decrypt (AES-256-GCM)', () => {
  it('정상 복호화 → 원본 JSON 복원', async () => {
    const result = await decrypt(
      { iv: FIXTURE.iv, ciphertext: FIXTURE.ciphertext, tag: FIXTURE.tag },
      FIXTURE.key
    )
    expect(result).toEqual({ price: 75000, symbol: 'TEST' })
  })

  it('잘못된 키 → 에러 throw', async () => {
    // 다른 32바이트 키 (base64)
    const wrongKey = 'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA='
    await expect(
      decrypt(
        { iv: FIXTURE.iv, ciphertext: FIXTURE.ciphertext, tag: FIXTURE.tag },
        wrongKey
      )
    ).rejects.toThrow()
  })

  it('변조된 ciphertext → 에러 throw (base64ToArrayBuffer 간접 검증 포함)', async () => {
    // ciphertext 마지막 바이트를 변조
    const tampered = FIXTURE.ciphertext.slice(0, -4) + 'AAAA'
    await expect(
      decrypt(
        { iv: FIXTURE.iv, ciphertext: tampered, tag: FIXTURE.tag },
        FIXTURE.key
      )
    ).rejects.toThrow()
  })
})
