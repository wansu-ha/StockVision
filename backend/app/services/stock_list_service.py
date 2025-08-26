import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from app.core.database import get_db_session
from app.core.lru_cache import LRUCache
from app.models.stock import Stock
import logging

logger = logging.getLogger(__name__)

class StockListService:
    def __init__(self):
        self.db = get_db_session()
        
        # 환경별 설정
        self.environment = os.getenv("ENVIRONMENT", "development")
        if self.environment == "production":
            self.update_interval = 6 * 60 * 60  # 운영: 6시간
            self.max_cache_size = 200  # 운영: 최대 200개
        else:
            self.update_interval = 2 * 60 * 60  # 개발: 2시간
            self.max_cache_size = 100  # 개발: 최대 100개
        
        # LRU 캐시 사용
        self.stock_list_cache = LRUCache(
            max_size=self.max_cache_size,
            default_ttl=self.update_interval
        )
        
        logger.info(f"StockListService 초기화 완료 - 환경: {self.environment}, TTL: {self.update_interval//3600}시간, 최대 캐시: {self.max_cache_size}개")
    
    def get_stock_list(self) -> List[Dict]:
        """주식 목록 반환 (LRU 캐싱 적용)"""
        cache_key = "stock_list"
        
        # LRU 캐시 확인
        cached_data = self.stock_list_cache.get(cache_key)
        if cached_data:
            logger.debug(f"주식 목록 캐시 히트: {len(cached_data)}개")
            return cached_data
        
        # 캐시 미스: DB에서 조회
        logger.info("주식 목록 캐시 미스 - DB에서 조회")
        stocks = self.db.query(Stock).all()
        stock_list = [self._format_stock(stock) for stock in stocks]
        
        # LRU 캐시에 저장
        self.stock_list_cache.put(cache_key, stock_list, self.update_interval)
        
        logger.info(f"주식 목록 캐시 갱신 완료: {len(stock_list)}개")
        return stock_list
    
    def _format_stock(self, stock: Stock) -> Dict:
        """주식 데이터 포맷팅"""
        return {
            'id': stock.id,
            'symbol': stock.symbol,
            'name': stock.name,
            'sector': stock.sector,
            'industry': stock.industry,
            'market_cap': stock.market_cap,
            'created_at': stock.created_at.isoformat() if stock.created_at else None,
            'updated_at': stock.updated_at.isoformat() if stock.updated_at else None
        }
    
    def refresh_cache(self) -> bool:
        """캐시 강제 갱신"""
        try:
            self.stock_list_cache.clear()
            logger.info("주식 목록 캐시 강제 갱신 완료")
            return True
        except Exception as e:
            logger.error(f"캐시 갱신 실패: {e}")
            return False
    
    def get_cache_info(self) -> Dict:
        """캐시 상태 정보 반환"""
        cache_stats = self.stock_list_cache.get_stats()
        return {
            'environment': self.environment,
            'ttl_hours': self.update_interval // 3600,
            'max_cache_size': self.max_cache_size,
            'cache_stats': cache_stats
        }
    
    def cleanup_cache(self) -> int:
        """만료된 캐시 정리"""
        try:
            expired_count = self.stock_list_cache.cleanup_expired()
            logger.info(f"주식 목록 캐시 정리 완료: {expired_count}개 만료 항목")
            return expired_count
        except Exception as e:
            logger.error(f"주식 목록 캐시 정리 실패: {e}")
            return 0
    
    def __del__(self):
        """소멸자: DB 세션 정리"""
        if hasattr(self, 'db'):
            self.db.close()
