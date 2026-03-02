from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import pandas as pd
import logging

from app.core.database import get_db
from app.models.stock import Stock, StockPrice, TechnicalIndicator
from app.services.technical_indicators import TechnicalIndicatorCalculator
from app.services.stock_list_service import StockListService
from app.services.stock_data_service import StockDataService
from app.services.data_collector import DataCollector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stocks", tags=["stocks"])

# 서비스 인스턴스 직접 생성
stock_list_service = StockListService()
stock_data_service = StockDataService()


class RegisterRequest(BaseModel):
    symbols: List[str]
    days: int = 730


@router.post("/register")
async def register_stocks(request: RegisterRequest):
    """종목 등록 — yfinance에서 정보/가격 수집 + 기술적 지표 계산"""
    if not request.symbols:
        raise HTTPException(status_code=400, detail="symbols 목록이 비어있습니다")
    if len(request.symbols) > 20:
        raise HTTPException(status_code=400, detail="한 번에 최대 20개 종목까지 등록 가능합니다")

    try:
        collector = DataCollector()
        results = await collector.register_stocks(request.symbols, request.days)

        # 캐시 갱신
        stock_list_service.refresh_cache()

        return {
            "success": True,
            "data": results,
            "count": len(results['registered'])
        }
    except Exception as e:
        logger.error(f"종목 등록 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"종목 등록 실패: {str(e)}")


@router.get("/")
async def get_stocks():
    """등록된 모든 주식 목록 조회 (메모리 캐싱 적용)"""
    import time
    start_time = time.time()
    
    try:
        stocks = stock_list_service.get_stock_list()
        process_time = time.time() - start_time
        
        # 응답 시간이 1초 이상이면 로그 기록
        if process_time > 1.0:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"느린 주식 목록 조회: {process_time:.3f}초")
        
        return {
            "success": True,
            "data": stocks,
            "count": len(stocks),
            "process_time": f"{process_time:.3f}s"
        }
    except Exception as e:
        process_time = time.time() - start_time
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"주식 목록 조회 실패 ({process_time:.3f}초): {str(e)}")
        raise HTTPException(status_code=500, detail=f"주식 목록 조회 실패: {str(e)}")

@router.get("/{symbol}")
async def get_stock_detail(symbol: str, db: Session = Depends(get_db)):
    """특정 주식 상세 정보 조회"""
    try:
        stock = db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
        if not stock:
            raise HTTPException(status_code=404, detail=f"주식을 찾을 수 없습니다: {symbol}")
        
        return {
            "success": True,
            "data": {
                "id": stock.id,
                "symbol": stock.symbol,
                "name": stock.name,
                "sector": stock.sector,
                "industry": stock.industry,
                "market_cap": stock.market_cap,
                "created_at": stock.created_at,
                "updated_at": stock.updated_at
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"주식 상세 정보 조회 실패: {str(e)}")

@router.get("/{symbol}/prices")
async def get_stock_prices(
    symbol: str,
    days: int = Query(30, ge=1, le=365, description="조회할 일수")
):
    """주식 가격 데이터 조회 (메모리 캐싱 + DB 캐싱)"""
    try:
        # 캐싱 서비스를 통한 데이터 조회
        data = stock_data_service.get_stock_data(symbol.upper(), days)
        
        if not data or len(data) == 0:
            raise HTTPException(status_code=404, detail=f"주식 데이터를 찾을 수 없습니다: {symbol}")
        
        return {
            "success": True,
            "data": data
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"가격 데이터 조회 실패: {str(e)}")

@router.get("/{symbol}/indicators")
async def get_stock_indicators(
    symbol: str,
    indicator_type: Optional[str] = Query(None, description="지표 타입 (RSI, EMA, MACD 등)"),
    days: int = Query(30, ge=1, le=365, description="조회할 일수"),
    db: Session = Depends(get_db)
):
    """주식 기술적 지표 조회"""
    try:
        # 주식 ID 조회
        stock = db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
        if not stock:
            raise HTTPException(status_code=404, detail=f"주식을 찾을 수 없습니다: {symbol}")
        
        # 지표 데이터 조회
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        query = db.query(TechnicalIndicator).filter(
            TechnicalIndicator.stock_id == stock.id,
            TechnicalIndicator.date >= start_date
        )
        
        if indicator_type:
            query = query.filter(TechnicalIndicator.indicator_type == indicator_type.upper())
        
        indicators = query.order_by(TechnicalIndicator.date).all()
        
        # 지표별로 그룹화
        indicators_by_type = {}
        for indicator in indicators:
            if indicator.indicator_type not in indicators_by_type:
                indicators_by_type[indicator.indicator_type] = []
            
            indicators_by_type[indicator.indicator_type].append({
                "date": indicator.date.strftime("%Y-%m-%d"),
                "value": indicator.value,
                "parameters": indicator.parameters
            })
        
        return {
            "success": True,
            "data": {
                "symbol": stock.symbol,
                "name": stock.name,
                "indicators": indicators_by_type
            },
            "count": len(indicators)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"기술적 지표 조회 실패: {str(e)}")

@router.get("/{symbol}/summary")
async def get_stock_summary(symbol: str):
    """주식 요약 정보 조회 (메모리 캐싱 적용)"""
    try:
        # 캐싱 서비스를 통한 요약 정보 조회
        summary = stock_data_service.get_stock_summary(symbol.upper())
        
        if not summary:
            raise HTTPException(status_code=404, detail=f"주식 요약 정보를 찾을 수 없습니다: {symbol}")
        
        return {
            "success": True,
            "data": summary
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"주식 요약 정보 조회 실패: {str(e)}")

@router.get("/cache/status")
async def get_cache_status():
    """캐시 상태 정보 조회"""
    try:
        return {
            "success": True,
            "data": {
                "stock_list_cache": stock_list_service.get_cache_info(),
                "stock_data_cache": stock_data_service.get_cache_info(),
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"캐시 상태 조회 실패: {str(e)}")

@router.post("/cache/refresh")
async def refresh_cache():
    """전체 캐시 강제 갱신"""
    try:
        # 주식 목록 캐시 갱신
        stock_list_refreshed = stock_list_service.refresh_cache()
        
        # 가격 데이터 캐시 정리
        stock_data_service.clear_cache()
        
        return {
            "success": True,
            "data": {
                "stock_list_cache_refreshed": stock_list_refreshed,
                "stock_data_cache_cleared": True,
                "message": "캐시 갱신 완료",
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"캐시 갱신 실패: {str(e)}")

@router.post("/cache/refresh/{symbol}")
async def refresh_stock_cache(symbol: str):
    """특정 주식의 캐시만 갱신"""
    try:
        # 해당 주식의 가격 데이터 캐시만 정리
        stock_data_service.clear_cache(symbol.upper())
        
        return {
            "success": True,
            "data": {
                "symbol": symbol.upper(),
                "cache_cleared": True,
                "message": f"{symbol} 주식 캐시 갱신 완료",
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"주식 캐시 갱신 실패: {str(e)}")
