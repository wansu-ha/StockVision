# StockVision v3 개발 계획 일정 리뷰

> 작성일: 2026-03-17 | 리뷰어: PM 에이전트 | 대상: development-plan-v3.md + T1~T3 spec/plan 9종

---

## 1. 검토 범위

| 문서 | 상태 |
|------|------|
| `docs/development-plan-v3.md` | 확정 (2026-03-17 갱신) |
| `spec/engine-live-execution/plan.md` | 확정 |
| `spec/dsl-client-parser/plan.md` | 확정 |
| `spec/chart-timeframe/plan.md` | 확정 |
| `spec/local-server-resilience/plan.md` | 확정 |
| `spec/relay-infra/plan.md` | 확정 |
| `spec/auth-extension/plan.md` | **초안** ← 미확정 |
| `spec/remote-ops/plan.md` | 확정 |
| `spec/phase-a-cleanup/plan.md` | 확정 |
| `spec/doc-refresh/plan.md` | 확정 |
| `spec/production-hardening/plan.md` | 확정 |

---

## 2. 의존성 정합 검증

### 2-1. T1 내부 의존성

| 관계 | v3 다이어그램 | 각 plan | 정합 여부 |
|------|-------------|---------|----------|
| T1-3(백엔드) → T1-4(프론트엔드) | ✅ 명시 | ✅ chart-timeframe plan Stage 1+2 → Stage 3 | 정합 |
| T1-1, T1-2, T1-3 병렬 | ✅ 명시 | ✅ 각 plan 독립 선언 | 정합 |
| T1-5(R1~R3, R5) 병렬 | ✅ 명시 | ✅ resilience plan 독립 선언 | 정합 |
| T1-5 R4 → T2 이동 | ✅ 명시 ("R4 relay-infra 의존") | ✅ resilience plan Step 3에서 "Phase C로 이동" 명시 | 정합 |

**T1 이슈 없음.**

### 2-2. T2 내부 의존성

| 관계 | v3 다이어그램 | 각 plan | 정합 여부 |
|------|-------------|---------|----------|
| relay-infra Step 1→2→3+4→5+6+7→8 순서 | ✅ 명시 | ✅ relay-infra plan 의존성 그래프 동일 | 정합 |
| auth-extension 병렬 착수, relay Step 5 전 완료 필요 | ✅ "Step 5 디바이스 WS 전에 완료 필요" | ⚠️ auth-extension plan Step 6(Device 모델)이 relay Step 5에서 필요하나 명시 약함 | **부분 불일치** |
| relay-infra → R4(Heartbeat WS Ack) | ✅ 명시 | ✅ resilience plan에서 "relay-infra 완료 후" 명시 | 정합 |
| relay-infra + auth-extension → remote-ops | ✅ 명시 | ✅ remote-ops plan "C6-a + C6-b 완료 전제" 명시 | 정합 |

**T2 이슈**: auth-extension plan에서 relay-infra Step 5와의 연동 조건이 명시적이지 않다.
auth-extension Step 6(Device 모델)이 relay-infra Step 5(`/ws/remote` 디바이스 WS 인증)의 선행 조건임을 auth-extension plan 본문에 추가해야 한다.

### 2-3. T3 의존성

| 관계 | v3 다이어그램 | 각 plan | 정합 여부 |
|------|-------------|---------|----------|
| doc-refresh → T1~T2 완료 후 | v3에 "T3 런칭 전" 기술 | doc-refresh plan "Phase B~D 완료 전제" 명시 | 정합 |
| production-hardening 독립 | v3 §D3 | hardening plan 모든 step 독립 명시 | 정합 |
| phase-a-cleanup → T1 비차단 | v3에 Phase A 잔여로 분류 | cleanup plan 자체 의존성 없음 | 정합 |

### 2-4. Phase A Cleanup → T1 차단 여부

**결론: T1 시작을 차단하지 않는다.**

phase-a-cleanup의 6개 항목(F2+ staleTime, F1+ 라우트 리셋, D1 플랜 상수, Q5 공휴일, F3 닉네임, D4 메신저 드롭다운)은 모두 프론트엔드/설정 수정이다. T1의 핵심 항목인 engine-live-execution(백엔드), dsl-client-parser(프론트 유틸), chart-timeframe(백엔드+프론트)과 파일 수준 충돌이 없다.

단, **주의 사항**: phase-a-cleanup Step 3(D1: `cloud_server/core/config.py`)과 production-hardening Step 4(M4: `cloud_server/core/config.py`)가 같은 파일을 수정한다. Phase A cleanup을 T1 이전에 커밋하면 충돌 회피 가능.

---

## 3. 크리티컬 패스 다이어그램

```
Week 0 (현재)
  [phase-a-cleanup] — 1~2일 (비차단, 병렬 가능)

Week 1~2 (T1 착수)
  ┌─ [T1-1] engine-live-execution  ──────────────── 5~7일 ─────────┐
  ├─ [T1-2] dsl-client-parser       ──── D1→D2→D3→D4, 5~7일 ──────┤
  └─ [T1-3] chart-timeframe Stage 1+2 ──────────── 4~5일 ─────┐   │
                                                                │   │
Week 3 (T1 후반)                                               │   │
  [T1-4] chart-timeframe Stage 3 ───────── 3~4일 ─────────────┘   │
  [T1-5] local-server-resilience ─────────── R1~R5, 3~4일 ─────────┘

Week 4~5 (T2 착수)
  ┌─ [relay-infra] Step 1 → 2 → 3+4 ────────────── ~1주 ───────────────────────────────────┐
  └─ [auth-extension] Step 1→2→3+5→4→6→7→8 ─────── ~1~2주 (병렬, Step 6은 Step 5 완료 후)──┤
                                                                                            ↓
Week 6~7                                                                                    │
  [relay-infra] Step 5+6+7 ─────────── (auth-extension Step 6 완료 대기) ──────── ~1주 ─────┘
  [relay-infra] Step 8 (감사 로그) ─── 2~3일

Week 7~8
  [R4 Heartbeat WS Ack] ─────────────────────────── 1일 ─────────┐
  [remote-ops] Step 1→2→3+4 + Step 5→6 + Step 7+8 ── 2~3주 ──────┘

Week 10~11 (T3)
  ┌─ [doc-refresh] ── 1~2시간 (병렬)
  └─ [production-hardening] ── 2~3일 (병렬)

══════════════════════════════════════════════════════════════
크리티컬 패스:
  T1-3(4~5일) → T1-4(3~4일) → relay-infra Step1~4(~1주) →
  auth-extension Step 6(Device 모델, 의존 합류) →
  relay-infra Step 5+6+7(~1주) →
  remote-ops Step 1~9(2~3주) → T3

총 크리티컬 패스 길이: 약 12~14주
```

### 병목 지점

1. **relay-infra Step 5 대기점** (Week 6): relay-infra Step 5(`/ws/remote`)가 auth-extension Step 6(Device 모델)을 기다린다. auth-extension이 늦어지면 relay-infra Step 5 이후 전체가 지연된다.

2. **remote-ops 전체 길이** (Week 7~10): 9단계 + 통합 테스트로 T2에서 가장 긴 단일 작업. FCM 백엔드(Step 5)가 독립적이므로 relay-infra Step 4 완료 직후 병렬 착수 가능하지만, v3 다이어그램에서 명시되지 않은 부분이다.

3. **T1-3 → T1-4 순차** (Week 2~3): chart-timeframe Stage 3(프론트)가 Stage 1+2(백엔드) 완료를 기다린다. 백엔드 API 스펙을 먼저 확정하면 프론트 목 개발로 일부 병렬화 가능.

---

## 4. 파일 충돌 매트릭스 — 보완

v3 §10의 기존 매트릭스에 누락된 충돌이 있다. 아래는 T1~T3에서 추가로 발견된 충돌 목록이다.

### 4-1. 기존 매트릭스 (v3 §10) — 검증 결과

| 파일 | 관련 Spec | 기록 순서 | 검증 |
|------|----------|----------|------|
| `cloud_server/api/auth.py` | security-phase2, legal, F3 | security→legal→F3 | ✅ 정확 |
| `frontend/src/pages/Settings.tsx` | legal, F3, broker-auto-connect | 순서 적절 | ✅ 정확 |
| `local_server/cloud/ws_relay_client.py` | relay-infra(재작성), R4 | relay→R4 | ✅ 정확 |

### 4-2. 누락된 신규 충돌 (T1~T3)

| 파일 | 관련 Spec | 충돌 유형 | 권장 순서 |
|------|----------|----------|----------|
| `cloud_server/api/auth.py` | **auth-extension** (OAuth 엔드포인트, verify-password), **remote-ops** (verify-password) | 동일 파일 동시 수정 | auth-extension → remote-ops |
| `cloud_server/core/config.py` | **phase-a-cleanup** (D1 플랜 상수), **auth-extension** (OAuth 환경변수), **production-hardening** M4 (환경변수 필수 검증) | 3개 spec이 같은 파일 수정 | phase-a-cleanup → auth-extension → hardening |
| `cloud_server/services/relay_manager.py` | **relay-infra** (핵심 구현), **remote-ops** (FCM 트리거) | relay-infra가 파일 신규 생성, remote-ops가 수정 | relay-infra → remote-ops |
| `cloud_server/main.py` | **relay-infra** (WS 라우터 등록), **auth-extension** (devices 라우터 등록), **remote-ops** (Firebase SDK 초기화, push 라우터) | 3개 spec이 같은 파일 수정 | relay-infra → auth-extension → remote-ops |
| `cloud_server/core/init_db.py` | **relay-infra** (PendingCommand, AuditLog 모델), **auth-extension** (Device, OAuthAccount 모델) | 2개 spec이 모델 import 추가 | relay-infra → auth-extension (또는 배치 처리) |
| `local_server/cloud/heartbeat.py` | **local-server-resilience** R3 (SyncQueue flush), **relay-infra** Step 3 (WS heartbeat 전환) | R3가 HTTP heartbeat에 연동, relay-infra Step 3이 WS로 전환 | relay-infra Step 3 → R3 재검토 필요 |
| `local_server/cloud/ws_relay_client.py` | **relay-infra** (신규 생성), **remote-ops** (command 핸들러 추가), **R4** (버전 파싱 추가) | 신규 생성 후 2개 spec이 순차 수정 | relay-infra → remote-ops → R4 |
| `frontend/src/services/cloudClient.ts` | **chart-timeframe** Stage 3 (cloudBars 확장), **auth-extension** (OAuth, 디바이스 API), **remote-ops** (verify-password, push/register) | 3개 spec이 순차 수정 | chart-timeframe → auth-extension → remote-ops |
| `frontend/src/services/localClient.ts` | **chart-timeframe** Stage 3 (localBars 추가), **remote-ops** (WS 연결 함수) | 수정 시점 겹침 가능 | chart-timeframe → remote-ops |
| `frontend/src/pages/Settings.tsx` | **phase-a-cleanup** F3 (닉네임), **auth-extension** (디바이스 관리 섹션) | 순차 수정 | phase-a-cleanup → auth-extension |
| `local_server/main.py` | **relay-infra** (WS 클라이언트 lifespan), **auth-extension** (devices 라우터), **chart-timeframe** Stage 1 (bars 라우터) | 3개 spec이 같은 파일 수정 | chart-timeframe → relay-infra → auth-extension |
| `frontend/src/App.tsx` | **phase-a-cleanup** F1+ (ErrorBoundary 라우트 리셋), **remote-ops** (SW 등록, FCM 초기화, RemoteMode Context) | 수정 시점 분리 필요 | phase-a-cleanup → remote-ops |
| `frontend/src/components/main/ListView.tsx` | **local-server-resilience** R2 경고 UI (간접), **remote-ops** Step 8 (모바일 반응형, 필요 시) | 낮은 충돌 가능성 | 확인 후 결정 |

### 4-3. heartbeat.py 특이 충돌 상세

`local_server/cloud/heartbeat.py`는 두 spec이 서로 다른 방향으로 수정한다.

- **local-server-resilience R3**: HTTP heartbeat 복구 감지 시 SyncQueue flush 추가
- **relay-infra Step 3**: HTTP heartbeat → WS heartbeat로 전환, HTTP는 폴백으로 유지

구현 순서: **relay-infra Step 3을 먼저** 구현하여 WS/HTTP 분기 구조를 완성한 후, R3 SyncQueue flush를 해당 구조에 맞게 추가해야 한다. 현재 T1에서 R3를 T2 전에 구현하려는 계획(T1-5)은 heartbeat.py의 이 충돌로 인해 R3 구현 범위가 제한될 수 있다.

**권고**: T1-5 R3는 HTTP heartbeat 기준으로만 구현하고, relay-infra Step 3 완료 후 WS heartbeat에 flush 로직을 추가하는 R3-b를 T2에 포함시키는 것을 검토.

---

## 5. 공수 추정 검증

### 5-1. T1

| 항목 | Step 수 | 수정 파일 수 | v3 예상 공수 | 평가 |
|------|---------|------------|------------|------|
| engine-live-execution | 5 (S1 완료, S2~S5 잔여 4) | 3 | 5~7일 | ✅ 적정. yfinance 연동 + IndicatorProvider 구현 포함 |
| dsl-client-parser | 4 (D1~D4 순차) | 6 | 5~7일 | ✅ 적정. 파서 구현이 핵심 |
| chart-timeframe | 11 (Stage 1~3) | 11 | 7~9일 합계 | ⚠️ 낙관적. KIS 분봉 페이지네이션 + lazy load 구현 포함 시 10~12일 예상 |
| local-server-resilience | 4 (R1~R3, R5) | 6 | 3~4일 | ✅ 적정. 각 step 단순 |

**chart-timeframe 리스크**: 11개 파일, lazy load(onVisibleTimeRangeChanged) 미검증 API, KIS 분봉 페이지네이션. 현재 7~9일 추정 대비 10~12일 버퍼 권장.

### 5-2. T2

| 항목 | Step 수 | 수정 파일 수 | v3 예상 공수 | 평가 |
|------|---------|------------|------------|------|
| relay-infra | 8 | 12 (클라우드 7, 로컬 5) | 2~3주 | ⚠️ 낙관적. E2E 암호화 크로스 플랫폼(Python+TS) + WS 재연결 robust 구현은 2.5~4주 |
| auth-extension | 8 | 15 (클라우드 9, 로컬 2, 프론트 4) | 1~2주 | ✅ 적정. Google/Kakao OAuth 패턴 유사 |
| remote-ops | 9 | 17 (클라우드 6, 로컬 2, 프론트 15) | 2~3주 | ⚠️ 낙관적. FCM + PWA + 통합 테스트 포함 시 3~4주 |
| R4 | 1 | 2 | 1일 | ✅ 적정 |

**T2 전체 공수 리스크**: v3 예상 5~7주 대비 실제 7~10주 가능성. 특히 relay-infra와 remote-ops에서 각 1~2주 초과 위험.

### 5-3. T3

| 항목 | Step 수 | 수정 파일 수 | 예상 공수 | 평가 |
|------|---------|------------|---------|------|
| phase-a-cleanup | 6 | 13 | 1~2일 | ✅ 적정 (모두 소규모 수정) |
| doc-refresh | 2 | 5 | 1~2시간 | ✅ 적정 |
| production-hardening | 8 | 8 | 2~3일 | ✅ 적정 (코드 5, 인프라 3) |

---

## 6. 병렬화 기회 분석

### 현재 미병렬화된 구간

| 구간 | 현재 | 개선안 | 예상 단축 |
|------|------|-------|---------|
| relay-infra Step 5+6+7 | auth-extension 전체 완료 대기 | auth-extension Step 6(Device 모델)만 완료되면 Step 5 착수 가능. Step 7(로컬 페어링)은 relay Step 6(E2E 암호화) 완료 후 병렬 | 2~4일 |
| remote-ops Step 5(FCM 백엔드) | remote-ops 순차 | relay-infra Step 4 완료 직후 FCM 백엔드 병렬 착수 가능 (WS 연결에 독립) | 3~5일 |
| remote-ops Step 7(PWA) | Step 2 이후 | Step 7은 순수 정적 파일(manifest, sw.js, 아이콘). relay-infra 완료 직후 병렬 착수 가능 | 1~2일 |
| T1-3 Stage 3(프론트) | Stage 1+2 전체 완료 대기 | API 스펙 확정 후 프론트 목 개발 병렬 → API 완성 시 연동만 | 2~3일 |
| production-hardening Step 6~8(인프라) | T3 전체 시작 이후 | T2 완료 전 인프라 설정(Nginx TLS, CSP, CI)은 언제든 가능 | 배포 준비 1주 단축 |
| doc-refresh | T3 시작 후 | T2 작업과 병행 가능 (코드 충돌 없음) | T3 기간 내 단축 |

### 개선된 T2 병렬 구조 (권장)

```
Week 4 (T2 착수):
  ┌─ [relay-infra] Step 1+2 ─────────────────────────────────────────────────┐
  └─ [auth-extension] Step 1+4(이메일) ─ 독립 병렬 ─────────────────────────┤

Week 5:
  ┌─ [relay-infra] Step 3+4 ─────────────────────────────────────────────────┤
  ├─ [auth-extension] Step 2+3(Google OAuth) ── Step 5(Kakao)와 병렬 ─────────┤
  └─ [remote-ops] Step 5(FCM 백엔드) ← relay Step 4 완료 후 병렬 착수 가능 ───┤

Week 6:
  ┌─ [relay-infra] Step 5 ← auth-extension Step 6(Device 모델) 대기 ──────────┤
  ├─ [auth-extension] Step 6+7+8 ────────────────────────────────────────────┤
  └─ [remote-ops] Step 6(FCM 프론트) + Step 7(PWA) 병렬 ─────────────────────┤

Week 7~8:
  [relay-infra] Step 6+7+8 → [R4] → [remote-ops] Step 1~4+8+9 (통합 테스트)
```

---

## 7. 리스크 목록

### 7-1. 일정 리스크

| # | 리스크 | 영향도 | 가능성 | 대응 |
|---|--------|--------|--------|------|
| R1 | relay-infra E2E 암호화 크로스 플랫폼 구현 지연 | 🔴 High (T2 전체 차단) | 중간 | Python ↔ TypeScript 단위 테스트를 Step 6 착수 전 선행 작성 |
| R2 | auth-extension Step 6(Device 모델) 지연 → relay-infra Step 5 차단 | 🔴 High | 낮음 | auth-extension Step 6을 최우선으로 완료, 나머지 Step(OAuth UI 등)은 후행 |
| R3 | chart-timeframe KIS 분봉 API 페이지네이션 + lazy load 구현 초과 | 🟡 Medium (T1 일정 지연) | 중간 | mock 브로커로 먼저 개발, KIS 실제 연동은 별도 Sprint |
| R4 | remote-ops FCM + PWA 통합 테스트 공수 초과 | 🟡 Medium (T2 후반 지연) | 중간 | FCM 백엔드를 T2 초반에 병렬 착수하여 버퍼 확보 |
| R5 | heartbeat.py 이중 수정(R3 + relay-infra) 충돌 | 🟡 Medium | 높음 | T1-5 R3를 HTTP 전용으로 제한, relay Step 3 후 R3-b 추가 |
| R6 | auth-extension plan 상태가 "초안" — 확정 전 구현 착수 리스크 | 🟡 Medium | 중간 | T2 착수 전 auth-extension plan 확정 필요 |
| R7 | T2 전체 공수 v3 예상(5~7주) 대비 실제 7~10주 가능성 | 🔴 High | 중간 | T2 Week 4~5에 릴레이 핵심(Step 1~4)만 MVP로 우선 완성, 나머지 병렬화 |

### 7-2. 기술 리스크

| # | 리스크 | 영향도 | 대응 |
|---|--------|--------|------|
| T1 | KIS 분봉 API(FHKST03010200) 30건 제한 + 페이지네이션 | 🟡 Medium | mock 테스트 선행 |
| T2 | Google/Kakao OAuth 앱 등록 필요 (외부 의존성) | 🟡 Medium | 개발용 OAuth 앱 사전 등록 |
| T3 | Firebase Admin SDK + FCM HTTP v1 설정 복잡도 | 🟡 Medium | Firebase 프로젝트 사전 설정 |
| T4 | PWA + ServiceWorker + FCM SW 상호 작용 | 🟡 Medium | Chrome DevTools 테스트 충분히 |
| T5 | lightweight-charts `onVisibleTimeRangeChanged` 지원 여부 미확인 | 🟡 Medium | 라이브러리 문서/소스 선행 확인 |

### 7-3. 문서 리스크

| # | 리스크 | 대응 |
|---|--------|------|
| D1 | auth-extension plan이 "초안" 상태로 T2 착수 직전까지 미확정 | T2 시작 1주 전에 확정 필수 |
| D2 | v3 §10 파일 충돌 매트릭스가 T1~T2 신규 충돌 11건 미반영 | 이 문서 §4-2를 v3 §10에 병합 필요 |

---

## 8. 최종 권고 사항

1. **v3 §10 파일 충돌 매트릭스 갱신**: 이 리뷰의 §4-2에서 발견된 11건의 신규 충돌을 v3 §10에 추가할 것.

2. **auth-extension plan 확정**: 현재 "초안" 상태. T2 착수 전(Week 3 종료 시점)까지 "확정"으로 전환 필요. 특히 relay-infra Step 5와의 연동 전제 조건을 plan 본문에 명시해야 함.

3. **R3 구현 분리**: T1-5에서 local-server-resilience R3(SyncQueue heartbeat flush)를 HTTP 전용으로 제한 구현하고, relay-infra Step 3 완료 후 R3-b(WS 버전 flush)를 T2 내에 추가.

4. **chart-timeframe 공수 버퍼**: 현재 7~9일 추정에 2~3일 버퍼 추가. KIS 분봉 API는 mock 브로커로 먼저 개발하고 실제 연동을 후행.

5. **T2 병렬화 개선**: remote-ops Step 5(FCM 백엔드)와 Step 7(PWA)을 relay-infra Step 4 완료 시점에 병렬 착수. T2를 약 1~2주 단축 가능.

6. **production-hardening 조기 착수**: Step 6~8(인프라 TLS/CSP/CI)은 코드 의존성이 없으므로 T2 진행 중에 병렬로 처리 가능.

7. **T2 전체 공수 재설정**: v3에 "5~7주"로 기재된 T2 일정을 "7~10주"로 현실화. relay-infra + remote-ops의 복잡도와 외부 의존성(Firebase, OAuth 앱)을 반영.

---

## 9. 요약

| 검토 항목 | 결과 |
|----------|------|
| 의존성 정합 | ✅ 대체로 정합. auth-extension ↔ relay-infra Step 5 연동 조건 명시 보완 필요 |
| 파일 충돌 매트릭스 | ⚠️ T1~T3에서 11건 신규 충돌 발견. v3 §10 갱신 필요 |
| 크리티컬 패스 | 약 12~14주 (auth-extension Step 6 → relay-infra Step 5 병목이 핵심) |
| 공수 추정 | ⚠️ chart-timeframe 낙관적, T2 전체 1~3주 초과 가능성 |
| 병렬화 가능성 | remote-ops Step 5/7, doc-refresh 조기 병렬 착수로 1~2주 단축 가능 |
| Phase A Cleanup → T1 차단 여부 | ✅ T1을 차단하지 않음. config.py 충돌만 순서 주의 |
