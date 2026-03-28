"""백테스트 엔진 — data_client API로 봉 조회, sv_core로 시뮬레이션.

cloud_server/services/backtest_runner.py에서 이식.
변경점: DB 직접 조회 → data_client.get_bars() 호출.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from itertools import groupby
from typing import Any

import numpy as np
import pandas as pd

from sv_core.indicators.calculator import (
    calc_all_indicators,
    calc_avg_volume,
    calc_bollinger,
    calc_ema,
    calc_rsi,
    calc_sma,
)
from sv_core.parsing.evaluator import evaluate as dsl_evaluate
from sv_core.parsing.parser import parse

from backtest_server.services.data_client import get_bars

logger = logging.getLogger(__name__)

INDICATOR_LOOKBACK = 60


@dataclass
class Trade:
    entry_date: str
    entry_price: float
    exit_date: str = ""
    exit_price: float = 0.0
    qty: int = 0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    commission: float = 0.0
    tax: float = 0.0
    slippage: float = 0.0
    hold_bars: int = 0


@dataclass
class BacktestResult:
    equity_curve: list[float] = field(default_factory=list)
    trades: list[Trade] = field(default_factory=list)
    total_return_pct: float = 0.0
    cagr: float = 0.0
    max_drawdown_pct: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    avg_hold_bars: float = 0.0
    trade_count: int = 0
    total_commission: float = 0.0
    total_tax: float = 0.0
    total_slippage: float = 0.0


@dataclass
class BacktestConfig:
    initial_cash: float = 10_000_000
    commission_rate: float = 0.00015
    tax_rate: float = 0.0018
    slippage_rate: float = 0.001
    max_position_pct: float = 0.95


async def run_backtest(
    script: str,
    symbol: str,
    start_date: date,
    end_date: date,
    timeframe: str = "1d",
    config: BacktestConfig | None = None,
) -> BacktestResult:
    """백테스트 실행."""
    cfg = config or BacktestConfig()

    # 1. DSL 파싱
    ast = parse(script)

    # 2. 데이터 서버에서 봉 로드
    raw_bars = await get_bars(symbol, timeframe, start_date, end_date)
    bars = _normalize_bars(raw_bars, timeframe)

    if len(bars) < INDICATOR_LOOKBACK:
        logger.warning("데이터 부족: %s %d bars", symbol, len(bars))
        return BacktestResult()

    # 3. 지표 사전 계산
    closes = pd.Series([b["close"] for b in bars], dtype=float)
    volumes = pd.Series([b["volume"] for b in bars], dtype=float)
    all_indicators = _precompute_indicators(closes, volumes)

    # 4. 시뮬레이션
    return _simulate(ast, bars, all_indicators, cfg, closes, volumes)


def _normalize_bars(raw: list[dict], timeframe: str) -> list[dict]:
    """API 응답을 시뮬레이션용 형식으로 정규화."""
    ts_field = "timestamp" if timeframe != "1d" else "date"
    return [
        {
            "timestamp": b.get("timestamp", b.get("date", "")),
            "open": float(b.get("open") or 0),
            "high": float(b.get("high") or 0),
            "low": float(b.get("low") or 0),
            "close": float(b.get("close") or 0),
            "volume": float(b.get("volume") or 0),
        }
        for b in raw
    ]


def _precompute_indicators(closes: pd.Series, volumes: pd.Series) -> list[dict]:
    results = []
    for i in range(len(closes)):
        if i < INDICATOR_LOOKBACK - 1:
            results.append({})
            continue
        results.append(calc_all_indicators(closes.iloc[: i + 1], volumes.iloc[: i + 1]))
    return results


def _simulate(
    ast, bars: list[dict], indicators: list[dict],
    cfg: BacktestConfig, closes: pd.Series, volumes: pd.Series,
) -> BacktestResult:
    cash = cfg.initial_cash
    position: dict | None = None
    trades: list[Trade] = []
    equity_curve: list[float] = []
    eval_state: dict[str, Any] = {}

    for i, bar in enumerate(bars):
        price = bar["close"]
        volume = bar["volume"]

        equity = cash + position["qty"] * price if position else cash
        equity_curve.append(equity)

        if not indicators[i]:
            continue

        context = {
            "현재가": price,
            "거래량": volume,
            "수익률": ((price / position["entry_price"]) - 1) * 100 if position else 0.0,
            "보유수량": position["qty"] if position else 0,
        }
        _c = closes.iloc[: i + 1]
        _v = volumes.iloc[: i + 1]
        context["RSI"] = lambda p, tf=None, _w=_c: calc_rsi(_w, int(p))
        context["MA"] = lambda p, tf=None, _w=_c: calc_sma(_w, int(p))
        context["EMA"] = lambda p, tf=None, _w=_c: calc_ema(_w, int(p))
        context["MACD"] = lambda tf=None, _i=indicators[i]: _i.get("macd")
        context["MACD_SIGNAL"] = lambda tf=None, _i=indicators[i]: _i.get("macd_signal")
        context["볼린저_상단"] = lambda p, tf=None, _w=_c: calc_bollinger(_w, int(p))[0]
        context["볼린저_하단"] = lambda p, tf=None, _w=_c: calc_bollinger(_w, int(p))[1]
        context["평균거래량"] = lambda p, tf=None, _w=_v: calc_avg_volume(_w, int(p))

        try:
            buy_signal, sell_signal = dsl_evaluate(ast, context, eval_state)
        except Exception:
            continue

        if buy_signal and position is None and price > 0:
            invest = cash * cfg.max_position_pct
            slippage = price * cfg.slippage_rate
            buy_price = price + slippage
            qty = int(invest / buy_price)
            if qty > 0:
                commission = buy_price * qty * cfg.commission_rate
                cash -= buy_price * qty + commission
                position = {
                    "entry_price": buy_price, "qty": qty,
                    "entry_idx": i, "entry_date": bar["timestamp"],
                    "commission_buy": commission, "slippage_buy": slippage * qty,
                }

        elif sell_signal and position is not None:
            slippage = price * cfg.slippage_rate
            sell_price = price - slippage
            qty = position["qty"]
            gross = sell_price * qty
            commission = gross * cfg.commission_rate
            tax = gross * cfg.tax_rate
            net = gross - commission - tax
            cash += net

            pnl = net - position["entry_price"] * qty - position["commission_buy"]
            trades.append(Trade(
                entry_date=position["entry_date"],
                entry_price=position["entry_price"],
                exit_date=bar["timestamp"], exit_price=sell_price,
                qty=qty, pnl=round(pnl, 0),
                pnl_pct=round((sell_price / position["entry_price"] - 1) * 100, 2),
                commission=round(position["commission_buy"] + commission, 0),
                tax=round(tax, 0),
                slippage=round(position["slippage_buy"] + slippage * qty, 0),
                hold_bars=i - position["entry_idx"],
            ))
            position = None

    # 미청산 강제 청산
    if position and bars:
        last = bars[-1]["close"]
        qty = position["qty"]
        pnl = last * qty - position["entry_price"] * qty
        trades.append(Trade(
            entry_date=position["entry_date"],
            entry_price=position["entry_price"],
            exit_date=bars[-1]["timestamp"], exit_price=last,
            qty=qty, pnl=round(pnl, 0),
            pnl_pct=round((last / position["entry_price"] - 1) * 100, 2),
            hold_bars=len(bars) - 1 - position["entry_idx"],
        ))

    return _aggregate_result(equity_curve, trades, cfg)


def _aggregate_result(
    equity_curve: list[float], trades: list[Trade], cfg: BacktestConfig,
) -> BacktestResult:
    initial = cfg.initial_cash
    final = equity_curve[-1] if equity_curve else initial
    total_return = (final / initial - 1) * 100 if initial > 0 else 0.0

    mdd = 0.0
    if equity_curve:
        peak = equity_curve[0]
        for eq in equity_curve:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak * 100
            if dd > mdd:
                mdd = dd

    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl <= 0]
    win_rate = len(wins) / len(trades) * 100 if trades else 0.0
    total_profit = sum(t.pnl for t in wins)
    total_loss = abs(sum(t.pnl for t in losses))
    profit_factor = total_profit / total_loss if total_loss > 0 else (999.99 if total_profit > 0 else 0.0)

    years = max(len(equity_curve) / 250, 0.01)
    cagr = ((final / initial) ** (1 / years) - 1) * 100 if initial > 0 else 0.0

    sharpe = 0.0
    if len(equity_curve) > 1:
        returns = pd.Series(equity_curve).pct_change().dropna()
        if returns.std() > 0:
            sharpe = round(float(returns.mean() / returns.std() * np.sqrt(250)), 2)

    return BacktestResult(
        equity_curve=equity_curve, trades=trades,
        total_return_pct=round(total_return, 2), cagr=round(cagr, 2),
        max_drawdown_pct=round(mdd, 2), win_rate=round(win_rate, 2),
        profit_factor=round(profit_factor, 2), sharpe_ratio=sharpe,
        avg_hold_bars=round(sum(t.hold_bars for t in trades) / len(trades), 1) if trades else 0.0,
        trade_count=len(trades),
        total_commission=round(sum(t.commission for t in trades), 0),
        total_tax=round(sum(t.tax for t in trades), 0),
        total_slippage=round(sum(t.slippage for t in trades), 0),
    )
