"""
백테스팅 엔진

과거 데이터 기반 전략 시뮬레이션. 일봉 단위로 스코어링→매수/매도를 반복하고
성과 지표(총 수익률, 승률, 샤프비율, 최대 낙폭)를 계산한다.
"""

import logging
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.stock import Stock, StockPrice
from app.models.auto_trading import BacktestResult
from app.services.scoring_engine import ScoringEngine, BUY_THRESHOLD, SELL_THRESHOLD

logger = logging.getLogger(__name__)

# 수수료/세금
BUY_COMMISSION = 0.00015
SELL_COMMISSION = 0.00015
SELL_TAX = 0.0023


class BacktestEngine:
    """백테스팅 엔진"""

    def __init__(self, db: Optional[Session] = None):
        self.db = db or SessionLocal()
        self._owns_db = db is None

    def close(self):
        if self._owns_db:
            self.db.close()

    def run(
        self,
        strategy_name: str,
        start_date: str,
        end_date: str,
        initial_balance: float = 10_000_000.0,
        buy_threshold: float = BUY_THRESHOLD,
        sell_threshold: float = SELL_THRESHOLD,
        max_positions: int = 5,
        budget_ratio: float = 0.7,
    ) -> Optional[dict]:
        """백테스팅 실행

        Args:
            strategy_name: 전략 이름
            start_date: 시작일 (YYYY-MM-DD)
            end_date: 종료일 (YYYY-MM-DD)
            initial_balance: 초기 자본금
            buy_threshold: 매수 스코어 기준
            sell_threshold: 매도 스코어 기준 (미사용 — 일괄 매도 방식)
            max_positions: 최대 보유 종목 수
            budget_ratio: 예산 사용 비율

        Returns:
            백테스팅 결과 dict or None
        """
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")

            # 등록된 전 종목의 가격 데이터 로드
            stocks = self.db.query(Stock).all()
            if not stocks:
                logger.warning("등록된 종목 없음")
                return None

            # 종목별 가격 DataFrame 준비
            stock_prices: dict[int, pd.DataFrame] = {}
            stock_symbols: dict[int, str] = {}
            for stock in stocks:
                prices = (
                    self.db.query(StockPrice)
                    .filter(
                        StockPrice.stock_id == stock.id,
                        StockPrice.date >= start,
                        StockPrice.date <= end,
                    )
                    .order_by(StockPrice.date)
                    .all()
                )
                if prices:
                    df = pd.DataFrame(
                        [{"date": p.date, "close": p.close, "volume": p.volume} for p in prices]
                    )
                    df.set_index("date", inplace=True)
                    stock_prices[stock.id] = df
                    stock_symbols[stock.id] = stock.symbol

            if not stock_prices:
                logger.warning("해당 기간 가격 데이터 없음")
                return None

            # 거래일 목록 (모든 종목 합집합)
            all_dates = sorted(
                set().union(*(df.index.tolist() for df in stock_prices.values()))
            )

            # 시뮬레이션 상태
            balance = initial_balance
            positions: dict[int, dict] = {}  # {stock_id: {"qty", "avg_price", "symbol"}}
            trades: list[dict] = []
            daily_values: list[float] = [initial_balance]

            # 스코어링 엔진
            scorer = ScoringEngine(self.db)

            for date in all_dates:
                # 1) 보유 포지션 평가
                portfolio_value = balance
                for sid, pos in list(positions.items()):
                    if sid in stock_prices and date in stock_prices[sid].index:
                        current_price = stock_prices[sid].loc[date, "close"]
                        portfolio_value += current_price * pos["qty"]
                    else:
                        portfolio_value += pos["avg_price"] * pos["qty"]

                daily_values.append(portfolio_value)

                # 2) 매도 판단 — 보유 종목 중 스코어 낮은 종목 매도
                for sid in list(positions.keys()):
                    if sid not in stock_prices or date not in stock_prices[sid].index:
                        continue
                    score_data = scorer.score_stock(sid, stock_symbols[sid])
                    if score_data and score_data["total_score"] <= sell_threshold:
                        price = stock_prices[sid].loc[date, "close"]
                        qty = positions[sid]["qty"]
                        total_amount = price * qty
                        commission = total_amount * SELL_COMMISSION
                        tax = total_amount * SELL_TAX
                        net = total_amount - commission - tax
                        realized_pnl = net - (positions[sid]["avg_price"] * qty)

                        balance += net
                        trades.append({
                            "date": str(date),
                            "symbol": stock_symbols[sid],
                            "type": "SELL",
                            "quantity": qty,
                            "price": float(price),
                            "total_amount": float(total_amount),
                            "commission": float(commission),
                            "tax": float(tax),
                            "realized_pnl": float(realized_pnl),
                        })
                        del positions[sid]

                # 3) 매수 판단 — 빈 자리가 있으면 스코어 상위 종목 매수
                available_slots = max_positions - len(positions)
                if available_slots > 0:
                    # 간이 스코어 계산 (전 종목)
                    candidates = []
                    for sid, symbol in stock_symbols.items():
                        if sid in positions:
                            continue
                        if sid not in stock_prices or date not in stock_prices[sid].index:
                            continue
                        score_data = scorer.score_stock(sid, symbol)
                        if score_data and score_data["total_score"] >= buy_threshold:
                            candidates.append((sid, score_data["total_score"]))

                    # 스코어 내림차순 정렬, 상위 N개
                    candidates.sort(key=lambda x: x[1], reverse=True)
                    buy_targets = candidates[:available_slots]

                    if buy_targets:
                        budget_per_stock = (balance * budget_ratio) / len(buy_targets)
                        for sid, _ in buy_targets:
                            price = stock_prices[sid].loc[date, "close"]
                            qty = int(budget_per_stock / (price * (1 + BUY_COMMISSION)))
                            if qty <= 0:
                                continue

                            total_amount = price * qty
                            commission = total_amount * BUY_COMMISSION
                            cost = total_amount + commission

                            if cost > balance:
                                continue

                            balance -= cost
                            positions[sid] = {
                                "qty": qty,
                                "avg_price": price,
                                "symbol": stock_symbols[sid],
                            }
                            trades.append({
                                "date": str(date),
                                "symbol": stock_symbols[sid],
                                "type": "BUY",
                                "quantity": qty,
                                "price": float(price),
                                "total_amount": float(total_amount),
                                "commission": float(commission),
                                "tax": 0.0,
                                "realized_pnl": None,
                            })

            scorer.close()

            # 마지막 날 미청산 포지션 강제 청산
            if positions and all_dates:
                last_date = all_dates[-1]
                for sid, pos in list(positions.items()):
                    if sid in stock_prices and last_date in stock_prices[sid].index:
                        price = stock_prices[sid].loc[last_date, "close"]
                    else:
                        price = pos["avg_price"]
                    qty = pos["qty"]
                    total_amount = price * qty
                    commission = total_amount * SELL_COMMISSION
                    tax = total_amount * SELL_TAX
                    net = total_amount - commission - tax
                    realized_pnl = net - (pos["avg_price"] * qty)
                    balance += net
                    trades.append({
                        "date": str(last_date),
                        "symbol": pos["symbol"],
                        "type": "SELL(CLOSE)",
                        "quantity": qty,
                        "price": float(price),
                        "total_amount": float(total_amount),
                        "commission": float(commission),
                        "tax": float(tax),
                        "realized_pnl": float(realized_pnl),
                    })
                positions.clear()

            # 성과 지표 계산
            final_balance = balance
            total_return = ((final_balance - initial_balance) / initial_balance) * 100

            sell_trades = [t for t in trades if t["type"] in ("SELL", "SELL(CLOSE)")]
            total_trades_count = len(sell_trades)
            win_trades_count = len([t for t in sell_trades if (t.get("realized_pnl") or 0) > 0])
            win_rate = (win_trades_count / total_trades_count * 100) if total_trades_count > 0 else 0

            # 샤프비율 (일별 수익률 기준, 무위험 수익률 0)
            daily_returns = pd.Series(daily_values).pct_change().dropna()
            sharpe_ratio = 0.0
            if len(daily_returns) > 1 and daily_returns.std() > 0:
                sharpe_ratio = float(
                    (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)
                )

            # 최대 낙폭 (MDD)
            cumulative = pd.Series(daily_values)
            peak = cumulative.cummax()
            drawdown = (cumulative - peak) / peak
            max_drawdown = float(drawdown.min()) * 100  # 퍼센트

            result = {
                "strategy_name": strategy_name,
                "start_date": start_date,
                "end_date": end_date,
                "initial_balance": initial_balance,
                "final_balance": round(final_balance, 0),
                "total_return": round(total_return, 2),
                "total_trades": total_trades_count,
                "win_trades": win_trades_count,
                "win_rate": round(win_rate, 2),
                "sharpe_ratio": round(sharpe_ratio, 4),
                "max_drawdown": round(max_drawdown, 2),
                "trade_details": trades,
            }

            # DB 저장
            backtest_result = BacktestResult(
                strategy_name=strategy_name,
                start_date=start,
                end_date=end,
                initial_balance=initial_balance,
                final_balance=round(final_balance, 0),
                total_return=round(total_return, 2),
                sharpe_ratio=round(sharpe_ratio, 4),
                max_drawdown=round(max_drawdown, 2),
                win_rate=round(win_rate, 2),
                total_trades=total_trades_count,
                win_trades=win_trades_count,
                strategy_type="scoring",
                trade_details=trades,
                parameters={
                    "buy_threshold": buy_threshold,
                    "sell_threshold": sell_threshold,
                    "max_positions": max_positions,
                    "budget_ratio": budget_ratio,
                },
            )
            self.db.add(backtest_result)
            self.db.commit()
            self.db.refresh(backtest_result)
            result["id"] = backtest_result.id

            logger.info(
                f"백테스팅 완료: {strategy_name} "
                f"({start_date}~{end_date}, 수익률 {total_return:.2f}%, 승률 {win_rate:.1f}%)"
            )
            return result

        except Exception as e:
            logger.error(f"백테스팅 실패: {e}")
            return None

    def get_result(self, result_id: int) -> Optional[BacktestResult]:
        """백테스팅 결과 조회"""
        return self.db.query(BacktestResult).filter(BacktestResult.id == result_id).first()

    def get_results(self, limit: int = 20) -> list[BacktestResult]:
        """백테스팅 결과 목록"""
        return (
            self.db.query(BacktestResult)
            .order_by(BacktestResult.created_at.desc())
            .limit(limit)
            .all()
        )
