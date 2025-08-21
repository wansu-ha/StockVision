from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import pandas as pd

from app.core.database import get_db
from app.models.stock import Stock, StockPrice, TechnicalIndicator
from app.services.technical_indicators import TechnicalIndicatorCalculator

router = APIRouter(prefix="/stocks", tags=["stocks"])

@router.get("/")
async def get_stocks(db: Session = Depends(get_db)):
    """등록된 모든 주식 목록 조회"""
    try:
        stocks = db.query(Stock).all()
        return {
            "success": True,
            "data": [
                {
                    "id": stock.id,
                    "symbol": stock.symbol,
                    "name": stock.name,
                    "sector": stock.sector,
                    "industry": stock.industry,
                    "market_cap": stock.market_cap
                }
                for stock in stocks
            ],
            "count": len(stocks)
        }
    except Exception as e:
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
    days: int = Query(30, ge=1, le=365, description="조회할 일수"),
    db: Session = Depends(get_db)
):
    """주식 가격 데이터 조회"""
    try:
        # 주식 ID 조회
        stock = db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
        if not stock:
            raise HTTPException(status_code=404, detail=f"주식을 찾을 수 없습니다: {symbol}")
        
        # 가격 데이터 조회
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        prices = db.query(StockPrice).filter(
            StockPrice.stock_id == stock.id,
            StockPrice.date >= start_date
        ).order_by(StockPrice.date).all()
        
        return {
            "success": True,
            "data": {
                "symbol": stock.symbol,
                "name": stock.name,
                "prices": [
                    {
                        "date": price.date.strftime("%Y-%m-%d"),
                        "open": price.open,
                        "high": price.high,
                        "low": price.low,
                        "close": price.close,
                        "volume": price.volume
                    }
                    for price in prices
                ]
            },
            "count": len(prices)
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
async def get_stock_summary(symbol: str, db: Session = Depends(get_db)):
    """주식 요약 정보 조회 (가격 + 지표)"""
    try:
        # 주식 ID 조회
        stock = db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
        if not stock:
            raise HTTPException(status_code=404, detail=f"주식을 찾을 수 없습니다: {symbol}")
        
        # 최신 가격 데이터
        latest_price = db.query(StockPrice).filter(
            StockPrice.stock_id == stock.id
        ).order_by(StockPrice.date.desc()).first()
        
        # 최신 기술적 지표들
        latest_indicators = db.query(TechnicalIndicator).filter(
            TechnicalIndicator.stock_id == stock.id
        ).order_by(TechnicalIndicator.date.desc()).all()
        
        # 지표별 최신 값
        current_indicators = {}
        for indicator in latest_indicators:
            if indicator.indicator_type not in current_indicators:
                current_indicators[indicator.indicator_type] = indicator.value
        
        return {
            "success": True,
            "data": {
                "symbol": stock.symbol,
                "name": stock.name,
                "sector": stock.sector,
                "industry": stock.industry,
                "latest_price": {
                    "date": latest_price.date.strftime("%Y-%m-%d") if latest_price else None,
                    "close": latest_price.close if latest_price else None,
                    "volume": latest_price.volume if latest_price else None
                } if latest_price else None,
                "current_indicators": current_indicators
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"주식 요약 정보 조회 실패: {str(e)}")
