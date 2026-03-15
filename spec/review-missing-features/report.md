> 작성일: 2026-03-15 | 상태: 초안 | 미개발 사항 리뷰 v3

# StockVision 미개발 Spec & Plan 상세 분석 + 개발 순서

## 1. 현황 요약

| # | Spec | 상태 | Plan | 공수 | 미충족 기준 |
|---|------|------|------|------|------------|
| 1 | frontend-quality | 초안 | ✅ | 7-10h | 6개 |
| 2 | security-phase2 | 초안 | ✅ | 6-10h | 7개 |
| 3 | legal (UI 연동) | 확정 | ✅ | 8-10h | 3개 |
| 4 | kis-adapter-completion | 초안 | ✅ | 3-5h | 5개 |
| 5 | engine-live-execution | 초안 | ✅ | 2-3일 | 4개 |
| 6 | dsl-client-parser | 초안 | ✅ | 3-4일 | 6개 |
| 7 | chart-timeframe | 초안 | ✅ (신규) | 5-7일 | 12개 |
| 8 | local-server-resilience | 초안 | ✅ | 2-3일 | 7개 |
| 9 | watchlist-heart | 초안 | ✅ (신규) | 1-2일 | 8개 |
| 10 | relay-infra | 초안 | ✅ | 2-3주 | 16개 |
| 11 | remote-ops | 초안 | ✅ | 2-3주 | 23개 |

---

## 2. 교차 의존성 분석

### 2.1 파일 충돌 매트릭스

| 공유 파일 | 관련 Spec | 충돌 유형 | 대응 |
|----------|----------|----------|------|
| `cloud_server/api/auth.py` | frontend-quality F3, legal | 양쪽 모두 엔드포인트 추가 | legal 선행 → F3 후행 |
| `frontend/src/pages/Settings.tsx` | frontend-quality F3, legal | F3=닉네임, legal=약관 | legal 선행 → F3 후행 |
| `local_server/cloud/ws_relay_client.py` | local-server-resilience R4, relay-infra | relay-infra가 파일 전면 교체 | ⚠️ R4는 relay-infra 후에만 의미 |
| `local_server/broker/kis/auth.py` | kis-adapter-completion K2, chart-timeframe 1-3 | K2=approval_key, 1-3=REST 분봉 | 충돌 없음 (다른 메서드) |
| `local_server/engine/bar_builder.py` | engine-live-execution, chart-timeframe | 다른 레이어 (지표 vs UI) | 충돌 없음 |

### 2.2 핵심 의존 관계

```
⚠️ 절대 의존 (순서 필수):
  legal → frontend-quality F3    (auth.py, Settings.tsx 공유)
  relay-infra → local-server-resilience R4  (ws_relay_client.py 전면 교체)
  relay-infra → remote-ops       (WS 인프라 기반)

💡 권장 순서 (필수는 아니지만 효율적):
  kis-adapter-completion K2 → chart-timeframe Stage 1  (KIS auth 강화 후 REST 분봉)
  chart-timeframe Stage 1 → engine-live-execution  (KIS REST 데이터 소스 공유 가능)

✅ 완전 독립 (아무 순서나 가능):
  security-phase2 (S1/S2/S4) ↔ 다른 모든 spec
  dsl-client-parser ↔ 다른 모든 spec (순수 프론트엔드)
  watchlist-heart ↔ 다른 모든 spec (순수 프론트엔드)
  frontend-quality F1/F2 ↔ 다른 모든 spec
```

---

## 3. 개발 순서 제안

### Phase A — 기반 안정화 (1-2주)

**목표**: 운영 전 필수 사항 해결. 보안, 안정성, 법무.

```
Week 1:
  ┌─ security-phase2 (S1→S2, S3, S4)    ← 보안 필수, 6-10h
  ├─ frontend-quality (F1, F2)           ← ErrorBoundary + staleTime, 5-7h
  ├─ kis-adapter-completion (K1, K2)     ← 실매매 기반, 3-5h
  └─ watchlist-heart                     ← 독립 + 소규모, 1-2일
      (모두 병렬 가능)

Week 2:
  ┌─ legal (UI 연동)                    ← 법무 필수, auth.py 수정
  └─ frontend-quality (F3)              ← legal 후행 (auth.py 공유)
      (순차)
```

**산출물**: 보안 강화, ErrorBoundary, 캐시 최적화, 약관 동의, 프로필 수정, KIS 어댑터 완성, 하트 토글

---

### Phase B — 핵심 기능 완성 (3-4주)

**목표**: 전략 엔진 E2E, DSL 편집, 차트 확장, 로컬 서버 안정성.

```
Week 3-4:
  ┌─ engine-live-execution (S2→S3→S5)   ← IndicatorProvider, 2-3일
  ├─ dsl-client-parser (D1→D2→D3→D4)   ← TS 파서, 3-4일
  └─ chart-timeframe Stage 1+2          ← 로컬 분봉 API + 클라우드 주봉, 3-4일
      (모두 병렬 가능)

Week 5:
  ┌─ chart-timeframe Stage 3            ← 프론트엔드 UI, 2-3일
  └─ local-server-resilience (R1, R2, R3) ← R4 제외*, 2일
      (병렬 가능)
```

⚠️ **local-server-resilience R4 (Heartbeat WS Ack)는 Phase C로 연기**
- 이유: relay-infra가 ws_relay_client.py를 전면 교체 → R4를 지금 구현하면 코드 버려짐
- R1 (Config atomic write), R2 (Mock 자동감지), R3 (SyncQueue)는 독립적이므로 여기서 구현

**산출물**: 지표 기반 전략 실행, DSL 폼 편집, 분봉/주봉/월봉 차트, 로컬 서버 안정성

---

### Phase C — 원격 제어 (5-7주)

**목표**: 릴레이 인프라 + 원격 운영 + 잔여 안정화.

```
Week 6-8:
  relay-infra (8단계 순차)              ← WS 인프라 전면 구축, 2-3주

Week 8 (relay-infra 후반부와 병렬):
  local-server-resilience R4            ← relay-infra 새 WS 구조에 맞춰 구현

Week 9-11:
  remote-ops (9단계)                    ← relay-infra 위에 원격 기능, 2-3주
```

**산출물**: 양방향 WS, E2E 암호화, 원격 킬스위치, FCM 푸시, PWA

---

## 4. 재검토 결과 — 새로 발견된 필요사항

### 4.1 local-server-resilience R4 연기 필요 ⚠️

**기존 plan**: R4를 Phase B에서 구현 (R1/R2와 병렬)
**문제**: relay-infra가 `ws_relay_client.py`를 전면 교체할 예정
- R4를 지금 구현하면 relay-infra에서 해당 코드가 삭제됨
- **결정**: R4는 relay-infra 완료 후 Phase C에서 구현

→ `spec/local-server-resilience/plan.md` 수정 필요: R4를 relay-infra 의존으로 표기

### 4.2 legal → frontend-quality F3 순서 강제 ⚠️

**기존 plan**: F1/F2/F3 모두 독립 (병렬 가능)
**문제**: F3와 legal이 `auth.py`, `Settings.tsx` 공유
- F3이 먼저 PATCH /profile을 추가하면, legal이 같은 파일에 terms 로직 추가 시 충돌
- **결정**: legal 선행 → F3 후행

→ `spec/frontend-quality/plan.md` 수정 필요: F3에 legal 의존 명시

### 4.3 chart-timeframe ↔ engine-live-execution 데이터 소스 공유 기회

**발견**: 두 spec 모두 로컬 서버에서 KIS REST 데이터 필요
- chart-timeframe: KIS REST 분봉 조회 (Step 1-3)
- engine-live-execution: yfinance 일봉 (독립 경로)
- **현재는 독립** — 하지만 chart-timeframe의 SQLite 분봉 캐시가 engine에서 활용 가능
- **결정**: 지금은 독립 유지, 추후 통합 검토

### 4.4 heroicons 패키지 확인 필요

**watchlist-heart plan**에서 `@heroicons/react` 사용
- 프로젝트에 이미 설치되어 있는지 확인 필요
- 미설치 시 `npm install @heroicons/react` 선행

### 4.5 Alembic 마이그레이션 누락

**security-phase2 S4**: `User.deleted_at` 필드 추가
**legal**: `User.terms_accepted_at` 필드 추가 가능
- 두 spec 모두 DB 스키마 변경이 필요하나 Alembic 마이그레이션 단계가 plan에 미포함
- **결정**: 각 plan에 마이그레이션 step 추가 필요

### 4.6 lightweight-charts lazy load API 확인 필요

**chart-timeframe Step 3-6**: `onVisibleTimeRangeChanged` 콜백 사용
- lightweight-charts 버전에 따라 API가 다를 수 있음
- 프로젝트에서 사용 중인 버전 확인 후 plan 조정 필요

---

## 5. 총 공수 추정 (갱신)

| Phase | 기간 | 포함 Spec |
|-------|------|----------|
| A — 기반 안정화 | 2주 | security-phase2, frontend-quality (F1/F2), kis-adapter, watchlist-heart, legal, frontend-quality (F3) |
| B — 핵심 기능 | 3-4주 | engine-live-execution, dsl-client-parser, chart-timeframe, local-server-resilience (R1/R2/R3) |
| C — 원격 제어 | 5-7주 | relay-infra, local-server-resilience (R4), remote-ops |
| **합계** | **10-13주** | |

---

## 6. 의존 관계 전체 다이어그램

```
Phase A (Week 1-2)
═══════════════════════════════════════════════════════
  [security-phase2] ─── 독립        ──────────────┐
  [frontend-quality F1/F2] ─── 독립   ──────────┐  │
  [kis-adapter-completion] ─── 독립    ────────┐ │  │
  [watchlist-heart] ─── 독립          ───────┐ │ │  │
                                             │ │ │  │
  [legal] ──────────────────────────┐        │ │ │  │
                                    ↓        │ │ │  │
  [frontend-quality F3] ← legal 후행 ────────┤ │ │  │
                                             │ │ │  │
Phase B (Week 3-5)                           │ │ │  │
═══════════════════════════════════════════════════════
  [engine-live-execution] ─── 독립     ──────┤ │ │  │
  [dsl-client-parser] ─── 독립        ──────┤ │ │  │
  [chart-timeframe] ─── kis-adapter 권장   ──┤ │ │  │
  [local-server-resilience R1/R2/R3] ──────┐ │ │ │  │
                                           │ │ │ │  │
Phase C (Week 6-11)                        │ │ │ │  │
═══════════════════════════════════════════════════════
  [relay-infra] ─────────────────────┐     │ │ │ │  │
                                     ↓     │ │ │ │  │
  [local-server-resilience R4] ← relay 후행 │ │ │  │
                                     ↓     │ │ │ │  │
  [remote-ops] ← relay-infra 완료 후 ──────┘ │ │ │  │
```
