import logging
import time
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# psutil 의존성 체크 및 fallback 구현
try:
    import psutil
    PSUTIL_AVAILABLE = True
    logger.info("psutil 라이브러리 사용 가능")
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil 라이브러리가 설치되지 않음 - 기본 메모리 모니터링 사용")

class MemoryMonitor:
    """
    메모리 사용량 모니터링 및 관리
    캐시 시스템의 메모리 사용량을 추적하고 한계를 체크
    psutil이 없을 때는 기본 모니터링 사용
    """
    
    def __init__(self, warning_threshold_mb: int = 400, critical_threshold_mb: int = 500):
        self.warning_threshold_mb = warning_threshold_mb
        self.critical_threshold_mb = critical_threshold_mb
        self.memory_history = []
        self.max_history_size = 100
        
        self.psutil_available = PSUTIL_AVAILABLE
        
        if self.psutil_available:
            try:
                self.process = psutil.Process()
                logger.info(f"메모리 모니터 초기화 완료 - 환경: {warning_threshold_mb}MB, 위험 임계값 {critical_threshold_mb}MB")
            except Exception as e:
                logger.error(f"psutil 프로세스 초기화 실패: {e}")
                self.psutil_available = False
        else:
            logger.info("기본 메모리 모니터링 모드로 초기화")
    
    def get_memory_usage(self) -> Dict[str, Any]:
        """현재 메모리 사용량 정보 반환"""
        if not self.psutil_available:
            return self._get_basic_memory_usage()
        
        try:
            memory_info = self.process.memory_info()
            memory_percent = self.process.memory_percent()
            
            # 시스템 전체 메모리 정보
            system_memory = psutil.virtual_memory()
            
            memory_data = {
                'process': {
                    'rss_mb': memory_info.rss / 1024 / 1024,  # Resident Set Size (실제 물리 메모리)
                    'vms_mb': memory_info.vms / 1024 / 1024,  # Virtual Memory Size (가상 메모리)
                    'percent': memory_percent,
                    'available_mb': memory_info.rss / 1024 / 1024
                },
                'system': {
                    'total_mb': system_memory.total / 1024 / 1024,
                    'available_mb': system_memory.available / 1024 / 1024,
                    'percent': system_memory.percent,
                    'free_mb': system_memory.free / 1024 / 1024
                },
                'timestamp': time.time()
            }
            
            # 메모리 사용량 히스토리에 추가
            self._add_to_history(memory_data)
            
            return memory_data
            
        except Exception as e:
            logger.error(f"메모리 사용량 조회 실패: {e}")
            return self._get_basic_memory_usage()
    
    def _get_basic_memory_usage(self) -> Dict[str, Any]:
        """기본 메모리 사용량 정보 (psutil 없을 때)"""
        try:
            # 간단한 메모리 추정 (Python 객체 수 기반)
            import gc
            gc.collect()  # 가비지 컬렉션 실행
            
            # 객체 수 기반 메모리 추정
            object_count = len(gc.get_objects())
            estimated_memory_mb = object_count * 0.001  # 매우 대략적인 추정
            
            memory_data = {
                'process': {
                    'rss_mb': estimated_memory_mb,
                    'vms_mb': estimated_memory_mb * 1.5,
                    'percent': 0.0,  # 알 수 없음
                    'available_mb': estimated_memory_mb
                },
                'system': {
                    'total_mb': 0.0,  # 알 수 없음
                    'available_mb': 0.0,
                    'percent': 0.0,
                    'free_mb': 0.0
                },
                'timestamp': time.time(),
                'note': '기본 모니터링 모드 (psutil 없음)'
            }
            
            self._add_to_history(memory_data)
            return memory_data
            
        except Exception as e:
            logger.error(f"기본 메모리 사용량 조회 실패: {e}")
            return {
                'error': str(e),
                'timestamp': time.time()
            }
    
    def _add_to_history(self, memory_data: Dict[str, Any]):
        """메모리 사용량 히스토리에 추가"""
        self.memory_history.append(memory_data)
        
        # 히스토리 크기 제한
        if len(self.memory_history) > self.max_history_size:
            self.memory_history.pop(0)
    
    def check_memory_status(self) -> Dict[str, Any]:
        """메모리 상태 체크 및 경고 레벨 반환"""
        memory_usage = self.get_memory_usage()
        
        if 'error' in memory_usage:
            return {
                'status': 'error',
                'message': f"메모리 상태 확인 실패: {memory_usage['error']}",
                'level': 'unknown'
            }
        
        process_rss = memory_usage['process']['rss_mb']
        
        if not self.psutil_available:
            # 기본 모니터링 모드에서는 항상 정상으로 처리
            return {
                'status': '정상 (기본 모드)',
                'level': 'normal',
                'message': f"기본 모니터링 모드: 추정 메모리 {process_rss:.1f}MB",
                'process_rss_mb': process_rss,
                'system_percent': 0.0,
                'thresholds': {
                    'warning_mb': self.warning_threshold_mb,
                    'critical_mb': self.critical_threshold_mb
                }
            }
        
        system_percent = memory_usage['system']['percent']
        
        # 경고 레벨 결정
        if process_rss >= self.critical_threshold_mb or system_percent >= 90:
            level = 'critical'
            status = '위험'
            message = f"메모리 사용량이 위험 수준입니다: 프로세스 {process_rss:.1f}MB, 시스템 {system_percent:.1f}%"
        elif process_rss >= self.warning_threshold_mb or system_percent >= 80:
            level = 'warning'
            status = '경고'
            message = f"메모리 사용량이 경고 수준입니다: 프로세스 {process_rss:.1f}MB, 시스템 {system_percent:.1f}%"
        else:
            level = 'normal'
            status = '정상'
            message = f"메모리 사용량이 정상 범위입니다: 프로세스 {process_rss:.1f}MB, 시스템 {system_percent:.1f}%"
        
        return {
            'status': status,
            'level': level,
            'message': message,
            'process_rss_mb': process_rss,
            'system_percent': system_percent,
            'thresholds': {
                'warning_mb': self.warning_threshold_mb,
                'critical_mb': self.critical_threshold_mb
            }
        }
    
    def is_memory_critical(self) -> bool:
        """메모리가 위험 수준인지 확인"""
        if not self.psutil_available:
            return False  # 기본 모드에서는 항상 False
        memory_status = self.check_memory_status()
        return memory_status['level'] == 'critical'
    
    def is_memory_warning(self) -> bool:
        """메모리가 경고 수준인지 확인"""
        if not self.psutil_available:
            return False  # 기본 모드에서는 항상 False
        memory_status = self.check_memory_status()
        return memory_status['level'] in ['warning', 'critical']
    
    def force_cleanup(self) -> Dict[str, Any]:
        """강제 메모리 정리"""
        try:
            # 가비지 컬렉션 실행
            import gc
            collected_objects = gc.collect()
            
            if not self.psutil_available:
                return {
                    'collected_objects': collected_objects,
                    'memory_reduction_mb': 0.0,
                    'before_memory_mb': 0.0,
                    'after_memory_mb': 0.0,
                    'timestamp': time.time(),
                    'note': '기본 모니터링 모드 - 정확한 메모리 측정 불가'
                }
            
            # 메모리 정리 전후 상태 비교
            before_memory = self.get_memory_usage()
            time.sleep(0.1)  # 잠시 대기
            after_memory = self.get_memory_usage()
            
            # 메모리 사용량 변화 계산
            memory_reduction = 0
            if 'error' not in before_memory and 'error' not in after_memory:
                memory_reduction = before_memory['process']['rss_mb'] - after_memory['process']['rss_mb']
            
            cleanup_result = {
                'collected_objects': collected_objects,
                'memory_reduction_mb': max(0, memory_reduction),
                'before_memory_mb': before_memory.get('process', {}).get('rss_mb', 0),
                'after_memory_mb': after_memory.get('process', {}).get('rss_mb', 0),
                'timestamp': time.time()
            }
            
            logger.info(f"강제 메모리 정리 완료: {collected_objects}개 객체, {memory_reduction:.1f}MB 감소")
            
            return cleanup_result
            
        except Exception as e:
            logger.error(f"강제 메모리 정리 실패: {e}")
            return {
                'error': str(e),
                'timestamp': time.time()
            }
    
    def get_memory_trend(self, hours: int = 1) -> Dict[str, Any]:
        """메모리 사용량 트렌드 분석"""
        try:
            current_time = time.time()
            cutoff_time = current_time - (hours * 3600)
            
            # 지정된 시간 범위의 데이터만 필터링
            recent_data = [
                data for data in self.memory_history
                if data.get('timestamp', 0) >= cutoff_time
            ]
            
            if not recent_data:
                return {
                    'message': f"최근 {hours}시간 동안의 메모리 데이터가 없습니다",
                    'data_points': 0
                }
            
            # 메모리 사용량 변화 분석
            rss_values = [data['process']['rss_mb'] for data in recent_data if 'process' in data]
            
            if not rss_values:
                return {
                    'message': "유효한 메모리 데이터가 없습니다",
                    'data_points': 0
                }
            
            trend_analysis = {
                'data_points': len(rss_values),
                'current_mb': rss_values[-1],
                'average_mb': sum(rss_values) / len(rss_values),
                'min_mb': min(rss_values),
                'max_mb': max(rss_values),
                'trend': 'stable',
                'change_mb': rss_values[-1] - rss_values[0] if len(rss_values) > 1 else 0,
                'hours_analyzed': hours
            }
            
            # 트렌드 방향 결정
            if len(rss_values) > 1:
                change = rss_values[-1] - rss_values[0]
                if change > 10:  # 10MB 이상 증가
                    trend_analysis['trend'] = 'increasing'
                elif change < -10:  # 10MB 이상 감소
                    trend_analysis['trend'] = 'decreasing'
            
            return trend_analysis
            
        except Exception as e:
            logger.error(f"메모리 트렌드 분석 실패: {e}")
            return {
                'error': str(e),
                'data_points': 0
            }
    
    def get_detailed_stats(self) -> Dict[str, Any]:
        """상세한 메모리 통계 정보"""
        try:
            memory_usage = self.get_memory_usage()
            memory_status = self.check_memory_status()
            memory_trend = self.get_memory_trend(1)  # 최근 1시간
            
            return {
                'current_usage': memory_usage,
                'status': memory_status,
                'trend': memory_trend,
                'history_size': len(self.memory_history),
                'psutil_available': self.psutil_available,
                'monitor_config': {
                    'warning_threshold_mb': self.warning_threshold_mb,
                    'critical_threshold_mb': self.critical_threshold_mb,
                    'max_history_size': self.max_history_size
                }
            }
            
        except Exception as e:
            logger.error(f"상세 메모리 통계 조회 실패: {e}")
            return {
                'error': str(e),
                'timestamp': time.time()
            }
    
    def reset_history(self):
        """메모리 히스토리 초기화"""
        self.memory_history.clear()
        logger.info("메모리 히스토리 초기화 완료")
    
    def __del__(self):
        """소멸자: 리소스 정리"""
        try:
            self.memory_history.clear()
        except:
            pass
