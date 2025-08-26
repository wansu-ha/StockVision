from collections import OrderedDict
import time
import logging
import threading
from typing import Any, Optional, Dict

logger = logging.getLogger(__name__)

class LRUCache:
    """
    LRU (Least Recently Used) 캐시 구현
    용량 제한과 TTL 기반 자동 정리 기능 포함
    스레드 안전성 보장
    """
    
    def __init__(self, max_size: int = 100, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache = OrderedDict()
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'expired_cleanups': 0
        }
        self._lock = threading.RLock()  # 재진입 가능한 락
        
        logger.info(f"LRU 캐시 초기화 완료: 최대 {max_size}개, 기본 TTL {default_ttl}초")
    
    def get(self, key: str) -> Optional[Any]:
        """캐시에서 데이터 조회"""
        with self._lock:
            if key in self.cache:
                cache_entry = self.cache[key]
                current_time = time.time()
                
                # TTL 확인
                if current_time - cache_entry['timestamp'] > cache_entry['ttl']:
                    # 만료된 항목 제거
                    del self.cache[key]
                    self.stats['expired_cleanups'] += 1
                    logger.debug(f"만료된 캐시 항목 제거: {key}")
                    return None
                
                # 사용된 항목을 맨 뒤로 이동 (LRU)
                self.cache.move_to_end(key)
                self.stats['hits'] += 1
                logger.debug(f"캐시 히트: {key}")
                return cache_entry['data']
            
            self.stats['misses'] += 1
            logger.debug(f"캐시 미스: {key}")
            return None
    
    def put(self, key: str, value: Any, ttl: int = None) -> bool:
        """캐시에 데이터 저장"""
        with self._lock:
            try:
                ttl = ttl or self.default_ttl
                current_time = time.time()
                
                if key in self.cache:
                    # 기존 항목 제거
                    del self.cache[key]
                    logger.debug(f"기존 캐시 항목 업데이트: {key}")
                elif len(self.cache) >= self.max_size:
                    # 용량 한계 도달 시 가장 오래된 항목 제거 (LRU)
                    oldest_key = next(iter(self.cache))
                    del self.cache[oldest_key]
                    self.stats['evictions'] += 1
                    logger.info(f"LRU 캐시 항목 제거: {oldest_key} (용량 한계)")
                
                # 새 항목 추가
                self.cache[key] = {
                    'data': value,
                    'timestamp': current_time,
                    'ttl': ttl
                }
                
                logger.debug(f"캐시 항목 저장: {key} (TTL: {ttl}초)")
                return True
                
            except Exception as e:
                logger.error(f"캐시 저장 실패 {key}: {e}")
                return False
    
    def delete(self, key: str) -> bool:
        """특정 키의 캐시 항목 삭제"""
        with self._lock:
            try:
                if key in self.cache:
                    del self.cache[key]
                    logger.debug(f"캐시 항목 삭제: {key}")
                    return True
                return False
            except Exception as e:
                logger.error(f"캐시 삭제 실패 {key}: {e}")
                return False
    
    def clear(self) -> int:
        """전체 캐시 정리"""
        with self._lock:
            try:
                cleared_count = len(self.cache)
                self.cache.clear()
                logger.info(f"전체 캐시 정리 완료: {cleared_count}개 항목")
                return cleared_count
            except Exception as e:
                logger.error(f"전체 캐시 정리 실패: {e}")
                return 0
    
    def cleanup_expired(self) -> int:
        """만료된 항목 정리"""
        with self._lock:
            try:
                current_time = time.time()
                expired_keys = [
                    key for key, item in self.cache.items()
                    if current_time - item['timestamp'] > item['ttl']
                ]
                
                for key in expired_keys:
                    del self.cache[key]
                
                expired_count = len(expired_keys)
                if expired_count > 0:
                    self.stats['expired_cleanups'] += expired_count
                    logger.info(f"만료된 캐시 항목 정리: {expired_count}개")
                
                return expired_count
                
            except Exception as e:
                logger.error(f"만료된 캐시 정리 실패: {e}")
                return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """캐시 통계 정보 반환"""
        with self._lock:
            current_time = time.time()
            
            # 현재 캐시 상태 분석
            active_entries = 0
            expired_entries = 0
            total_memory_estimate = 0
            
            for key, item in self.cache.items():
                if current_time - item['timestamp'] <= item['ttl']:
                    active_entries += 1
                    # 간단한 메모리 사용량 추정 (키 + 데이터 크기)
                    total_memory_estimate += len(str(key)) + len(str(item['data']))
                else:
                    expired_entries += 1
            
            return {
                'max_size': self.max_size,
                'current_size': len(self.cache),
                'active_entries': active_entries,
                'expired_entries': expired_entries,
                'memory_estimate_bytes': total_memory_estimate,
                'hit_rate': self.stats['hits'] / (self.stats['hits'] + self.stats['misses']) if (self.stats['hits'] + self.stats['misses']) > 0 else 0,
                'stats': self.stats.copy()
            }
    
    def exists(self, key: str) -> bool:
        """키 존재 여부 확인 (TTL 무시)"""
        with self._lock:
            return key in self.cache
    
    def get_size(self) -> int:
        """현재 캐시 크기 반환"""
        with self._lock:
            return len(self.cache)
    
    def is_full(self) -> bool:
        """캐시가 가득 찼는지 확인"""
        with self._lock:
            return len(self.cache) >= self.max_size
    
    def __len__(self) -> int:
        """캐시 크기 반환"""
        with self._lock:
            return len(self.cache)
    
    def __contains__(self, key: str) -> bool:
        """키 존재 여부 확인"""
        with self._lock:
            return key in self.cache
