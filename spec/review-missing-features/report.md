> 작성일: 2026-03-15 | 갱신일: 2026-03-16 | 상태: 구현 완료 | 미개발 사항 교차검증 리뷰 v5
>
> **A1~A9 구현 완료** — 상세: `reports/phase-a-implementation.md`
> **잔여 TODO** — 상세: `reports/remaining-todos.md`

# StockVision 교차검증 리뷰 — Spec · Plan · 아키텍처 · 제품문서 · 리서치

## 검증 소스

| 소스 | 파일 수 | 주요 내용 |
|------|--------|----------|
| spec/ (79개 디렉터리) | ~160 | 기능 spec + plan + reports |
| docs/development-plan*.md | 3 | v1 원본 계획, v2 아키텍처 변경 |
| docs/architecture*.md | 2 | Phase 3 아키텍처, 원래 설계 |
| docs/product/ | 5+ | 제품 방향, Free/Pro 경계, UX 우선순위 |
| docs/research/ | 52+ | 보안 감사, API 리뷰, 법무, LLM 연동 |
| docs/legal/ | 5 | 이용약관, 개인정보, 면책, 브로커 준수 |
| spec/phase-a-review.md | 1 | Phase A 졸업 블로커 |
| spec/phase-b-backlog.md | 1 | Phase B 설계 미결정 |

---

## Part 1: 새로 발견된 미해결 사항

### 1.1 Phase A 졸업 블로커 — 기존 리뷰에서 누락 ⚠️

이전 리뷰(v3)에서 **초안 상태 spec 11건**만 분석했으나, `phase-a-review.md`에 **이미 구현 완료 표기된 spec들의 미충족 기준**이 남아 있었다.

#### 프론트엔드 미구현 (frontend-ux-v2)

| ID | 항목 | 상태 | 영향 |
|----|------|------|------|
| U2 | 엔진 신호등 카드 → ListView로 이동 | ✅ 이미 구현됨 (A5에서 확인) | — |
| U3 | 전략 실행/중지 버튼 | ✅ 이미 구현됨 (A5에서 확인) | — |
| U4 | 신호등 3색 (연결/엔진/킬스위치) | ✅ 이미 구현됨 (A5에서 확인) | — |
| U5 | Header 신호등 제거 | ✅ 이미 구현됨 (A5에서 확인) | — |

#### 전략 목록 정보 부족 (strategy-list-info)

| ID | 항목 | 상태 |
|----|------|------|
| S1 | 전략 카드에 종목명 표시 | ✅ 이미 구현됨 (A5에서 확인) |
| S2 | 전략 방향(매수/매도) 표시 | ✅ 이미 구현됨 (A5에서 확인) |
| S3 | 실행 상태 표시 | ✅ 이미 구현됨 (A5에서 확인) |

#### 프론트엔드 버그 — 4건

| 버그 | 심각도 | 위치 |
|------|--------|------|
| AuthContext setState 경쟁 조건 — RT 갱신 시 `localReady=false` 리셋 → 잔고 미로딩 | 🔴 높음 | ✅ A1+A2에서 수정 |
| useStockData quotesQuery/namesQuery 클로저 race condition | 🔴 높음 | ✅ A4에서 수정 (watchlistSet 메모이제이션) |
| 미체결 "취소" 버튼 stub — onClick 없음, PendingOrder.orderId 타입 누락 | 🟡 중간 | ⏳ 잔여 TODO |
| Settings 키 등록 후 localStatus 캐시 미갱신 (5초 지연) | 🟡 중간 | ✅ A9에서 수정 (reconnect + invalidateQueries) |

#### 추가 품질 이슈 — 7건

| 이슈 | 영향 |
|------|------|
| App.tsx 중첩 Routes에 404 fallback 없음 | ✅ A8에서 확인 — catch-all 라우트 존재 |
| useAccountStatus가 localReady 무관하게 폴링 → 인증 전 401 | ✅ A8에서 확인 — localReady 가드 존재 |
| cloudClient 401 인터셉터 — AuthContext 정리 불완전 | ✅ A1+A2에서 수정 — 커스텀 이벤트 동기화 |
| LocalStatusData.broker에 `reason?: string` 없음 | ✅ A8에서 확인 — reason 필드 존재 |
| 장 상태 공휴일 무시 (useMarketContext 미사용) | ⏳ 잔여 TODO (낮은 우선순위) |
| AdminGuard가 어드민 로그인 대신 메인으로 리다이렉트 | ✅ A8에서 확인 — 정상 동작 |
| Register.tsx 라이트 테마 불일치 | ⏳ 잔여 TODO (기술 부채) |

---

### 1.2 broker-auto-connect 미완성 — 기존 리뷰에서 누락

Phase A 리뷰에서 **broker-auto-connect가 "구현 완료" 표기**되었으나, 실제로 프론트엔드 연동이 빠져 있다.

| 항목 | 상태 |
|------|------|
| F8: 키 등록 후 즉시 재연결 트리거 | ✅ A9에서 수정 — `localBroker.reconnect()` 호출 추가 |
| localClient.ts에 reconnect 함수 | ✅ 이미 존재 확인 (`localBroker.reconnect()`) |
| 키 미등록 온보딩 CTA | ⏳ 잔여 TODO |

---

### 1.3 legal plan-v2 상세 — L1/L2/L3 미구현

`spec/legal/plan-v2.md`에 상세 구현 계획이 있으나 전부 미시작:

**L1 (회원가입 약관 동의)**:
- [x] 체크박스 2개 미체크 시 가입 버튼 비활성 ← A7
- [x] 서버 `terms_agreed=false` → 400 ← A7
- [x] `legal_consents` 테이블에 2건 기록 ← A7 (Alembic 마이그레이션 필요)
- [x] 약관 링크 → 새 탭에서 전문 열람 ← A7

**L2 (약관 열람)**:
- [x] `/legal/terms`, `/legal/privacy`, `/legal/disclaimer` 페이지 ← A7
- [ ] Settings에 "약관 및 고지" 섹션 ← 잔여 TODO
- [x] Footer에 3개 링크 ← A7

**L3 (약관 버전 관리)**:
- [x] `legal_documents` 테이블 + 시드 데이터 ← A7 (Alembic + 시드 필요)
- [x] `GET /api/v1/legal/documents/{type}` API ← A7
- [x] `GET /api/v1/legal/consent/status` API ← A7
- [ ] 약관 업데이트 시 `requires_consent` 반환 → 재동의 모달 ← 잔여 TODO

**미결정 사항 (Q1-Q5)**:
- Q1: 마크다운 렌더링 — `react-markdown` vs 직접 (제안: react-markdown)
- Q2: 약관 원문 — DB vs 파일 (제안: DB)
- Q3: 기존 사용자 — 다음 로그인 시 재동의
- Q4: 면책 고지 시점 — 가입 시 vs 전략 활성화 시 (제안: 전략 활성화 시)
- Q5: react-markdown 의존성 추가 필요 여부

---

### 1.4 개발계획서 vs 현실 — 전략적 피벗 확인

`docs/development-plan.md` (v1 원본)과 현재 구현을 비교한 결과, **의도적 피벗**과 **진짜 누락**을 구분해야 한다.

#### 의도적 피벗 (문제 아님)

| 원래 계획 | 현재 | 이유 |
|----------|------|------|
| LSTM/RF/SVM ML 모델 | Claude API 분석 | AI 예측 → LLM 비서로 전환 |
| 가상 거래 시뮬레이터 | 브로커 직접 연동 | 실전 주문 엔진으로 전환 |
| 중앙집중 DB (10+ 테이블) | 클라우드 최소 + 로컬 SQLite | 3프로세스 아키텍처 |
| 다중 브로커 (Yahoo, CCXT) | KIS/키움 한국 증권사 | 한국 시장 집중 |

#### 진짜 누락 (향후 구현 필요)

| 항목 | 원래 Phase | 현재 상태 | 제안 시기 |
|------|-----------|----------|----------|
| 백테스팅 엔진 | Phase 4 | spec 없음 | v2 |
| 포트폴리오 리밸런싱 | Phase 5 | spec 없음 | Phase E |
| 리스크 메트릭 (VaR, MDD, Sharpe) | Phase 5 | spec 없음 | Phase E |
| 2FA 인증 | Phase 1 | 미구현 | v2 |
| 텔레그램/Slack 연동 | Phase D4 | spec 초안만 | Phase D |
| 사용자 프로필/메모리 | Phase E | spec 없음 | Phase E |
| BYO LLM 연동 | v2 | 설계만 | v2 |

---

### 1.5 제품 방향 문서에서 발견된 미결정 사항

`docs/product/product-direction-log.md`, `free-pro-boundary.md`에서 제품 전략 미결정:

| 미결정 사항 | 영향 | 긴급도 |
|------------|------|--------|
| 무료/Pro 경계 확정 | 가격 정책 | 🟡 런칭 전 |
| 사용자 프로필 스키마 | Phase E 기반 | 🟢 나중 |
| 비서 메모리 저장소 (로컬 vs 클라우드) | 아키텍처 | 🟢 나중 |
| 메신저 1순위 채널 | Phase D | 🟢 나중 |
| 오픈소스 라이선스 (AGPL vs MPL-2.0 vs 듀얼) | 공개 전 필수 | 🟡 런칭 전 |
| LLM 권한 정책 (생성 가능 결과 범위) | 안전성 | 🟡 런칭 전 |

---

## Part 2: 기존 리뷰 항목 수정 사항

### 2.1 개발 순서 수정 — Phase A에 추가 항목

기존 Phase A (기반 안정화)에 **Phase A 졸업 블로커**를 포함해야 한다.

```diff
Phase A (Week 1-2) — 기반 안정화
+ ┌─ Phase A 졸업 블로커 (버그 4건 + UI 7건)          ← 신규 추가
  ├─ security-phase2 (S1→S2, S3, S4)
  ├─ frontend-quality (F1, F2)
  ├─ kis-adapter-completion (K1, K2)
  └─ watchlist-heart
  순차: legal → frontend-quality (F3)
```

### 2.2 Alembic 마이그레이션 필요 목록 (확장)

| Spec | 필드/테이블 | 마이그레이션 |
|------|-----------|-------------|
| security-phase2 S4 | `User.deleted_at` | ALTER TABLE users ADD |
| legal L3 | `legal_documents` 테이블 | CREATE TABLE |
| legal L3 | `legal_consents` 테이블 | CREATE TABLE |
| legal L1 | `User.terms_accepted_at` (선택) | ALTER TABLE users ADD |

### 2.3 npm 의존성 추가 필요

| 패키지 | 용도 | 필요 Spec |
|--------|------|----------|
| `@heroicons/react` | HeartToggle 아이콘 | watchlist-heart |
| `react-markdown` | 약관 렌더링 | legal L2 |

---

## Part 3: 갱신된 개발 순서

### Phase A — 기반 안정화 + 졸업 블로커 (2-3주)

```
Week 1 (병렬):
  ┌─ Phase A 버그 수정 (4건)
  │    - AuthContext 경쟁 조건
  │    - useStockData 클로저 race
  │    - 미체결 취소 버튼 + orderId 타입
  │    - Settings 키 등록 캐시
  │
  ├─ Phase A UI 미구현 (7건)
  │    - frontend-ux-v2 U2~U5 (신호등, 버튼, Header)
  │    - strategy-list-info S1~S3 (종목명, 방향, 상태)
  │
  ├─ security-phase2 (S1→S2, S3, S4)
  ├─ kis-adapter-completion (K1, K2)
  └─ watchlist-heart

Week 2 (병렬 + 순차):
  ┌─ frontend-quality (F1 ErrorBoundary, F2 staleTime)   ← 병렬
  ├─ legal (L1 + L2 + L3)                                 ← 병렬
  │    └→ frontend-quality F3 (legal 후행)                 ← 순차
  └─ 추가 품질 이슈 (404 fallback, 폴링 가드, 공휴일)     ← 병렬
```

### Phase B — 핵심 기능 완성 (3-4주)

```
Week 3-4 (병렬):
  ┌─ engine-live-execution (IndicatorProvider)
  ├─ dsl-client-parser (D1→D2→D3→D4)
  └─ chart-timeframe Stage 1 + 2

Week 5:
  ┌─ chart-timeframe Stage 3 (프론트엔드)
  └─ local-server-resilience (R1, R2, R3 — R4 제외)
```

### Phase C — 원격 제어 (5-7주)

```
Week 6-8:  relay-infra (8단계)
Week 8:    local-server-resilience R4 (relay-infra 후행)
Week 9-11: remote-ops (9단계)
```

---

## Part 4: 최종 미해결 항목 통합

### 카테고리별 미해결 항목 수

| 카테고리 | 항목 수 | 우선순위 | 이전 리뷰 대비 |
|---------|--------|---------|--------------|
| Phase A 졸업 블로커 (버그 + UI) | 18건 | 🔴 즉시 | **신규 발견** |
| 초안 Spec 미충족 기준 | ~100건 | 🔴-🟡 | 기존 유지 |
| Legal UI/API 미구현 (L1-L3) | 15건 | 🔴 운영 전 | **상세화** |
| Alembic 마이그레이션 | 4건 | 🔴 구현 시 | **신규 발견** |
| npm 의존성 추가 | 2건 | 🟡 구현 시 | **신규 발견** |
| 제품 전략 미결정 | 6건 | 🟡 런칭 전 | **신규 발견** |
| v2 기능 (백테스팅, 리밸런싱 등) | 7건 | 🟢 v2 | **신규 발견** |
| **총계** | **~152건** | | +52건 추가 |

### 기존 리뷰에서 누락되었던 항목 요약

| # | 항목 | 이유 |
|---|------|------|
| 1 | Phase A 졸업 블로커 18건 | "구현 완료" 표기 spec의 미충족 기준을 확인하지 않았음 |
| 2 | broker-auto-connect F8 프론트엔드 | 백엔드는 구현되었으나 프론트 연동 누락 |
| 3 | legal plan-v2 상세 (L1-L3, 30개 체크리스트) | plan-v2.md를 별도로 확인하지 않았음 |
| 4 | Alembic 마이그레이션 4건 | Plan에 DB 스키마 변경은 있으나 마이그레이션 단계 없음 |
| 5 | 개발계획서 v1 대비 미구현 7건 | 의도적 피벗 vs 진짜 누락 구분 필요했음 |
| 6 | 제품 방향 미결정 6건 | spec이 아닌 product 문서에만 존재 |
| 7 | 오픈소스 라이선스 미결정 | docs/open-source/ 문서에만 존재 |

---

## Part 5: 의존 관계 전체 다이어그램 (갱신)

```
Phase A (Week 1-3) ═══════════════════════════════════════
  [Phase A 버그 4건] ─── 즉시              ⬅ 신규
  [Phase A UI 7건] ─── 즉시                ⬅ 신규
  [security-phase2] ─── 독립 (Alembic 포함) ⬅ 수정
  [kis-adapter-completion] ─── 독립
  [watchlist-heart] ─── 독립 (heroicons 확인)⬅ 수정
  [frontend-quality F1/F2] ─── 독립
  [legal L1+L2+L3] ──┐ (Alembic + react-markdown) ⬅ 상세화
                      ↓
  [frontend-quality F3] ← legal 후행

Phase B (Week 4-6) ═══════════════════════════════════════
  [engine-live-execution] ─── 독립
  [dsl-client-parser] ─── 독립
  [chart-timeframe Stage 1+2] ─── 독립
  [chart-timeframe Stage 3] ← Stage 1+2 후행
  [local-server-resilience R1/R2/R3] ─── 독립 (R4 제외)

Phase C (Week 7-13) ═══════════════════════════════════════
  [relay-infra] ──────────────┐
                              ↓
  [local-server-resilience R4] ← relay-infra 후행
                              ↓
  [remote-ops] ← relay-infra 후행
```

---

## Part 6: 리서치 문서 교차검증 — 보안 감사 · API 리뷰 · 코드 분석

`docs/research/` 52개 파일을 검증한 결과, 대부분의 Critical/High 이슈는 **이미 수정됨**.
아래는 **현재 코드에서 미해결 상태인 항목만** 정리.

### 6.1 보안 — 미해결 1건

| 이슈 | 소스 | 상세 | 심각도 |
|------|------|------|--------|
| 이메일/비밀번호 리셋 토큰 평문 저장 | security-audit C3 | `EmailVerificationToken.token`, `PasswordResetToken.token`이 DB에 해싱 없이 저장됨. `RefreshToken`은 `hash_token()` 적용되어 있으나 이 두 모델은 누락. DB 유출 시 임의 계정 비밀번호 리셋 가능 | 🔴 P1 |

**수정 방법**: `RefreshToken`과 동일한 `hash_token()` 패턴을 `EmailVerificationToken`, `PasswordResetToken`에 적용

### 6.2 보안 — 이미 수정 확인된 항목 (참고)

| 이슈 | 소스 | 현재 상태 |
|------|------|----------|
| Kill Switch 상태 플래그만 (LS-C1) | review-local-server | ✅ `safeguard.py` — evaluate_all() 차단 + 미체결 취소 |
| 뮤테이션 엔드포인트 인증 없음 (LS-C2) | review-local-server | ✅ `require_local_secret()` 전 엔드포인트 적용 |
| OAuth 콜백 login() 미호출 (FE-C1) | review-frontend | ✅ `loginWithTokens()` 정상 호출 |
| WS 메시지 타입 불일치 (W1) | cross-review-api | ✅ `price_update`, `execution`, `status_change` 일치 |
| 토큰 필드명 `jwt` → `access_token` (A7) | cross-review-api | ✅ `access_token` 반환 |
| 응답 `count` 필드 누락 (A8) | cross-review-api | ✅ 전 엔드포인트 `{ success, data, count }` |
| WS sec 쿼리 파라미터 노출 (LS-C5) | review-local-server | ✅ 메시지 기반 인증, 쿼리 파라미터 미사용 |
| SECRET_KEY 기본값 취약 (SEC-C2) | cross-review-security | ✅ 기본값 빈 문자열 + `validate_settings()` 강제 |
| LogDB asyncio 차단 (LS-C4) | review-local-server | ✅ `async_write()` → `asyncio.to_thread()` |
| alertsClient 인증 미적용 (FE-C2) | review-frontend | ⚠️ axios 인터셉터 경유로 적용됨 (초기화 순서 의존) |

### 6.3 리서치 문서의 미반영 권장사항

| 권장 사항 | 소스 | 현재 상태 | 관련 Spec |
|----------|------|----------|----------|
| WS Origin 헤더 검증 | security-audit H3 | ❌ 미구현 — localhost 외부 접근 가능 | security-phase2에 미포함 |
| reset-password 토큰 URL 노출 | security-audit H6 | ❌ 미구현 — 브라우저 히스토리/Referer 노출 | security-phase2에 미포함 |
| 비밀번호 강도 검증 | security-audit H5 | ❌ 미구현 — 빈 문자열 허용 | security-phase2에 미포함 |
| KIS App Secret 모든 요청에 포함 | cross-review-security SEC-C1 | ❌ 미구현 — 토큰 발급 시에만 필요 | kis-adapter-completion에 미포함 |
| Daily budget 재시작 시 리셋 | review-local-server LS-H4 | ❌ 미구현 — 인메모리 카운터 | local-server-resilience에 미포함 |
| StrategyBuilder 편집 시 데이터 유실 | review-frontend FE-I5 | ❌ 미구현 — 폼 초기화됨 | dsl-client-parser에서 해결 예정 |
| Workbench UI (전문가 모드) | dual-audience-strategy | ❌ spec 없음 | 향후 검토 |
| Windows Credential Manager LLM 키 저장 | key-storage-trust | ❌ 미구현 — 브로커 키만 적용 | spec 없음 |

### 6.4 문서 갱신 필요

| 문서 | 이슈 | 상태 |
|------|------|------|
| Phase 1/2 문서 5건 | SUPERSEDED 헤더 미표기 | 🟡 혼란 가능 |
| architecture.md | Phase C 기능 8건 미기재 (E2E 암호화, WS Relay 등) | 🟡 |
| 6개 spec 상태 헤더 | "초안/진행 중"이나 실제 "구현 완료" | 🟡 |

---

## Part 7: 최종 미해결 항목 통합 (갱신)

### 카테고리별 미해결 항목 수

| 카테고리 | 항목 수 | 우선순위 | v4 대비 |
|---------|--------|---------|---------|
| Phase A 졸업 블로커 (버그 + UI) | 18건 | 🔴 즉시 | 유지 |
| 보안 미해결 (토큰 해싱) | 1건 | 🔴 운영 전 | **신규** |
| 보안 권장사항 미반영 | 5건 | 🟡 운영 전 | **신규** |
| 초안 Spec 미충족 기준 | ~100건 | 🔴-🟡 | 유지 |
| Legal UI/API (L1-L3) | 15건 | 🔴 운영 전 | 유지 |
| Alembic 마이그레이션 | 4건 | 🔴 구현 시 | 유지 |
| npm 의존성 추가 | 2건 | 🟡 구현 시 | 유지 |
| 코드 품질 권장사항 | 3건 | 🟡 | **신규** |
| 문서 갱신 | 3건 | 🟡 | **신규** |
| 제품 전략 미결정 | 6건 | 🟡 런칭 전 | 유지 |
| v2 기능 | 7건 | 🟢 v2 | 유지 |
| **총계** | **~164건** | | +12건 |

### security-phase2 spec에 추가해야 할 항목

현재 spec에 포함되지 않은 보안 이슈가 있으며, spec 갱신 또는 별도 spec이 필요:

| 항목 | 현재 위치 | 제안 |
|------|----------|------|
| 토큰 해싱 (C3) | 미반영 | security-phase2에 S5로 추가 |
| WS Origin 검증 (H3) | 미반영 | security-phase2에 S6로 추가 |
| 비밀번호 강도 (H5) | 미반영 | security-phase2에 S7로 추가 |
| reset-password URL 토큰 (H6) | 미반영 | security-phase2에 S8로 추가 |
| KIS App Secret 불필요 전송 (SEC-C1) | 미반영 | kis-adapter-completion에 K3로 추가 |
| LimitChecker 재시작 리셋 (LS-H4) | 미반영 | local-server-resilience에 R5로 추가 |

---

## Part 8: Plan 수정 필요 목록 (최종)

| Plan 파일 | 수정 내용 |
|----------|----------|
| `spec/local-server-resilience/plan.md` | R4를 relay-infra 의존으로 표기 + R5 (LimitChecker 영속화) 추가 |
| `spec/frontend-quality/plan.md` | F3에 legal 선행 의존 명시 |
| `spec/security-phase2/plan.md` | S4에 Alembic 마이그레이션 step 추가 + S5~S8 (토큰 해싱, WS Origin, 비밀번호 강도, URL 토큰) 추가 |
| `spec/security-phase2/spec.md` | 수용 기준에 S5~S8 추가 |
| `spec/kis-adapter-completion/plan.md` | K3 (App Secret 불필요 전송 제거) 추가 |
| `spec/legal/plan-v2.md` | Q1-Q5 결정 반영 필요 |
