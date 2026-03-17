# StockVision 개발 계획서 v3 — 기술 구현 백로그

> 작성일: 2026-03-15 | 갱신: 2026-03-17 | 상태: 확정
> 선행: `docs/development-plan-v2.md` (3프로세스 전환), `spec/review-missing-features/report.md` (교차검증)
>
> **정본 관계**: Phase 현황과 사용자 가치 기준 로드맵은 `docs/roadmap.md`가 정본이다.
> 이 문서는 **기술 구현 백로그**로, roadmap.md의 Phase(A~E)와 다른 축(A → T1 → T2 → T3)으로 기술 항목을 조직한다.
> roadmap Phase와 이 문서의 단계는 1:1 대응이 아니며, 각자의 관점에서 독립적으로 추적한다.
>
> **2026-03-17 갱신**: A1~A4, A5(U2~U5/S1~S3 기구현 확인), A6(F1+F2), A7, A9 구현 완료. D1~D6 결정 완료. Alembic+시드 적용. 로컬 서버 v0.1.3 릴리스.

---

## 1. 전체 요약

| 단계 | 기간 (예상) | 핵심 목표 | 주요 항목 수 |
|------|-----------|----------|------------|
| **A** | 2-3주 | 기반 안정화 + Phase A 졸업 | ~50건 |
| **T1** | 3-4주 | 엔진 완성 + DSL + 차트 확장 | ~40건 |
| **T2** | 5-7주 | 릴레이 인프라 + 원격 제어 보강 | ~35건 |
| **T3** | 런칭 전 | 제품 미결정 + 문서 정리 + 하드닝 | ~15건 |
| v2 | 런칭 후 | 백테스팅, 리밸런싱, 2FA 등 | ~7건 |

**총계: ~164건** (버그 4, UI 갭 7, 품질 7, 보안 9, 법무 15, Spec 미충족 ~100, 미결정 6, v2 7)

---

## 2. Phase A — 기반 안정화 + 졸업 블로커 (2-3주)

### 목표
- Phase A 졸업 블로커 전부 해결
- 보안 기본 사항 (rate limit, token, soft-delete, 비밀번호) 적용
- 법무 프레임워크 구축 (약관/면책/개인정보)
- 관심종목 UX 개선

### Week 1 — 버그 수정 + 보안 + 어댑터

모두 **독립** 작업으로 병렬 진행 가능.

#### A1. Phase A 버그 수정 (4건) — ✅ 구현 완료 (2026-03-16)

| # | 버그 | 파일 | 심각도 |
|---|------|------|--------|
| B1 | AuthContext setState 경쟁 조건 — RT 갱신 시 `localReady=false` 리셋 | `AuthContext.tsx` | 🔴 |
| B2 | useStockData quotesQuery/namesQuery 클로저 race condition | `useStockData.ts` | 🔴 |
| B3 | 미체결 "취소" 버튼 stub — onClick 없음, PendingOrder.orderId 타입 누락 | `ListView.tsx` | 🟡 |
| B4 | Settings 키 등록 후 localStatus 캐시 미갱신 (5초 지연) | `Settings.tsx` | 🟡 |

#### A2. security-phase2 (S1~S8) — ✅ 구현 완료 (2026-03-16)

| Step | 항목 | 파일 | 의존 |
|------|------|------|------|
| S1 | Rate Limiter X-Forwarded-For 신뢰 | `rate_limit.py` | 독립 |
| S2 | Redis 슬라이딩 윈도우 | `rate_limit.py` | S1 후 |
| S3 | RT sessionStorage 이동 + "로그인 유지" | `AuthContext.tsx`, `Login.tsx` | 독립 |
| S4 | Soft-Delete (deleted_at + Alembic) | `user.py` | 독립 |
| S5 | 이메일/리셋 토큰 해싱 | `user.py`, `auth.py` | 독립 |
| S6 | WebSocket Origin 검증 | `ws.py` | 독립 |
| S7 | 비밀번호 강도 (8자+영문+숫자) | `auth.py`, `Register.tsx` | 독립 |
| S8 | 리셋 URL fragment 전환 | `auth.py`, `ResetPassword.tsx` | S5 후 |

**Alembic 마이그레이션**: S4 (deleted_at), S5 (token_hash)

#### A3. kis-adapter-completion (K1~K3) — ✅ 구현 완료 (2026-03-16)

| Step | 항목 | 파일 |
|------|------|------|
| K1 | 매도 TR ID 검증 | `order.py` |
| K2 | Approval Key 발급 | `auth.py`, `ws.py` |
| K3 | App Secret 불필요 전송 제거 | `auth.py` |

**선행**: KIS API 문서 확인 필요

#### A4. watchlist-heart (하트 토글) — ✅ 구현 완료 (2026-03-16)

| Step | 항목 | 파일 |
|------|------|------|
| 1 | HeartToggle 컴포넌트 + useWatchlistToggle 훅 | 신규 2개 |
| 2 | ListView 적용 | `ListView.tsx` |
| 3 | StockSearch 적용 | `StockSearch.tsx` |
| 4 | DetailView 적용 | `DetailView.tsx` |

---

### Phase A 잔여 — UI 갭 + 품질

#### A5. Phase A UI 미구현 (7건)

| # | 항목 | Spec | 파일 |
|---|------|------|------|
| U2 | 엔진 신호등 카드 → ListView 이동 | frontend-ux-v2 | `ListView.tsx` |
| U3 | 전략 실행/중지 버튼 | frontend-ux-v2 | `ListView.tsx` |
| U4 | 신호등 3색 (연결/엔진/킬스위치) | frontend-ux-v2 | `ListView.tsx` |
| U5 | Header 신호등 제거 | frontend-ux-v2 | `Header.tsx` |
| S1 | 전략 카드 종목명 표시 | strategy-list-info | `RuleCard.tsx` |
| S2 | 전략 방향(매수/매도) 표시 | strategy-list-info | `RuleCard.tsx` |
| S3 | 전략 실행 상태 표시 | strategy-list-info | `RuleCard.tsx` |

**예상 공수**: 3-4일

#### A6. frontend-quality (F1~F3) — ⚠️ 부분 구현

| Step | 항목 | 파일 | 상태 |
|------|------|------|------|
| F1 | ErrorBoundary | `ErrorBoundary.tsx`, `App.tsx` | ✅ (라우트 리셋 미구현) |
| F2 | staleTime 설정 | 다수 (6+ 파일) | ⚠️ 8/20+ 쿼리만 설정 |
| F3 | 프로필 수정 (닉네임) | `auth.py`, `Settings.tsx` | ❌ 미구현 |

#### A7. legal (L1~L3) — ✅ 구현 완료 (2026-03-16)

| Step | 항목 | 파일 |
|------|------|------|
| L1 | 회원가입 약관 동의 | `Register.tsx`, `auth.py`, 마이그레이션 |
| L2 | 약관 열람 페이지 | `LegalDocument.tsx`, `Settings.tsx`, `Layout.tsx` |
| L3 | 약관 버전 관리 | `legal_documents` 테이블, API, ConsentGate, DisclaimerModal |

**Alembic 마이그레이션**: 운영 DB 적용 완료 (2026-03-17 stamp + seed)

#### A8. 추가 품질 이슈 (7건 + 추가 4건)

기존 7건 + 이번 리뷰에서 추가된 4건. 개별 항목은 아래 테이블에서 추적.

| # | 이슈 | 파일 | 상태 |
|---|------|------|------|
| Q1 | 404 fallback 추가 | `App.tsx` | ✅ 구현 완료 |
| Q2 | useAccountStatus 폴링 가드 (인증 전 차단) | `useAccountStatus.ts` | ✅ 구현 완료 |
| Q3 | cloudClient 401 인터셉터 정리 | `cloudClient.ts`, `AuthContext.tsx` | ✅ 구현 완료 |
| Q4 | LocalStatusData.broker에 `reason` 추가 | 타입 파일 | ✅ 구현 완료 |
| Q5 | 장 상태 공휴일 (useMarketContext 활용) | `MainDashboard.tsx` | ❌ 미구현 |
| Q6 | AdminGuard 리다이렉트 개선 | `AdminGuard.tsx` | ✅ 구현 완료 |
| Q7 | Register.tsx 다크 테마 적용 | `Register.tsx` | ✅ 구현 완료 |
| F1+ | ErrorBoundary 라우트 리셋 | `ErrorBoundary.tsx` | ❌ 미구현 |
| F2+ | staleTime 미설정 쿼리 ~7건 | 다수 파일 | ❌ 미구현 |
| D1 | .env 플랜 상수 추가 | `core/config.py` | ❌ 미구현 |
| D4 | 메신저 드롭다운 UI 선점 | `Settings.tsx` | ❌ 미구현 |

**A8 잔여 5건 + A6 F3 닉네임 = 총 6건 → `spec/phase-a-cleanup/` 에서 추적**

#### A9. broker-auto-connect — ✅ 구현 완료 (2026-03-16)

| # | 항목 | 파일 |
|---|------|------|
| F8 | 키 등록 후 reconnect 트리거 | `Settings.tsx`, `localClient.ts` |
| — | 키 미등록 온보딩 CTA | `ListView.tsx` |

---

### Phase A 완료 기준

- [x] 4건 버그 전부 수정 (2026-03-16)
- [x] 보안 S1~S8 전부 적용 (2026-03-16)
- [x] KIS 어댑터 K1~K3 완료 (2026-03-16)
- [x] 하트 토글 ListView/StockSearch/DetailView 적용 (2026-03-16)
- [x] UI 미구현 U2~U5, S1~S3 — 기구현 확인 (2026-03-16, `spec/phase-a-review.md`)
- [ ] ErrorBoundary 라우트 리셋 + staleTime 잔여 ~14건
- [x] 약관 동의/열람/버전관리 (L1~L3) 완료 (2026-03-16)
- [ ] 품질 이슈 잔여: F1+ 라우트 리셋, F2+ staleTime, Q5 공휴일 → `spec/phase-a-cleanup/`
- [x] Q1~Q4, Q6 구현 완료 확인 (2026-03-17), Q7 다크 테마 구현 완료 확인 (2026-03-17)
- [x] broker-auto-connect 프론트 연동 완료 (2026-03-16)
- [ ] 프로필 수정 (F3) 구현
- [ ] `npm run build` 경고 없음
- [ ] `npm run lint` 통과

---

## 3. T1 — 엔진 완성 + DSL + 차트 확장 (3-4주)

> roadmap.md Phase와 별도 축. 기술 구현 백로그.

### 목표
- 실전 매매 엔진 완성 (지표 계산, DSL 파서)
- 차트 타임프레임 (분/주/월봉)
- 로컬 서버 견고성

### Week 3-4 (병렬)

#### T1-1. engine-live-execution (IndicatorProvider) — 🔴

전략 규칙이 기술 지표 (MA, RSI, MACD 등)를 실시간으로 계산하여 매매 신호를 생성하는 핵심 모듈.

| 수용 기준 | 상태 |
|----------|------|
| IndicatorProvider가 실시간 봉 데이터에서 지표 계산 | ❌ |
| 전략 엔진이 IndicatorProvider 결과로 매매 판단 | ❌ |
| 지표 불일치 시 주문 차단 | ❌ |
| 봉 데이터 부족 시 graceful 처리 | ❌ |

**관련 파일**: `local_server/engine/indicator_provider.py`, `local_server/engine/strategy_runner.py`
**예상 공수**: 5-7일

#### T1-2. dsl-client-parser (D1~D4) — 🔴

프론트엔드에서 전략 규칙 DSL을 파싱/검증하여 서버 의존 없이 즉시 피드백.

| Step | 항목 | 의존 |
|------|------|------|
| D1 | DSL 문법 정의 (EBNF) | 독립 |
| D2 | 파서 구현 (TypeScript) | D1 후 |
| D3 | StrategyBuilder 통합 | D2 후 |
| D4 | 에러 메시지 한국어화 | D3 후 |

**예상 공수**: 5-7일

#### T1-3. chart-timeframe Stage 1+2 (백엔드) — 🟡

| Stage | 항목 | 파일 |
|-------|------|------|
| 1 | 로컬 분봉 API (MinuteBarStore, BarBuilder, REST) | `local_server/` 5 파일 |
| 2 | 클라우드 주봉/월봉 집계 | `cloud_server/` 2 파일 |

**예상 공수**: 4-5일

### Week 5

#### T1-4. chart-timeframe Stage 3 (프론트엔드) — 🟡

| 항목 | 파일 |
|------|------|
| Resolution 타입 + 클라이언트 | `types/`, `localClient.ts`, `cloudClient.ts` |
| PriceChart 타임프레임 UI | `PriceChart.tsx` |
| 데이터 소스 분기 (로컬 분봉 vs 클라우드 일/주/월봉) | `useStockData.ts` |

**의존**: T1-3 (Stage 1+2) 완료 후
**예상 공수**: 3-4일

#### T1-5. local-server-resilience (R1, R2, R3, R5) — 🟡

| Step | 항목 | 파일 |
|------|------|------|
| R1 | Config atomic write | `config.py` |
| R2 | Mock/실전 자동감지 | `factory.py` |
| R3 | SyncQueue 연동 | `rules.py`, `heartbeat.py`, `sync_queue.py` |
| R5 | LimitChecker 재시작 복원 | `limit_checker.py` |

**R4 (Heartbeat WS Ack)**: ⚠️ T2로 이동 (relay-infra 의존)
**예상 공수**: 3-4일

---

### T1 완료 기준

- [ ] IndicatorProvider 실시간 지표 계산 동작
- [ ] DSL 파서가 프론트에서 규칙 검증
- [ ] 분/일/주/월봉 타임프레임 전환
- [ ] Config atomic write + SyncQueue 연동
- [ ] LimitChecker 재시작 시 today_executed 복원
- [ ] Mock/실전 자동감지 경고 동작

---

## 4. T2 — 릴레이 인프라 + 원격 제어 보강 (5-7주)

> roadmap.md Phase C에서 릴레이/원격 핵심(C6-a, C6-c)은 이미 구현됨. 이 섹션은 잔여 보강 항목.

### 목표
- 릴레이 인프라 보강 (FCM 푸시, 재전송 등)
- 웹에서 로컬 엔진 제어 고도화
- 원격 모니터링 + 긴급 제어 잔여

### Week 6-8: relay-infra (8단계)

클라우드 서버를 경유하여 프론트엔드 ↔ 로컬 서버 간 실시간 통신 인프라.

| Step | 항목 |
|------|------|
| 1 | Redis Pub/Sub 채널 설계 |
| 2 | 클라우드 WS 릴레이 허브 |
| 3 | 로컬→클라우드 WS 클라이언트 (ws_relay_client.py 재작성) |
| 4 | 프론트→클라우드 WS 클라이언트 |
| 5 | 메시지 라우팅 + 인증 |
| 6 | E2E 암호화 (민감 데이터) |
| 7 | 연결 복구 + 재전송 |
| 8 | 통합 테스트 |

**수용 기준**: 13건
**예상 공수**: 2-3주

### Week 8: local-server-resilience R4

| 항목 | 파일 | 의존 |
|------|------|------|
| Heartbeat WS Ack 버전 파싱 | `ws_relay_client.py`, `heartbeat.py` | relay-infra 완료 후 |

**예상 공수**: 1일

### Week 9-11: remote-ops (9단계)

릴레이 인프라 위에서 구현되는 원격 제어 기능.

| Step | 항목 |
|------|------|
| 1 | 원격 엔진 시작/중지 |
| 2 | 원격 킬스위치 |
| 3 | 원격 전략 활성화/비활성화 |
| 4 | 원격 잔고/미체결 조회 |
| 5 | 원격 체결 로그 조회 |
| 6 | 원격 상태 대시보드 |
| 7 | 푸시 알림 (체결/에러) |
| 8 | 모바일 대응 레이아웃 |
| 9 | 통합 테스트 |

**의존**: relay-infra 완료 후
**수용 기준**: 14건
**예상 공수**: 2-3주

---

### T2 완료 기준

- [ ] 클라우드 릴레이 WS 통신 동작
- [ ] E2E 암호화 적용
- [ ] 웹에서 엔진 시작/중지/킬스위치
- [ ] 원격 잔고/미체결/로그 조회
- [ ] WS heartbeat_ack 버전 파싱 (R4)
- [ ] 연결 끊김 시 자동 재연결

---

## 5. T3 — 런칭 전 정리

### D1. 제품 전략 — ✅ 6건 전부 결정 완료 (2026-03-17)

| 결정 사항 | 결과 | 문서 |
|----------|------|------|
| 무료/Pro 경계 | `.env` 상수 → Pro 때 DB 전환 | `docs/product/free-pro-boundary.md` (확정) |
| 오픈소스 라이선스 | MPL-2.0 | `docs/open-source/oss-license-strategy.md` (확정) |
| LLM 권한 정책 | 금지 권한 하드코딩, config에 provider/limit만 | `docs/product/llm-permission-policy.md` (확정) |
| 메신저 채널 | 전부 제공 목표, Settings 드롭다운 UI 선점 | Phase A8에서 UI 구현 |
| 사용자 프로필 스키마 | 벤치마킹 리서치 후 결정 | Phase D에서 착수 |
| 비서 메모리 저장소 | 로컬 PC 정본, Pro만 클라우드 암호화 백업 | `docs/product/assistant-copilot-engine-structure.md` (확정) |

### D2. 문서 갱신

| 문서 | 이슈 | 상태 |
|------|------|------|
| Phase 1/2 문서 5건 | SUPERSEDED 헤더 추가 | 미착수 |
| architecture.md | Phase C 기능 8건 추가 | 미착수 |
| spec 상태 헤더 | "구현 완료"로 갱신 | ✅ 7건 완료 (2026-03-17) |
| docs/product 3건 | 확정 상태 전환 | ✅ 완료 (2026-03-17) |

### D3. 프로덕션 하드닝 (M1~M6)

`spec/pre-deploy-hardening/` 및 보안 감사 M1~M6 체크리스트:
- 환경변수 검증
- HTTPS 강제
- CORS 프로덕션 화이트리스트
- 로깅/모니터링
- 백업 정책
- Rate limit 프로덕션 튜닝

---

## 6. v2 기능 (런칭 후)

| 항목 | 원래 Phase | 비고 |
|------|-----------|------|
| 백테스팅 엔진 | Phase 4 | 별도 spec 필요 |
| 포트폴리오 리밸런싱 | Phase 5 | 별도 spec 필요 |
| 리스크 메트릭 (VaR, MDD, Sharpe) | Phase 5 | 별도 spec 필요 |
| 2FA 인증 | Phase 1 | 보안 강화 |
| 텔레그램/Slack 연동 | Phase D4 | spec 초안 존재 |
| BYO LLM 연동 | v2 | 설계만 |
| 사용자 프로필/메모리 | Phase E | spec 없음 |

---

## 7. 의존관계 전체 다이어그램

```
Phase A (Week 1-3) — ✅ 완료 ═════════════════════════════════════

  Week 1 (모두 병렬):
  ┌─ [A1] 버그 수정 4건                     ✅
  ├─ [A2] security-phase2 S1→S8             ✅
  ├─ [A3] kis-adapter-completion K1~K3      ✅
  └─ [A4] watchlist-heart                   ✅

  Week 2 (병렬 + 순차):
  ┌─ [A5] UI U2~U5, S1~S3 (기구현 확인)    ✅
  ├─ [A6] frontend-quality F1, F2 (부분)    ⚠️
  ├─ [A7] legal L1→L2→L3                   ✅
  ├─ [A8] 품질 이슈 (잔여 있음)             ⚠️
  └─ [A9] broker-auto-connect               ✅

T1 (Week 4-6) ════════════════════════════════════════════════════

  Week 3-4 (병렬):
  ┌─ [T1-1] engine-live-execution
  ├─ [T1-2] dsl-client-parser D1→D2→D3→D4
  └─ [T1-3] chart-timeframe Stage 1+2

  Week 5 (병렬 + 순차):
  ┌─ [T1-4] chart-timeframe Stage 3         ← T1-3 후행
  └─ [T1-5] local-server-resilience R1~R5   ← 병렬

T2 (Week 7-13) ═══════════════════════════════════════════════════

  [relay-infra 보강] ──────────────┐
                                    ├→ [R4] Heartbeat WS Ack
                                    └→ [remote-ops 잔여]
```

---

## 8. Alembic 마이그레이션 목록

> ✅ 운영 DB 적용 완료 (2026-03-17). `create_all()`로 이미 생성된 테이블을 `alembic stamp head`로 동기화.

| Phase | Spec | 테이블/컬럼 | 마이그레이션 | 상태 |
|-------|------|-----------|-------------|------|
| A | initial | 전체 스키마 | `5fc19af729fc` | ✅ stamp |
| A | security-phase2 | `password_hash` nullable | `a1b2c3d4e5f6` | ✅ stamp |
| A | legal L3 | `legal_documents`, `legal_consents` | `b7c8d9e0f1a2` | ✅ stamp |

시드 데이터: `legal_documents` 3건 (terms, privacy, disclaimer v1.0) 삽입 완료.

---

## 9. npm 의존성 추가 목록

| 패키지 | 용도 | Phase |
|--------|------|-------|
| `@heroicons/react` | HeartToggle 아이콘 (설치 여부 확인) | A |
| `react-markdown` | 약관 렌더링 (legal L2 결정에 따라) | A |

---

## 10. 파일 충돌 매트릭스 — 순차 필요 영역

같은 파일을 수정하는 spec이 여러 개 있으면 병렬 작업 시 충돌이 발생한다.

| 파일 | 관련 Spec | 순서 |
|------|----------|------|
| `cloud_server/api/auth.py` | security-phase2 (S5, S7, S8), legal (L1), frontend-quality (F3) | security → legal → F3 |
| `frontend/src/pages/Settings.tsx` | legal (L2), frontend-quality (F3), broker-auto-connect (F8) | legal → F3, F8 독립 |
| `cloud_server/models/user.py` | security-phase2 (S4, S5) | S4 → S5 |
| `frontend/src/context/AuthContext.tsx` | security-phase2 (S3), 버그 B1 | B1 → S3 |
| `frontend/src/components/main/ListView.tsx` | UI (U2~U4), watchlist-heart, 버그 B3 | B3 → U2~U4 → heart |
| `local_server/broker/kis/auth.py` | K2, K3 | K2 → K3 |
| `local_server/cloud/ws_relay_client.py` | T2 relay-infra (재작성), R4 | relay-infra → R4 |

---

## 11. 커밋 전략

`workflow.md` 규칙에 따라:

### Phase A 커밋 이력 + 잔여

```
완료:
✅ docs: development-plan-v3 + spec/plan 수정
✅ fix: Phase A 버그 4건
✅ feat(security): S1~S8
✅ feat(kis): K1~K3
✅ feat(watchlist): HeartToggle
✅ feat(quality): F1 ErrorBoundary + F2 staleTime (부분)
✅ feat(legal): L1~L3
✅ feat(broker): auto-connect
✅ chore: bump local server v0.1.3
✅ docs: spec 7건 상태 갱신 + product 3건 확정

잔여:
→ feat(ux): U2~U5 신호등 + S1~S3 전략 카드 정보
→ feat(quality): F1+ 라우트 리셋 + F2+ staleTime 잔여 + F3 닉네임
→ fix: 품질 이슈 Q1~Q7
→ feat(settings): 메신저 드롭다운 UI + .env 플랜 상수
```

---

## 12. 리스크 & 블로커

| 리스크 | 영향 | 대응 | 상태 |
|--------|------|------|------|
| KIS API 문서 접근 불가 | K1, K2 검증 불가 | 모의서버 기준 + 주석 표기 | ✅ 해소 (코드 구현 완료) |
| legal Q1-Q5 미결정 | L2 구현 지연 | Q1-Q5 결정 후 착수 | ✅ 해소 (구현 완료) |
| relay-infra 복잡도 | Phase C 일정 초과 | 단계별 검증, MVP 우선 | 유효 |
| React 19 호환성 | 라이브러리 충돌 가능 | react-markdown 등 호환 확인 | ✅ 해소 (호환 확인) |

---

## 참고 문서

| 문서 | 역할 |
|------|------|
| `spec/review-missing-features/report.md` | 교차검증 결과 (v5) |
| `spec/phase-a-review.md` | Phase A 졸업 블로커 |
| `spec/phase-b-backlog.md` | Phase B 설계 미결정 |
| `docs/development-plan-v2.md` | 이전 계획서 (참고) |
| `docs/architecture.md` | 3프로세스 아키텍처 |
| `docs/product/product-direction-log.md` | 제품 방향 미결정 |
| `docs/research/security-audit-report.md` | 보안 감사 원본 |
