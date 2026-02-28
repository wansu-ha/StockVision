from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from datetime import datetime
from app.core.database import Base

class VirtualAccount(Base):
    __tablename__ = "virtual_accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    initial_balance = Column(Float, nullable=False, default=10000000.0)  # 기본 1천만원
    current_balance = Column(Float, nullable=False, default=10000000.0)
    total_profit_loss = Column(Float, default=0.0)     # 총 실현 손익
    total_trades = Column(Integer, default=0)           # 총 거래 횟수
    win_trades = Column(Integer, default=0)             # 수익 거래 횟수
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class VirtualPosition(Base):
    __tablename__ = "virtual_positions"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, nullable=False)
    stock_id = Column(Integer, nullable=False)
    symbol = Column(String(10))                         # 종목 심볼
    quantity = Column(Integer, nullable=False)
    avg_price = Column(Float, nullable=False)
    current_price = Column(Float)                       # 현재가
    unrealized_pnl = Column(Float, default=0.0)         # 미실현 손익
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class VirtualTrade(Base):
    __tablename__ = "virtual_trades"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, nullable=False)
    stock_id = Column(Integer, nullable=False)
    symbol = Column(String(10))                         # 종목 심볼
    trade_type = Column(String(10), nullable=False)     # BUY, SELL
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    total_amount = Column(Float)                        # 총 거래 금액
    commission = Column(Float, default=0.0)             # 수수료
    tax = Column(Float, default=0.0)                    # 세금
    realized_pnl = Column(Float)                        # 실현 손익 (매도 시)
    timestamp = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
