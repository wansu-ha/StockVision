"""
조건 검증

- validate_conditions: v1 JSON 조건 형식 검증
- validate_dsl_script: v2 DSL 스크립트 파싱 검증
"""

VALID_OPERATORS = {"AND", "OR"}
VALID_TYPES = {"indicator", "context", "price"}
VALID_FIELD_OPERATORS = {"<", ">", "<=", ">=", "==", "!="}


def validate_conditions(conditions: dict | None) -> None:
    """
    조건 JSON 형식 검증. 무효 시 ValueError 발생.

    형식:
    {
      "operator": "AND" | "OR",
      "conditions": [
        {
          "type": "indicator" | "context" | "price",
          "field": "rsi_14" | "market_kospi_rsi" | "current_price",
          "operator": "<=" | ">=" | "==" | "!=" | "<" | ">",
          "value": number
        }
      ]
    }
    """
    if conditions is None:
        return  # 조건 없음 허용

    if not isinstance(conditions, dict):
        raise ValueError("conditions는 dict 형식이어야 합니다.")

    if conditions.get("operator") not in VALID_OPERATORS:
        raise ValueError(f"operator는 {VALID_OPERATORS} 중 하나여야 합니다.")

    items = conditions.get("conditions")
    if not isinstance(items, list):
        raise ValueError("conditions.conditions는 list 형식이어야 합니다.")

    for i, cond in enumerate(items):
        if not isinstance(cond, dict):
            raise ValueError(f"conditions[{i}]는 dict 형식이어야 합니다.")

        if cond.get("type") not in VALID_TYPES:
            raise ValueError(f"conditions[{i}].type은 {VALID_TYPES} 중 하나여야 합니다.")

        if cond.get("operator") not in VALID_FIELD_OPERATORS:
            raise ValueError(f"conditions[{i}].operator는 {VALID_FIELD_OPERATORS} 중 하나여야 합니다.")

        if not isinstance(cond.get("field"), str) or not cond.get("field"):
            raise ValueError(f"conditions[{i}].field는 비어있지 않은 문자열이어야 합니다.")

        value = cond.get("value")
        if not isinstance(value, (int, float)):
            raise ValueError(f"conditions[{i}].value는 숫자여야 합니다.")


def validate_dsl_script(script: str) -> None:
    """DSL 스크립트 파싱 검증. 무효 시 ValueError (위치+메시지)."""
    from sv_core.parsing import parse, DSLError

    try:
        parse(script)
    except DSLError as e:
        raise ValueError(f"[{e.line}:{e.col}] {e.message}") from e
