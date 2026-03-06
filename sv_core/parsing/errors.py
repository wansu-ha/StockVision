"""DSL 파싱/타입 에러 — 위치(line, col) + 한국어 메시지."""


class DSLError(Exception):
    """DSL 에러 기반 클래스."""

    def __init__(self, message: str, line: int = 0, col: int = 0):
        self.message = message
        self.line = line
        self.col = col
        super().__init__(f"[{line}:{col}] {message}")


class DSLSyntaxError(DSLError):
    """문법 오류 (렉서/파서)."""


class DSLTypeError(DSLError):
    """타입 제약 위반 (타입 체커)."""


class DSLNameError(DSLError):
    """미정의 식별자 또는 이름 충돌."""


class DSLRuntimeError(DSLError):
    """평가 시 런타임 에러 (null 전파 등)."""
