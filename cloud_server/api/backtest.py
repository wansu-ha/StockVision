"""백테스트 API.

POST /api/v1/backtest/run — DSL 규칙 백테스트 실행
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from cloud_server.api.dependencies import current_user
from cloud_server.core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/backtest", tags=["backtest"])


class BacktestRequest(BaseModel):
    """백테스트 요청."""
    rule_id: int | None = None
    script: str | None = None              # inline DSL (rule_id 없을 때)
    symbol: str
    start_date: date | None = None         # 미지정 시 1년 전
    end_date: date | None = None           # 미지정 시 오늘
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
    """DSL 규칙 백테스트 실행.

    rule_id 또는 script 중 하나 필수.
    rule_id 지정 시 DB에서 규칙 로드, script 지정 시 inline DSL 사용.
    """
    # 스크립트 결정
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

    if not script:
        raise HTTPException(status_code=400, detail="rule_id 또는 script가 필요합니다.")

    # 기간 기본값
    end_date = req.end_date or date.today()
    start_date = req.start_date or (end_date - timedelta(days=365))

    # 실행
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

    # 응답 (equity_curve는 길 수 있으므로 샘플링)
    equity = result.equity_curve
    if len(equity) > 500:
        # 500포인트로 다운샘플
        step = len(equity) // 500
        equity = equity[::step]

    return {
        "success": True,
        "data": {
            "summary": {
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
            },
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
