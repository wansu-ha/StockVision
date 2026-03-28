> 작성일: 2026-03-28 | 상태: 초안

# e2eCrypto 유닛 테스트 — 구현 계획

## 구현 순서

### Step 1: 테스트 인프라

- happy-dom 내장 IndexedDB로 먼저 시도
  - 실패 시 `fake-indexeddb` 설치 + setup 파일에 mock 등록
- Web Crypto polyfill 필요 여부 확인 (Node 18+ 내장)

**verify**: 빈 테스트 파일이 Vitest에서 실행됨

### Step 2: IndexedDB 함수 테스트

테스트 케이스:
1. saveDeviceKey → loadDeviceKey 왕복
2. loadDeviceKey 미등록 ID → null
3. deleteDeviceKey 후 조회 → null
4. getStoredDeviceId 비어있으면 null
5. getStoredDeviceId 키 있으면 첫 번째 ID

**verify**: 5개 테스트 통과

### Step 3: 암호화/복호화 테스트

fixture 생성:
1. Python으로 AES-256-GCM 암호화 수행
2. key, iv, ciphertext, tag를 base64로 export
3. 테스트에서 이 fixture로 decrypt 검증

테스트 케이스:
1. 정상 복호화 → 원본 JSON 복원
2. 잘못된 키 → DOMException throw
3. 변조된 ciphertext → throw

(base64ToArrayBuffer는 내부 함수(export 없음) → decrypt 경유로 간접 검증)

**verify**: 3개 테스트 통과

### Step 4: 전체 통합

- `npm run test` 전체 통과 확인
- 기존 dslParser + dslConverter 테스트도 통과

## 위험 요소

- Node 환경 Web Crypto와 브라우저 Web Crypto 미세 차이 가능성
  → fixture 기반이므로 입출력만 검증, 내부 구현 차이 무관
- happy-dom IndexedDB 구현이 불완전할 수 있음
  → 실패 시 fake-indexeddb로 즉시 전환
