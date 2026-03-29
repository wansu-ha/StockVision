"""백테스트 API.

POST /api/v1/backtest/run       — DSL 규칙 백테스트 실행 + 결과 저장
GET  /api/v1/backtest/history   — 사용자별 이력 조회
GET  /api/v1/backtest/{id}      — 특정 결과 상세
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from cloud_server.api.dependencies import current_user
from cloud_server.core.database import get_db
from cloud_server.models.backtest import BacktestExecution

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/backtest", tags=["backtest"])


class BacktestRequest(BaseModel):
    """백테스트 요청."""
    rule_id: int | None = None
    script: str | None = None
    symbol: str
    start_date: date | None = None
    end_date: date | None = None
    timeframe: str = Field("1d", pattern="^(1m|5m|15m|1h|1d)$")
    initial_cash: float = 10_000_000
    commission_rate: float = 0.00015
    tax_rate: float = 0.0018
    slippage_rate: float = 0.001


@router.post("/run")
async def run_backtest(
    req: BacktestRequest,
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    """DSL 규칙 백테스트 실행 + 결과 DB 저장."""
    script = req.script
    if req.rule_id is not None and not script:
        from cloud_server.models.rule import TradingRule
        rule = db.query(TradingRule).filter(
            TradingRule.id == req.rule_id,
            TradingRule.user_id == user["sub"],
        ).first()
        if not rule:
            raise HTTPException(status_code=404, detail="규칙을 찾을 수 없습니다.")
        script = rule.script
        if not script:
            raise HTTPException(status_code=400, detail="DSL 스크립트가 없는 규칙입니다.")
        # 파싱 오류가 있는 규칙은 백테스트 불가
        if rule.dsl_meta and rule.dsl_meta.get("parse_status") == "error":
            raise HTTPException(status_code=400, detail="DSL 파싱 오류가 있는 규칙은 백테스트할 수 없습니다.")

    if not script:
        raise HTTPException(status_code=400, detail="rule_id 또는 script가 필요합니다.")

    end_date = req.end_date or date.today()
    start_date = req.start_date or (end_date - timedelta(days=365))

    from cloud_server.services.backtest_runner import BacktestRunner, BacktestConfig

    config = BacktestConfig(
        initial_cash=req.initial_cash,
        commission_rate=req.commission_rate,
        tax_rate=req.tax_rate,
        slippage_rate=req.slippage_rate,
    )

    runner = BacktestRunner(db)
    try:
        result = await runner.run(
            script=script,
            symbol=req.symbol,
            start_date=start_date,
            end_date=end_date,
            timeframe=req.timeframe,
            config=config,
        )
    except Exception as e:
        logger.error("백테스트 실패: %s", e)
        raise HTTPException(status_code=500, detail=f"백테스트 실행 실패: {e}")

    # DB 저장
    summary_dict = {
        "total_return_pct": result.total_return_pct,
        "cagr": result.cagr,
        "max_drawdown_pct": result.max_drawdown_pct,
        "win_rate": result.win_rate,
        "profit_factor": result.profit_factor,
        "sharpe_ratio": result.sharpe_ratio,
        "avg_hold_bars": result.avg_hold_bars,
        "trade_count": result.trade_count,
        "total_commission": result.total_commission,
        "total_tax": result.total_tax,
        "total_slippage": result.total_slippage,
    }

    execution = BacktestExecution(
        user_id=user["sub"],
        rule_id=req.rule_id,
        symbol=req.symbol,
        start_date=start_date,
        end_date=end_date,
        timeframe=req.timeframe,
        initial_cash=req.initial_cash,
        summary=summary_dict,
        trade_count=result.trade_count,
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)

    # 응답
    equity = result.equity_curve
    if len(equity) > 500:
        step = len(equity) // 500
        equity = equity[::step]

    return {
        "success": True,
        "data": {
            "id": execution.id,
            "summary": summary_dict,
            "equity_curve": equity,
            "trades": [
                {
                    "entry_date": t.entry_date,
                    "entry_price": t.entry_price,
                    "exit_date": t.exit_date,
                    "exit_price": t.exit_price,
                    "qty": t.qty,
                    "pnl": t.pnl,
                    "pnl_pct": t.pnl_pct,
                    "commission": t.commission,
                    "tax": t.tax,
                    "hold_bars": t.hold_bars,
                }
                for t in result.trades
            ],
        },
    }


@router.get("/history")
async def backtest_history(
    rule_id: int | None = Query(None),
    limit: int = Query(20, le=100),
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    """사용자별 백테스트 이력 조회. rule_id 필터 가능."""
    query = db.query(BacktestExecution).filter(
        BacktestExecution.user_id == user["sub"],
    )
    if rule_id is not None:
        query = query.filter(BacktestExecution.rule_id == rule_id)

    rows = query.order_by(BacktestExecution.executed_at.desc()).limit(limit).all()

    return {
        "success": True,
        "data": [
            {
                "id": r.id,
                "rule_id": r.rule_id,
                "symbol": r.symbol,
                "start_date": str(r.start_date),
                "end_date": str(r.end_date),
                "timeframe": r.timeframe,
                "summary": r.summary,
                "trade_count": r.trade_count,
                "executed_at": r.executed_at.isoformat() if r.executed_at else None,
            }
            for r in rows
        ],
        "count": len(rows),
    }


@router.get("/{execution_id}")
async def backtest_detail(
    execution_id: int,
    user: dict = Depends(current_user),
    db: Session = Depends(get_db),
):
    """백테스트 결과 상세."""
    row = db.query(BacktestExecution).filter(
        BacktestExecution.id == execution_id,
        BacktestExecution.user_id == user["sub"],
    ).first()

    if not row:
        raise HTTPException(status_code=404, detail="백테스트 결과를 찾을 수 없습니다.")

    return {
        "success": True,
        "data": {
            "id": row.id,
            "rule_id": row.rule_id,
            "symbol": row.symbol,
            "start_date": str(row.start_date),
            "end_date": str(row.end_date),
            "timeframe": row.timeframe,
            "initial_cash": row.initial_cash,
            "summary": row.summary,
            "trade_count": row.trade_count,
            "executed_at": row.executed_at.isoformat() if row.executed_at else None,
        },
    }
