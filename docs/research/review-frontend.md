# Frontend 코드 리뷰

> 작성일: 2026-03-13 | 대상: frontend/src/ 전체

---

## 요약

| 분류 | 건수 |
|------|------|
| Critical | 4 |
| Important | 10 |
| Medium | 6 |
| 미완성 기능 | 5 |

핵심 문제: (1) OAuth 콜백에서 AuthContext 미갱신 → 로그인 항상 실패, (2) alertsClient 인증 헤더 없음, (3) StrategyBuilder 편집 모드에서 조건이 기본값으로 리셋 → 데이터 손실.

---

## Critical

### C-1: OAuth 콜백 → AuthContext 미갱신, 로그인 실패

**파일**: `pages/OAuthCallback.tsx` L31-34
**신뢰도**: 100%

토큰을 sessionStorage에 저장하지만 AuthContext의 `login()` 미호출. `isAuthenticated`가 `false`로 유지되어 ProtectedRoute가 `/login`으로 리다이렉트.

### C-2: alertsClient — 인증 헤더 없음

**파일**: `services/alertsClient.ts` L29, 35
**신뢰도**: 100%

bare `axios` 사용, `X-Local-Secret` 미첨부. 모든 경고 설정 API 호출 실패.

### C-3: Settings.tsx handleLaunch — setInterval 누수

**파일**: `pages/Settings.tsx` L63-81
**신뢰도**: 95%

컴포넌트 언마운트 시 interval 미정리. 네트워크 요청 누수.

### C-4: DeviceManager 페어링 — X-Local-Secret 없음

**파일**: `components/DeviceManager.tsx` L28-29, 43-44
**신뢰도**: 95%

raw `fetch()` 사용, 인증 헤더 없음. 디바이스 페어링 완전 비작동.

---

## Important

### I-1: useLocalBridgeWS — 3회 실패 후 영구 중단

**파일**: `hooks/useLocalBridgeWS.ts` L79-83
**신뢰도**: 95%

브릿지 재시작 후에도 WS 재연결 안 됨. 페이지 새로고침 필요.

### I-2: useRemoteMode — 1회만 체크, 이후 미갱신

**파일**: `hooks/useRemoteMode.ts` L14-31
**신뢰도**: 90%

브릿지 시작/종료 후에도 `isRemote` 상태 안 바뀜.

### I-3: MainDashboard — selectedStock! non-null assertion

**파일**: `pages/MainDashboard.tsx` L204
**신뢰도**: 90%

상태 불일치 시 런타임 크래시 가능.

### I-4: StockList — watchlist 순차 fetch (Promise.allSettled 필요)

**파일**: `pages/StockList.tsx` L25-29
**신뢰도**: 90%

20개 종목 × 순차 API 호출 → O(n) 지연.

### I-5: StrategyBuilder 편집 모드 — 조건 기본값 리셋 (데이터 손실)

**파일**: `pages/StrategyBuilder.tsx` L111-123
**신뢰도**: 100%

`startEdit()` 호출 시 실제 규칙 조건이 아닌 EMPTY_FORM의 기본 조건으로 세팅. DSL 역파싱 미구현 (`// TODO: script → 폼 역파싱`). 저장하면 기존 전략 덮어씀.

### I-6: auth.ts — 별도 axios 인스턴스, env URL 미적용

**파일**: `services/auth.ts`
**신뢰도**: 85%

`VITE_CLOUD_API_URL` 미반영. 프로덕션에서 잘못된 URL로 호출 가능.

### I-7: MainDashboard — `as never` 타입 이스케이프

**파일**: `pages/MainDashboard.tsx` L55
**신뢰도**: 85%

타입 불일치를 `as never`로 숨김. LogFilter 인터페이스에 `log_type` 필드 누락.

### I-8: Layout.tsx — 라이트 테마, 나머지 앱 다크 테마

**파일**: `components/Layout.tsx` L29-31
**신뢰도**: 85%

`bg-gray-50`/`bg-white` 사용. 페이지 이동 시 라이트/다크 전환 발생.

### I-9: proto-a/b/c — 인증 없이 접근 가능

**파일**: `App.tsx` L61-63
**신뢰도**: 85%

ProtectedRoute 미적용. 프로덕션 빌드에서 제외하거나 인증 필요.

### I-10: useRemoteControl — 동시 재연결 체인 가능

**파일**: `hooks/useRemoteControl.ts` L89-97
**신뢰도**: 80%

`enabled` 빠른 토글 시 여러 WS 연결 동시 생성 가능.

---

## Medium

### M-1: LogSummary 인터페이스 중복 정의
`services/localClient.ts` + `services/logs.ts`.

### M-2: window.confirm() 사용 — 네이티브 다이얼로그
`pages/StrategyList.tsx`. PWA에서 문제 가능.

### M-3: TrafficLightStatus — 5초마다 3개 중복 폴링 + 자동 리로드
`components/TrafficLightStatus.tsx`. React Query 미사용, 중복 요청.

### M-4: fadeSlideIn 키프레임 미정의
`tailwind.config.js`. `MainDashboard`의 뷰 전환 애니메이션 비작동.

### M-5: getStoredDeviceId() — IndexedDB 첫 번째 키 반환
`utils/e2eCrypto.ts`. 멀티 디바이스 시 잘못된 키 사용.

### M-6: Admin 사이드바 isActive — 복수 항목 하이라이트 가능
`pages/Admin/index.tsx`.

---

## 미완성 기능

| ID | 내용 |
|----|------|
| S-1 | `cloudAuth.updateProfile` 미구현 (`{ success: false }` 반환) |
| S-2 | StrategyBuilder DSL 역파싱 미구현 (편집 모드 데이터 손실) |
| S-3 | ProtoA/B/C 목업 데이터만, 실제 API 미연결 |
| S-4 | 원격 제어 (C6-C8) — Firebase/FCM 미착수 |
| S-5 | MinuteBar 데이터 수집 미구현 |
