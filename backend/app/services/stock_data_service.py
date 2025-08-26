import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from app.core.database import get_db_session
from app.core.lru_cache import LRUCache
from app.models.stock import Stock, StockPrice
import logging

logger = logging.getLogger(__name__)

class StockDataService:
    def __init__(self):
        self.db = get_db_session()
        
        # 환경별 설정
        self.environment = os.getenv("ENVIRONMENT", "development")
        if self.environment == "production":
            self.price_cache_ttl = 2 * 60 * 60  # 운영: 2시간
            self.max_cache_size = 500  # 운영: 최대 500개
        else:
            self.price_cache_ttl = 30 * 60  # 개발: 30분
            self.max_cache_size = 200  # 개발: 최대 200개
        
        # LRU 캐시 사용
        self.price_cache = LRUCache(
            max_size=self.max_cache_size,
            default_ttl=self.price_cache_ttl
        )
        
        logger.info(f"StockDataService 초기화 완료 - 환경: {self.environment}, TTL: {self.price_cache_ttl//60}분, 최대 캐시: {self.max_cache_size}개")
    
    def get_stock_data(self, symbol: str, days: int = 365) -> Dict[str, Any]:
        """주식 데이터 조회 (LRU 캐싱 + DB 캐싱)"""
        cache_key = f"{symbol}_{days}"
        
        # LRU 캐시 확인
        cached_data = self.price_cache.get(cache_key)
        if cached_data:
            logger.debug(f"가격 데이터 캐시 히트: {symbol} ({days}일)")
            return cached_data
        
        # 캐시 미스: DB에서 조회 (DB 캐싱 활용)
        logger.info(f"가격 데이터 캐시 미스 - DB에서 조회: {symbol} ({days}일)")
        stored_data = self._get_stored_stock_data(symbol, days)
        
        # DB에 데이터가 없거나 오래된 경우 yfinance API 호출
        if not stored_data:
            logger.info(f"DB에 데이터 없음 - yfinance API 호출: {symbol}")
            try:
                from app.services.data_collector import DataCollector
                collector = DataCollector()
                prices_df = collector.collect_stock_prices(symbol, days)
                if not prices_df.empty:
                    # DataFrame을 딕셔너리 리스트로 변환
                    stored_data = []
                    for _, row in prices_df.iterrows():
                        stored_data.append({
                            'date': row['date'].isoformat() if hasattr(row['date'], 'isoformat') else str(row['date']),
                            'open': row['open'],
                            'high': row['high'],
                            'low': row['low'],
                            'close': row['close'],
                            'volume': row['volume']
                        })
                    logger.info(f"yfinance API에서 {len(stored_data)}개 데이터 수집 완료: {symbol}")
                else:
                    logger.warning(f"yfinance API에서 데이터 수집 실패: {symbol}")
            except Exception as e:
                logger.error(f"yfinance API 호출 실패 {symbol}: {e}")
        
        # 결과를 LRU 캐시에 저장
        result = {
            'symbol': symbol,
            'prices': stored_data,
            'last_updated': datetime.utcnow().isoformat(),
            'cache_source': 'yfinance_api' if not stored_data else 'database'
        }
        
        self.price_cache.put(cache_key, result, self.price_cache_ttl)
        
        logger.info(f"가격 데이터 캐시 저장 완료: {symbol} ({len(stored_data)}개)")
        return stored_data  # prices 리스트만 반환
    
    def _get_stored_stock_data(self, symbol: str, days: int) -> List[Dict]:
        """DB에서 저장된 주식 데이터 조회"""
        try:
            stock = self.db.query(Stock).filter(Stock.symbol == symbol).first()
            if not stock:
                logger.warning(f"주식 정보 없음: {symbol}")
                return []
            
            # 최근 N일 데이터 조회 (날짜만 비교)
            cutoff_date = datetime.utcnow().date() - timedelta(days=days)
            prices = self.db.query(StockPrice).filter(
                StockPrice.stock_id == stock.id,
                StockPrice.date >= cutoff_date
            ).order_by(StockPrice.date.desc()).all()
            
            return [
                {
                    'date': price.date.isoformat() if price.date else None,
                    'open': price.open,
                            'high': price.high,
        'low': price.low,
                    'close': price.close,
                    'volume': price.volume,
                    'adjusted_close': price.adjusted_close if hasattr(price, 'adjusted_close') else None
                }
                for price in prices
            ]
            
        except Exception as e:
            logger.error(f"DB에서 주식 데이터 조회 실패 {symbol}: {e}")
            return []
    
    def get_stock_summary(self, symbol: str) -> Dict[str, Any]:
        """주식 요약 정보 조회 (메모리 캐싱)"""
        cache_key = f"{symbol}_summary"
        
        # LRU 캐시 확인
        cached_data = self.price_cache.get(cache_key)
        if cached_data:
            return cached_data
        
        # DB에서 요약 정보 조회
        try:
            stock = self.db.query(Stock).filter(Stock.symbol == symbol).first()
            if not stock:
                return {}
            
            # 최신 가격 데이터 조회
            latest_price = self.db.query(StockPrice).filter(
                StockPrice.stock_id == stock.id
            ).order_by(StockPrice.date.desc()).first()
            
            if not latest_price:
                return {}
            
            # 이전 가격 데이터 조회 (변화율 계산용)
            prev_price = self.db.query(StockPrice).filter(
                StockPrice.stock_id == stock.id,
                StockPrice.date < latest_price.date
            ).order_by(StockPrice.date.desc()).first()
            
            # 변화율 계산
            price_change = 0
            price_change_percent = 0
            if prev_price:
                price_change = latest_price.close - prev_price.close
                price_change_percent = (price_change / prev_price.close) * 100
            
            summary = {
                'symbol': stock.symbol,
                'name': stock.name,
                'sector': stock.sector,
                'industry': stock.industry,
                'market_cap': stock.market_cap,
                'current_price': latest_price.close,
                'price_change': price_change,
                'price_change_percent': price_change_percent,
                'volume': latest_price.volume,
                'last_updated': latest_price.date.isoformat() if latest_price.date else None
            }
            
            # LRU 캐시에 저장
            self.price_cache.put(cache_key, summary, self.price_cache_ttl)
            
            return summary
            
        except Exception as e:
            logger.error(f"주식 요약 정보 조회 실패 {symbol}: {e}")
            return {}
    
    def clear_cache(self, symbol: str = None):
        """캐시 정리"""
        if symbol:
            # 특정 주식의 캐시만 정리
            keys_to_remove = [k for k in self.price_cache.keys() if k.startswith(symbol)]
            for key in keys_to_remove:
                self.price_cache.delete(key)
            logger.info(f"주식 캐시 정리 완료: {symbol} ({len(keys_to_remove)}개)")
        else:
            # 전체 캐시 정리
            cleared_count = self.price_cache.clear()
            logger.info(f"전체 가격 데이터 캐시 정리 완료: {cleared_count}개")
    
    def cleanup_cache(self) -> int:
        """만료된 캐시 정리"""
        try:
            expired_count = self.price_cache.cleanup_expired()
            logger.info(f"가격 데이터 캐시 정리 완료: {expired_count}개 만료 항목")
            return expired_count
        except Exception as e:
            logger.error(f"가격 데이터 캐시 정리 실패: {e}")
            return 0
    
    def get_cache_info(self) -> Dict:
        """캐시 상태 정보 반환"""
        cache_stats = self.price_cache.get_stats()
        return {
            'environment': self.environment,
            'ttl_minutes': self.price_cache_ttl // 60,
            'max_cache_size': self.max_cache_size,
            'cache_stats': cache_stats
        }
    
    def __del__(self):
        """소멸자: DB 세션 정리"""
        if hasattr(self, 'db'):
            self.db.close()
