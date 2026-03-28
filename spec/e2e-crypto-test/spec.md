> 작성일: 2026-03-28 | 상태: 초안

# e2eCrypto 유닛 테스트

## 배경

`src/utils/e2eCrypto.ts`는 QR 페어링 시 교환한 키로 금융 데이터를 AES-256-GCM 복호화한다.
Web Crypto API + IndexedDB를 사용하며 현재 테스트 0개.

암호화가 깨지면 로컬 서버 데이터가 프론트에서 표시 불가 → 핵심 기능 마비.

## 대상 함수

| 함수 | 역할 |
|------|------|
| saveDeviceKey(id, key) | IndexedDB에 키 저장 |
| loadDeviceKey(id) | IndexedDB에서 키 로드 |
| deleteDeviceKey(id) | 키 삭제 |
| getStoredDeviceId() | 저장된 첫 디바이스 ID 반환 |
| decrypt(encrypted, key) | AES-256-GCM 복호화 |
| base64ToArrayBuffer(b64) | base64 → ArrayBuffer 변환 |

## 수용 기준

- [ ] saveDeviceKey → loadDeviceKey 왕복 검증
- [ ] deleteDeviceKey 후 loadDeviceKey === null
- [ ] getStoredDeviceId: 키 없으면 null, 있으면 첫 번째 ID
- [ ] decrypt: 알려진 key + ciphertext → 원본 복원
- [ ] decrypt: 잘못된 키 → 에러 throw
- [ ] base64ToArrayBuffer: decrypt 경유로 간접 검증 (내부 함수, export 없음)

## 기술적 도전

- **IndexedDB**: happy-dom(vitest 환경)이 IndexedDB 내장 지원 → 먼저 시도
  - 실패 시 `fake-indexeddb` 도입
- **Web Crypto**: Node 18+에서 `globalThis.crypto.subtle` 사용 가능
  - 또는 `@peculiar/webcrypto` polyfill
- 테스트용 암호문 생성: Python 서버의 암호화 로직과 동일한 방식으로 fixture 생성

## 변경 대상

| 파일 | 변경 |
|------|------|
| frontend/src/utils/__tests__/e2eCrypto.test.ts | 신규 |
| frontend/package.json | fake-indexeddb devDependency 추가 |
