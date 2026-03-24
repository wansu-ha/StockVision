# 즉시 착수 개발 스프린트 — 구현 계획서

> 작성일: 2026-03-18 | 상태: 구현 완료 | 갱신: 2026-03-19 전 Stage 구현 완료

## 목표

외부 의존성·사용자 결정 없이 **지금 바로 코드 작성 가능한** 항목만 처리한다.

---

## 범위

### 포함 (4건)

| # | 항목 | 출처 | 복잡도 |
|---|------|------|--------|
| 1 | F2 staleTime 잔여 전수 정리 (~24건) | A6/A8 | trivial ×24 |
| 2 | Q5 장 상태 공휴일 | A8 | small (백+프 3파일) |
| 3 | F3 프로필 닉네임 수정 | A6 | small (백+프 3파일) |
| 4 | R4 Heartbeat WS Ack 버전 파싱 | T1-5 | small (2파일) |

### 제외 — 사유

| 항목 | 제외 사유 |
|------|----------|
| ~~T1-1 IndicatorProvider~~ | **코드 기구현됨.** 단, 차단급 버그 있음 (KOSDAQ `.KS` 오분류, yfinance SPOF/배치). 수정 방향은 사용자 결정 필요 → 별도 세션 |
| ~~B3 미체결 취소 버튼~~ | **기구현 확인** (MainDashboard.tsx handleCancelOrder → localAccount.cancelOrder, query invalidation 포함) |
| B1/B2 race condition | 재현 시나리오 미확인, 디버깅 세션 필요 |
| auth-extension | 사용자 결정 필요 (OAuth provider, 콜백 URL) |
| remote-ops | auth-extension 의존 |
| E2E 암호화 와이어링 | auth-extension 의존 (E2E 암호화 코드 자체는 구현 완료: local e2e_crypto.py + frontend e2eCrypto.ts + 디바이스 페어링) |
| KIS 분봉 e2e 테스트 | 실계좌 환경 필요 |

---

## 구현 순서

모든 Stage가 독립 — 순서 무관, 병렬 가능.

### Stage 1: F2 staleTime 잔여 전수 정리

이번 세션에서 7건 완료 → 잔여 ~24건 추가 설정.

**원칙**: 폴링 쿼리는 `staleTime ≈ refetchInterval / 2`. 정적 데이터는 용도별.

| 파일 | queryKey | refetchInterval | staleTime |
|------|----------|-----------------|-----------|
| `pages/StockList.tsx` | `watchlist` | — | 30_000 |
| `pages/StockList.tsx` | `watchlist-details` | — | 30_000 |
| `pages/StrategyList.tsx` | `lastRuleResults` | 10s | 5_000 |
| `pages/StrategyBuilder.tsx` | `rules` | — | 120_000 |
| `components/main/DetailView.tsx` | `symbol-timeline` | 30s | 15_000 |
| `components/main/PriceChart.tsx` | `fillLogs` (symbol별) | 30s | 15_000 |
| `components/main/OpsPanel.tsx` | `cloudHealth` | 10s | 5_000 |
| `components/main/OpsPanel.tsx` | `localHealth` | 10s | 5_000 |
| `components/main/OpsPanel.tsx` | `localStatus` | 10s | 5_000 |
| `components/main/OpsPanel.tsx` | `logSummary` | 30s | 15_000 |
| `components/main/OpsPanel.tsx` | `dailyPnl` | 30s | 15_000 |
| `components/DeviceManager.tsx` | `devices` | — | 30_000 |
| `pages/ExecutionLog.tsx` | `execution-logs` | 10s | 5_000 |
| `pages/ExecutionLog.tsx` | `log-summary` | 10s | 5_000 |
| `pages/ExecutionLog.tsx` | `execution-timeline` | 10s | 5_000 |
| `pages/ExecutionLog.tsx` | `alert-logs` | 10s | 5_000 |
| `pages/Admin/AiMonitor.tsx` | `admin.ai.stats` | 30s | 15_000 |
| `pages/Admin/AiMonitor.tsx` | `admin.ai.recent` | 30s | 15_000 |
| `pages/Admin/Dashboard.tsx` | `admin.stats` | 10s | 5_000 |
| `pages/Admin/Dashboard.tsx` | `admin.collector` | 10s | 5_000 |
| `pages/Admin/Dashboard.tsx` | `admin.ai.stats-summary` | 30s | 15_000 |
| `pages/Admin/Dashboard.tsx` | `admin.errors-recent` | 10s | 5_000 |
| `pages/Admin/ServiceKeys.tsx` | `admin.service-keys` | — | 60_000 |
| `pages/Admin/Stats.tsx` | `admin.stats.connections` | 30s | 15_000 |
| `pages/Admin/Templates.tsx` | `admin.templates` | — | 60_000 |
| `pages/Admin/Users.tsx` | `admin.users` | — | 30_000 |

**검증**: `npm run build` + `npm run lint` 통과

---

### Stage 2: Q5 장 상태 공휴일

`spec/phase-a-cleanup/plan.md` Step 4.

**수정 파일**:
1. `cloud_server/services/context_service.py` — `KOREAN_HOLIDAYS_2026` 상수 + `build_context()`에 `is_holiday` 추가
2. `frontend/src/types/dashboard.ts` — `MarketContextData.is_holiday?: boolean`
3. `frontend/src/pages/MainDashboard.tsx` — 주말/공휴일 → '휴장' 표시

---

### Stage 3: F3 프로필 닉네임 수정

`spec/phase-a-cleanup/plan.md` Step 5.

**수정 파일**:
1. `cloud_server/api/auth.py` — `PATCH /api/v1/auth/profile` (nickname 2~20자, 공백 trim)
2. `frontend/src/services/cloudClient.ts` — `cloudAuth.updateProfile()` 구현 (기존 스텁 교체)
3. `frontend/src/pages/Settings.tsx` — 닉네임 인라인 편집 + 저장 버튼 + 토스트

---

### ~~Stage 4: B3 미체결 취소 버튼~~ — 기구현 확인, 제거

> 2026-03-18 감사 결과: `MainDashboard.tsx:168-175`에 `handleCancelOrder` 완전 구현됨.
> `localAccount.cancelOrder(orderId)` 호출 + query invalidation 포함. ListView에 prop 전달 (line 228).

---

### Stage 4: R4 Heartbeat WS Ack 버전 파싱

relay-infra 완료로 의존성 해소.

**수정 파일**:
1. `local_server/cloud/ws_relay_client.py` — `_handle_heartbeat_ack()`에서 `rules_version`, `context_version` 추출
2. `local_server/cloud/heartbeat.py` — 버전 변경 감지 → fetch 트리거 콜백 연결

---

## 커밋 계획

| # | 메시지 | Stage |
|---|--------|-------|
| 1 | `feat: F2 staleTime 전수 정리 (잔여 ~24건)` | 1 |
| 2 | `feat: Q5 장 상태 공휴일 반영 (백엔드 is_holiday + 프론트 휴장)` | 2 |
| 3 | `feat: F3 프로필 닉네임 수정 (PATCH /auth/profile)` | 3 |
| 4 | `feat: R4 Heartbeat WS Ack 버전 파싱` | 4 |
| 5 | `docs: dev-plan-v3 + spec 상태 갱신` | 전체 |

---

## 완료 후 상태

### Phase A 졸업 기준
- [x] F1+ ErrorBoundary ✅ (이전 세션)
- [ ] F2 staleTime 전수 → Stage 1
- [ ] F3 닉네임 → Stage 3
- [ ] Q5 공휴일 → Stage 2
- [x] D1, D4 ✅ (이전 세션)
- [x] B3 취소 ✅ (기구현 확인, 2026-03-18 감사)
- [ ] B1, B2 — 별도 디버깅 세션
- [ ] `npm run build` + `npm run lint` 통과

→ **B1/B2 제외 Phase A 졸업 달성 (B3은 기구현)**

### T1-1 IndicatorProvider (별도 세션에서 결정 필요)
- 코드 기구현 (엔진 연동 완료)
- ❌ KOSDAQ 종목 `.KS` 오분류 (차단급) — exchange 매핑 방식 결정 필요
- ⚠️ yfinance SPOF — 폴백 소스 결정 필요 (클라우드 일봉 API? KIS REST?)
- ⚠️ 배치 요청 미최적화 — `yf.download(tickers=...)` 전환
