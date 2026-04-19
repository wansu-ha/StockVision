# 전략 엔진 v2 구현 계획

> 작성일: 2026-03-29 | 상태: 구현 완료 | Phase E
>
> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** DSL v2 파서 + 엔진 실행 모델 + 조건 상태 API + 카드 UI 모니터링을 구현하여, 프로 수준 전략 표현과 실시간 투명성을 제공한다.

**Architecture:** 4개 Phase 순차 구현. Phase 1(sv_core DSL 파서) → Phase 2(local_server 엔진) → Phase 3(상태 API + 클라우드) → Phase 4(프론트엔드). 각 Phase는 독립 테스트 가능. P0 항목 먼저 구현 후 P1 확장.

**Tech Stack:** Python 3.13 (sv_core, local_server, cloud_server), FastAPI, SQLAlchemy, React 19, TypeScript, Vite, Tailwind CSS, HeroUI, React Query

---

## 파일 구조

### 신규 생성 파일

| 파일 | 설명 |
|------|------|
| `sv_core/parsing/tests/test_parser_v2.py` | v2 파서 테스트 |
| `sv_core/parsing/tests/test_evaluator_v2.py` | v2 평가기 테스트 |
| `local_server/engine/position_state.py` | PositionState 클래스 |
| `local_server/engine/condition_tracker.py` | 조건 상태 추적기 |
| `local_server/engine/tests/test_position_state.py` | PositionState 테스트 |
| `local_server/engine/tests/test_condition_tracker.py` | 조건 추적기 테스트 |
| `local_server/engine/tests/test_engine_v2.py` | v2 엔진 통합 테스트 |
| `local_server/routers/conditions.py` | 조건 상태 API 라우터 |
| `frontend/src/hooks/useConditionStatus.ts` | 조건 상태 API 훅 |
| `frontend/src/components/strategy/StrategyMonitorCard.tsx` | 전략 모니터링 카드 |
| `frontend/src/components/strategy/ConditionStatusRow.tsx` | 조건 행 컴포넌트 |
| `frontend/src/components/strategy/TriggerTimeline.tsx` | 트리거 이력 타임라인 |

### 수정 파일

| 파일 | 변경 |
|------|------|
| `sv_core/parsing/tokens.py` | ARROW, PERCENT, LBRACKET, RBRACKET, KW_ALL, KW_REST, KW_BETWEEN 토큰 추가 |
| `sv_core/parsing/lexer.py` | 새 토큰 렉싱 (→, ->, %, [, ]) |
| `sv_core/parsing/ast_nodes.py` | Rule, Action, ConstDecl, IndexAccess, ScriptV2 노드 추가 |
| `sv_core/parsing/parser.py` | v2 문법 파싱 + v1 매수:/매도: 폴백 |
| `sv_core/parsing/evaluator.py` | 규칙 리스트 평가, 상태 함수, IndexAccess, 우선순위 충돌 해소 |
| `sv_core/parsing/builtins.py` | ATR, 최고가, 최저가, 이격도, 횟수, 연속, 실행횟수, 시간/보유 필드 추가 |
| `sv_core/parsing/__init__.py` | evaluate_v2 함수 공개 |
| `sv_core/indicators/calculator.py` | calc_atr, calc_highest, calc_lowest 추가 |
| `local_server/engine/evaluator.py` | v2 평가 모델 (규칙 리스트, ActionResult 반환) |
| `local_server/engine/engine.py` | PositionState 관리, 다단계 청산, 조건 상태 수집 |
| `local_server/engine/executor.py` | 부분 매도 비율 계산 |
| `local_server/engine/indicator_provider.py` | ATR/최고가/최저가 계산, 지표 히스토리 링버퍼 |
| `cloud_server/models/rule.py` | parameters JSON 컬럼 추가 |
| `cloud_server/api/rules.py` | 파라미터 메타데이터 CRUD |
| `frontend/src/types/strategy.ts` | v2 타입 추가 (ConditionStatus, PositionInfo 등) |
| `frontend/src/services/localClient.ts` | conditions API 추가 |
| `frontend/src/pages/StrategyList.tsx` | 모니터링 카드 통합 |
| `frontend/src/utils/dslParser.ts` | v2 DSL 파싱/직렬화 (카드 UI ↔ DSL 변환) |

---

## Phase 1: DSL 파서 (sv_core)

### Task 1.1 — 토큰 확장

- [ ] `sv_core/parsing/tokens.py` — 새 토큰 타입 추가
- [ ] `sv_core/parsing/lexer.py` — 새 토큰 렉싱

**파일: `sv_core/parsing/tokens.py`**

TokenType enum에 다음을 추가:

```python
# tokens.py — TokenType enum 내부에 추가
    ARROW = auto()     # → 또는 ->
    PERCENT = auto()   # %
    LBRACKET = auto()  # [
    RBRACKET = auto()  # ]

    # v2 키워드
    KW_ALL = auto()    # 전량
    KW_REST = auto()   # 나머지
    KW_BETWEEN = auto()  # BETWEEN
```

KEYWORDS dict에 추가:

```python
KEYWORDS: dict[str, TokenType] = {
    "매수": TokenType.KW_BUY,
    "매도": TokenType.KW_SELL,
    "AND": TokenType.AND,
    "OR": TokenType.OR,
    "NOT": TokenType.NOT,
    "전량": TokenType.KW_ALL,
    "나머지": TokenType.KW_REST,
    "BETWEEN": TokenType.KW_BETWEEN,
}
```

**파일: `sv_core/parsing/lexer.py`**

`_TWO_CHAR_OPS`에 추가:

```python
_TWO_CHAR_OPS: dict[str, TokenType] = {
    ">=": TokenType.GE,
    "<=": TokenType.LE,
    "==": TokenType.EQ,
    "!=": TokenType.NE,
    "->": TokenType.ARROW,
}
```

`_ONE_CHAR_OPS`에 추가:

```python
_ONE_CHAR_OPS: dict[str, TokenType] = {
    # ... 기존 유지 ...
    "%": TokenType.PERCENT,
    "[": TokenType.LBRACKET,
    "]": TokenType.RBRACKET,
}
```

렉서 메인 루프에서 `→` (U+2192) 처리 추가. 주석 판별 전에 위치:

```python
# lexer.py — while 루프 내, 주석 처리 직후에 추가
# → (U+2192) 유니코드 화살표
if ch == "\u2192":
    tokens.append(Token(TokenType.ARROW, "\u2192", line, col))
    pos += 1
    col += 1
    continue
```

주의: `→`는 식별자 시작 문자로 인식될 수 있으므로, `_is_ident_start`에서 화살표를 제외할 필요는 없다 — `\u2192`는 `isalpha()`가 False이므로 이미 제외됨.

**테스트: `sv_core/parsing/tests/test_parser_v2.py`** (이 Task에서는 렉서 테스트만)

```python
"""v2 파서 테스트 — Task 1.1: 토큰 확장."""
import pytest
from sv_core.parsing.lexer import tokenize
from sv_core.parsing.tokens import TokenType


class TestV2Tokens:
    def test_arrow_unicode(self):
        tokens = tokenize("조건 → 매수 100%")
        types = [t.type for t in tokens]
        assert TokenType.ARROW in types

    def test_arrow_ascii(self):
        tokens = tokenize("조건 -> 매도 전량")
        types = [t.type for t in tokens]
        assert TokenType.ARROW in types

    def test_percent(self):
        tokens = tokenize("매수 50%")
        assert tokens[1].type == TokenType.NUMBER
        assert tokens[2].type == TokenType.PERCENT

    def test_brackets(self):
        tokens = tokenize("현재가[1]")
        types = [t.type for t in tokens]
        assert TokenType.LBRACKET in types
        assert TokenType.RBRACKET in types

    def test_keyword_all(self):
        tokens = tokenize("매도 전량")
        assert tokens[1].type == TokenType.KW_ALL

    def test_keyword_rest(self):
        tokens = tokenize("매도 나머지")
        assert tokens[1].type == TokenType.KW_REST

    def test_keyword_between(self):
        tokens = tokenize("수익률 BETWEEN 1 AND 3")
        types = [t.type for t in tokens]
        assert TokenType.KW_BETWEEN in types
```

**테스트 실행:**

```bash
cd d:/Projects/StockVision
python -m pytest sv_core/parsing/tests/test_parser_v2.py::TestV2Tokens -v
# 기대: 7 passed
```

**git:**

```bash
git add sv_core/parsing/tokens.py sv_core/parsing/lexer.py sv_core/parsing/tests/test_parser_v2.py
git commit -m "feat(dsl): v2 토큰 확장 — ARROW, PERCENT, BRACKET, BETWEEN, 전량/나머지 키워드"
```

---

### Task 1.2 — AST 노드 추가

- [ ] `sv_core/parsing/ast_nodes.py` — v2 전용 노드 추가

기존 노드(`BuyBlock`, `SellBlock`, `Script` 등)는 수정하지 않음 — v1 호환용으로 유지.

**파일: `sv_core/parsing/ast_nodes.py`** — 파일 하단에 추가:

```python
# ── v2 노드 ──

@dataclass(frozen=True, slots=True)
class ConstDecl(Node):
    """상수 선언: 이름 = 값."""
    name: str = ""
    value: Node = field(default_factory=Node)  # NumberLit 또는 StringLit


@dataclass(frozen=True, slots=True)
class IndexAccess(Node):
    """이전 봉 참조: expr[N]. N은 정수, 최대 60."""
    expr: Node = field(default_factory=Node)
    index: int = 0


@dataclass(frozen=True, slots=True)
class Action(Node):
    """행동: 매수/매도 + 수량.

    side: "매수" | "매도"
    qty_type: "percent" | "all"
    qty_value: float  — percent일 때 0~100, all일 때 무시
    """
    side: str = ""
    qty_type: str = "all"  # "percent" | "all"
    qty_value: float = 100.0


@dataclass(frozen=True, slots=True)
class Rule(Node):
    """규칙: 조건 → 행동."""
    condition: Node = field(default_factory=Node)
    action: Action = field(default_factory=Action)


@dataclass(frozen=True, slots=True)
class ScriptV2(Node):
    """v2 최상위 AST — 상수 선언 + 규칙 리스트.

    custom_funcs: 커스텀 함수(v1 호환 + v2 `이름 = 조건식`)
    consts: 상수 선언 리스트
    rules: 규칙 리스트 (위→아래 = 우선순위)
    """
    custom_funcs: tuple[CustomFuncDef, ...] = ()
    consts: tuple[ConstDecl, ...] = ()
    rules: tuple[Rule, ...] = ()
```

**테스트: `sv_core/parsing/tests/test_parser_v2.py`에 추가**

```python
from sv_core.parsing.ast_nodes import (
    Action, ConstDecl, IndexAccess, Rule, ScriptV2,
    NumberLit, StringLit, FieldRef, FuncCall, Comparison, BinOp,
)


class TestV2ASTNodes:
    def test_const_decl_number(self):
        node = ConstDecl(name="기간", value=NumberLit(value=14.0))
        assert node.name == "기간"
        assert node.value.value == 14.0

    def test_const_decl_string(self):
        node = ConstDecl(name="tf", value=StringLit(value="1d"))
        assert node.name == "tf"

    def test_index_access(self):
        node = IndexAccess(
            expr=FieldRef(name="현재가"),
            index=1,
        )
        assert node.index == 1

    def test_action_percent(self):
        action = Action(side="매수", qty_type="percent", qty_value=50.0)
        assert action.side == "매수"
        assert action.qty_type == "percent"
        assert action.qty_value == 50.0

    def test_action_all(self):
        action = Action(side="매도", qty_type="all")
        assert action.qty_type == "all"

    def test_rule(self):
        rule = Rule(
            condition=Comparison(op=">", left=FieldRef(name="수익률"), right=NumberLit(value=5.0)),
            action=Action(side="매도", qty_type="all"),
        )
        assert isinstance(rule.condition, Comparison)
        assert rule.action.side == "매도"

    def test_script_v2(self):
        s = ScriptV2(
            consts=(ConstDecl(name="손절", value=NumberLit(value=-2.0)),),
            rules=(
                Rule(
                    condition=FieldRef(name="골든크로스"),
                    action=Action(side="매수", qty_type="percent", qty_value=100.0),
                ),
            ),
        )
        assert len(s.consts) == 1
        assert len(s.rules) == 1
```

**테스트 실행:**

```bash
python -m pytest sv_core/parsing/tests/test_parser_v2.py::TestV2ASTNodes -v
# 기대: 7 passed
```

**git:**

```bash
git add sv_core/parsing/ast_nodes.py sv_core/parsing/tests/test_parser_v2.py
git commit -m "feat(dsl): v2 AST 노드 — ConstDecl, IndexAccess, Action, Rule, ScriptV2"
```

---

### Task 1.3 — v2 파서 구현

- [ ] `sv_core/parsing/parser.py` — v2 문법 파싱

파서 전략:
1. `parse()` 함수는 기존대로 유지 (v1 반환).
2. 새로운 `parse_v2()` 함수를 추가 — `ScriptV2` 반환.
3. `parse()` 내부에서 `→` / `->` 토큰이 존재하면 자동으로 `parse_v2()` 위임.
4. v1 `매수:/매도:` 패턴 감지 시 자동 변환하여 `ScriptV2` 반환.

**파일: `sv_core/parsing/parser.py`**

`Parser` 클래스에 다음 메서드 추가:

```python
class Parser:
    # ... 기존 코드 유지 ...

    def parse_v2(self) -> ScriptV2:
        """v2 파싱 → ScriptV2 AST."""
        self._skip_newlines()

        consts: list[ConstDecl] = []
        custom_funcs: list[CustomFuncDef] = []
        rules: list[Rule] = []

        while not self._at(TokenType.EOF):
            tok = self._peek()

            # v1 호환: 매수: expr, 매도: expr → v2 규칙으로 변환
            if tok.type == TokenType.KW_BUY and self._is_v1_block():
                rules.extend(self._parse_v1_buy_as_rules())
                self._skip_newlines()
                continue
            if tok.type == TokenType.KW_SELL and self._is_v1_block():
                rules.extend(self._parse_v1_sell_as_rules())
                self._skip_newlines()
                continue

            # IDENT 시작 — 상수, 커스텀 함수, 또는 규칙의 조건 시작
            if tok.type == TokenType.IDENT:
                if self._is_const_or_func_def():
                    node = self._parse_const_or_func_def()
                    if isinstance(node, ConstDecl):
                        consts.append(node)
                    else:
                        custom_funcs.append(node)
                    self._skip_newlines()
                    continue

            # 규칙: 조건 → 행동
            rule = self._parse_rule()
            rules.append(rule)
            self._skip_newlines()

        if not rules:
            tok = self._peek()
            raise DSLSyntaxError("규칙이 하나 이상 필요합니다", tok.line, tok.col)

        return ScriptV2(
            custom_funcs=tuple(custom_funcs),
            consts=tuple(consts),
            rules=tuple(rules),
        )

    def _is_v1_block(self) -> bool:
        """현재 위치가 v1 블록 (매수: / 매도:)인지."""
        p = self._pos
        if p + 1 >= len(self._tokens):
            return False
        return self._tokens[p + 1].type == TokenType.COLON

    def _parse_v1_buy_as_rules(self) -> list[Rule]:
        """v1 매수: expr → v2 규칙 변환.

        변환: expr AND 보유수량 == 0 → 매수 100%
        """
        tok = self._advance()  # 매수
        self._expect(TokenType.COLON)
        expr = self._parse_expression()
        self._check_type(expr, _BOOLEAN, "매수: 블록 결과는 boolean이어야 합니다")
        self._expect_terminator()

        # 보유수량 == 0 조건 추가
        hold_check = Comparison(
            op="==",
            left=FieldRef(name="보유수량"),
            right=NumberLit(value=0.0),
            line=tok.line, col=tok.col,
        )
        combined = BinOp(op="AND", left=expr, right=hold_check, line=tok.line, col=tok.col)

        return [Rule(
            condition=combined,
            action=Action(side="매수", qty_type="percent", qty_value=100.0),
            line=tok.line, col=tok.col,
        )]

    def _parse_v1_sell_as_rules(self) -> list[Rule]:
        """v1 매도: expr → v2 규칙 변환.

        변환: expr → 매도 전량
        """
        tok = self._advance()  # 매도
        self._expect(TokenType.COLON)
        expr = self._parse_expression()
        self._check_type(expr, _BOOLEAN, "매도: 블록 결과는 boolean이어야 합니다")
        self._expect_terminator()

        return [Rule(
            condition=expr,
            action=Action(side="매도", qty_type="all"),
            line=tok.line, col=tok.col,
        )]

    def _is_const_or_func_def(self) -> bool:
        """IDENT 다음이 = 또는 IDENT ( ) = 인지 lookahead."""
        p = self._pos
        tokens = self._tokens
        if p + 1 >= len(tokens):
            return False
        # IDENT = 값 (상수 또는 커스텀 함수)
        if tokens[p + 1].type == TokenType.ASSIGN:
            return True
        # IDENT ( ) = 식 (v1 커스텀 함수)
        if (p + 3 < len(tokens)
            and tokens[p + 1].type == TokenType.LPAREN
            and tokens[p + 2].type == TokenType.RPAREN
            and tokens[p + 3].type == TokenType.ASSIGN):
            return True
        return False

    def _parse_const_or_func_def(self) -> ConstDecl | CustomFuncDef:
        """상수 또는 커스텀 함수 정의 파싱.

        이름 = 숫자/문자열 → ConstDecl
        이름 = 조건식 → CustomFuncDef (괄호 없는 커스텀 함수)
        이름() = 식 → CustomFuncDef (v1 호환)
        """
        name_tok = self._peek()
        name = name_tok.value

        # 이름 중복 체크
        if name in self._custom_funcs:
            raise DSLNameError(f"'{name}'이 이미 정의되었습니다", name_tok.line, name_tok.col)

        # v1 형태: IDENT ( ) = expr
        if (self._pos + 3 < len(self._tokens)
            and self._tokens[self._pos + 1].type == TokenType.LPAREN
            and self._tokens[self._pos + 2].type == TokenType.RPAREN
            and self._tokens[self._pos + 3].type == TokenType.ASSIGN):
            return self._parse_custom_func_def()

        # v2 형태: IDENT = 값_or_조건식
        self._advance()  # name
        self._expect(TokenType.ASSIGN)

        # peek — 숫자 또는 문자열만이면 상수
        tok = self._peek()
        if tok.type == TokenType.NUMBER:
            # 숫자 다음이 줄끝/EOF이면 상수
            if self._is_simple_const_value():
                val = self._advance()
                self._expect_terminator()

                # 내장 이름과 충돌 시 경고 (§2.5 rule 7)
                if name in BUILTIN_FIELDS or name in BUILTIN_FUNCTIONS or name in BUILTIN_PATTERNS:
                    # 경고만 — 사용자 상수 우선
                    pass

                return ConstDecl(
                    name=name,
                    value=NumberLit(value=float(val.value), line=val.line, col=val.col),
                    line=name_tok.line, col=name_tok.col,
                )

        if tok.type == TokenType.STRING:
            val = self._advance()
            self._expect_terminator()
            return ConstDecl(
                name=name,
                value=StringLit(value=val.value, line=val.line, col=val.col),
                line=name_tok.line, col=name_tok.col,
            )

        # 조건식 → 커스텀 함수 (괄호 없는 v2 형태)
        self._current_func_name = name
        body = self._parse_expression()
        self._current_func_name = None

        ret_type = _infer_type(body, self._custom_funcs)
        self._custom_funcs[name] = ret_type

        self._expect_terminator()
        return CustomFuncDef(name=name, body=body, line=name_tok.line, col=name_tok.col)

    def _is_simple_const_value(self) -> bool:
        """현재 위치의 NUMBER 다음이 NEWLINE/EOF인지 (= 상수 선언).

        숫자 뒤에 연산자가 오면 조건식으로 판단 → 커스텀 함수.
        """
        p = self._pos
        # 현재 토큰이 NUMBER일 때, 다음 토큰 확인
        next_pos = p + 1
        if next_pos >= len(self._tokens):
            return True
        next_tok = self._tokens[next_pos]
        return next_tok.type in (TokenType.NEWLINE, TokenType.EOF)

    def _parse_rule(self) -> Rule:
        """규칙: 조건식 → 행동."""
        condition = self._parse_expression()
        self._check_type(condition, _BOOLEAN, "규칙의 조건은 boolean이어야 합니다")

        tok = self._peek()
        if tok.type != TokenType.ARROW:
            raise DSLSyntaxError(
                f"'→' 또는 '->'가 필요하지만 '{tok.value}'이 있습니다",
                tok.line, tok.col,
            )
        self._advance()  # →

        action = self._parse_action()
        self._expect_terminator()
        return Rule(condition=condition, action=action, line=tok.line, col=tok.col)

    def _parse_action(self) -> Action:
        """행동: 매수/매도 + 수량."""
        tok = self._peek()
        if tok.type not in (TokenType.KW_BUY, TokenType.KW_SELL):
            raise DSLSyntaxError(
                f"'매수' 또는 '매도'가 필요하지만 '{tok.value}'이 있습니다",
                tok.line, tok.col,
            )
        side_tok = self._advance()
        side = side_tok.value  # "매수" | "매도"

        # 수량: N% | 전량 | 나머지
        tok = self._peek()
        if tok.type == TokenType.KW_ALL:
            self._advance()
            return Action(side=side, qty_type="all", line=side_tok.line, col=side_tok.col)
        if tok.type == TokenType.KW_REST:
            self._advance()
            return Action(side=side, qty_type="all", line=side_tok.line, col=side_tok.col)  # 나머지 = 전량의 별칭
        if tok.type == TokenType.NUMBER:
            num_tok = self._advance()
            self._expect(TokenType.PERCENT)
            return Action(
                side=side, qty_type="percent", qty_value=float(num_tok.value),
                line=side_tok.line, col=side_tok.col,
            )

        raise DSLSyntaxError(
            f"수량이 필요합니다 (N%, 전량, 나머지): '{tok.value}'",
            tok.line, tok.col,
        )
```

파서 `_parse_comparison`에 BETWEEN 지원 추가:

```python
    def _parse_comparison(self) -> Node:
        left = self._parse_additive()

        # BETWEEN: left BETWEEN low AND high → left >= low AND left <= high
        if self._at(TokenType.KW_BETWEEN):
            between_tok = self._advance()
            self._check_type(left, _NUMBER, "BETWEEN 피연산자는 숫자여야 합니다")
            low = self._parse_additive()
            self._check_type(low, _NUMBER, "BETWEEN 하한은 숫자여야 합니다")
            if not self._at(TokenType.AND):
                raise DSLSyntaxError(
                    "BETWEEN 뒤에 AND가 필요합니다", self._peek().line, self._peek().col,
                )
            self._advance()  # AND
            high = self._parse_additive()
            self._check_type(high, _NUMBER, "BETWEEN 상한은 숫자여야 합니다")

            ge_node = Comparison(op=">=", left=left, right=low,
                                 line=between_tok.line, col=between_tok.col)
            le_node = Comparison(op="<=", left=left, right=high,
                                 line=between_tok.line, col=between_tok.col)
            return BinOp(op="AND", left=ge_node, right=le_node,
                         line=between_tok.line, col=between_tok.col)

        if self._at(TokenType.GT, TokenType.GE, TokenType.LT, TokenType.LE,
                     TokenType.EQ, TokenType.NE):
            op_tok = self._advance()
            self._check_type(left, _NUMBER, "비교 연산자의 피연산자는 숫자여야 합니다")
            right = self._parse_additive()
            self._check_type(right, _NUMBER, "비교 연산자의 피연산자는 숫자여야 합니다")
            node = Comparison(op=op_tok.value, left=left, right=right,
                              line=op_tok.line, col=op_tok.col)
            if self._at(TokenType.GT, TokenType.GE, TokenType.LT, TokenType.LE,
                         TokenType.EQ, TokenType.NE):
                bad = self._peek()
                raise DSLSyntaxError(
                    "비교 연산을 연속으로 사용할 수 없습니다", bad.line, bad.col,
                )
            return node
        return left
```

`_parse_unary` 다음에 `_parse_postfix` 레벨 추가 (IndexAccess):

```python
    # 레벨 7: 단항 -
    def _parse_unary(self) -> Node:
        if self._at(TokenType.MINUS):
            op_tok = self._advance()
            operand = self._parse_unary()
            self._check_type(operand, _NUMBER, "단항 -의 피연산자는 숫자여야 합니다")
            return UnaryOp(op="-", operand=operand, line=op_tok.line, col=op_tok.col)
        return self._parse_postfix()

    # 레벨 7.5: 후위 IndexAccess — expr[N]
    def _parse_postfix(self) -> Node:
        node = self._parse_primary()
        if self._at(TokenType.LBRACKET):
            bracket_tok = self._advance()
            idx_tok = self._expect(TokenType.NUMBER)
            idx = int(float(idx_tok.value))
            if idx != float(idx_tok.value):
                raise DSLSyntaxError(
                    "인덱스는 정수만 허용됩니다", idx_tok.line, idx_tok.col,
                )
            if idx < 0 or idx > 60:
                raise DSLSyntaxError(
                    "인덱스 범위: 0~60", idx_tok.line, idx_tok.col,
                )
            self._expect(TokenType.RBRACKET)
            node = IndexAccess(expr=node, index=idx, line=bracket_tok.line, col=bracket_tok.col)
        return node
```

`_parse_ident` 수정 — 이름 해석 순서를 v2 spec에 맞게 변경:

```python
    def _parse_ident(self) -> Node:
        name_tok = self._advance()
        name = name_tok.value

        # 함수 호출: IDENT ( args )
        if self._at(TokenType.LPAREN):
            self._advance()  # (
            args: list[Node] = []
            if not self._at(TokenType.RPAREN):
                args.append(self._parse_expression())
                while self._at(TokenType.COMMA):
                    self._advance()
                    args.append(self._parse_expression())
            self._expect(TokenType.RPAREN)

            # 재귀 감지
            if name == self._current_func_name:
                raise DSLNameError(
                    f"'{name}'이 자기 자신을 참조합니다",
                    name_tok.line, name_tok.col,
                )

            # 커스텀 함수
            if name in self._custom_funcs:
                if args:
                    raise DSLSyntaxError(
                        f"'{name}'은 인자를 받지 않습니다",
                        name_tok.line, name_tok.col,
                    )
                return FuncCall(name=name, args=(), line=name_tok.line, col=name_tok.col)

            # 패턴 함수
            pat = get_pattern_func(name)
            if pat is not None:
                if args:
                    raise DSLSyntaxError(
                        f"'{name}'은 인자를 받지 않습니다",
                        name_tok.line, name_tok.col,
                    )
                return FuncCall(name=name, args=(), line=name_tok.line, col=name_tok.col)

            # 내장 함수
            spec = get_builtin_func(name)
            if spec is not None:
                if spec.param_max >= 0 and not (spec.param_min <= len(args) <= spec.param_max):
                    if spec.param_min == spec.param_max:
                        msg = f"'{name}'은 {spec.param_min}개 인자가 필요하지만 {len(args)}개가 전달되었습니다"
                    else:
                        msg = f"'{name}'은 {spec.param_min}~{spec.param_max}개 인자가 필요하지만 {len(args)}개가 전달되었습니다"
                    raise DSLSyntaxError(msg, name_tok.line, name_tok.col)
                return FuncCall(name=name, args=tuple(args), line=name_tok.line, col=name_tok.col)

            raise DSLNameError(
                f"'{name}'은 정의되지 않은 식별자입니다",
                name_tok.line, name_tok.col,
            )

        # 괄호 없는 식별자 참조
        if name == self._current_func_name:
            raise DSLNameError(
                f"'{name}'이 자기 자신을 참조합니다",
                name_tok.line, name_tok.col,
            )

        # v2 이름 해석 순서 (§2.5 rule 7):
        # 사용자 상수 → 커스텀 함수(괄호 없이 호출) → 내장 필드 → 패턴/내장 함수(괄호 없이 호출) → 에러

        # 1. 사용자 상수 — _consts에 등록된 이름
        if hasattr(self, '_v2_consts') and name in self._v2_consts:
            return FieldRef(name=name, line=name_tok.line, col=name_tok.col)

        # 2. 커스텀 함수 (괄호 선택)
        if name in self._custom_funcs:
            return FuncCall(name=name, args=(), line=name_tok.line, col=name_tok.col)

        # 3. 내장 필드
        if name in BUILTIN_FIELDS:
            return FieldRef(name=name, line=name_tok.line, col=name_tok.col)

        # 4. 패턴 함수 (괄호 선택 — §2.5 rule 5)
        if name in BUILTIN_PATTERNS:
            return FuncCall(name=name, args=(), line=name_tok.line, col=name_tok.col)

        # 5. 내장 함수 (괄호 선택 — 무인자 함수만)
        spec = get_builtin_func(name)
        if spec is not None:
            if spec.param_min == 0:
                return FuncCall(name=name, args=(), line=name_tok.line, col=name_tok.col)
            raise DSLSyntaxError(
                f"'{name}'은 {spec.param_min}개 이상 인자가 필요합니다. '{name}(...)' 형태로 호출하세요",
                name_tok.line, name_tok.col,
            )

        raise DSLNameError(
            f"'{name}'은 정의되지 않은 식별자입니다",
            name_tok.line, name_tok.col,
        )
```

`_v2_consts` set은 `parse_v2()` 진입 시 `_parse_const_or_func_def`에서 등록:

```python
    def parse_v2(self) -> ScriptV2:
        self._skip_newlines()
        self._v2_consts: set[str] = set()  # 상수 이름 추적
        # ... 나머지 기존 코드 ...
```

`_parse_const_or_func_def`에서 상수 등록 추가 (ConstDecl 반환 직전):

```python
        # 상수 반환 시:
        self._v2_consts.add(name)
        return ConstDecl(...)
```

최상위 `parse_v2` 함수 추가:

```python
def parse_v2(source: str) -> ScriptV2:
    """DSL 소스 → ScriptV2 AST. v2 문법 + v1 호환."""
    from .lexer import tokenize
    tokens = tokenize(source)
    parser = Parser(tokens)
    return parser.parse_v2()
```

**테스트: `sv_core/parsing/tests/test_parser_v2.py`에 추가**

```python
from sv_core.parsing.parser import parse_v2
from sv_core.parsing.ast_nodes import (
    Action, ConstDecl, CustomFuncDef, IndexAccess, Rule, ScriptV2,
    NumberLit, StringLit, FieldRef, FuncCall, Comparison, BinOp,
)
from sv_core.parsing.errors import DSLSyntaxError, DSLNameError


class TestV2Parser:
    def test_simple_rule(self):
        ast = parse_v2("RSI(14) < 30 → 매수 100%")
        assert isinstance(ast, ScriptV2)
        assert len(ast.rules) == 1
        rule = ast.rules[0]
        assert rule.action.side == "매수"
        assert rule.action.qty_type == "percent"
        assert rule.action.qty_value == 100.0

    def test_arrow_ascii(self):
        ast = parse_v2("RSI(14) < 30 -> 매수 100%")
        assert len(ast.rules) == 1

    def test_sell_all(self):
        ast = parse_v2("수익률 >= 5 → 매도 전량")
        assert ast.rules[0].action.side == "매도"
        assert ast.rules[0].action.qty_type == "all"

    def test_sell_rest(self):
        ast = parse_v2("고점 대비 <= -1.5 → 매도 나머지")
        assert ast.rules[0].action.qty_type == "all"  # 나머지 = 전량 별칭

    def test_sell_percent(self):
        ast = parse_v2("수익률 >= 3 → 매도 50%")
        assert ast.rules[0].action.qty_type == "percent"
        assert ast.rules[0].action.qty_value == 50.0

    def test_const_number(self):
        ast = parse_v2("기간 = 14\nRSI(기간) < 30 → 매수 100%")
        assert len(ast.consts) == 1
        assert ast.consts[0].name == "기간"
        assert isinstance(ast.consts[0].value, NumberLit)
        assert ast.consts[0].value.value == 14.0

    def test_const_string(self):
        ast = parse_v2('tf = "1d"\nRSI(14) < 30 → 매수 100%')
        assert len(ast.consts) == 1
        assert isinstance(ast.consts[0].value, StringLit)

    def test_custom_func_v2(self):
        """v2 커스텀 함수: 괄호 없는 정의, 괄호 없는 사용."""
        ast = parse_v2("내조건 = RSI(14) < 30\n내조건 → 매수 100%")
        assert len(ast.custom_funcs) == 1
        assert ast.custom_funcs[0].name == "내조건"
        rule_cond = ast.rules[0].condition
        assert isinstance(rule_cond, FuncCall)
        assert rule_cond.name == "내조건"

    def test_custom_func_v1_compat(self):
        """v1 커스텀 함수: 괄호 있는 정의."""
        ast = parse_v2("내조건() = RSI(14) < 30\n내조건() → 매수 100%")
        assert len(ast.custom_funcs) == 1

    def test_index_access(self):
        ast = parse_v2("현재가[1] > 현재가 → 매수 100%")
        cond = ast.rules[0].condition
        assert isinstance(cond, Comparison)
        assert isinstance(cond.left, IndexAccess)
        assert cond.left.index == 1

    def test_index_on_func_call(self):
        ast = parse_v2("RSI(14)[3] < 30 → 매수 100%")
        cond = ast.rules[0].condition
        assert isinstance(cond.left, IndexAccess)
        assert cond.left.index == 3
        assert isinstance(cond.left.expr, FuncCall)

    def test_index_max_60(self):
        parse_v2("현재가[60] > 0 → 매수 100%")  # 최대 OK

    def test_index_over_60_error(self):
        with pytest.raises(DSLSyntaxError, match="범위"):
            parse_v2("현재가[61] > 0 → 매수 100%")

    def test_between(self):
        ast = parse_v2("수익률 BETWEEN -1 AND 1 → 매도 전량")
        cond = ast.rules[0].condition
        assert isinstance(cond, BinOp)
        assert cond.op == "AND"

    def test_multiple_rules_order(self):
        src = """수익률 <= -2 → 매도 전량
수익률 >= 3 → 매도 50%
고점 대비 <= -1.5 → 매도 나머지
RSI(14) < 30 → 매수 100%"""
        ast = parse_v2(src)
        assert len(ast.rules) == 4
        assert ast.rules[0].action.side == "매도"
        assert ast.rules[3].action.side == "매수"

    def test_no_paren_pattern_func(self):
        """괄호 없는 패턴 함수: 골든크로스 → 매수."""
        ast = parse_v2("골든크로스 → 매수 100%")
        cond = ast.rules[0].condition
        assert isinstance(cond, FuncCall)
        assert cond.name == "골든크로스"

    def test_no_rules_error(self):
        with pytest.raises(DSLSyntaxError, match="규칙"):
            parse_v2("기간 = 14")

    def test_name_resolution_const_over_builtin(self):
        """사용자 상수가 내장 필드보다 우선 (§2.5 rule 7)."""
        ast = parse_v2("수익률 = 5\n수익률 >= 3 → 매도 전량")
        # "수익률"이 상수로 resolve되어 FieldRef (상수도 FieldRef로 표현)
        assert len(ast.consts) == 1

    def test_comment_ignored(self):
        src = """-- 주석
기간 = 14
RSI(기간) < 30 → 매수 100%"""
        ast = parse_v2(src)
        assert len(ast.rules) == 1


class TestV1Compat:
    def test_v1_buy_sell_blocks(self):
        """v1 매수:/매도: → v2 규칙 자동 변환."""
        ast = parse_v2("매수: RSI(14) < 30\n매도: 수익률 >= 5")
        assert isinstance(ast, ScriptV2)
        assert len(ast.rules) == 2
        # 매수 규칙: RSI(14) < 30 AND 보유수량 == 0 → 매수 100%
        buy_rule = ast.rules[0]
        assert buy_rule.action.side == "매수"
        assert isinstance(buy_rule.condition, BinOp)
        assert buy_rule.condition.op == "AND"
        # 매도 규칙: 수익률 >= 5 → 매도 전량
        sell_rule = ast.rules[1]
        assert sell_rule.action.side == "매도"
        assert sell_rule.action.qty_type == "all"
```

**테스트 실행:**

```bash
python -m pytest sv_core/parsing/tests/test_parser_v2.py::TestV2Parser sv_core/parsing/tests/test_parser_v2.py::TestV1Compat -v
# 기대: 20+ passed
```

**기존 테스트 회귀 확인:**

```bash
python -m pytest sv_core/parsing/tests/test_parser.py -v
# 기대: all passed (기존 v1 파서 변경 없음)
```

**git:**

```bash
git add sv_core/parsing/parser.py sv_core/parsing/tests/test_parser_v2.py
git commit -m "feat(dsl): v2 파서 — 규칙 구조, 상수, IndexAccess, BETWEEN, v1 호환 변환"
```

---

### Task 1.4 — v1 호환 통합 테스트

- [ ] 기존 v1 테스트 전체 통과 확인
- [ ] v1 스크립트가 parse_v2 경유 시 동일 의미 보장

**테스트: `sv_core/parsing/tests/test_parser_v2.py`에 추가**

```python
class TestV1FullCompat:
    """기존 v1 스크립트가 parse_v2로 올바르게 변환되는지 검증."""

    def test_v1_with_custom_func(self):
        src = "과매도() = RSI(14) <= 30\n매수: 과매도()\n매도: true"
        ast = parse_v2(src)
        assert len(ast.custom_funcs) == 1
        assert len(ast.rules) == 2

    def test_v1_complex_conditions(self):
        src = "매수: RSI(14) < 30 AND 현재가 > MA(20)\n매도: 수익률 >= 5 OR 수익률 <= -3"
        ast = parse_v2(src)
        assert len(ast.rules) == 2
        # 매수 규칙에 보유수량 == 0 추가됨
        buy_cond = ast.rules[0].condition
        assert isinstance(buy_cond, BinOp)

    def test_v1_evaluator_unchanged(self):
        """기존 v1 evaluate 함수가 정상 작동."""
        from sv_core.parsing import parse, evaluate
        ast = parse("매수: RSI(14) < 30\n매도: 수익률 >= 5")
        ctx = {
            "현재가": 50000, "거래량": 1000, "수익률": 0, "보유수량": 0,
            "RSI": lambda p: 25.0, "MA": lambda p: 50000,
        }
        buy, sell = evaluate(ast, ctx)
        assert buy is True
        assert sell is False
```

**테스트 실행:**

```bash
python -m pytest sv_core/parsing/tests/ -v
# 기대: v1 + v2 테스트 모두 통과
```

**git:**

```bash
git add sv_core/parsing/tests/test_parser_v2.py
git commit -m "test(dsl): v1 호환 통합 테스트 — parse_v2에서 v1 스크립트 변환 검증"
```

---

### Task 1.5 — builtins 확장 + ATR/최고가/최저가

- [ ] `sv_core/parsing/builtins.py` — 필드/함수 추가
- [ ] `sv_core/indicators/calculator.py` — ATR, 최고가, 최저가 함수 추가

**파일: `sv_core/parsing/builtins.py`**

BUILTIN_FIELDS 확장:

```python
BUILTIN_FIELDS: set[str] = {
    # 기존
    "현재가",
    "거래량",
    "수익률",
    "보유수량",
    # v2 포지션 필드
    "고점 대비",     # 보유 중 최고가 대비 하락률%
    "수익률고점",     # 보유 중 최고 수익률%
    "진입가",        # 평균 진입 단가
    "보유일",        # 영업일 수
    "보유봉",        # 봉 수
    # v2 시간 필드 (P1)
    "시간",          # 현재 시각 HHMM (정수)
    "장시작후",       # 장 시작 후 경과 분
    "요일",          # 1=월 ~ 5=금
    # v2 상태 필드
    "실행횟수",       # 이 규칙의 현재 포지션 내 실행 횟수
}
```

BUILTIN_FUNCTIONS 확장:

```python
BUILTIN_FUNCTIONS: dict[str, BuiltinFuncSpec] = {
    # 기존 유지 ...
    "RSI": BuiltinFuncSpec("RSI", 1, 2, "number"),
    "MA": BuiltinFuncSpec("MA", 1, 2, "number"),
    "EMA": BuiltinFuncSpec("EMA", 1, 2, "number"),
    "MACD": BuiltinFuncSpec("MACD", 0, 1, "number"),
    "MACD_SIGNAL": BuiltinFuncSpec("MACD_SIGNAL", 0, 1, "number"),
    "볼린저_상단": BuiltinFuncSpec("볼린저_상단", 1, 2, "number"),
    "볼린저_하단": BuiltinFuncSpec("볼린저_하단", 1, 2, "number"),
    "평균거래량": BuiltinFuncSpec("평균거래량", 1, 2, "number"),
    "상향돌파": BuiltinFuncSpec("상향돌파", 2, 2, "boolean"),
    "하향돌파": BuiltinFuncSpec("하향돌파", 2, 2, "boolean"),
    # v2 신규
    "ATR": BuiltinFuncSpec("ATR", 1, 2, "number"),
    "최고가": BuiltinFuncSpec("최고가", 1, 2, "number"),
    "최저가": BuiltinFuncSpec("최저가", 1, 2, "number"),
    "이격도": BuiltinFuncSpec("이격도", 1, 2, "number"),
    # 상태 함수 (P1) — 조건 인자를 받는 특수 함수
    "횟수": BuiltinFuncSpec("횟수", 2, 2, "number"),
    "연속": BuiltinFuncSpec("연속", 1, 1, "number"),
}
```

주의: `실행횟수`는 필드로 등록 (인자 없음). `횟수`와 `연속`은 함수로 등록 (인자 있음).

**파일: `sv_core/indicators/calculator.py`**

```python
def calc_atr(
    highs: pd.Series, lows: pd.Series, closes: pd.Series, period: int = 14,
) -> float | None:
    """ATR (Average True Range)."""
    if len(closes) < period + 1:
        return None
    prev_close = closes.shift(1)
    tr = pd.concat([
        highs - lows,
        (highs - prev_close).abs(),
        (lows - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    val = atr.iloc[-1]
    return round(float(val), 2) if not np.isnan(val) else None


def calc_highest(prices: pd.Series, period: int) -> float | None:
    """N봉 최고가."""
    if len(prices) < period:
        return None
    val = prices.iloc[-period:].max()
    return round(float(val), 2) if not np.isnan(val) else None


def calc_lowest(prices: pd.Series, period: int) -> float | None:
    """N봉 최저가."""
    if len(prices) < period:
        return None
    val = prices.iloc[-period:].min()
    return round(float(val), 2) if not np.isnan(val) else None
```

**테스트: `sv_core/parsing/tests/test_parser_v2.py`에 추가**

```python
class TestV2Builtins:
    def test_atr_in_rule(self):
        ast = parse_v2("현재가 <= 진입가 - ATR(14) * 2 → 매도 전량")
        assert len(ast.rules) == 1

    def test_highest_lowest(self):
        ast = parse_v2("현재가 >= 최고가(20) → 매도 전량")
        assert len(ast.rules) == 1

    def test_disparity(self):
        ast = parse_v2("이격도(20) < -5 → 매수 100%")
        assert len(ast.rules) == 1

    def test_position_fields(self):
        """포지션 필드 참조."""
        src = """고점 대비 <= -1.5 → 매도 전량
수익률고점 >= 3 → 매도 50%
보유일 >= 3 → 매도 전량
보유봉 >= 10 → 매도 전량
진입가 > 0 → 매도 전량"""
        ast = parse_v2(src)
        assert len(ast.rules) == 5

    def test_execution_count_field(self):
        """실행횟수 필드 (괄호 없음)."""
        ast = parse_v2("수익률 >= 3 AND 실행횟수 < 1 → 매도 50%")
        cond = ast.rules[0].condition
        assert isinstance(cond, BinOp)

    def test_count_func(self):
        """횟수(조건, 기간) — 상태 함수."""
        ast = parse_v2("횟수(수익률 >= 2, 보유봉) >= 1 → 매도 전량")
        assert len(ast.rules) == 1

    def test_consecutive_func(self):
        """연속(조건) — 상태 함수."""
        ast = parse_v2("연속(RSI(14) < 30) >= 3 → 매수 100%")
        assert len(ast.rules) == 1

    def test_time_fields(self):
        """시간 필드 (P1)."""
        ast = parse_v2("장시작후 >= 10 → 매수 100%")
        assert len(ast.rules) == 1


class TestIndicatorCalc:
    def test_calc_atr(self):
        from sv_core.indicators.calculator import calc_atr
        highs = pd.Series([102, 104, 103, 105, 106, 107, 108, 109, 110, 111,
                           112, 113, 114, 115, 116], dtype=float)
        lows = pd.Series([98, 100, 99, 101, 102, 103, 104, 105, 106, 107,
                          108, 109, 110, 111, 112], dtype=float)
        closes = pd.Series([100, 102, 101, 103, 104, 105, 106, 107, 108, 109,
                            110, 111, 112, 113, 114], dtype=float)
        result = calc_atr(highs, lows, closes, 14)
        assert result is not None
        assert isinstance(result, float)

    def test_calc_highest(self):
        from sv_core.indicators.calculator import calc_highest
        prices = pd.Series([100, 105, 102, 108, 103])
        assert calc_highest(prices, 5) == 108.0

    def test_calc_lowest(self):
        from sv_core.indicators.calculator import calc_lowest
        prices = pd.Series([100, 105, 102, 108, 103])
        assert calc_lowest(prices, 5) == 100.0
```

**테스트 실행:**

```bash
python -m pytest sv_core/parsing/tests/test_parser_v2.py::TestV2Builtins sv_core/parsing/tests/test_parser_v2.py::TestIndicatorCalc -v
# 기대: 12 passed
```

**git:**

```bash
git add sv_core/parsing/builtins.py sv_core/indicators/calculator.py sv_core/parsing/tests/test_parser_v2.py
git commit -m "feat(dsl): builtins 확장 — ATR/최고가/최저가/이격도, 포지션/시간/상태 필드, 횟수/연속 함수"
```

---

### Task 1.6 — v2 평가기

- [ ] `sv_core/parsing/evaluator.py` — evaluate_v2 함수
- [ ] `sv_core/parsing/__init__.py` — 공개 API 추가

**파일: `sv_core/parsing/evaluator.py`**

기존 `evaluate()` 함수와 `_Evaluator` 클래스는 유지. 새로운 함수와 클래스를 추가:

```python
# ── v2 평가 ──

@dataclass
class ActionResult:
    """규칙 평가 결과."""
    rule_index: int
    side: str           # "매수" | "매도"
    qty_type: str       # "percent" | "all"
    qty_value: float    # percent일 때 0~100
    expr_text: str      # 규칙 조건 원문 (디버그용)


@dataclass
class ConditionSnapshot:
    """조건 스냅샷 — 투명성 API용."""
    rule_index: int
    result: bool | None  # True/False/None(null)
    details: dict[str, Any]  # {"MA(20)": 73100, "수익률": 1.8, ...}


@dataclass
class EvalV2Result:
    """v2 평가 전체 결과."""
    action: ActionResult | None  # 실행할 행동 (없으면 None)
    snapshots: list[ConditionSnapshot]  # 모든 규칙 조건 스냅샷


def evaluate_v2(
    ast: ScriptV2,
    context: dict[str, Any],
    state: dict[str, Any] | None = None,
) -> EvalV2Result:
    """ScriptV2 평가 → 실행 행동 + 조건 스냅샷.

    §5.1 우선순위:
      1. 전량 매도 (True인 것 중 가장 위)
      2. 부분 매도 (전량 매도가 없을 때만)
      3. 매수 (매도가 하나도 없을 때만)
      한 사이클 최대 1개.
    """
    if state is None:
        state = {}
    if "cross_prev" not in state:
        state["cross_prev"] = {}

    ev = _EvaluatorV2(ast, context, state)
    return ev.run()


class _EvaluatorV2:
    def __init__(self, ast: ScriptV2, context: dict[str, Any], state: dict[str, Any]):
        self._ast = ast
        self._ctx = context
        self._state = state
        self._inner = _Evaluator(context, state)
        self._const_values: dict[str, Any] = {}
        self._snapshots: list[ConditionSnapshot] = []
        # 값 추적 (투명성)
        self._tracked_values: dict[str, Any] = {}

    def run(self) -> EvalV2Result:
        # 1. 상수 평가 → context에 주입
        for const in self._ast.consts:
            val = self._inner._eval(const.value)
            self._const_values[const.name] = val
            self._ctx[const.name] = val

        # 2. 커스텀 함수 평가
        for func_def in self._ast.custom_funcs:
            self._inner.eval_custom_def(func_def)

        # 3. 모든 규칙 평가 (실행 여부와 무관하게 전부)
        full_sell: ActionResult | None = None    # 전량 매도 중 가장 위
        partial_sell: ActionResult | None = None  # 부분 매도 중 가장 위
        buy: ActionResult | None = None           # 매수 중 가장 위

        for i, rule in enumerate(self._ast.rules):
            self._tracked_values = {}
            result = self._eval_with_tracking(rule.condition)

            is_true = result is not None and result is not _NULL and bool(result)

            self._snapshots.append(ConditionSnapshot(
                rule_index=i,
                result=is_true if result is not _NULL else None,
                details=dict(self._tracked_values),
            ))

            if not is_true:
                continue

            action = rule.action
            ar = ActionResult(
                rule_index=i,
                side=action.side,
                qty_type=action.qty_type,
                qty_value=action.qty_value,
                expr_text="",  # 원문은 호출 측에서 설정 가능
            )

            if action.side == "매도":
                if action.qty_type == "all":
                    if full_sell is None:
                        full_sell = ar
                else:
                    if partial_sell is None:
                        partial_sell = ar
            else:  # 매수
                if buy is None:
                    buy = ar

        # §5.1 우선순위 결정
        chosen: ActionResult | None = None
        if full_sell:
            chosen = full_sell
        elif partial_sell:
            chosen = partial_sell
        elif buy:
            chosen = buy

        return EvalV2Result(action=chosen, snapshots=self._snapshots)

    def _eval_with_tracking(self, node: Node) -> Any:
        """평가하면서 필드/함수 값 추적."""
        if isinstance(node, FieldRef):
            val = self._ctx.get(node.name)
            self._tracked_values[node.name] = val
            return val

        if isinstance(node, IndexAccess):
            # IndexAccess: context에서 히스토리 조회
            inner_val = self._eval_with_tracking(node.expr)
            key = self._index_key(node)
            history = self._ctx.get("__history__", {})
            if key in history:
                arr = history[key]
                if node.index < len(arr):
                    val = arr[node.index]
                    self._tracked_values[f"{key}[{node.index}]"] = val
                    return val
            return _NULL

        if isinstance(node, FuncCall):
            # 횟수/연속 상태 함수는 특수 처리
            if node.name == "횟수":
                return self._eval_count_func(node)
            if node.name == "연속":
                return self._eval_consecutive_func(node)

            val = self._inner._eval_func_call(node)
            # 함수 결과 추적
            func_repr = self._func_repr(node)
            self._tracked_values[func_repr] = val
            return val

        if isinstance(node, Comparison):
            left = self._eval_with_tracking(node.left)
            right = self._eval_with_tracking(node.right)
            if left is _NULL or right is _NULL:
                return _NULL
            op = node.op
            ops = {">": lambda: left > right, ">=": lambda: left >= right,
                   "<": lambda: left < right, "<=": lambda: left <= right,
                   "==": lambda: left == right, "!=": lambda: left != right}
            return ops.get(op, lambda: _NULL)()

        if isinstance(node, BinOp):
            left = self._eval_with_tracking(node.left)
            right = self._eval_with_tracking(node.right)
            if left is _NULL or right is _NULL:
                return _NULL
            op = node.op
            if op == "AND":
                return bool(left) and bool(right)
            if op == "OR":
                return bool(left) or bool(right)
            if op == "+":
                return left + right
            if op == "-":
                return left - right
            if op == "*":
                return left * right
            if op == "/":
                return left / right if right != 0 else _NULL
            return _NULL

        if isinstance(node, UnaryOp):
            val = self._eval_with_tracking(node.operand)
            if val is _NULL:
                return _NULL
            if node.op == "NOT":
                return not bool(val)
            if node.op == "-":
                return -val
            return _NULL

        return self._inner._eval(node)

    def _eval_count_func(self, node: FuncCall) -> Any:
        """횟수(조건, 기간) — 상태 함수.

        기간 내 조건이 True였던 봉 수를 반환.
        state["count_history"][key] = [bool, bool, ...] 링버퍼.
        """
        if len(node.args) != 2:
            return _NULL

        # 조건 평가 (현재 사이클)
        cond_result = self._eval_with_tracking(node.args[0])
        is_true = cond_result is not None and cond_result is not _NULL and bool(cond_result)

        # 기간 평가
        period_val = self._eval_with_tracking(node.args[1])
        if period_val is _NULL or period_val is None:
            return _NULL
        period = int(period_val)

        # 히스토리 key
        key = f"count:{repr(node.args[0])}"
        history = self._state.setdefault("count_history", {})
        buf = history.setdefault(key, [])
        buf.append(is_true)

        # 윈도우 내 True 수
        window = buf[-period:] if period > 0 else buf
        count = sum(1 for v in window if v)
        return count

    def _eval_consecutive_func(self, node: FuncCall) -> Any:
        """연속(조건) — 현재 연속 True 봉 수."""
        if len(node.args) != 1:
            return _NULL

        cond_result = self._eval_with_tracking(node.args[0])
        is_true = cond_result is not None and cond_result is not _NULL and bool(cond_result)

        key = f"consec:{repr(node.args[0])}"
        consec = self._state.setdefault("consecutive", {})

        if is_true:
            consec[key] = consec.get(key, 0) + 1
        else:
            consec[key] = 0

        return consec[key]

    def _index_key(self, node: IndexAccess) -> str:
        """IndexAccess의 히스토리 키 생성."""
        if isinstance(node.expr, FieldRef):
            return node.expr.name
        if isinstance(node.expr, FuncCall):
            return self._func_repr(node.expr)
        return repr(node.expr)

    def _func_repr(self, node: FuncCall) -> str:
        """함수 호출의 문자열 표현."""
        if not node.args:
            return node.name
        args_str = ", ".join(str(self._inner._eval(a)) for a in node.args)
        return f"{node.name}({args_str})"
```

`from dataclasses import dataclass` import 추가. `ScriptV2`, `Action`, `Rule`, `ConstDecl`, `IndexAccess` import 추가.

**파일: `sv_core/parsing/__init__.py`**

```python
"""sv_core.parsing — DSL 파서 공개 API."""

from .parser import parse, parse_v2
from .evaluator import evaluate, evaluate_v2, EvalV2Result, ActionResult, ConditionSnapshot
from .errors import DSLError, DSLSyntaxError, DSLTypeError, DSLNameError, DSLRuntimeError

__all__ = [
    "parse", "parse_v2",
    "evaluate", "evaluate_v2",
    "EvalV2Result", "ActionResult", "ConditionSnapshot",
    "DSLError", "DSLSyntaxError", "DSLTypeError", "DSLNameError", "DSLRuntimeError",
]
```

**테스트: `sv_core/parsing/tests/test_evaluator_v2.py`**

```python
"""v2 평가기 단위 테스트."""
import pytest

from sv_core.parsing import parse_v2, evaluate_v2
from sv_core.parsing.evaluator import ActionResult, ConditionSnapshot, EvalV2Result


def _ctx(**overrides):
    """기본 컨텍스트."""
    base = {
        "현재가": 50000,
        "거래량": 1000,
        "수익률": 0,
        "보유수량": 0,
        "고점 대비": 0,
        "수익률고점": 0,
        "진입가": 0,
        "보유일": 0,
        "보유봉": 0,
        "실행횟수": 0,
        "장시작후": 30,
        "시간": 930,
        "요일": 1,
        "RSI": lambda period, tf=None: 50,
        "MA": lambda period, tf=None: 50000,
        "EMA": lambda period, tf=None: 50000,
        "MACD": lambda tf=None: 0,
        "MACD_SIGNAL": lambda tf=None: 0,
        "볼린저_상단": lambda period, tf=None: 55000,
        "볼린저_하단": lambda period, tf=None: 45000,
        "평균거래량": lambda period, tf=None: 500,
        "ATR": lambda period, tf=None: 1000,
        "최고가": lambda period, tf=None: 52000,
        "최저가": lambda period, tf=None: 48000,
        "이격도": lambda period, tf=None: 0,
    }
    base.update(overrides)
    return base


class TestEvalV2Basic:
    def test_single_buy_rule(self):
        ast = parse_v2("RSI(14) < 30 → 매수 100%")
        result = evaluate_v2(ast, _ctx(RSI=lambda p, tf=None: 25))
        assert result.action is not None
        assert result.action.side == "매수"
        assert result.action.qty_value == 100.0

    def test_single_sell_rule(self):
        ast = parse_v2("수익률 >= 5 → 매도 전량")
        result = evaluate_v2(ast, _ctx(수익률=6))
        assert result.action is not None
        assert result.action.side == "매도"
        assert result.action.qty_type == "all"

    def test_no_match(self):
        ast = parse_v2("RSI(14) < 30 → 매수 100%")
        result = evaluate_v2(ast, _ctx(RSI=lambda p, tf=None: 60))
        assert result.action is None

    def test_snapshots_always_recorded(self):
        ast = parse_v2("RSI(14) < 30 → 매수 100%\n수익률 >= 5 → 매도 전량")
        result = evaluate_v2(ast, _ctx(RSI=lambda p, tf=None: 60, 수익률=2))
        assert len(result.snapshots) == 2
        assert result.snapshots[0].result is False
        assert result.snapshots[1].result is False


class TestEvalV2Priority:
    """§5.1 우선순위 테스트."""

    def test_full_sell_over_partial(self):
        """전량 매도 > 부분 매도."""
        src = """수익률 >= 3 → 매도 50%
수익률 <= -2 → 매도 전량"""
        ast = parse_v2(src)
        result = evaluate_v2(ast, _ctx(수익률=-3))
        assert result.action is not None
        assert result.action.qty_type == "all"

    def test_sell_over_buy(self):
        """매도 > 매수."""
        src = """RSI(14) < 30 → 매수 100%
수익률 >= 5 → 매도 전량"""
        ast = parse_v2(src)
        result = evaluate_v2(ast, _ctx(RSI=lambda p, tf=None: 25, 수익률=6))
        assert result.action.side == "매도"

    def test_top_rule_wins_same_type(self):
        """같은 유형 중 가장 위가 선택."""
        src = """수익률 <= -2 → 매도 전량
수익률 <= -5 → 매도 전량"""
        ast = parse_v2(src)
        result = evaluate_v2(ast, _ctx(수익률=-6))
        assert result.action.rule_index == 0

    def test_partial_sell_when_no_full(self):
        """전량 매도 없으면 부분 매도."""
        src = """수익률 >= 3 → 매도 50%
수익률 >= 5 → 매도 전량"""
        ast = parse_v2(src)
        result = evaluate_v2(ast, _ctx(수익률=4))
        assert result.action.qty_type == "percent"
        assert result.action.qty_value == 50.0

    def test_buy_only_when_no_sell(self):
        """매도 없을 때만 매수."""
        src = """수익률 <= -2 → 매도 전량
RSI(14) < 30 → 매수 100%"""
        ast = parse_v2(src)
        result = evaluate_v2(ast, _ctx(수익률=0, RSI=lambda p, tf=None: 25))
        assert result.action.side == "매수"


class TestEvalV2Constants:
    def test_const_substitution(self):
        """상수가 조건에서 올바르게 치환."""
        src = """기간 = 14
RSI(기간) < 30 → 매수 100%"""
        ast = parse_v2(src)
        result = evaluate_v2(ast, _ctx(RSI=lambda p, tf=None: 25))
        assert result.action is not None
        assert result.action.side == "매수"

    def test_const_in_comparison(self):
        src = """손절 = -2
수익률 <= 손절 → 매도 전량"""
        ast = parse_v2(src)
        result = evaluate_v2(ast, _ctx(수익률=-3))
        assert result.action is not None
        assert result.action.side == "매도"


class TestEvalV2CustomFunc:
    def test_custom_func_no_parens(self):
        src = """내조건 = RSI(14) < 30
내조건 → 매수 100%"""
        ast = parse_v2(src)
        result = evaluate_v2(ast, _ctx(RSI=lambda p, tf=None: 25))
        assert result.action is not None

    def test_custom_func_with_parens(self):
        src = """내조건() = RSI(14) < 30
내조건() → 매수 100%"""
        ast = parse_v2(src)
        result = evaluate_v2(ast, _ctx(RSI=lambda p, tf=None: 25))
        assert result.action is not None


class TestEvalV2Between:
    def test_between_true(self):
        src = "수익률 BETWEEN -1 AND 1 → 매도 전량"
        ast = parse_v2(src)
        result = evaluate_v2(ast, _ctx(수익률=0.5))
        assert result.action is not None

    def test_between_false_below(self):
        src = "수익률 BETWEEN -1 AND 1 → 매도 전량"
        ast = parse_v2(src)
        result = evaluate_v2(ast, _ctx(수익률=-2))
        assert result.action is None

    def test_between_false_above(self):
        src = "수익률 BETWEEN -1 AND 1 → 매도 전량"
        ast = parse_v2(src)
        result = evaluate_v2(ast, _ctx(수익률=2))
        assert result.action is None


class TestEvalV2StateFunctions:
    """상태 함수 테스트 (P1)."""

    def test_count_func(self):
        """횟수(조건, 기간) — 여러 사이클 시뮬레이션."""
        src = "횟수(수익률 >= 2, 보유봉) >= 1 → 매도 전량"
        ast = parse_v2(src)
        state = {}

        # 사이클 1: 수익률 = 1 (조건 False)
        r1 = evaluate_v2(ast, _ctx(수익률=1, 보유봉=1), state)
        assert r1.action is None

        # 사이클 2: 수익률 = 3 (조건 True, 보유봉=2이므로 윈도우 [False, True] → count=1)
        r2 = evaluate_v2(ast, _ctx(수익률=3, 보유봉=2), state)
        assert r2.action is not None  # 횟수 >= 1 달성

    def test_consecutive_func(self):
        """연속(조건) — 연속 True 봉 수."""
        src = "연속(RSI(14) < 30) >= 3 → 매수 100%"
        ast = parse_v2(src)
        state = {}

        # 3연속 RSI < 30
        for i in range(2):
            r = evaluate_v2(ast, _ctx(RSI=lambda p, tf=None: 25), state)
            assert r.action is None  # 아직 3 미만

        r = evaluate_v2(ast, _ctx(RSI=lambda p, tf=None: 25), state)
        assert r.action is not None  # 3연속 달성

    def test_consecutive_reset(self):
        """연속 — 중간에 끊기면 리셋."""
        src = "연속(RSI(14) < 30) >= 2 → 매수 100%"
        ast = parse_v2(src)
        state = {}

        evaluate_v2(ast, _ctx(RSI=lambda p, tf=None: 25), state)  # 1
        evaluate_v2(ast, _ctx(RSI=lambda p, tf=None: 50), state)  # 리셋
        r = evaluate_v2(ast, _ctx(RSI=lambda p, tf=None: 25), state)  # 1
        assert r.action is None  # 아직 1


class TestEvalV2Snapshots:
    """투명성 — 조건 스냅샷 테스트."""

    def test_snapshot_details(self):
        src = "RSI(14) < 30 AND MA(20) > MA(60) → 매수 100%"
        ast = parse_v2(src)
        ctx = _ctx(
            RSI=lambda p, tf=None: 35,
            MA=lambda p, tf=None: 73100 if p == 20 else 71800,
        )
        result = evaluate_v2(ast, ctx)
        snap = result.snapshots[0]
        assert snap.result is False
        # details에 RSI, MA 값이 기록됨
        assert "RSI" in str(snap.details) or len(snap.details) > 0

    def test_all_rules_have_snapshots(self):
        src = """수익률 <= -2 → 매도 전량
수익률 >= 5 → 매도 전량
RSI(14) < 30 → 매수 100%"""
        ast = parse_v2(src)
        result = evaluate_v2(ast, _ctx(수익률=0, RSI=lambda p, tf=None: 50))
        assert len(result.snapshots) == 3
```

**테스트 실행:**

```bash
python -m pytest sv_core/parsing/tests/test_evaluator_v2.py -v
# 기대: 20+ passed
```

**기존 평가기 회귀:**

```bash
python -m pytest sv_core/parsing/tests/test_evaluator.py -v
# 기대: all passed
```

**git:**

```bash
git add sv_core/parsing/evaluator.py sv_core/parsing/__init__.py sv_core/parsing/tests/test_evaluator_v2.py
git commit -m "feat(dsl): v2 평가기 — 규칙 우선순위, 상태 함수, 조건 스냅샷, 상수 치환"
```

---

## Phase 2: 엔진 (local_server)

### Task 2.1 — PositionState

- [ ] `local_server/engine/position_state.py` — 포지션 상태 관리 클래스

**파일: `local_server/engine/position_state.py`**

```python
"""PositionState — 종목별 포지션 상태 추적.

spec §3.3: entry_price, highest_price, pnl_high, bars_held, days_held, func_state.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


@dataclass
class PositionState:
    """종목 포지션 상태."""
    symbol: str
    entry_price: float = 0.0           # DCA 가중평균 진입가
    entry_time: datetime | None = None  # 최초 진입 시각
    highest_price: float = 0.0          # 보유 중 최고가
    pnl_high: float = 0.0              # 보유 중 최고 수익률%
    bars_held: int = 0                  # 보유 봉 수
    days_held: int = 0                  # 영업일 수
    total_cost: float = 0.0            # 총 매입금액 (DCA 계산용)
    total_qty: int = 0                  # 총 보유수량
    remaining_ratio: float = 1.0        # 잔여 비율 (다단계 청산용)
    last_trade_date: date | None = None # 마지막 거래일 (days_held 계산용)
    # 규칙별 실행횟수: {rule_index: count}
    execution_counts: dict[int, int] = field(default_factory=dict)
    # 상태 함수 내부 state (횟수, 연속 등)
    func_state: dict[str, Any] = field(default_factory=dict)

    @property
    def is_holding(self) -> bool:
        return self.total_qty > 0

    def record_buy(self, price: float, qty: int, at: datetime | None = None) -> None:
        """매수 기록 — DCA 진입가 갱신."""
        if not self.is_holding:
            # 새 포지션
            self.entry_time = at or datetime.now()
            self.bars_held = 1
            self.days_held = 1
            self.last_trade_date = (at or datetime.now()).date()

        self.total_cost += price * qty
        self.total_qty += qty
        self.entry_price = self.total_cost / self.total_qty
        self.highest_price = max(self.highest_price, price)

    def record_sell(self, qty: int) -> None:
        """매도 기록 — 수량 차감. 전량 매도 시 리셋."""
        self.total_qty = max(0, self.total_qty - qty)
        if self.total_qty == 0:
            self.reset()

    def reset(self) -> None:
        """포지션 전량 청산 — 전체 리셋."""
        self.entry_price = 0.0
        self.entry_time = None
        self.highest_price = 0.0
        self.pnl_high = 0.0
        self.bars_held = 0
        self.days_held = 0
        self.total_cost = 0.0
        self.total_qty = 0
        self.remaining_ratio = 1.0
        self.last_trade_date = None
        self.execution_counts.clear()
        self.func_state.clear()

    def update_cycle(self, current_price: float) -> None:
        """매 사이클 갱신 — 최고가, 보유봉, pnl_high."""
        if not self.is_holding:
            return
        self.bars_held += 1
        self.highest_price = max(self.highest_price, current_price)
        if self.entry_price > 0:
            pnl = (current_price - self.entry_price) / self.entry_price * 100
            self.pnl_high = max(self.pnl_high, pnl)

    def update_day(self, today: date) -> None:
        """영업일 경계 시 days_held 증가."""
        if not self.is_holding:
            return
        if self.last_trade_date and today > self.last_trade_date:
            self.days_held += 1
            self.last_trade_date = today

    def record_execution(self, rule_index: int) -> None:
        """규칙 실행 횟수 증가."""
        self.execution_counts[rule_index] = self.execution_counts.get(rule_index, 0) + 1

    def get_pnl_pct(self, current_price: float) -> float:
        """현재 수익률%."""
        if self.entry_price <= 0:
            return 0.0
        return (current_price - self.entry_price) / self.entry_price * 100

    def get_drawdown_pct(self, current_price: float) -> float:
        """고점 대비 하락률%."""
        if self.highest_price <= 0:
            return 0.0
        return (current_price - self.highest_price) / self.highest_price * 100

    def to_context(self, current_price: float) -> dict[str, Any]:
        """DSL evaluator context로 변환."""
        return {
            "수익률": self.get_pnl_pct(current_price),
            "보유수량": self.total_qty,
            "고점 대비": self.get_drawdown_pct(current_price),
            "수익률고점": self.pnl_high,
            "진입가": self.entry_price,
            "보유일": self.days_held,
            "보유봉": self.bars_held,
        }
```

**테스트: `local_server/engine/tests/test_position_state.py`**

```python
"""PositionState 단위 테스트."""
import pytest
from datetime import datetime, date

from local_server.engine.position_state import PositionState


class TestPositionStateBasic:
    def test_initial_state(self):
        ps = PositionState(symbol="005930")
        assert not ps.is_holding
        assert ps.entry_price == 0.0
        assert ps.bars_held == 0

    def test_buy_creates_position(self):
        ps = PositionState(symbol="005930")
        ps.record_buy(72000, 50, at=datetime(2026, 3, 29, 9, 30))
        assert ps.is_holding
        assert ps.entry_price == 72000
        assert ps.total_qty == 50
        assert ps.bars_held == 1
        assert ps.days_held == 1

    def test_dca_weighted_avg(self):
        """DCA 진입가 = 가중평균."""
        ps = PositionState(symbol="005930")
        ps.record_buy(72000, 50)
        ps.record_buy(70000, 30)
        expected = (72000 * 50 + 70000 * 30) / 80
        assert abs(ps.entry_price - expected) < 0.01
        assert ps.total_qty == 80

    def test_sell_partial(self):
        ps = PositionState(symbol="005930")
        ps.record_buy(72000, 100)
        ps.record_sell(50)
        assert ps.is_holding
        assert ps.total_qty == 50
        # 부분 매도 시 상태 유지
        assert ps.entry_price == 72000

    def test_sell_all_resets(self):
        """전량 매도 → 전체 리셋."""
        ps = PositionState(symbol="005930")
        ps.record_buy(72000, 100)
        ps.record_execution(0)
        ps.record_sell(100)
        assert not ps.is_holding
        assert ps.entry_price == 0.0
        assert ps.execution_counts == {}

    def test_update_cycle(self):
        ps = PositionState(symbol="005930")
        ps.record_buy(72000, 50)
        ps.update_cycle(73000)
        assert ps.highest_price == 73000
        assert ps.bars_held == 2  # 진입=1, update=+1

    def test_pnl_high_tracking(self):
        ps = PositionState(symbol="005930")
        ps.record_buy(72000, 50)
        ps.update_cycle(75000)  # pnl = 4.17%
        ps.update_cycle(73000)  # pnl = 1.39%
        assert ps.pnl_high > 4.0  # 최고점 유지

    def test_to_context(self):
        ps = PositionState(symbol="005930")
        ps.record_buy(72000, 50)
        ps.update_cycle(73000)
        ctx = ps.to_context(73000)
        assert ctx["보유수량"] == 50
        assert ctx["진입가"] == 72000
        assert abs(ctx["수익률"] - 1.3889) < 0.01
        assert ctx["보유봉"] == 2

    def test_reentry_after_full_sell(self):
        """재진입 시 상태 완전 리셋."""
        ps = PositionState(symbol="005930")
        ps.record_buy(72000, 50)
        ps.record_execution(0)
        ps.record_sell(50)  # 전량 청산
        ps.record_buy(70000, 30)  # 재진입
        assert ps.entry_price == 70000
        assert ps.total_qty == 30
        assert ps.bars_held == 1
        assert ps.execution_counts == {}

    def test_execution_count(self):
        ps = PositionState(symbol="005930")
        ps.record_buy(72000, 50)
        ps.record_execution(0)
        ps.record_execution(0)
        ps.record_execution(1)
        assert ps.execution_counts[0] == 2
        assert ps.execution_counts[1] == 1
```

**테스트 실행:**

```bash
python -m pytest local_server/engine/tests/test_position_state.py -v
# 기대: 11 passed
```

**git:**

```bash
git add local_server/engine/position_state.py local_server/engine/tests/test_position_state.py
git commit -m "feat(engine): PositionState — DCA 가중평균, 사이클 갱신, 전량 청산 리셋"
```

---

### Task 2.2 — 지표 히스토리 링버퍼

- [ ] `local_server/engine/indicator_provider.py` — 히스토리 링버퍼 추가

**파일: `local_server/engine/indicator_provider.py`**

`IndicatorProvider` 클래스에 추가:

```python
from collections import deque

_HISTORY_MAX = 60  # 최대 60봉 히스토리

class IndicatorProvider:
    def __init__(self) -> None:
        self._daily_cache: dict[str, dict] = {}
        self._minute_cache: dict[str, dict[str, dict]] = {}
        # 지표 히스토리: {symbol: {tf: {key: deque}}}
        self._history: dict[str, dict[str, dict[str, deque]]] = {}

    def record_history(self, symbol: str, tf: str, indicators: dict[str, Any]) -> None:
        """현재 사이클 지표를 히스토리에 기록."""
        sym_hist = self._history.setdefault(symbol, {})
        tf_hist = sym_hist.setdefault(tf, {})
        for key, val in indicators.items():
            if key not in tf_hist:
                tf_hist[key] = deque(maxlen=_HISTORY_MAX)
            tf_hist[key].appendleft(val)  # [0]=현재, [1]=1봉전, ...

    def get_history(self, symbol: str, tf: str, key: str, index: int) -> Any:
        """히스토리 조회. 없으면 None."""
        try:
            return self._history[symbol][tf][key][index]
        except (KeyError, IndexError):
            return None

    def get_history_dict(self, symbol: str, tf: str) -> dict[str, list]:
        """종목/TF별 전체 히스토리 dict 반환 (evaluator에 전달용)."""
        result: dict[str, list] = {}
        try:
            tf_hist = self._history[symbol][tf]
            for key, buf in tf_hist.items():
                result[key] = list(buf)
        except KeyError:
            pass
        return result
```

ATR, 최고가, 최저가 계산을 `calc_all_indicators`에 추가:

**파일: `sv_core/indicators/calculator.py`**

`calc_all_indicators` 수정 — 고가/저가 Series도 받도록:

```python
def calc_all_indicators(
    closes: pd.Series,
    volumes: pd.Series,
    highs: pd.Series | None = None,
    lows: pd.Series | None = None,
) -> dict:
    """evaluator가 기대하는 전체 indicators dict."""
    macd, macd_signal = calc_macd(closes)
    bb_upper_20, bb_lower_20 = calc_bollinger(closes, 20)

    result = {
        # 기존 유지 ...
        "rsi_14": calc_rsi(closes, 14),
        "rsi_21": calc_rsi(closes, 21),
        "ma_5": calc_sma(closes, 5),
        "ma_10": calc_sma(closes, 10),
        "ma_20": calc_sma(closes, 20),
        "ma_60": calc_sma(closes, 60),
        "ema_12": calc_ema(closes, 12),
        "ema_20": calc_ema(closes, 20),
        "ema_26": calc_ema(closes, 26),
        "macd": macd,
        "macd_signal": macd_signal,
        "bb_upper_20": bb_upper_20,
        "bb_lower_20": bb_lower_20,
        "avg_volume_20": calc_avg_volume(volumes, 20),
    }

    # v2: ATR, 최고가, 최저가 (highs/lows 있을 때만)
    if highs is not None and lows is not None:
        result["atr_14"] = calc_atr(highs, lows, closes, 14)
        result["highest_20"] = calc_highest(closes, 20)
        result["lowest_20"] = calc_lowest(closes, 20)

    return result
```

**테스트:**

```python
# local_server/engine/tests/test_position_state.py에 추가 (또는 별도 파일)

class TestIndicatorHistory:
    def test_record_and_get(self):
        from local_server.engine.indicator_provider import IndicatorProvider
        prov = IndicatorProvider()
        prov.record_history("005930", "1d", {"rsi_14": 50.0, "ma_20": 72000})
        prov.record_history("005930", "1d", {"rsi_14": 48.0, "ma_20": 71500})
        # [0] = 최신 (48), [1] = 이전 (50)
        assert prov.get_history("005930", "1d", "rsi_14", 0) == 48.0
        assert prov.get_history("005930", "1d", "rsi_14", 1) == 50.0

    def test_get_missing(self):
        from local_server.engine.indicator_provider import IndicatorProvider
        prov = IndicatorProvider()
        assert prov.get_history("005930", "1d", "rsi_14", 0) is None

    def test_max_60(self):
        from local_server.engine.indicator_provider import IndicatorProvider
        prov = IndicatorProvider()
        for i in range(70):
            prov.record_history("005930", "1d", {"rsi_14": float(i)})
        # 60개만 유지, [0]=69(최신), [59]=10
        assert prov.get_history("005930", "1d", "rsi_14", 0) == 69.0
        assert prov.get_history("005930", "1d", "rsi_14", 59) == 10.0
        assert prov.get_history("005930", "1d", "rsi_14", 60) is None
```

**테스트 실행:**

```bash
python -m pytest local_server/engine/tests/test_position_state.py::TestIndicatorHistory -v
# 기대: 3 passed
```

**git:**

```bash
git add local_server/engine/indicator_provider.py sv_core/indicators/calculator.py local_server/engine/tests/test_position_state.py
git commit -m "feat(engine): 지표 히스토리 링버퍼 (최대 60봉) + ATR/최고가/최저가 계산"
```

---

### Task 2.3 — ConditionTracker (조건 상태 추적기)

- [ ] `local_server/engine/condition_tracker.py` — 조건 상태 인메모리 저장소

**파일: `local_server/engine/condition_tracker.py`**

```python
"""ConditionTracker — 조건 상태 인메모리 저장소.

매 사이클 모든 규칙의 조건 평가 결과를 저장하고,
트리거 이력을 기록한다. API에서 조회.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class RuleConditionStatus:
    """규칙별 조건 상태."""
    rule_index: int
    expr_text: str
    result: bool | None
    details: dict[str, Any]


@dataclass
class TriggerRecord:
    """트리거 이력 레코드."""
    at: str  # ISO 형식
    rule_index: int
    action_text: str  # "매수 100%", "매도 전량" 등


@dataclass
class RuleStatusSnapshot:
    """규칙 전체 상태 스냅샷."""
    rule_id: int
    cycle: str  # ISO 형식
    position: dict[str, Any]
    conditions: list[RuleConditionStatus]
    action: dict[str, Any] | None
    triggered_history: list[TriggerRecord]


_MAX_TRIGGERS = 50  # 트리거 이력 최대 개수


class ConditionTracker:
    """조건 상태 추적기 — 규칙별 상태 관리."""

    def __init__(self) -> None:
        # {rule_id: RuleStatusSnapshot}
        self._snapshots: dict[int, RuleStatusSnapshot] = {}
        # {rule_id: deque[TriggerRecord]}
        self._triggers: dict[int, deque[TriggerRecord]] = {}

    def update(
        self,
        rule_id: int,
        conditions: list[RuleConditionStatus],
        position: dict[str, Any],
        action: dict[str, Any] | None = None,
    ) -> None:
        """사이클 결과 업데이트."""
        trigger_history = list(self._triggers.get(rule_id, []))
        self._snapshots[rule_id] = RuleStatusSnapshot(
            rule_id=rule_id,
            cycle=datetime.now().isoformat(),
            position=position,
            conditions=conditions,
            action=action,
            triggered_history=trigger_history,
        )

    def record_trigger(self, rule_id: int, rule_index: int, action_text: str) -> None:
        """트리거 발생 기록."""
        if rule_id not in self._triggers:
            self._triggers[rule_id] = deque(maxlen=_MAX_TRIGGERS)
        self._triggers[rule_id].appendleft(TriggerRecord(
            at=datetime.now().isoformat(),
            rule_index=rule_index,
            action_text=action_text,
        ))

    def get(self, rule_id: int) -> RuleStatusSnapshot | None:
        """규칙 상태 조회."""
        return self._snapshots.get(rule_id)

    def get_all(self) -> dict[int, RuleStatusSnapshot]:
        """전체 상태 조회."""
        return dict(self._snapshots)

    def clear(self, rule_id: int | None = None) -> None:
        """상태 초기화."""
        if rule_id is not None:
            self._snapshots.pop(rule_id, None)
            self._triggers.pop(rule_id, None)
        else:
            self._snapshots.clear()
            self._triggers.clear()
```

**테스트: `local_server/engine/tests/test_condition_tracker.py`**

```python
"""ConditionTracker 단위 테스트."""
import pytest

from local_server.engine.condition_tracker import (
    ConditionTracker, RuleConditionStatus, TriggerRecord,
)


class TestConditionTracker:
    def test_update_and_get(self):
        tracker = ConditionTracker()
        conditions = [
            RuleConditionStatus(rule_index=0, expr_text="RSI(14) < 30", result=True, details={"RSI(14)": 25}),
            RuleConditionStatus(rule_index=1, expr_text="수익률 >= 5", result=False, details={"수익률": 2.0}),
        ]
        tracker.update(rule_id=1, conditions=conditions, position={"status": "보유중"})
        snap = tracker.get(1)
        assert snap is not None
        assert snap.rule_id == 1
        assert len(snap.conditions) == 2
        assert snap.conditions[0].result is True

    def test_record_trigger(self):
        tracker = ConditionTracker()
        tracker.record_trigger(rule_id=1, rule_index=0, action_text="매수 100%")
        tracker.record_trigger(rule_id=1, rule_index=1, action_text="매도 전량")
        tracker.update(rule_id=1, conditions=[], position={})
        snap = tracker.get(1)
        assert len(snap.triggered_history) == 2
        assert snap.triggered_history[0].action_text == "매도 전량"  # 최신 먼저

    def test_trigger_max_limit(self):
        tracker = ConditionTracker()
        for i in range(60):
            tracker.record_trigger(rule_id=1, rule_index=0, action_text=f"action_{i}")
        tracker.update(rule_id=1, conditions=[], position={})
        snap = tracker.get(1)
        assert len(snap.triggered_history) == 50  # 최대 50개

    def test_get_all(self):
        tracker = ConditionTracker()
        tracker.update(rule_id=1, conditions=[], position={})
        tracker.update(rule_id=2, conditions=[], position={})
        all_snaps = tracker.get_all()
        assert len(all_snaps) == 2

    def test_clear_single(self):
        tracker = ConditionTracker()
        tracker.update(rule_id=1, conditions=[], position={})
        tracker.update(rule_id=2, conditions=[], position={})
        tracker.clear(rule_id=1)
        assert tracker.get(1) is None
        assert tracker.get(2) is not None

    def test_clear_all(self):
        tracker = ConditionTracker()
        tracker.update(rule_id=1, conditions=[], position={})
        tracker.clear()
        assert len(tracker.get_all()) == 0
```

**테스트 실행:**

```bash
python -m pytest local_server/engine/tests/test_condition_tracker.py -v
# 기대: 6 passed
```

**git:**

```bash
git add local_server/engine/condition_tracker.py local_server/engine/tests/test_condition_tracker.py
git commit -m "feat(engine): ConditionTracker — 조건 상태 인메모리 저장 + 트리거 이력"
```

---

### Task 2.4 — 엔진 통합 (v2 평가 모델)

- [ ] `local_server/engine/evaluator.py` — v2 평가 경로
- [ ] `local_server/engine/engine.py` — PositionState + ConditionTracker 통합
- [ ] `local_server/engine/executor.py` — 부분 매도 비율 계산

**파일: `local_server/engine/evaluator.py`**

기존 `_eval_dsl` 메서드 유지. v2 평가 메서드 추가:

```python
from sv_core.parsing import parse_v2, evaluate_v2
from sv_core.parsing.evaluator import EvalV2Result
from sv_core.parsing.ast_nodes import ScriptV2

class RuleEvaluator:
    # 기존 코드 유지...

    def evaluate_v2(
        self,
        rule: dict,
        market_data: dict,
        context: dict,
        position_context: dict[str, Any] | None = None,
        func_state: dict[str, Any] | None = None,
    ) -> EvalV2Result | None:
        """v2 규칙 평가 → EvalV2Result.

        script에 → 또는 -> 가 포함되면 v2 경로.
        아니면 기존 v1 경로 (evaluate 메서드).
        """
        script = rule.get("script")
        if script is None:
            return None

        rule_id = rule.get("id", 0)

        try:
            ast = self._get_or_parse_v2(rule_id, script)
            if ast is None:
                return None  # v1 스크립트

            eval_ctx = self._build_dsl_context(market_data, context)
            # 포지션 컨텍스트 주입
            if position_context:
                eval_ctx.update(position_context)
            # 히스토리 주입
            history = market_data.get("__history__")
            if history:
                eval_ctx["__history__"] = history

            state = func_state if func_state is not None else self._cross_states.setdefault(rule_id, {})
            return evaluate_v2(ast, eval_ctx, state)
        except Exception:
            logger.exception("Rule %d v2 평가 오류", rule_id)
            return None

    def _get_or_parse_v2(self, rule_id: int, script: str) -> ScriptV2 | None:
        """v2 AST 캐시 조회. v1 스크립트면 None."""
        # v2 판별: → 또는 -> 포함
        if "\u2192" not in script and "->" not in script:
            # v1 매수:/매도: 패턴도 v2로 변환 가능
            if "매수:" in script or "매도:" in script:
                pass  # v1 호환 변환 시도
            else:
                return None

        script_hash = hashlib.md5(script.encode()).hexdigest()
        cache_key = f"v2_{rule_id}"
        cached = self._ast_cache.get(cache_key)
        if cached and cached[0] == script_hash:
            return cached[1]

        ast = parse_v2(script)
        self._ast_cache[cache_key] = (script_hash, ast)
        return ast

    def is_v2_script(self, script: str) -> bool:
        """스크립트가 v2 형식인지 판별."""
        return "\u2192" in script or "->" in script or "매수:" in script or "매도:" in script
```

**파일: `local_server/engine/engine.py`**

`StrategyEngine.__init__`에 추가:

```python
from local_server.engine.position_state import PositionState
from local_server.engine.condition_tracker import ConditionTracker, RuleConditionStatus

class StrategyEngine:
    def __init__(self, broker, config=None):
        # 기존 코드 유지...

        # v2 포지션 상태: {symbol: PositionState}
        self._position_states: dict[str, PositionState] = {}
        # v2 조건 추적기
        self._condition_tracker = ConditionTracker()

    @property
    def condition_tracker(self) -> ConditionTracker:
        return self._condition_tracker
```

`_collect_candidates` 메서드를 확장하여 v2 경로 추가:

```python
    def _collect_candidates(self, rule, cycle_id):
        rule_id = rule.get("id", 0)
        symbol = rule.get("symbol", "")
        results = []

        try:
            latest = self._bar_builder.get_latest(symbol)
            if not latest:
                return results

            # 지표 주입 (기존)
            indicators_by_tf = {}
            daily_ind = self._indicator_provider.get(symbol, "1d")
            indicators_by_tf["1d"] = daily_ind
            for tf in _extract_rule_tfs(rule):
                minute_ind = self._indicator_provider.get(symbol, tf)
                if minute_ind is not None:
                    indicators_by_tf[tf] = minute_ind
            latest["indicators"] = indicators_by_tf

            # 히스토리 주입 (v2)
            history = self._indicator_provider.get_history_dict(symbol, "1d")
            latest["__history__"] = history

            context = self._context_cache.get()
            price = float(latest.get("price", 0))

            # PositionState 조회/생성
            ps = self._position_states.setdefault(symbol, PositionState(symbol=symbol))
            position_ctx = ps.to_context(price)

            # 실행횟수 (전 규칙 합산이 아닌 개별 규칙)
            # evaluate_v2에서 규칙 인덱스별로 조회하므로 여기서는 context에 넣지 않음

            # v2 평가 시도
            v2_result = self._evaluator.evaluate_v2(
                rule, latest, context,
                position_context=position_ctx,
                func_state=ps.func_state,
            )

            if v2_result is not None:
                # v2 경로: 조건 스냅샷 기록
                conditions = [
                    RuleConditionStatus(
                        rule_index=s.rule_index,
                        expr_text="",  # 원문은 별도 추출 필요
                        result=s.result,
                        details=s.details,
                    )
                    for s in v2_result.snapshots
                ]
                pos_info = {
                    "status": "보유중" if ps.is_holding else "미보유",
                    "entry_price": ps.entry_price,
                    "highest_price": ps.highest_price,
                    "pnl_pct": ps.get_pnl_pct(price),
                    "bars_held": ps.bars_held,
                    "days_held": ps.days_held,
                    "remaining_ratio": ps.remaining_ratio,
                }
                action_info = None
                if v2_result.action:
                    a = v2_result.action
                    action_info = {"side": a.side, "qty_type": a.qty_type, "qty_value": a.qty_value}
                self._condition_tracker.update(rule_id, conditions, pos_info, action_info)

                if v2_result.action:
                    a = v2_result.action
                    side = "BUY" if a.side == "매수" else "SELL"

                    # 수량 계산
                    execution = rule.get("execution") or {}
                    if a.qty_type == "percent":
                        if side == "BUY":
                            # 매수 N% = 일일 예산의 N%
                            base_qty = int(execution.get("qty_value", rule.get("qty", 1)))
                            qty = max(1, int(base_qty * a.qty_value / 100))
                        else:
                            # 매도 N% = 보유수량의 N%
                            qty = max(1, int(ps.total_qty * a.qty_value / 100))
                    else:
                        # 전량
                        if side == "BUY":
                            qty = int(execution.get("qty_value", rule.get("qty", 1)))
                        else:
                            qty = ps.total_qty

                    if qty <= 0:
                        return results

                    signal = CandidateSignal(
                        signal_id=uuid.uuid4().hex[:12],
                        cycle_id=cycle_id,
                        rule_id=rule_id,
                        symbol=symbol,
                        side=side,
                        priority=rule.get("priority", 0),
                        desired_qty=qty,
                        detected_at=datetime.now(),
                        latest_price=price,
                        reason=f"v2 규칙 {a.rule_index} 충족",
                        raw_rule=rule,
                        intent_id=uuid.uuid4().hex[:12],
                    )
                    results.append((signal, latest))

                    # 트리거 기록
                    qty_text = f"{a.qty_value}%" if a.qty_type == "percent" else "전량"
                    self._condition_tracker.record_trigger(
                        rule_id, a.rule_index, f"{a.side} {qty_text}"
                    )

                return results

            # v1 폴백 (기존 코드 유지)
            buy_result, sell_result = self._evaluator.evaluate(rule, latest, context)
            # ... 기존 CandidateSignal 생성 로직 ...

        except Exception:
            logger.exception("Rule %d 후보 수집 오류", rule_id)

        return results
```

**테스트: `local_server/engine/tests/test_engine_v2.py`**

```python
"""v2 엔진 통합 테스트."""
import pytest

from sv_core.parsing import parse_v2, evaluate_v2
from sv_core.parsing.evaluator import EvalV2Result
from local_server.engine.position_state import PositionState
from local_server.engine.condition_tracker import ConditionTracker, RuleConditionStatus


def _make_ctx(**overrides):
    base = {
        "현재가": 72000,
        "거래량": 10000,
        "수익률": 0,
        "보유수량": 0,
        "고점 대비": 0,
        "수익률고점": 0,
        "진입가": 0,
        "보유일": 0,
        "보유봉": 0,
        "실행횟수": 0,
        "장시작후": 30,
        "시간": 930,
        "요일": 1,
        "RSI": lambda p, tf=None: 50,
        "MA": lambda p, tf=None: 72000,
        "EMA": lambda p, tf=None: 72000,
        "MACD": lambda tf=None: 0,
        "MACD_SIGNAL": lambda tf=None: 0,
        "볼린저_상단": lambda p, tf=None: 75000,
        "볼린저_하단": lambda p, tf=None: 69000,
        "평균거래량": lambda p, tf=None: 5000,
        "ATR": lambda p, tf=None: 1000,
        "최고가": lambda p, tf=None: 74000,
        "최저가": lambda p, tf=None: 70000,
        "이격도": lambda p, tf=None: 0,
    }
    base.update(overrides)
    return base


class TestEngineV2Integration:
    """엔진 레벨 v2 통합 테스트."""

    def test_full_flow_buy(self):
        """매수 규칙 트리거 → PositionState 갱신."""
        src = "RSI(14) < 30 AND 보유수량 == 0 → 매수 100%"
        ast = parse_v2(src)
        ps = PositionState(symbol="005930")
        ctx = _make_ctx(RSI=lambda p, tf=None: 25)
        ctx.update(ps.to_context(72000))

        result = evaluate_v2(ast, ctx)
        assert result.action is not None
        assert result.action.side == "매수"

        # 매수 실행 시뮬
        ps.record_buy(72000, 50)
        assert ps.is_holding

    def test_full_flow_trailing_stop(self):
        """트레일링 스탑 시나리오."""
        src = """수익률 <= -2 → 매도 전량
수익률 >= 3 AND 실행횟수 < 1 → 매도 50%
고점 대비 <= -1.5 → 매도 나머지"""
        ast = parse_v2(src)
        ps = PositionState(symbol="005930")
        ps.record_buy(72000, 100)

        # 수익률 4%, 고점대비 -0.5% → 50% 부분 매도
        ctx = _make_ctx(
            수익률=4.0, 보유수량=100,
            고점 대비=-0.5, 실행횟수=0,
        )
        result = evaluate_v2(ast, ctx)
        assert result.action is not None
        assert result.action.qty_type == "percent"
        assert result.action.qty_value == 50.0

        # 실행 후 상태 갱신
        ps.record_execution(result.action.rule_index)
        ps.record_sell(50)
        assert ps.total_qty == 50

        # 다음 사이클: 고점대비 -2% → 매도 나머지
        ctx2 = _make_ctx(
            수익률=2.0, 보유수량=50,
            고점 대비=-2.0, 실행횟수=1,
        )
        result2 = evaluate_v2(ast, ctx2)
        assert result2.action is not None
        assert result2.action.qty_type == "all"

    def test_dca_scenario(self):
        """DCA 분할 매수 시나리오."""
        src = """RSI(14) < 30 AND 보유수량 == 0 → 매수 50%
RSI(14) < 20 AND 보유수량 > 0 → 매수 30%
수익률 >= 5 → 매도 전량"""
        ast = parse_v2(src)
        ps = PositionState(symbol="005930")

        # 1차 매수
        ctx1 = _make_ctx(RSI=lambda p, tf=None: 25, 보유수량=0)
        r1 = evaluate_v2(ast, ctx1)
        assert r1.action.side == "매수"
        assert r1.action.qty_value == 50.0

        ps.record_buy(72000, 50)

        # 2차 매수 (RSI 더 하락)
        ctx2 = _make_ctx(RSI=lambda p, tf=None: 18, 보유수량=50)
        r2 = evaluate_v2(ast, ctx2)
        assert r2.action.side == "매수"
        assert r2.action.qty_value == 30.0

        ps.record_buy(70000, 30)
        expected_avg = (72000 * 50 + 70000 * 30) / 80
        assert abs(ps.entry_price - expected_avg) < 0.01

    def test_condition_tracker_integration(self):
        """ConditionTracker에 스냅샷 저장."""
        src = """수익률 <= -2 → 매도 전량
수익률 >= 5 → 매도 전량"""
        ast = parse_v2(src)
        tracker = ConditionTracker()

        ctx = _make_ctx(수익률=3.0)
        result = evaluate_v2(ast, ctx)

        # 스냅샷 기록
        conditions = [
            RuleConditionStatus(
                rule_index=s.rule_index, expr_text="",
                result=s.result, details=s.details,
            )
            for s in result.snapshots
        ]
        tracker.update(rule_id=1, conditions=conditions, position={"status": "보유중"})

        snap = tracker.get(1)
        assert snap is not None
        assert len(snap.conditions) == 2
        assert snap.conditions[0].result is False  # 수익률 3 > -2
        assert snap.conditions[1].result is False  # 수익률 3 < 5

    def test_v1_compat_through_v2(self):
        """v1 매수:/매도: 스크립트가 v2로 정상 변환+실행."""
        src = "매수: RSI(14) < 30\n매도: 수익률 >= 5"
        ast = parse_v2(src)
        ctx = _make_ctx(RSI=lambda p, tf=None: 25, 보유수량=0)
        result = evaluate_v2(ast, ctx)
        assert result.action is not None
        assert result.action.side == "매수"


class TestEngineV2SpecPatterns:
    """spec §4 실전 패턴 파싱+평가 테스트."""

    def test_pattern_basic_trend(self):
        """§4.1 기본 추세 추종."""
        src = """기간 = 14
MA(20) <= MA(60) AND 보유수량 > 0 → 매도 전량
RSI(기간) < 30 AND MA(20) > MA(60) AND 보유수량 == 0 → 매수 100%
수익률 <= -2 → 매도 전량
수익률 >= 5 → 매도 전량"""
        ast = parse_v2(src)
        assert len(ast.consts) == 1
        assert len(ast.rules) == 4

    def test_pattern_multi_exit(self):
        """§4.2 다단계 청산 + 트레일링."""
        src = """수익률 <= -2 → 매도 전량
수익률 >= 3 AND 실행횟수 < 1 → 매도 50%
고점 대비 <= -1.5 → 매도 나머지
보유일 >= 3 AND 수익률 BETWEEN -1 AND 1 → 매도 전량"""
        ast = parse_v2(src)
        assert len(ast.rules) == 4

    def test_pattern_atr_dynamic(self):
        """§4.6 ATR 기반 동적 청산."""
        src = """배수 = 2
현재가 <= 진입가 - ATR(14) * 배수 → 매도 전량
현재가 >= 진입가 + ATR(14) * 배수 * 1.5 → 매도 전량
RSI(14) < 30 AND 보유수량 == 0 → 매수 100%"""
        ast = parse_v2(src)
        assert len(ast.consts) == 1
        assert len(ast.rules) == 3

    def test_pattern_volume_disparity(self):
        """§4.7 거래량 + 이격도."""
        src = """거래량 > 평균거래량(20) * 2 AND 이격도(20) < -5 AND 보유수량 == 0 → 매수 100%
이격도(20) > 3 → 매도 전량
수익률 <= -3 → 매도 전량"""
        ast = parse_v2(src)
        assert len(ast.rules) == 3
```

**테스트 실행:**

```bash
python -m pytest local_server/engine/tests/test_engine_v2.py -v
# 기대: 9 passed
```

**기존 엔진 테스트 회귀:**

```bash
python -m pytest local_server/tests/test_engine.py -v
# 기대: all passed
```

**git:**

```bash
git add local_server/engine/evaluator.py local_server/engine/engine.py local_server/engine/executor.py local_server/engine/tests/test_engine_v2.py
git commit -m "feat(engine): v2 평가 통합 — PositionState/ConditionTracker 연동, 다단계 청산, v1 폴백"
```

---

## Phase 3: API + Cloud

### Task 3.1 — 조건 상태 API

- [ ] `local_server/routers/conditions.py` — API 엔드포인트
- [ ] `local_server/routers/__init__.py` — 라우터 등록

**파일: `local_server/routers/conditions.py`**

```python
"""조건 상태 API — 실시간 전략 투명성."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from typing import Any

from local_server.deps import get_engine

router = APIRouter(prefix="/conditions", tags=["conditions"])


@router.get("/status")
async def get_all_status(engine=Depends(get_engine)) -> dict[str, Any]:
    """모든 규칙의 조건 상태 조회."""
    tracker = engine.condition_tracker
    snapshots = tracker.get_all()

    result = {}
    for rule_id, snap in snapshots.items():
        result[str(rule_id)] = _serialize_snapshot(snap)

    return {"success": True, "data": result, "count": len(result)}


@router.get("/status/{rule_id}")
async def get_rule_status(rule_id: int, engine=Depends(get_engine)) -> dict[str, Any]:
    """특정 규칙의 조건 상태 조회."""
    tracker = engine.condition_tracker
    snap = tracker.get(rule_id)

    if snap is None:
        return {"success": True, "data": None}

    return {"success": True, "data": _serialize_snapshot(snap)}


def _serialize_snapshot(snap) -> dict[str, Any]:
    """RuleStatusSnapshot → JSON dict."""
    return {
        "rule_id": snap.rule_id,
        "cycle": snap.cycle,
        "position": snap.position,
        "conditions": [
            {
                "index": c.rule_index,
                "expr": c.expr_text,
                "result": c.result,
                "details": c.details,
            }
            for c in snap.conditions
        ],
        "action": snap.action,
        "triggered_history": [
            {"at": t.at, "index": t.rule_index, "action": t.action_text}
            for t in snap.triggered_history
        ],
    }
```

`local_server/routers/__init__.py` 또는 `local_server/main.py`에서 라우터 등록:

```python
from local_server.routers.conditions import router as conditions_router
app.include_router(conditions_router, prefix="/api")
```

의존성 주입(`get_engine`)이 이미 존재한다고 가정. 없다면:

**파일: `local_server/deps.py`** (존재하지 않으면 신규)

```python
"""의존성 주입."""
from local_server.engine.engine import StrategyEngine

_engine: StrategyEngine | None = None

def set_engine(engine: StrategyEngine) -> None:
    global _engine
    _engine = engine

def get_engine() -> StrategyEngine:
    if _engine is None:
        raise RuntimeError("엔진 미초기화")
    return _engine
```

**테스트:**

```python
# local_server/engine/tests/test_engine_v2.py에 추가

class TestConditionStatusAPI:
    """API 직렬화 테스트 (라우터 없이 직접)."""

    def test_serialize_snapshot(self):
        from local_server.routers.conditions import _serialize_snapshot
        from local_server.engine.condition_tracker import (
            ConditionTracker, RuleConditionStatus, RuleStatusSnapshot,
        )
        tracker = ConditionTracker()
        tracker.record_trigger(rule_id=1, rule_index=0, action_text="매수 100%")
        tracker.update(
            rule_id=1,
            conditions=[
                RuleConditionStatus(rule_index=0, expr_text="RSI < 30", result=True, details={"RSI(14)": 25}),
            ],
            position={"status": "미보유"},
            action={"side": "매수", "qty_type": "percent", "qty_value": 100},
        )
        snap = tracker.get(1)
        serialized = _serialize_snapshot(snap)
        assert serialized["rule_id"] == 1
        assert len(serialized["conditions"]) == 1
        assert serialized["conditions"][0]["result"] is True
        assert len(serialized["triggered_history"]) == 1
```

**테스트 실행:**

```bash
python -m pytest local_server/engine/tests/test_engine_v2.py::TestConditionStatusAPI -v
# 기대: 1 passed
```

**git:**

```bash
git add local_server/routers/conditions.py local_server/deps.py local_server/engine/tests/test_engine_v2.py
git commit -m "feat(api): 조건 상태 API — GET /api/conditions/status, /api/conditions/status/{rule_id}"
```

---

### Task 3.2 — Cloud parameters 컬럼 + 메타데이터 API

- [ ] `cloud_server/models/rule.py` — parameters 컬럼 추가
- [ ] `cloud_server/api/rules.py` — 파라미터 메타데이터 CRUD

**파일: `cloud_server/models/rule.py`**

TradingRule 모델에 추가:

```python
class TradingRule(Base):
    # 기존 컬럼 유지...

    # v2 파라미터 메타데이터 (상수 선언에서 자동 추출)
    # {"기간": {"type": "number", "default": 14, "min": 5, "max": 60},
    #  "tf": {"type": "string", "default": "1d", "options": ["1m","5m","1d"]}}
    parameters = Column(JSON, nullable=True)
```

**파일: `cloud_server/api/rules.py`**

기존 CRUD에 parameters 포함. create/update 시:

```python
# rule 생성 시 script에서 parameters 자동 추출
def _extract_parameters(script: str | None) -> dict | None:
    """DSL script에서 상수 선언을 추출하여 파라미터 메타데이터 생성."""
    if not script:
        return None
    try:
        from sv_core.parsing import parse_v2
        ast = parse_v2(script)
        if not ast.consts:
            return None
        params = {}
        for const in ast.consts:
            from sv_core.parsing.ast_nodes import NumberLit, StringLit
            if isinstance(const.value, NumberLit):
                params[const.name] = {
                    "type": "number",
                    "default": const.value.value,
                }
            elif isinstance(const.value, StringLit):
                params[const.name] = {
                    "type": "string",
                    "default": const.value.value,
                }
        return params if params else None
    except Exception:
        return None
```

create/update 라우터에서:

```python
# 기존 create 라우터 내부
if payload.script:
    rule.parameters = _extract_parameters(payload.script)
```

GET 응답에 parameters 포함:

```python
# 기존 rule 직렬화에 추가
def _serialize_rule(rule: TradingRule) -> dict:
    return {
        # 기존 필드...
        "parameters": rule.parameters,
    }
```

**Alembic 마이그레이션:**

```bash
cd d:/Projects/StockVision
python -m alembic revision --autogenerate -m "add parameters column to trading_rules"
python -m alembic upgrade head
```

**테스트:**

```python
# cloud_server/tests/test_rules_api.py에 추가 (또는 inline 검증)

class TestParameterExtraction:
    def test_extract_number_params(self):
        from cloud_server.api.rules import _extract_parameters
        params = _extract_parameters("기간 = 14\n손절 = -2\nRSI(기간) < 30 → 매수 100%")
        assert params is not None
        assert params["기간"]["type"] == "number"
        assert params["기간"]["default"] == 14.0
        assert params["손절"]["default"] == -2.0

    def test_extract_string_params(self):
        from cloud_server.api.rules import _extract_parameters
        params = _extract_parameters('tf = "1d"\nRSI(14) < 30 → 매수 100%')
        assert params["tf"]["type"] == "string"
        assert params["tf"]["default"] == "1d"

    def test_no_params(self):
        from cloud_server.api.rules import _extract_parameters
        params = _extract_parameters("RSI(14) < 30 → 매수 100%")
        assert params is None

    def test_none_script(self):
        from cloud_server.api.rules import _extract_parameters
        assert _extract_parameters(None) is None
```

**테스트 실행:**

```bash
python -m pytest cloud_server/tests/test_rules_api.py::TestParameterExtraction -v
# 기대: 4 passed
```

**git:**

```bash
git add cloud_server/models/rule.py cloud_server/api/rules.py
git commit -m "feat(cloud): parameters JSON 컬럼 + 자동 추출 — 상수 선언 → 파라미터 메타데이터"
```

---

### Task 3.3 — P1 시간 필드

- [ ] `local_server/engine/evaluator.py` — 시간 컨텍스트 주입
- [ ] `local_server/engine/engine.py` — 시간 필드 계산

**파일: `local_server/engine/evaluator.py`**

`_build_dsl_context`에 시간 필드 추가:

```python
    @staticmethod
    def _build_dsl_context(market_data: dict, context: dict) -> dict[str, Any]:
        # 기존 코드...

        # v2 시간 필드
        from datetime import datetime
        now = datetime.now()
        ctx["시간"] = now.hour * 100 + now.minute  # HHMM 정수 (예: 930, 1015)
        market_open = now.replace(hour=9, minute=0, second=0, microsecond=0)
        elapsed = (now - market_open).total_seconds() / 60
        ctx["장시작후"] = max(0, int(elapsed))
        ctx["요일"] = now.isoweekday()  # 1=월 ~ 7=일

        return ctx
```

**테스트:**

```python
# sv_core/parsing/tests/test_evaluator_v2.py에 추가

class TestTimeFields:
    def test_time_field_type(self):
        """시간 필드가 숫자 타입."""
        src = "장시작후 >= 10 AND 보유수량 == 0 → 매수 100%"
        ast = parse_v2(src)
        result = evaluate_v2(ast, _ctx(장시작후=30, 보유수량=0))
        assert result.action is not None

    def test_time_field_block(self):
        """장 시작 10분 이내 진입 금지."""
        src = "장시작후 >= 10 AND RSI(14) < 30 → 매수 100%"
        ast = parse_v2(src)
        result = evaluate_v2(ast, _ctx(장시작후=5, RSI=lambda p, tf=None: 25))
        assert result.action is None  # 5분 < 10분

    def test_weekday_filter(self):
        src = "요일 <= 4 AND RSI(14) < 30 → 매수 100%"
        ast = parse_v2(src)
        result = evaluate_v2(ast, _ctx(요일=5, RSI=lambda p, tf=None: 25))
        assert result.action is None  # 금요일(5) > 4
```

**테스트 실행:**

```bash
python -m pytest sv_core/parsing/tests/test_evaluator_v2.py::TestTimeFields -v
# 기대: 3 passed
```

**git:**

```bash
git add local_server/engine/evaluator.py sv_core/parsing/tests/test_evaluator_v2.py
git commit -m "feat(engine): P1 시간 필드 — 시간, 장시작후, 요일 컨텍스트 주입"
```

---

## Phase 4: Frontend

### Task 4.1 — TypeScript 타입 + hooks

- [ ] `frontend/src/types/strategy.ts` — v2 타입 추가
- [ ] `frontend/src/hooks/useConditionStatus.ts` — 조건 상태 API 폴링
- [ ] `frontend/src/services/localClient.ts` — conditions API 메서드

**파일: `frontend/src/types/strategy.ts`**

기존 코드 하단에 추가:

```typescript
/** v2 조건 상태 타입 */

export interface ConditionDetail {
  index: number
  expr: string
  result: boolean | null
  details: Record<string, number | string | null>
}

export interface PositionInfo {
  status: '보유중' | '미보유'
  entry_price: number
  highest_price: number
  pnl_pct: number
  bars_held: number
  days_held: number
  remaining_ratio: number
}

export interface TriggerHistoryItem {
  at: string
  index: number
  action: string
}

export interface RuleConditionStatus {
  rule_id: number
  cycle: string
  position: PositionInfo
  conditions: ConditionDetail[]
  action: { side: string; qty_type: string; qty_value: number } | null
  triggered_history: TriggerHistoryItem[]
}

/** v2 DSL 규칙 구조 (파싱 결과) */
export interface DslRule {
  condition: string
  action: { side: '매수' | '매도'; qty_type: 'percent' | 'all'; qty_value: number }
}

export interface DslConst {
  name: string
  type: 'number' | 'string'
  value: number | string
}

export interface ParsedDslV2 {
  consts: DslConst[]
  rules: DslRule[]
}

/** 파라미터 메타데이터 (cloud 저장) */
export interface ParameterMeta {
  type: 'number' | 'string'
  default: number | string
  min?: number
  max?: number
  options?: string[]
}

export type ParametersMap = Record<string, ParameterMeta>
```

**파일: `frontend/src/hooks/useConditionStatus.ts`**

```typescript
/**
 * useConditionStatus — 조건 상태 API 폴링 훅.
 *
 * 로컬 서버 /api/conditions/status를 주기적으로 조회.
 */
import { useQuery } from '@tanstack/react-query'
import { localConditions } from '../services/localClient'
import type { RuleConditionStatus } from '../types/strategy'

export function useConditionStatus(ruleId?: number) {
  return useQuery<RuleConditionStatus | null>({
    queryKey: ['conditionStatus', ruleId],
    queryFn: async () => {
      if (ruleId == null) return null
      const res = await localConditions.getStatus(ruleId)
      return res.data ?? null
    },
    enabled: ruleId != null,
    refetchInterval: 5000,  // 5초 폴링
    staleTime: 3000,
  })
}

export function useAllConditionStatus() {
  return useQuery<Record<string, RuleConditionStatus>>({
    queryKey: ['conditionStatusAll'],
    queryFn: async () => {
      const res = await localConditions.getAllStatus()
      return res.data ?? {}
    },
    refetchInterval: 5000,
    staleTime: 3000,
  })
}
```

**파일: `frontend/src/services/localClient.ts`**

기존 exports 하단에 추가:

```typescript
/** 조건 상태 API */
export const localConditions = {
  getAllStatus: async () => {
    const res = await client.get('/conditions/status')
    return res.data
  },
  getStatus: async (ruleId: number) => {
    const res = await client.get(`/conditions/status/${ruleId}`)
    return res.data
  },
}
```

**테스트: `frontend/src/utils/__tests__/dslParser.test.ts`에 타입 import 확인**

```typescript
// 타입 컴파일 확인용 (런타임 테스트 아님)
import type {
  RuleConditionStatus, ConditionDetail, PositionInfo,
  TriggerHistoryItem, DslRule, DslConst, ParsedDslV2,
  ParameterMeta, ParametersMap,
} from '../../types/strategy'

describe('v2 types', () => {
  it('RuleConditionStatus 구조 확인', () => {
    const status: RuleConditionStatus = {
      rule_id: 1,
      cycle: '2026-03-29T10:01:00',
      position: {
        status: '보유중',
        entry_price: 72500,
        highest_price: 74200,
        pnl_pct: 1.8,
        bars_held: 15,
        days_held: 1,
        remaining_ratio: 0.5,
      },
      conditions: [
        { index: 0, expr: 'RSI(14) < 30', result: true, details: { 'RSI(14)': 25 } },
      ],
      action: { side: '매수', qty_type: 'percent', qty_value: 100 },
      triggered_history: [
        { at: '2026-03-29T09:32:00', index: 0, action: '매수 100%' },
      ],
    }
    expect(status.rule_id).toBe(1)
  })
})
```

**테스트 실행:**

```bash
cd frontend && npm run lint && npx vitest run src/utils/__tests__/dslParser.test.ts
# 기대: lint 통과, 테스트 통과
```

**git:**

```bash
git add frontend/src/types/strategy.ts frontend/src/hooks/useConditionStatus.ts frontend/src/services/localClient.ts frontend/src/utils/__tests__/dslParser.test.ts
git commit -m "feat(frontend): v2 타입 + useConditionStatus 훅 + localConditions API"
```

---

### Task 4.2 — 모니터링 카드 컴포넌트

- [ ] `frontend/src/components/strategy/StrategyMonitorCard.tsx` — 메인 카드
- [ ] `frontend/src/components/strategy/ConditionStatusRow.tsx` — 조건 행

**파일: `frontend/src/components/strategy/ConditionStatusRow.tsx`**

```tsx
/**
 * ConditionStatusRow — 규칙 조건 행 (상태 표시 + 현재 값).
 */
import type { ConditionDetail } from '../../types/strategy'

interface Props {
  condition: ConditionDetail
  actionText: string
}

export default function ConditionStatusRow({ condition, actionText }: Props) {
  const statusIcon = condition.result === true ? '✅' : condition.result === false ? '❌' : '⏳'

  const detailEntries = Object.entries(condition.details)

  return (
    <div className="flex items-center justify-between px-3 py-2 border-b border-default-100 last:border-b-0">
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium text-default-700 truncate">
          {condition.expr || `규칙 ${condition.index + 1}`}
          <span className="text-default-400 ml-2">{actionText}</span>
        </div>
        {detailEntries.length > 0 && (
          <div className="text-xs text-default-500 mt-0.5">
            {detailEntries.map(([key, val]) => (
              <span key={key} className="mr-3">
                {key}: <span className="font-mono">{val != null ? String(val) : '-'}</span>
              </span>
            ))}
          </div>
        )}
      </div>
      <span className="text-lg ml-2 flex-shrink-0">{statusIcon}</span>
    </div>
  )
}
```

**파일: `frontend/src/components/strategy/StrategyMonitorCard.tsx`**

```tsx
/**
 * StrategyMonitorCard — 전략 모니터링 카드.
 *
 * spec §3.7 와이어프레임 구현.
 * 조건별 실시간 상태 + 포지션 정보 + 트리거 이력.
 */
import { Card, CardBody, CardHeader, Chip, Divider } from '@heroui/react'
import { useConditionStatus } from '../../hooks/useConditionStatus'
import ConditionStatusRow from './ConditionStatusRow'
import type { Rule } from '../../types/strategy'

interface Props {
  rule: Rule
  onEditClick?: () => void
}

export default function StrategyMonitorCard({ rule, onEditClick }: Props) {
  const { data: status, isLoading } = useConditionStatus(rule.id)

  if (isLoading) {
    return (
      <Card className="w-full">
        <CardBody className="text-center text-default-400 py-6">상태 로딩 중...</CardBody>
      </Card>
    )
  }

  if (!status) {
    return (
      <Card className="w-full">
        <CardBody className="text-center text-default-400 py-6">
          평가 데이터 없음 (엔진 미실행 또는 미평가)
        </CardBody>
      </Card>
    )
  }

  const buyConditions = status.conditions.filter((_, i) => {
    const action = _getActionForIndex(rule.script, i)
    return action?.startsWith('매수')
  })
  const sellConditions = status.conditions.filter((_, i) => {
    const action = _getActionForIndex(rule.script, i)
    return action?.startsWith('매도')
  })

  const pos = status.position

  return (
    <Card className="w-full">
      <CardHeader className="flex justify-between items-center px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="text-base font-semibold">{rule.name}</span>
          <Chip size="sm" variant="flat" color={rule.is_active ? 'success' : 'default'}>
            {rule.is_active ? '활성' : '비활성'}
          </Chip>
        </div>
        {onEditClick && (
          <button
            onClick={onEditClick}
            className="text-sm text-primary hover:underline"
          >
            편집
          </button>
        )}
      </CardHeader>

      <Divider />

      <CardBody className="p-0">
        {/* 진입 규칙 */}
        {buyConditions.length > 0 && (
          <div>
            <div className="px-4 py-2 text-xs font-semibold text-default-500 bg-default-50">
              진입 규칙
            </div>
            {buyConditions.map((cond) => (
              <ConditionStatusRow
                key={cond.index}
                condition={cond}
                actionText={_getActionForIndex(rule.script, cond.index) ?? ''}
              />
            ))}
          </div>
        )}

        {/* 청산 규칙 */}
        {sellConditions.length > 0 && (
          <div>
            <div className="px-4 py-2 text-xs font-semibold text-default-500 bg-default-50">
              청산 규칙
            </div>
            {sellConditions.map((cond) => (
              <ConditionStatusRow
                key={cond.index}
                condition={cond}
                actionText={_getActionForIndex(rule.script, cond.index) ?? ''}
              />
            ))}
          </div>
        )}

        <Divider />

        {/* 포지션 정보 */}
        <div className="px-4 py-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-default-600">
          <span>상태: <b>{pos.status}</b></span>
          {pos.status === '보유중' && (
            <>
              <span>진입: <b>{pos.entry_price.toLocaleString()}원</b></span>
              <span>최고: <b>{pos.highest_price.toLocaleString()}원</b></span>
              <span>수익률: <b className={pos.pnl_pct >= 0 ? 'text-danger' : 'text-primary'}>
                {pos.pnl_pct >= 0 ? '+' : ''}{pos.pnl_pct.toFixed(2)}%
              </b></span>
              <span>보유: <b>{pos.days_held}일 {pos.bars_held}봉</b></span>
            </>
          )}
        </div>

        {/* 트리거 이력 */}
        {status.triggered_history.length > 0 && (
          <>
            <Divider />
            <div className="px-4 py-2">
              <div className="text-xs font-semibold text-default-500 mb-1">최근 트리거</div>
              {status.triggered_history.slice(0, 5).map((t, i) => (
                <div key={i} className="text-xs text-default-600 py-0.5">
                  <span className="text-default-400 mr-2">
                    {new Date(t.at).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })}
                  </span>
                  {t.action}
                </div>
              ))}
            </div>
          </>
        )}
      </CardBody>
    </Card>
  )
}

/** DSL script에서 규칙 인덱스에 해당하는 행동 텍스트 추출. */
function _getActionForIndex(script: string | null, index: number): string | null {
  if (!script) return null
  // 규칙 줄 추출 (→ 또는 -> 포함하는 줄만)
  const lines = script.split('\n').filter(
    (line) => (line.includes('\u2192') || line.includes('->')) && !line.trim().startsWith('--')
  )
  if (index >= lines.length) return null
  const line = lines[index]
  const arrowIdx = line.indexOf('\u2192') !== -1 ? line.indexOf('\u2192') : line.indexOf('->')
  if (arrowIdx === -1) return null
  const afterArrow = line.substring(arrowIdx + (line[arrowIdx] === '\u2192' ? 1 : 2)).trim()
  return afterArrow || null
}
```

**테스트:** 컴포넌트 렌더링 테스트는 vitest + @testing-library/react.

```typescript
// frontend/src/components/strategy/__tests__/ConditionStatusRow.test.tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import ConditionStatusRow from '../ConditionStatusRow'
import type { ConditionDetail } from '../../../types/strategy'

describe('ConditionStatusRow', () => {
  it('True 조건 표시', () => {
    const cond: ConditionDetail = {
      index: 0, expr: 'RSI(14) < 30', result: true,
      details: { 'RSI(14)': 25 },
    }
    render(<ConditionStatusRow condition={cond} actionText="매수 100%" />)
    expect(screen.getByText(/RSI\(14\) < 30/)).toBeDefined()
    expect(screen.getByText(/매수 100%/)).toBeDefined()
  })

  it('False 조건 표시', () => {
    const cond: ConditionDetail = {
      index: 1, expr: '수익률 >= 5', result: false,
      details: { '수익률': 2.0 },
    }
    render(<ConditionStatusRow condition={cond} actionText="매도 전량" />)
    expect(screen.getByText(/수익률 >= 5/)).toBeDefined()
  })
})
```

**테스트 실행:**

```bash
cd frontend && npx vitest run src/components/strategy/__tests__/ConditionStatusRow.test.tsx
# 기대: 2 passed
```

**git:**

```bash
git add frontend/src/components/strategy/StrategyMonitorCard.tsx frontend/src/components/strategy/ConditionStatusRow.tsx frontend/src/components/strategy/__tests__/ConditionStatusRow.test.tsx
git commit -m "feat(frontend): StrategyMonitorCard + ConditionStatusRow — 조건별 실시간 상태 표시"
```

---

### Task 4.3 — StrategyList 통합 + DSL 편집

- [ ] `frontend/src/pages/StrategyList.tsx` — 모니터링 카드 통합
- [ ] `frontend/src/pages/StrategyBuilder.tsx` — DSL 직접 편집 모드

**파일: `frontend/src/pages/StrategyList.tsx`**

기존 RuleCard 옆에 모니터링 카드 토글 추가:

```tsx
// import 추가
import StrategyMonitorCard from '../components/strategy/StrategyMonitorCard'
import { useAllConditionStatus } from '../hooks/useConditionStatus'

// 컴포넌트 내부
export default function StrategyList() {
  // 기존 코드 유지...
  const [expandedRule, setExpandedRule] = useState<number | null>(null)

  // 조건 상태 (엔진 실행 중일 때만)
  const { data: conditionStatuses } = useAllConditionStatus()

  // 규칙 목록 렌더링에 모니터링 카드 추가
  // 기존 rules.map 내부에서:
  // {expandedRule === rule.id && <StrategyMonitorCard rule={rule} />}
  // 를 RuleCard 아래에 배치
}
```

구체적 수정: 기존 `rules.map` 블록 안에서 `RuleCard` 다음에:

```tsx
{/* 모니터링 카드 (확장 시) */}
{expandedRule === rule.id && engineRunning && (
  <StrategyMonitorCard
    rule={rule}
    onEditClick={() => navigate(`/strategy/edit/${rule.id}`)}
  />
)}
```

RuleCard에 확장 토글 추가 (기존 onClick이 없다면):

```tsx
<div
  onClick={() => setExpandedRule(expandedRule === rule.id ? null : rule.id)}
  className="cursor-pointer"
>
  <RuleCard ... />
</div>
```

**파일: `frontend/src/pages/StrategyBuilder.tsx`**

DSL 직접 편집 모드 토글 추가. 기존 StrategyBuilder에:

```tsx
// 기존 imports에 추가
import { useState } from 'react'
import { Textarea, Switch } from '@heroui/react'

// 컴포넌트 내부
const [dslMode, setDslMode] = useState(false)
const [dslText, setDslText] = useState(rule?.script ?? '')

// JSX 내부에 DSL 편집 토글 추가
<div className="flex items-center gap-2 mb-4">
  <Switch
    isSelected={dslMode}
    onValueChange={setDslMode}
    size="sm"
  />
  <span className="text-sm text-default-600">DSL 직접 편집</span>
</div>

{dslMode ? (
  <Textarea
    label="DSL 스크립트"
    value={dslText}
    onValueChange={setDslText}
    minRows={10}
    maxRows={30}
    classNames={{ input: 'font-mono text-sm' }}
    placeholder={`-- 상수\n기간 = 14\n\n-- 규칙\nRSI(기간) < 30 → 매수 100%\n수익률 >= 5 → 매도 전량`}
  />
) : (
  // 기존 폼 빌더 UI
  <>{/* existing form UI */}</>
)}
```

**테스트:** 빌드 확인으로 대체.

```bash
cd frontend && npm run build
# 기대: 빌드 성공, 에러 없음
```

**git:**

```bash
git add frontend/src/pages/StrategyList.tsx frontend/src/pages/StrategyBuilder.tsx
git commit -m "feat(frontend): StrategyList 모니터링 카드 통합 + DSL 직접 편집 모드"
```

---

### Task 4.4 — P1 트리거 타임라인 + 카드<->DSL 변환

- [ ] `frontend/src/components/strategy/TriggerTimeline.tsx` — 트리거 이력 타임라인
- [ ] `frontend/src/utils/dslParser.ts` — v2 DSL 파싱/직렬화

**파일: `frontend/src/components/strategy/TriggerTimeline.tsx`**

```tsx
/**
 * TriggerTimeline — 트리거 이력 타임라인 컴포넌트.
 */
import type { TriggerHistoryItem } from '../../types/strategy'

interface Props {
  triggers: TriggerHistoryItem[]
  maxItems?: number
}

export default function TriggerTimeline({ triggers, maxItems = 10 }: Props) {
  if (triggers.length === 0) {
    return (
      <div className="text-xs text-default-400 py-2 text-center">
        트리거 이력 없음
      </div>
    )
  }

  const items = triggers.slice(0, maxItems)

  return (
    <div className="relative pl-4">
      {/* 세로 타임라인 선 */}
      <div className="absolute left-1.5 top-0 bottom-0 w-px bg-default-200" />

      {items.map((trigger, i) => {
        const time = new Date(trigger.at)
        const timeStr = time.toLocaleTimeString('ko-KR', {
          hour: '2-digit', minute: '2-digit', second: '2-digit',
        })
        const isBuy = trigger.action.includes('매수')

        return (
          <div key={i} className="relative flex items-start gap-2 py-1.5">
            {/* 점 */}
            <div className={`absolute -left-[calc(1rem-3px)] top-2.5 w-1.5 h-1.5 rounded-full ${
              isBuy ? 'bg-danger' : 'bg-primary'
            }`} />
            <div className="text-xs">
              <span className="text-default-400 font-mono mr-2">{timeStr}</span>
              <span className={`font-medium ${isBuy ? 'text-danger' : 'text-primary'}`}>
                {trigger.action}
              </span>
            </div>
          </div>
        )
      })}
    </div>
  )
}
```

**파일: `frontend/src/utils/dslParser.ts`**

기존 파서 하단에 v2 파싱/직렬화 함수 추가:

```typescript
// ── v2 DSL 파싱 ──

export interface DslV2ParseResult {
  success: boolean
  consts: Array<{ name: string; value: string | number }>
  rules: Array<{ condition: string; action: string }>
  errors: ParseError[]
}

/**
 * v2 DSL 문자열을 구조화.
 * 서버 파서의 간소화 버전 — 규칙 분리와 상수 추출만 수행.
 */
export function parseDslV2(input: string): DslV2ParseResult {
  const errors: ParseError[] = []
  const consts: Array<{ name: string; value: string | number }> = []
  const rules: Array<{ condition: string; action: string }> = []

  const lines = input.split('\n')
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim()
    if (!line || line.startsWith('--')) continue

    // 상수: name = value (숫자 또는 문자열)
    const constMatch = line.match(/^([가-힣a-zA-Z_]\w*)\s*=\s*(-?\d+(?:\.\d+)?|"[^"]*")\s*$/)
    if (constMatch) {
      const name = constMatch[1]
      const rawVal = constMatch[2]
      const value = rawVal.startsWith('"') ? rawVal.slice(1, -1) : parseFloat(rawVal)
      consts.push({ name, value })
      continue
    }

    // 규칙: condition → action
    const arrowIdx = line.indexOf('\u2192') !== -1 ? line.indexOf('\u2192') : line.indexOf('->')
    if (arrowIdx !== -1) {
      const condition = line.substring(0, arrowIdx).trim()
      const arrowLen = line[arrowIdx] === '\u2192' ? 1 : 2
      const action = line.substring(arrowIdx + arrowLen).trim()
      if (condition && action) {
        rules.push({ condition, action })
        continue
      }
    }

    // v1 호환: 매수: / 매도:
    const v1Match = line.match(/^(매수|매도)\s*:\s*(.+)$/)
    if (v1Match) {
      const side = v1Match[1]
      const expr = v1Match[2].trim()
      if (side === '매수') {
        rules.push({ condition: expr, action: '매수 100%' })
      } else {
        rules.push({ condition: expr, action: '매도 전량' })
      }
      continue
    }

    // 커스텀 함수 정의 (무시 — 조건식이므로)
    const funcMatch = line.match(/^([가-힣a-zA-Z_]\w*)\s*(?:\(\))?\s*=\s*(.+)$/)
    if (funcMatch) {
      continue  // 카드 UI에서는 스킵
    }

    errors.push({ line: i + 1, column: 1, message: `인식 불가: ${line}` })
  }

  return { success: errors.length === 0, consts, rules, errors }
}

/**
 * 구조화된 v2 데이터를 DSL 문자열로 직렬화.
 */
export function serializeDslV2(
  consts: Array<{ name: string; value: string | number }>,
  rules: Array<{ condition: string; action: string }>,
): string {
  const lines: string[] = []

  // 상수
  for (const c of consts) {
    const val = typeof c.value === 'string' ? `"${c.value}"` : String(c.value)
    lines.push(`${c.name} = ${val}`)
  }

  if (consts.length > 0 && rules.length > 0) {
    lines.push('')  // 빈 줄 구분
  }

  // 규칙
  for (const r of rules) {
    lines.push(`${r.condition} \u2192 ${r.action}`)
  }

  return lines.join('\n')
}
```

**테스트: `frontend/src/utils/__tests__/dslParser.test.ts`에 추가**

```typescript
import { parseDslV2, serializeDslV2 } from '../dslParser'

describe('parseDslV2', () => {
  it('상수 + 규칙 파싱', () => {
    const r = parseDslV2('기간 = 14\nRSI(기간) < 30 → 매수 100%')
    expect(r.success).toBe(true)
    expect(r.consts).toHaveLength(1)
    expect(r.consts[0]).toEqual({ name: '기간', value: 14 })
    expect(r.rules).toHaveLength(1)
    expect(r.rules[0].condition).toBe('RSI(기간) < 30')
    expect(r.rules[0].action).toBe('매수 100%')
  })

  it('문자열 상수', () => {
    const r = parseDslV2('tf = "1d"\nRSI(14) < 30 → 매수 100%')
    expect(r.consts[0].value).toBe('1d')
  })

  it('복수 규칙', () => {
    const r = parseDslV2(`수익률 <= -2 → 매도 전량
수익률 >= 3 → 매도 50%
RSI(14) < 30 → 매수 100%`)
    expect(r.rules).toHaveLength(3)
  })

  it('주석 무시', () => {
    const r = parseDslV2('-- 주석\nRSI(14) < 30 → 매수 100%')
    expect(r.rules).toHaveLength(1)
  })

  it('v1 호환', () => {
    const r = parseDslV2('매수: RSI(14) < 30\n매도: 수익률 >= 5')
    expect(r.rules).toHaveLength(2)
    expect(r.rules[0].action).toBe('매수 100%')
    expect(r.rules[1].action).toBe('매도 전량')
  })

  it('-> 화살표 지원', () => {
    const r = parseDslV2('RSI(14) < 30 -> 매수 100%')
    expect(r.rules).toHaveLength(1)
  })
})

describe('serializeDslV2', () => {
  it('상수 + 규칙 직렬화', () => {
    const result = serializeDslV2(
      [{ name: '기간', value: 14 }],
      [{ condition: 'RSI(기간) < 30', action: '매수 100%' }],
    )
    expect(result).toContain('기간 = 14')
    expect(result).toContain('RSI(기간) < 30')
    expect(result).toContain('매수 100%')
  })

  it('문자열 상수 따옴표', () => {
    const result = serializeDslV2(
      [{ name: 'tf', value: '1d' }],
      [{ condition: 'RSI(14) < 30', action: '매수 100%' }],
    )
    expect(result).toContain('tf = "1d"')
  })

  it('양방향 변환', () => {
    const original = '기간 = 14\n\nRSI(기간) < 30 \u2192 매수 100%'
    const parsed = parseDslV2(original)
    const serialized = serializeDslV2(parsed.consts, parsed.rules)
    const reparsed = parseDslV2(serialized)
    expect(reparsed.consts).toEqual(parsed.consts)
    expect(reparsed.rules).toEqual(parsed.rules)
  })
})
```

**테스트 실행:**

```bash
cd frontend && npx vitest run src/utils/__tests__/dslParser.test.ts
# 기대: all passed
```

**git:**

```bash
git add frontend/src/components/strategy/TriggerTimeline.tsx frontend/src/utils/dslParser.ts frontend/src/utils/__tests__/dslParser.test.ts
git commit -m "feat(frontend): P1 TriggerTimeline + v2 DSL 파싱/직렬화 (카드↔DSL 변환)"
```

---

## Final: 회귀 테스트

### Task 5.1 — 전체 회귀 테스트

- [ ] sv_core 테스트 전체 통과
- [ ] local_server 테스트 전체 통과
- [ ] frontend 빌드 + lint + 테스트 통과

**테스트 실행:**

```bash
# 1. sv_core 전체
cd d:/Projects/StockVision
python -m pytest sv_core/ -v --tb=short
# 기대: all passed (v1 + v2 테스트 모두)

# 2. local_server 전체
python -m pytest local_server/ -v --tb=short
# 기대: all passed (기존 + v2 테스트)

# 3. frontend
cd frontend
npm run lint
# 기대: 0 errors

npm run build
# 기대: 빌드 성공

npx vitest run
# 기대: all passed
```

**확인 사항:**

1. 기존 v1 `parse()` + `evaluate()` 함수가 변경 없이 동작
2. 기존 `RuleEvaluator.evaluate()` (v1 경로)가 변경 없이 동작
3. v1 JSON 조건 폴백이 정상 동작
4. 기존 `StrategyEngine.evaluate_all()` 흐름이 깨지지 않음
5. `frontend/src/types/strategy.ts`의 기존 타입이 변경 없음
6. 기존 `dslParser.ts`의 `parseDsl()` 함수가 변경 없이 동작

**git:**

```bash
git add -A
git commit -m "test: v2 전체 회귀 테스트 통과 확인"
```

---

## 구현 순서 요약

| Phase | Task | 파일 | 의존성 |
|-------|------|------|--------|
| 1 | 1.1 토큰 | tokens.py, lexer.py | 없음 |
| 1 | 1.2 AST | ast_nodes.py | 없음 |
| 1 | 1.3 파서 | parser.py | 1.1, 1.2 |
| 1 | 1.4 v1 호환 | test_parser_v2.py | 1.3 |
| 1 | 1.5 builtins | builtins.py, calculator.py | 1.2 |
| 1 | 1.6 평가기 | evaluator.py, __init__.py | 1.3, 1.5 |
| 2 | 2.1 PositionState | position_state.py | 없음 |
| 2 | 2.2 히스토리 | indicator_provider.py | 없음 |
| 2 | 2.3 ConditionTracker | condition_tracker.py | 없음 |
| 2 | 2.4 엔진 통합 | evaluator.py, engine.py | 1.6, 2.1~2.3 |
| 3 | 3.1 상태 API | conditions.py | 2.3 |
| 3 | 3.2 Cloud params | rule.py, rules.py | 1.3 |
| 3 | 3.3 시간 필드 | evaluator.py | 1.5 |
| 4 | 4.1 타입+hooks | strategy.ts, useConditionStatus.ts | 3.1 |
| 4 | 4.2 카드 컴포넌트 | StrategyMonitorCard.tsx, ConditionStatusRow.tsx | 4.1 |
| 4 | 4.3 StrategyList | StrategyList.tsx, StrategyBuilder.tsx | 4.2 |
| 4 | 4.4 타임라인+DSL | TriggerTimeline.tsx, dslParser.ts | 4.1 |
| F | 5.1 회귀 테스트 | 전체 | 전체 |

**병렬 가능 그룹:**
- Phase 1: Task 1.1 + 1.2 동시 → 1.3 → 1.4 + 1.5 동시 → 1.6
- Phase 2: Task 2.1 + 2.2 + 2.3 동시 → 2.4
- Phase 3: Task 3.1 + 3.2 + 3.3 동시
- Phase 4: Task 4.1 → 4.2 + 4.4 동시 → 4.3
