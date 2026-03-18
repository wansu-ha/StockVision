# Phase A 잔여 항목 정리 명세서

> 작성일: 2026-03-17 | 상태: 부분 구현 | 갱신: 2026-03-18 (F1+, F2+ 7건, D1, D4 구현 완료. 잔여: F3, Q5. F2+ 전체 현황: 14/~38 쿼리 staleTime 설정, ~24건 잔여 → Sprint Stage 1)

---

## 1. 목표

dev-plan-v3 Phase A 완료 기준 중 잔여 소규모 항목 6건을 정리한다.
각 항목은 1~3파일 수정 수준이므로 하나의 spec으로 묶는다.

---

## 2. 항목 목록

| ID | 항목 | 복잡도 |
|----|------|--------|
| F1+ | ErrorBoundary 라우트 리셋 | trivial |
| F2+ | staleTime 미설정 쿼리 7건 | trivial |
| F3 | 프로필 수정 (닉네임) | small |
| Q5 | 장 상태 — 주말/공휴일 반영 | small |
| D1 | .env 플랜 상수 추가 | trivial |
| D4 | 메신저 드롭다운 UI 선점 | small |

---

## 3. 상세 명세

### F1+ — ErrorBoundary 라우트 리셋

**현재**: `ErrorBoundary`(클래스 컴포넌트)는 에러 발생 시 수동 버튼 클릭으로만 리셋 가능.
사용자가 사이드바에서 다른 페이지로 이동해도 에러 화면이 유지된다.

**변경**: `App.tsx`에서 `<ErrorBoundary key={location.pathname}>`로 감싸서, 라우트 변경 시 React가 컴포넌트를 재마운트하도록 한다. ErrorBoundary 자체는 수정 불필요.

**수정 파일**: `frontend/src/App.tsx`

**수용 기준**:
- [x] 에러 발생 후 사이드바 네비게이션으로 다른 페이지 이동 시 에러 화면 사라짐 (2026-03-18)
- [x] 같은 페이지 내 에러는 "다시 시도" 버튼으로 리셋 가능 (기존 동작 유지) (2026-03-18)

---

### F2+ — staleTime 미설정 쿼리

**현재**: React Query의 `useQuery` 호출 중 7건에 `staleTime`이 없었다 (이 spec 작성 당시).
전수 감사 결과 전체 ~38개 쿼리 중 14개만 staleTime 설정됨. ~24건 잔여 → Sprint Stage 1에서 처리.

**미설정 쿼리 목록**:

| 파일 | queryKey | refetchInterval | 권장 staleTime |
|------|----------|-----------------|---------------|
| `hooks/useAccountBalance.ts` | `['accountBalance']` | 30s | 5_000 |
| `hooks/useAccountBalance.ts` | `['openOrders']` | 15s | 5_000 |
| `hooks/useAccountStatus.ts` | `['localStatus']` | 5s | 3_000 |
| `hooks/useMarketContext.ts` | `['marketContext']` | 30s | 15_000 |
| `pages/MainDashboard.tsx` | `['fillLogs']` | 15s | 10_000 |
| `pages/MainDashboard.tsx` | `['dailyPnl']` | 30s | 15_000 |
| `pages/Admin/ErrorLogs.tsx` | `['admin', 'errors', ...]` | 10s | 5_000 |

**원칙**: `staleTime ≤ refetchInterval`이어야 한다. staleTime이 refetchInterval보다 크면 폴링이 무의미해진다.

**수용 기준**:
- [x] 위 7건 모두 staleTime 설정됨 (2026-03-18)
- [x] 탭 전환/컴포넌트 재마운트 시 staleTime 내 데이터는 캐시 사용 (2026-03-18)

---

### F3 — 프로필 수정 (닉네임)

**현재**:
- `User` 모델에 `nickname: str | None` 필드 존재 (가입 시 설정 가능)
- 가입 이후 닉네임 수정 엔드포인트 없음
- Settings 페이지에 이메일만 표시 (disabled)

**변경**:

1. **백엔드** — `PATCH /api/v1/auth/profile` 엔드포인트 추가
   - 인증 필수 (`current_user` 의존성)
   - 요청 바디: `{ nickname: string }` (1~50자, 공백 trim)
   - 응답: `{ success: true, data: { nickname } }`

2. **프론트엔드** — Settings "계정" 섹션에 닉네임 편집 UI 추가
   - 현재 닉네임 표시 + 편집 가능한 input
   - 저장 버튼 (변경 시에만 활성화)
   - 성공/에러 토스트

3. **API 클라이언트** — `cloudAuth.updateProfile({ nickname })` 추가

**수정 파일**:
- `cloud_server/api/auth.py`
- `frontend/src/pages/Settings.tsx`
- `frontend/src/services/cloudClient.ts`

**수용 기준**:
- [ ] Settings에서 닉네임 확인 및 수정 가능
- [ ] 빈 문자열/공백만 입력 시 거부 (서버 측 검증)
- [ ] 50자 초과 시 거부
- [ ] 수정 성공 시 토스트 표시

---

### Q5 — 장 상태: 주말/공휴일 반영

**현재**: `MainDashboard.tsx:134-141`에서 현재 시각 기반으로만 장 상태를 추정.
주말과 한국 공휴일을 무시한다.

```typescript
// 현재 로직 — 주말/공휴일 미감지
const hhmm = now.getHours() * 100 + now.getMinutes()
const status = hhmm >= 900 && hhmm < 1530 ? '장중' : hhmm < 900 ? '장전' : '장후'
```

**변경**:

1. **백엔드** — Context API 응답에 `is_holiday: bool` 필드 추가
   - `context_service.py`에 `KOREAN_HOLIDAYS` 상수 (해당 연도 공휴일 날짜 리스트) 정의
   - `build_context()`에서 오늘 날짜가 리스트에 포함되면 `is_holiday: true`
   - 주말은 프론트에서 자체 판단 (백엔드 중복 불필요)
   - ※ 공휴일 관련 코드/테이블이 프로젝트에 없으므로 하드코딩으로 시작.
     매년 수동 갱신 또는 향후 외부 API 연동으로 확장 가능

2. **프론트엔드 타입** — `MarketContextData`에 `is_holiday?: boolean` 추가

3. **프론트엔드 로직** — 장 상태 판정 개선
   - 주말 (토/일): '휴장'
   - `context.is_holiday === true`: '휴장'
   - 평일 + 비공휴일: 기존 시간 기반 로직

**수정 파일**:
- `cloud_server/services/context_service.py`
- `frontend/src/types/dashboard.ts`
- `frontend/src/pages/MainDashboard.tsx`

**수용 기준**:
- [ ] 토/일요일에 '휴장' 표시
- [ ] 공휴일에 '휴장' 표시 (백엔드 데이터 기반)
- [ ] 평일 장중/장전/장후 기존 동작 유지
- [ ] 백엔드 응답 없어도 주말 감지는 프론트 단독으로 동작

---

### D1 — .env 플랜 상수

**현재**: `cloud_server/core/config.py`에 플랜 관련 상수 없음.
**참고**: `docs/product/free-pro-boundary.md` §13에 명시:

```env
PLAN_MAX_STRATEGIES=3
PLAN_HISTORY_DAYS=30
```

**변경**: `Settings` 클래스에 추가:

```python
# 플랜 제한 (무료 기본값)
PLAN_MAX_STRATEGIES: int = int(os.environ.get("PLAN_MAX_STRATEGIES", "3"))
PLAN_HISTORY_DAYS: int = int(os.environ.get("PLAN_HISTORY_DAYS", "30"))
```

**수정 파일**: `cloud_server/core/config.py`

**수용 기준**:
- [x] `settings.PLAN_MAX_STRATEGIES`, `settings.PLAN_HISTORY_DAYS` 참조 가능 (2026-03-18)
- [x] 환경변수 미설정 시 무료 플랜 기본값 사용 (2026-03-18)

---

### D4 — 메신저 드롭다운 UI 선점

**현재**: `AlertSettings.tsx`에 알림 규칙(enable/threshold) 관리만 있고,
알림 전달 채널 설정이 없다.

**변경**: "알림 채널" 섹션 추가 (UI 선점, 백엔드 미연동).

- 드롭다운 선택지: 앱 내 알림 (기본, 활성), 이메일, 텔레그램, 디스코드
- 앱 내 알림 외에는 "준비 중" 뱃지 + disabled
- 선택 값은 로컬 상태로만 관리 (서버 저장 없음)

**수정 파일**: `frontend/src/components/AlertSettings.tsx`

**수용 기준**:
- [x] "알림 채널" 드롭다운이 AlertSettings 상단에 표시 (2026-03-18)
- [x] 앱 내 알림이 기본 선택 (2026-03-18)
- [x] 이메일/텔레그램/디스코드는 "준비 중" 표시 + 선택 불가 (2026-03-18)
- [x] 기존 알림 규칙 토글 기능에 영향 없음 (2026-03-18)
