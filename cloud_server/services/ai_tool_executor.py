"""비서 tool 실행기 — Claude tool_use 결과를 반환한다.

클라우드 직접 호출 tool: list_rules, get_rule, update_rule_dsl, get_backtest_result
프론트 컨텍스트 기반 tool: get_execution_logs, get_daily_pnl, get_positions
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Claude tool_use 스키마 정의
ASSISTANT_TOOLS = [
    {
        "name": "list_rules",
        "description": "사용자의 전체 전략 규칙 목록을 조회합니다.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_rule",
        "description": "특정 규칙의 DSL 스크립트와 설정을 조회합니다.",
        "input_schema": {
            "type": "object",
            "properties": {"rule_id": {"type": "integer", "description": "규칙 ID"}},
            "required": ["rule_id"],
        },
    },
    {
        "name": "update_rule_dsl",
        "description": "규칙의 DSL 스크립트를 수정합니다. 새 버전이 생성됩니다.",
        "input_schema": {
            "type": "object",
            "properties": {
                "rule_id": {"type": "integer", "description": "규칙 ID"},
                "script": {"type": "string", "description": "수정된 DSL 스크립트"},
            },
            "required": ["rule_id", "script"],
        },
    },
    {
        "name": "get_backtest_result",
        "description": "특정 규칙의 최근 백테스트 결과를 조회합니다.",
        "input_schema": {
            "type": "object",
            "properties": {"rule_id": {"type": "integer", "description": "규칙 ID"}},
            "required": ["rule_id"],
        },
    },
    {
        "name": "get_execution_logs",
        "description": "실행 로그를 조회합니다 (프론트에서 주입한 컨텍스트 기반).",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_daily_pnl",
        "description": "오늘의 일일 P&L (실현 손익, 승률)을 조회합니다.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_positions",
        "description": "현재 보유 종목과 잔고를 조회합니다.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]


def execute_tool(
    tool_name: str,
    tool_input: dict[str, Any],
    user_id: str,
    db: Session,
    context: dict[str, Any] | None = None,
) -> str:
    """tool 실행 → JSON 문자열 반환."""
    import json

    ctx = context or {}

    try:
        if tool_name == "list_rules":
            return _list_rules(user_id, db)
        elif tool_name == "get_rule":
            return _get_rule(tool_input["rule_id"], user_id, db)
        elif tool_name == "update_rule_dsl":
            return _update_rule_dsl(tool_input["rule_id"], tool_input["script"], user_id, db)
        elif tool_name == "get_backtest_result":
            return _get_backtest_result(tool_input["rule_id"], user_id, db)
        elif tool_name == "get_execution_logs":
            return json.dumps(ctx.get("execution_logs", {"message": "실행 로그 데이터 없음"}), ensure_ascii=False)
        elif tool_name == "get_daily_pnl":
            return json.dumps(ctx.get("daily_pnl", {"message": "P&L 데이터 없음"}), ensure_ascii=False)
        elif tool_name == "get_positions":
            return json.dumps(ctx.get("positions", {"message": "포지션 데이터 없음"}), ensure_ascii=False)
        else:
            return json.dumps({"error": f"알 수 없는 tool: {tool_name}"}, ensure_ascii=False)
    except Exception as e:
        logger.error("tool 실행 실패: %s — %s", tool_name, e)
        return json.dumps({"error": str(e)}, ensure_ascii=False)


def _list_rules(user_id: str, db: Session) -> str:
    import json
    from cloud_server.models.rule import TradingRule

    rules = db.query(TradingRule).filter(
        TradingRule.user_id == user_id,
    ).all()
    result = [
        {"id": r.id, "name": r.name, "symbol": r.symbol, "is_active": r.is_active, "script_preview": (r.script or "")[:100]}
        for r in rules
    ]
    return json.dumps(result, ensure_ascii=False)


def _get_rule(rule_id: int, user_id: str, db: Session) -> str:
    import json
    from cloud_server.models.rule import TradingRule

    rule = db.query(TradingRule).filter(
        TradingRule.id == rule_id,
        TradingRule.user_id == user_id,
    ).first()
    if not rule:
        return json.dumps({"error": "규칙을 찾을 수 없습니다"}, ensure_ascii=False)
    return json.dumps({
        "id": rule.id, "name": rule.name, "symbol": rule.symbol,
        "is_active": rule.is_active, "script": rule.script,
        "priority": rule.priority, "version": rule.version,
    }, ensure_ascii=False)


def _update_rule_dsl(rule_id: int, script: str, user_id: str, db: Session) -> str:
    import json
    from cloud_server.models.rule import TradingRule

    rule = db.query(TradingRule).filter(
        TradingRule.id == rule_id,
        TradingRule.user_id == user_id,
    ).first()
    if not rule:
        return json.dumps({"error": "규칙을 찾을 수 없습니다"}, ensure_ascii=False)

    # DSL 파싱 검증
    try:
        from sv_core.parsing.parser import parse_v2
        parse_v2(script)
    except Exception as e:
        return json.dumps({"error": f"DSL 문법 오류: {e}"}, ensure_ascii=False)

    rule.script = script
    rule.version = (rule.version or 0) + 1
    db.commit()

    return json.dumps({"success": True, "version": rule.version, "message": f"규칙 '{rule.name}' DSL 수정 완료 (v{rule.version})"}, ensure_ascii=False)


def _get_backtest_result(rule_id: int, user_id: str, db: Session) -> str:
    import json
    from cloud_server.models.backtest import BacktestExecution

    result = db.query(BacktestExecution).filter(
        BacktestExecution.rule_id == rule_id,
        BacktestExecution.user_id == user_id,
    ).order_by(BacktestExecution.executed_at.desc()).first()

    if not result:
        return json.dumps({"message": "백테스트 결과가 없습니다"}, ensure_ascii=False)

    return json.dumps({
        "rule_id": result.rule_id,
        "symbol": result.symbol,
        "timeframe": result.timeframe,
        "executed_at": result.executed_at.isoformat(),
        "summary": result.summary,
    }, ensure_ascii=False)
