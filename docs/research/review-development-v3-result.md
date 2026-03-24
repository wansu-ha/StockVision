# development-plan-v3 종합 리뷰

> 리뷰 기준일: 2026-03-17 | 비교 문서: `roadmap.md`, `phase-a-review.md`, 각 spec 파일, 실제 코드
> 리뷰어: Claude Code (Opus 4.6)

---

## 핵심 발견: dev-plan-v3는 현재 프로젝트 상태와 심각하게 불일치한다

`development-plan-v3.md`(2026-03-15 작성, 03-17 갱신)가 `roadmap.md`(2026-03-12 갱신) 및 실제 코드 상태와 Phase B~D에서 전면적으로 불일치한다.

---

## 1. Phase 정의 불일치 — 같은 이름, 다른 내용

두 문서가 같은 Phase 레이블(A/B/C/D)을 사용하지만 **내용이 완전히 다르다**.

| Phase | dev-plan-v3 정의 | roadmap.md 정의 | 실제 현황 |
|-------|----------------|----------------|---------|
| **A** | 기반 안정화 (버그/보안/KIS/UI) | "켜면 바로 쓸 수 있다" | **일치** — 두 문서 모두 완료 |
| **B** | IndicatorProvider, DSL TS 파서, 차트 타임프레임, 로컬 견고성 | System Trader, 규칙 카드 구조화, 차트 타입 전환, 이벤트 마커 | **불일치** — roadmap B 완료, dev-plan B 미착수 |
| **C** | relay-infra 8단계, remote-ops 9단계 | P&L, OpsPanel, 실행 타임라인, exe 패키징, 온보딩, 원격 제어 | **불일치** — roadmap C1~C5 완료 + C6 핵심 구현, dev-plan C 전부 미착수 |
| **D** | 제품 결정, 문서 갱신, 프로덕션 하드닝 | 실시간 경고, 시장 브리핑, 종목 분석, 텔레그램 | **불일치** — roadmap D1~D3 구현 완료, dev-plan D는 다른 내용 |

**근본 원인**: roadmap.md는 "사용자 가치 단위"로, dev-plan-v3는 "기술 레이어"로 Phase를 나눈다.

---

## 2. 상태 갱신 누락

### 2-1. Phase A 완료 기준 미체크
| 항목 | dev-plan-v3 상태 | 실제 상태 | 근거 |
|------|-----------------|---------|------|
| UI 미구현 U2~U5, S1~S3 | `[ ]` | **완료** | `phase-a-review.md` — "이미 구현됨 확인" |
| 품질 이슈 Q1~Q7 | `[ ]` | **대부분 완료** | `phase-a-implementation.md` |

### 2-2. dev-plan-v3에 존재하지 않는 구현 완료 항목 11건

roadmap.md 기준 완료되었으나 dev-plan-v3에 **아예 없는** 항목:

**Phase B (완료):**
- System Trader Phase 1 (`spec/system-trader/spec.md` — 구현 완료)
- 규칙 카드 구조화 (`spec/rule-card-structured/spec.md` — 구현 완료)
- 차트 타입 전환 (`spec/chart-type-switcher/spec.md` — 구현 완료)
- 차트 이벤트 마커 (`spec/chart-event-markers/spec.md` — 구현 완료)

**Phase C (완료):**
- OpsPanel v2 (`spec/ops-panel-v2/spec.md` — 구현 완료)
- 실행 로그 타임라인 (`spec/execution-log-timeline/spec.md` — 구현 완료)
- exe 패키징 + 딥링크 (`spec/local-exe-deeplink/spec.md` — 구현 완료)
- 온보딩 v2 (`spec/onboarding-v2/spec.md` — 구현 완료)

**Phase D (완료):**
- 실시간 경고 (`spec/realtime-alerts/spec.md` — 구현 완료)
- 시장 브리핑 (`spec/market-briefing/spec.md` — 구현 완료)
- 종목별 분석 (`spec/stock-analysis/spec.md` — 구현 완료)

### 2-3. Phase C relay/remote — 부분 구현됨

`spec/c6-remote-ops/reports/260312-report.md` 기준:
- relay_manager, ws_relay, e2e_crypto 구현 완료 (C6-a)
- useRemoteControl, KillSwitchFAB, PWA 구현 완료 (C6-c)
- 16/16 브라우저 테스트 PASS
- 미완: FCM 푸시, C7(재개/무장), C8(외부 주문 감지)

---

## 3. dev-plan-v3 Phase B 항목 — 실제 코드 검증

| 항목 | dev-plan-v3 상태 | 실제 코드 | spec 상태 |
|------|-----------------|---------|----------|
| B1: IndicatorProvider | 🔴 미착수 | **코드 존재** (`local_server/engine/indicator_provider.py`) | 초안 |
| B2: DSL TS 파서 | 🔴 미착수 | **미구현** (프론트엔드에 TS 파서 없음) | 초안 |
| B3/B4: 차트 타임프레임 | 🟡 | **미구현** (일봉만 지원) | 초안 |
| B5: 로컬 서버 견고성 R1~R5 | 🟡 | **부분 구현** (R1, R3, R5 존재) | 초안 |

→ B2/B3/B4 미구현 표시는 정확. B1/B5는 부분 구현이므로 상태 업데이트 필요.

---

## 4. 구조적 문제

1. **마스터 문서 2개**: roadmap.md와 dev-plan-v3가 모두 "현재 개발 방향"을 기술 → 어느 것이 정본인지 불명확
2. **깨진 참조**: `spec/phase-a-cleanup/plan.md` 파일 미존재 (A8에서 참조)
3. **Alembic/npm 목록**: Phase A까지만 기록. Phase B~D 구현분의 마이그레이션, npm 의존성 누락
4. **v2 vs Phase D 불일치**: dev-plan-v3는 텔레그램을 v2(런칭 후)로 미루지만 roadmap.md는 Phase D(현재)에 포함

---

## 5. 추천 조치

### 조치 1 (최우선): 역할 분리 명확화
dev-plan-v3 헤더에 추가:
> "Phase 현황은 `docs/roadmap.md`가 정본. 이 문서는 Phase A 시점 기술 설계 메모이며, Phase B~D 구현분은 각 spec 상태 헤더로 추적한다."

### 조치 2: Phase A 완료 기준 체크박스 업데이트
- `[ ] UI 미구현 U2~U5, S1~S3` → `[x]`
- `[ ] 품질 이슈 Q1~Q7` → 부분 체크 + 잔여 명시

### 조치 3: Phase B~D 현황 반영
- **옵션 A (권장)**: dev-plan-v3를 "히스토리 문서"로 동결, roadmap.md에 잔여 기술 항목 통합
- **옵션 B**: dev-plan-v3를 전면 갱신하여 roadmap.md와 Phase 정의 일치

### 조치 4: 깨진 참조 수정
- `spec/phase-a-cleanup/plan.md` → 실제 문서 또는 "별도 추적 없음" 표기

### 조치 5: dev-plan-v3 B1~B5 위치 결정
roadmap.md에 포함되지 않은 미착수 기술 항목들(IndicatorProvider, DSL TS 파서, 차트 타임프레임, 로컬 견고성)의 배치 결정 필요.
