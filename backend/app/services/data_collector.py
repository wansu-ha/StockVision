import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from app.models.stock import Stock, StockPrice
from app.core.database import SessionLocal
from app.core.rate_limit_monitor import rate_limit_monitor
from app.core.api_logging import api_logger_instance
import logging
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def to_yfinance_symbol(symbol: str) -> str:
    """DB 심볼을 yfinance 심볼로 변환 (한국 주식: .KS 접미사)"""
    # 이미 .KS/.KQ 붙어있으면 그대로
    if symbol.endswith(('.KS', '.KQ')):
        return symbol
    # 숫자 6자리 = 한국 주식
    if re.match(r'^\d{6}$', symbol):
        return f"{symbol}.KS"
    return symbol


def to_db_symbol(symbol: str) -> str:
    """yfinance 심볼에서 DB용 심볼 추출 (.KS/.KQ 제거)"""
    for suffix in ('.KS', '.KQ'):
        if symbol.endswith(suffix):
            return symbol[:-len(suffix)]
    return symbol


class DataCollector:
    def __init__(self):
        self.session = SessionLocal()
        
    async def collect_stock_info(self, symbols: List[str]) -> List[Dict]:
        """주식 기본 정보 수집 (Semaphore로 동시 호출 제한)"""
        stocks_data = []

        for symbol in symbols:
            try:
                yf_symbol = to_yfinance_symbol(symbol)
                db_symbol = to_db_symbol(symbol)

                # API 제한 확인
                can_request, status = rate_limit_monitor.can_make_request()
                if not can_request:
                    logger.warning(f"야후 파이낸스 API 제한 초과: {status['status']}")
                    continue

                ticker = yf.Ticker(yf_symbol)
                info = ticker.info

                stock_data = {
                    'symbol': db_symbol,
                    'name': info.get('longName', db_symbol),
                    'sector': info.get('sector', 'Unknown'),
                    'industry': info.get('industry', 'Unknown'),
                    'market_cap': info.get('marketCap')
                }
                stocks_data.append(stock_data)

                # API 호출 기록
                rate_limit_monitor.record_request(db_symbol, "stock_info")
                api_logger_instance.increment_yahoo_calls(db_symbol, "stock_info")
                logger.info(f"주식 정보 수집 완료: {db_symbol} (yfinance: {yf_symbol})")

            except Exception as e:
                logger.error(f"주식 정보 수집 실패 {symbol}: {str(e)}")

        return stocks_data
    
    async def collect_stock_prices(self, symbol: str, days: int = 365) -> pd.DataFrame:
        """주식 가격 데이터 수집 (Semaphore로 동시 호출 제한)"""
        try:
            yf_symbol = to_yfinance_symbol(symbol)
            db_symbol = to_db_symbol(symbol)

            # API 제한 확인
            can_request, status = rate_limit_monitor.can_make_request()
            if not can_request:
                logger.warning(f"야후 파이낸스 API 제한 초과: {status['status']}")
                return pd.DataFrame()

            ticker = yf.Ticker(yf_symbol)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            df = ticker.history(start=start_date, end=end_date)

            if df.empty:
                logger.warning(f"가격 데이터 없음: {yf_symbol}")
                return pd.DataFrame()

            # 컬럼명 정규화
            df.columns = [col.lower() for col in df.columns]
            df.reset_index(inplace=True)

            # Date 컬럼 정규화 (대소문자 + 타임존 제거)
            if 'Date' in df.columns:
                df.rename(columns={'Date': 'date'}, inplace=True)
            if 'date' in df.columns and hasattr(df['date'].dt, 'tz') and df['date'].dt.tz is not None:
                df['date'] = df['date'].dt.tz_localize(None)

            # API 호출 기록
            rate_limit_monitor.record_request(db_symbol, "price_data")
            api_logger_instance.increment_yahoo_calls(db_symbol, "price_data")
            logger.info(f"가격 데이터 수집 완료: {db_symbol} ({len(df)}개)")
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
    
    async def register_stocks(self, symbols: List[str], days: int = 730) -> Dict:
        """종목 등록: 주식 정보 + 가격 데이터 + 기술적 지표 일괄 수집"""
        from app.services.technical_indicators import TechnicalIndicatorCalculator

        results = {
            'registered': [],
            'failed': [],
            'total_prices': 0,
            'total_indicators': 0
        }

        indicator_calc = TechnicalIndicatorCalculator()

        for symbol in symbols:
            db_symbol = to_db_symbol(symbol)
            try:
                # 1. 주식 정보 수집 + DB 저장
                stock_infos = await self.collect_stock_info([symbol])
                if not stock_infos:
                    results['failed'].append({'symbol': db_symbol, 'reason': '정보 수집 실패'})
                    continue

                stock = self.save_stock_to_db(stock_infos[0])
                if not stock:
                    results['failed'].append({'symbol': db_symbol, 'reason': 'DB 저장 실패'})
                    continue

                # 2. 가격 데이터 수집 + DB 저장
                prices_df = await self.collect_stock_prices(symbol, days)
                price_count = 0
                if not prices_df.empty:
                    price_count = self.save_prices_to_db(stock.id, prices_df)

                # 3. 기술적 지표 계산 + DB 저장
                indicator_count = 0
                if price_count > 0:
                    indicators = indicator_calc.calculate_all_indicators(stock.id)
                    if indicators:
                        indicator_count = indicator_calc.save_indicators_to_db(stock.id, indicators)

                results['registered'].append({
                    'symbol': db_symbol,
                    'name': stock.name,
                    'stock_id': stock.id,
                    'prices': price_count,
                    'indicators': indicator_count
                })
                results['total_prices'] += price_count
                results['total_indicators'] += indicator_count

                logger.info(f"종목 등록 완료: {db_symbol} (가격: {price_count}개, 지표: {indicator_count}개)")

            except Exception as e:
                logger.error(f"종목 등록 실패 {db_symbol}: {str(e)}")
                results['failed'].append({'symbol': db_symbol, 'reason': str(e)})
                continue

        logger.info(f"종목 등록 완료: {len(results['registered'])}개 성공, {len(results['failed'])}개 실패")
        return results
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()
