from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Index
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime
from app.core.database import Base

class Stock(Base):
    __tablename__ = "stocks"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    sector = Column(String(50))
    industry = Column(String(100))
    market_cap = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class StockPrice(Base):
    __tablename__ = "stock_prices"
    
    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, nullable=False)
    date = Column(DateTime, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_stock_date', 'stock_id', 'date'),
    )

class TechnicalIndicator(Base):
    __tablename__ = "technical_indicators"
    
    id = Column(Integer, primary_key=True, index=True)
    stock_id = Column(Integer, nullable=False)
    date = Column(DateTime, nullable=False)
    indicator_type = Column(String(20), nullable=False)  # RSI, EMA, MACD, etc.
    value = Column(Float, nullable=False)
    parameters = Column(Text)  # JSON string for indicator parameters
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_stock_indicator_date', 'stock_id', 'indicator_type', 'date'),
    )
