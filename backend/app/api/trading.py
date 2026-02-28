"""
가상 거래 API 라우터

계좌, 주문, 포지션, 거래 내역, 스코어링, 백테스팅, 자동매매 규칙
모든 응답: { success, data, count }
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.models.auto_trading import AutoTradingRule
from app.services.trading_engine import TradingEngine
from app.services.scoring_engine import ScoringEngine
from app.services.backtest_engine import BacktestEngine

router = APIRouter(prefix="/trading", tags=["trading"])


# ── 요청 스키마 ──

class AccountCreate(BaseModel):
    name: str
    initial_balance: float = 10_000_000.0

class OrderCreate(BaseModel):
    account_id: int
    stock_id: int
    symbol: str
    trade_type: str  # BUY or SELL
    quantity: int
    price: float

class BacktestRequest(BaseModel):
    strategy_name: str = "기본 스코어링 전략"
    start_date: str  # YYYY-MM-DD
    end_date: str
    initial_balance: float = 10_000_000.0
    buy_threshold: float = 70.0
    sell_threshold: float = 30.0
    max_positions: int = 5
    budget_ratio: float = 0.7

class RuleCreate(BaseModel):
    name: str
    strategy_type: str = "scoring"
    account_id: Optional[int] = None
    buy_score_threshold: float = 70.0
    max_position_count: int = 5
    budget_ratio: float = 0.7
    schedule_buy: Optional[str] = None
    schedule_sell: Optional[str] = None
    parameters: Optional[dict] = None

class RuleUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    buy_score_threshold: Optional[float] = None
    max_position_count: Optional[int] = None
    budget_ratio: Optional[float] = None
    schedule_buy: Optional[str] = None
    schedule_sell: Optional[str] = None
    parameters: Optional[dict] = None


# ── 계좌 API ──

@router.post("/accounts")
async def create_account(req: AccountCreate, db: Session = Depends(get_db)):
    """가상 계좌 생성"""
    engine = TradingEngine(db)
    account = engine.create_account(req.name, req.initial_balance)
    return {
        "success": True,
        "data": {
            "id": account.id,
            "name": account.name,
            "initial_balance": account.initial_balance,
            "current_balance": account.current_balance,
            "created_at": str(account.created_at),
        },
        "count": 1,
    }

@router.get("/accounts")
async def list_accounts(db: Session = Depends(get_db)):
    """계좌 목록 조회"""
    engine = TradingEngine(db)
    accounts = engine.get_accounts()
    data = [
        {
            "id": a.id,
            "name": a.name,
            "initial_balance": a.initial_balance,
            "current_balance": a.current_balance,
            "total_profit_loss": a.total_profit_loss,
            "total_trades": a.total_trades,
            "win_trades": a.win_trades,
            "created_at": str(a.created_at),
        }
        for a in accounts
    ]
    return {"success": True, "data": data, "count": len(data)}

@router.get("/accounts/{account_id}")
async def get_account_detail(account_id: int, db: Session = Depends(get_db)):
    """계좌 상세 (잔고, 수익률)"""
    engine = TradingEngine(db)
    summary = engine.get_account_summary(account_id)
    if not summary:
        raise HTTPException(status_code=404, detail="계좌를 찾을 수 없습니다")
    return {"success": True, "data": summary, "count": 1}


# ── 주문 API ──

@router.post("/orders")
async def place_order(req: OrderCreate, db: Session = Depends(get_db)):
    """매수/매도 주문"""
    engine = TradingEngine(db)

    if req.trade_type.upper() == "BUY":
        result = engine.buy(req.account_id, req.stock_id, req.symbol, req.quantity, req.price)
    elif req.trade_type.upper() == "SELL":
        result = engine.sell(req.account_id, req.stock_id, req.symbol, req.quantity, req.price)
    else:
        raise HTTPException(status_code=400, detail="trade_type은 BUY 또는 SELL이어야 합니다")

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    trade = result["trade"]
    return {
        "success": True,
        "data": {
            "id": trade.id,
            "account_id": trade.account_id,
            "symbol": trade.symbol,
            "trade_type": trade.trade_type,
            "quantity": trade.quantity,
            "price": trade.price,
            "total_amount": trade.total_amount,
            "commission": trade.commission,
            "tax": trade.tax,
            "realized_pnl": trade.realized_pnl,
            "timestamp": str(trade.timestamp),
        },
        "count": 1,
    }


# ── 포지션 API ──

@router.get("/positions/{account_id}")
async def get_positions(account_id: int, db: Session = Depends(get_db)):
    """포지션 조회"""
    engine = TradingEngine(db)
    positions = engine.get_positions(account_id)
    data = [
        {
            "id": p.id,
            "stock_id": p.stock_id,
            "symbol": p.symbol,
            "quantity": p.quantity,
            "avg_price": p.avg_price,
            "current_price": p.current_price,
            "unrealized_pnl": p.unrealized_pnl,
        }
        for p in positions
    ]
    return {"success": True, "data": data, "count": len(data)}


# ── 거래 내역 API ──

@router.get("/history/{account_id}")
async def get_trade_history(
    account_id: int,
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
):
    """거래 내역 조회"""
    engine = TradingEngine(db)
    trades = engine.get_trades(account_id, limit)
    data = [
        {
            "id": t.id,
            "symbol": t.symbol,
            "trade_type": t.trade_type,
            "quantity": t.quantity,
            "price": t.price,
            "total_amount": t.total_amount,
            "commission": t.commission,
            "tax": t.tax,
            "realized_pnl": t.realized_pnl,
            "timestamp": str(t.timestamp),
        }
        for t in trades
    ]
    return {"success": True, "data": data, "count": len(data)}


# ── 스코어링 API ──

@router.post("/scores/calculate")
async def calculate_scores(db: Session = Depends(get_db)):
    """전 종목 스코어링 실행"""
    scorer = ScoringEngine(db)
    results = scorer.score_all_stocks()
    return {"success": True, "data": results, "count": len(results)}

@router.get("/scores")
async def get_scores(
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db),
):
    """최신 스코어 조회 (순위)"""
    scorer = ScoringEngine(db)
    scores = scorer.get_latest_scores(limit)
    data = [
        {
            "id": s.id,
            "stock_id": s.stock_id,
            "symbol": s.symbol,
            "rsi_score": s.rsi_score,
            "macd_score": s.macd_score,
            "bollinger_score": s.bollinger_score,
            "ema_score": s.ema_score,
            "prediction_score": s.prediction_score,
            "total_score": s.total_score,
            "signal": s.signal,
            "date": str(s.date),
        }
        for s in scores
    ]
    return {"success": True, "data": data, "count": len(data)}


# ── 백테스팅 API ──

@router.post("/backtest")
async def run_backtest(req: BacktestRequest, db: Session = Depends(get_db)):
    """백테스팅 실행"""
    engine = BacktestEngine(db)
    result = engine.run(
        strategy_name=req.strategy_name,
        start_date=req.start_date,
        end_date=req.end_date,
        initial_balance=req.initial_balance,
        buy_threshold=req.buy_threshold,
        sell_threshold=req.sell_threshold,
        max_positions=req.max_positions,
        budget_ratio=req.budget_ratio,
    )
    if not result:
        raise HTTPException(status_code=400, detail="백테스팅 실행 실패")
    return {"success": True, "data": result, "count": 1}

@router.get("/backtest/{result_id}")
async def get_backtest_result(result_id: int, db: Session = Depends(get_db)):
    """백테스팅 결과 조회"""
    engine = BacktestEngine(db)
    result = engine.get_result(result_id)
    if not result:
        raise HTTPException(status_code=404, detail="결과를 찾을 수 없습니다")
    return {
        "success": True,
        "data": {
            "id": result.id,
            "strategy_name": result.strategy_name,
            "start_date": str(result.start_date),
            "end_date": str(result.end_date),
            "initial_balance": result.initial_balance,
            "final_balance": result.final_balance,
            "total_return": result.total_return,
            "sharpe_ratio": result.sharpe_ratio,
            "max_drawdown": result.max_drawdown,
            "win_rate": result.win_rate,
            "total_trades": result.total_trades,
            "win_trades": result.win_trades,
            "strategy_type": result.strategy_type,
            "trade_details": result.trade_details,
            "parameters": result.parameters,
            "created_at": str(result.created_at),
        },
        "count": 1,
    }

@router.get("/backtest")
async def list_backtest_results(
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db),
):
    """백테스팅 결과 목록"""
    engine = BacktestEngine(db)
    results = engine.get_results(limit)
    data = [
        {
            "id": r.id,
            "strategy_name": r.strategy_name,
            "start_date": str(r.start_date),
            "end_date": str(r.end_date),
            "total_return": r.total_return,
            "win_rate": r.win_rate,
            "sharpe_ratio": r.sharpe_ratio,
            "max_drawdown": r.max_drawdown,
            "total_trades": r.total_trades,
            "created_at": str(r.created_at),
        }
        for r in results
    ]
    return {"success": True, "data": data, "count": len(data)}


# ── 자동매매 규칙 API ──

@router.post("/rules")
async def create_rule(req: RuleCreate, db: Session = Depends(get_db)):
    """자동매매 규칙 등록"""
    rule = AutoTradingRule(
        name=req.name,
        strategy_type=req.strategy_type,
        account_id=req.account_id,
        buy_score_threshold=req.buy_score_threshold,
        max_position_count=req.max_position_count,
        budget_ratio=req.budget_ratio,
        schedule_buy=req.schedule_buy,
        schedule_sell=req.schedule_sell,
        parameters=req.parameters or {},
        is_active=True,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return {
        "success": True,
        "data": _rule_to_dict(rule),
        "count": 1,
    }

@router.get("/rules")
async def list_rules(db: Session = Depends(get_db)):
    """규칙 목록 조회"""
    rules = db.query(AutoTradingRule).all()
    data = [_rule_to_dict(r) for r in rules]
    return {"success": True, "data": data, "count": len(data)}

@router.patch("/rules/{rule_id}")
async def update_rule(rule_id: int, req: RuleUpdate, db: Session = Depends(get_db)):
    """규칙 수정/활성화 토글"""
    rule = db.query(AutoTradingRule).filter(AutoTradingRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="규칙을 찾을 수 없습니다")

    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    rule.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(rule)
    return {"success": True, "data": _rule_to_dict(rule), "count": 1}

@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    """규칙 삭제"""
    rule = db.query(AutoTradingRule).filter(AutoTradingRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="규칙을 찾을 수 없습니다")
    db.delete(rule)
    db.commit()
    return {"success": True, "data": {"id": rule_id, "deleted": True}, "count": 1}


# ── 헬퍼 ──

def _rule_to_dict(rule: AutoTradingRule) -> dict:
    return {
        "id": rule.id,
        "name": rule.name,
        "strategy_type": rule.strategy_type,
        "account_id": rule.account_id,
        "is_active": rule.is_active,
        "buy_score_threshold": rule.buy_score_threshold,
        "max_position_count": rule.max_position_count,
        "budget_ratio": rule.budget_ratio,
        "schedule_buy": rule.schedule_buy,
        "schedule_sell": rule.schedule_sell,
        "last_executed_at": str(rule.last_executed_at) if rule.last_executed_at else None,
        "parameters": rule.parameters,
        "created_at": str(rule.created_at),
        "updated_at": str(rule.updated_at),
    }
