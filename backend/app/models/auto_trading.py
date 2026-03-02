from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, JSON
from datetime import datetime
from app.core.database import Base

class AutoTradingRule(Base):
    __tablename__ = "auto_trading_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    strategy_type = Column(String(50), nullable=False)  # RSI, MACD, etc.
    parameters = Column(JSON)  # Strategy parameters
    is_active = Column(Boolean, default=True)
    account_id = Column(Integer)                        # 연결 계좌
    buy_score_threshold = Column(Float, default=70.0)   # 매수 스코어 기준
    max_position_count = Column(Integer, default=5)     # 최대 보유 종목 수
    budget_ratio = Column(Float, default=0.7)           # 예산 사용 비율
    schedule_buy = Column(String(20))                   # 매수 스케줄 (cron 표현)
    schedule_sell = Column(String(20))                  # 매도 스케줄
    last_executed_at = Column(DateTime)                 # 마지막 실행 시간
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class BacktestResult(Base):
    __tablename__ = "backtest_results"

    id = Column(Integer, primary_key=True, index=True)
    strategy_name = Column(String(100), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    initial_balance = Column(Float, nullable=False)
    final_balance = Column(Float, nullable=False)
    total_return = Column(Float, nullable=False)
    sharpe_ratio = Column(Float)
    max_drawdown = Column(Float)
    win_rate = Column(Float)
    total_trades = Column(Integer)                      # 총 거래 횟수
    win_trades = Column(Integer)                        # 수익 거래 횟수
    strategy_type = Column(String(50))                  # 전략 유형
    trade_details = Column(JSON)                        # 개별 거래 상세 기록
    parameters = Column(JSON)  # Strategy parameters used
    created_at = Column(DateTime, default=datetime.utcnow)
