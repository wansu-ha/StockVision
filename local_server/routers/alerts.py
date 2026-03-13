"""경고 설정 API.

GET  /api/settings/alerts  — 현재 경고 설정 반환
PUT  /api/settings/alerts  — 경고 설정 변경 (Kill Switch/손실 락 비활성화 거부)
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from local_server.config import get_config

logger = logging.getLogger(__name__)

router = APIRouter()

# 항상 ON이어야 하는 규칙 (enabled=false 변경 불가)
_PROTECTED_RULES = frozenset({"kill_switch", "loss_lock"})


@router.get("/settings/alerts")
async def get_alert_settings() -> dict[str, Any]:
    """현재 경고 설정을 반환한다."""
    cfg = get_config()
    alerts = cfg.get("alerts") or {}
    return {"success": True, "data": alerts}


@router.put("/settings/alerts")
async def update_alert_settings(body: dict[str, Any]) -> dict[str, Any]:
    """경고 설정을 변경한다.

    Kill Switch / 손실 락 규칙은 enabled=false로 변경할 수 없다.
    """
    rules = body.get("rules", {})

    # 보호된 규칙 enabled=false 거부
    for rule_name in _PROTECTED_RULES:
        if rule_name in rules:
            rule_val = rules[rule_name]
            if isinstance(rule_val, dict) and rule_val.get("enabled") is False:
                raise HTTPException(
                    status_code=400,
                    detail=f"'{rule_name}' 경고는 비활성화할 수 없습니다.",
                )

    cfg = get_config()
    current = cfg.get("alerts") or {}

    # 보호된 규칙은 병합 시 enabled=true 강제
    merged_rules = dict(current.get("rules", {}))
    for k, v in rules.items():
        if k in _PROTECTED_RULES:
            merged_rules[k] = {**v, "enabled": True}
        else:
            merged_rules[k] = v

    updated: dict[str, Any] = {
        "master_enabled": body.get("master_enabled", current.get("master_enabled", True)),
        "rules": merged_rules,
    }

    cfg.set("alerts", updated)
    cfg.save()

    logger.info("경고 설정 변경: master_enabled=%s", updated["master_enabled"])
    return {"success": True, "data": updated}
