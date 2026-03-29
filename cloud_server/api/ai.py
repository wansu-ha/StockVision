"""
AI 분석 API

GET /api/v1/ai/analysis/{symbol}        종목 AI 분석 (온디맨드, AIService)
GET /api/v1/ai/status                   AI 모듈 상태
GET /api/v1/ai/history                  분석 이력 (어드민)
GET /api/v1/ai/briefing                 시장 브리핑
GET /api/v1/ai/stock-analysis/{symbol}  종목별 일일 분석 (StockAnalysisService)
POST /api/v1/ai/chat                    AI 대화 (SSE 스��리밍)
GET  /api/v1/ai/conversations           대화 목록
GET  /api/v1/ai/conversations/{id}      대화 상세
DELETE /api/v1/ai/conversations/{id}    대화 삭제
GET  /api/v1/ai/credit                  크레딧 잔량
POST /api/v1/ai/apikey                  BYO API Key 등록
DELETE /api/v1/ai/apikey                BYO API Key 삭제
"""
import asyncio
import json
from datetime import date as date_
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from cloud_server.api.dependencies import current_user, require_admin
from cloud_server.core.database import get_db
from cloud_server.core.rate_limit import check_ai_rate
from cloud_server.models.ai import AIAnalysisLog
from cloud_server.services.ai_service import AIService
from cloud_server.services.briefing_service import BriefingService
from cloud_server.services.stock_analysis_service import StockAnalysisService
from cloud_server.services.ai_chat_service import AIChatService
from cloud_server.services.credit_service import CreditService

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])

_VALID_TYPES = {"sentiment", "summary", "risk", "technical"}


def _parse_date(date_str: str | None) -> date_ | None:
    """YYYY-MM-DD 문자열 → date 변환. 실패 시 None."""
    if not date_str:
        return None
    try:
        return date_.fromisoformat(date_str)
    except ValueError:
        return None


@router.get("/analysis/{symbol}")
def analyze(
    symbol: str,
    type: str = Query("summary"),
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    """종목 AI 분석"""
    check_ai_rate(user["sub"])
    if type not in _VALID_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"유효하지 않은 분석 유형: {type}. 가능한 값: {', '.join(sorted(_VALID_TYPES))}",
        )
    service = AIService(db)
    result = service.analyze(symbol, type, user["sub"])
    return {"success": True, "data": result}


@router.get("/status")
def status(user: dict = Depends(current_user)):
    """AI 모듈 상태"""
    service = AIService.__new__(AIService)
    return {"success": True, "data": service.get_status()}


@router.get("/history")
def history(
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    _admin: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """분석 이력 조회 (어드민 전용)"""
    total = db.query(AIAnalysisLog).count()
    items = (
        db.query(AIAnalysisLog)
        .order_by(AIAnalysisLog.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "success": True,
        "data": {
            "items": [
                {
                    "id": log.id,
                    "symbol": log.symbol,
                    "type": log.type,
                    "source": log.source,
                    "score": log.score,
                    "token_input": log.token_input,
                    "token_output": log.token_output,
                    "model": log.model,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
                for log in items
            ],
            "total": total,
        },
    }


@router.get("/briefing")
def get_briefing(
    date_str: str | None = Query(None, alias="date", description="YYYY-MM-DD, 기본값: 오늘"),
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    """시장 브리핑 조회 (캐시 우선, 없으면 생성)"""
    target = _parse_date(date_str) or date_.today()
    service = BriefingService()
    result = service.get_briefing(target, db)
    return {"success": True, "data": result}


@router.get("/stock-analysis/{symbol}")
def stock_analysis(
    symbol: str,
    date_str: str | None = Query(None, alias="date", description="YYYY-MM-DD, 기본값: 오늘"),
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    """종목별 일일 AI 분석 (오늘: 캐시→DB→온디맨드, 과거: DB only)"""
    target = _parse_date(date_str) or date_.today()
    service = StockAnalysisService()
    result = service.get_analysis(symbol, target, db)
    return {"success": True, "data": result}


# ── AI 대화 (코파일럿 + 비서) ──


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    message: str
    current_dsl: str | None = None
    mode: str = "builder"  # builder | assistant
    thinking: bool = False
    context: dict | None = None  # 프론트에서 주입하는 로컬 데이터 (assistant 모드)


@router.post("/chat")
async def chat(
    body: ChatRequest,
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    """AI 대화 — SSE 스트리밍 응답."""
    service = AIChatService(db)

    async def generate():
        async for event in service.chat(
            conversation_id=body.conversation_id,
            message=body.message,
            current_dsl=body.current_dsl,
            mode=body.mode,
            thinking=body.thinking,
            user_id=user["sub"],
            context=body.context,
        ):
            yield f"event: {event['event']}\ndata: {json.dumps(event['data'], ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/conversations")
def list_conversations(
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    """대화 목록."""
    service = AIChatService(db)
    return {"success": True, "data": service.list_conversations(user["sub"])}


@router.get("/conversations/{conv_id}")
def get_conversation(
    conv_id: str,
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    """대화 상세."""
    service = AIChatService(db)
    result = service.get_conversation(conv_id, user["sub"])
    if not result:
        raise HTTPException(404, "대화를 찾을 수 없습니다")
    return {"success": True, "data": result}


@router.delete("/conversations/{conv_id}")
def delete_conversation(
    conv_id: str,
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    """대화 삭제."""
    service = AIChatService(db)
    if not service.delete_conversation(conv_id, user["sub"]):
        raise HTTPException(404, "대화를 찾을 수 없습니다")
    return {"success": True}


@router.get("/credit")
def get_credit(
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    """크레딧 잔량."""
    service = CreditService(db)
    return {"success": True, "data": service.get_balance(user["sub"])}


class ApiKeyRequest(BaseModel):
    api_key: str


@router.post("/apikey")
def register_api_key(
    body: ApiKeyRequest,
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    """BYO API Key 등록."""
    service = CreditService(db)
    service.register_byo_key(user["sub"], body.api_key)
    db.commit()
    return {"success": True}


@router.delete("/apikey")
def delete_api_key(
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    """BYO API Key 삭제."""
    service = CreditService(db)
    if not service.delete_byo_key(user["sub"]):
        raise HTTPException(404, "등록된 API 키가 없습니다")
    db.commit()
    return {"success": True}
