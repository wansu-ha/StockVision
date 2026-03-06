# 규칙 데이터 모델 구현 계획서 (rule-model)

> 작성일: 2026-03-07 | 상태: 초안
>
> **기반**: `spec/rule-model/spec.md` v2 (DSL 기반)

---

## 1. 아키텍처

```
┌─────────────────────────────────────────────────────┐
│                   sv_core/parsing/                  │
│  ┌──────────┐ ┌──────────┐ ┌────────────────────┐   │
│  │  Lexer   │→│  Parser  │→│  AST Nodes         │   │
│  └──────────┘ └──────────┘ │  (BuyBlock,         │   │
│                            │   SellBlock,         │   │
│  ┌──────────────────────┐  │   BinOp, Not, ...)  │   │
│  │  builtin_registry    │  └────────────────────┘   │
│  │  (fields, functions, │                           │
│  │   patterns)          │  ┌────────────────────┐   │
│  └──────────────────────┘  │  Evaluator         │   │
│                            │  (AST → bool)      │   │
│                            └────────────────────┘   │
└─────────────────────────────────────────────────────┘
        ▲ validate only              ▲ full evaluate
        │                            │
┌───────┴──────────┐       ┌─────────┴──────────────┐
│  Cloud Server    │       │  Local Server           │
│  POST/PUT rules  │       │  EngineScheduler        │
│  → parse + reject│       │  → parse + eval + exec  │
│    (400 on error)│       │    (1분 주기)            │
└──────────────────┘       └─────────────────────────┘
```

**데이터 흐름**: 프론트엔드(폼 → script 생성) → 클라우드(검증 + 저장) → 로컬(sync → 파싱 → 평가 → 주문)

**공유 패키지**: `sv_core/parsing/`을 클라우드와 로컬 양쪽에서 import. 클라우드는 파싱(검증)만, 로컬은 파싱+평가 모두 사용.

---

## 2. 수정 파일 목록

### 2.1 새 파일 (sv_core/parsing/)

| 파일 | 내용 |
|------|------|
| `sv_core/parsing/__init__.py` | 패키지 공개 API (`parse`, `validate`, `evaluate`) |
| `sv_core/parsing/tokens.py` | TokenType enum, Token dataclass |
| `sv_core/parsing/lexer.py` | 한국어/영문 토큰화. 키워드: `매수`, `매도`, `AND`, `OR`, `NOT` |
| `sv_core/parsing/ast_nodes.py` | AST 노드 클래스 (Script, BuyBlock, SellBlock, CustomFunc, BinOp, UnaryOp, Comparison, FuncCall, FieldRef, NumberLit, BoolLit) |
| `sv_core/parsing/parser.py` | 재귀 하강 파서. 연산자 우선순위 7단계 (DSL 리서치 §3.3) |
| `sv_core/parsing/builtins.py` | 내장 필드/함수/패턴 함수 레지스트리 (spec §2.2, §3) |
| `sv_core/parsing/evaluator.py` | AST 평가기. 시세 데이터 컨텍스트에서 boolean 반환 |
| `sv_core/parsing/errors.py` | DSLSyntaxError, DSLTypeError — 위치(line, col) + 한국어 메시지 |

### 2.2 클라우드 서버 수정

| 파일 | 변경 내용 |
|------|----------|
| `cloud_server/models/rule.py` | `script`(Text), `execution`(JSON), `trigger_policy`(JSON), `priority`(Integer) 컬럼 추가. `order_type`, `qty`, `max_position_count`, `budget_ratio` 유지 (하위 호환) |
| `cloud_server/api/rules.py` | `RuleCreateBody`/`RuleUpdateBody`에 `script`, `execution`, `trigger_policy`, `priority` 추가. 기존 필드 optional 유지 |
| `cloud_server/services/rule_service.py` | create/update에서 `script` 존재 시 `validate_dsl_script()` 호출. `_rule_to_dict()`에 새 필드 추가 |
| `cloud_server/core/validators.py` | `validate_dsl_script(script: str)` 추가 — `sv_core.parsing.parse()` 호출, 실패 시 ValueError (위치+메시지) |

### 2.3 로컬 서버 수정

| 파일 | 변경 내용 |
|------|----------|
| `local_server/engine/models.py` | `RuleConfig` 재구조: `script`, `execution`, `trigger_policy` 필드 추가. `buy_conditions`/`sell_conditions` 유지 (하위 호환). `from_dict()` 갱신 |
| `local_server/engine/evaluator.py` | `RuleEvaluator.evaluate()` — `script is not None`이면 DSL 경로, 아니면 기존 JSON 경로. AST 캐시 추가 |
| `local_server/engine/executor.py` | 매도 보호: `side == SELL`일 때 `보유수량 > 0` 사전 확인. `execution` dict에서 order_type/qty 추출 |

### 2.4 프론트엔드 수정

| 파일 | 변경 내용 |
|------|----------|
| `frontend/src/types/strategy.ts` | `Rule` 인터페이스에 `script`, `execution`, `trigger_policy` 추가. 기존 `side`/`operator`/`conditions` deprecated |
| `frontend/src/services/rules.ts` | API 클라이언트: 클라우드 서버(`/api/v1/rules`)로 요청. `script` 필드 포함 |
| `frontend/src/pages/StrategyBuilder.tsx` | 폼 UI 유지하되, 저장 시 폼 값 → DSL script 문자열로 변환하여 전송 (v1 전략) |

---

## 3. 구현 순서

### Step 1: DSL 파서 — 토큰/AST/에러 (sv_core/parsing)

**파일**: `tokens.py`, `ast_nodes.py`, `errors.py`

**작업**:
- TokenType enum 정의 (NUMBER, IDENT, KEYWORD_BUY, KEYWORD_SELL, AND, OR, NOT, LPAREN, RPAREN, COMMA, COLON, EQ, ASSIGN, COMPARE_OP, NEWLINE, COMMENT, EOF)
- AST 노드 dataclass 정의 (Script, BuyBlock, SellBlock, CustomFuncDef, BinOp, UnaryOp, Comparison, FuncCall, FieldRef, NumberLit, BoolLit)
- DSLSyntaxError, DSLTypeError (line, col, message 포함)

**verify**: 각 클래스 import 성공, 인스턴스 생성 확인

### Step 2: DSL 파서 — 렉서 (sv_core/parsing)

**파일**: `lexer.py`, `builtins.py`

**작업**:
- 내장 필드/함수/패턴 함수 레지스트리 (`builtins.py`)
- Lexer: 입력 문자열 → Token 리스트 변환
  - 한국어 식별자 지원 (유니코드)
  - `--` 주석 무시
  - 연산자: `>=`, `<=`, `>`, `<`, `==`, `!=`, `+`, `-`, `*`, `/`
  - 키워드: `매수`, `매도`, `AND`, `OR`, `NOT`, `true`, `false`
  - `=` (커스텀 함수 정의) vs `==` (비교) 구분

**verify**: 렉서 단위 테스트 — spec §2.3 예시 스크립트 토큰화 성공

### Step 3: DSL 파서 — 파서 (sv_core/parsing)

**파일**: `parser.py`, `__init__.py`

**작업**:
- 재귀 하강 파서 구현
  - 연산자 우선순위: `OR` < `AND` < `NOT` < 비교(`>`, `<`, `>=`, `<=`, `==`, `!=`) < 가감(`+`, `-`) < 승제(`*`, `/`) < 단항(`-`) < 호출/괄호
  - 최상위: 커스텀 함수 선언*, 매수: 블록, 매도: 블록
  - 커스텀 함수: `이름() = 식` (후방 참조 금지, 재귀 금지)
  - 매수:/매도: 둘 다 필수, 각 1회
  - 타입 체크: 비교는 숫자↔숫자, 논리는 boolean↔boolean
- `__init__.py`에 `parse(script: str) -> Script` 공개

**verify**: spec §2.3 예시 + 에러 케이스 (매도 누락, 타입 오류, 재귀 참조) 파싱 테스트

### Step 4: DSL 평가기 (sv_core/parsing)

**파일**: `evaluator.py`

**작업**:
- `evaluate(ast: Script, context: dict) -> tuple[bool, bool]` — (매수 결과, 매도 결과)
- context dict 구조: `{"현재가": Decimal, "거래량": int, "RSI": Callable, "MA": Callable, ...}`
- 내장 함수 호출: context에서 callable 조회 → 인자 전달 → 결과 반환
- 내장 패턴 함수: builtins 레지스트리에서 정의 조회 → 인라인 평가
- 커스텀 함수: 선언 순서대로 평가, 결과 캐시
- null 전파: 어디서든 None 발생 → 해당 블록 전체 False (spec §7.2)
- 0으로 나누기 → None (null 전파로 블록 실패)

**verify**: 골든크로스+RSI 조합 시나리오, null 전파 시나리오, 0 나누기 시나리오

### Step 5: 클라우드 데이터 모델 + 검증

**파일**: `cloud_server/models/rule.py`, `cloud_server/core/validators.py`

**작업**:
- TradingRule 모델에 컬럼 추가:
  ```python
  script = Column(Text, nullable=True)
  execution = Column(JSON, nullable=True)
  trigger_policy = Column(JSON, nullable=True, default={"frequency": "ONCE_PER_DAY"})
  priority = Column(Integer, default=0)
  ```
- 기존 `order_type`, `qty`, `max_position_count`, `budget_ratio` 컬럼 유지 (하위 호환)
- `validators.py`에 `validate_dsl_script()` 추가:
  ```python
  from sv_core.parsing import parse
  def validate_dsl_script(script: str) -> None:
      parse(script)  # DSLSyntaxError/DSLTypeError 시 ValueError 변환
  ```

**verify**: 유효 DSL → 통과, 잘못된 DSL → ValueError (위치+메시지)

### Step 6: 클라우드 API + 서비스

**파일**: `cloud_server/api/rules.py`, `cloud_server/services/rule_service.py`

**작업**:
- Pydantic 스키마 갱신:
  - `RuleCreateBody`: `script: str | None = None`, `execution: dict | None = None`, `trigger_policy: dict | None = None`, `priority: int = 0` 추가
  - `RuleUpdateBody`: 동일 필드 optional 추가
- `rule_service.create_rule()`: `script` 존재 시 `validate_dsl_script()` 호출
- `rule_service.update_rule()`: `script` 변경 시 `validate_dsl_script()` 호출
- `_rule_to_dict()`: `script`, `execution`, `trigger_policy`, `priority` 추가

**verify**: POST/PUT에 script 포함 → 검증 통과 → 저장 성공. 잘못된 script → 400

### Step 7: 로컬 엔진 모델 + 평가기

**파일**: `local_server/engine/models.py`, `local_server/engine/evaluator.py`

**작업**:
- `RuleConfig` 재구조:
  ```python
  script: str | None = None
  buy_conditions: dict | None = None  # 하위 호환
  sell_conditions: dict | None = None
  execution: dict = field(default_factory=...)
  trigger_policy: dict = field(default_factory=...)
  ```
  - `from_dict()` 갱신: 새 필드 파싱 + 기존 필드 호환
- `RuleEvaluator` DSL 경로 추가:
  ```
  if rule.script is not None:
      ast = cache.get(rule.id) or parse(rule.script)
      buy, sell = evaluate(ast, context)
  else:
      buy = self._eval_json(rule.buy_conditions, ...)
      sell = self._eval_json(rule.sell_conditions, ...)
  ```
  - AST 캐시: `{rule_id: (script_hash, ast)}` — script 변경 시 무효화
- `MarketSnapshot` → evaluator 컨텍스트 dict 변환 로직

**verify**: DSL 규칙 평가 → 매수/매도 판정 정확. JSON 규칙 → 기존 동작 유지

### Step 8: 로컬 실행기 — 매도 보호

**파일**: `local_server/engine/executor.py`

**작업**:
- 매도 주문 실행 전 `보유수량 > 0` 확인 추가 (spec §7.3)
- `execution` dict에서 `order_type`, `qty_type`, `qty_value`, `limit_price` 추출
- `trigger_policy` 처리: `ONCE` → 실행 후 `is_active=false` 설정

**verify**: 미보유 종목 매도 시도 → REJECTED. ONCE 트리거 → 1회 실행 후 비활성화

### Step 9: 프론트엔드 타입 + API 클라이언트

**파일**: `frontend/src/types/strategy.ts`, `frontend/src/services/rules.ts`

**작업**:
- `Rule` 인터페이스에 `script`, `execution`, `trigger_policy` 추가
- `Execution`, `TriggerPolicy` 인터페이스 정의
- API 클라이언트: 클라우드 서버 URL로 변경, `script` 필드 포함
- 서버 에러 응답 (400 DSL 에러) 파싱 → 사용자에게 에러 위치/메시지 표시

**verify**: TypeScript 빌드 성공. API 호출 시 새 필드 포함

### Step 10: 프론트엔드 폼 — DSL 변환

**파일**: `frontend/src/pages/StrategyBuilder.tsx`

**작업**:
- 기존 폼 UI 유지 (v1: 조건 드롭다운/값 입력)
- 저장 시 폼 값 → DSL script 문자열 생성 함수 구현
  - 예: `{field: "RSI(14)", op: "<=", value: 30}` → `RSI(14) <= 30`
  - 매수/매도 조건 각각 AND 결합 → `매수: A AND B AND C`
- 서버 응답의 `script` → 폼 역파싱 (간단한 패턴만, 복잡한 DSL은 읽기 전용 표시)

**verify**: 폼으로 규칙 생성 → script 필드 포함하여 저장 → 재조회 시 폼에 표시

---

## 4. 검증 방법

### 4.1 단위 테스트

| 대상 | 테스트 항목 |
|------|-----------|
| Lexer | 토큰화 정확성, 한국어 식별자, 주석 무시, 에러 위치 |
| Parser | spec §2.3 예시 파싱, 연산자 우선순위, 커스텀 함수, 매수/매도 필수 검증 |
| Evaluator | 조건 충족/미충족, null 전파, 내장 패턴 함수, 0 나누기 |
| Cloud validator | 유효/무효 script → 통과/에러 |
| RuleConfig | from_dict() — DSL 규칙 + JSON 규칙 양쪽 |

### 4.2 통합 테스트

| 시나리오 | 검증 |
|----------|------|
| 클라우드 POST script → 로컬 sync → 평가 | 전체 파이프라인 동작 |
| 잘못된 DSL POST | 400 + 에러 위치/메시지 |
| JSON 규칙 (하위 호환) | 기존 동작 유지 |
| 미보유 매도 | REJECTED |
| ONCE 트리거 | 1회 후 비활성화 |

### 4.3 빌드 확인

- `cd frontend && npm run build` — TypeScript 컴파일 에러 없음
- `cd sv_core && python -c "from sv_core.parsing import parse"` — import 성공
- `cd cloud_server && python -c "from cloud_server.models.rule import TradingRule"` — 모델 로드 성공

---

## 5. 범위 외 (이 plan에서 하지 않는 것)

- DSL 에디터 (v2 — CodeMirror)
- LLM 연동 (v2 — AI 분석)
- 전략 템플릿 갤러리 (v2)
- DB 마이그레이션 스크립트 실행 (Alembic — 별도 작업)
- JSON → DSL 일괄 변환 스크립트 (마이그레이션 — 별도 작업)

---

**마지막 갱신**: 2026-03-07
