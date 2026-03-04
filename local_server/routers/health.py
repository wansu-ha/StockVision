from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/api/health")
def health():
    return {"status": "ok"}


@router.get("/api/dashboard")
def dashboard():
    from kiwoom.session import get_session
    from storage.config_manager import get_config_manager
    from storage.log_db import query_summary_today, query_logs
    from cloud.context import get_context

    session = get_session()
    cm      = get_config_manager()
    rules   = cm.get("rules", [])
    active  = sum(1 for r in rules if r.get("is_active"))

    today   = query_summary_today()
    ctx     = get_context()
    market  = ctx.get("market", {})

    recent = query_logs(limit=5)

    return {
        "success": True,
        "data": {
            "bridge_connected": True,
            "kiwoom_mode":      session.mode,
            "kiwoom_connected": session.connected,
            "active_rules":     active,
            "today":            today,
            "market_context":   {
                "kospi_rsi_14": market.get("kospi_rsi_14"),
                "trend":        market.get("market_trend"),
            },
            "recent_logs": recent,
        },
    }
