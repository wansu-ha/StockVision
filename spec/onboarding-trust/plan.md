# 온보딩 신뢰 강화 — 구현 계획

> 작성일: 2026-03-12 | 상태: 구현 완료 | spec: `spec/onboarding-trust/spec.md`

## 전제 조건 확인

| 항목 | 현재 상태 |
|------|----------|
| BridgeInstaller 컴포넌트 | ✅ 존재 (60줄, WS 폴링, 다운로드 URL "#") |
| 로그인/회원가입 | ✅ 동작 |
| 로컬 서버 health | ✅ `GET /health` |
| 브로커 키 등록 | ✅ Settings 페이지에서 동작 |
| 온보딩 라우트 | ❌ 없음 — `/onboarding` 미등록 |
| 온보딩 완료 상태 저장 | ❌ 없음 |

## 구현 단계

### Step 1: 온보딩 완료 상태 관리

**파일**: `frontend/src/hooks/useOnboarding.ts` (신규)

localStorage에 온보딩 완료 여부 저장:
```typescript
const ONBOARDING_KEY = 'stockvision:onboarding_completed'

export function useOnboarding() {
  const completed = localStorage.getItem(ONBOARDING_KEY) === 'true'
  const complete = () => localStorage.setItem(ONBOARDING_KEY, 'true')
  const reset = () => localStorage.removeItem(ONBOARDING_KEY)
  return { completed, complete, reset }
}
```

**verify**: hook import 에러 없음

### Step 2: 온보딩 라우트 추가

**파일**: `frontend/src/App.tsx`

```typescript
import OnboardingWizard from './pages/OnboardingWizard'

// 로그인 후 온보딩 미완료 시 리다이렉트
<Route path="/onboarding" element={<ProtectedRoute><OnboardingWizard /></ProtectedRoute>} />
```

리다이렉트 위치: MainDashboard 컴포넌트 내부 (ProtectedRoute는 인증만 담당, 온보딩 판단은 분리).
```typescript
// MainDashboard.tsx 상단
const { completed } = useOnboarding()
if (!completed) return <Navigate to="/onboarding" replace />
```

**verify**: 미완료 상태에서 `/` 접근 시 `/onboarding`으로 리다이렉트. 완료 후에는 직행.

### Step 3: OnboardingWizard 페이지 생성

**파일**: `frontend/src/pages/OnboardingWizard.tsx` (신규)

5단계 위저드:
1. 계정 확인 (로그인 완료 → 자동 완료)
2. 로컬 서버 연결 (BridgeInstaller 확장)
3. 증권사 연결 (BrokerKeyForm 임베드)
4. 시작 준비 완료 (요약 + 안내)
5. 완료 (대시보드 이동)

구조:
```typescript
export default function OnboardingWizard() {
  const [step, setStep] = useState(1)
  const { complete } = useOnboarding()
  // step 1: 로그인 완료 확인 → 자동 다음
  // step 2: BridgeInstaller (connected → 다음)
  // step 3: BrokerKeyForm (연결 확인 → 다음)
  // step 4: 요약 + "시작" 버튼
  // step 5: complete() → navigate('/')
}
```

공통 레이아웃: StepIndicator (상단 진행 표시) + StepContent + Navigation

**verify**: 빌드 에러 없음, 각 단계 이동 동작

### Step 4: StepIndicator 컴포넌트

**파일**: `frontend/src/components/onboarding/StepIndicator.tsx` (신규)

수평 진행 표시 (1─2─3─4─5):
- 완료: 녹색 체크
- 현재: 파란 원
- 미완료: 회색 원

**verify**: 시각적 확인

### Step 5: BridgeInstaller 확장

**파일**: `frontend/src/components/BridgeInstaller.tsx`

기존 컴포넌트에 3단계 분리 표시 추가:
1. 다운로드 — 버튼 + 상태 (URL은 여전히 "#", 플레이스홀더 유지)
2. 실행 — "설치 후 실행하세요" 안내
3. 연결 — health 폴링 → 연결 성공 시 콜백

실패 시 체크리스트 + 재시도/도움말 표시.

기존 WS 폴링을 health HTTP 폴링으로 변경 (더 안정적):
```typescript
const checkHealth = () => fetch('http://localhost:4020/health')
  .then(r => r.ok)
  .catch(() => false)
```

**verify**: 로컬 서버 끄고 켤 때 연결 감지 동작

### Step 6: BrokerKeyForm 추출

**파일**: `frontend/src/components/onboarding/BrokerKeyForm.tsx` (신규)

Settings 페이지의 API 키 등록 UI + 로직을 재사용 가능한 컴포넌트로 추출.
상태 관리: 내부에 독립적인 useState + useMutation 보유 (외부 의존 최소화).
Props: `onSuccess` 콜백만 받음.
Settings 페이지도 이 컴포넌트를 사용하도록 리팩토링.

추가 안내 텍스트 (온보딩 모드에서만):
- "API 키는 내 PC에만 저장됩니다"
- 모의/실전 선택 안내

**verify**: Settings 페이지 기존 동작 유지, 온보딩에서도 동일 동작

### Step 7: RiskDisclosure 컴포넌트

**파일**: `frontend/src/components/onboarding/RiskDisclosure.tsx` (신규)

위험고지 카드 (Step 2 진입 전 또는 Step 2 상단에 표시):
- 🖥️ 로컬 실행
- 🔒 키 미전송
- ⚠️ 사용자 책임

"이해했습니다" 체크박스 → 다음 단계 활성화.

**verify**: 체크 안 하면 다음 버튼 비활성화

### Step 8: 시작 준비 완료 (Step 4)

**파일**: OnboardingWizard.tsx 내부

연결 상태 요약:
- 브로커: 키움증권 / KIS (모의/실전)
- 로컬 서버: 연결됨
- 다음 안내: "대시보드에서 종목을 선택하고 전략 규칙을 추가하세요"
- 모의투자 권장 메시지

"시작" 버튼 → `complete()` → `navigate('/')`

**verify**: 요약 정보 정확, 대시보드 전환 동작

---

## 변경 파일 요약

| 파일 | 변경 | Step |
|------|------|------|
| `frontend/src/hooks/useOnboarding.ts` | 신규 — 완료 상태 관리 | 1 |
| `frontend/src/App.tsx` | `/onboarding` 라우트 추가, 리다이렉트 | 2 |
| `frontend/src/pages/OnboardingWizard.tsx` | 신규 — 5단계 위저드 페이지 | 3 |
| `frontend/src/components/onboarding/StepIndicator.tsx` | 신규 — 진행 표시 | 4 |
| `frontend/src/components/BridgeInstaller.tsx` | 3단계 분리, health 폴링 전환 | 5 |
| `frontend/src/components/onboarding/BrokerKeyForm.tsx` | 신규 — Settings에서 추출 | 6 |
| `frontend/src/pages/Settings.tsx` | BrokerKeyForm 사용으로 리팩토링 | 6 |
| `frontend/src/components/onboarding/RiskDisclosure.tsx` | 신규 — 위험고지 카드 | 7 |

## 검증 계획

1. `npm run build` — 빌드 에러 없음
2. 신규 사용자 시뮬레이션: localStorage 초기화 → 로그인 → `/onboarding` 리다이렉트
3. 각 단계 진행: 로컬 서버 연결 → 브로커 키 등록 → 완료 → 대시보드
4. 온보딩 완료 후 재로그인 → 대시보드 직행 (온보딩 스킵)
5. 중간 이탈 시뮬레이션: 브라우저 닫기 → 재방문 → URL 파라미터로 단계 복원
6. Settings 페이지 기존 동작 유지 확인
