from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["config"])


class UnlockBody(BaseModel):
    jwt: str


@router.get("/config")
def get_config():
    from storage.config_manager import get_config_manager
    return {"success": True, "data": get_config_manager().get_all()}


@router.patch("/config")
def patch_config(patch: dict):
    from storage.config_manager import get_config_manager
    get_config_manager().update(patch)
    return {"success": True}


@router.post("/config/unlock")
async def unlock(body: UnlockBody):
    """React 로그인 후 JWT 전달 → 설정 로드"""
    from cloud.auth_client import AuthClient
    from storage.config_manager import get_config_manager
    from routers.ws import broadcast

    try:
        auth = AuthClient()
        cloud_config = auth.get_config(body.jwt)
        get_config_manager().load(cloud_config, jwt=body.jwt)
        await broadcast({"type": "config_loaded", "data": {}})
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── 규칙 CRUD ────────────────────────────────────────────────

class RuleBody(BaseModel):
    name:       str
    stock_code: str
    side:       str
    conditions: list
    quantity:   int
    is_active:  bool = True


@router.get("/rules")
def get_rules():
    from storage.config_manager import get_config_manager
    rules = get_config_manager().get("rules", [])
    return {"success": True, "data": rules, "count": len(rules)}


@router.post("/rules")
def create_rule(body: RuleBody):
    from storage.config_manager import get_config_manager
    cm = get_config_manager()
    rules = list(cm.get("rules", []))
    new_id = max((r.get("id", 0) for r in rules), default=0) + 1
    rule = {"id": new_id, **body.model_dump()}
    rules.append(rule)
    cm.update({"rules": rules})
    return {"success": True, "data": rule}


@router.put("/rules/{rule_id}")
def update_rule(rule_id: int, body: RuleBody):
    from storage.config_manager import get_config_manager
    cm = get_config_manager()
    rules = list(cm.get("rules", []))
    for i, r in enumerate(rules):
        if r.get("id") == rule_id:
            rules[i] = {"id": rule_id, **body.model_dump()}
            cm.update({"rules": rules})
            return {"success": True, "data": rules[i]}
    raise HTTPException(status_code=404, detail="규칙 없음")


@router.delete("/rules/{rule_id}")
def delete_rule(rule_id: int):
    from storage.config_manager import get_config_manager
    cm = get_config_manager()
    rules = [r for r in cm.get("rules", []) if r.get("id") != rule_id]
    cm.update({"rules": rules})
    return {"success": True}


@router.patch("/rules/{rule_id}/toggle")
def toggle_rule(rule_id: int):
    from storage.config_manager import get_config_manager
    cm = get_config_manager()
    rules = list(cm.get("rules", []))
    for r in rules:
        if r.get("id") == rule_id:
            r["is_active"] = not r.get("is_active", True)
            cm.update({"rules": rules})
            return {"success": True, "data": {"is_active": r["is_active"]}}
    raise HTTPException(status_code=404, detail="규칙 없음")


# ── 변수 목록 API ────────────────────────────────────────────

_OPERATORS = [">", "<", ">=", "<=", "=="]
_MARKET_VARS = [
    "kospi_rsi_14", "kospi_20d_volatility",
    "kosdaq_rsi_14", "market_trend",
]
_PRICE_VARS = ["price"]


@router.get("/variables")
def get_variables():
    from cloud.context import get_context
    ctx_market = get_context().get("market", {})
    # 현재 값 포함
    market = [
        {"key": k, "label": k, "current": ctx_market.get(k)}
        for k in _MARKET_VARS
    ]
    price = [{"key": k, "label": k, "current": None} for k in _PRICE_VARS]
    return {
        "success": True,
        "data": {
            "market":    market,
            "price":     price,
            "operators": _OPERATORS,
        },
    }
