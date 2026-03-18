# Phase A 코드 감사 보고서

> 작성일: 2026-03-18 | 감사자: Claude Opus

---

## A6 Frontend Quality

### F1 ErrorBoundary — EXISTS (완전 구현)

- **파일**: `frontend/src/components/ErrorBoundary.tsx` (66줄)
- **구현**: 클래스 컴포넌트, `getDerivedStateFromError` + `componentDidCatch` 구현
- **기능**: 에러 화면 (오류 메시지, 다시 시도/새로고침 버튼), DEV 환경에서 에러 메시지 표시
- **App.tsx 적용** (line 34, 58, 138):
  - 외부 `<ErrorBoundary>` — App 전체 감싸기 (line 138)
  - 내부 `<ErrorBoundary key={location.pathname}>` — 라우트 변경 시 리셋 (line 58)
- **`key={location.pathname}` 패턴**: EXISTS (line 58) — 페이지 전환 시 에러 상태 자동 리셋

### F2 staleTime — PARTIAL (46개 useQuery 중 20개에 staleTime 설정)

**staleTime 있음 (20개):**

| 파일 | queryKey | staleTime |
|------|----------|-----------|
| `LegalDocument.tsx:30` | legalDoc | 30분 |
| `StrategyList.tsx:20` | rules | 2분 |
| `StrategyList.tsx:53` | stockNames | 5분 |
| `Admin/ErrorLogs.tsx:25` | admin/errors | 5초 |
| `MainDashboard.tsx:64` | fillLogs | 10초 |
| `MainDashboard.tsx:74` | dailyPnl | 15초 |
| `useAccountBalance.ts:17` | accountBalance | 5초 |
| `useAccountBalance.ts:26` | openOrders | 5초 |
| `useStockData.ts:43` | rules | 2분 |
| `useStockData.ts:51` | watchlist | 2분 |
| `useStockData.ts:86` | quotes | 10초 |
| `useStockData.ts:110` | stockNames | 5분 |
| `useAccountStatus.ts:32` | localStatus | 3초 |
| `useConsentStatus.ts:24` | consentStatus | 5분 |
| `useMarketContext.ts:11` | marketContext | 15초 |
| `BriefingCard.tsx:55` | marketBriefing | 30분 |
| `MarketContext.tsx:10` | market-context | 1분 |
| `PriceChart.tsx:298` | bars | 5분 |
| `PriceChart.tsx:307` | localBars | 30초 |
| `StockAnalysisCard.tsx:42` | stockAnalysis | 30분 |

**staleTime 없음 (26개):**

| 파일 | queryKey | 비고 |
|------|----------|------|
| `StrategyBuilder.tsx:56` | rules | staleTime 없음 |
| `StrategyList.tsx:27` | lastRuleResults | refetchInterval만 있음 |
| `ExecutionLog.tsx:66` | execution-logs | refetchInterval만 있음 |
| `ExecutionLog.tsx:75` | log-summary | refetchInterval만 있음 |
| `ExecutionLog.tsx:83` | execution-timeline | refetchInterval만 있음 |
| `ExecutionLog.tsx:95` | alert-logs | refetchInterval만 있음 |
| `Admin/ServiceKeys.tsx:22` | admin/service-keys | 없음 |
| `Admin/Stats.tsx:18` | admin/stats/connections | refetchInterval만 있음 |
| `Admin/AiMonitor.tsx:31` | admin/ai/stats | refetchInterval만 있음 |
| `Admin/AiMonitor.tsx:37` | admin/ai/recent | refetchInterval만 있음 |
| `Admin/Users.tsx:22` | admin/users | 없음 |
| `Admin/Dashboard.tsx:6` | admin/stats | refetchInterval만 있음 |
| `Admin/Dashboard.tsx:12` | admin/collector | refetchInterval만 있음 |
| `Admin/Dashboard.tsx:18` | admin/ai/stats-summary | refetchInterval만 있음 |
| `Admin/Dashboard.tsx:24` | admin/errors-recent | refetchInterval만 있음 |
| `Admin/Templates.tsx:21` | admin/templates | 없음 |
| `StockList.tsx:17` | watchlist | 없음 |
| `StockList.tsx:23` | watchlist-details | 없음 |
| `DeviceManager.tsx:16` | devices | 없음 |
| `OpsPanel.tsx:90` | cloudHealth | refetchInterval만 있음 |
| `OpsPanel.tsx:98` | localHealth | refetchInterval만 있음 |
| `OpsPanel.tsx:106` | localStatus | refetchInterval만 있음 |
| `OpsPanel.tsx:115` | logSummary | refetchInterval만 있음 |
| `OpsPanel.tsx:124` | dailyPnl | refetchInterval만 있음 |
| `DetailView.tsx:37` | symbol-timeline | refetchInterval만 있음 |
| `PriceChart.tsx:326` | fillLogs (symbol) | refetchInterval만 있음 |

> 참고: QueryClient 기본 설정(App.tsx line 37-44)에는 `retry: 1`, `refetchOnWindowFocus: false`만 있고 글로벌 staleTime은 0 (기본값).

### F3 Profile nickname — PARTIAL (프론트 스텁, 백엔드 미구현)

**Backend** (`cloud_server/api/auth.py`):
- PATCH /profile 엔드포인트 **NOT EXISTS** — auth.py에 profile 관련 라우트 없음
- RegisterBody에 `nickname` 필드 있음 (line 56), 가입 시 저장됨 (line 111)
- 가입 이후 닉네임 수정 API는 존재하지 않음

**Frontend** (`frontend/src/services/cloudClient.ts`, line 88-92):
- `cloudAuth.updateProfile` 함수 **EXISTS** — 그러나 스텁:
  ```typescript
  updateProfile: (_nickname: string) => {
    // TODO: 서버에 /api/v1/auth/profile 엔드포인트 없음 — 클라우드 서버 구현 후 연결
    console.warn('cloudAuth.updateProfile: 서버 엔드포인트 미구현')
    return Promise.resolve({ success: false, message: 'not implemented' })
  },
  ```

**Frontend UI** (`frontend/src/pages/Settings.tsx`, line 273-285):
- 계정 섹션에 이메일만 표시 (disabled input)
- 닉네임 편집 UI **NOT EXISTS** — 이메일 표시만 있고 닉네임 필드 없음

---

## A8 Quality Issues

### Q5 Holiday — NOT EXISTS

**Backend** (`cloud_server/services/context_service.py`):
- `is_holiday` 필드나 공휴일 판별 로직 **없음**
- 주말/공휴일 관련 코드는 yfinance 데이터 수집 시 여유 일수 계산 주석에만 존재 (`days + 5  # 주말/공휴일 여유`)
- 공휴일 데이터베이스/API 연동 없음

**Frontend** (`frontend/src/pages/MainDashboard.tsx`):
- 주말/휴장 판별 로직 **없음**
- `MarketStatus` 타입에 `'휴장'` 상태가 정의되어 있으나 (ListView.tsx line 50), 실제로 이를 결정하는 로직은 프론트엔드에 존재하지 않음
- 장전/장중/장후/휴장 상태는 로컬 서버에서 수신하는 것으로 추정되나 프론트엔드 자체에 판별 로직 없음

### D1 Plan constants — EXISTS

**파일**: `cloud_server/core/config.py` (line 96-97)
```python
PLAN_MAX_STRATEGIES: int = int(os.environ.get("PLAN_MAX_STRATEGIES", "3"))
PLAN_HISTORY_DAYS: int = int(os.environ.get("PLAN_HISTORY_DAYS", "30"))
```
- 환경변수로 오버라이드 가능, 기본값: 전략 3개, 히스토리 30일

### D4 Messenger dropdown — EXISTS (UI만)

**파일**: `frontend/src/components/AlertSettings.tsx` (line 111-125)
```tsx
<select
  className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-xs text-gray-200"
  defaultValue="app"
>
  <option value="app">앱 내 알림</option>
  <option value="email" disabled>이메일 (준비 중)</option>
  <option value="telegram" disabled>텔레그램 (준비 중)</option>
  <option value="discord" disabled>디스코드 (준비 중)</option>
</select>
```
- 드롭다운 UI **EXISTS**
- `defaultValue="app"` 하드코딩, `onChange` 핸들러 없음
- email/telegram/discord 옵션은 `disabled` 상태 — UI 스텁

---

## Bugs

### B1 AuthContext race condition — NOT EXISTS (이미 해결됨)

**파일**: `frontend/src/context/AuthContext.tsx`

분석:
- `localReady`는 초기값 `false` (line 53)
- RT refresh 성공 시 `localReady: true` 설정 (line 84)
- RT refresh 실패 시에도 `localReady: true` 설정 (line 90)
- 토큰 없어서 로컬 복원 시도 + 성공/실패 모두 `localReady: true` 설정 (line 103, 106)
- `handleRefreshed` 이벤트 (line 114-116)에서는 `localReady`를 변경하지 않음 — 이미 `true`인 상태에서만 발생

**잠재적 문제**: `logout` 시 `localReady: false`로 리셋 (line 168). 이후 재로그인 시 `login` 콜백에서 `localReady: true` 설정 (line 150). 정상 흐름.

401 인터셉터의 `handleRefreshed` (line 114-116)가 `localReady`를 건드리지 않으므로, RT refresh 중 `localReady`가 false로 리셋되는 race condition은 **없음**. 이 버그는 이미 해결된 상태.

### B2 useStockData race condition — NOT EXISTS (closure 문제 없음)

**파일**: `frontend/src/hooks/useStockData.ts`

분석:
- 모든 데이터 fetch는 `useQuery` 기반 — React Query가 stale/cancel 관리
- `quotesQuery`와 `namesQuery`는 `sortedSymbolKey`를 queryKey에 포함 (line 72, 96)
- queryFn 내에서 `queryKey`에서 심볼을 추출 (line 73-74, 97-98) — 클로저 캡처가 아닌 queryKey 기반이므로 stale closure 문제 없음
- `allSymbols`는 렌더링 스코프에서 계산되지만 queryKey로 직렬화되어 전달됨

**결론**: React Query의 queryKey 기반 아키텍처로 인해 클로저 race condition은 구조적으로 방지됨. 버그 **없음**.

### B3 Cancel button — EXISTS (조건부 동작)

**파일**: `frontend/src/components/main/ListView.tsx` (line 337-345)

```tsx
{o.orderId && onCancelOrder ? (
  <button
    onClick={() => onCancelOrder(o.orderId!)}
    className="text-xs text-yellow-400 hover:text-yellow-300 transition"
  >
    취소
  </button>
) : (
  <button className="text-xs text-gray-600 cursor-not-allowed" disabled>취소</button>
)}
```

- `onCancelOrder` prop이 전달되고 `orderId`가 존재하면 **동작하는 버튼** 렌더링
- 둘 중 하나라도 없으면 **disabled 스텁 버튼** 렌더링
- `onCancelOrder`는 `ListViewProps`에 optional로 정의 (line 73): `onCancelOrder?: (orderId: string) => void`

**실제 연결 확인** — MainDashboard.tsx (line 168-173, 228):
- `handleCancelOrder` 함수 구현됨: `localAccount.cancelOrder(orderId)` 호출 + `openOrders` 쿼리 무효화
- `isRemote ? undefined : handleCancelOrder`로 전달 — 로컬 모드에서만 활성화, 원격 모드에서는 undefined (disabled 표시)
- 버튼 자체는 스텁이 아니며 **조건부 동작** — 로컬 모드 + orderId 존재 시 실제 취소 동작

---

## 요약

| 항목 | 상태 | 요약 |
|------|------|------|
| F1 ErrorBoundary | **EXISTS** | 완전 구현. key={location.pathname} 패턴 포함 |
| F2 staleTime | **PARTIAL** | 46개 중 20개만 설정 (43%). Admin 패널, ExecutionLog, OpsPanel, StockList, DeviceManager, DetailView 등 미설정 |
| F3 Profile nickname | **PARTIAL** | 가입 시 저장만 가능. 수정 API 미구현, 프론트 스텁, Settings UI에 닉네임 필드 없음 |
| Q5 Holiday | **NOT EXISTS** | 공휴일 판별 로직 전무. MarketStatus 타입에 '휴장' 정의만 존재 |
| D1 Plan constants | **EXISTS** | config.py에 PLAN_MAX_STRATEGIES=3, PLAN_HISTORY_DAYS=30 구현 |
| D4 Messenger dropdown | **EXISTS (UI only)** | select 드롭다운 존재. email/telegram/discord disabled. onChange 미연결 |
| B1 AuthContext race | **NOT EXISTS** | 이미 해결. RT refresh 중 localReady 리셋 없음 |
| B2 useStockData race | **NOT EXISTS** | queryKey 기반 설계로 구조적 방지 |
| B3 Cancel button | **EXISTS (조건부)** | orderId + onCancelOrder prop 있으면 동작, 없으면 disabled |
