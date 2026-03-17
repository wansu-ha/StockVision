# 동의 관리 통합 구현 계획서 (재동의 + 면책 고지)

> 작성일: 2026-03-16 | 수정: 2026-03-17 | 상태: 초안 | 범위: plan-v2 Step F + 면책 고지 시점

---

## 0. 배경 및 현황

plan-v2의 Step A~E (모델, API, 회원가입 동의, 열람 페이지, Settings 섹션)는 구현 완료.
**잔여 2건**이 미구현:

| ID | 이슈 | spec 근거 | 현재 상태 |
|----|------|----------|----------|
| F1 | **기존 사용자 재동의 모달** | spec §9 미결 "약관 버전 관리 + 변경 시 재동의 정책" | 백엔드 `consent/status` API 완성, 프론트 미구현 |
| F2 | **면책 고지 시점 (전략 활성화 시)** | spec §6.2 "전략 빌더에서 첫 규칙 활성화 시 확인 팝업" | `handleStrategyToggle`에 체크 없음 |

### 코드 현황

**이미 완성된 백엔드**:
- `cloud_server/models/legal.py` — `LegalDocument`, `LegalConsent` 모델
- `cloud_server/api/legal.py`:
  - `GET /api/v1/legal/consent/status` → `{ terms: { up_to_date: bool, ... }, privacy: {...}, disclaimer: {...} }`
  - `POST /api/v1/legal/consent` → `{ doc_type, doc_version }` 기록
  - `GET /api/v1/legal/documents/{doc_type}` → 최신 약관 마크다운
- `CURRENT_VERSIONS = { terms: "1.1", privacy: "1.1", disclaimer: "1.1" }`

**프론트엔드 기존 패턴**:
- 모달: 커스텀 div 오버레이 (`fixed inset-0 bg-black/60`) — HeroUI Modal 미사용
- 참고: `ArmDialog.tsx`, `DetailView.tsx`의 AddRuleModal
- `AuthContext.tsx`: login 후 `setState({ jwt, email, isAuthenticated, localReady })` — 동의 상태 없음
- `App.tsx`: `ProtectedRoute`는 `isAuthenticated`만 체크

**login 엔드포인트** (`auth.py:162`): `requires_consent` 필드 미반환

---

## 1. 설계 결정

### D1: 동의 체크 시점 — 프론트엔드 주도

**선택**: 로그인 응답을 수정하지 않고, 프론트엔드에서 `consent/status` API를 직접 호출.

**이유**:
- 백엔드 login 엔드포인트 변경 최소화 (기존 인터페이스 유지)
- `consent/status` API가 이미 완성되어 있어 추가 백엔드 작업 불필요
- 약관 변경은 드물지만, 체크 로직은 프론트 단에서 유연하게 제어 가능
- 토큰 갱신(`loginWithTokens`, 자동 로그인) 시에도 동일하게 동작

### D2: 면책 고지 — 세션당 1회

**선택**: disclaimer 동의는 `legal_consents` DB에 기록 + 세션 중 재확인 없음.

**이유**:
- spec §6.2: "첫 규칙 활성화 시 확인 팝업" → 최초 1회 동의 후 DB 기록
- 매번 팝업은 UX 악화 → `consent/status`에서 `disclaimer.up_to_date=true`면 스킵
- 약관 버전 업데이트 시 자동으로 `up_to_date=false` → 재동의 트리거

### D3: 모달 차단 레벨

| 상황 | 차단 레벨 |
|------|----------|
| terms/privacy 재동의 | **강제** — 모달 닫기 불가, 서비스 이용 불가 |
| disclaimer 미동의 (전략 실행 시) | **조건부** — 전략 시작만 차단, 나머지 기능 사용 가능 |

---

## 2. 구현 단계

### Step 1: `useConsentStatus` 훅

**신규 파일**: `frontend/src/hooks/useConsentStatus.ts`

```typescript
import { useQuery } from '@tanstack/react-query'
import cloudClient from '../services/cloudClient'

interface ConsentItem {
  agreed_version: string | null
  agreed_at: string | null
  latest_version: string
  up_to_date: boolean
}

export interface ConsentStatus {
  terms: ConsentItem
  privacy: ConsentItem
  disclaimer: ConsentItem
}

export function useConsentStatus(enabled = true) {
  return useQuery<ConsentStatus>({
    queryKey: ['consentStatus'],
    queryFn: async () => {
      const res = await cloudClient.get('/api/v1/legal/consent/status')
      return res.data.data
    },
    staleTime: 5 * 60_000,   // 5분 캐시
    enabled,
  })
}
```

### Step 2: `ConsentGate` 컴포넌트

**신규 파일**: `frontend/src/components/ConsentGate.tsx`

기존 `ProtectedRoute`를 감싸는 래퍼. 로그인 후 terms/privacy 동의 상태를 체크하고, `up_to_date=false`인 항목이 있으면 재동의 모달을 표시.

**동작 흐름**:
1. `useConsentStatus()` 호출
2. 로딩 중 → 스피너 (children 렌더 차단 — 동의 확인 전 접근 불가)
3. API 에러 → 에러 UI + 재시도 버튼 (children 렌더 차단)
4. `terms.up_to_date=false` 또는 `privacy.up_to_date=false` → `ConsentRenewalModal` 표시
5. 모달은 배경 클릭/ESC로 닫기 불가 (강제 동의)
6. 동의 완료 → `POST /consent` 호출 → `queryClient.invalidateQueries(['consentStatus'])`
7. 모든 약관 `up_to_date=true` → children 렌더

**UI 목업**:
```
┌─ 약관 변경 안내 ──────────────────────────────────┐
│                                                   │
│  서비스 약관이 변경되었습니다.                        │
│  계속 이용하시려면 변경된 약관에 동의해 주세요.        │
│                                                   │
│  📄 이용약관 (v1.0 → v1.1)           [변경 확인 →]  │
│  📄 개인정보처리방침 (v1.0 → v1.1)    [변경 확인 →]  │
│                                                   │
│  ☐ 변경된 약관 내용을 확인하고 동의합니다             │
│                                                   │
│  [동의하고 계속]              [로그아웃]              │
│                                                   │
└───────────────────────────────────────────────────┘
```

**컴포넌트 구조**:
```
ConsentGate
├── useConsentStatus()
├── 조건: outdated terms/privacy → ConsentRenewalModal
│   ├── 약관별 링크 (/legal/:type, 새 탭)
│   ├── 동의 체크박스 (필수)
│   ├── [동의하고 계속] → POST /consent (각 doc_type별)
│   └── [로그아웃] → auth.logout()
└── 조건: 모두 up_to_date → children
```

### Step 3: App.tsx에 ConsentGate 적용

**변경 파일**: `frontend/src/App.tsx`

`ProtectedRoute` 내부에 `ConsentGate` 추가:

```typescript
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth()
  if (import.meta.env.DEV && import.meta.env.VITE_AUTH_BYPASS === 'true') return <>{children}</>
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return <ConsentGate>{children}</ConsentGate>   // ← 추가
}
```

> 주의: 온보딩(`/onboarding`) 경로도 ProtectedRoute 안이므로 ConsentGate 적용됨.
> 이는 의도적 — 온보딩 중에도 약관 동의는 선행되어야 함.

### Step 4: 면책 고지 확인 (전략 활성화 시)

**변경 파일**: `frontend/src/pages/MainDashboard.tsx`

`handleStrategyToggle` 수정:

```typescript
// 현재 (139-151행)
const handleStrategyToggle = async () => {
  setStrategyLoading(true)
  try {
    if (engineRunning) {
      await localEngine.stop()
    } else {
      await localEngine.start()       // ← disclaimer 체크 없음
    }
    queryClient.invalidateQueries({ queryKey: ['localStatus'] })
  } finally {
    setStrategyLoading(false)
  }
}

// 변경
const [showDisclaimer, setShowDisclaimer] = useState(false)
const { data: consentStatus } = useConsentStatus()

const handleStrategyToggle = async () => {
  if (!engineRunning) {
    // 엔진 시작 시: disclaimer 동의 여부 확인
    if (!consentStatus?.disclaimer.up_to_date) {
      setShowDisclaimer(true)     // ← 면책 모달 표시
      return
    }
  }
  // 기존 로직
  setStrategyLoading(true)
  try {
    if (engineRunning) {
      await localEngine.stop()
    } else {
      await localEngine.start()
    }
    queryClient.invalidateQueries({ queryKey: ['localStatus'] })
  } finally {
    setStrategyLoading(false)
  }
}
```

**DisclaimerModal 컴포넌트** (같은 파일 내 또는 별도 파일):

```
┌─ 투자 위험 고지 ──────────────────────────────────┐
│                                                   │
│  ⚠️ 자동매매를 시작하기 전에 확인해 주세요           │
│                                                   │
│  • 모든 매매 규칙은 사용자가 직접 정의합니다          │
│  • AI/LLM 정보는 참고용이며 투자 추천이 아닙니다      │
│  • 과거 성과는 미래 수익을 보장하지 않습니다          │
│  • 시스템 오류로 인한 손실이 발생할 수 있습니다       │
│  • 투자 손익은 사용자 본인에게 귀속됩니다             │
│                                                   │
│  📄 투자 위험 고지 전문 확인            [전문 보기 →] │
│                                                   │
│  ☐ 위 내용을 확인하고 동의합니다                     │
│                                                   │
│  [동의하고 시작]                        [취소]       │
│                                                   │
└───────────────────────────────────────────────────┘
```

**동작**:
1. "전문 보기" → `/legal/disclaimer` 새 탭
2. 체크박스 체크 + "동의하고 시작" → `POST /consent` (doc_type: "disclaimer") → 엔진 시작
3. "취소" → 모달 닫기 (전략 실행 안 함)
4. 동의 후 consentStatus 갱신 → 다음부터 모달 미표시

### Step 5: cloudClient에 legal API 함수 추가

**변경 파일**: `frontend/src/services/cloudClient.ts`

```typescript
// 기존 export 섹션에 추가
export const legalApi = {
  getConsentStatus: () =>
    client.get('/api/v1/legal/consent/status').then(r => r.data),
  recordConsent: (docType: string, docVersion: string) =>
    client.post('/api/v1/legal/consent', { doc_type: docType, doc_version: docVersion }).then(r => r.data),
  getDocument: (docType: string) =>
    client.get(`/api/v1/legal/documents/${docType}`).then(r => r.data),
}
```

> 이 함수들을 useConsentStatus 훅과 ConsentGate/DisclaimerModal에서 사용.

---

## 3. 파일 변경 목록

### 신규 파일 (3개)

| 파일 | 용도 | 줄수 추정 |
|------|------|----------|
| `frontend/src/hooks/useConsentStatus.ts` | 동의 상태 조회 훅 | ~25 |
| `frontend/src/components/ConsentGate.tsx` | 재동의 강제 게이트 + 모달 | ~120 |
| `frontend/src/components/DisclaimerModal.tsx` | 면책 고지 확인 모달 | ~80 |

### 수정 파일 (3개)

| 파일 | 변경 내용 | 변경 범위 |
|------|----------|----------|
| `frontend/src/services/cloudClient.ts` | `legalApi` 객체 추가 | +10줄 |
| `frontend/src/App.tsx` | ProtectedRoute에 ConsentGate 래핑, import 추가 | ~3줄 |
| `frontend/src/pages/MainDashboard.tsx` | handleStrategyToggle에 disclaimer 체크, showDisclaimer 상태, DisclaimerModal 렌더 | ~20줄 |

### 백엔드 변경: 없음

기존 API (consent/status, consent, documents) 그대로 사용.

---

## 4. 구현 순서 및 의존성

```
Step 5 (legalApi) ─┬── Step 1 (useConsentStatus) ── Step 2 (ConsentGate) ── Step 3 (App.tsx)
                   └── Step 4 (DisclaimerModal + MainDashboard)
```

| 순서 | Step | 의존 | 설명 |
|------|------|------|------|
| 1 | Step 5 | 없음 | cloudClient에 legalApi 추가 |
| 2 | Step 1 | Step 5 | useConsentStatus 훅 |
| 3 | Step 2 + 3 | Step 1 | ConsentGate + App.tsx 적용 (F1 완료) |
| 4 | Step 4 | Step 1 | DisclaimerModal + MainDashboard 수정 (F2 완료) |

Step 3과 Step 4는 병렬 가능하나, 같은 개발자가 순차 진행하는 것이 현실적.

---

## 5. 수용 기준

### F1: 재동의 모달

- [ ] 로그인 후 `consent/status` API 호출
- [ ] `terms.up_to_date=false` → 재동의 모달 표시
- [ ] `privacy.up_to_date=false` → 재동의 모달 표시
- [ ] 모달 배경 클릭/ESC로 닫기 불가
- [ ] "변경 확인" 클릭 → 약관 전문 새 탭
- [ ] 체크박스 미체크 시 "동의하고 계속" 비활성
- [ ] "동의하고 계속" → POST /consent (해당 doc_type별) → 모달 닫힘
- [ ] "로그아웃" → 세션 종료, 로그인 페이지 이동
- [ ] 동의 완료 후 서비스 정상 이용 가능
- [ ] 모든 약관 up_to_date=true → 모달 미표시

### F2: 면책 고지 (전략 활성화 시)

- [ ] 엔진 시작 클릭 시 `disclaimer.up_to_date` 확인
- [ ] `false` → DisclaimerModal 표시
- [ ] 5개 위험 항목 표시 (spec §6.1 문구)
- [ ] "전문 보기" → `/legal/disclaimer` 새 탭
- [ ] 체크박스 미체크 시 "동의하고 시작" 비활성
- [ ] "동의하고 시작" → POST /consent (disclaimer) → 엔진 시작
- [ ] "취소" → 모달 닫기, 엔진 미시작
- [ ] 동의 후 다음 엔진 시작 시 모달 미표시
- [ ] 엔진 정지는 disclaimer 체크 없이 가능

---

## 6. 커밋 계획

| # | 메시지 | 파일 |
|---|--------|------|
| 1 | `docs: 동의 관리 통합 plan-v3 작성` | spec/legal/plan-v3.md |
| 2 | `feat(legal): legalApi + useConsentStatus 훅` | cloudClient.ts, useConsentStatus.ts |
| 3 | `feat(legal): ConsentGate 재동의 모달 (F1)` | ConsentGate.tsx, App.tsx |
| 4 | `feat(legal): DisclaimerModal 면책 고지 (F2)` | DisclaimerModal.tsx, MainDashboard.tsx |

---

## 7. "동의 없이 못 쓴다" 증명 체인

### 7.1 증명 구조

```
[회원가입] ─── Register.tsx: termsAgreed + privacyAgreed 필수
    │           └ 서버: auth.py:125 LegalConsent DB 저장 (terms 1.1, privacy 1.1)
    │           └ 버튼 disabled={!termsAgreed || !privacyAgreed}
    ▼
[로그인 후] ─── ConsentGate (ProtectedRoute 내부)
    │           └ consent/status API → up_to_date 확인
    │           └ false → 강제 모달 (닫기 불가, 로그아웃만 가능)
    │           └ 증명: 약관 변경 시에도 동의 없이 서비스 이용 불가
    ▼
[전략 실행] ─── DisclaimerModal (handleStrategyToggle)
                └ disclaimer.up_to_date=false → 실행 차단
                └ 동의 후 POST /consent → DB 기록
                └ 증명: 면책 동의 없이 자동매매 불가
```

### 7.2 보장 근거

1. **라우터 레벨 차단**: ConsentGate가 ProtectedRoute 내부 → 인증된 모든 경로에 적용
2. **서버 사이드 기록**: 동의는 `legal_consents` 테이블에 저장 (누가, 언제, 어떤 버전)
3. **프론트 우회 불가**: 동의 상태는 서버 API에서 판단 (클라이언트 조작 무의미)
4. **버전 관리**: CURRENT_VERSIONS 변경 시 자동으로 재동의 트리거

### 7.3 엣지 케이스

| 상황 | 처리 |
|------|------|
| consent/status API 실패 | **차단 유지** — 에러 UI + 재시도 버튼 (통과 불가) |
| consent/status 로딩 중 | 로딩 스피너 표시 (children 렌더 차단) |
| 토큰 갱신 후 재진입 | React Query 캐시로 즉시 응답 (5분 stale) |
| DEV 모드 AUTH_BYPASS | ConsentGate도 bypass (ProtectedRoute 내부이므로 자동) |
| 동시에 terms + privacy 모두 재동의 필요 | 하나의 모달에 둘 다 표시, 한 번에 동의 |
| disclaimer 버전 업데이트 | 다음 엔진 시작 시 자동으로 재동의 요청 |
| POST /consent 실패 | 에러 toast 표시, 모달 유지 (재시도 가능) |
| 신규 가입 직후 로그인 | terms/privacy는 가입 시 시딩됨 → ConsentGate 통과 |
| disclaimer 미동의 상태로 서비스 이용 | 가능 (조회, 설정 등) — 전략 실행만 차단 (의도적 설계) |

---

**마지막 갱신**: 2026-03-17
