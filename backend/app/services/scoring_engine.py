"""
스코어링 엔진

기술적 지표(RSI, MACD, 볼린저밴드, EMA) + RF 예측을 결합하여
종목별 통합 스코어(0~100)를 산출하고 매매 신호를 판정한다.

가중치:
  RSI 0.20, MACD 0.20, 볼린저밴드 0.15, EMA 0.15, RF 예측 0.30

신호: ≥70 BUY, ≤30 SELL, 그 외 HOLD
"""

import logging
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.stock import Stock, StockPrice, TechnicalIndicator
from app.models.stock_score import StockScore
from app.services.technical_indicators import TechnicalIndicatorCalculator
from app.services.prediction_model import PredictionModel

logger = logging.getLogger(__name__)

# 가중치
WEIGHTS = {
    "rsi": 0.20,
    "macd": 0.20,
    "bollinger": 0.15,
    "ema": 0.15,
    "prediction": 0.30,
}

# 신호 임계값
BUY_THRESHOLD = 70
SELL_THRESHOLD = 30


class ScoringEngine:
    """종목 스코어링 엔진"""

    def __init__(self, db: Optional[Session] = None):
        self.db = db or SessionLocal()
        self._owns_db = db is None
        self.indicator_calc = TechnicalIndicatorCalculator()
        self.prediction_model = PredictionModel()

    def close(self):
        if self._owns_db:
            self.db.close()

    # ── 개별 지표 스코어 (0~100) ──

    @staticmethod
    def _rsi_score(rsi: float) -> float:
        """RSI → 스코어: 과매도(RSI<30)=높은 점수, 과매수(RSI>70)=낮은 점수"""
        if np.isnan(rsi):
            return 50.0
        # RSI 30 이하 → 매수 기회 (100점 방향)
        # RSI 70 이상 → 매도 경고 (0점 방향)
        return float(np.clip(100 - rsi, 0, 100))

    @staticmethod
    def _macd_score(macd: float, signal: float, histogram: float) -> float:
        """MACD → 스코어: 골든크로스(MACD>Signal)=높은 점수"""
        if any(np.isnan(v) for v in [macd, signal, histogram]):
            return 50.0
        # 히스토그램 양수(MACD>Signal) → 상승 추세
        # 정규화: 히스토그램 값을 -1~1 범위로 보고 0~100으로 변환
        normalized = np.tanh(histogram * 0.1)  # tanh로 -1~1 정규화
        return float(np.clip((normalized + 1) * 50, 0, 100))

    @staticmethod
    def _bollinger_score(price: float, upper: float, lower: float, middle: float) -> float:
        """볼린저밴드 → 스코어: 하단 근접=높은 점수(매수 기회)"""
        if any(np.isnan(v) for v in [price, upper, lower, middle]):
            return 50.0
        band_width = upper - lower
        if band_width == 0:
            return 50.0
        # 가격이 하단밴드에 가까울수록 100, 상단밴드에 가까울수록 0
        position = (upper - price) / band_width
        return float(np.clip(position * 100, 0, 100))

    @staticmethod
    def _ema_score(price: float, ema_20: float, ema_50: float) -> float:
        """EMA → 스코어: 상승 추세(EMA20>EMA50, 가격>EMA20)=높은 점수"""
        if any(np.isnan(v) for v in [price, ema_20, ema_50]):
            return 50.0
        score = 50.0
        # EMA 20이 EMA 50 위 → 상승 추세
        if ema_20 > ema_50:
            score += 25.0
        else:
            score -= 25.0
        # 가격이 EMA 20 위 → 추가 상승 신호
        if price > ema_20:
            score += 25.0
        else:
            score -= 25.0
        return float(np.clip(score, 0, 100))

    @staticmethod
    def _prediction_score(predicted_change_pct: float) -> float:
        """RF 예측 변동률 → 스코어: 상승 예측=높은 점수"""
        if np.isnan(predicted_change_pct):
            return 50.0
        # 예측 변동률을 스코어로 변환 (±5% → 0~100)
        normalized = np.tanh(predicted_change_pct / 5.0)
        return float(np.clip((normalized + 1) * 50, 0, 100))

    # ── 통합 스코어 계산 ──

    def score_stock(self, stock_id: int, symbol: str) -> Optional[dict]:
        """단일 종목 스코어링

        Returns:
            {
                "stock_id", "symbol", "rsi_score", "macd_score",
                "bollinger_score", "ema_score", "prediction_score",
                "total_score", "signal"
            }
        """
        try:
            # 기술적 지표 계산
            indicators = self.indicator_calc.calculate_all_indicators(stock_id)
            if not indicators:
                logger.warning(f"지표 데이터 없음: {symbol}")
                return None

            # 최신 값 추출
            rsi_val = indicators.get("rsi", pd.Series()).dropna()
            macd_val = indicators.get("macd", pd.Series()).dropna()
            signal_val = indicators.get("signal", pd.Series()).dropna()
            histogram_val = indicators.get("histogram", pd.Series()).dropna()
            upper_val = indicators.get("upper", pd.Series()).dropna()
            lower_val = indicators.get("lower", pd.Series()).dropna()
            middle_val = indicators.get("middle", pd.Series()).dropna()
            ema_20_val = indicators.get("ema_20", pd.Series()).dropna()
            ema_50_val = indicators.get("ema_50", pd.Series()).dropna()

            # 최신 종가
            prices_df = self.indicator_calc.get_stock_prices(stock_id)
            if prices_df.empty:
                return None
            current_price = prices_df["close"].iloc[-1]

            # 개별 스코어 계산
            rsi_s = self._rsi_score(rsi_val.iloc[-1] if len(rsi_val) > 0 else float("nan"))
            macd_s = self._macd_score(
                macd_val.iloc[-1] if len(macd_val) > 0 else float("nan"),
                signal_val.iloc[-1] if len(signal_val) > 0 else float("nan"),
                histogram_val.iloc[-1] if len(histogram_val) > 0 else float("nan"),
            )
            bollinger_s = self._bollinger_score(
                current_price,
                upper_val.iloc[-1] if len(upper_val) > 0 else float("nan"),
                lower_val.iloc[-1] if len(lower_val) > 0 else float("nan"),
                middle_val.iloc[-1] if len(middle_val) > 0 else float("nan"),
            )
            ema_s = self._ema_score(
                current_price,
                ema_20_val.iloc[-1] if len(ema_20_val) > 0 else float("nan"),
                ema_50_val.iloc[-1] if len(ema_50_val) > 0 else float("nan"),
            )

            # RF 예측 스코어
            prediction = self.prediction_model.predict_next_day(stock_id)
            pred_change_pct = prediction["price_change_percent"] if prediction else 0.0
            pred_s = self._prediction_score(pred_change_pct)

            # 가중 평균
            total = (
                rsi_s * WEIGHTS["rsi"]
                + macd_s * WEIGHTS["macd"]
                + bollinger_s * WEIGHTS["bollinger"]
                + ema_s * WEIGHTS["ema"]
                + pred_s * WEIGHTS["prediction"]
            )
            total = round(float(np.clip(total, 0, 100)), 2)

            # 신호 판정
            if total >= BUY_THRESHOLD:
                signal = "BUY"
            elif total <= SELL_THRESHOLD:
                signal = "SELL"
            else:
                signal = "HOLD"

            return {
                "stock_id": stock_id,
                "symbol": symbol,
                "rsi_score": round(rsi_s, 2),
                "macd_score": round(macd_s, 2),
                "bollinger_score": round(bollinger_s, 2),
                "ema_score": round(ema_s, 2),
                "prediction_score": round(pred_s, 2),
                "total_score": total,
                "signal": signal,
            }

        except Exception as e:
            logger.error(f"스코어링 실패 ({symbol}): {e}")
            return None

    def score_all_stocks(self) -> list[dict]:
        """전 종목 스코어링 실행 → DB 저장 → 결과 반환"""
        stocks = self.db.query(Stock).all()
        results = []

        for stock in stocks:
            score_data = self.score_stock(stock.id, stock.symbol)
            if score_data is None:
                continue

            # DB 저장
            stock_score = StockScore(
                stock_id=score_data["stock_id"],
                symbol=score_data["symbol"],
                date=datetime.utcnow(),
                rsi_score=score_data["rsi_score"],
                macd_score=score_data["macd_score"],
                bollinger_score=score_data["bollinger_score"],
                ema_score=score_data["ema_score"],
                prediction_score=score_data["prediction_score"],
                total_score=score_data["total_score"],
                signal=score_data["signal"],
            )
            self.db.add(stock_score)
            results.append(score_data)

        self.db.commit()
        # 스코어 내림차순 정렬
        results.sort(key=lambda x: x["total_score"], reverse=True)
        logger.info(f"전 종목 스코어링 완료: {len(results)}종목")
        return results

    def get_latest_scores(self, limit: int = 20) -> list[StockScore]:
        """최신 스코어 상위 N개 조회"""
        # 각 종목별 최신 스코어만 가져오기 위해 서브쿼리 사용
        from sqlalchemy import func

        subq = (
            self.db.query(
                StockScore.stock_id,
                func.max(StockScore.id).label("max_id"),
            )
            .group_by(StockScore.stock_id)
            .subquery()
        )

        scores = (
            self.db.query(StockScore)
            .join(subq, StockScore.id == subq.c.max_id)
            .order_by(StockScore.total_score.desc())
            .limit(limit)
            .all()
        )
        return scores
