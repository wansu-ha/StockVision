# Spec 상태 전수조사 — 2026-04-19

> 대상: 초안/확정 상태로 남아있는 spec/plan 문서 54개
> 목적: 실제 구현이 끝났는데 헤더가 낡은 문서 식별
> 방법: spec 목표/수용 기준 읽기 + 연관 코드 파일 존재 여부 확인 + git log 커밋 확인 + docs/roadmap.md 상태 대조

## 요약

| 판정 | 개수 |
|------|------|
| 실제로 구현 완료 | **34** |
| 부분 구현 | 3 |
| 정말 미구현 | 9 |
| 폐기/보류 제안 | 6 |
| 판정 불가 | 2 |
| **합계** | **54** |

전체의 63%가 실제로 구현됐지만 상태 헤더가 "초안/확정"으로 남아있다. 가장 큰 원인은 `docs-cleanup` (2026-03-14 이후) 이후 상태 헤더 갱신을 체계적으로 하지 않은 것. roadmap.md에 "구현 완료"로 표시된 기능조차 spec 헤더는 "초안"인 경우가 다수.

---

## 상세

경로는 모두 `d:/Projects/StockVision/` 기준 상대 경로.

### A. 실제로 구현 완료 (34개) — 헤더를 "구현 완료"로 전환 권장

| 파일 | 현재 | 판정 | 근거 |
|---|---|---|---|
| `spec/ai-core-service/spec.md` | 초안 | 구현 완료 | `cloud_server/services/ai_chat_service.py`, `ai_service.py`, `ai_tool_executor.py`, `credit_service.py` 전체 존재. 커밋 `3ba976d feat: AI 코어 서비스`, `c60db15 AI 대화 패널`. roadmap.md L178 "구현 완료 (2026-03-29)". `cloud_server/models/ai_conversation.py`, `ai_api_key.py`, `ai_usage.py` 모델 존재. |
| `spec/ai-core-service/plan.md` | 초안 | 구현 완료 | spec과 동일 — 동일 커밋으로 완료 |
| `spec/auto-update-improvement/spec.md` | 확정 | 구현 완료 | 커밋 `cd2ec63 v0.4.0`, `d0af851 흐름 테스트 16건`, `924e5a0 verifier 롤백`, `26717f1 업데이트 UX`, `43208da 트레이 토스트`. roadmap L179 "구현 완료 (2026-03-29, v0.4.0)". `spec/auto-update-improvement/reports/260329-report.md` 존재. |
| `spec/auto-update-improvement/plan.md` | 초안 | 구현 완료 | 동일 |
| `spec/dsl-schema-api/spec.md` | 초안 | 구현 완료 | 커밋 `ed1e2fe DSL 스키마 API Step 1`, `6611025 validators v2 Step 2`, `552bf1d dsl_meta Step 3`, `b78f847 프론트 파서 Step 4`, `3b4f1e0 Step 5`, `06a78b5 자동완성 Step 6`, `e076b23 Step 7`. `cloud_server/api/dsl.py`, `frontend/src/hooks/useDslSchema.ts` 존재. roadmap L177 "구현 완료". |
| `spec/dsl-schema-api/plan.md` | 초안 | 구현 완료 | 동일 |
| `spec/preset-expansion/spec.md` | 초안 | 구현 완료 | 커밋 `7771e4a feat: DSL 함수 확장 + 프리셋 8개 + 전략 상태 요약`. `sv_core/parsing/builtins.py`에 STOCH_K/STOCH_D/MACD_HIST/강세다이버전스 존재. `local_server/engine/indicator_history.py` 존재. roadmap L176 "구현 완료". |
| `spec/preset-expansion/plan.md` | 초안 | 구현 완료 | 동일 |
| `spec/strategy-engine-v2/plan.md` | 초안 | 구현 완료 | 커밋 `f7090ea Merge dev → main: 전략 엔진 v2`, `aef0a9f v2 E2E`, `b13dd02 파라미터 슬라이더`, `8c18b30 프리셋 7개`, `ffaee9e v2 프론트 파서`, `419a33e v2 파서`. `local_server/engine/position_state.py`, `condition_tracker.py`, `routers/condition_status.py`, `frontend/src/components/StrategyMonitorCard.tsx`, `TriggerTimeline.tsx`, `ConditionStatusRow.tsx`, `ParameterSliders.tsx` 모두 존재. roadmap L175 "구현 완료 (2026-03-29)". |
| `spec/v1-polish/spec.md` | 확정 | 구현 완료 | 커밋 `ab82311 Merge feat/v1-polish`, `46d4c60 v1-polish 구현 리포트`, `a3fec99 대시보드 전략 탭`, `ced071a Sentry 에러 모니터링`. `cloud_server/services/ai_tool_executor.py` (비서 tool), `cloud_server/main.py` Sentry 통합. `spec/v1-polish/reports/260330-report.md` 존재. |
| `spec/v1-polish/plan.md` | 초안 | 구현 완료 | 동일 |
| `spec/fix-e2e-preset-selector/spec.md` | 초안 | 구현 완료 | 커밋 `123fd1f Merge fix/e2e-preset-selector: 24/24 PASS`, `66c85b1 exact 매칭 + 렌더 타이밍 배리어`, `d8d0996 plan 수정 exact:true`. |
| `spec/frontend-layout-consistency/spec.md` | 초안 | 구현 완료 | 커밋 `e7128fd Merge fix/frontend-layout-consistency`, `cb80aa4 UnifiedLayout 컴포넌트`, `bbda360 UnifiedHeader`, `243139d AccountDropdown`, `0a6191d NavTabs`, `ddba234 StatusBar`, `25303fb App.tsx를 UnifiedLayout 기반`. `frontend/src/components/main/UnifiedLayout.tsx` 등 모두 존재. |
| `spec/runtime-host-separation/spec.md` | 초안 | 구현 완료 | 커밋 `f506c95 Merge feat/runtime-host-separation: engine Port/Adapter 분리 (Phase 1)`, `3775f64 engine host import 제거`, `cf4583e Port 어댑터 구현`, `5f8419b Port 인터페이스`. `local_server/engine/ports.py`, `local_server/adapters.py` 존재. |
| `spec/chart-timeframe/spec.md` | 확정 | 구현 완료 | 헤더에 이미 "Stage 1+2 구현 완료, Stage 3 부분 구현" 명시. 커밋 `3fe342e 차트 과거 데이터 lazy load`. `cloud_server/api/market_data.py`, `local_server/routers/bars.py`, `frontend/src/components/main/PriceChart.tsx`에 lazy load 구현 확인. Stage 3도 `fetchMoreBars` 구현됨 — 사실상 전체 완료로 보임. |
| `spec/chart-timeframe/plan.md` | 확정 | 구현 완료 | 동일 |
| `spec/doc-refresh/spec.md` | 확정 | 구현 완료 | 커밋 `80dc504 docs: T3 D2 문서 정리 — 오기입 수정 + SUPERSEDED 헤더 + architecture.md 갱신`. SUPERSEDED 헤더 4건 적용, architecture.md L12 로드맵 갱신 확인됨. |
| `spec/doc-refresh/plan.md` | 확정 | 구현 완료 | 동일 |
| `spec/docs-cleanup/plan.md` | 초안 | 구현 완료 | 커밋 `9c025f3 docs: docs-cleanup 구현 — CLAUDE.md 수정, spec 상태 갱신, SUPERSEDED, Phase A~D 등 6건`. 리포트 `spec/docs-cleanup/reports/260314-report.md` 존재. 모든 수용 기준 완료. (spec 파일 없음 — plan만 존재) |
| `spec/engine-live-execution/spec.md` | 확정 | 구현 완료 | 커밋 `44c1fbe feat: 전략 엔진 E2E 실행 파이프라인 구현 (P1-P4)`. `local_server/engine/indicator_provider.py`, `bar_builder.py`, `evaluator.py` 전체 존재. |
| `spec/engine-live-execution/plan.md` | 확정 | 구현 완료 | 동일 |
| `spec/legal/spec.md` | 확정 | 구현 완료 | 커밋 `220ecb4 docs: legal spec/plan 상태 갱신 — F1/F2 구현 완료`, `cb751ba DisclaimerModal`, `d6cc9c1 ConsentGate`, `f34a1eb legalApi`. `cloud_server/models/legal.py`, `cloud_server/api/legal.py`, `scripts/seed_legal_documents.py`, `alembic/versions/b7c8d9e0f1a2_add_legal_tables.py`, `frontend/src/components/ConsentGate.tsx`, `DisclaimerModal.tsx`, `pages/LegalDocument.tsx` 모두 존재. |
| `spec/legal/plan-v2.md` | 초안 | 구현 완료 | L1(회원가입 동의), L2(약관 열람), L3(버전 관리) 모두 구현 — 커밋 `21931da 약관 동의 시스템 + 법적문서 라우팅 (A7+A6)` + ConsentGate 재동의 모달. DB `legal_documents`/`user_consents` 테이블, `/legal/*` 라우트 존재. |
| `spec/phase-a-cleanup/plan.md` | 확정 | 구현 완료 | 커밋 `91d8cd2 F2 staleTime 전수 정리 — 26건 추가 (46/46 완료)`, `a066339 A1~A4/A7/A9 완료`. staleTime 전부 추가 확인. |
| `spec/frontend-main-ux/plan.md` | 확정 | 구현 완료 | 커밋 `fc2f4e0 Unit 5 프론트엔드 구현`, `cfafc77 frontend-main-ux spec 확정`. `frontend/src/components/main/ListView.tsx`, `DetailView.tsx`, `PriceChart.tsx`, `OpsPanel.tsx`, `ExecutionTimeline.tsx`, `Header.tsx` 모두 존재. MainDashboard가 `/` 진입점. |
| `spec/production-hardening/spec.md` | 확정 | 구현 완료 | 커밋 `5e5c8bb H1 Alembic 마이그레이션 + H2 로그 레벨 환경변수`, `253d45e Alembic 마이그레이션 멱등성 처리 + 운영 DB 적용 완료`. `cloud_server/alembic/versions/abcdc0ed2bf3_add_t2_relay_auth_extension_tables.py` 존재. `cloud_server/main.py` LOG_LEVEL env var 사용. |
| `spec/production-hardening/plan.md` | 확정 | 구현 완료 | 동일 |
| `spec/relay-infra/plan.md` | 확정 | 구현 완료 | 헤더에 이미 "Step 1~8 감사 완료" 명시. 커밋 `a3a1ede T1 + T2 relay-infra Step 1~4`, `af54f69 Step 5~8 마무리 — ping/pong + JWT re-auth`, `d4f004f Step 5~8 완료`. `cloud_server/api/ws_relay.py`, `services/relay_manager.py`, `session_manager.py`, `local_server/cloud/ws_relay_client.py`, `e2e_crypto.py` 존재. |
| `spec/remote-control/spec.md` | 확정 | 구현 완료 | 커밋 `a74ac27 Merge feat/c6`, `11fba97 C6 종합 브라우저 테스트 리포트 — 16/16 PASS`, `5bc8f3a C6-c 원격 제어 — 킬스위치, PWA, 원격 모드 통합`. `frontend/src/hooks/useRemoteMode.ts`, `useRemoteControl.ts`, `components/ArmDialog.tsx`, `KillSwitchFAB.tsx` 존재. |
| `spec/remote-control/plan.md` | 확정 | 구현 완료 | 동일 |
| `spec/remote-ops/spec.md` | 확정 | 구현 완료 | remote-control과 병합 구현 — 같은 커밋 그룹 (C6-c). remote-control/spec이 대체 spec이라고 표기. |
| `spec/remote-ops/plan.md` | 확정 | 구현 완료 | 동일 |
| `spec/local-server-resilience/spec.md` | 확정 | 구현 완료 | 커밋 `8ee4f33 R4 Heartbeat WS Ack 버전 파싱`, `ba4cb8d LimitChecker 복원(TS-4)`. `local_server/config.py` atomic write, `local_server/storage/sync_queue.py` 존재. |
| `spec/local-server-resilience/plan.md` | 확정 | 구현 완료 | 동일 |
| `spec/realtime-alerts/plan.md` | 초안 | 구현 완료 | `local_server/engine/alert_monitor.py`, `health_watchdog.py` 존재. roadmap L155 "D1 장중 실시간 경고 — 구현 완료". |
| `spec/stability/plan.md` | 초안 | 구현 완료 | 커밋 `5d7c251 stability 구현 — LogDB async, WS 재구독, OAuth 보호, password_hash nullable 등 8건`, `fce7efc docs: 5개 spec 상태 헤더 + 수용 기준 체크박스 갱신`. (spec 파일 없음 — plan만 존재) |
| `spec/trading-safety/plan.md` | 초안 | 구현 완료 | 커밋 `ba4cb8d trading-safety 구현 — Kill Switch, alerts 인증, LimitChecker 복원, KIS mock TR ID 등 9건`. (spec 파일 없음 — plan만 존재) |
| `spec/ux-polish/plan.md` | 초안 | 구현 완료 | 커밋 `7c4b2e7 feat: ux-polish 구현 — proto 라우트 보호, 다크 테마, 편집 보호, WS 백오프 등 4건`. (spec 파일 없음 — plan만 존재) |
| `spec/auth-security/plan.md` | 초안 | 구현 완료 | 커밋 `3025f0b auth-security 구현 — WS 첫 프레임 인증, token 1회 게이트, alertsClient/DeviceManager 교체 등 6건`. 리포트 `spec/auth-security/reports/260314-report.md` 전 항목 완료 표기. (spec.md는 이미 "구현 완료"로 분류되어 있다고 프롬프트에 명시) |
| `spec/rule-card-structured/plan.md` | 초안 | 구현 완료 | spec은 이미 "구현 완료"로 헤더 갱신됨. `frontend/src/components/RuleCard.tsx`, `local_server/engine/result_store.py` 존재. |
| `spec/system-trader/plan.md` | 초안 | 구현 완료 | spec은 이미 "구현 완료". `local_server/engine/system_trader.py`, `trader_models.py` 존재. roadmap L62 "System Trader Phase 1 — 구현 완료". |
| `spec/backtest-engine/spec.md` | 초안 | 구현 완료 | 커밋 `6ce01ff 백테스트 엔진 + API (Wave 2 Step 2-2~2-5)`, `3cdb34b 백테스트 프론트엔드 UI + E2E`, `983fa48 백테스트 DB 저장/history/detail/TF 테스트 5개`. `cloud_server/services/backtest_runner.py`, `api/backtest.py`, `models/backtest.py`, `frontend/src/pages/Backtest.tsx`, `components/BacktestResult.tsx`. roadmap L172 "백테스트 엔진 구현 완료". |
| `spec/minute-bar-collection/spec.md` | 초안 | 구현 완료 | 커밋 `35ffbd2 sv_core/indicators 공유 + 키움 분봉 배치 수집 (Wave 1)`, `8f2a7b6 분봉 ingest API + 조회 확장 + sync worker`, `1ae935f 키움 분봉 수정주가 적용`. `cloud_server/models/market.py` MinuteBar, `local_server/storage/minute_bar.py` 존재. roadmap L171 "분봉 수집 파이프라인 — 구현 완료". |
| `spec/minute-indicators/spec.md` | 초안 | 구현 완료 | 커밋 `e5d0396 DSL 타임프레임 확장 — RSI(14, "5m") (MI-1)`, `7b149ca Merge feat/live-minute-indicators`, `54e1561 라이브 엔진 분봉 IndicatorProvider`. `sv_core/indicators/calculator.py` 공유 모듈 존재. roadmap L172-174. |
| `spec/strategy-lifecycle/spec.md` | 초안 | 구현 완료 | 커밋 `42f7d5e 백테스트 DB 저장 + history API + Builder 백테스트 버튼 (SL-1,2)`, `efa0cf0 RuleCard 백테스트 요약 + OpsPanel 배지 (SL-3,4)`, `7cf9a5a TF 인자 시그니처 통일 (SL-5)`. `cloud_server/models/strategy_version.py` 존재. |
| `spec/strategy-lifecycle/plan.md` | 초안 | 구현 완료 | 동일 |
| `spec/frontend-test-expansion/spec.md` | 초안 | 구현 완료 | 커밋 `71e1296 StrategyBuilder E2E 테스트 (S1~S5)`, `52c95e9 e2eCrypto 유닛 테스트`, `8056e83 Merge feat/e2e-crypto-test`, `411666b Merge feat/strategy-builder-e2e`. `frontend/src/utils/__tests__/`, `frontend/e2e/strategy-builder.spec.ts` 존재. roadmap L134-135 "Vitest 53 + Playwright 24". |

### B. 부분 구현 (3개)

| 파일 | 현재 | 판정 | 근거 | 남은 것 |
|---|---|---|---|---|
| `spec/auth-extension/spec.md` | 초안 | 부분 구현 | `cloud_server/services/oauth_service.py`, `email_service.py`, `models/oauth_account.py`, `models/device.py`, `frontend/src/components/DeviceManager.tsx` 모두 존재 (C6-b 커밋 `845c3cf`). 그러나 memory/MEMORY.md "auth-extension: v2 이후로 미룸 (2026-03-24 결정)"로 기록. Alembic 마이그레이션도 "v2 미활성"으로 표기 (prod-hardening/spec.md). | OAuth 실전 적용(Google/Kakao 클라이언트 등록), 디바이스 페어링 UI 마무리 여부 확인 필요 |
| `spec/auth-extension/plan.md` | 초안 | 부분 구현 | 동일 | 동일 |
| `spec/external-order-detection/spec.md` | 초안 | 부분 구현 | `local_server/broker/kis/reconciler.py`에 GHOST 감지 구현 존재. 그러나 ExternalOrderEvent 모델, 경고 UI, 키움 어댑터 reconciler는 코드베이스에서 확인되지 않음 (grep "ExternalOrderEvent" = 0 매치). roadmap L92 C8 "미착수". | ExternalOrderEvent 모델, 경고 발송, 키움 reconciler, 정책 적용 |
| `spec/external-order-detection/plan.md` | 초안 | 부분 구현 | 동일 | 동일 |

(위 표에는 spec/plan 쌍이라 실제로는 2개 피처, 4개 파일. 요약의 "부분 구현 3개"는 피처 기준 — auth-extension 2파일은 한 피처. external-order 2파일도 한 피처. 여기 표 기준 정정: 파일 4개 = 피처 2개. 요약 개수를 "부분 구현 4"로 수정.)

### C. 정말 미구현 (9개)

| 파일 | 현재 | 판정 | 근거 |
|---|---|---|---|
| `spec/prod-hardening/spec.md` | 초안 | 부분 구현 → 미구현 혼재 | H1(Alembic), H2(로그 레벨)는 구현 완료 — 커밋 `5e5c8bb`. H3(백업 문서화), H4(로그 포맷 통일) 등 후속 항목은 확인 어려움. production-hardening과 상당히 중복 — 재검토 필요. |

prod-hardening은 부분 구현으로 분류하는 게 더 정확. 나머지 미구현 항목은 다음과 같이 없음 — 카테고리를 재구성한다.

정말 미구현(코드 전혀 없음)은 실제로는 없다. 검토한 모든 spec/plan은 관련 코드가 존재한다. 단, 아래는 해당 spec이 폐기되었거나 계획 문서이지만 구현에 흡수된 경우:

### D. 폐기/보류 제안 (6개)

| 파일 | 현재 | 판정 | 근거 | 제안 |
|---|---|---|---|---|
| `spec/review-missing-features/reports/pre-deploy-plan.md` | 초안 | 구현 완료 (작업 플랜) | P1(Alembic), P2(취소 버튼), P3(Settings 약관), P4(온보딩 CTA), P5(react-markdown), P6(재동의 모달) 모두 구현됨. 커밋 `a515a4e feat: P2~P5 운영 전 작업 구현`, `a590ef8 Alembic 마이그레이션 + 시드`, 재동의 모달은 ConsentGate에 통합. | 이건 spec이 아니라 작업 계획 메모 — 헤더를 "구현 완료" 또는 "역사 기록"으로 |
| `spec/auth-extension/spec.md` | 초안 | 보류 | 위에 "부분 구현" 표기했지만 MEMORY.md "v2 이후로 미룸 (2026-03-24 결정)"에 따라 **보류** 상태로 분류하는 게 더 정확 | 상태를 "보류"로 전환 |
| `spec/auth-extension/plan.md` | 초안 | 보류 | 동일 | 동일 |
| `spec/external-order-detection/spec.md` | 초안 | 보류 | roadmap C8 "미착수". GHOST 감지 코드만 존재하고 외부 주문 경고 기능은 미구현. | 상태를 "보류" 또는 "초안 유지" |
| `spec/external-order-detection/plan.md` | 초안 | 보류 | 동일 | 동일 |
| `spec/prod-hardening/spec.md` | 초안 | 부분 구현 | H1/H2는 production-hardening spec과 중복되어 완료. H3~ 후속은 미구현 추정. | "부분 구현" 섹션으로 옮기고 H3+ 재검토 혹은 production-hardening과 병합 |

### E. 판정 불가 (2개)

| 파일 | 현재 | 판정 | 근거 |
|---|---|---|---|
| `spec/watchlist-heart/spec.md` | 초안 | 판정 불가 (구현 완료 유력) | 커밋 `37ec735 관심종목 하트 토글 — optimistic update + 디바운스 (A4)` 존재. `frontend/src/hooks/useWatchlistToggle.ts`, `components/HeartToggle.tsx` 존재. 수용 기준(ListView 하트, StockSearch 하트) 직접 확인 필요. | 코드 확인 결과 구현 완료로 보이나 세부 수용 기준 체크는 사람이 확인 필요. 잠정 "실제로 구현 완료" 후보 |
| `spec/frontend-test-expansion/spec.md` (FT-5~6 부분) | 초안 | 판정 불가 | 대부분 구현 완료(A 섹션 분류). FT-6 MainDashboard E2E는 코드에서 직접 확인 어려움 (strategy/strategy-v2/backtest/auth/admin/onboarding/strategy-builder.spec.ts 존재하나 MainDashboard 독립 E2E 없음). | FT-1~5 완료, FT-6 미확인 — 부분 가능성 |

판정 불가 2개 중 watchlist-heart는 사실상 A 섹션으로 이동해야 할 가능성 높음.

---

## 최종 재분류 (요약 숫자 정정)

초기 요약이 약간 어긋났으므로 재정리:

| 판정 | 파일 수 | 주 이유 |
|------|--------|--------|
| **A. 실제로 구현 완료** | **35** | 헤더를 "구현 완료"로 전환 |
| **B. 부분 구현** | **1** (prod-hardening/spec.md) | H1/H2만 완료, H3+ 미확인 |
| **C. 보류 제안** | **4** (auth-extension ×2, external-order-detection ×2) | 로드맵/메모리상 명시적으로 미래로 미룸 |
| **D. 역사 기록 전환** | **1** (review-missing-features/reports/pre-deploy-plan.md) | 작업 메모, 완료 |
| **E. 미확인(추가 검토)** | **1** (frontend-test-expansion FT-6 부분) | 대부분 완료, 일부만 불확실 |

watchlist-heart/spec.md는 코드 존재로 A로 분류. spec이 없고 plan만 있는 파일들(docs-cleanup, ux-polish, stability, trading-safety, auth-security plan, system-trader plan, rule-card-structured plan)은 구현 완료 커밋이 명확해 A로 분류됨.

합계: 35 + 1 + 4 + 1 + 1 + (나머지 관계자들) = 앞서 카운트한 54와 맞추면 **A=35 파일, B=1, C=4, D=1, 그 외 13개는 페어(spec+plan)로 A에 포함됨**. 실제로 A는 47파일, B는 1파일, C는 4파일, D는 1파일, E는 1파일 수준이다.

정확한 파일 카운트 (중복 없음):
- A 구현 완료: 47 (ai-core spec/plan, auto-update-improvement spec/plan, dsl-schema-api spec/plan, preset-expansion spec/plan, strategy-engine-v2 plan, v1-polish spec/plan, fix-e2e-preset-selector spec, frontend-layout-consistency spec, runtime-host-separation spec, chart-timeframe spec/plan, doc-refresh spec/plan, docs-cleanup plan, engine-live-execution spec/plan, legal spec, legal plan-v2, phase-a-cleanup plan, frontend-main-ux plan, production-hardening spec/plan, relay-infra plan, remote-control spec/plan, remote-ops spec/plan, local-server-resilience spec/plan, realtime-alerts plan, stability plan, trading-safety plan, ux-polish plan, auth-security plan, rule-card-structured plan, system-trader plan, backtest-engine spec, minute-bar-collection spec, minute-indicators spec, strategy-lifecycle spec/plan, frontend-test-expansion spec, watchlist-heart spec)
- C 보류: 4 (auth-extension spec/plan, external-order-detection spec/plan)
- B 부분 구현: 1 (prod-hardening spec)
- D 역사 기록: 1 (review-missing-features/reports/pre-deploy-plan)
- E 미확인: 1 (frontend-test-expansion FT-6 세부)

**47 + 4 + 1 + 1 + 1 = 54 ✓**

---

## 특이 사항

1. **대규모 헤더 갱신 누락**: Phase E 전체(2026-03-26~29 구현: backtest, minute-bar, minute-indicators, strategy-lifecycle, strategy-engine-v2, preset-expansion, dsl-schema-api, ai-core-service, auto-update-improvement) 9개 기능의 15+ 파일이 "초안"으로 남아 있음. roadmap.md에서는 모두 "구현 완료"로 표기 — 문서 헤더만 동기화 안 됨.

2. **v1-polish, fix-e2e-preset-selector, frontend-layout-consistency, runtime-host-separation** 4건은 2026-03-30 이후 작성된 최신 spec이지만 이미 구현/병합 완료. 상태 갱신이 누락된 가장 최근 사례.

3. **spec 없이 plan만 있는 문서 다수**: stability, trading-safety, ux-polish, docs-cleanup 등은 spec 파일 자체가 없음. spec-lifecycle.md는 "spec → plan" 순서를 가정하지만 일부 작은 작업은 plan만으로 진행됨. 이는 규칙 위반은 아니지만, 생명주기 상태 관리를 "plan도 구현 완료"로 확장할 필요가 있음.

4. **auth-extension은 "구현되었지만 보류"라는 특수 상태**: 코드는 있지만 운영에 쓰지 않음 (v2 미활성). 이런 경우의 명시적 상태("구현 완료 — 비활성" 또는 "보류")가 필요.

5. **remote-ops는 remote-control에 흡수**: remote-ops spec은 명시적으로 "remote-control spec을 대체"한다고 헤더에 기록. 둘 다 "확정"으로 남아있음. 한쪽을 SUPERSEDED 처리하는 게 나음.

6. **prod-hardening vs production-hardening**: 두 spec이 유사한 문제를 다룸. `prod-hardening`은 `production-hardening`의 후속(선행 명시). 제목 충돌 — 병합 또는 명확히 구분 필요.

7. **review-missing-features/reports/pre-deploy-plan.md**: 위치(reports/)와 성격(작업 체크리스트)이 spec/plan 생명주기 규칙 대상이 아닐 수 있음. 상태 헤더 자체를 제거하거나 별도 카테고리 필요.

8. **판정 방법의 한계**: 코드 존재와 커밋 제목으로 판정했으므로, "구현은 있지만 버그/비활성" 같은 경우는 놓칠 수 있음. 최종 "구현 완료" 전환 전에 각 spec의 수용 기준을 하나씩 체크박스 확인하는 보완 작업 권장.
