# 코드-문서 전수 감사 결과

> 작성일: 2026-03-18 | 목적: 구현 현황과 문서 상태 간 불일치 전수 정리

---

## 감사 방법

1. 코드베이스 전체 grep/glob으로 각 항목의 실제 구현 여부 검증
2. 관련 문서(dev-plan-v3, spec, plan)의 상태 표기와 비교
3. 불일치 발견 시 문서 수정

---

## 불일치 발견 및 수정 사항

### 1. B3 미체결 취소 버튼 — 문서: "stub" → 실제: **완전 구현**

- **문서 기록**: A1 B3 "onClick 없음, PendingOrder.orderId 타입 누락"
- **실제 코드**: `MainDashboard.tsx:168-175` — `handleCancelOrder` 완전 구현
  - `localAccount.cancelOrder(orderId)` 호출
  - query invalidation (`openOrders`, `fillLogs`) 포함
  - ListView에 prop 전달 (line 228)
- **조치**: dev-plan-v3 A1 B3 상태 → "✅ 기구현 확인", Sprint plan에서 Stage 4 제거

### 2. F2 staleTime — 문서: "잔여 ~5건" → 실제: **~24건 잔여**

- **문서 기록**: "15/20+ 쿼리 설정", "잔여 ~5건"
- **실제 코드**: 전체 ~38개 useQuery 중 14개만 staleTime 설정됨
  - **설정 완료 (14)**: useAccountBalance(2), useAccountStatus(1), useMarketContext(1), useStockData(4), MainDashboard(2), MarketContext(1), BriefingCard(1), StockAnalysisCard(1), StrategyList rules(1)
  - **미설정 (~24)**: StrategyBuilder(1), StockList(2), StrategyList(2), ExecutionLog(4), OpsPanel(3+), DeviceManager(1), DetailView(1), Admin/Dashboard(4), Admin/AiMonitor(2), Admin/ServiceKeys(1), Admin/Templates(1), Admin/Stats(1), Admin/Users(1)
- **조치**: 모든 문서의 staleTime 수치 정정, Sprint Stage 1에 ~24건 반영

### 3. E2E 암호화 — 문서: "PARTIAL" → 실제: **대부분 구현**

- **문서 기록**: "encrypt_for_all 와이어링은 auth-extension 후"
- **실제 코드**:
  - `local_server/cloud/e2e_crypto.py` — AES-256-GCM 완전 구현 (generate_key, encrypt/decrypt, encrypt_for_all, 디바이스 키 관리)
  - `frontend/src/utils/e2eCrypto.ts` — Web Crypto API 기반 복호화 + IndexedDB 키 저장
  - `local_server/routers/devices.py` — QR 기반 디바이스 페어링 (pair/init, pair/complete)
  - `frontend/src/hooks/useRemoteControl.ts` — E2E 복호화 통합
  - `sv_core/e2e_crypto.py` — 미존재 (의도적: local/frontend 독립 구현)
- **조치**: dev-plan-v3 relay-infra Step 6 상세 설명 보강

### 4. T1-1 IndicatorProvider — 문서 정확 (⚠️ 기구현, 차단급 버그)

- 코드: `indicator_provider.py` 189줄, `engine.py:322` 연동
- KOSDAQ `.KS` 오분류 (line 98), yfinance SPOF — 문서와 일치
- **조치**: 변경 없음 (이미 정확)

---

## 미구현 확인 항목 (Sprint 대상)

| 항목 | 코드 근거 |
|------|----------|
| F3 프로필 닉네임 | `cloudClient.ts:88-90` console.warn 스텁, `auth.py`에 PATCH 없음, Settings에 UI 없음 |
| Q5 장 상태 공휴일 | `context_service.py`에 is_holiday 없음, `MainDashboard.tsx`에 주말 로직 없음 |
| R4 Heartbeat Ack 파싱 | `ws_relay_client.py` `_handle_heartbeat_ack()` → `logger.debug("heartbeat_ack 수신")` 뿐 |
| F2 staleTime ~24건 | 위 상세 목록 참조 |

---

## 구현 완료 확인 항목 (문서와 일치)

| 항목 | 상태 |
|------|------|
| F1+ ErrorBoundary route reset | ✅ `App.tsx:58` `key={location.pathname}` |
| D1 Plan constants | ✅ `config.py:96-97` |
| D4 AlertSettings channel | ✅ `AlertSettings.tsx:111` |
| T1-2 DSL parser | ✅ `dslParser.ts` + `dslConverter.ts` |
| T1-3 Chart backend | ✅ `minute_bar.py`, `bars.py`, `market_data.py` |
| T1-4 Chart frontend | ✅ `PriceChart.tsx` resolution + lazy load |
| T1-5 R1~R3, R5 | ✅ atomic write, auto-detect, sync_queue, limit_checker restore |
| relay-infra Steps 1-8 | ✅ 전부 구현 (ping/pong, JWT re-auth 포함) |
| E2E crypto (코드) | ✅ local + frontend + device pairing 구현 (와이어링만 auth 후) |
| Session manager | ✅ ping/pong, JWT expiry tracking |

---

## 수정된 문서

1. `docs/development-plan-v3.md` — B3 상태, F2 수치, E2E 상세, 커밋 전략 잔여 목록
2. `spec/immediate-dev-sprint/plan.md` — B3 제거(v3), staleTime ~24건 정정, E2E 설명 보강
3. `spec/phase-a-cleanup/spec.md` — F2 전체 현황 정정
