"""
전략 규칙 CRUD API

GET    /api/v1/rules         내 규칙 목록
POST   /api/v1/rules         규칙 생성
GET    /api/v1/rules/{id}    규칙 상세
PUT    /api/v1/rules/{id}    규칙 수정
DELETE /api/v1/rules/{id}    규칙 삭제
"""
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from cloud_server.api.dependencies import current_user
from cloud_server.core.database import get_db
from cloud_server.services import rule_service

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
