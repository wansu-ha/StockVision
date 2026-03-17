# Phase A 잔여 항목 — 구현 계획서

> 작성일: 2026-03-17 | 상태: 초안

---

## 구현 순서

의존성 없는 항목부터 처리. trivial → small 순서.

### Step 1: F2+ staleTime 설정

5개 파일의 7개 쿼리에 `staleTime` 옵션 추가.

| 파일 | 추가 코드 |
|------|----------|
| `hooks/useAccountBalance.ts` | balanceQuery에 `staleTime: 5_000`, ordersQuery에 `staleTime: 5_000` |
| `hooks/useAccountStatus.ts` | `staleTime: 3_000` |
| `hooks/useMarketContext.ts` | `staleTime: 15_000` |
| `pages/MainDashboard.tsx` | fillLogs `staleTime: 10_000`, dailyPnl `staleTime: 15_000` |
| `pages/Admin/ErrorLogs.tsx` | `staleTime: 5_000` |

### Step 2: F1+ ErrorBoundary 라우트 리셋

`App.tsx`에서:
1. `useLocation()` import 추가
2. `<ErrorBoundary>` → `<ErrorBoundary key={location.pathname}>`

### Step 3: D1 .env 플랜 상수

`cloud_server/core/config.py` Settings 클래스에 2줄 추가:
```python
PLAN_MAX_STRATEGIES: int = int(os.environ.get("PLAN_MAX_STRATEGIES", "3"))
PLAN_HISTORY_DAYS: int = int(os.environ.get("PLAN_HISTORY_DAYS", "30"))
```

### Step 4: Q5 장 상태 공휴일

1. `cloud_server/services/context_service.py` — `KOREAN_HOLIDAYS` 상수 정의 + `build_context()`에 `is_holiday` 필드 추가
2. `frontend/src/types/dashboard.ts` — `MarketContextData`에 `is_holiday?: boolean`
3. `frontend/src/pages/MainDashboard.tsx` — 장 상태 판정 로직 수정:
   ```typescript
   const day = now.getDay()
   const isWeekend = day === 0 || day === 6
   const isHoliday = context?.is_holiday ?? false
   const status = isWeekend || isHoliday ? '휴장' : (시간 기반 기존 로직)
   ```

### Step 5: F3 프로필 수정

1. `cloud_server/api/auth.py` — `PATCH /api/v1/auth/profile` 추가
   - `ProfileUpdateRequest` 스키마: `nickname: str` (1~50자)
   - DB 업데이트 후 `{ success: true, data: { nickname } }` 응답
2. `frontend/src/services/cloudClient.ts` — `cloudAuth.updateProfile()` 추가
3. `frontend/src/pages/Settings.tsx` — 닉네임 input + 저장 버튼 추가

### Step 6: D4 메신저 드롭다운

`frontend/src/components/AlertSettings.tsx`:
- 알림 규칙 토글 위에 "알림 채널" 섹션 추가
- `<select>` + 옵션 4개 (앱 내 알림, 이메일, 텔레그램, 디스코드)
- 앱 내 알림 외 disabled + "준비 중" 라벨

---

## 수정 파일 종합

| 파일 | Step |
|------|------|
| `frontend/src/hooks/useAccountBalance.ts` | 1 |
| `frontend/src/hooks/useAccountStatus.ts` | 1 |
| `frontend/src/hooks/useMarketContext.ts` | 1 |
| `frontend/src/pages/MainDashboard.tsx` | 1, 4 |
| `frontend/src/pages/Admin/ErrorLogs.tsx` | 1 |
| `frontend/src/App.tsx` | 2 |
| `cloud_server/core/config.py` | 3 |
| `cloud_server/services/context_service.py` | 4 |
| `frontend/src/types/dashboard.ts` | 4 |
| `cloud_server/api/auth.py` | 5 |
| `frontend/src/services/cloudClient.ts` | 5 |
| `frontend/src/pages/Settings.tsx` | 5 |
| `frontend/src/components/AlertSettings.tsx` | 6 |

---

## 검증

1. `cd frontend && npm run build` — 빌드 에러 없음
2. `cd frontend && npm run lint` — lint 통과
