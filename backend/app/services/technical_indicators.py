import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from app.models.stock import StockPrice, TechnicalIndicator
from app.core.database import SessionLocal
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TechnicalIndicatorCalculator:
    def __init__(self):
        self.session = SessionLocal()
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """RSI(Relative Strength Index) 계산"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def calculate_ema(self, prices: pd.Series, period: int = 20) -> pd.Series:
        """EMA(Exponential Moving Average) 계산"""
        return prices.ewm(span=period).mean()
    
    def calculate_macd(self, prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
        """MACD(Moving Average Convergence Divergence) 계산"""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal).mean()
        histogram = macd_line - signal_line
        
        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }
    
    def calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: int = 2) -> Dict[str, pd.Series]:
        """볼린저 밴드 계산"""
        sma = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        
        return {
            'upper': upper_band,
            'middle': sma,
            'lower': lower_band
        }
    
    def get_stock_prices(self, stock_id: int, days: int = 365) -> pd.DataFrame:
        """데이터베이스에서 주식 가격 데이터 조회"""
        try:
            end_date = datetime.now()
            start_date = end_date.replace(year=end_date.year - 1)
            
            prices = self.session.query(StockPrice).filter(
                StockPrice.stock_id == stock_id,
                StockPrice.date >= start_date
            ).order_by(StockPrice.date).all()
            
            if not prices:
                return pd.DataFrame()
            
            data = []
            for price in prices:
                data.append({
                    'date': price.date,
                    'close': price.close,
                    'volume': price.volume
                })
            
            df = pd.DataFrame(data)
            df.set_index('date', inplace=True)
            df.sort_index(inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"가격 데이터 조회 실패 {stock_id}: {str(e)}")
            return pd.DataFrame()
    
    def calculate_all_indicators(self, stock_id: int) -> Dict[str, pd.DataFrame]:
        """모든 기술적 지표 계산"""
        prices_df = self.get_stock_prices(stock_id)
        if prices_df.empty:
            return {}
        
        close_prices = prices_df['close']
        
        indicators = {}
        
        # RSI 계산
        indicators['rsi'] = self.calculate_rsi(close_prices)
        
        # EMA 계산 (20일, 50일)
        indicators['ema_20'] = self.calculate_ema(close_prices, 20)
        indicators['ema_50'] = self.calculate_ema(close_prices, 50)
        
        # MACD 계산
        macd_data = self.calculate_macd(close_prices)
        indicators.update(macd_data)
        
        # 볼린저 밴드 계산
        bb_data = self.calculate_bollinger_bands(close_prices)
        indicators.update(bb_data)
        
        return indicators
    
    def save_indicators_to_db(self, stock_id: int, indicators: Dict[str, pd.DataFrame]) -> int:
        """계산된 지표를 데이터베이스에 저장"""
        if not indicators:
            return 0
        
        try:
            saved_count = 0
            
            for indicator_type, values in indicators.items():
                if values.empty:
                    continue
                
                # 기존 지표 데이터 확인 및 삭제
                self.session.query(TechnicalIndicator).filter(
                    TechnicalIndicator.stock_id == stock_id,
                    TechnicalIndicator.indicator_type == indicator_type
                ).delete()
                
                # 새 지표 데이터 저장
                for date, value in values.items():
                    if pd.notna(value):  # NaN 값 제외
                        indicator_data = {
                            'stock_id': stock_id,
                            'date': date,
                            'indicator_type': indicator_type,
                            'value': float(value),
                            'parameters': '{}'  # 기본 파라미터
                        }
                        
                        indicator = TechnicalIndicator(**indicator_data)
                        self.session.add(indicator)
                        saved_count += 1
            
            self.session.commit()
            logger.info(f"기술적 지표 저장 완료: {stock_id} ({saved_count}개)")
            return saved_count
            
        except Exception as e:
            self.session.rollback()
            logger.error(f"기술적 지표 저장 실패 {stock_id}: {str(e)}")
            return 0
    
    def process_stock_indicators(self, stock_id: int) -> bool:
        """주식의 모든 기술적 지표를 계산하고 저장"""
        try:
            logger.info(f"기술적 지표 계산 시작: {stock_id}")
            
            # 지표 계산
            indicators = self.calculate_all_indicators(stock_id)
            if not indicators:
                logger.warning(f"지표 계산 실패: {stock_id}")
                return False
            
            # 데이터베이스에 저장
            saved_count = self.save_indicators_to_db(stock_id, indicators)
            
            if saved_count > 0:
                logger.info(f"기술적 지표 처리 완료: {stock_id} ({saved_count}개)")
                return True
            else:
                logger.warning(f"지표 저장 실패: {stock_id}")
                return False
                
        except Exception as e:
            logger.error(f"기술적 지표 처리 실패 {stock_id}: {str(e)}")
            return False
    
    def __del__(self):
        if hasattr(self, 'session'):
            self.session.close()
