from fastapi import APIRouter, Query
from storage.log_db import query_logs, query_summary_today

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("")
def get_logs(
    rule_id:   int | None = Query(None),
    date_from: str | None = Query(None),
    date_to:   str | None = Query(None),
    limit:     int        = Query(100, ge=1, le=500),
    offset:    int        = Query(0, ge=0),
):
    data = query_logs(
        rule_id=rule_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return {"success": True, "data": data, "count": len(data)}


@router.get("/summary")
def get_summary():
    return {"success": True, "data": query_summary_today()}
