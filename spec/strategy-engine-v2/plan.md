# 전략 엔진 v2 구현 계획 (Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** DSL v2 파서 + 엔진 실행 모델 + 조건 상태 API + 카드 UI 모니터링을 구현하여, 프로 수준 전략 표현과 실시간 투명성을 제공한다.

**Architecture:** 4개 Phase로 구분. Phase 1(DSL 파서)→Phase 2(엔진)→Phase 3(상태 API)→Phase 4(프론트). 각 Phase는 독립 테스트 가능하며, Phase 내 태스크는 TDD 순서.

**Tech Stack:** Python 3.13 (sv_core, local_server), FastAPI, SQLAlchemy, React 19, TypeScript, Vite, Tailwind CSS, HeroUI, React Query

**Spec:** `spec/strategy-engine-v2/spec.md`

---

## 파일 구조

### 신규 생성

```
sv_core/parsing/ast_nodes_v2.py      # v2 AST 노드 (Rule, Action, Modifier, ParamDecl, IndexAccess)
sv_core/parsing/parser_v2.py         # v2 파서 (조건→행동 구조)
sv_core/parsing/evaluator_v2.py      # v2 평가기 (규칙 리스트 평가, 우선순위, 수식어)
sv_core/indicators/atr.py            # ATR 계산기
sv_core/indicators/extremes.py       # 최고가/최저가 계산기
sv_core/indicators/derived.py        # 이격도, 카운트, 연속 계산기
sv_core/parsing/tests/test_parser_v2.py
sv_core/parsing/tests/test_evaluator_v2.py
sv_core/indicators/tests/test_atr.py
sv_core/indicators/tests/test_derived.py

local_server/engine/position_state.py     # PositionState 데이터 클래스
local_server/engine/rule_executor_v2.py   # v2 규칙 실행기 (우선순위 결정 + 실행)
local_server/engine/condition_tracker.py  # 조건 상태 추적기 (투명성 API 데이터)
local_server/engine/indicator_history.py  # 지표 히스토리 링버퍼
local_server/tests/test_position_state.py
local_server/tests/test_rule_executor_v2.py
local_server/tests/test_condition_tracker.py
local_server/tests/test_indicator_history.py
local_server/routers/condition_status.py  # 조건 상태 API 라우터

frontend/src/components/StrategyMonitorCard.tsx   # 전략 모니터링 카드
frontend/src/components/ConditionStatusRow.tsx     # 조건 상태 행
frontend/src/components/TriggerTimeline.tsx        # 트리거 이력
frontend/src/hooks/useConditionStatus.ts           # 조건 상태 API 폴링 훅
frontend/src/types/condition-status.ts             # 조건 상태 TypeScript 타입
frontend/src/utils/__tests__/dslParserV2.test.ts   # v2 프론트 DSL 파서 테스트
```

### 수정

```
sv_core/parsing/tokens.py           # →, [, ], @, ->, BETWEEN 토큰 추가
sv_core/parsing/lexer.py            # 새 토큰 렉싱
sv_core/parsing/builtins.py         # ATR, 최고가, 최저가, 시간/포지션 필드 추가
sv_core/indicators/calculator.py    # ATR, 최고가, 최저가 계산 함수 호출 추가

local_server/engine/evaluator.py    # v2 평가 경로 추가 (v1 폴백 유지)
local_server/engine/engine.py       # PositionState 관리, v2 평가 호출, 조건 추적
local_server/engine/executor.py     # 부분 매도 수량 비율 계산 추가
local_server/engine/indicator_provider.py  # 히스토리 링버퍼 연동

cloud_server/models/rule.py         # parameters JSON 컬럼 추가
frontend/src/pages/StrategyBuilder.tsx     # DSL v2 편집 모드
frontend/src/pages/StrategyList.tsx        # 모니터링 카드 통합
frontend/src/utils/dslParser.ts            # v2 DSL 파싱 지원
frontend/src/types/strategy.ts             # parameters 필드 추가
```

---

## Phase 1: DSL 파서 확장 (sv_core)

### Task 1: 토큰 확장

**Files:**
- Modify: `sv_core/parsing/tokens.py`
- Modify: `sv_core/parsing/lexer.py`
- Test: `sv_core/parsing/tests/test_lexer.py`

- [ ] **Step 1: 토큰 타입 추가 테스트 작성**

`sv_core/parsing/tests/test_lexer.py`에 추가:

```python
class TestV2Tokens:
    def test_arrow(self):
        tokens = tokenize("RSI(14) < 30 → 매수 50%")
        arrow = [t for t in tokens if t.type == "ARROW"]
        assert len(arrow) == 1

    def test_arrow_ascii(self):
        tokens = tokenize("RSI(14) < 30 -> 매수 50%")
        arrow = [t for t in tokens if t.type == "ARROW"]
        assert len(arrow) == 1

    def test_at_param(self):
        tokens = tokenize("@기간 = 14")
        at = [t for t in tokens if t.type == "AT"]
        assert len(at) == 1

    def test_brackets(self):
        tokens = tokenize("현재가[1]")
        lbracket = [t for t in tokens if t.type == "LBRACKET"]
        rbracket = [t for t in tokens if t.type == "RBRACKET"]
        assert len(lbracket) == 1
        assert len(rbracket) == 1

    def test_percent(self):
        tokens = tokenize("매수 50%")
        pct = [t for t in tokens if t.type == "PERCENT"]
        assert len(pct) == 1
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `python -m pytest sv_core/parsing/tests/test_lexer.py::TestV2Tokens -v`
Expected: FAIL (ARROW, AT, LBRACKET, RBRACKET, PERCENT 토큰 미정의)

- [ ] **Step 3: tokens.py에 토큰 타입 추가**

`sv_core/parsing/tokens.py`에 추가:

```python
# v2 토큰
ARROW = "ARROW"         # → 또는 ->
AT = "AT"               # @
LBRACKET = "LBRACKET"   # [
RBRACKET = "RBRACKET"   # ]
PERCENT = "PERCENT"     # %
```

- [ ] **Step 4: lexer.py에 렉싱 로직 추가**

`sv_core/parsing/lexer.py`의 `tokenize()` 함수에 추가:

```python
# → (유니코드 화살표)
if ch == "→":
    tokens.append(Token("ARROW", "→", line, col))
    pos += 1
    col += 1
    continue

# -> (ASCII 화살표)
if ch == "-" and pos + 1 < len(source) and source[pos + 1] == ">":
    tokens.append(Token("ARROW", "->", line, col))
    pos += 2
    col += 2
    continue

# @
if ch == "@":
    tokens.append(Token("AT", "@", line, col))
    pos += 1
    col += 1
    continue

# [ ]
if ch == "[":
    tokens.append(Token("LBRACKET", "[", line, col))
    pos += 1
    col += 1
    continue
if ch == "]":
    tokens.append(Token("RBRACKET", "]", line, col))
    pos += 1
    col += 1
    continue

# %
if ch == "%":
    tokens.append(Token("PERCENT", "%", line, col))
    pos += 1
    col += 1
    continue
```

주의: `->`의 `-`가 기존 MINUS 토큰과 충돌하지 않도록 `->` 체크를 MINUS보다 먼저 배치.

- [ ] **Step 5: 테스트 실행 — 통과 확인**

Run: `python -m pytest sv_core/parsing/tests/test_lexer.py::TestV2Tokens -v`
Expected: PASS

- [ ] **Step 6: 기존 렉서 테스트 회귀 확인**

Run: `python -m pytest sv_core/parsing/tests/test_lexer.py -v`
Expected: 전체 PASS (기존 테스트 깨지지 않음)

- [ ] **Step 7: 커밋**

```bash
git add sv_core/parsing/tokens.py sv_core/parsing/lexer.py sv_core/parsing/tests/test_lexer.py
git commit -m "feat(dsl): v2 토큰 추가 (→, @, [], %)"
```

---

### Task 2: v2 AST 노드

**Files:**
- Create: `sv_core/parsing/ast_nodes_v2.py`

- [ ] **Step 1: v2 AST 노드 정의**

```python
"""v2 AST 노드. 기존 ast_nodes.py는 v1 호환용으로 유지."""
from __future__ import annotations
from dataclasses import dataclass, field
from sv_core.parsing.ast_nodes import Node


@dataclass(frozen=True, slots=True)
class ParamDecl(Node):
    """파라미터 선언: @이름 = 기본값"""
    name: str = ""
    default_value: float = 0.0


@dataclass(frozen=True, slots=True)
class ParamRef(Node):
    """파라미터 참조: @이름"""
    name: str = ""


@dataclass(frozen=True, slots=True)
class IndexAccess(Node):
    """이전 봉 참조: expr[N]"""
    expr: Node = field(default_factory=Node)
    index: int = 0  # 0=현재, 1=1봉전, 최대 60


@dataclass(frozen=True, slots=True)
class Action(Node):
    """행동: 매수/매도 + 수량"""
    side: str = ""       # "매수" | "매도"
    quantity: str = ""   # "100%", "50%", "전량", "나머지"


@dataclass(frozen=True, slots=True)
class Modifier(Node):
    """수식어: [1회], [래치], [유지 N봉], [N봉내]"""
    kind: str = ""       # "1회" | "래치" | "유지" | "봉내"
    value: int = 0       # N봉의 N (1회/래치는 0)


@dataclass(frozen=True, slots=True)
class Rule(Node):
    """규칙: 조건 → 행동"""
    condition: Node = field(default_factory=Node)
    action: Action = field(default_factory=Action)
    modifier: Modifier | None = None


@dataclass(frozen=True, slots=True)
class ScriptV2(Node):
    """v2 스크립트: 파라미터 선언 + 규칙 리스트"""
    params: tuple[ParamDecl, ...] = ()
    rules: tuple[Rule, ...] = ()
```

- [ ] **Step 2: 커밋**

```bash
git add sv_core/parsing/ast_nodes_v2.py
git commit -m "feat(dsl): v2 AST 노드 정의 (Rule, Action, Modifier, ParamDecl, IndexAccess)"
```

---

### Task 3: v2 파서 — 파라미터 + 규칙 기본 구조

**Files:**
- Create: `sv_core/parsing/parser_v2.py`
- Create: `sv_core/parsing/tests/test_parser_v2.py`

- [ ] **Step 1: 기본 파싱 테스트 작성**

```python
"""v2 파서 테스트."""
import pytest
from sv_core.parsing.parser_v2 import parse_v2
from sv_core.parsing.ast_nodes_v2 import (
    ScriptV2, ParamDecl, Rule, Action, ParamRef, IndexAccess, Modifier,
)
from sv_core.parsing.ast_nodes import (
    Comparison, FieldRef, NumberLit, FuncCall, BinOp,
)


class TestParamDecl:
    def test_single_param(self):
        ast = parse_v2("@기간 = 14\nRSI(@기간) < 30 → 매수 100%")
        assert len(ast.params) == 1
        assert ast.params[0].name == "기간"
        assert ast.params[0].default_value == 14.0

    def test_multiple_params(self):
        ast = parse_v2("@기간 = 14\n@손절 = -2\nRSI(@기간) < 30 → 매수 100%")
        assert len(ast.params) == 2
        assert ast.params[1].name == "손절"
        assert ast.params[1].default_value == -2.0


class TestBasicRule:
    def test_simple_buy(self):
        ast = parse_v2("RSI(14) < 30 → 매수 100%")
        assert len(ast.rules) == 1
        rule = ast.rules[0]
        assert isinstance(rule.condition, Comparison)
        assert rule.action.side == "매수"
        assert rule.action.quantity == "100%"

    def test_sell_all(self):
        ast = parse_v2("수익률 <= -2 → 매도 전량")
        rule = ast.rules[0]
        assert rule.action.side == "매도"
        assert rule.action.quantity == "전량"

    def test_sell_remainder(self):
        ast = parse_v2("고점 대비 <= -1.5 → 매도 나머지")
        rule = ast.rules[0]
        assert rule.action.quantity == "나머지"

    def test_multiple_rules(self):
        source = (
            "수익률 <= -2 → 매도 전량\n"
            "RSI(14) < 30 → 매수 50%\n"
            "수익률 >= 5 → 매도 전량\n"
        )
        ast = parse_v2(source)
        assert len(ast.rules) == 3
        assert ast.rules[0].action.side == "매도"
        assert ast.rules[1].action.side == "매수"
        assert ast.rules[2].action.side == "매도"

    def test_arrow_ascii(self):
        ast = parse_v2("RSI(14) < 30 -> 매수 100%")
        assert ast.rules[0].action.side == "매수"

    def test_param_ref_in_condition(self):
        ast = parse_v2("@기간 = 14\nRSI(@기간) < 30 → 매수 100%")
        rule = ast.rules[0]
        func = rule.condition.left
        assert isinstance(func, FuncCall)
        assert isinstance(func.args[0], ParamRef)
        assert func.args[0].name == "기간"

    def test_comment_ignored(self):
        source = "-- 이건 주석\nRSI(14) < 30 → 매수 100%"
        ast = parse_v2(source)
        assert len(ast.rules) == 1


class TestIndexAccess:
    def test_field_index(self):
        ast = parse_v2("현재가[1] < MA(20) → 매수 100%")
        rule = ast.rules[0]
        left = rule.condition.left
        assert isinstance(left, IndexAccess)
        assert isinstance(left.expr, FieldRef)
        assert left.expr.name == "현재가"
        assert left.index == 1

    def test_func_index(self):
        ast = parse_v2("RSI(14)[3] < 30 → 매수 100%")
        rule = ast.rules[0]
        left = rule.condition.left
        assert isinstance(left, IndexAccess)
        assert isinstance(left.expr, FuncCall)
        assert left.index == 3

    def test_index_max_60(self):
        ast = parse_v2("현재가[60] > 0 → 매수 100%")
        assert ast.rules[0].condition.left.index == 60

    def test_index_over_60_error(self):
        with pytest.raises(Exception, match="60"):
            parse_v2("현재가[61] > 0 → 매수 100%")


class TestModifier:
    def test_once(self):
        ast = parse_v2("수익률 >= 3 [1회] → 매도 50%")
        assert ast.rules[0].modifier.kind == "1회"

    def test_latch(self):
        ast = parse_v2("(수익률 >= 2)[래치] AND 수익률 <= 0 → 매도 전량")
        # 래치는 조건의 일부로 파싱됨
        rule = ast.rules[0]
        assert rule.modifier is None  # 래치는 조건 수식어, 규칙 수식어가 아님
        # 구현 시 래치가 조건 내부 Modifier 노드로 들어가는 방식 확정 필요

    def test_hold_n(self):
        ast = parse_v2("(MA(5) > MA(20))[유지 3봉] AND RSI(14) < 30 → 매수 100%")
        # 유지도 조건 내부 수식어
        assert len(ast.rules) == 1

    def test_within_n(self):
        ast = parse_v2("골든크로스()[3봉내] AND RSI(14) < 35 → 매수 100%")
        assert len(ast.rules) == 1
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `python -m pytest sv_core/parsing/tests/test_parser_v2.py -v`
Expected: FAIL (parse_v2 미존재)

- [ ] **Step 3: v2 파서 구현**

`sv_core/parsing/parser_v2.py` — 핵심 구조:

```python
"""v2 DSL 파서.

문법:
  script    = param_decl* rule+
  param_decl = '@' IDENT '=' NUMBER NEWLINE
  rule      = expression ARROW action NEWLINE
  action    = ('매수' | '매도') (NUMBER '%' | '전량' | '나머지')
  expression = 기존 v1 expression 문법 + IndexAccess + ParamRef + Modifier
"""
from __future__ import annotations
from sv_core.parsing.lexer import tokenize, Token
from sv_core.parsing.ast_nodes import (
    Node, NumberLit, BoolLit, StringLit, FieldRef, FuncCall,
    BinOp, UnaryOp, Comparison,
)
from sv_core.parsing.ast_nodes_v2 import (
    ScriptV2, ParamDecl, ParamRef, IndexAccess, Action, Modifier, Rule,
)
from sv_core.parsing.builtins import BUILTIN_FIELDS, BUILTIN_FUNCS, BUILTIN_PATTERNS
from sv_core.parsing.errors import DSLSyntaxError


def parse_v2(source: str) -> ScriptV2:
    """v2 DSL 소스를 파싱하여 ScriptV2 AST를 반환."""
    tokens = tokenize(source)
    parser = _ParserV2(tokens, source)
    return parser.parse()


class _ParserV2:
    def __init__(self, tokens: list[Token], source: str) -> None:
        self._tokens = [t for t in tokens if t.type not in ("NEWLINE", "EOF")]
        self._pos = 0
        self._source = source
        self._params: dict[str, float] = {}

    def parse(self) -> ScriptV2:
        params = self._parse_params()
        rules = self._parse_rules()
        if not rules:
            raise DSLSyntaxError("규칙이 하나도 없습니다", 0, 0)
        return ScriptV2(params=tuple(params), rules=tuple(rules))

    # --- 파라미터 파싱 ---
    def _parse_params(self) -> list[ParamDecl]:
        params = []
        while self._pos < len(self._tokens) and self._peek_type() == "AT":
            self._consume("AT")
            name_tok = self._consume("IDENT")
            self._consume("ASSIGN")
            # 음수 기본값 지원
            neg = False
            if self._peek_type() == "MINUS":
                self._consume("MINUS")
                neg = True
            val_tok = self._consume("NUMBER")
            value = -float(val_tok.value) if neg else float(val_tok.value)
            decl = ParamDecl(name=name_tok.value, default_value=value,
                            line=name_tok.line, col=name_tok.col)
            self._params[name_tok.value] = value
            params.append(decl)
        return params

    # --- 규칙 파싱 ---
    def _parse_rules(self) -> list[Rule]:
        rules = []
        while self._pos < len(self._tokens):
            condition = self._parse_expression()
            # 규칙 수식어 (조건 뒤, → 앞)
            modifier = None
            if self._peek_type() == "LBRACKET":
                modifier = self._parse_rule_modifier()
            self._consume("ARROW")
            action = self._parse_action()
            rules.append(Rule(condition=condition, action=action, modifier=modifier))
        return rules

    def _parse_rule_modifier(self) -> Modifier:
        self._consume("LBRACKET")
        tok = self._consume("IDENT")
        if tok.value == "1회":
            self._consume("RBRACKET")
            return Modifier(kind="1회", value=0)
        elif tok.value == "래치":
            self._consume("RBRACKET")
            return Modifier(kind="래치", value=0)
        # [유지 N봉], [N봉내]는 추가 파싱 필요
        raise DSLSyntaxError(f"알 수 없는 수식어: {tok.value}", tok.line, tok.col)

    def _parse_action(self) -> Action:
        side_tok = self._consume("IDENT")
        if side_tok.value not in ("매수", "매도"):
            raise DSLSyntaxError(
                f"'매수' 또는 '매도' 예상, '{side_tok.value}' 발견",
                side_tok.line, side_tok.col)
        # 수량 파싱
        if self._peek_type() == "NUMBER":
            qty_tok = self._consume("NUMBER")
            self._consume("PERCENT")
            return Action(side=side_tok.value, quantity=f"{qty_tok.value}%")
        elif self._peek_type() == "IDENT":
            qty_tok = self._consume("IDENT")
            if qty_tok.value in ("전량", "나머지"):
                return Action(side=side_tok.value, quantity=qty_tok.value)
            raise DSLSyntaxError(
                f"'전량', '나머지', 또는 숫자% 예상", qty_tok.line, qty_tok.col)
        raise DSLSyntaxError("수량 예상", side_tok.line, side_tok.col)

    # --- Expression 파싱 (v1 기반, ParamRef/IndexAccess 추가) ---
    # _parse_expression, _parse_or, _parse_and, _parse_not,
    # _parse_comparison, _parse_additive, _parse_multiplicative,
    # _parse_unary, _parse_primary 구현
    # 기존 parser.py의 expression 문법을 재사용하되:
    # - @IDENT → ParamRef 노드
    # - expr[N] → IndexAccess 노드
    # - (expr)[수식어] → 조건 수식어 처리

    def _parse_expression(self) -> Node:
        return self._parse_or()

    def _parse_or(self) -> Node:
        left = self._parse_and()
        while self._peek_value() == "OR":
            self._advance()
            right = self._parse_and()
            left = BinOp(op="OR", left=left, right=right)
        return left

    def _parse_and(self) -> Node:
        left = self._parse_not()
        while self._peek_value() == "AND":
            self._advance()
            right = self._parse_not()
            left = BinOp(op="AND", left=left, right=right)
        return left

    def _parse_not(self) -> Node:
        if self._peek_value() == "NOT":
            self._advance()
            operand = self._parse_not()
            return UnaryOp(op="NOT", operand=operand)
        return self._parse_comparison()

    def _parse_comparison(self) -> Node:
        left = self._parse_additive()
        if self._peek_type() in ("GT", "GE", "LT", "LE", "EQ", "NE"):
            op_tok = self._advance()
            right = self._parse_additive()
            return Comparison(op=op_tok.value, left=left, right=right)
        return left

    def _parse_additive(self) -> Node:
        left = self._parse_multiplicative()
        while self._peek_type() in ("PLUS", "MINUS"):
            op_tok = self._advance()
            right = self._parse_multiplicative()
            left = BinOp(op=op_tok.value, left=left, right=right)
        return left

    def _parse_multiplicative(self) -> Node:
        left = self._parse_unary()
        while self._peek_type() in ("STAR", "SLASH"):
            op_tok = self._advance()
            right = self._parse_unary()
            left = BinOp(op=op_tok.value, left=left, right=right)
        return left

    def _parse_unary(self) -> Node:
        if self._peek_type() == "MINUS":
            self._advance()
            operand = self._parse_unary()
            return UnaryOp(op="-", operand=operand)
        return self._parse_postfix()

    def _parse_postfix(self) -> Node:
        node = self._parse_primary()
        # IndexAccess: expr[N]
        if self._peek_type() == "LBRACKET":
            self._consume("LBRACKET")
            idx_tok = self._consume("NUMBER")
            idx = int(float(idx_tok.value))
            if idx > 60:
                raise DSLSyntaxError(
                    f"이전 봉 참조 최대 [60], [{idx}] 사용 불가",
                    idx_tok.line, idx_tok.col)
            self._consume("RBRACKET")
            node = IndexAccess(expr=node, index=idx)
        return node

    def _parse_primary(self) -> Node:
        tok = self._peek()
        if tok is None:
            raise DSLSyntaxError("예상치 못한 입력 끝", 0, 0)

        # 숫자
        if tok.type == "NUMBER":
            self._advance()
            return NumberLit(value=float(tok.value), line=tok.line, col=tok.col)

        # 불리언
        if tok.type == "BOOL":
            self._advance()
            return BoolLit(value=tok.value == "true", line=tok.line, col=tok.col)

        # 문자열
        if tok.type == "STRING":
            self._advance()
            return StringLit(value=tok.value, line=tok.line, col=tok.col)

        # 파라미터 참조 @이름
        if tok.type == "AT":
            self._advance()
            name_tok = self._consume("IDENT")
            if name_tok.value not in self._params:
                raise DSLSyntaxError(
                    f"정의되지 않은 파라미터: @{name_tok.value}",
                    name_tok.line, name_tok.col)
            return ParamRef(name=name_tok.value, line=tok.line, col=tok.col)

        # 괄호 그룹
        if tok.type == "LPAREN":
            self._advance()
            expr = self._parse_expression()
            self._consume("RPAREN")
            # 괄호 뒤에 수식어가 올 수 있음: (조건)[래치]
            # 이건 postfix에서 처리하지 않고 여기서 처리
            return expr

        # 식별자 (필드, 함수, 패턴)
        if tok.type == "IDENT":
            self._advance()
            # 함수 호출
            if self._peek_type() == "LPAREN":
                self._consume("LPAREN")
                args = self._parse_args()
                self._consume("RPAREN")
                return FuncCall(name=tok.value, args=tuple(args),
                              line=tok.line, col=tok.col)
            # 내장 필드
            return FieldRef(name=tok.value, line=tok.line, col=tok.col)

        raise DSLSyntaxError(
            f"예상치 못한 토큰: {tok.type} '{tok.value}'",
            tok.line, tok.col)

    def _parse_args(self) -> list[Node]:
        args = []
        if self._peek_type() == "RPAREN":
            return args
        args.append(self._parse_expression())
        while self._peek_type() == "COMMA":
            self._advance()
            args.append(self._parse_expression())
        return args

    # --- 유틸리티 ---
    def _peek(self) -> Token | None:
        if self._pos >= len(self._tokens):
            return None
        return self._tokens[self._pos]

    def _peek_type(self) -> str:
        tok = self._peek()
        return tok.type if tok else "EOF"

    def _peek_value(self) -> str:
        tok = self._peek()
        return tok.value if tok else ""

    def _advance(self) -> Token:
        tok = self._tokens[self._pos]
        self._pos += 1
        return tok

    def _consume(self, expected_type: str) -> Token:
        tok = self._peek()
        if tok is None or tok.type != expected_type:
            actual = f"{tok.type} '{tok.value}'" if tok else "EOF"
            raise DSLSyntaxError(
                f"'{expected_type}' 예상, {actual} 발견",
                tok.line if tok else 0, tok.col if tok else 0)
        return self._advance()
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

Run: `python -m pytest sv_core/parsing/tests/test_parser_v2.py -v`
Expected: 대부분 PASS. 수식어 관련 테스트는 구현 범위에 따라 조정 필요.

- [ ] **Step 5: 커밋**

```bash
git add sv_core/parsing/parser_v2.py sv_core/parsing/tests/test_parser_v2.py
git commit -m "feat(dsl): v2 파서 — 파라미터, 규칙, IndexAccess, 기본 수식어"
```

---

### Task 4: v1 호환 — 기존 매수:/매도: 자동 변환

**Files:**
- Modify: `sv_core/parsing/parser_v2.py`
- Test: `sv_core/parsing/tests/test_parser_v2.py`

- [ ] **Step 1: v1 호환 테스트 작성**

```python
class TestV1Compat:
    def test_v1_buy_sell_blocks(self):
        """기존 v1 DSL이 v2 파서에서도 동작."""
        source = "매수: RSI(14) < 30\n매도: 수익률 >= 5"
        ast = parse_v2(source)
        assert len(ast.rules) == 2
        # 매수: RSI(14) < 30 → RSI(14) < 30 AND 보유수량 == 0 → 매수 100%
        buy_rule = ast.rules[0]
        assert buy_rule.action.side == "매수"
        assert buy_rule.action.quantity == "100%"
        # 매도: 수익률 >= 5 → 수익률 >= 5 → 매도 전량
        sell_rule = ast.rules[1]
        assert sell_rule.action.side == "매도"
        assert sell_rule.action.quantity == "전량"

    def test_v1_with_custom_func(self):
        source = "내함수() = RSI(14) < 30\n매수: 내함수()\n매도: 수익률 >= 5"
        ast = parse_v2(source)
        assert len(ast.rules) == 2
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `python -m pytest sv_core/parsing/tests/test_parser_v2.py::TestV1Compat -v`

- [ ] **Step 3: v1 감지 + 자동 변환 구현**

`parser_v2.py`의 `parse()` 메서드에 v1 감지 로직 추가:

```python
def parse(self) -> ScriptV2:
    params = self._parse_params()
    # v1 감지: '매수:' 또는 '매도:' 키워드가 있으면 v1 모드
    if self._is_v1_format():
        return self._parse_v1_compat(params)
    rules = self._parse_rules()
    if not rules:
        raise DSLSyntaxError("규칙이 하나도 없습니다", 0, 0)
    return ScriptV2(params=tuple(params), rules=tuple(rules))

def _is_v1_format(self) -> bool:
    """현재 위치부터 v1 형식(매수:/매도:)인지 감지."""
    for i in range(self._pos, len(self._tokens)):
        tok = self._tokens[i]
        if tok.type == "IDENT" and tok.value in ("매수", "매도"):
            if i + 1 < len(self._tokens) and self._tokens[i + 1].type == "COLON":
                return True
    return False

def _parse_v1_compat(self, params: list[ParamDecl]) -> ScriptV2:
    """v1 매수:/매도: 형식을 v2 Rule 리스트로 변환."""
    # 커스텀 함수 건너뛰기 (IDENT '(' ')' '=' 패턴)
    custom_funcs = self._skip_custom_funcs()
    rules = []
    buy_expr = None
    sell_expr = None
    while self._pos < len(self._tokens):
        tok = self._consume("IDENT")
        self._consume("COLON")
        expr = self._parse_expression()
        if tok.value == "매수":
            buy_expr = expr
        elif tok.value == "매도":
            sell_expr = expr
    if buy_expr:
        # 매수 규칙: 조건 AND 보유수량 == 0 → 매수 100%
        condition = BinOp(op="AND", left=buy_expr,
                         right=Comparison(op="==",
                                         left=FieldRef(name="보유수량"),
                                         right=NumberLit(value=0)))
        rules.append(Rule(condition=condition,
                         action=Action(side="매수", quantity="100%")))
    if sell_expr:
        rules.append(Rule(condition=sell_expr,
                         action=Action(side="매도", quantity="전량")))
    return ScriptV2(params=tuple(params), rules=tuple(rules))
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

Run: `python -m pytest sv_core/parsing/tests/test_parser_v2.py -v`

- [ ] **Step 5: 커밋**

```bash
git add sv_core/parsing/parser_v2.py sv_core/parsing/tests/test_parser_v2.py
git commit -m "feat(dsl): v1 매수:/매도: 호환 — v2 Rule로 자동 변환"
```

---

### Task 5: 내장 함수/필드 확장 + 지표 계산기

**Files:**
- Modify: `sv_core/parsing/builtins.py`
- Create: `sv_core/indicators/atr.py`
- Create: `sv_core/indicators/extremes.py`
- Create: `sv_core/indicators/derived.py`
- Create: `sv_core/indicators/tests/test_atr.py`
- Create: `sv_core/indicators/tests/test_derived.py`

- [ ] **Step 1: ATR 계산기 테스트 작성**

```python
"""ATR 계산기 테스트."""
import pandas as pd
import pytest
from sv_core.indicators.atr import calc_atr


class TestATR:
    def test_basic(self):
        highs = pd.Series([105, 110, 108, 112, 107, 115, 109, 113, 111, 116,
                           108, 114, 110, 117, 112] + [110] * 5)
        lows = pd.Series([95, 100, 98, 102, 97, 105, 99, 103, 101, 106,
                          98, 104, 100, 107, 102] + [100] * 5)
        closes = pd.Series([100, 105, 103, 108, 102, 110, 104, 109, 106, 112,
                            103, 110, 105, 113, 107] + [105] * 5)
        result = calc_atr(highs, lows, closes, period=14)
        assert result is not None
        assert result > 0

    def test_insufficient_data(self):
        highs = pd.Series([105, 110])
        lows = pd.Series([95, 100])
        closes = pd.Series([100, 105])
        result = calc_atr(highs, lows, closes, period=14)
        assert result is None
```

- [ ] **Step 2: ATR 계산기 구현**

```python
"""ATR (Average True Range) 계산기."""
from __future__ import annotations
import pandas as pd


def calc_atr(
    highs: pd.Series, lows: pd.Series, closes: pd.Series, period: int = 14
) -> float | None:
    """ATR 계산. 데이터 부족 시 None."""
    if len(closes) < period + 1:
        return None
    prev_close = closes.shift(1)
    tr = pd.concat([
        highs - lows,
        (highs - prev_close).abs(),
        (lows - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean().iloc[-1]
    return round(float(atr), 2) if pd.notna(atr) else None
```

- [ ] **Step 3: 최고가/최저가 계산기**

`sv_core/indicators/extremes.py`:

```python
"""최고가/최저가 계산기."""
from __future__ import annotations
import pandas as pd


def calc_highest(prices: pd.Series, period: int) -> float | None:
    if len(prices) < period:
        return None
    return round(float(prices.iloc[-period:].max()), 2)


def calc_lowest(prices: pd.Series, period: int) -> float | None:
    if len(prices) < period:
        return None
    return round(float(prices.iloc[-period:].min()), 2)
```

- [ ] **Step 4: 이격도 계산기**

`sv_core/indicators/derived.py`:

```python
"""파생 지표 계산기 (이격도, 카운트, 연속)."""
from __future__ import annotations
from sv_core.indicators.calculator import calc_sma


def calc_disparity(closes, period: int) -> float | None:
    """이격도 = (현재가 - MA) / MA × 100."""
    import pandas as pd
    ma = calc_sma(closes, period)
    if ma is None or ma == 0:
        return None
    current = float(closes.iloc[-1])
    return round((current - ma) / ma * 100, 2)
```

- [ ] **Step 5: builtins.py에 새 필드/함수 등록**

```python
# 새 내장 필드
BUILTIN_FIELDS.update({
    "고점 대비", "진입가", "보유일", "보유봉",
    "시간", "장시작후", "요일",
})

# 새 내장 함수
BUILTIN_FUNCS["ATR"] = FuncSpec("ATR", param_min=1, param_max=2, return_type="number")
BUILTIN_FUNCS["최고가"] = FuncSpec("최고가", param_min=1, param_max=2, return_type="number")
BUILTIN_FUNCS["최저가"] = FuncSpec("최저가", param_min=1, param_max=2, return_type="number")
BUILTIN_FUNCS["카운트"] = FuncSpec("카운트", param_min=2, param_max=2, return_type="number")
BUILTIN_FUNCS["연속"] = FuncSpec("연속", param_min=1, param_max=1, return_type="number")
BUILTIN_FUNCS["이격도"] = FuncSpec("이격도", param_min=1, param_max=2, return_type="number")
```

- [ ] **Step 6: 테스트 실행**

Run: `python -m pytest sv_core/indicators/tests/ sv_core/parsing/tests/ -v`

- [ ] **Step 7: 커밋**

```bash
git add sv_core/indicators/ sv_core/parsing/builtins.py
git commit -m "feat(dsl): ATR, 최고가, 최저가, 이격도 지표 + 내장 필드/함수 확장"
```

---

### Task 6: v2 평가기

**Files:**
- Create: `sv_core/parsing/evaluator_v2.py`
- Create: `sv_core/parsing/tests/test_evaluator_v2.py`

- [ ] **Step 1: 평가기 테스트 작성**

```python
"""v2 평가기 테스트."""
import pytest
from sv_core.parsing.parser_v2 import parse_v2
from sv_core.parsing.evaluator_v2 import evaluate_v2, EvalResult


def _ctx(**overrides):
    base = {
        "현재가": 50000, "거래량": 1000, "수익률": 0,
        "보유수량": 0, "고점 대비": 0, "진입가": 0,
        "보유일": 0, "보유봉": 0, "시간": "10:00",
        "장시작후": 60, "요일": 1,
        "RSI": lambda p, tf=None: 25,
        "MA": lambda p, tf=None: 50000,
        "ATR": lambda p, tf=None: 1000,
    }
    base.update(overrides)
    return base


class TestBasicEval:
    def test_single_buy(self):
        ast = parse_v2("RSI(14) < 30 → 매수 100%")
        ctx = _ctx(RSI=lambda p, tf=None: 25)
        results = evaluate_v2(ast, ctx, {})
        assert len(results) == 1
        assert results[0].triggered is True
        assert results[0].action.side == "매수"

    def test_single_buy_false(self):
        ast = parse_v2("RSI(14) < 30 → 매수 100%")
        ctx = _ctx(RSI=lambda p, tf=None: 35)
        results = evaluate_v2(ast, ctx, {})
        assert len(results) == 1
        assert results[0].triggered is False

    def test_priority_full_sell_over_partial(self):
        """전량 매도가 부분 매도보다 우선."""
        source = (
            "수익률 >= 3 → 매도 50%\n"
            "수익률 <= -2 → 매도 전량\n"
        )
        ast = parse_v2(source)
        ctx = _ctx(수익률=-3, 보유수량=100)
        results = evaluate_v2(ast, ctx, {})
        # 두 규칙 다 True이지만, 실행은 전량 매도만
        selected = [r for r in results if r.selected]
        assert len(selected) == 1
        assert selected[0].action.quantity == "전량"

    def test_sell_over_buy(self):
        """매도가 매수보다 우선."""
        source = (
            "RSI(14) < 30 → 매수 100%\n"
            "수익률 <= -2 → 매도 전량\n"
        )
        ast = parse_v2(source)
        ctx = _ctx(RSI=lambda p, tf=None: 25, 수익률=-3, 보유수량=100)
        results = evaluate_v2(ast, ctx, {})
        selected = [r for r in results if r.selected]
        assert len(selected) == 1
        assert selected[0].action.side == "매도"

    def test_param_substitution(self):
        source = "@기간 = 14\nRSI(@기간) < 30 → 매수 100%"
        ast = parse_v2(source)
        called_with = {}
        def mock_rsi(p, tf=None):
            called_with["period"] = p
            return 25
        ctx = _ctx(RSI=mock_rsi)
        evaluate_v2(ast, ctx, {})
        assert called_with["period"] == 14


class TestOnceModifier:
    def test_once_blocks_second_execution(self):
        source = "수익률 >= 3 [1회] → 매도 50%"
        ast = parse_v2(source)
        state = {}
        # 1차: 실행
        ctx1 = _ctx(수익률=4, 보유수량=100)
        r1 = evaluate_v2(ast, ctx1, state)
        assert r1[0].selected is True
        # 2차: [1회]로 인해 차단
        r2 = evaluate_v2(ast, ctx1, state)
        assert r2[0].selected is False

    def test_once_resets_on_full_exit(self):
        source = "수익률 >= 3 [1회] → 매도 50%"
        ast = parse_v2(source)
        state = {}
        # 실행
        ctx1 = _ctx(수익률=4, 보유수량=100)
        evaluate_v2(ast, ctx1, state)
        # 전량 청산 신호
        state["_position_cleared"] = True
        # 리셋 후 재실행 가능
        r3 = evaluate_v2(ast, ctx1, state)
        assert r3[0].selected is True
```

- [ ] **Step 2: 평가기 구현**

```python
"""v2 DSL 평가기.

규칙 리스트를 순차 평가하고, §5.1 우선순위에 따라 실행 규칙을 결정.
모든 규칙의 평가 결과를 반환 (투명성 API용).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from sv_core.parsing.ast_nodes import (
    Node, NumberLit, BoolLit, StringLit, FieldRef, FuncCall,
    BinOp, UnaryOp, Comparison,
)
from sv_core.parsing.ast_nodes_v2 import (
    ScriptV2, ParamRef, IndexAccess, Action, Modifier, Rule,
)


@dataclass
class EvalResult:
    """규칙 하나의 평가 결과."""
    index: int                     # 규칙 순서 (0-based)
    condition_expr: str            # 조건 표현식 (문자열 복원)
    triggered: bool                # 조건 True 여부
    selected: bool                 # 실행 대상으로 선택됨 (§5.1 우선순위 적용 후)
    action: Action                 # 행동
    details: dict[str, Any] = field(default_factory=dict)  # 조건 내 변수 현재값


def evaluate_v2(
    ast: ScriptV2,
    context: dict[str, Any],
    state: dict[str, Any],
    params: dict[str, float] | None = None,
) -> list[EvalResult]:
    """v2 스크립트를 평가하여 모든 규칙의 결과를 반환."""
    # 파라미터 기본값 적용
    param_values = {p.name: p.default_value for p in ast.params}
    if params:
        param_values.update(params)

    # 포지션 리셋 시 수식어 상태 초기화
    if state.pop("_position_cleared", False):
        state.pop("_modifier", None)

    modifier_state = state.setdefault("_modifier", {})
    evaluator = _ExprEvaluator(context, param_values, state)
    results: list[EvalResult] = []

    for i, rule in enumerate(ast.rules):
        details = {}
        triggered = evaluator.eval_node(rule.condition, details)
        if triggered is None:
            triggered = False

        # 수식어 적용
        if rule.modifier and triggered:
            mod_key = f"rule_{i}_{rule.modifier.kind}"
            if rule.modifier.kind == "1회":
                if modifier_state.get(mod_key):
                    triggered = False  # 이미 실행됨
            elif rule.modifier.kind == "래치":
                modifier_state[mod_key] = True

        results.append(EvalResult(
            index=i,
            condition_expr=_expr_to_str(rule.condition),
            triggered=bool(triggered),
            selected=False,
            action=rule.action,
            details=details,
        ))

    # §5.1 우선순위 결정
    _apply_priority(results, modifier_state)
    return results


def _apply_priority(results: list[EvalResult], modifier_state: dict) -> None:
    """§5.1: 전량 매도 > 부분 매도 > 매수, 사이클당 최대 1개."""
    triggered = [r for r in results if r.triggered]
    if not triggered:
        return

    # 우선순위 1: 전량 매도
    full_sells = [r for r in triggered
                  if r.action.side == "매도"
                  and r.action.quantity in ("전량", "나머지")]
    if full_sells:
        full_sells[0].selected = True
        return

    # 우선순위 2: 부분 매도
    partial_sells = [r for r in triggered
                     if r.action.side == "매도"
                     and r.action.quantity not in ("전량", "나머지")]
    if partial_sells:
        r = partial_sells[0]
        r.selected = True
        # [1회] 수식어 마킹
        if r.action.side == "매도" and results[r.index].action:
            rule = results[r.index]
            # 원본 Rule의 modifier 접근은 ast를 통해야 하므로,
            # modifier_state에 직접 기록
            mod_key = f"rule_{r.index}_1회"
            modifier_state[mod_key] = True
        return

    # 우선순위 3: 매수
    buys = [r for r in triggered if r.action.side == "매수"]
    if buys:
        buys[0].selected = True


def _expr_to_str(node: Node) -> str:
    """AST 노드를 문자열로 복원 (디버깅/투명성용)."""
    if isinstance(node, NumberLit):
        return str(node.value)
    if isinstance(node, FieldRef):
        return node.name
    if isinstance(node, FuncCall):
        args = ", ".join(_expr_to_str(a) for a in node.args)
        return f"{node.name}({args})"
    if isinstance(node, Comparison):
        return f"{_expr_to_str(node.left)} {node.op} {_expr_to_str(node.right)}"
    if isinstance(node, BinOp):
        return f"{_expr_to_str(node.left)} {node.op} {_expr_to_str(node.right)}"
    if isinstance(node, ParamRef):
        return f"@{node.name}"
    if isinstance(node, IndexAccess):
        return f"{_expr_to_str(node.expr)}[{node.index}]"
    return str(node)


class _ExprEvaluator:
    """AST 노드를 평가하는 내부 클래스."""

    def __init__(self, context: dict, params: dict, state: dict) -> None:
        self._ctx = context
        self._params = params
        self._state = state

    def eval_node(self, node: Node, details: dict) -> Any:
        if isinstance(node, NumberLit):
            return node.value
        if isinstance(node, BoolLit):
            return node.value
        if isinstance(node, StringLit):
            return node.value
        if isinstance(node, ParamRef):
            val = self._params.get(node.name)
            details[f"@{node.name}"] = val
            return val
        if isinstance(node, FieldRef):
            val = self._ctx.get(node.name)
            details[node.name] = val
            return val
        if isinstance(node, FuncCall):
            return self._eval_func(node, details)
        if isinstance(node, Comparison):
            left = self.eval_node(node.left, details)
            right = self.eval_node(node.right, details)
            if left is None or right is None:
                return None
            ops = {">": lambda a, b: a > b, ">=": lambda a, b: a >= b,
                   "<": lambda a, b: a < b, "<=": lambda a, b: a <= b,
                   "==": lambda a, b: a == b, "!=": lambda a, b: a != b}
            return ops[node.op](left, right)
        if isinstance(node, BinOp):
            return self._eval_binop(node, details)
        if isinstance(node, UnaryOp):
            operand = self.eval_node(node.operand, details)
            if node.op == "NOT":
                return not operand if operand is not None else None
            if node.op == "-":
                return -operand if operand is not None else None
        if isinstance(node, IndexAccess):
            return self._eval_index(node, details)
        return None

    def _eval_func(self, node: FuncCall, details: dict) -> Any:
        func = self._ctx.get(node.name)
        if func is None:
            return None
        args = [self.eval_node(a, details) for a in node.args]
        if any(a is None for a in args):
            return None
        result = func(*args)
        details[f"{node.name}({', '.join(str(a) for a in args)})"] = result
        return result

    def _eval_binop(self, node: BinOp, details: dict) -> Any:
        left = self.eval_node(node.left, details)
        right = self.eval_node(node.right, details)
        if node.op in ("AND", "OR"):
            if left is None or right is None:
                return None
            if node.op == "AND":
                return left and right
            return left or right
        if left is None or right is None:
            return None
        ops = {"+": lambda a, b: a + b, "-": lambda a, b: a - b,
               "*": lambda a, b: a * b, "/": lambda a, b: a / b if b != 0 else None}
        return ops.get(node.op, lambda a, b: None)(left, right)

    def _eval_index(self, node: IndexAccess, details: dict) -> Any:
        # 히스토리 조회: context에 _history 딕셔너리가 있어야 함
        history = self._ctx.get("_history", {})
        if isinstance(node.expr, FieldRef):
            key = node.expr.name
            hist = history.get(key, [])
            if node.index < len(hist):
                val = hist[-(node.index + 1)]  # 최신이 마지막
                details[f"{key}[{node.index}]"] = val
                return val
            return None
        if isinstance(node.expr, FuncCall):
            # 함수 히스토리 키: "RSI(14)"
            args = [self.eval_node(a, details) for a in node.expr.args]
            key = f"{node.expr.name}({', '.join(str(a) for a in args)})"
            hist = history.get(key, [])
            if node.index < len(hist):
                val = hist[-(node.index + 1)]
                details[f"{key}[{node.index}]"] = val
                return val
            return None
        return None
```

- [ ] **Step 3: 테스트 실행**

Run: `python -m pytest sv_core/parsing/tests/test_evaluator_v2.py -v`

- [ ] **Step 4: 커밋**

```bash
git add sv_core/parsing/evaluator_v2.py sv_core/parsing/tests/test_evaluator_v2.py
git commit -m "feat(dsl): v2 평가기 — 우선순위 결정, 수식어, 투명성 데이터"
```

---

## Phase 2: 엔진 실행 모델 (local_server)

### Task 7: PositionState

**Files:**
- Create: `local_server/engine/position_state.py`
- Create: `local_server/tests/test_position_state.py`

- [ ] **Step 1: 테스트 작성**

```python
"""PositionState 테스트."""
from datetime import datetime
from local_server.engine.position_state import PositionState


class TestPositionState:
    def test_initial_state(self):
        ps = PositionState()
        assert ps.is_empty()
        assert ps.entry_price == 0
        assert ps.highest_price == 0

    def test_entry(self):
        ps = PositionState()
        ps.record_entry(price=72000, qty=50, at=datetime(2026, 3, 29, 9, 30))
        assert not ps.is_empty()
        assert ps.entry_price == 72000
        assert ps.highest_price == 72000

    def test_dca_entry_weighted_avg(self):
        ps = PositionState()
        ps.record_entry(price=72000, qty=50, at=datetime(2026, 3, 29, 9, 30))
        ps.record_entry(price=70000, qty=30, at=datetime(2026, 3, 29, 10, 0))
        expected = (72000 * 50 + 70000 * 30) / 80
        assert ps.entry_price == expected
        assert ps.total_qty == 80

    def test_update_highest(self):
        ps = PositionState()
        ps.record_entry(price=72000, qty=50, at=datetime(2026, 3, 29, 9, 30))
        ps.update_cycle(current_price=74000)
        assert ps.highest_price == 74000
        ps.update_cycle(current_price=73000)
        assert ps.highest_price == 74000  # 갱신 안 됨

    def test_partial_exit(self):
        ps = PositionState()
        ps.record_entry(price=72000, qty=100, at=datetime(2026, 3, 29, 9, 30))
        ps.record_exit(qty=50)
        assert ps.total_qty == 50
        assert ps.remaining_ratio == 0.5
        assert not ps.is_empty()

    def test_full_exit_resets(self):
        ps = PositionState()
        ps.record_entry(price=72000, qty=100, at=datetime(2026, 3, 29, 9, 30))
        ps.record_exit(qty=100)
        assert ps.is_empty()
        assert ps.entry_price == 0

    def test_pnl_pct(self):
        ps = PositionState()
        ps.record_entry(price=72000, qty=50, at=datetime(2026, 3, 29, 9, 30))
        assert ps.pnl_pct(74000) == pytest.approx((74000 - 72000) / 72000 * 100, abs=0.01)

    def test_drawdown_from_high(self):
        ps = PositionState()
        ps.record_entry(price=72000, qty=50, at=datetime(2026, 3, 29, 9, 30))
        ps.update_cycle(current_price=74000)
        dd = ps.drawdown_from_high(73000)
        assert dd == pytest.approx((73000 - 74000) / 74000 * 100, abs=0.01)
```

- [ ] **Step 2: PositionState 구현**

```python
"""포지션 상태 관리. spec §3.3."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PositionState:
    entry_price: float = 0
    entry_time: datetime | None = None
    highest_price: float = 0
    total_qty: int = 0
    _initial_qty: int = 0
    bars_held: int = 0
    days_held: int = 0
    modifier_state: dict = field(default_factory=dict)

    @property
    def remaining_ratio(self) -> float:
        if self._initial_qty == 0:
            return 0
        return self.total_qty / self._initial_qty

    def is_empty(self) -> bool:
        return self.total_qty == 0

    def record_entry(self, price: float, qty: int, at: datetime) -> None:
        if self.total_qty == 0:
            self.entry_price = price
            self.entry_time = at
            self.highest_price = price
            self.total_qty = qty
            self._initial_qty = qty
        else:
            # DCA 가중평균
            total_cost = self.entry_price * self.total_qty + price * qty
            self.total_qty += qty
            self.entry_price = total_cost / self.total_qty

    def record_exit(self, qty: int) -> None:
        self.total_qty = max(0, self.total_qty - qty)
        if self.is_empty():
            self._reset()

    def update_cycle(self, current_price: float) -> None:
        if current_price > self.highest_price:
            self.highest_price = current_price
        self.bars_held += 1

    def pnl_pct(self, current_price: float) -> float:
        if self.entry_price == 0:
            return 0
        return (current_price - self.entry_price) / self.entry_price * 100

    def drawdown_from_high(self, current_price: float) -> float:
        if self.highest_price == 0:
            return 0
        return (current_price - self.highest_price) / self.highest_price * 100

    def _reset(self) -> None:
        self.entry_price = 0
        self.entry_time = None
        self.highest_price = 0
        self.total_qty = 0
        self._initial_qty = 0
        self.bars_held = 0
        self.days_held = 0
        self.modifier_state.clear()
```

- [ ] **Step 3: 테스트 실행**

Run: `python -m pytest local_server/tests/test_position_state.py -v`

- [ ] **Step 4: 커밋**

```bash
git add local_server/engine/position_state.py local_server/tests/test_position_state.py
git commit -m "feat(engine): PositionState — DCA 가중평균, 트레일링 고점, 부분 청산"
```

---

### Task 8: 지표 히스토리 링버퍼

**Files:**
- Create: `local_server/engine/indicator_history.py`
- Create: `local_server/tests/test_indicator_history.py`

- [ ] **Step 1: 테스트 작성**

```python
"""지표 히스토리 링버퍼 테스트."""
from local_server.engine.indicator_history import IndicatorHistory


class TestIndicatorHistory:
    def test_push_and_get(self):
        h = IndicatorHistory(max_size=60)
        h.push("RSI(14)", 35.2)
        h.push("RSI(14)", 38.1)
        h.push("RSI(14)", 42.0)
        assert h.get("RSI(14)", 0) == 42.0  # 현재
        assert h.get("RSI(14)", 1) == 38.1  # 1봉 전
        assert h.get("RSI(14)", 2) == 35.2  # 2봉 전

    def test_get_out_of_range(self):
        h = IndicatorHistory(max_size=60)
        h.push("RSI(14)", 35.2)
        assert h.get("RSI(14)", 1) is None

    def test_max_size_eviction(self):
        h = IndicatorHistory(max_size=3)
        for i in range(5):
            h.push("MA(20)", float(i))
        assert h.get("MA(20)", 0) == 4.0
        assert h.get("MA(20)", 2) == 2.0
        assert h.get("MA(20)", 3) is None  # 밀려남

    def test_get_all_as_list(self):
        h = IndicatorHistory(max_size=60)
        for i in range(5):
            h.push("현재가", float(100 + i))
        lst = h.get_list("현재가")
        assert lst == [100.0, 101.0, 102.0, 103.0, 104.0]
```

- [ ] **Step 2: 링버퍼 구현**

```python
"""지표 히스토리 링버퍼. spec §5.5."""
from __future__ import annotations
from collections import deque


class IndicatorHistory:
    def __init__(self, max_size: int = 60) -> None:
        self._max = max_size
        self._data: dict[str, deque[float]] = {}

    def push(self, key: str, value: float) -> None:
        if key not in self._data:
            self._data[key] = deque(maxlen=self._max)
        self._data[key].append(value)

    def get(self, key: str, index: int) -> float | None:
        buf = self._data.get(key)
        if buf is None or index >= len(buf):
            return None
        return buf[-(index + 1)]

    def get_list(self, key: str) -> list[float]:
        buf = self._data.get(key)
        return list(buf) if buf else []

    def clear(self) -> None:
        self._data.clear()
```

- [ ] **Step 3: 테스트 실행 + 커밋**

```bash
python -m pytest local_server/tests/test_indicator_history.py -v
git add local_server/engine/indicator_history.py local_server/tests/test_indicator_history.py
git commit -m "feat(engine): 지표 히스토리 링버퍼 (최근 60봉, §5.5)"
```

---

### Task 9: 조건 상태 추적기

**Files:**
- Create: `local_server/engine/condition_tracker.py`
- Create: `local_server/tests/test_condition_tracker.py`

- [ ] **Step 1: 테스트 작성**

```python
"""조건 상태 추적기 테스트."""
from local_server.engine.condition_tracker import ConditionTracker


class TestConditionTracker:
    def test_record_and_get(self):
        tracker = ConditionTracker(max_history=100)
        tracker.record(rule_id=1, cycle="2026-03-29T10:01:00",
                      conditions=[{"index": 0, "expr": "RSI(14) < 30",
                                   "result": True, "details": {"RSI(14)": 25}}],
                      position={"status": "미보유"},
                      action={"side": "매수", "quantity": "100%"})
        snap = tracker.get_latest(rule_id=1)
        assert snap is not None
        assert snap["conditions"][0]["result"] is True

    def test_trigger_history(self):
        tracker = ConditionTracker(max_history=100)
        tracker.record_trigger(rule_id=1, at="2026-03-29T10:01:00",
                              index=0, action="매수 100%")
        history = tracker.get_trigger_history(rule_id=1)
        assert len(history) == 1
        assert history[0]["action"] == "매수 100%"
```

- [ ] **Step 2: 추적기 구현**

```python
"""조건 상태 추적기. spec §3.6."""
from __future__ import annotations
from collections import deque
from typing import Any


class ConditionTracker:
    def __init__(self, max_history: int = 100) -> None:
        self._latest: dict[int, dict] = {}
        self._triggers: dict[int, deque[dict]] = {}
        self._max = max_history

    def record(self, rule_id: int, cycle: str,
               conditions: list[dict], position: dict,
               action: dict | None) -> None:
        self._latest[rule_id] = {
            "rule_id": rule_id,
            "cycle": cycle,
            "conditions": conditions,
            "position": position,
            "action": action,
        }

    def record_trigger(self, rule_id: int, at: str,
                       index: int, action: str) -> None:
        if rule_id not in self._triggers:
            self._triggers[rule_id] = deque(maxlen=self._max)
        self._triggers[rule_id].append({"at": at, "index": index, "action": action})

    def get_latest(self, rule_id: int) -> dict | None:
        snap = self._latest.get(rule_id)
        if snap is None:
            return None
        snap["triggered_history"] = list(self._triggers.get(rule_id, []))
        return snap

    def get_all_latest(self) -> dict[int, dict]:
        return {rid: self.get_latest(rid) for rid in self._latest}

    def get_trigger_history(self, rule_id: int) -> list[dict]:
        return list(self._triggers.get(rule_id, []))
```

- [ ] **Step 3: 테스트 실행 + 커밋**

```bash
python -m pytest local_server/tests/test_condition_tracker.py -v
git add local_server/engine/condition_tracker.py local_server/tests/test_condition_tracker.py
git commit -m "feat(engine): 조건 상태 추적기 (투명성 API 데이터, §3.6)"
```

---

### Task 10: 조건 상태 API 라우터

**Files:**
- Create: `local_server/routers/condition_status.py`
- Modify: `local_server/main.py` (라우터 등록)

- [ ] **Step 1: 라우터 구현**

```python
"""조건 상태 API. spec §3.6 T5."""
from fastapi import APIRouter

router = APIRouter(prefix="/api/conditions", tags=["conditions"])


@router.get("/status")
async def get_all_status():
    """모든 규칙의 최신 조건 상태 반환."""
    from local_server.engine import get_engine
    engine = get_engine()
    if engine is None or engine._condition_tracker is None:
        return {"success": True, "data": {}, "count": 0}
    data = engine._condition_tracker.get_all_latest()
    return {"success": True, "data": data, "count": len(data)}


@router.get("/status/{rule_id}")
async def get_rule_status(rule_id: int):
    """특정 규칙의 조건 상태 반환."""
    from local_server.engine import get_engine
    engine = get_engine()
    if engine is None or engine._condition_tracker is None:
        return {"success": True, "data": None}
    data = engine._condition_tracker.get_latest(rule_id)
    return {"success": True, "data": data}
```

- [ ] **Step 2: main.py에 라우터 등록**

`local_server/main.py`에 추가:

```python
from local_server.routers.condition_status import router as condition_router
app.include_router(condition_router)
```

- [ ] **Step 3: 커밋**

```bash
git add local_server/routers/condition_status.py local_server/main.py
git commit -m "feat(api): 조건 상태 API 엔드포인트 (/api/conditions/status)"
```

---

### Task 11: 엔진 통합 — v2 평가 경로 연결

**Files:**
- Modify: `local_server/engine/evaluator.py`
- Modify: `local_server/engine/engine.py`
- Modify: `local_server/engine/executor.py`

이 태스크는 기존 엔진 코드에 v2 경로를 연결하는 통합 작업. 기존 v1 경로는 유지하면서 `script`에 `→`가 포함되면 v2 경로로 분기.

- [ ] **Step 1: evaluator.py에 v2 분기 추가**

```python
# local_server/engine/evaluator.py — evaluate() 메서드에 추가
def evaluate(self, rule: dict, market_data: dict, context: dict):
    script = rule.get("script")
    if script and "→" in script or "->" in script:
        return self._evaluate_v2(rule, market_data, context)
    # 기존 v1 경로 유지
    ...

def _evaluate_v2(self, rule, market_data, context):
    """v2 DSL 평가. EvalResult 리스트를 반환."""
    from sv_core.parsing.parser_v2 import parse_v2
    from sv_core.parsing.evaluator_v2 import evaluate_v2
    # AST 캐시 (rule_id + script hash)
    # context 구성 (market_data + position 필드 + indicator 함수)
    # evaluate_v2 호출
    # EvalResult → (buy, sell) 또는 선택된 Action 반환
    ...
```

- [ ] **Step 2: engine.py에 PositionState + ConditionTracker 통합**

```python
# engine.py — __init__에 추가
self._position_states: dict[str, PositionState] = {}  # symbol → state
self._condition_tracker = ConditionTracker()
self._indicator_history = IndicatorHistory()
```

`evaluate_all()` 흐름에 v2 연동:
- 매 사이클 PositionState.update_cycle() 호출
- v2 평가 결과에서 selected Action 추출
- ConditionTracker.record() 호출
- 선택된 Action이 있으면 CandidateSignal 생성 (기존 흐름과 합류)

- [ ] **Step 3: executor.py에 부분 매도 지원**

```python
# executor.py — execute() 메서드에 수량 비율 계산 추가
# action.quantity가 "50%"면: qty = int(보유수량 * 0.5)
# "전량"이면: qty = 보유수량
# "나머지"면: qty = 보유수량 (같은 사이클에서 1개만 실행되므로)
```

- [ ] **Step 4: 통합 테스트**

```bash
python -m pytest local_server/tests/test_engine.py -v
python -m pytest sv_core/parsing/tests/ -v
```

- [ ] **Step 5: 커밋**

```bash
git add local_server/engine/
git commit -m "feat(engine): v2 평가 경로 통합 — PositionState, ConditionTracker, 부분 매도"
```

---

## Phase 3: 클라우드 서버 변경

### Task 12: parameters 컬럼 추가

**Files:**
- Modify: `cloud_server/models/rule.py`
- Modify: `cloud_server/api/rules.py`

- [ ] **Step 1: TradingRule에 parameters 컬럼 추가**

```python
# cloud_server/models/rule.py
parameters = Column(JSON, nullable=True)  # {"기간": {"default": 14, "min": 1, "max": 60}, ...}
```

- [ ] **Step 2: API에 parameters CRUD 추가**

`RuleCreateBody`에 `parameters: dict | None = None` 필드 추가.

- [ ] **Step 3: 마이그레이션 + 커밋**

```bash
git add cloud_server/models/rule.py cloud_server/api/rules.py
git commit -m "feat(cloud): TradingRule parameters JSON 컬럼 추가"
```

---

## Phase 4: 프론트엔드

### Task 13: 조건 상태 타입 + 폴링 훅

**Files:**
- Create: `frontend/src/types/condition-status.ts`
- Create: `frontend/src/hooks/useConditionStatus.ts`

- [ ] **Step 1: TypeScript 타입 정의**

```typescript
// frontend/src/types/condition-status.ts
export interface ConditionDetail {
  index: number
  expr: string
  result: boolean
  details: Record<string, number | boolean | string | null>
}

export interface PositionInfo {
  status: string
  entry_price: number
  highest_price: number
  pnl_pct: number
  bars_held: number
  days_held: number
  remaining_ratio: number
}

export interface TriggerEntry {
  at: string
  index: number
  action: string
}

export interface ConditionStatus {
  rule_id: number
  cycle: string
  position: PositionInfo | null
  conditions: ConditionDetail[]
  action: { side: string; quantity: string } | null
  triggered_history: TriggerEntry[]
}
```

- [ ] **Step 2: React Query 폴링 훅**

```typescript
// frontend/src/hooks/useConditionStatus.ts
import { useQuery } from '@tanstack/react-query'
import { localClient } from '../services/localClient'
import type { ConditionStatus } from '../types/condition-status'

export function useConditionStatus(ruleId: number | null) {
  return useQuery<ConditionStatus | null>({
    queryKey: ['condition-status', ruleId],
    queryFn: async () => {
      if (!ruleId) return null
      const res = await localClient.get(`/api/conditions/status/${ruleId}`)
      return res.data?.data ?? null
    },
    refetchInterval: 3000,
    enabled: !!ruleId,
  })
}

export function useAllConditionStatus() {
  return useQuery<Record<number, ConditionStatus>>({
    queryKey: ['condition-status-all'],
    queryFn: async () => {
      const res = await localClient.get('/api/conditions/status')
      return res.data?.data ?? {}
    },
    refetchInterval: 3000,
  })
}
```

- [ ] **Step 3: 커밋**

```bash
git add frontend/src/types/condition-status.ts frontend/src/hooks/useConditionStatus.ts
git commit -m "feat(frontend): 조건 상태 TypeScript 타입 + React Query 폴링 훅"
```

---

### Task 14: 전략 모니터링 카드 컴포넌트

**Files:**
- Create: `frontend/src/components/StrategyMonitorCard.tsx`
- Create: `frontend/src/components/ConditionStatusRow.tsx`
- Create: `frontend/src/components/TriggerTimeline.tsx`

- [ ] **Step 1: ConditionStatusRow 컴포넌트**

```tsx
// frontend/src/components/ConditionStatusRow.tsx
import type { ConditionDetail } from '../types/condition-status'

interface Props {
  condition: ConditionDetail
}

export default function ConditionStatusRow({ condition }: Props) {
  const { expr, result, details } = condition
  const detailStr = Object.entries(details)
    .map(([k, v]) => `${k}: ${typeof v === 'number' ? v.toLocaleString() : v}`)
    .join('  ')

  return (
    <div className="flex items-center justify-between px-3 py-2 border-b border-default-100 last:border-b-0">
      <div className="flex-1">
        <div className="text-sm font-mono">{expr}</div>
        <div className="text-xs text-default-400">{detailStr}</div>
      </div>
      <div className={`text-lg ${result ? 'text-success' : 'text-default-300'}`}>
        {result ? '●' : '○'}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: TriggerTimeline 컴포넌트**

```tsx
// frontend/src/components/TriggerTimeline.tsx
import type { TriggerEntry } from '../types/condition-status'

interface Props {
  history: TriggerEntry[]
  maxItems?: number
}

export default function TriggerTimeline({ history, maxItems = 5 }: Props) {
  const recent = history.slice(-maxItems).reverse()
  if (recent.length === 0) return null

  return (
    <div className="mt-2">
      <div className="text-xs font-semibold text-default-500 mb-1">최근 트리거</div>
      {recent.map((entry, i) => (
        <div key={i} className="flex items-center gap-2 text-xs text-default-400 py-0.5">
          <span className="font-mono">{entry.at.slice(11, 16)}</span>
          <span>{entry.action}</span>
        </div>
      ))}
    </div>
  )
}
```

- [ ] **Step 3: StrategyMonitorCard 컴포넌트**

```tsx
// frontend/src/components/StrategyMonitorCard.tsx
import { Card, CardBody, CardHeader, Chip } from '@heroui/react'
import ConditionStatusRow from './ConditionStatusRow'
import TriggerTimeline from './TriggerTimeline'
import { useConditionStatus } from '../hooks/useConditionStatus'
import type { Rule } from '../types/strategy'

interface Props {
  rule: Rule
}

export default function StrategyMonitorCard({ rule }: Props) {
  const { data: status } = useConditionStatus(rule.id)

  const buyConditions = status?.conditions.filter(c => c.expr.includes('매수')) ?? []
  const sellConditions = status?.conditions.filter(c => !c.expr.includes('매수')) ?? []

  return (
    <Card className="w-full">
      <CardHeader className="flex justify-between items-center">
        <div className="font-semibold">{rule.name}</div>
        <Chip size="sm" color={rule.is_active ? 'success' : 'default'}>
          {rule.is_active ? '실행중' : '중지'}
        </Chip>
      </CardHeader>
      <CardBody className="p-0">
        {/* 규칙 목록 */}
        {status?.conditions.map((c) => (
          <ConditionStatusRow key={c.index} condition={c} />
        ))}

        {/* 포지션 정보 */}
        {status?.position && !isEmptyPosition(status.position) && (
          <div className="px-3 py-2 bg-default-50 text-xs">
            <span>진입: {status.position.entry_price.toLocaleString()}원</span>
            <span className="ml-3">최고: {status.position.highest_price.toLocaleString()}원</span>
            <span className="ml-3">보유: {status.position.days_held}일 {status.position.bars_held}봉</span>
          </div>
        )}

        {/* 트리거 이력 */}
        {status?.triggered_history && (
          <div className="px-3 pb-2">
            <TriggerTimeline history={status.triggered_history} />
          </div>
        )}
      </CardBody>
    </Card>
  )
}

function isEmptyPosition(pos: { entry_price: number }) {
  return pos.entry_price === 0
}
```

- [ ] **Step 4: 커밋**

```bash
git add frontend/src/components/StrategyMonitorCard.tsx frontend/src/components/ConditionStatusRow.tsx frontend/src/components/TriggerTimeline.tsx
git commit -m "feat(frontend): 전략 모니터링 카드 — 조건 상태 + 트리거 이력"
```

---

### Task 15: StrategyList에 모니터링 카드 통합

**Files:**
- Modify: `frontend/src/pages/StrategyList.tsx`

- [ ] **Step 1: 기존 RuleCard를 StrategyMonitorCard로 교체/병행**

엔진 실행 중인 규칙에 대해 StrategyMonitorCard를 표시. 엔진 미실행 시 기존 RuleCard 유지.

```tsx
// StrategyList.tsx 내 규칙 카드 렌더링 부분
{rules.map(rule => (
  engineRunning && conditionStatusAvailable
    ? <StrategyMonitorCard key={rule.id} rule={rule} />
    : <RuleCard key={rule.id} rule={rule} ... />
))}
```

- [ ] **Step 2: 커밋**

```bash
git add frontend/src/pages/StrategyList.tsx
git commit -m "feat(frontend): StrategyList에 모니터링 카드 통합"
```

---

### Task 16: DSL 직접 편집 모드

**Files:**
- Modify: `frontend/src/pages/StrategyBuilder.tsx`

- [ ] **Step 1: v2 DSL 편집 토글 추가**

기존 폼 모드 + 스크립트 모드에 "v2 편집" 모드를 추가. `→` 가 포함된 스크립트는 v2로 인식.

- [ ] **Step 2: 커밋**

```bash
git add frontend/src/pages/StrategyBuilder.tsx
git commit -m "feat(frontend): StrategyBuilder v2 DSL 편집 모드"
```

---

## 최종 통합 테스트

### Task 17: 전체 회귀 테스트

- [ ] **Step 1: sv_core 전체 테스트**

```bash
python -m pytest sv_core/ -v
```

Expected: 기존 v1 테스트 + 신규 v2 테스트 전부 PASS

- [ ] **Step 2: local_server 전체 테스트**

```bash
python -m pytest local_server/tests/ -v
```

Expected: 기존 테스트 + 신규 테스트 전부 PASS

- [ ] **Step 3: frontend 전체 테스트**

```bash
cd frontend && npm run test && npm run lint
```

Expected: PASS

- [ ] **Step 4: spec 상태 갱신**

`spec/strategy-engine-v2/spec.md` 상단 상태를 `구현 완료`로 변경, P0 체크박스 전부 체크.

- [ ] **Step 5: 최종 커밋**

```bash
git add spec/strategy-engine-v2/spec.md
git commit -m "docs: strategy-engine-v2 spec 구현 완료 상태 갱신"
```
