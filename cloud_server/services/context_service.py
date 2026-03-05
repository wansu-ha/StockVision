"""
AI 컨텍스트 계산 서비스

시세 DB에서 지표 계산 (RSI, EMA, 변동성 등).
v1: 지표 계산만 (Claude 호출 없음)
v2: Claude API 호출 추가 (ai_service.py 사용)
"""
import logging
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import yfinance as yf
from sqlalchemy.orm import Session

from cloud_server.models.market import DailyBar

logger = logging.getLogger(__name__)

_RSI_PERIOD = 14
_VOL_PERIOD = 20
_LOOKBACK = 60

# 컨텍스트에서 사용 가능한 변수 목록
AVAILABLE_VARIABLES = [
    "market_kospi_rsi",
    "market_kosdaq_rsi",
    "market_kospi_ema",
    "market_volatility",
    "rsi_14",
    "rsi_21",
    "macd",
    "macd_signal",
    "bollinger_upper",
    "bollinger_lower",
    "current_price",
]


def _calc_rsi(prices: pd.Series, period: int = _RSI_PERIOD) -> float | None:
    """RSI 계산"""
    if len(prices) < period + 1:
        return None
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    val = rsi.iloc[-1]
    return round(float(val), 2) if not np.isnan(val) else None


def _calc_ema(prices: pd.Series, period: int = 20) -> float | None:
    """EMA 계산"""
    if len(prices) < period:
        return None
    ema = prices.ewm(span=period).mean()
    val = ema.iloc[-1]
    return round(float(val), 2) if not np.isnan(val) else None


def _calc_volatility(prices: pd.Series, period: int = _VOL_PERIOD) -> float | None:
    """연율화 변동성 계산"""
    if len(prices) < period + 1:
        return None
    returns = prices.pct_change().dropna()
    vol = returns.tail(period).std() * np.sqrt(252)
    return round(float(vol), 4) if not np.isnan(vol) else None


class ContextService:
    """시장 컨텍스트 계산"""

    def __init__(self, db: Session):
        self.db = db

    def get_current_context(self) -> dict:
        """
        최신 시장 컨텍스트 계산.

        1차: cloud_server DB의 DailyBar 데이터 사용
        2차 폴백: yfinance 직접 조회 (DB 데이터 없을 때)
        """
        result = {
            "date": datetime.now(tz=timezone.utc).date().isoformat(),
            "computed_at": datetime.now(tz=timezone.utc).isoformat(),
            "market": {},
            "version": 1,
        }

        indices = {"kospi": "^KS11", "kosdaq": "^KQ11"}

        for key, symbol in indices.items():
            bars = self.db.query(DailyBar).filter(
                DailyBar.symbol == symbol
            ).order_by(DailyBar.date.desc()).limit(_LOOKBACK).all()

            if len(bars) >= _RSI_PERIOD + 1:
                # DB 데이터 사용
                prices = pd.Series([b.close for b in reversed(bars)], dtype=float)
            else:
                # yfinance 폴백
                prices = self._fetch_yfinance(symbol)

            if prices is None or len(prices) < _RSI_PERIOD + 1:
                logger.warning(f"{symbol} 데이터 부족")
                continue

            rsi = _calc_rsi(prices)
            result["market"][f"{key}_rsi"] = rsi

            if key == "kospi":
                result["market"]["kospi_ema_20"] = _calc_ema(prices, 20)
                result["market"]["volatility"] = _calc_volatility(prices)
                result["market"]["market_trend"] = self._trend(rsi)

        return result

    def _fetch_yfinance(self, symbol: str) -> pd.Series | None:
        """yfinance 폴백 조회"""
        try:
            df = yf.download(symbol, period=f"{_LOOKBACK}d", auto_adjust=True, progress=False)
            if df.empty:
                return None
            close = df["Close"].squeeze()
            return close
        except Exception as e:
            logger.error(f"yfinance 폴백 실패 {symbol}: {e}")
            return None

    @staticmethod
    def _trend(rsi: float | None) -> str:
        if rsi is None:
            return "unknown"
        if rsi > 60:
            return "bullish"
        if rsi < 40:
            return "bearish"
        return "neutral"
