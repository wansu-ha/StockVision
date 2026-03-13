"""
yfinance 보조 수집 서비스

해외 지수, 환율, 국내 지수(^KS11, ^KQ11) 수집.
키움 WS로 수집하지 못하는 데이터 보완.
"""
import logging
from datetime import date, timedelta

import numpy as np
import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

# yfinance 심볼 → 내부 심볼 매핑
_SYMBOL_MAP = {
    "^KS11": "^KS11",   # KOSPI
    "^KQ11": "^KQ11",   # KOSDAQ
    "^GSPC": "^GSPC",   # S&P 500
    "^DJI":  "^DJI",    # Dow Jones
    "^IXIC": "^IXIC",   # NASDAQ
    "USDKRW=X": "USDKRW",  # 환율
}

# 수집 대상 기본 심볼 목록
DEFAULT_SYMBOLS = list(_SYMBOL_MAP.keys())


class YFinanceService:
    """yfinance 기반 데이터 수집"""

    def fetch_daily(
        self,
        symbols: list[str],
        start_date: date,
        end_date: date,
    ) -> dict[str, list[dict]]:
        """
        지정 심볼의 일봉 데이터 수집.

        Returns:
            {symbol: [{"date": date, "open": int, "high": int, "low": int, "close": int, "volume": int}]}
        """
        result: dict[str, list[dict]] = {}

        for symbol in symbols:
            try:
                df = yf.download(
                    symbol,
                    start=start_date.isoformat(),
                    end=(end_date + timedelta(days=1)).isoformat(),
                    auto_adjust=True,
                    progress=False,
                )

                if df.empty:
                    logger.warning(f"yfinance 데이터 없음: {symbol}")
                    continue

                # MultiIndex 처리 (여러 종목 동시 다운로드 시)
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.droplevel(1)

                bars = []
                for ts, row in df.iterrows():
                    close_val = row.get("Close")
                    if close_val is None or (isinstance(close_val, float) and np.isnan(close_val)):
                        continue

                    # yfinance는 float 반환 → 원 단위로 변환 (지수/환율은 소수 유지 위해 float 사용)
                    bars.append({
                        "date": ts.date() if hasattr(ts, "date") else ts,
                        "open": self._to_int(row.get("Open")),
                        "high": self._to_int(row.get("High")),
                        "low": self._to_int(row.get("Low")),
                        "close": self._to_int(close_val),
                        "volume": int(row.get("Volume", 0)),
                        "change_pct": self._calc_change_pct(df, ts),
                    })

                # 내부 심볼로 매핑
                internal_symbol = _SYMBOL_MAP.get(symbol, symbol)
                result[internal_symbol] = bars
                logger.info(f"yfinance 수집 완료: {symbol} ({len(bars)}봉)")

            except Exception as e:
                logger.error(f"yfinance 수집 실패 {symbol}: {e}")

        return result

    def fetch_recent(self, symbols: list[str], days: int = 1) -> dict[str, list[dict]]:
        """최근 N일 데이터 수집"""
        end_date = date.today()
        start_date = end_date - timedelta(days=days + 5)  # 주말/공휴일 여유
        return self.fetch_daily(symbols, start_date, end_date)

    @staticmethod
    def _to_int(value) -> int | None:
        """float → int 변환 (None/NaN 처리)"""
        if value is None:
            return None
        try:
            f = float(value)
            if np.isnan(f):
                return None
            return int(f)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _calc_change_pct(df: pd.DataFrame, ts) -> float | None:
        """전일 대비 등락률 계산"""
        try:
            idx = df.index.get_loc(ts)
            if idx == 0:
                return None
            prev_close = df["Close"].iloc[idx - 1]
            curr_close = df["Close"].iloc[idx]
            if prev_close and prev_close != 0:
                return round((float(curr_close) - float(prev_close)) / float(prev_close) * 100, 4)
        except Exception:
            pass
        return None
