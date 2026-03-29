"""
전략 규칙 CRUD API

GET    /api/v1/rules         내 규칙 목록
POST   /api/v1/rules         규칙 생성
GET    /api/v1/rules/{id}    규칙 상세
PUT    /api/v1/rules/{id}    규칙 수정
DELETE /api/v1/rules/{id}    규칙 삭제
"""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from cloud_server.api.dependencies import current_user
from cloud_server.core.database import get_db
from cloud_server.services import rule_service
from cloud_server.models.strategy_version import StrategyVersion

router = APIRouter(prefix="/api/v1/rules", tags=["rules"])


# ── Pydantic 스키마 ──────────────────────────────────────────────────


class ConditionItem(BaseModel):
    type: str      # indicator | context | price
    field: str
    operator: str  # < > <= >= == !=
    value: float


class Conditions(BaseModel):
    operator: str        # AND | OR
    conditions: list[ConditionItem]


class RuleCreateBody(BaseModel):
    name: str
    symbol: str
    # v2 DSL
    script: str | None = None
    execution: dict | None = None
    trigger_policy: dict | None = None
    priority: int = 0
    # v1 하위 호환
    buy_conditions: dict | None = None
    sell_conditions: dict | None = None
    order_type: str = "market"
    qty: int = 1
    max_position_count: int = 5
    budget_ratio: float = 0.2
    is_active: bool = True


class RuleUpdateBody(BaseModel):
    name: str | None = None
    symbol: str | None = None
    # v2 DSL
    script: str | None = None
    execution: dict | None = None
    trigger_policy: dict | None = None
    priority: int | None = None
    # v1 하위 호환
    buy_conditions: dict | None = None
    sell_conditions: dict | None = None
    order_type: str | None = None
    qty: int | None = None
    max_position_count: int | None = None
    budget_ratio: float | None = None
    is_active: bool | None = None


# ── 헬퍼 ─────────────────────────────────────────────────────────────


def _extract_dsl_metadata(script: str | None) -> tuple[dict | None, dict]:
    """DSL script에서 파라미터 + dsl_meta를 한 번에 추출.

    Returns:
        (parameters, dsl_meta) — parameters는 슬라이더용, dsl_meta는 정식 파싱 결과.
    """
    empty_meta = {"parse_status": "error", "is_v2": False, "constants": [],
                  "custom_functions": [], "rules": [], "errors": []}
    if not script:
        return None, {**empty_meta, "parse_status": "ok"}

    try:
        from sv_core.parsing import parse_v2, DSLError
        from sv_core.parsing.ast_nodes import NumberLit, StringLit
        ast = parse_v2(script)

        # parameters 추출 (상수 슬라이더용)
        params = {}
        for const in ast.consts:
            if isinstance(const.value, NumberLit):
                params[const.name] = {"type": "number", "default": const.value.value}
            elif isinstance(const.value, StringLit):
                params[const.name] = {"type": "string", "default": const.value.value}
            else:
                val = const.value
                if isinstance(val, (int, float)):
                    params[const.name] = {"type": "number", "default": val}
                elif isinstance(val, str):
                    params[const.name] = {"type": "string", "default": val}

        # dsl_meta 구성
        dsl_meta: dict = {
            "parse_status": "ok",
            "is_v2": bool(ast.rules),
            "constants": [{"name": c.name,
                          "value": c.value.value if hasattr(c.value, 'value') else
                                   (c.value if isinstance(c.value, (int, float, str)) else str(c.value))}
                          for c in ast.consts],
            "custom_functions": [{"name": f.name, "body": str(f.body)}
                                 for f in ast.custom_funcs],
            "rules": [{"index": i, "condition": str(r.condition), "side": r.action.side,
                        "qty": f"{r.action.qty_value}{'%' if r.action.qty_type == 'percent' else ''}"}
                      for i, r in enumerate(ast.rules)],
            "errors": [],
        }
        return params if params else None, dsl_meta

    except Exception as e:
        error_info = {"line": 0, "column": 0, "message": str(e)}
        if hasattr(e, "line"):
            error_info["line"] = e.line
        if hasattr(e, "col"):
            error_info["column"] = e.col
        if hasattr(e, "message"):
            error_info["message"] = e.message
        return None, {**empty_meta, "errors": [error_info]}


# ── 엔드포인트 ────────────────────────────────────────────────────────


@router.get("")
def list_rules(
    version: int | None = Query(None, description="이 버전 이상인 규칙만 반환"),
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    """내 규칙 목록 + 최신 version"""
    rules = rule_service.list_rules(user["sub"], db)
    current_version = rule_service.get_max_version(user["sub"], db)
    return {
        "success": True,
        "data": rules,
        "version": current_version,
        "count": len(rules),
    }


@router.post("", status_code=201)
def create_rule(
    body: RuleCreateBody,
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    """규칙 생성"""
    data = body.model_dump(exclude_unset=False)
    params, dsl_meta = _extract_dsl_metadata(data.get("script"))
    data["parameters"] = params
    data["dsl_meta"] = dsl_meta
    rule = rule_service.create_rule(user["sub"], data, db)
    return {"success": True, "data": rule}


@router.get("/{rule_id}")
def get_rule(
    rule_id: int,
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    """규칙 상세"""
    rule = rule_service.get_rule(rule_id, user["sub"], db)
    return {"success": True, "data": rule}


@router.put("/{rule_id}")
def update_rule(
    rule_id: int,
    body: RuleUpdateBody,
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    """규칙 수정 (version 증가)"""
    data = body.model_dump(exclude_unset=True)
    if "script" in data:
        params, dsl_meta = _extract_dsl_metadata(data.get("script"))
        data["parameters"] = params
        data["dsl_meta"] = dsl_meta
    rule = rule_service.update_rule(rule_id, user["sub"], data, db)
    return {"success": True, "data": rule}


@router.delete("/{rule_id}", status_code=200)
def delete_rule(
    rule_id: int,
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    """규칙 삭제"""
    rule_service.delete_rule(rule_id, user["sub"], db)
    return {"success": True}


# ── 전략 버전 스냅샷 ──


@router.get("/{rule_id}/versions")
def list_versions(
    rule_id: int,
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    """전략 버전 목록."""
    # 규칙 소유 확인
    rule_service.get_rule(rule_id, user["sub"], db)
    versions = (
        db.query(StrategyVersion)
        .filter(StrategyVersion.rule_id == rule_id)
        .order_by(StrategyVersion.version.desc())
        .all()
    )
    return {
        "success": True,
        "data": [
            {
                "version": v.version,
                "message": v.message,
                "created_by": v.created_by,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in versions
        ],
    }


@router.get("/{rule_id}/versions/{v1}/diff/{v2}")
def diff_versions(
    rule_id: int,
    v1: int,
    v2: int,
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    """두 버전 간 디프."""
    rule_service.get_rule(rule_id, user["sub"], db)
    ver1 = db.query(StrategyVersion).filter(
        StrategyVersion.rule_id == rule_id, StrategyVersion.version == v1,
    ).first()
    ver2 = db.query(StrategyVersion).filter(
        StrategyVersion.rule_id == rule_id, StrategyVersion.version == v2,
    ).first()
    if not ver1 or not ver2:
        raise HTTPException(404, "버전을 찾을 수 없습니다")
    return {
        "success": True,
        "data": {
            "v1": {"version": ver1.version, "script": ver1.script},
            "v2": {"version": ver2.version, "script": ver2.script},
        },
    }


@router.post("/{rule_id}/versions/{version}/restore")
def restore_version(
    rule_id: int,
    version: int,
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    """이전 버전으로 되돌리기."""
    rule_service.get_rule(rule_id, user["sub"], db)
    ver = db.query(StrategyVersion).filter(
        StrategyVersion.rule_id == rule_id, StrategyVersion.version == version,
    ).first()
    if not ver:
        raise HTTPException(404, "버전을 찾을 수 없습니다")
    # 현재 규칙의 script를 해당 버전으로 교체
    data = {"script": ver.script}
    data["parameters"] = _extract_parameters(ver.script)
    rule = rule_service.update_rule(rule_id, user["sub"], data, db)
    return {"success": True, "data": rule}
