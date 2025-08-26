import time
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, Tuple
import logging

class YahooFinanceRateLimitMonitor:
    """야후 파이낸스 API 호출 제한 모니터링"""
    
    def __init__(self):
        # 시간당 제한 (1000회)
        self.hourly_limit = 1000
        # 분당 제한 (분당 1000/60 = 약 17회)
        self.minute_limit = int(self.hourly_limit / 60)
        
        # 호출 기록 (시간별, 분별)
        self.hourly_calls = defaultdict(int)
        self.minute_calls = defaultdict(int)
        
        # 현재 시간대 키
        self.current_hour_key = self._get_hour_key()
        self.current_minute_key = self._get_minute_key()
        
        # 로거 설정
        self.logger = logging.getLogger(__name__)
        
        # 제한 경고 임계값 (80%)
        self.warning_threshold = 0.8
        
    def _get_hour_key(self) -> str:
        """현재 시간대 키 반환 (YYYY-MM-DD-HH)"""
        return datetime.now().strftime('%Y-%m-%d-%H')
    
    def _get_minute_key(self) -> str:
        """현재 분대 키 반환 (YYYY-MM-DD-HH-MM)"""
        return datetime.now().strftime('%Y-%m-%d-%H-%M')
    
    def _cleanup_old_records(self):
        """오래된 기록 정리"""
        current_time = datetime.now()
        
        # 1시간 이상 오래된 시간별 기록 정리
        for hour_key in list(self.hourly_calls.keys()):
            try:
                hour_time = datetime.strptime(hour_key, '%Y-%m-%d-%H')
                if current_time - hour_time > timedelta(hours=1):
                    del self.hourly_calls[hour_key]
            except:
                del self.hourly_calls[hour_key]
        
        # 1분 이상 오래된 분별 기록 정리
        for minute_key in list(self.minute_calls.keys()):
            try:
                minute_time = datetime.strptime(minute_key, '%Y-%m-%d-%H-%M')
                if current_time - minute_time > timedelta(minutes=1):
                    del self.minute_calls[minute_key]
            except:
                del self.minute_calls[minute_key]
    
    def can_make_request(self) -> Tuple[bool, Dict]:
        """API 요청 가능 여부 확인"""
        self._cleanup_old_records()
        
        # 현재 시간대 키 업데이트
        current_hour = self._get_hour_key()
        current_minute = self._get_minute_key()
        
        # 시간별, 분별 호출 횟수 확인
        hourly_count = self.hourly_calls[current_hour]
        minute_count = self.minute_calls[current_minute]
        
        # 제한 확인
        hourly_available = hourly_count < self.hourly_limit
        minute_available = minute_count < self.minute_limit
        
        # 사용률 계산
        hourly_usage = hourly_count / self.hourly_limit
        minute_usage = minute_count / self.minute_limit
        
        # 경고 상태 확인
        hourly_warning = hourly_usage >= self.warning_threshold
        minute_warning = minute_usage >= self.warning_threshold
        
        # 상태 정보
        status = {
            "can_request": hourly_available and minute_available,
            "hourly": {
                "current": hourly_count,
                "limit": self.hourly_limit,
                "usage": hourly_usage,
                "warning": hourly_warning
            },
            "minute": {
                "current": minute_count,
                "limit": self.minute_limit,
                "usage": minute_usage,
                "warning": minute_warning
            },
            "status": "normal"
        }
        
        # 상태 메시지 설정
        if not hourly_available:
            status["status"] = "hourly_limit_exceeded"
        elif not minute_available:
            status["status"] = "minute_limit_exceeded"
        elif hourly_warning or minute_warning:
            status["status"] = "warning"
        
        return hourly_available and minute_available, status
    
    def record_request(self, symbol: str, data_type: str) -> Dict:
        """API 요청 기록"""
        self._cleanup_old_records()
        
        # 현재 시간대 키 업데이트
        current_hour = self._get_hour_key()
        current_minute = self._get_minute_key()
        
        # 호출 횟수 증가
        self.hourly_calls[current_hour] += 1
        self.minute_calls[current_minute] += 1
        
        # 현재 상태 확인
        can_request, status = self.can_make_request()
        
        # 로그 기록
        if status["status"] == "warning":
            self.logger.warning(f"야후 파이낸스 API 제한 경고: 시간당 {status['hourly']['current']}/{status['hourly']['limit']} ({status['hourly']['usage']:.1%})")
        elif status["status"] in ["hourly_limit_exceeded", "minute_limit_exceeded"]:
            self.logger.error(f"야후 파이낸스 API 제한 초과: {status['status']}")
        
        return status
    
    def get_current_status(self) -> Dict:
        """현재 제한 상태 반환"""
        _, status = self.can_make_request()
        return status
    
    def get_usage_summary(self) -> Dict:
        """사용률 요약 반환"""
        status = self.get_current_status()
        
        return {
            "hourly_usage": status["hourly"]["usage"],
            "minute_usage": status["minute"]["usage"],
            "hourly_warning": status["hourly"]["warning"],
            "minute_warning": status["minute"]["warning"],
            "status": status["status"],
            "can_request": status["can_request"]
        }

# 전역 인스턴스
rate_limit_monitor = YahooFinanceRateLimitMonitor()
