# DSL 클라이언트 파서 — TypeScript 파서 포팅 + ConditionEditor 연동

> 작성일: 2026-03-15 | 상태: 확정

## 1. 배경

StockVision의 전략 규칙은 DSL 스크립트로 표현된다.
서버(Python)에는 완전한 파서가 존재하나 (`sv_core/parsing/`),
프론트엔드에는 DSL ↔ 폼 조건 간 변환 로직이 없어 규칙 편집에 제약이 있다.

### 현재 상태

**서버 (Python)** — `sv_core/parsing/`:
- `lexer.py`: 토큰화
- `parser.py`: AST 생성
- `ast_nodes.py`: AST 노드 정의
- `evaluator.py`: AST 평가

**프론트엔드** — 불완전:
- `conditionsToDsl()` (`services/rules.ts:21-29`): 폼 → DSL 단방향 변환만 존재
  ```typescript
  // "매수: rsi_14 > 30 AND macd < 0\n매도: price < 50000" 형식
  ```
- `ConditionEditor.tsx`: 드롭다운 기반 UI (type/field/operator/value)
- **역변환 없음**: DSL 문자열 → 폼 조건 파싱 불가

### 문제

1. 서버에서 저장된 기존 규칙을 프론트에서 편집할 수 없음 (DSL → 폼 변환 불가)
2. 복잡한 DSL (중첩 조건, 함수 호출)은 폼으로 표현 불가
3. 프론트에서 DSL 문법 검증 불가 (서버 왕복 필요)

## 2. 범위

### 2.1 포함

| # | 항목 |
|---|------|
| D1 | TypeScript DSL 파서 (lexer + parser) |
| D2 | DSL → 폼 조건 역변환 (`dslToConditions`) |
| D3 | ConditionEditor에 DSL 미리보기 + 직접 편집 모드 |
| D4 | DSL 문법 에러 인라인 표시 |

### 2.2 제외

- 서버 파서 변경 (Python 파서는 그대로 유지)
- 복잡한 AST 기능 포팅 (함수 호출, 중첩 괄호 등은 v2)
- DSL 자동완성/인텔리센스

## 3. 요구사항

### D1: TypeScript DSL 파서

**지원 문법** (v1 — 서버 파서의 서브셋):

```
규칙      := "매수:" 조건식 "\n" "매도:" 조건식
조건식    := 조건 (("AND" | "OR") 조건)*
조건      := 필드 연산자 값
필드      := identifier ("." identifier)*    # e.g., rsi_14, macd.signal
연산자    := ">" | ">=" | "<" | "<=" | "==" | "!="
값        := 숫자 | 문자열
```

**요구사항**:
- `parseDsl(script: string): ParseResult` 함수
- `ParseResult`: `{ success: boolean, buy?: ConditionGroup, sell?: ConditionGroup, errors?: ParseError[] }`
- `ParseError`: `{ line: number, column: number, message: string }`
- 파싱 실패 시에도 가능한 부분까지 파싱 (부분 결과 반환)
- 서버 파서와 동일한 결과를 보장할 필요 없음 (폼 변환 용도)

### D2: DSL ↔ 폼 변환

**요구사항**:
- `dslToConditions(script: string): { buyConditions: Condition[], sellConditions: Condition[], operator: 'AND' | 'OR' }`
- 기존 `conditionsToDsl()` 유지 (역함수 관계)
- 변환 불가능한 복잡 DSL → 에러 반환 + "직접 편집 모드" 유도
- round-trip 보장: `conditionsToDsl(dslToConditions(dsl)) ≈ dsl` (공백/포맷 차이 허용)

### D3: ConditionEditor 확장

**요구사항**:
- "폼 모드" (현재) + "스크립트 모드" (DSL 직접 편집) 토글
- 폼 모드: 기존 드롭다운 UI, 변경 시 DSL 미리보기 표시
- 스크립트 모드: textarea에 DSL 직접 입력, 실시간 파싱 + 에러 표시
- 모드 전환 시 자동 변환 (가능한 경우)

### D4: 에러 표시

**요구사항**:
- 스크립트 모드에서 문법 에러 위치를 인라인 표시
- 에러 메시지 한국어 (예: "3번째 줄: 알 수 없는 연산자 '==='")
- 디바운스 적용 (300ms) — 타이핑 중 실시간 검증

## 4. 변경 파일 (예상)

| 파일 | 변경 |
|------|------|
| `frontend/src/utils/dslParser.ts` | D1: **신규** — lexer + parser |
| `frontend/src/utils/dslConverter.ts` | D2: **신규** — DSL ↔ 조건 변환 |
| `frontend/src/services/rules.ts` | D2: `conditionsToDsl` 리팩토링, `dslToConditions` 추가 |
| `frontend/src/components/ConditionEditor.tsx` | D3: 모드 토글 + DSL 미리보기 |
| `frontend/src/components/DslEditor.tsx` | D3: **신규** — 스크립트 편집 컴포넌트 |
| `frontend/src/pages/StrategyBuilder.tsx` | D3: 에디터 모드 상태 관리 |

## 5. 수용 기준

- [ ] `parseDsl("매수: rsi_14 > 30 AND macd < 0\n매도: price < 50000")`이 올바른 구조를 반환한다
- [ ] `dslToConditions()` → `conditionsToDsl()` round-trip이 동일 결과를 생성한다
- [ ] 서버에 저장된 기존 규칙을 프론트에서 폼 모드로 편집할 수 있다
- [ ] 문법 에러가 있는 DSL 입력 시 에러 위치와 메시지가 표시된다
- [ ] 폼 모드 ↔ 스크립트 모드 전환 시 데이터가 유지된다
- [ ] 변환 불가능한 복잡 DSL은 스크립트 모드에서만 편집 가능하다

## 6. 참고

- 서버 파서: `sv_core/parsing/` (parser.py, lexer.py, ast_nodes.py, evaluator.py)
- 현재 변환: `frontend/src/services/rules.ts` (conditionsToDsl)
- 조건 에디터: `frontend/src/components/ConditionEditor.tsx`
- 전략 빌더: `frontend/src/pages/StrategyBuilder.tsx`
- Condition 타입: `frontend/src/types/rule.ts`
