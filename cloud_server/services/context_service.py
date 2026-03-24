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

# 한국 공휴일 (2026년). 매년 초 갱신 필요.
KOREAN_HOLIDAYS_2026 = {
    "2026-01-01",  # 신정
    "2026-01-28",  # 설날 전날 (수)
    "2026-01-29",  # 설날 (목)
    "2026-01-30",  # 설날 다음날 (금)
    "2026-03-01",  # 삼일절
    "2026-05-05",  # 어린이날
    "2026-05-24",  # 부처님 오신 날
    "2026-06-06",  # 현충일
    "2026-08-15",  # 광복절
    "2026-09-24",  # 추석 전날
    "2026-09-25",  # 추석
    "2026-09-26",  # 추석 다음날
    "2026-10-03",  # 개천절
    "2026-10-09",  # 한글날
    "2026-12-25",  # 크리스마스
}
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


def _calc_macd(prices: pd.Series) -> tuple[float | None, float | None]:
    """MACD (12, 26, 9) 계산. Returns: (macd, signal)"""
    if len(prices) < 35:
        return None, None
    ema12 = prices.ewm(span=12).mean()
    ema26 = prices.ewm(span=26).mean()
    macd_line = ema12 - ema26
    signal = macd_line.ewm(span=9).mean()
    m = macd_line.iloc[-1]
    s = signal.iloc[-1]
    if np.isnan(m) or np.isnan(s):
        return None, None
    return round(float(m), 2), round(float(s), 2)


def _calc_bollinger(prices: pd.Series, period: int = 20) -> tuple[float | None, float | None]:
    """볼린저 밴드 (상단, 하단). Returns: (upper, lower)"""
    if len(prices) < period:
        return None, None
    sma = prices.rolling(period).mean()
    std = prices.rolling(period).std()
    upper = sma + 2 * std
    lower = sma - 2 * std
    u, l = upper.iloc[-1], lower.iloc[-1]
    if np.isnan(u) or np.isnan(l):
        return None, None
    return round(float(u), 2), round(float(l), 2)


class ContextService:
    """시장 컨텍스트 계산"""

    def __init__(self, db: Session):
        self.db = db

    def get_symbol_context(self, symbol: str) -> dict:
        """종목별 기술적 지표 계산."""
        prices = self._get_prices(symbol)
        if prices is None or len(prices) < _RSI_PERIOD + 1:
            return {
                "symbol": symbol,
                "current_price": None,
                "rsi_14": None, "rsi_21": None,
                "macd": None, "macd_signal": None,
                "bollinger_upper": None, "bollinger_lower": None,
                "volatility": None,
            }
        macd, macd_signal = _calc_macd(prices)
        b_upper, b_lower = _calc_bollinger(prices)
        return {
            "symbol": symbol,
            "current_price": round(float(prices.iloc[-1]), 2),
            "rsi_14": _calc_rsi(prices, 14),
            "rsi_21": _calc_rsi(prices, 21),
            "macd": macd,
            "macd_signal": macd_signal,
            "bollinger_upper": b_upper,
            "bollinger_lower": b_lower,
            "volatility": _calc_volatility(prices),
        }

    def _get_prices(self, symbol: str) -> pd.Series | None:
        """DB 조회 → yfinance fallback으로 종가 시리즈 반환."""
        bars = self.db.query(DailyBar).filter(
            DailyBar.symbol == symbol
        ).order_by(DailyBar.date.desc()).limit(_LOOKBACK).all()
        if len(bars) >= _RSI_PERIOD + 1:
            return pd.Series([b.close for b in reversed(bars)], dtype=float)
        return self._fetch_yfinance(symbol)

    def get_current_context(self) -> dict:
        """
        최신 시장 컨텍스트 계산.

        1차: cloud_server DB의 DailyBar 데이터 사용
        2차 폴백: yfinance 직접 조회 (DB 데이터 없을 때)
        """
        today_str = datetime.now(tz=timezone.utc).date().isoformat()
        result = {
            "date": today_str,
            "computed_at": datetime.now(tz=timezone.utc).isoformat(),
            "market": {},
            "is_holiday": today_str in KOREAN_HOLIDAYS_2026,
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
