"""
전략 규칙 비즈니스 로직
"""
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from cloud_server.core.validators import validate_conditions, validate_dsl_script
from cloud_server.models.rule import TradingRule


def _rule_to_dict(rule: TradingRule) -> dict:
    """TradingRule → 응답 dict"""
    return {
        "id": rule.id,
        "user_id": rule.user_id,
        "name": rule.name,
        "symbol": rule.symbol,
        "script": rule.script,
        "buy_conditions": rule.buy_conditions,
        "sell_conditions": rule.sell_conditions,
        "execution": rule.execution,
        "trigger_policy": rule.trigger_policy,
        "priority": rule.priority,
        "order_type": rule.order_type,
        "qty": rule.qty,
        "max_position_count": rule.max_position_count,
        "budget_ratio": rule.budget_ratio,
        "parameters": rule.parameters,
        "is_active": rule.is_active,
        "version": rule.version,
        "created_at": rule.created_at.isoformat() if rule.created_at else None,
        "updated_at": rule.updated_at.isoformat() if rule.updated_at else None,
    }


def list_rules(user_id: str, db: Session) -> list[dict]:
    """사용자 규칙 목록 조회"""
    rules = db.query(TradingRule).filter(
        TradingRule.user_id == user_id
    ).order_by(TradingRule.created_at.desc()).all()
    return [_rule_to_dict(r) for r in rules]


def get_rule(rule_id: int, user_id: str, db: Session) -> dict:
    """규칙 상세 조회 (소유권 확인)"""
    rule = db.query(TradingRule).filter(
        TradingRule.id == rule_id,
        TradingRule.user_id == user_id,
    ).first()
    if not rule:
        raise HTTPException(status_code=404, detail="규칙을 찾을 수 없습니다.")
    return _rule_to_dict(rule)


def create_rule(user_id: str, data: dict, db: Session) -> dict:
    """규칙 생성"""
    # DSL 스크립트 검증 (v2)
    if data.get("script"):
        try:
            validate_dsl_script(data["script"])
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # 조건 JSON 검증 (v1 하위 호환)
    try:
        validate_conditions(data.get("buy_conditions"))
        validate_conditions(data.get("sell_conditions"))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    rule = TradingRule(
        user_id=user_id,
        name=data["name"],
        symbol=data["symbol"],
        script=data.get("script"),
        execution=data.get("execution"),
        trigger_policy=data.get("trigger_policy", {"frequency": "ONCE_PER_DAY"}),
        priority=data.get("priority", 0),
        buy_conditions=data.get("buy_conditions"),
        sell_conditions=data.get("sell_conditions"),
        order_type=data.get("order_type", "market"),
        qty=data.get("qty", 1),
        max_position_count=data.get("max_position_count", 5),
        budget_ratio=data.get("budget_ratio", 0.2),
        parameters=data.get("parameters"),
        is_active=data.get("is_active", True),
        version=1,
    )
    db.add(rule)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=409, detail="같은 이름의 규칙이 이미 존재합니다.")

    db.refresh(rule)
    return _rule_to_dict(rule)


def update_rule(rule_id: int, user_id: str, data: dict, db: Session) -> dict:
    """규칙 수정 (version 증가)"""
    rule = db.query(TradingRule).filter(
        TradingRule.id == rule_id,
        TradingRule.user_id == user_id,
    ).first()
    if not rule:
        raise HTTPException(status_code=404, detail="규칙을 찾을 수 없습니다.")

    # DSL 스크립트 검증 (v2)
    if "script" in data and data["script"]:
        try:
            validate_dsl_script(data["script"])
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # 조건 JSON 검증 (v1 하위 호환)
    if "buy_conditions" in data:
        try:
            validate_conditions(data["buy_conditions"])
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    if "sell_conditions" in data:
        try:
            validate_conditions(data["sell_conditions"])
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # 필드 업데이트
    updatable = [
        "name", "symbol", "script", "execution", "trigger_policy", "priority",
        "buy_conditions", "sell_conditions",
        "order_type", "qty", "max_position_count", "budget_ratio", "is_active",
        "parameters",
    ]
    for field in updatable:
        if field in data:
            setattr(rule, field, data[field])

    rule.version += 1
    rule.updated_at = datetime.utcnow()

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=409, detail="같은 이름의 규칙이 이미 존재합니다.")

    db.refresh(rule)
    return _rule_to_dict(rule)


def delete_rule(rule_id: int, user_id: str, db: Session) -> None:
    """규칙 삭제 (물리 삭제)"""
    rule = db.query(TradingRule).filter(
        TradingRule.id == rule_id,
        TradingRule.user_id == user_id,
    ).first()
    if not rule:
        raise HTTPException(status_code=404, detail="규칙을 찾을 수 없습니다.")

    db.delete(rule)
    db.commit()


def get_max_version(user_id: str, db: Session) -> int:
    """사용자 규칙의 최신 version 값"""
    result = db.query(func.max(TradingRule.version)).filter(
        TradingRule.user_id == user_id
    ).scalar()
    return result or 0
