# 프로젝트 정리 작업 — 2026-04-19

> 종합 점검 결과를 기반으로 한 일괄 정리 작업 기록
> 선행 리포트: `docs/research/spec-audit-2026-04-19.md`

## 작업 배경

사용자 요청으로 프로젝트 전반을 점검하던 중:
- 초안/확정 상태로 남아있는 spec 54개가 실제로는 대부분 구현 완료 상태임을 확인
- 프론트엔드에 프로토타입 잔여물(Proto A/B/C, ~1,449줄) 발견
- 문서·코드 동기화 누락이 다수 누적

2단계 검증(샘플 10건 직접 확인, 10/10 정확) 후 일괄 정리 진행.

---

## Batch A — 코드 정리

### Proto 프로토타입 페이지 삭제

- `frontend/src/pages/ProtoA.tsx` (290줄) — 삭제
- `frontend/src/pages/ProtoB.tsx` (288줄) — 삭제
- `frontend/src/pages/ProtoC.tsx` (871줄) — 삭제
- `frontend/src/App.tsx` — import 3줄, DEV-only 라우트 블록 7줄 제거

판단 근거:
1. 전부 Mock 데이터만 사용 (실제 API 연동 없음)
2. 주석으로 "claude/design-frontend-Kd0vV", "codex/frontend-admin-design" 브랜치 기반임이 명시 — 과거 디자인 후보
3. 최근 커밋 `25303fb`에서 `UnifiedLayout` + `MainDashboard`를 정본으로 채택 — 디자인 결정 완료
4. 네비게이션 링크 없음 (직접 URL 입력해야만 접근 가능)
5. 단일 커밋 `d205ab2`로 추가됨 → 필요 시 git에서 복구 가능

TypeScript 컴파일 통과 확인.

### auth-security 상태 불일치 수정

- `spec/auth-security/plan.md`: 상태 `초안` → `구현 완료` (spec.md와 일치)

---

## Batch B — spec 54개 상태 헤더 일괄 갱신

전수 조사 결과(spec-audit-2026-04-19.md)에 따라 일괄 처리:

### 구현 완료로 전환 (48개)

sed 일괄 처리(`상태: 초안` → `상태: 구현 완료`, `상태: 확정` → `상태: 구현 완료`):

ai-core-service, auto-update-improvement, dsl-schema-api, preset-expansion, strategy-engine-v2,
v1-polish, fix-e2e-preset-selector, frontend-layout-consistency, runtime-host-separation,
chart-timeframe(갱신 정보 유지), doc-refresh, docs-cleanup, engine-live-execution, legal,
phase-a-cleanup, frontend-main-ux, production-hardening, relay-infra, remote-control, remote-ops,
local-server-resilience, realtime-alerts, stability, trading-safety, ux-polish,
rule-card-structured, system-trader, backtest-engine, minute-bar-collection, minute-indicators,
strategy-lifecycle, frontend-test-expansion, watchlist-heart.

### 보류로 전환 (4개)

- `spec/auth-extension/spec.md`, `plan.md` → "보류 (2026-03-24 결정, v2 이후)"
  - 근거: `memory/MEMORY.md`에 명시된 결정. 코드는 있으나 운영 비활성
- `spec/external-order-detection/spec.md`, `plan.md` → "보류 (GHOST 감지만 구현, 외부 주문 경고 미착수)"
  - 근거: roadmap C8 "미착수". `ExternalOrderEvent` 모델/경고 UI 등 핵심 부분 미구현

### 부분 구현으로 전환 (1개)

- `spec/prod-hardening/spec.md` → "부분 구현 (H1 Alembic + H2 로그 레벨 완료, H3~ 미구현)"

### 구현 완료로 전환 (특수 케이스, 1개)

- `spec/review-missing-features/reports/pre-deploy-plan.md` → "구현 완료 (P1~P6 전항목 커밋 완료)"

**합계 54 = 48 + 4 + 1 + 1 ✓**

---

## Batch C — 중복/선후관계 명시

### remote-control SUPERSEDED 마크

- `spec/remote-control/spec.md`, `plan.md` 상태 헤더에 `(SUPERSEDED by spec/remote-ops/)` 추가
- 근거: `spec/remote-ops/spec.md` 헤더가 명시적으로 "remote-control spec 기능 부분을 대체"

### prod-hardening 선행 관계 명시

- `spec/prod-hardening/spec.md` 헤더의 선행 필드에 `production-hardening` (M1~M6 완료) 추가
- prod-hardening은 production-hardening의 v2 후속이지만 별개 피처 (병합 안 함)

---

## Batch D-1 — 구조 개선

### sv_core 패키징

- `sv_core/pyproject.toml` 신규 생성
- `cloud_server/requirements.txt:44` `# -e ../sv_core` 주석 해제
- `local_server/requirements.txt` 말미에 `-e ../sv_core` 추가
- Dockerfile은 기존 `COPY sv_core/` 방식 유지 (동작 중이므로 별도 검증 후 개선)

### docs/archive/ 재배치

- `docs/archive/` 디렉토리 생성
- `docs/development-plan.md` → `docs/archive/development-plan-v1.md`
- `docs/development-plan-v2.md` → `docs/archive/development-plan-v2.md`
- v3는 `docs/` 최상위에 유지 (최신)

### spec-lifecycle.md 규칙 보완

- `부분 구현`, `보류` 상태 카테고리 추가
- `SUPERSEDED` 마크 가이드 추가
- `plan만 존재` 케이스 명시 (spec 없이 plan만 작성되는 작은 작업)

---

## 보류한 작업 (별도 진행 권장)

### 프론트엔드 테스트 확장

현재 4개(`frontend/src/**/*.test.ts(x)`) → 확장 필요. 별도 spec으로 진행 권장.
기준: backtest, auth, admin, onboarding, strategy-builder, strategy, strategy-v2는 E2E 존재.
추가 대상: MainDashboard, Settings, components 레벨 unit test.

### Dockerfile 개선

`cloud_server/Dockerfile` — `COPY sv_core/` 방식을 `pip install ./sv_core`로 전환할지 검토.
현재는 동작 중이므로 별도 이슈로 분리.

---

## 변경 통계

- 코드 감축: ~1,449줄 (Proto*)
- spec/plan 헤더 수정: 57개 파일
- 신규 파일: 3개 (pyproject.toml, 이 리포트, spec-audit 리포트)
- 아카이브 이동: 2개 문서
- 규칙 문서 갱신: 1개

## 검증

- [x] TypeScript 컴파일 통과 (Proto 삭제 후)
- [ ] 프론트엔드 빌드 (`npm run build`) — 커밋 전 실행 권장
- [ ] Python 임포트 동작 확인 (sv_core 패키징 후)
