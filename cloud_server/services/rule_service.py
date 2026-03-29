"""
전략 규칙 비즈니스 로직
"""
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from cloud_server.core.validators import validate_conditions
from cloud_server.models.rule import TradingRule
from cloud_server.models.strategy_version import StrategyVersion


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
        "dsl_meta": rule.dsl_meta,
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
    # DSL 파싱은 라우터의 _extract_dsl_metadata()에서 완료 → dsl_meta로 판단
    dsl_meta = data.get("dsl_meta")
    if dsl_meta and dsl_meta.get("parse_status") == "error":
        # 파싱 실패한 스크립트도 저장 허용하되 강제 비활성화
        data["is_active"] = False

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
        dsl_meta=data.get("dsl_meta"),
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

    # 초기 버전 스냅샷
    if rule.script:
        _create_version_snapshot(rule.id, rule.script, "초기 생성", "user", db)

    return _rule_to_dict(rule)


def update_rule(rule_id: int, user_id: str, data: dict, db: Session) -> dict:
    """규칙 수정 (version 증가)"""
    rule = db.query(TradingRule).filter(
        TradingRule.id == rule_id,
        TradingRule.user_id == user_id,
    ).first()
    if not rule:
        raise HTTPException(status_code=404, detail="규칙을 찾을 수 없습니다.")

    # DSL 파싱은 라우터의 _extract_dsl_metadata()에서 완료 → dsl_meta로 판단
    dsl_meta = data.get("dsl_meta")
    if dsl_meta and dsl_meta.get("parse_status") == "error":
        # script 수정으로 파싱 실패 → 강제 비활성화
        data["is_active"] = False
    if "is_active" in data and data["is_active"] is True:
        # 활성화 요청 시 parse_status 체크
        current_meta = dsl_meta or (rule.dsl_meta if rule.dsl_meta else None)
        if current_meta and current_meta.get("parse_status") == "error":
            raise HTTPException(status_code=400, detail="파싱 오류가 있는 규칙은 활성화할 수 없습니다.")

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
        "parameters", "dsl_meta",
    ]
    for field in updatable:
        if field in data:
            setattr(rule, field, data[field])

    # script 변경 시 버전 스냅샷
    script_changed = "script" in data and data["script"] != rule.script

    rule.version += 1
    rule.updated_at = datetime.utcnow()

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=409, detail="같은 이름의 규칙이 이미 존재합니다.")

    db.refresh(rule)

    if script_changed and rule.script:
        _create_version_snapshot(rule.id, rule.script, "수정", "user", db)

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


def _create_version_snapshot(
    rule_id: int, script: str, message: str, created_by: str, db: Session,
) -> None:
    """전략 버전 스냅샷 생성."""
    max_ver = db.query(func.max(StrategyVersion.version)).filter(
        StrategyVersion.rule_id == rule_id,
    ).scalar() or 0
    sv = StrategyVersion(
        rule_id=rule_id,
        version=max_ver + 1,
        script=script,
        message=message,
        created_by=created_by,
    )
    db.add(sv)
    db.commit()


def get_max_version(user_id: str, db: Session) -> int:
    """사용자 규칙의 최신 version 값"""
    result = db.query(func.max(TradingRule.version)).filter(
        TradingRule.user_id == user_id
    ).scalar()
    return result or 0
