# 전략 엔진 v2 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** DSL v2 파서 + 엔진 실행 모델 + 조건 상태 API + 카드 UI 모니터링을 구현하여, 프로 수준 전략 표현과 실시간 투명성을 제공한다.

**Architecture:** 4개 Phase 순차 구현. Phase 1(sv_core DSL 파서) → Phase 2(local_server 엔진) → Phase 3(상태 API + 클라우드) → Phase 4(프론트엔드). 각 Phase는 독립 테스트 가능. P0 항목 먼저 구현 후 P1 확장.

**Tech Stack:** Python 3.13 (sv_core, local_server, cloud_server), FastAPI, SQLAlchemy, React 19, TypeScript, Vite, Tailwind CSS, HeroUI, React Query

**Spec:** `spec/strategy-engine-v2/spec.md`

---

## 구현 단계 요약

| Phase | Task | 내용 | 의존 |
|-------|------|------|------|
| 1 | 1 | 토큰 확장 (ARROW, LBRACKET 등) | - |
| 1 | 2 | v2 AST 노드 | Task 1 |
| 1 | 3 | v2 파서 (상수, 규칙, IndexAccess, BETWEEN) | Task 1-2 |
| 1 | 4 | v1 호환 (매수:/매도: 자동 변환) | Task 3 |
| 1 | 5 | 내장 필드/함수 + ATR 지표 | Task 3 |
| 1 | 6 | v2 평가기 (우선순위, 상수 치환, 투명성) | Task 3-5 |
| 2 | 7 | PositionState | - |
| 2 | 8 | 지표 히스토리 링버퍼 | - |
| 2 | 9 | 조건 상태 추적기 | - |
| 2 | 10 | 엔진 통합 (v2 평가 경로 연결) | Task 6-9 |
| 3 | 11 | 조건 상태 API 라우터 | Task 9 |
| 3 | 12 | 클라우드 parameters 컬럼 | - |
| 4 | 13 | 프론트 타입 + 폴링 훅 | Task 11 |
| 4 | 14 | 모니터링 카드 컴포넌트 | Task 13 |
| 4 | 15 | StrategyList 통합 + DSL 편집 | Task 14 |
| - | 16 | 전체 회귀 테스트 | 전체 |

---

Plan 본문은 이전 커밋의 plan.md 참조. spec 변경사항(수식어→함수, @제거, 횟수/연속/실행횟수 통합, BETWEEN P1) 반영 완료.

핵심 변경점 (이전 plan 대비):
- `@` 토큰/ParamRef 삭제 → 상수는 FieldRef로 resolve (이름 해석 순서)
- Modifier AST 노드 삭제 → 상태 함수(횟수, 연속)는 일반 FuncCall로 파싱
- `달성` + `카운트` → `횟수`로 통합
- BETWEEN P2 → P1으로 승격, EBNF에 포함
- 무인자 함수 괄호 선택 (골든크로스 = 골든크로스())
- 매도 나머지 = 매도 전량의 의미적 별칭
