"""DSL 재귀 하강 파서 — grammar.md §2 구문 규칙 1:1 대응.

구문 분석 + 의미 제약(§4.1) + 타입 제약(§4.2) 검증.
"""

from __future__ import annotations

from .ast_nodes import (
    BinOp,
    BoolLit,
    BuyBlock,
    Comparison,
    CustomFuncDef,
    FieldRef,
    FuncCall,
    Node,
    NumberLit,
    Script,
    SellBlock,
    UnaryOp,
)
from .builtins import (
    BUILTIN_FIELDS,
    BUILTIN_FUNCTIONS,
    BUILTIN_PATTERNS,
    get_builtin_func,
    get_pattern_func,
)
from .errors import DSLNameError, DSLSyntaxError, DSLTypeError
from .tokens import Token, TokenType, KEYWORDS, BOOL_LITERALS


# ── 타입 추론 ──

_BOOLEAN = "boolean"
_NUMBER = "number"
_UNKNOWN = "unknown"


def _infer_type(node: Node, custom_funcs: dict[str, str]) -> str:
    """AST 노드의 결과 타입을 추론."""
    if isinstance(node, NumberLit):
        return _NUMBER
    if isinstance(node, BoolLit):
        return _BOOLEAN
    if isinstance(node, FieldRef):
        return _NUMBER  # 내장 필드는 모두 숫자
    if isinstance(node, Comparison):
        return _BOOLEAN
    if isinstance(node, BinOp):
        if node.op in ("AND", "OR"):
            return _BOOLEAN
        return _NUMBER  # +, -, *, /
    if isinstance(node, UnaryOp):
        if node.op == "NOT":
            return _BOOLEAN
        return _NUMBER  # 단항 -
    if isinstance(node, FuncCall):
        # 커스텀 함수
        if node.name in custom_funcs:
            return custom_funcs[node.name]
        # 내장 패턴 함수
        if node.name in BUILTIN_PATTERNS:
            return _BOOLEAN
        # 내장 함수
        spec = BUILTIN_FUNCTIONS.get(node.name)
        if spec:
            return spec.return_type
        return _UNKNOWN
    return _UNKNOWN


# ── 파서 ──

class Parser:
    """재귀 하강 파서. grammar.md EBNF 1:1 대응."""

    def __init__(self, tokens: list[Token]):
        self._tokens = tokens
        self._pos = 0
        # 의미 제약: 커스텀 함수 선언 추적
        self._custom_funcs: dict[str, str] = {}  # name -> return_type
        self._current_func_name: str | None = None  # 재귀 감지용

    # ── 토큰 유틸 ──

    def _peek(self) -> Token:
        return self._tokens[self._pos]

    def _advance(self) -> Token:
        tok = self._tokens[self._pos]
        self._pos += 1
        return tok

    def _expect(self, tt: TokenType) -> Token:
        tok = self._peek()
        if tok.type != tt:
            raise DSLSyntaxError(
                f"'{tt.name}' 토큰이 필요하지만 '{tok.value}'({tok.type.name})이 있습니다",
                tok.line, tok.col,
            )
        return self._advance()

    def _at(self, *types: TokenType) -> bool:
        return self._peek().type in types

    def _skip_newlines(self):
        while self._at(TokenType.NEWLINE):
            self._advance()

    # ── 최상위: script ──

    def parse(self) -> Script:
        """최상위 파싱 → Script AST."""
        self._skip_newlines()

        custom_funcs: list[CustomFuncDef] = []
        buy_block: BuyBlock | None = None
        sell_block: SellBlock | None = None

        while not self._at(TokenType.EOF):
            tok = self._peek()

            # 매수 블록
            if tok.type == TokenType.KW_BUY:
                if buy_block is not None:
                    raise DSLSyntaxError("매수: 블록이 중복됩니다", tok.line, tok.col)
                buy_block = self._parse_buy_block()

            # 매도 블록
            elif tok.type == TokenType.KW_SELL:
                if sell_block is not None:
                    raise DSLSyntaxError("매도: 블록이 중복됩니다", tok.line, tok.col)
                sell_block = self._parse_sell_block()

            # 커스텀 함수 정의: IDENT ( ) = expr
            elif tok.type == TokenType.IDENT and self._is_custom_func_def():
                func = self._parse_custom_func_def()
                custom_funcs.append(func)

            else:
                raise DSLSyntaxError(
                    f"예상치 못한 토큰: '{tok.value}'", tok.line, tok.col,
                )

            self._skip_newlines()

        # 의미 제약: 매수/매도 필수
        if buy_block is None:
            tok = self._peek()
            raise DSLSyntaxError("매수: 블록이 없습니다", tok.line, tok.col)
        if sell_block is None:
            tok = self._peek()
            raise DSLSyntaxError("매도: 블록이 없습니다", tok.line, tok.col)

        return Script(
            custom_funcs=tuple(custom_funcs),
            buy_block=buy_block,
            sell_block=sell_block,
        )

    def _is_custom_func_def(self) -> bool:
        """현재 위치가 커스텀 함수 정의인지 lookahead."""
        # IDENT ( ) =
        p = self._pos
        if p + 3 >= len(self._tokens):
            return False
        return (
            self._tokens[p].type == TokenType.IDENT
            and self._tokens[p + 1].type == TokenType.LPAREN
            and self._tokens[p + 2].type == TokenType.RPAREN
            and self._tokens[p + 3].type == TokenType.ASSIGN
        )

    # ── 블록 파싱 ──

    def _parse_buy_block(self) -> BuyBlock:
        tok = self._advance()  # 매수
        self._expect(TokenType.COLON)
        expr = self._parse_expression()
        self._check_type(expr, _BOOLEAN, "매수: 블록 결과는 boolean이어야 합니다")
        self._expect_terminator()
        return BuyBlock(expr=expr, line=tok.line, col=tok.col)

    def _parse_sell_block(self) -> SellBlock:
        tok = self._advance()  # 매도
        self._expect(TokenType.COLON)
        expr = self._parse_expression()
        self._check_type(expr, _BOOLEAN, "매도: 블록 결과는 boolean이어야 합니다")
        self._expect_terminator()
        return SellBlock(expr=expr, line=tok.line, col=tok.col)

    def _parse_custom_func_def(self) -> CustomFuncDef:
        name_tok = self._advance()  # IDENT
        name = name_tok.value

        # 의미 제약: 이름 중복 금지
        if name in self._custom_funcs:
            raise DSLNameError(
                f"'{name}'이 이미 정의되었습니다", name_tok.line, name_tok.col,
            )

        self._expect(TokenType.LPAREN)
        self._expect(TokenType.RPAREN)
        self._expect(TokenType.ASSIGN)

        # 재귀 감지
        self._current_func_name = name
        body = self._parse_expression()
        self._current_func_name = None

        ret_type = _infer_type(body, self._custom_funcs)
        self._custom_funcs[name] = ret_type

        self._expect_terminator()
        return CustomFuncDef(name=name, body=body, line=name_tok.line, col=name_tok.col)

    def _expect_terminator(self):
        """NEWLINE 또는 EOF."""
        if self._at(TokenType.NEWLINE):
            self._advance()
            self._skip_newlines()
        elif not self._at(TokenType.EOF):
            tok = self._peek()
            raise DSLSyntaxError(
                f"줄 끝 또는 파일 끝이 필요하지만 '{tok.value}'이 있습니다",
                tok.line, tok.col,
            )

    # ── 식 파싱 (우선순위 오름차순) ──

    def _parse_expression(self) -> Node:
        return self._parse_or()

    # 레벨 1: OR (가장 낮은 우선순위)
    def _parse_or(self) -> Node:
        left = self._parse_and()
        while self._at(TokenType.OR):
            op_tok = self._advance()
            self._check_type(left, _BOOLEAN, "OR 피연산자는 boolean이어야 합니다")
            right = self._parse_and()
            self._check_type(right, _BOOLEAN, "OR 피연산자는 boolean이어야 합니다")
            left = BinOp(op="OR", left=left, right=right, line=op_tok.line, col=op_tok.col)
        return left

    # 레벨 2: AND
    def _parse_and(self) -> Node:
        left = self._parse_not()
        while self._at(TokenType.AND):
            op_tok = self._advance()
            self._check_type(left, _BOOLEAN, "AND 피연산자는 boolean이어야 합니다")
            right = self._parse_not()
            self._check_type(right, _BOOLEAN, "AND 피연산자는 boolean이어야 합니다")
            left = BinOp(op="AND", left=left, right=right, line=op_tok.line, col=op_tok.col)
        return left

    # 레벨 3: NOT (단항)
    def _parse_not(self) -> Node:
        if self._at(TokenType.NOT):
            op_tok = self._advance()
            operand = self._parse_not()
            self._check_type(operand, _BOOLEAN, "NOT 피연산자는 boolean이어야 합니다")
            return UnaryOp(op="NOT", operand=operand, line=op_tok.line, col=op_tok.col)
        return self._parse_comparison()

    # 레벨 4: 비교 (체이닝 금지)
    def _parse_comparison(self) -> Node:
        left = self._parse_additive()
        if self._at(TokenType.GT, TokenType.GE, TokenType.LT, TokenType.LE, TokenType.EQ, TokenType.NE):
            op_tok = self._advance()
            self._check_type(left, _NUMBER, "비교 연산자의 피연산자는 숫자여야 합니다")
            right = self._parse_additive()
            self._check_type(right, _NUMBER, "비교 연산자의 피연산자는 숫자여야 합니다")
            node = Comparison(op=op_tok.value, left=left, right=right, line=op_tok.line, col=op_tok.col)
            # 체이닝 금지
            if self._at(TokenType.GT, TokenType.GE, TokenType.LT, TokenType.LE, TokenType.EQ, TokenType.NE):
                bad = self._peek()
                raise DSLSyntaxError(
                    "비교 연산을 연속으로 사용할 수 없습니다", bad.line, bad.col,
                )
            return node
        return left

    # 레벨 5: 덧셈/뺄셈
    def _parse_additive(self) -> Node:
        left = self._parse_multiplicative()
        while self._at(TokenType.PLUS, TokenType.MINUS):
            op_tok = self._advance()
            self._check_type(left, _NUMBER, "산술 연산자의 피연산자는 숫자여야 합니다")
            right = self._parse_multiplicative()
            self._check_type(right, _NUMBER, "산술 연산자의 피연산자는 숫자여야 합니다")
            left = BinOp(op=op_tok.value, left=left, right=right, line=op_tok.line, col=op_tok.col)
        return left

    # 레벨 6: 곱셈/나눗셈
    def _parse_multiplicative(self) -> Node:
        left = self._parse_unary()
        while self._at(TokenType.STAR, TokenType.SLASH):
            op_tok = self._advance()
            self._check_type(left, _NUMBER, "산술 연산자의 피연산자는 숫자여야 합니다")
            right = self._parse_unary()
            self._check_type(right, _NUMBER, "산술 연산자의 피연산자는 숫자여야 합니다")
            left = BinOp(op=op_tok.value, left=left, right=right, line=op_tok.line, col=op_tok.col)
        return left

    # 레벨 7: 단항 -
    def _parse_unary(self) -> Node:
        if self._at(TokenType.MINUS):
            op_tok = self._advance()
            operand = self._parse_unary()
            self._check_type(operand, _NUMBER, "단항 -의 피연산자는 숫자여야 합니다")
            return UnaryOp(op="-", operand=operand, line=op_tok.line, col=op_tok.col)
        return self._parse_primary()

    # 레벨 8: primary (가장 높은 우선순위)
    def _parse_primary(self) -> Node:
        tok = self._peek()

        # 숫자 리터럴
        if tok.type == TokenType.NUMBER:
            self._advance()
            return NumberLit(value=float(tok.value), line=tok.line, col=tok.col)

        # 불리언 리터럴
        if tok.type == TokenType.BOOL_LIT:
            self._advance()
            return BoolLit(value=BOOL_LITERALS[tok.value], line=tok.line, col=tok.col)

        # 괄호 그룹
        if tok.type == TokenType.LPAREN:
            self._advance()
            expr = self._parse_expression()
            self._expect(TokenType.RPAREN)
            return expr

        # 식별자: 함수 호출 또는 필드 참조
        if tok.type == TokenType.IDENT:
            return self._parse_ident()

        raise DSLSyntaxError(
            f"식이 필요하지만 '{tok.value}'({tok.type.name})이 있습니다",
            tok.line, tok.col,
        )

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

            # 의미 제약: 재귀 금지
            if name == self._current_func_name:
                raise DSLNameError(
                    f"'{name}'이 자기 자신을 참조합니다",
                    name_tok.line, name_tok.col,
                )

            # 해석 순서 (spec §4.3): 커스텀 > 패턴 > 내장 함수
            # 1. 커스텀 함수
            if name in self._custom_funcs:
                if args:
                    raise DSLSyntaxError(
                        f"'{name}'은 인자를 받지 않습니다",
                        name_tok.line, name_tok.col,
                    )
                return FuncCall(name=name, args=(), line=name_tok.line, col=name_tok.col)

            # 2. 내장 패턴 함수
            pat = get_pattern_func(name)
            if pat is not None:
                if args:
                    raise DSLSyntaxError(
                        f"'{name}'은 인자를 받지 않습니다",
                        name_tok.line, name_tok.col,
                    )
                return FuncCall(name=name, args=(), line=name_tok.line, col=name_tok.col)

            # 3. 내장 함수
            spec = get_builtin_func(name)
            if spec is not None:
                if spec.param_count >= 0 and len(args) != spec.param_count:
                    raise DSLSyntaxError(
                        f"'{name}'은 {spec.param_count}개 인자가 필요하지만 {len(args)}개가 전달되었습니다",
                        name_tok.line, name_tok.col,
                    )
                return FuncCall(name=name, args=tuple(args), line=name_tok.line, col=name_tok.col)

            # 4. 미정의 함수
            raise DSLNameError(
                f"'{name}'은 정의되지 않은 식별자입니다",
                name_tok.line, name_tok.col,
            )

        # 필드 참조: IDENT (괄호 없음)

        # 해석 순서: 커스텀 후방 참조 확인
        if name == self._current_func_name:
            raise DSLNameError(
                f"'{name}'이 자기 자신을 참조합니다",
                name_tok.line, name_tok.col,
            )

        # 커스텀 함수를 괄호 없이 참조 → 에러
        if name in self._custom_funcs:
            raise DSLSyntaxError(
                f"'{name}'은 함수입니다. '{name}()' 형태로 호출하세요",
                name_tok.line, name_tok.col,
            )

        # 내장 필드
        if name in BUILTIN_FIELDS:
            return FieldRef(name=name, line=name_tok.line, col=name_tok.col)

        # 패턴/내장 함수를 괄호 없이 참조 → 에러
        if name in BUILTIN_PATTERNS or name in BUILTIN_FUNCTIONS:
            raise DSLSyntaxError(
                f"'{name}'은 함수입니다. '{name}()' 형태로 호출하세요",
                name_tok.line, name_tok.col,
            )

        raise DSLNameError(
            f"'{name}'은 정의되지 않은 식별자입니다",
            name_tok.line, name_tok.col,
        )

    # ── 타입 검사 ──

    def _check_type(self, node: Node, expected: str, msg: str):
        actual = _infer_type(node, self._custom_funcs)
        if actual != _UNKNOWN and actual != expected:
            raise DSLTypeError(msg, node.line, node.col)


def parse(source: str) -> Script:
    """DSL 소스 → Script AST. 문법+타입 검증 포함."""
    from .lexer import tokenize

    tokens = tokenize(source)
    parser = Parser(tokens)
    return parser.parse()
