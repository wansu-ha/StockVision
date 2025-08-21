from app.core.database import engine, Base
from app.models import Stock, StockPrice, TechnicalIndicator, VirtualAccount, VirtualTrade, VirtualPosition, AutoTradingRule, BacktestResult

def init_db():
    """데이터베이스 테이블 생성"""
    Base.metadata.create_all(bind=engine)
    print("데이터베이스 테이블이 생성되었습니다.")

if __name__ == "__main__":
    init_db()
