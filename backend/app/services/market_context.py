"""
시장 컨텍스트 계산 서비스

- KOSPI(^KS11), KOSDAQ(^KQ11) 일봉 데이터 기반
- RSI(14), 20일 변동성, 시장 추세 계산
- 장 마감 후 1회 업데이트 (배치)
"""
import logging
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

_INDICES = {
    "kospi":  "^KS11",
    "kosdaq": "^KQ11",
}
_RSI_PERIOD  = 14
_VOL_PERIOD  = 20
_LOOKBACK    = 60  # 충분한 히스토리


def _rsi(prices: pd.Series, period: int = _RSI_PERIOD) -> float:
    delta = prices.diff()
    gain  = delta.where(delta > 0, 0).rolling(period).mean()
    loss  = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs    = gain / loss.replace(0, np.nan)
    rsi   = 100 - (100 / (1 + rs))
    return round(float(rsi.iloc[-1]), 2)


def _volatility_20d(prices: pd.Series) -> float:
    """연율화 20일 변동성"""
    returns = prices.pct_change().dropna()
    vol = returns.tail(_VOL_PERIOD).std() * np.sqrt(252)
    return round(float(vol), 4)


def _trend(rsi: float, vol: float) -> str:
    """단순 추세 분류"""
    if rsi > 60:
        return "bullish"
    if rsi < 40:
        return "bearish"
    return "neutral"


def compute_market_context() -> dict:
    """시장 컨텍스트 계산 — 장 마감 후 호출"""
    result: dict = {
        "date":        datetime.now(tz=timezone.utc).date().isoformat(),
        "computed_at": datetime.now(tz=timezone.utc).isoformat(),
        "market":      {},
        "sectors":     {},
    }

    for key, ticker in _INDICES.items():
        try:
            df = yf.download(ticker, period=f"{_LOOKBACK}d", auto_adjust=True, progress=False)
            if df.empty or len(df) < _RSI_PERIOD + 1:
                logger.warning(f"{ticker} 데이터 부족")
                continue
            prices = df["Close"].squeeze()
            rsi    = _rsi(prices)
            vol    = _volatility_20d(prices)
            result["market"][f"{key}_rsi_14"]         = rsi
            result["market"][f"{key}_20d_volatility"] = vol
            if key == "kospi":
                result["market"]["market_trend"] = _trend(rsi, vol)
        except Exception as e:
            logger.error(f"{ticker} 계산 실패: {e}")

    return result
