"""
전략 템플릿 초기 데이터 시딩

실행: cd backend && python -m scripts.seed_templates
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.database import SessionLocal, engine
from app.models.templates import StrategyTemplate
from app.core.database import Base

Base.metadata.create_all(bind=engine)

TEMPLATES = [
    {
        "name": "RSI 과매도 역추세",
        "description": "KOSPI RSI가 30 미만일 때 매수하는 단순 역추세 전략입니다. "
                       "시장이 과매도 구간에 진입했을 때 반등을 기대하고 매수합니다.",
        "category": "기술적 지표",
        "difficulty": "초급",
        "rule_json": {
            "side": "BUY",
            "conditions": [
                {"variable": "kospi_rsi_14", "operator": "<", "value": 30}
            ],
        },
        "backtest_summary": {"cagr": 12.3, "mdd": -18.5, "sharpe": 0.85},
        "tags": ["RSI", "역추세", "초급"],
    },
    {
        "name": "RSI 과매수 매도",
        "description": "KOSPI RSI가 70 초과일 때 매도하는 모멘텀 반전 전략입니다.",
        "category": "기술적 지표",
        "difficulty": "초급",
        "rule_json": {
            "side": "SELL",
            "conditions": [
                {"variable": "kospi_rsi_14", "operator": ">", "value": 70}
            ],
        },
        "backtest_summary": {"cagr": 8.7, "mdd": -12.1, "sharpe": 0.72},
        "tags": ["RSI", "모멘텀", "초급"],
    },
    {
        "name": "저변동성 매수",
        "description": "KOSPI 20일 변동성이 낮을 때 (0.01 미만) 매수합니다. "
                       "변동성이 낮은 안정적인 시장 국면에서 진입합니다.",
        "category": "변동성",
        "difficulty": "중급",
        "rule_json": {
            "side": "BUY",
            "conditions": [
                {"variable": "kospi_20d_volatility", "operator": "<", "value": 0.01}
            ],
        },
        "backtest_summary": {"cagr": 9.4, "mdd": -14.2, "sharpe": 0.91},
        "tags": ["변동성", "안정형", "중급"],
    },
    {
        "name": "이중 조건 역추세",
        "description": "KOSPI RSI < 35 이고 변동성 < 0.015 일 때 매수합니다. "
                       "두 조건을 동시에 만족할 때만 진입하여 필터링 효과를 높입니다.",
        "category": "복합전략",
        "difficulty": "중급",
        "rule_json": {
            "side": "BUY",
            "conditions": [
                {"variable": "kospi_rsi_14", "operator": "<", "value": 35},
                {"variable": "kospi_20d_volatility", "operator": "<", "value": 0.015},
            ],
        },
        "backtest_summary": {"cagr": 14.1, "mdd": -16.3, "sharpe": 1.02},
        "tags": ["RSI", "변동성", "복합", "중급"],
    },
]


def seed():
    db = SessionLocal()
    try:
        existing = db.query(StrategyTemplate).count()
        if existing > 0:
            print(f"[SKIP] 이미 {existing}개 템플릿 존재 — 시딩 생략")
            return
        for t in TEMPLATES:
            db.add(StrategyTemplate(**t))
        db.commit()
        print(f"[OK] {len(TEMPLATES)}개 템플릿 시딩 완료")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
