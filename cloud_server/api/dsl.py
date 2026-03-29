"""
DSL 스키마 API

GET /api/v1/dsl/schema   DSL 내장 필드/함수/패턴 스키마 반환 (인증 불필요)
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from sv_core.parsing.builtins import to_schema

router = APIRouter(prefix="/api/v1/dsl", tags=["dsl"])


@router.get("/schema")
def get_dsl_schema():
    """DSL 스키마 반환 — 내장 필드, 함수, 패턴 목록."""
    return JSONResponse(
        content={"success": True, "data": to_schema()},
        headers={"Cache-Control": "public, max-age=86400"},
    )
