import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from app.models.stock import Stock, StockPrice
from app.core.database import SessionLocal
from app.core.rate_limit_monitor import rate_limit_monitor
from app.core.api_logging import api_logger_instance
import logging
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataCollector:
    def __init__(self):
        self.session = SessionLocal()
        
    async def collect_stock_info(self, symbols: List[str]) -> List[Dict]:
        """주식 기본 정보 수집 (Semaphore로 동시 호출 제한)"""
        stocks_data = []
        
        for symbol in symbols:
            try:
                # Semaphore로 동시 호출 제한
                async with rate_limit_monitor.request_semaphore:
                    # API 제한 확인
                    can_request, status = rate_limit_monitor.can_make_request()
                    if not can_request:
                        logger.warning(f"야후 파이낸스 API 제한 초과: {status['status']}")
                        continue
                    
                    ticker = yf.Ticker(symbol)
                    info = ticker.info
                    
                    stock_data = {
                        'symbol': symbol,
                        'name': info.get('longName', symbol),
                        'sector': info.get('sector', 'Unknown'),
                        'industry': info.get('industry', 'Unknown'),
                        'market_cap': info.get('marketCap')
                    }
                    stocks_data.append(stock_data)
                    
                    # API 호출 기록
                    rate_limit_monitor.record_request(symbol, "stock_info")
                    api_logger_instance.increment_yahoo_calls(symbol, "stock_info")
                    logger.info(f"주식 정보 수집 완료: {symbol}")
                
            except Exception as e:
                logger.error(f"주식 정보 수집 실패 {symbol}: {str(e)}")
                
        return stocks_data
    
    async def collect_stock_prices(self, symbol: str, days: int = 365) -> pd.DataFrame:
        """주식 가격 데이터 수집 (Semaphore로 동시 호출 제한)"""
        try:
            # Semaphore로 동시 호출 제한
            async with rate_limit_monitor.request_semaphore:
                # API 제한 확인
                can_request, status = rate_limit_monitor.can_make_request()
                if not can_request:
                    logger.warning(f"야후 파이낸스 API 제한 초과: {status['status']}")
                    return pd.DataFrame()
                
                ticker = yf.Ticker(symbol)
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                
                df = ticker.history(start=start_date, end=end_date)
                
                if df.empty:
                    logger.warning(f"가격 데이터 없음: {symbol}")
                    return pd.DataFrame()
                    
                # 컬럼명 정규화
                df.columns = [col.lower() for col in df.columns]
                df.reset_index(inplace=True)
                
                # Date 컬럼이 있는지 확인하고 처리
                if 'date' in df.columns:
                    df.rename(columns={'date': 'date'}, inplace=True)
                elif 'Date' in df.columns:
                    df.rename(columns={'Date': 'date'}, inplace=True)
                
                # API 호출 기록
                rate_limit_monitor.record_request(symbol, "price_data")
                api_logger_instance.increment_yahoo_calls(symbol, "price_data")
                logger.info(f"가격 데이터 수집 완료: {symbol} ({len(df)}개)")
                return df
                
        except Exception as e:
            logger.error(f"가격 데이터 수집 실패 {symbol}: {str(e)}")
            return pd.DataFrame()
    
    def save_stock_to_db(self, stock_data: Dict) -> Optional[Stock]:
        """주식 정보를 데이터베이스에 저장"""
        try:
            # 기존 주식 확인
            existing_stock = self.session.query(Stock).filter(
                Stock.symbol == stock_data['symbol']
            ).first()
            
            if existing_stock:
                # 업데이트
                for key, value in stock_data.items():
                    if hasattr(existing_stock, key):
                        setattr(existing_stock, key, value)
                existing_stock.updated_at = datetime.utcnow()
                stock = existing_stock
            else:
                # 새로 생성
                stock = Stock(**stock_data)
                self.session.add(stock)
            
            self.session.commit()
            logger.info(f"주식 저장 완료: {stock_data['symbol']}")
            return stock
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"주식 저장 실패 {stock_data['symbol']}: {str(e)}")
            return None
    
    def save_prices_to_db(self, stock_id: int, prices_df: pd.DataFrame) -> int:
        """가격 데이터를 데이터베이스에 저장"""
        if prices_df.empty:
            return 0
            
        try:
            saved_count = 0
            
            # 컬럼 확인
            required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
            missing_columns = [col for col in required_columns if col not in prices_df.columns]
            
            if missing_columns:
                logger.error(f"필수 컬럼 누락: {missing_columns}")
                logger.info(f"사용 가능한 컬럼: {list(prices_df.columns)}")
                return 0
            
            for _, row in prices_df.iterrows():
                try:
                    # 기존 가격 데이터 확인
                    existing_price = self.session.query(StockPrice).filter(
                        StockPrice.stock_id == stock_id,
                        StockPrice.date == row['date']
                    ).first()
                    
                    if not existing_price:
                        price_data = {
                            'stock_id': stock_id,
                            'date': row['date'],
                            'open': float(row['open']),
                            'high': float(row['high']),
                            'low': float(row['low']),
                            'close': float(row['close']),
                            'volume': int(row['volume'])
                        }
                        
                        price = StockPrice(**price_data)
                        self.session.add(price)
                        saved_count += 1
                        
                except Exception as e:
                    logger.error(f"개별 가격 데이터 저장 실패: {str(e)}")
                    continue
            
            self.session.commit()
            logger.info(f"가격 데이터 저장 완료: {stock_id} ({saved_count}개)")
            return saved_count
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"가격 데이터 저장 실패 {stock_id}: {str(e)}")
            return 0
    
    def collect_and_save(self, symbols: List[str], days: int = 365):
        """주식 정보와 가격 데이터를 수집하고 저장"""
        logger.info(f"데이터 수집 시작: {len(symbols)}개 주식")
        
        for symbol in symbols:
            try:
                # 주식 정보 수집 및 저장
                stock_info = self.collect_stock_info([symbol])
                if stock_info:
                    stock = self.save_stock_to_db(stock_info[0])
                    if stock:
                        # 가격 데이터 수집 및 저장
                        prices_df = self.collect_stock_prices(symbol, days)
                        if not prices_df.empty:
                            self.save_prices_to_db(stock.id, prices_df)
                            
            except Exception as e:
                logger.error(f"전체 프로세스 실패 {symbol}: {str(e)}")
                continue
        
        logger.info("데이터 수집 완료")
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()
