> 작성일: 2026-03-15 | 상태: 초안 | 미개발 사항 교차검증 리뷰 v4

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
| U2 | 엔진 신호등 카드 → ListView로 이동 | ❌ 미구현 | 계좌 상태 표시 안 됨 |
| U3 | 전략 실행/중지 버튼 | ❌ 미구현 | UI에서 전략 제어 불가 |
| U4 | 신호등 3색 (연결/엔진/킬스위치) | ❌ 미구현 | 시스템 상태 파악 불가 |
| U5 | Header 신호등 제거 | ❌ 미구현 | 중복 UI 잔존 |

#### 전략 목록 정보 부족 (strategy-list-info)

| ID | 항목 | 상태 |
|----|------|------|
| S1 | 전략 카드에 종목명 표시 | ❌ 미구현 |
| S2 | 전략 방향(매수/매도) 표시 | ❌ 미구현 |
| S3 | 실행 상태 표시 | ❌ 미구현 |

#### 프론트엔드 버그 — 4건

| 버그 | 심각도 | 위치 |
|------|--------|------|
| AuthContext setState 경쟁 조건 — RT 갱신 시 `localReady=false` 리셋 → 잔고 미로딩 | 🔴 높음 | `AuthContext.tsx` |
| useStockData quotesQuery/namesQuery 클로저 race condition | 🔴 높음 | `useStockData.ts` |
| 미체결 "취소" 버튼 stub — onClick 없음, PendingOrder.orderId 타입 누락 | 🟡 중간 | `ListView.tsx` |
| Settings 키 등록 후 localStatus 캐시 미갱신 (5초 지연) | 🟡 중간 | `Settings.tsx` |

#### 추가 품질 이슈 — 7건

| 이슈 | 영향 |
|------|------|
| App.tsx 중첩 Routes에 404 fallback 없음 | 잘못된 URL → 빈 화면 |
| useAccountStatus가 localReady 무관하게 폴링 → 인증 전 401 | 콘솔 에러 |
| cloudClient 401 인터셉터 — AuthContext 정리 불완전 | 로그아웃 후 잔여 상태 |
| LocalStatusData.broker에 `reason?: string` 없음 | 타입 불일치 |
| 장 상태 공휴일 무시 (useMarketContext 미사용) | 공휴일에도 "장중" 표시 |
| AdminGuard가 어드민 로그인 대신 메인으로 리다이렉트 | 어드민 접근 UX |
| Register.tsx 라이트 테마 불일치 | 디자인 일관성 |

---

### 1.2 broker-auto-connect 미완성 — 기존 리뷰에서 누락

Phase A 리뷰에서 **broker-auto-connect가 "구현 완료" 표기**되었으나, 실제로 프론트엔드 연동이 빠져 있다.

| 항목 | 상태 |
|------|------|
| F8: 키 등록 후 즉시 재연결 트리거 | ❌ Settings.tsx에 `POST /api/broker/reconnect` 호출 없음 |
| localClient.ts에 reconnect 함수 | ❌ 누락 |
| 키 미등록 온보딩 CTA | ❌ 미구현 |

---

### 1.3 legal plan-v2 상세 — L1/L2/L3 미구현

`spec/legal/plan-v2.md`에 상세 구현 계획이 있으나 전부 미시작:

**L1 (회원가입 약관 동의)**:
- [ ] 체크박스 2개 미체크 시 가입 버튼 비활성
- [ ] 서버 `terms_agreed=false` → 400
- [ ] `legal_consents` 테이블에 2건 기록
- [ ] 약관 링크 → 새 탭에서 전문 열람

**L2 (약관 열람)**:
- [ ] `/legal/terms`, `/legal/privacy`, `/legal/disclaimer` 페이지
- [ ] Settings에 "약관 및 고지" 섹션
- [ ] Footer에 3개 링크

**L3 (약관 버전 관리)**:
- [ ] `legal_documents` 테이블 + 시드 데이터
- [ ] `GET /api/v1/legal/documents/{type}` API
- [ ] `GET /api/v1/legal/consent/status` API
- [ ] 약관 업데이트 시 `requires_consent` 반환 → 재동의 모달

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

## Part 6: Plan 수정 필요 목록

| Plan 파일 | 수정 내용 |
|----------|----------|
| `spec/local-server-resilience/plan.md` | R4를 relay-infra 의존으로 표기, Phase C로 이동 |
| `spec/frontend-quality/plan.md` | F3에 legal 선행 의존 명시 |
| `spec/security-phase2/plan.md` | S4에 Alembic 마이그레이션 step 추가 |
| `spec/legal/plan-v2.md` | Q1-Q5 결정 반영 필요 |
