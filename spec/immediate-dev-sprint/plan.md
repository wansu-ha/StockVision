# 즉시 착수 개발 스프린트 — 구현 계획서

> 작성일: 2026-03-18 | 상태: 초안

## 목표

외부 의존성 없이 즉시 착수 가능한 개발 항목을 일괄 처리한다.
Phase A 졸업 잔여 + T1 엔진 핵심 + staleTime 전수 정리 + R4 Heartbeat.

---

## 범위

### 포함 (6건)

| # | 항목 | 출처 | 복잡도 | Spec/Plan |
|---|------|------|--------|-----------|
| 1 | F2 staleTime 전수 정리 (~20건) | A6/A8 | trivial ×20 | `spec/frontend-quality/spec.md` |
| 2 | F3 프로필 닉네임 수정 | A6 | small | `spec/phase-a-cleanup/plan.md` Step 5 |
| 3 | Q5 장 상태 공휴일 | A8 | small | `spec/phase-a-cleanup/plan.md` Step 4 |
| 4 | T1-1 IndicatorProvider | T1 | large | `spec/engine-live-execution/plan.md` S2~S3 |
| 5 | R4 Heartbeat WS Ack 버전 파싱 | T1-5/T2 | small | `spec/local-server-resilience/spec.md` R4 |
| 6 | B3 미체결 취소 버튼 연결 | A1 | small | `docs/development-plan-v3.md` B3 |

### 제외

- B1/B2 (AuthContext/useStockData race condition) — 재현 시나리오 미확인, 디버깅 세션 필요
- auth-extension — 사용자 결정 필요 (OAuth provider 등)
- remote-ops — auth-extension 의존
- E2E 암호화 와이어링 — auth-extension 의존
- KIS 분봉 e2e 테스트 — 실계좌 환경 필요

---

## 구현 순서

의존성 체인: `1 → 2 → 3 → 6` (독립), `4 → 5` (4 먼저, 5는 4와 병렬 가능)

### Stage 1: staleTime 전수 정리 (기계적 작업)

이번 세션에서 7건 완료 → 잔여 ~20건. 폴링 쿼리 중심으로 전수 적용.

**원칙**: `staleTime = refetchInterval / 2` (반값). 폴링 없는 정적 데이터는 용도별 설정.

| 파일 | queryKey | refetchInterval | staleTime |
|------|----------|-----------------|-----------|
| `pages/StockList.tsx` | `watchlist` | — | 30_000 |
| `pages/StockList.tsx` | `watchlist-details` | — | 30_000 |
| `pages/StrategyList.tsx` | `lastRuleResults` | 10s | 5_000 |
| `pages/StrategyBuilder.tsx` | `rules` | — | 120_000 |
| `components/main/DetailView.tsx` | `symbol-timeline` | 30s | 15_000 |
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
| `pages/ExecutionLog.tsx` | `execution-logs` | 10s | 5_000 |
| `pages/ExecutionLog.tsx` | `log-summary` | 10s | 5_000 |
| `pages/ExecutionLog.tsx` | `execution-timeline` | 10s | 5_000 |
| `pages/ExecutionLog.tsx` | `alert-logs` | 10s | 5_000 |
| `components/main/OpsPanel.tsx` | `cloudHealth` | 10s | 5_000 |
| `components/main/OpsPanel.tsx` | `localHealth` | 10s | 5_000 |
| `components/main/OpsPanel.tsx` | `localStatus` | 10s | 5_000 |
| `components/main/OpsPanel.tsx` | `logSummary` | 30s | 15_000 |
| `components/main/OpsPanel.tsx` | `dailyPnl` | 30s | 15_000 |
| `components/main/PriceChart.tsx` | `fillLogs` (symbol) | 30s | 15_000 |
| `components/DeviceManager.tsx` | `devices` | — | 30_000 |

**검증**: `npm run build` + `npm run lint` 통과

---

### Stage 2: Q5 장 상태 공휴일

`spec/phase-a-cleanup/plan.md` Step 4 그대로 실행.

**수정 파일**:
1. `cloud_server/services/context_service.py` — `KOREAN_HOLIDAYS_2026` 상수 + `build_context()`에 `is_holiday` 추가
2. `frontend/src/types/dashboard.ts` — `MarketContextData.is_holiday?: boolean`
3. `frontend/src/pages/MainDashboard.tsx` — 주말/공휴일 → '휴장' 표시

**검증**: 프론트 빌드 통과, 백엔드 import 에러 없음

---

### Stage 3: F3 프로필 닉네임 수정

`spec/phase-a-cleanup/plan.md` Step 5 그대로 실행.

**수정 파일**:
1. `cloud_server/api/auth.py` — `PATCH /api/v1/auth/profile` (nickname 1~50자)
2. `frontend/src/services/cloudClient.ts` — `cloudAuth.updateProfile()` 구현
3. `frontend/src/pages/Settings.tsx` — 닉네임 input + 저장 버튼

**검증**: 프론트 빌드 + 린트 통과

---

### Stage 4: B3 미체결 취소 버튼

**현재**: `ListView.tsx`에 취소 버튼이 있으나 onClick 없음, orderId 타입 누락.

**수정 파일**:
1. `frontend/src/types/` — PendingOrder에 `orderId` 필드 추가
2. `frontend/src/components/main/ListView.tsx` — onClick → 로컬 서버 취소 API 호출
3. `frontend/src/services/localClient.ts` — 취소 API 함수 추가 (있다면 확인)

**검증**: 빌드 통과, 타입 에러 없음

---

### Stage 5: T1-1 IndicatorProvider (핵심)

`spec/engine-live-execution/plan.md` S2~S3 실행.

**Step 5-1**: 의존성 추가
- `local_server/requirements.txt`에 `pandas`, `yfinance` 추가

**Step 5-2**: IndicatorProvider 구현
- `local_server/engine/indicator_provider.py` (신규)
- pandas 기반 지표 계산: RSI, SMA, EMA, MACD, 볼린저, 평균거래량
- yfinance로 60일 일봉 조회 (한국 종목: `.KS`/`.KQ`)
- 1일 캐시 (장중 일봉 지표 불변)

**Step 5-3**: 엔진 연동
- `local_server/engine/engine.py` — IndicatorProvider 초기화 + evaluate 시 지표 주입

**Step 5-4**: Heartbeat 버전 비교 수정
- `local_server/cloud/heartbeat.py` — `rules_version` 비교 시 `str()` 통일

**검증**: `indicator_provider.get("005930")` → `rsi_14` 값이 float 반환

---

### Stage 6: R4 Heartbeat WS Ack 버전 파싱

relay-infra 완료로 의존성 해소. `ws_relay_client.py`의 `_handle_heartbeat_ack` 수정.

**수정 파일**:
1. `local_server/cloud/ws_relay_client.py` — ack 메시지에서 `rules_version`, `context_version` 추출
2. `local_server/cloud/heartbeat.py` — 버전 변경 감지 콜백 호출

**검증**: heartbeat_ack 수신 시 버전 변경 감지 로그 확인

---

## 커밋 계획

| # | 메시지 | Stage |
|---|--------|-------|
| 1 | `feat: staleTime 전수 정리 (~20건)` | 1 |
| 2 | `feat: Q5 장 상태 공휴일 반영` | 2 |
| 3 | `feat: F3 프로필 닉네임 수정 (PATCH /auth/profile)` | 3 |
| 4 | `fix: B3 미체결 취소 버튼 연결` | 4 |
| 5 | `feat: T1-1 IndicatorProvider 지표 계산 모듈` | 5 |
| 6 | `feat: R4 Heartbeat WS Ack 버전 파싱` | 6 |
| 7 | `docs: dev-plan-v3 + spec 상태 갱신` | 전체 |

---

## 예상 공수

| Stage | 예상 |
|-------|------|
| 1 (staleTime) | 기계적 — 짧음 |
| 2 (Q5 공휴일) | 짧음 |
| 3 (F3 닉네임) | 보통 (백엔드+프론트) |
| 4 (B3 취소버튼) | 짧음 |
| 5 (IndicatorProvider) | 가장 큼 (신규 모듈) |
| 6 (R4 Heartbeat) | 짧음 |

---

## 완료 후 Phase A / T1 상태

### Phase A
- [x] F1+ ErrorBoundary 라우트 리셋 ✅
- [x] F2 staleTime 전수 설정 → Stage 1에서 완료
- [x] F3 프로필 닉네임 → Stage 3에서 완료
- [x] Q5 공휴일 장 상태 → Stage 2에서 완료
- [x] D1, D4 ✅
- [x] B3 미체결 취소 → Stage 4에서 완료
- [ ] B1, B2 (race condition) — 별도 디버깅 세션
- [x] `npm run build` 경고 없음
- [x] `npm run lint` 통과

→ **B1/B2 제외 Phase A 졸업 달성**

### T1
- [x] T1-1 IndicatorProvider → Stage 5에서 완료
- [x] T1-2 DSL 파서 ✅
- [x] T1-3 차트 백엔드 ✅
- [x] T1-4 차트 프론트 (lazy load 포함) ✅
- [x] T1-5 R1~R3, R5 ✅
- [x] R4 Heartbeat WS Ack → Stage 6에서 완료

→ **T1 완료 달성** (E2E 검증은 모의서버 환경에서 별도)
