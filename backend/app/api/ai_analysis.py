import warnings
import logging
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import random

from ..core.database import get_db
from ..models.stock import Stock, TechnicalIndicator, StockPrice

router = APIRouter()
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# 내부 헬퍼 함수
# ─────────────────────────────────────────────

def _get_latest_indicators(stock_id: int, db: Session) -> Dict[str, float]:
    """종목의 최신 기술적 지표 조회"""
    result = {}
    for itype in ['rsi', 'macd', 'signal', 'ema_20', 'ema_50', 'upper', 'lower', 'middle']:
        row = (
            db.query(TechnicalIndicator)
            .filter(
                TechnicalIndicator.stock_id == stock_id,
                TechnicalIndicator.indicator_type == itype,
            )
            .order_by(TechnicalIndicator.date.desc())
            .first()
        )
        if row:
            result[itype] = row.value
    return result


def _compute_technical_analysis(indicators: Dict[str, float]) -> Dict[str, Any]:
    """실제 지표값 기반 기술적 분석"""
    rsi = indicators.get('rsi')
    macd = indicators.get('macd')
    signal = indicators.get('signal')
    ema_20 = indicators.get('ema_20')
    ema_50 = indicators.get('ema_50')
    bb_upper = indicators.get('upper')
    bb_lower = indicators.get('lower')

    # RSI 신호
    if rsi is not None:
        if rsi > 70:
            rsi_signal = '과매수'
        elif rsi < 30:
            rsi_signal = '과매도'
        else:
            rsi_signal = '중립'
    else:
        rsi_signal = 'N/A'

    # MACD 신호
    if macd is not None and signal is not None:
        macd_signal = '매수 신호' if macd > signal else '매도 신호'
    else:
        macd_signal = 'N/A'

    # 추세 강도 (EMA 기반)
    if ema_20 is not None and ema_50 is not None:
        if ema_20 > ema_50 * 1.01:
            trend_strength = '강함'
        elif ema_20 < ema_50 * 0.99:
            trend_strength = '약함'
        else:
            trend_strength = '보통'
    else:
        trend_strength = '보통'

    return {
        'trend_strength': trend_strength,
        'support_level': round(bb_lower) if bb_lower else None,
        'resistance_level': round(bb_upper) if bb_upper else None,
        'rsi_signal': rsi_signal,
        'macd_signal': macd_signal,
        'volume_trend': '보통',
        'price_momentum': trend_strength,
        'volatility_level': '보통',
    }


def _compute_investment_opinion(technical: Dict[str, Any]) -> Dict[str, Any]:
    """기술적 분석 기반 투자 의견"""
    score = 0
    if technical.get('trend_strength') == '강함':
        score += 1
    elif technical.get('trend_strength') == '약함':
        score -= 1
    if technical.get('rsi_signal') == '과매도':
        score += 1
    elif technical.get('rsi_signal') == '과매수':
        score -= 1
    if technical.get('macd_signal') == '매수 신호':
        score += 1
    elif technical.get('macd_signal') == '매도 신호':
        score -= 1

    if score >= 2:
        rec, conf = '강력매수', '높음'
    elif score == 1:
        rec, conf = '매수', '보통'
    elif score == -1:
        rec, conf = '매도', '보통'
    elif score <= -2:
        rec, conf = '강력매도', '높음'
    else:
        rec, conf = '중립', '보통'

    rsi_s = technical.get('rsi_signal', 'N/A')
    macd_s = technical.get('macd_signal', 'N/A')
    trend_s = technical.get('trend_strength', 'N/A')

    return {
        'recommendation': rec,
        'confidence_level': conf,
        'reasoning': f'RSI {rsi_s}, MACD {macd_s}, 추세 {trend_s} 기반 종합 분석 결과입니다.',
        'risk_reward_ratio': round(max(1.0, 1.5 + score * 0.3), 1),
        'time_horizon': '중기(3-12개월)',
    }


def _get_price_targets(stock_id: int, current_price: float) -> Dict[str, Any]:
    """예측 모델 기반 가격 목표 (실패 시 현재가 기반 추정)"""
    try:
        warnings.filterwarnings('ignore')
        from app.services.prediction_model import PredictionModel
        model = PredictionModel()
        pred = model.predict_next_day(stock_id)
        if pred:
            change_pct = pred['price_change_percent']
            predicted = pred['predicted_price']
            return {
                'short_term': round(predicted),
                'medium_term': round(current_price * (1 + change_pct / 100 * 3)),
                'long_term': round(current_price * (1 + change_pct / 100 * 6)),
                'upside_potential': round(max(change_pct, 0) * 3, 1),
                'downside_risk': round(abs(min(change_pct, 0)) * 3, 1),
            }
    except Exception as e:
        logger.warning(f"예측 모델 실패 (stock_id={stock_id}): {e}")

    return {
        'short_term': round(current_price * 1.03),
        'medium_term': round(current_price * 1.08),
        'long_term': round(current_price * 1.15),
        'upside_potential': 10.0,
        'downside_risk': 5.0,
    }


# ─────────────────────────────────────────────
# AI 분석 서비스
# ─────────────────────────────────────────────

class AIAnalysisService:
    """AI 주식 분석 서비스"""

    def generate_market_overview(self, db: Optional[Session] = None) -> Dict[str, Any]:
        """전반적인 주식시장 분석 — DB 데이터 우선, 없으면 중립"""
        market_sentiment = 'neutral'
        sentiment_score = 0.5

        if db:
            stocks = db.query(Stock).all()
            rsi_values = []
            for stock in stocks:
                row = (
                    db.query(TechnicalIndicator)
                    .filter(
                        TechnicalIndicator.stock_id == stock.id,
                        TechnicalIndicator.indicator_type == 'rsi',
                    )
                    .order_by(TechnicalIndicator.date.desc())
                    .first()
                )
                if row:
                    rsi_values.append(row.value)

            if rsi_values:
                avg_rsi = sum(rsi_values) / len(rsi_values)
                if avg_rsi > 60:
                    market_sentiment = 'bullish'
                    sentiment_score = round(min(0.5 + (avg_rsi - 60) / 80, 1.0), 2)
                elif avg_rsi < 40:
                    market_sentiment = 'bearish'
                    sentiment_score = round(max(avg_rsi / 80, 0.0), 2)
                else:
                    market_sentiment = 'neutral'
                    sentiment_score = round(avg_rsi / 100, 2)

        if market_sentiment == 'bullish':
            return {
                "overall_sentiment": "긍정적",
                "sentiment_score": sentiment_score,
                "market_trend": "상승 추세",
                "key_factors": [
                    "기술적 지표 전반 강세 신호",
                    "RSI 평균 과매수 미만 상승",
                    "MACD 골든크로스 종목 다수",
                    "EMA 상향 배열 유지",
                ],
                "risk_level": "보통",
                "investment_advice": "단계적 매수 전략 권장",
                "sector_outlook": {
                    "반도체": "강세 지속",
                    "인터넷": "안정적 성장",
                    "자동차": "점진적 개선",
                    "화학": "변동성 주의",
                },
                "market_volatility": "보통",
                "liquidity_condition": "양호",
                "analysis_timestamp": datetime.now().isoformat(),
            }
        elif market_sentiment == 'bearish':
            return {
                "overall_sentiment": "부정적",
                "sentiment_score": sentiment_score,
                "market_trend": "하락 압력",
                "key_factors": [
                    "RSI 과매도 종목 증가",
                    "MACD 데드크로스 신호",
                    "EMA 하향 배열",
                    "변동성 확대",
                ],
                "risk_level": "높음",
                "investment_advice": "현금 비중 확대 및 손절 관리",
                "sector_outlook": {
                    "반도체": "조정 압력",
                    "인터넷": "상대적 안정",
                    "자동차": "수요 감소 우려",
                    "화학": "원자재 부담",
                },
                "market_volatility": "높음",
                "liquidity_condition": "보통",
                "analysis_timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "overall_sentiment": "중립적",
                "sentiment_score": sentiment_score,
                "market_trend": "횡보 조정",
                "key_factors": [
                    "기술적 지표 혼재",
                    "종목별 차별화 장세",
                    "거래량 평균 수준",
                    "방향성 탐색 구간",
                ],
                "risk_level": "보통",
                "investment_advice": "분산 투자 및 리스크 관리 강화",
                "sector_outlook": {
                    "반도체": "조정 후 반등 기대",
                    "인터넷": "안정적",
                    "자동차": "정책 영향 주시",
                    "화학": "원자재 가격 변동",
                },
                "market_volatility": "보통",
                "liquidity_condition": "보통",
                "analysis_timestamp": datetime.now().isoformat(),
            }

    @staticmethod
    def generate_stock_analysis(stock: Stock, db: Session) -> Dict[str, Any]:
        """개별 주식 AI 분석 — 실제 지표 + 예측 모델"""
        indicators = _get_latest_indicators(stock.id, db)
        technical = _compute_technical_analysis(indicators)
        investment_opinion = _compute_investment_opinion(technical)

        # 현재가 조회
        price_row = (
            db.query(StockPrice)
            .filter(StockPrice.stock_id == stock.id)
            .order_by(StockPrice.date.desc())
            .first()
        )
        current_price = price_row.close if price_row else 50000

        price_targets = _get_price_targets(stock.id, current_price)

        return {
            "stock_symbol": stock.symbol,
            "stock_name": stock.name,
            "analysis_timestamp": datetime.now().isoformat(),
            "technical_analysis": technical,
            "news_analysis": AIAnalysisService._generate_news_analysis(stock),
            "sentiment_analysis": AIAnalysisService._analyze_investor_sentiment(stock, current_price),
            "investment_opinion": investment_opinion,
            "risk_assessment": AIAnalysisService._assess_risk(stock),
            "price_targets": price_targets,
            "holding_period": AIAnalysisService._recommend_holding_period(stock),
        }

    @staticmethod
    def _generate_news_analysis(stock: Stock) -> Dict[str, Any]:
        """뉴스 분석 — 실제 뉴스 API 없으므로 텍스트 기반"""
        news_topics = ["기업 실적 발표", "신제품 출시", "업계 동향", "글로벌 시장 영향", "규제 환경"]
        sentiments = ['긍정적', '중립적', '부정적']
        impacts = ['높음', '보통', '낮음']

        return {
            "recent_news": [
                {
                    "topic": news_topics[0],
                    "sentiment": sentiments[1],
                    "impact_level": impacts[1],
                    "summary": f"{stock.name}의 최근 사업 동향이 시장에서 주목받고 있습니다.",
                },
                {
                    "topic": news_topics[4],
                    "sentiment": sentiments[1],
                    "impact_level": impacts[2],
                    "summary": f"{stock.sector} 섹터의 전반적인 동향이 {stock.name}에 미치는 영향이 분석되고 있습니다.",
                },
            ],
            "market_reaction": "중립적",
            "sector_influence": "보통",
            "news_sentiment_score": 0.5,
        }

    @staticmethod
    def _analyze_investor_sentiment(stock: Stock, current_price: float = 50000) -> Dict[str, Any]:
        """투자자 심리 — 현재가 기반 목표가 추정"""
        return {
            "retail_sentiment": "중립적",
            "institutional_sentiment": "중립적",
            "analyst_rating": "중립",
            "price_target_consensus": round(current_price * 1.1),
            "earnings_expectations": "유지",
            "short_interest": 10.0,
            "options_flow": "중립",
        }

    @staticmethod
    def _assess_risk(stock: Stock) -> Dict[str, Any]:
        """리스크 평가"""
        return {
            "overall_risk": "보통",
            "volatility_risk": "보통",
            "liquidity_risk": "낮음",
            "sector_risk": "보통",
            "company_specific_risk": "보통",
            "risk_factors": [
                "시장 변동성",
                "섹터 순환 조정",
                "글로벌 경제 불확실성",
                "환율 리스크",
            ],
        }

    @staticmethod
    def _recommend_holding_period(stock: Stock) -> Dict[str, Any]:
        """보유 기간 권장"""
        return {
            "recommended_period": "중기",
            "reasoning": f"{stock.sector} 섹터 성장 전망과 기술적 지표를 고려한 권장사항입니다.",
            "rebalancing_frequency": "분기 1회",
            "exit_strategy": "목표 수익률 달성 시 단계적 이익실현 권장",
        }


# ─────────────────────────────────────────────
# 라우터
# ─────────────────────────────────────────────

@router.get("/market-overview")
async def get_market_overview(db: Session = Depends(get_db)):
    """전반적인 주식시장 AI 분석"""
    try:
        ai_service = AIAnalysisService()
        analysis = ai_service.generate_market_overview(db)
        return {
            "success": True,
            "data": analysis,
            "message": "시장 분석이 성공적으로 생성되었습니다.",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"시장 분석 생성 오류: {e}")
        raise HTTPException(status_code=500, detail=f"시장 분석 생성 실패: {str(e)}")


@router.get("/stocks/{symbol}/analysis")
async def get_stock_analysis(symbol: str, db: Session = Depends(get_db)):
    """개별 주식 AI 분석"""
    try:
        stock = db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
        if not stock:
            raise HTTPException(status_code=404, detail=f"주식 {symbol}을 찾을 수 없습니다.")
        analysis = AIAnalysisService.generate_stock_analysis(stock, db)
        return {
            "success": True,
            "data": analysis,
            "message": f"{stock.name}의 AI 분석이 성공적으로 생성되었습니다.",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"주식 분석 생성 중 오류: {str(e)}")


@router.get("/sectors/{sector}/analysis")
async def get_sector_analysis(sector: str, db: Session = Depends(get_db)):
    """섹터별 AI 분석"""
    try:
        ai_service = AIAnalysisService()
        market_overview = ai_service.generate_market_overview(db)
        market_sentiment = market_overview["overall_sentiment"]

        if market_sentiment == "긍정적":
            outlook, growth = "강세 지속", "높음"
        elif market_sentiment == "부정적":
            outlook, growth = "조정 압력", "낮음"
        else:
            outlook, growth = "횡보 후 반등 기대", "보통"

        return {
            "success": True,
            "data": {
                "sector_name": sector,
                "overall_outlook": outlook,
                "growth_potential": growth,
                "key_drivers": ["기술 혁신", "소비자 선호도 변화", "글로벌 시장 확장"],
                "risk_factors": ["경기 순환성", "정책 변화", "경쟁 심화"],
                "analysis_timestamp": datetime.now().isoformat(),
            },
            "message": f"{sector} 섹터 분석이 성공적으로 생성되었습니다.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"섹터 분석 생성 중 오류: {str(e)}")


@router.get("/ai-insights/latest")
async def get_latest_ai_insights():
    """최신 AI 인사이트"""
    try:
        base_time = datetime.now()
        insights = [
            {
                "id": 1,
                "title": "한국 주식시장 기술적 지표 분석",
                "summary": "등록 종목들의 RSI, MACD, 볼린저 밴드 기반 시장 동향을 분석하였습니다.",
                "impact_level": "높음",
                "timestamp": base_time.isoformat(),
                "tags": ["기술적분석", "RSI", "MACD"],
            },
            {
                "id": 2,
                "title": "EMA 골든/데드크로스 모니터링",
                "summary": "EMA 20/50 교차 신호를 통한 추세 전환 포착 전략입니다.",
                "impact_level": "보통",
                "timestamp": (base_time - timedelta(hours=2)).isoformat(),
                "tags": ["EMA", "골든크로스", "추세"],
            },
            {
                "id": 3,
                "title": "볼린저 밴드 지지/저항 분석",
                "summary": "볼린저 밴드 상단/하단을 활용한 매매 시점 포착 전략입니다.",
                "impact_level": "보통",
                "timestamp": (base_time - timedelta(hours=4)).isoformat(),
                "tags": ["볼린저밴드", "지지선", "저항선"],
            },
        ]
        return {
            "success": True,
            "data": insights,
            "message": "최신 AI 인사이트를 성공적으로 조회했습니다.",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 인사이트 조회 중 오류: {str(e)}")
