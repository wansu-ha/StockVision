# 문서 갱신 명세서 (T3-D2)

> 작성일: 2026-03-17 | 상태: 구현 완료

---

## 1. 목표

Phase B~D 구현 완료 후 갱신되지 않은 문서를 정리한다.
- 폐기된 Phase 1/2 문서에 SUPERSEDED 헤더 추가
- `architecture.md`에 Phase B~D 기능 반영
- spec 상태 헤더 최신화

---

## 2. SUPERSEDED 헤더 추가 대상

### 이미 표기 완료 (확인됨)

| 파일 | 대체 문서 |
|------|----------|
| `docs/development-plan.md` | → `docs/development-plan-v2.md` |
| `docs/integrated-development-plan.md` | → `docs/architecture.md` |
| `docs/architecture-phase3.md` | → `docs/architecture.md` |
| `spec/api-server/spec.md` | → `spec/cloud-server/spec.md` |
| `spec/data-server/spec.md` | → `spec/cloud-server/spec.md` |

### 추가 필요

| 파일 | 사유 | 대체 문서 |
|------|------|----------|
| `docs/project-blueprint.md` | Phase 1/2 청사진. 현재 구조와 불일치 | → `docs/roadmap.md` |
| `docs/future-improvements.md` | MVP 이후 개선 목록. 대부분 구현 완료 | → `docs/roadmap.md` |
| `docs/architecture-diagram.md` | `architecture.md` 기반이라 암시적 참조만 있음. 명시적 표기 필요 | → `docs/architecture.md` |
| `docs/development-plan-v2.md` | "참고용" 표기는 있으나 SUPERSEDED 명시 없음 | → `docs/development-plan-v3.md` |

**헤더 형식**:
```markdown
> ⚠️ SUPERSEDED — 이 문서는 더 이상 유지되지 않습니다. 최신 문서: `{대체 문서 경로}`
```

**수용 기준**:
- [ ] 위 4개 파일에 SUPERSEDED 헤더 추가
- [ ] 본문 내용은 수정하지 않음 (히스토리 보존)

---

## 3. architecture.md 갱신

**현재**: 2026-03-09 갱신. Custom LLM 통합(v2) 반영까지.
**누락**: Phase B~D에서 추가된 주요 기능:

| 미반영 기능 | spec |
|------------|------|
| System Trader (전략 엔진) | `spec/system-trader/spec.md` |
| 규칙 카드 구조화 (DSL) | `spec/rule-card-structured/spec.md` |
| OpsPanel v2 | `spec/ops-panel-v2/spec.md` |
| exe 패키징 + 딥링크 | `spec/local-exe-deeplink/spec.md` |
| relay/원격 제어 (e2e 암호화) | `spec/c6-remote-ops/spec.md` |
| 실시간 경고 시스템 | `spec/realtime-alerts/spec.md` |
| 시장 브리핑 | `spec/market-briefing/spec.md` |
| 종목별 분석 | `spec/stock-analysis/spec.md` |

**변경 범위**:
- §아키텍처 다이어그램에 relay/WS 경로 추가
- §로컬 서버 섹션에 전략 엔진, exe 패키징 설명 추가
- §클라우드 서버 섹션에 시장 브리핑, 종목 분석, 실시간 경고 추가
- §프론트엔드 섹션에 OpsPanel v2, 원격 제어 추가

**수용 기준**:
- [ ] 위 8개 기능이 architecture.md에 최소 1줄 이상 언급
- [ ] 갱신일 헤더 업데이트
- [ ] 기존 구조(섹션 순서) 유지

---

## 4. spec 상태 헤더 — 확인 완료

아래 7건은 이미 `구현 완료` 상태로 갱신됨 (추가 작업 없음):

- `spec/system-trader/spec.md`
- `spec/rule-card-structured/spec.md`
- `spec/chart-type-switcher/spec.md`
- `spec/chart-event-markers/spec.md`
- `spec/ops-panel-v2/spec.md`
- `spec/execution-log-timeline/spec.md`
- `spec/realtime-alerts/spec.md`

---

## 5. 수정 파일 종합

| 파일 | 작업 |
|------|------|
| `docs/project-blueprint.md` | SUPERSEDED 헤더 추가 |
| `docs/future-improvements.md` | SUPERSEDED 헤더 추가 |
| `docs/architecture-diagram.md` | SUPERSEDED 헤더 추가 |
| `docs/development-plan-v2.md` | SUPERSEDED 헤더 추가 |
| `docs/architecture.md` | Phase B~D 기능 반영 |
