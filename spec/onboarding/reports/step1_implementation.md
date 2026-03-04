# onboarding 구현 보고서

> 작성일: 2026-03-04 | 커밋 대기

## 생성/수정 파일 목록

| 파일 | 내용 |
|------|------|
| `backend/app/models/auth.py` | `OnboardingState` 모델 추가, `User` 관계 추가, `Integer` import 추가 |
| `backend/app/api/onboarding.py` | 온보딩 상태 API (`GET /api/onboarding/status`, `POST /api/onboarding/step/{n}`, `POST /api/onboarding/accept-risk`) |
| `backend/app/main.py` | `onboarding_router` 등록 |
| `frontend/src/services/onboarding.ts` | 로컬 서버 API 클라이언트 |
| `frontend/src/components/RiskDisclosure.tsx` | 위험고지 컴포넌트 (체크박스 2개 + 동의 버튼) |
| `frontend/src/components/BridgeInstaller.tsx` | 브릿지 설치 안내 + WS 자동 감지 |
| `frontend/src/pages/Onboarding.tsx` | 6단계 온보딩 페이지 |
| `frontend/src/App.tsx` | `/onboarding` 라우트 추가 |

## 주요 기능

### 온보딩 상태 추적
- `OnboardingState` 테이블: `step_completed(0~6)`, `risk_accepted`, `risk_accepted_at`, `completed_at`
- `_get_or_create()`: 첫 접속 시 자동 생성
- 단계 완료 API: `step_completed` 최대값으로 업데이트 (이전 단계로 역행 방지)
- 6단계 완료 시 `completed_at` 기록

### 위험고지 (RiskDisclosure)
- 체크박스 2개 모두 선택 후에만 버튼 활성화
- 동의 시 `/api/onboarding/accept-risk` 저장 + step 2 완료

### 브릿지 설치 감지 (BridgeInstaller)
- 5초마다 `ws://127.0.0.1:8765/ws` 연결 시도
- 성공 시 step 3 완료 + 다음 단계 자동 이동

### 온보딩 페이지
- 진행 바 (현재 단계 / 6)
- 완료된 사용자는 `/` 리다이렉트
- 6단계: "전략 만들기" → `/strategy`, "나중에 하기" → `/`

## 비고
- `/onboarding` 라우트는 Layout 외부에 독립 렌더링 (nav 없는 전체 화면)
- 키움 HTS 연결 상태는 단계 4에서 수동 확인 버튼 방식 (WS 이벤트 연동은 추후)
