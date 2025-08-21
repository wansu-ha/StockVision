from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean
from datetime import datetime
from app.core.database import Base

class VirtualAccount(Base):
    __tablename__ = "virtual_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    initial_balance = Column(Float, nullable=False, default=100000.0)
    current_balance = Column(Float, nullable=False, default=100000.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class VirtualPosition(Base):
    __tablename__ = "virtual_positions"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, nullable=False)
    stock_id = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False)
    avg_price = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class VirtualTrade(Base):
    __tablename__ = "virtual_trades"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, nullable=False)
    stock_id = Column(Integer, nullable=False)
    trade_type = Column(String(10), nullable=False)  # BUY, SELL
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
