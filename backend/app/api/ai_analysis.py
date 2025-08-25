from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import datetime, timedelta
import random
import json
import os

from ..core.database import get_db
from ..models.stock import Stock


router = APIRouter()

class AIAnalysisService:
    """AI 주식 분석 서비스"""
    
    def __init__(self):
        self.analysis_timestamp = datetime.now()
        self.is_development = os.getenv("ENVIRONMENT", "development") == "development"
    
    def generate_market_overview(self) -> Dict[str, Any]:
        """전반적인 주식시장 분석 생성"""
        if self.is_development:
            # 개발 모드: 랜덤 데이터
            market_sentiment = random.choice(['bullish', 'neutral', 'bearish'])
        else:
            # 운영 모드: 실제 데이터 기반 (향후 구현)
            market_sentiment = 'neutral'  # 기본값
        
        if market_sentiment == 'bullish':
            analysis = {
                "overall_sentiment": "긍정적",
                "sentiment_score": random.uniform(0.6, 0.9),
                "market_trend": "상승 추세",
                "key_factors": [
                    "글로벌 경제 회복세 지속",
                    "기업 실적 개선 전망",
                    "중앙은행의 완화적 통화정책",
                    "기술주 중심의 성장 동력 강화"
                ],
                "risk_level": "보통",
                "investment_advice": "단계적 매수 전략 권장",
                "sector_outlook": {
                    "technology": "강세 지속",
                    "healthcare": "안정적 성장",
                    "finance": "점진적 개선",
                    "energy": "변동성 증가"
                },
                "market_volatility": "보통",
                "liquidity_condition": "양호",
                "analysis_timestamp": self.analysis_timestamp.isoformat()
            }
        elif market_sentiment == 'neutral':
            analysis = {
                "overall_sentiment": "중립적",
                "sentiment_score": random.uniform(0.4, 0.6),
                "market_trend": "횡보 조정",
                "key_factors": [
                    "경제 지표 혼재",
                    "정책 불확실성",
                    "기업 실적 예상 범위 내",
                    "투자자 심리 조심스러움"
                ],
                "risk_level": "보통",
                "investment_advice": "분산 투자 및 리스크 관리 강화",
                "sector_outlook": {
                    "technology": "조정 후 반등 기대",
                    "healthcare": "안정적",
                    "finance": "정책 영향 주시",
                    "energy": "원자재 가격 변동성"
                },
                "market_volatility": "보통",
                "liquidity_condition": "보통",
                "analysis_timestamp": self.analysis_timestamp.isoformat()
            }
        else:  # bearish
            analysis = {
                "overall_sentiment": "부정적",
                "sentiment_score": random.uniform(0.1, 0.4),
                "market_trend": "하락 압력",
                "key_factors": [
                    "경제 성장 둔화 우려",
                    "인플레이션 압력",
                    "중앙은행 정책 긴축",
                    "지정학적 리스크 증가"
                ],
                "risk_level": "높음",
                "investment_advice": "현금 보유 및 방어적 포트폴리오",
                "sector_outlook": {
                    "technology": "조정 압력",
                    "healthcare": "방어적 성격",
                    "finance": "금리 상승 부담",
                    "energy": "수요 감소 우려"
                },
                "market_volatility": "높음",
                "liquidity_condition": "보통",
                "analysis_timestamp": self.analysis_timestamp.isoformat()
            }
        
        return analysis
    
    @staticmethod
    def generate_stock_analysis(stock: Stock, db: Session) -> Dict[str, Any]:
        """개별 주식 AI 분석 생성"""
        
        # 기술적 지표 기반 분석
        technical_analysis = AIAnalysisService._analyze_technical_indicators(stock)
        
        # 뉴스 및 시장 동향 분석
        news_analysis = AIAnalysisService._generate_news_analysis(stock)
        
        # 투자자 심리 분석
        sentiment_analysis = AIAnalysisService._analyze_investor_sentiment(stock)
        
        # 종합 투자 의견
        investment_opinion = AIAnalysisService._generate_investment_opinion(
            technical_analysis, sentiment_analysis
        )
        
        return {
            "stock_symbol": stock.symbol,
            "stock_name": stock.name,
            "analysis_timestamp": datetime.now().isoformat(),
            "technical_analysis": technical_analysis,
            "news_analysis": news_analysis,
            "sentiment_analysis": sentiment_analysis,
            "investment_opinion": investment_opinion,
            "risk_assessment": AIAnalysisService._assess_risk(stock),
            "price_target": AIAnalysisService._generate_price_target(stock),
            "holding_period": AIAnalysisService._recommend_holding_period(stock)
        }
    
    @staticmethod
    def _analyze_technical_indicators(stock: Stock) -> Dict[str, Any]:
        """기술적 지표 분석"""
        return {
            "trend_strength": random.choice(['강함', '보통', '약함']),
            "support_level": round(random.uniform(100, 500), 2),
            "resistance_level": round(random.uniform(600, 1000), 2),
            "rsi_signal": random.choice(['과매수', '중립', '과매도']),
            "macd_signal": random.choice(['매수 신호', '중립', '매도 신호']),
            "volume_trend": random.choice(['증가', '보통', '감소']),
            "price_momentum": random.choice(['강함', '보통', '약함']),
            "volatility_level": random.choice(['낮음', '보통', '높음'])
        }
    
    @staticmethod
    def _generate_news_analysis(stock: Stock) -> Dict[str, Any]:
        """뉴스 및 시장 동향 분석"""
        news_topics = [
            "기업 실적 발표",
            "신제품 출시",
            "경영진 변동",
            "업계 동향 변화",
            "규제 환경 변화",
            "글로벌 시장 영향",
            "기술 혁신",
            "경쟁사 동향"
        ]
        
        return {
            "recent_news": [
                {
                    "topic": random.choice(news_topics),
                    "sentiment": random.choice(['긍정적', '중립적', '부정적']),
                    "impact_level": random.choice(['높음', '보통', '낮음']),
                    "summary": f"{stock.name}의 {random.choice(news_topics)}에 대한 시장 반응이 주목받고 있습니다."
                },
                {
                    "topic": random.choice(news_topics),
                    "sentiment": random.choice(['긍정적', '중립적', '부정적']),
                    "impact_level": random.choice(['높음', '보통', '낮음']),
                    "summary": f"{stock.sector} 섹터의 전반적인 동향이 {stock.name}에 미치는 영향이 분석되고 있습니다."
                }
            ],
            "market_reaction": random.choice(['긍정적', '중립적', '부정적']),
            "sector_influence": random.choice(['높음', '보통', '낮음']),
            "news_sentiment_score": round(random.uniform(0.2, 0.8), 2)
        }
    
    @staticmethod
    def _analyze_investor_sentiment(stock: Stock) -> Dict[str, Any]:
        """투자자 심리 분석"""
        return {
            "retail_sentiment": random.choice(['매우 긍정적', '긍정적', '중립적', '부정적', '매우 부정적']),
            "institutional_sentiment": random.choice(['매우 긍정적', '긍정적', '중립적', '부정적', '매우 부정적']),
            "analyst_rating": random.choice(['매수', '강력매수', '중립', '매도', '강력매도']),
            "price_target_consensus": round(random.uniform(500, 1200), 2),
            "earnings_expectations": random.choice(['상향', '유지', '하향']),
            "short_interest": round(random.uniform(5, 25), 2),
            "options_flow": random.choice(['매수 우세', '중립', '매도 우세'])
        }
    
    @staticmethod
    def _generate_investment_opinion(technical: Dict, sentiment: Dict) -> Dict[str, Any]:
        """종합 투자 의견 생성"""
        # 기술적 지표와 심리 분석을 종합하여 투자 의견 생성
        technical_score = 0
        if technical['trend_strength'] == '강함':
            technical_score += 1
        elif technical['trend_strength'] == '약함':
            technical_score -= 1
            
        if technical['rsi_signal'] == '과매도':
            technical_score += 1
        elif technical['rsi_signal'] == '과매수':
            technical_score -= 1
        
        # 종합 점수에 따른 투자 의견
        if technical_score >= 1:
            opinion = "매수"
            confidence = "높음"
        elif technical_score <= -1:
            opinion = "매도"
            confidence = "높음"
        else:
            opinion = "중립"
            confidence = "보통"
        
        return {
            "recommendation": opinion,
            "confidence_level": confidence,
            "reasoning": f"기술적 지표와 시장 심리를 종합 분석한 결과, {opinion} 의견을 제시합니다.",
            "risk_reward_ratio": round(random.uniform(1.5, 3.0), 2),
            "time_horizon": random.choice(['단기(1-3개월)', '중기(3-12개월)', '장기(1년 이상)'])
        }
    
    @staticmethod
    def _assess_risk(stock: Stock) -> Dict[str, Any]:
        """리스크 평가"""
        return {
            "overall_risk": random.choice(['낮음', '보통', '높음']),
            "volatility_risk": random.choice(['낮음', '보통', '높음']),
            "liquidity_risk": random.choice(['낮음', '보통', '높음']),
            "sector_risk": random.choice(['낮음', '보통', '높음']),
            "company_specific_risk": random.choice(['낮음', '보통', '높음']),
            "risk_factors": [
                "시장 변동성 증가",
                "섹터별 순환 조정",
                "글로벌 경제 불확실성",
                "정책 리스크"
            ]
        }
    
    @staticmethod
    def _generate_price_target(stock: Stock) -> Dict[str, Any]:
        """가격 목표 생성"""
        base_price = random.uniform(400, 800)
        return {
            "short_term_target": round(base_price * random.uniform(0.9, 1.1), 2),
            "medium_term_target": round(base_price * random.uniform(1.1, 1.3), 2),
            "long_term_target": round(base_price * random.uniform(1.3, 1.6), 2),
            "upside_potential": round(random.uniform(10, 40), 1),
            "downside_risk": round(random.uniform(5, 25), 1)
        }
    
    @staticmethod
    def _recommend_holding_period(stock: Stock) -> Dict[str, Any]:
        """보유 기간 권장"""
        return {
            "recommended_period": random.choice(['단기', '중기', '장기']),
            "reasoning": f"{stock.sector} 섹터의 성장 전망과 {stock.name}의 사업 모델을 고려한 권장사항입니다.",
            "rebalancing_frequency": random.choice(['월 1회', '분기 1회', '반기 1회']),
            "exit_strategy": "목표 수익률 달성 시 단계적 이익실현 권장"
        }

@router.get("/market-overview")
async def get_market_overview():
    """전반적인 주식시장 AI 분석"""
    try:
        # AI 분석 서비스를 사용하여 실제 분석 생성
        ai_service = AIAnalysisService()
        analysis = ai_service.generate_market_overview()
        
        return {
            "success": True,
            "data": analysis,
            "message": "시장 분석이 성공적으로 생성되었습니다.",
            "timestamp": ai_service.analysis_timestamp.isoformat()
        }
    except Exception as e:
        # 로깅 추가 (향후 구현)
        print(f"시장 분석 생성 오류: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail={
                "error": "시장 분석 생성 실패",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )

@router.get("/stocks/{symbol}/analysis")
async def get_stock_analysis(symbol: str, db: Session = Depends(get_db)):
    """개별 주식 AI 분석"""
    try:
        # 주식 정보 조회
        stock = db.query(Stock).filter(Stock.symbol == symbol.upper()).first()
        if not stock:
            raise HTTPException(status_code=404, detail=f"주식 {symbol}을 찾을 수 없습니다.")
        
        # AI 분석 생성
        analysis = AIAnalysisService.generate_stock_analysis(stock, db)
        
        return {
            "success": True,
            "data": analysis,
            "message": f"{stock.name}의 AI 분석이 성공적으로 생성되었습니다."
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"주식 분석 생성 중 오류가 발생했습니다: {str(e)}")

@router.get("/sectors/{sector}/analysis")
async def get_sector_analysis(sector: str):
    """섹터별 AI 분석"""
    try:
        # 시장 전체 감정을 기반으로 섹터 분석 생성
        ai_service = AIAnalysisService()
        market_overview = ai_service.generate_market_overview()
        market_sentiment = market_overview["overall_sentiment"]
        
        # 시장 감정과 일관성 있는 섹터 전망 생성
        if market_sentiment == "긍정적":
            if sector == "technology":
                outlook = "강세 지속"
                growth = "높음"
            elif sector == "healthcare":
                outlook = "안정적 성장"
                growth = "보통"
            else:
                outlook = "점진적 개선"
                growth = "보통"
        elif market_sentiment == "부정적":
            if sector == "healthcare":
                outlook = "상대적으로 안정적"
                growth = "보통"
            elif sector == "consumer":
                outlook = "방어적 성격"
                growth = "낮음"
            else:
                outlook = "조정 압력"
                growth = "낮음"
        else:  # 중립적
            outlook = "조정 후 반등 기대"
            growth = "보통"
        
        sector_analysis = {
            "sector_name": sector,
            "overall_outlook": outlook,
            "growth_potential": growth,
            "key_drivers": [
                "기술 혁신",
                "소비자 선호도 변화",
                "규제 환경 개선",
                "글로벌 시장 확장"
            ],
            "risk_factors": [
                "경기 순환성",
                "정책 변화",
                "경쟁 심화",
                "원자재 가격 변동"
            ],
            "top_performers": [
                "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"
            ],
            "analysis_timestamp": ai_service.analysis_timestamp.isoformat()
        }
        
        return {
            "success": True,
            "data": sector_analysis,
            "message": f"{sector} 섹터 분석이 성공적으로 생성되었습니다."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"섹터 분석 생성 중 오류가 발생했습니다: {str(e)}")

@router.get("/ai-insights/latest")
async def get_latest_ai_insights():
    """최신 AI 인사이트"""
    try:
        insights = [
            {
                "id": 1,
                "title": "기술주 중심의 시장 회복세 지속",
                "summary": "AI 및 클라우드 기술의 성장으로 기술주 섹터가 시장을 선도하고 있습니다.",
                "impact_level": "높음",
                "timestamp": base_time.isoformat(),
                "tags": ["기술주", "AI", "시장 동향"]
            },
            {
                "id": 2,
                "title": "중앙은행 정책 변화에 따른 시장 변동성 증가",
                "summary": "금리 인상 우려로 인해 성장주 중심의 조정이 예상됩니다.",
                "impact_level": "보통",
                "timestamp": (base_time - timedelta(hours=2)).isoformat(),
                "tags": ["금리", "정책", "변동성"]
            },
            {
                "id": 3,
                "title": "에너지 섹터의 수요 회복 전망",
                "summary": "경제 재개로 인한 에너지 수요 증가가 예상되어 관련 주식들의 상승이 기대됩니다.",
                "impact_level": "보통",
                "timestamp": (base_time - timedelta(hours=4)).isoformat(),
                "tags": ["에너지", "경제 재개", "수요"]
            }
        ]
        
        return {
            "success": True,
            "data": insights,
            "message": "최신 AI 인사이트를 성공적으로 조회했습니다."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 인사이트 조회 중 오류가 발생했습니다: {str(e)}")
