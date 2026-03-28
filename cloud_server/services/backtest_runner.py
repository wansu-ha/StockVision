"""백테스트 엔진 코어 — 과거 데이터로 DSL 규칙을 시뮬레이션.

멀티 타임프레임 (1m, 5m, 15m, 1h, 1d) 지원.
sv_core/parsing evaluator와 sv_core/indicators calculator를 재사용.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from sv_core.indicators.calculator import calc_all_indicators
from sv_core.parsing.evaluator import evaluate as dsl_evaluate
from sv_core.parsing.parser import parse

logger = logging.getLogger(__name__)

# 지표 계산에 필요한 최소 lookback 바 수
INDICATOR_LOOKBACK = 60


@dataclass
class Trade:
    """체결된 거래 1건."""
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
    """백테스트 결과."""
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
    """백테스트 설정."""
    initial_cash: float = 10_000_000
    commission_rate: float = 0.00015    # 0.015% 편도
    tax_rate: float = 0.0018            # 매도 시 0.18%
    slippage_rate: float = 0.001        # 0.1%
    max_position_pct: float = 0.95      # 최대 투입 비율


class BacktestRunner:
    """백테스트 실행기."""

    def __init__(self, db: Session):
        self._db = db

    async def run(
        self,
        script: str,
        symbol: str,
        start_date: date,
        end_date: date,
        timeframe: str = "1d",
        config: BacktestConfig | None = None,
    ) -> BacktestResult:
        """백테스트 실행.

        Args:
            script: DSL 스크립트
            symbol: 종목코드
            start_date, end_date: 기간
            timeframe: "1m", "5m", "15m", "1h", "1d"
            config: 비용/자금 설정

        Returns:
            BacktestResult
        """
        cfg = config or BacktestConfig()

        # 1. DSL 파싱
        ast = parse(script)

        # 2. 바 데이터 로드
        bars = self._load_bars(symbol, start_date, end_date, timeframe)
        if len(bars) < INDICATOR_LOOKBACK:
            logger.warning("데이터 부족: %s %d bars (최소 %d)", symbol, len(bars), INDICATOR_LOOKBACK)
            return BacktestResult()

        # 3. 지표 사전 계산 (벡터화)
        closes = pd.Series([b["close"] for b in bars], dtype=float)
        volumes = pd.Series([b["volume"] for b in bars], dtype=float)
        all_indicators = self._precompute_indicators(closes, volumes)

        # 4. 시뮬레이션 루프
        return self._simulate(ast, bars, all_indicators, cfg)

    def _load_bars(
        self, symbol: str, start: date, end: date, timeframe: str,
    ) -> list[dict]:
        """DB에서 바 데이터 로드."""
        if timeframe == "1d":
            return self._load_daily_bars(symbol, start, end)
        else:
            return self._load_minute_bars(symbol, start, end, timeframe)

    def _load_daily_bars(self, symbol: str, start: date, end: date) -> list[dict]:
        """DailyBar 테이블에서 로드."""
        from cloud_server.models.market import DailyBar

        rows = (
            self._db.query(DailyBar)
            .filter(DailyBar.symbol == symbol, DailyBar.date >= start, DailyBar.date <= end)
            .order_by(DailyBar.date)
            .all()
        )
        return [
            {
                "timestamp": str(r.date),
                "open": float(r.open or 0),
                "high": float(r.high or 0),
                "low": float(r.low or 0),
                "close": float(r.close or 0),
                "volume": float(r.volume or 0),
            }
            for r in rows
        ]

    def _load_minute_bars(
        self, symbol: str, start: date, end: date, timeframe: str,
    ) -> list[dict]:
        """MinuteBar 테이블에서 로드 + 상위 TF 집계."""
        from cloud_server.models.market import MinuteBar

        start_dt = datetime.combine(start, datetime.min.time())
        end_dt = datetime.combine(end, datetime.max.time())

        rows = (
            self._db.query(MinuteBar)
            .filter(
                MinuteBar.symbol == symbol,
                MinuteBar.timestamp >= start_dt,
                MinuteBar.timestamp <= end_dt,
            )
            .order_by(MinuteBar.timestamp)
            .all()
        )
        bars = [
            {
                "timestamp": r.timestamp.isoformat(),
                "open": float(r.open or 0),
                "high": float(r.high or 0),
                "low": float(r.low or 0),
                "close": float(r.close or 0),
                "volume": float(r.volume or 0),
            }
            for r in rows
        ]

        # 1m → 상위 TF 집계
        if timeframe != "1m" and bars:
            bars = self._aggregate_bars(bars, timeframe)

        return bars

    def _aggregate_bars(self, bars: list[dict], timeframe: str) -> list[dict]:
        """1분봉 → 상위 타임프레임 집계."""
        from itertools import groupby

        minutes = {"5m": 5, "15m": 15, "1h": 60}
        bucket = minutes.get(timeframe, 5)

        def key_fn(b):
            ts = datetime.fromisoformat(b["timestamp"])
            floored = ts.replace(minute=(ts.minute // bucket) * bucket, second=0, microsecond=0)
            return floored.isoformat()

        result = []
        for _, group in groupby(bars, key=key_fn):
            gl = list(group)
            result.append({
                "timestamp": gl[0]["timestamp"],
                "open": gl[0]["open"],
                "high": max(b["high"] for b in gl),
                "low": min(b["low"] for b in gl),
                "close": gl[-1]["close"],
                "volume": sum(b["volume"] for b in gl),
            })
        return result

    def _precompute_indicators(
        self, closes: pd.Series, volumes: pd.Series,
    ) -> list[dict]:
        """각 바 시점의 지표를 사전 계산 (look-ahead bias 방지).

        i번째 바의 지표는 0~i까지의 데이터만 사용.
        """
        results = []
        for i in range(len(closes)):
            if i < INDICATOR_LOOKBACK - 1:
                results.append({})
                continue
            window_close = closes.iloc[: i + 1]
            window_vol = volumes.iloc[: i + 1]
            results.append(calc_all_indicators(window_close, window_vol))
        return results

    def _simulate(
        self,
        ast,
        bars: list[dict],
        indicators: list[dict],
        cfg: BacktestConfig,
    ) -> BacktestResult:
        """바 루프 시뮬레이션."""
        cash = cfg.initial_cash
        position: dict | None = None  # {"entry_price", "qty", "entry_idx", "entry_date"}
        trades: list[Trade] = []
        equity_curve: list[float] = []

        eval_state: dict[str, Any] = {}

        for i, bar in enumerate(bars):
            price = bar["close"]
            volume = bar["volume"]

            # 포트폴리오 평가
            if position:
                equity = cash + position["qty"] * price
            else:
                equity = cash
            equity_curve.append(equity)

            # 지표 부족 → skip
            if not indicators[i]:
                continue

            # DSL context 구성
            context = {
                "현재가": price,
                "거래량": volume,
                "수익률": ((price / position["entry_price"]) - 1) * 100 if position else 0.0,
                "보유수량": position["qty"] if position else 0,
            }
            # 지표 함수를 context에 주입
            # tf 인자가 지정되면 해당 TF의 지표를 조회 (현재는 메인 TF만)
            # 다른 TF 참조 시 None 반환 (데이터 없음)
            ind = indicators[i]
            main_tf = cfg.__dict__.get("_timeframe", timeframe) if hasattr(cfg, "_timeframe") else "default"

            def _make_indicator_fn(key_pattern: str, _ind=ind):
                def fn(period, tf=None):
                    # tf가 None이거나 메인 TF와 같으면 현재 지표 사용
                    return _ind.get(key_pattern.format(int(period)))
                return fn

            context["RSI"] = _make_indicator_fn("rsi_{}")
            context["MA"] = _make_indicator_fn("ma_{}")
            context["EMA"] = _make_indicator_fn("ema_{}")
            context["MACD"] = lambda tf=None, _i=ind: _i.get("macd")
            context["MACD_SIGNAL"] = lambda tf=None, _i=ind: _i.get("macd_signal")
            context["볼린저_상단"] = _make_indicator_fn("bb_upper_{}")
            context["볼린저_하단"] = _make_indicator_fn("bb_lower_{}")
            context["평균거래량"] = _make_indicator_fn("avg_volume_{}")

            # DSL 평가
            try:
                buy_signal, sell_signal = dsl_evaluate(ast, context, eval_state)
            except Exception:
                continue

            # 매수
            if buy_signal and position is None and price > 0:
                invest = cash * cfg.max_position_pct
                slippage = price * cfg.slippage_rate
                buy_price = price + slippage
                qty = int(invest / buy_price)
                if qty > 0:
                    commission = buy_price * qty * cfg.commission_rate
                    cash -= buy_price * qty + commission
                    position = {
                        "entry_price": buy_price,
                        "qty": qty,
                        "entry_idx": i,
                        "entry_date": bar["timestamp"],
                        "commission_buy": commission,
                        "slippage_buy": slippage * qty,
                    }

            # 매도
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
                total_commission = position["commission_buy"] + commission
                total_slippage = position["slippage_buy"] + slippage * qty

                trades.append(Trade(
                    entry_date=position["entry_date"],
                    entry_price=position["entry_price"],
                    exit_date=bar["timestamp"],
                    exit_price=sell_price,
                    qty=qty,
                    pnl=round(pnl, 0),
                    pnl_pct=round((sell_price / position["entry_price"] - 1) * 100, 2),
                    commission=round(total_commission, 0),
                    tax=round(tax, 0),
                    slippage=round(total_slippage, 0),
                    hold_bars=i - position["entry_idx"],
                ))
                position = None

        # 미청산 포지션 강제 청산 (마지막 바 기준)
        if position and bars:
            last_price = bars[-1]["close"]
            qty = position["qty"]
            gross = last_price * qty
            pnl = gross - position["entry_price"] * qty
            trades.append(Trade(
                entry_date=position["entry_date"],
                entry_price=position["entry_price"],
                exit_date=bars[-1]["timestamp"],
                exit_price=last_price,
                qty=qty,
                pnl=round(pnl, 0),
                pnl_pct=round((last_price / position["entry_price"] - 1) * 100, 2),
                hold_bars=len(bars) - 1 - position["entry_idx"],
            ))

        # 결과 집계
        return self._aggregate_result(equity_curve, trades, cfg)

    def _aggregate_result(
        self, equity_curve: list[float], trades: list[Trade], cfg: BacktestConfig,
    ) -> BacktestResult:
        """결과 지표 계산."""
        initial = cfg.initial_cash
        final = equity_curve[-1] if equity_curve else initial

        total_return = (final / initial - 1) * 100 if initial > 0 else 0.0

        # MDD
        mdd = 0.0
        if equity_curve:
            peak = equity_curve[0]
            for eq in equity_curve:
                if eq > peak:
                    peak = eq
                dd = (peak - eq) / peak * 100
                if dd > mdd:
                    mdd = dd

        # 승률, 손익비
        wins = [t for t in trades if t.pnl > 0]
        losses = [t for t in trades if t.pnl <= 0]
        win_rate = len(wins) / len(trades) * 100 if trades else 0.0
        total_profit = sum(t.pnl for t in wins)
        total_loss = abs(sum(t.pnl for t in losses))
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf') if total_profit > 0 else 0.0

        # CAGR
        n_bars = len(equity_curve)
        # 대략적 연 환산 (일봉 250바 = 1년, 분봉은 95000바 = 1년)
        years = max(n_bars / 250, 0.01) if n_bars > 0 else 1.0
        cagr = ((final / initial) ** (1 / years) - 1) * 100 if initial > 0 and years > 0 else 0.0

        # 샤프 비율 (일별 수익률 기반)
        sharpe = 0.0
        if len(equity_curve) > 1:
            returns = pd.Series(equity_curve).pct_change().dropna()
            if returns.std() > 0:
                sharpe = round(float(returns.mean() / returns.std() * np.sqrt(250)), 2)

        return BacktestResult(
            equity_curve=equity_curve,
            trades=trades,
            total_return_pct=round(total_return, 2),
            cagr=round(cagr, 2),
            max_drawdown_pct=round(mdd, 2),
            win_rate=round(win_rate, 2),
            profit_factor=round(profit_factor, 2) if profit_factor != float('inf') else 999.99,
            sharpe_ratio=sharpe,
            avg_hold_bars=round(sum(t.hold_bars for t in trades) / len(trades), 1) if trades else 0.0,
            trade_count=len(trades),
            total_commission=round(sum(t.commission for t in trades), 0),
            total_tax=round(sum(t.tax for t in trades), 0),
            total_slippage=round(sum(t.slippage for t in trades), 0),
        )
