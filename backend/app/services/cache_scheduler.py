import os
import logging
import time
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# APScheduler 의존성 체크 및 fallback 구현
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    APSCHEDULER_AVAILABLE = True
    logger.info("APScheduler 라이브러리 사용 가능")
except ImportError:
    APSCHEDULER_AVAILABLE = False
    logger.warning("APScheduler 라이브러리가 설치되지 않음 - 기본 스케줄링 사용")

from app.core.memory_monitor import MemoryMonitor
from app.services.stock_list_service import StockListService
from app.services.stock_data_service import StockDataService

class CacheScheduler:
    """
    캐시 자동 정리 및 메모리 모니터링 스케줄러
    정기적으로 캐시를 정리하고 메모리 사용량을 체크
    APScheduler가 없을 때는 기본 스케줄링 사용
    """
    
    def __init__(self):
        self.memory_monitor = MemoryMonitor()
        
        # 환경별 설정
        self.environment = os.getenv("ENVIRONMENT", "development")
        if self.environment == "production":
            # 운영 환경: 더 보수적인 설정
            self.cache_cleanup_interval = 30  # 30분마다
            self.memory_check_interval = 15   # 15분마다
            self.force_cleanup_threshold = 450  # 450MB에서 강제 정리
        else:
            # 개발 환경: 더 적극적인 설정
            self.cache_cleanup_interval = 15  # 15분마다
            self.memory_check_interval = 5    # 5분마다
            self.force_cleanup_threshold = 300  # 300MB에서 강제 정리
        
        # 서비스 인스턴스 (나중에 주입)
        self.stock_list_service = None
        self.stock_data_service = None
        
        # 스케줄러 초기화
        if APSCHEDULER_AVAILABLE:
            self.scheduler = BackgroundScheduler()
            logger.info(f"CacheScheduler 초기화 완료 - 환경: {self.environment} (APScheduler 사용)")
        else:
            self.scheduler = None
            self.last_cleanup_time = time.time()
            self.last_memory_check_time = time.time()
            logger.info(f"CacheScheduler 초기화 완료 - 환경: {self.environment} (기본 스케줄링 사용)")
    
    def set_services(self, stock_list_service: StockListService, stock_data_service: StockDataService):
        """서비스 인스턴스 설정"""
        self.stock_list_service = stock_list_service
        self.stock_data_service = stock_data_service
        logger.info("캐시 서비스 인스턴스 설정 완료")
    
    def setup_jobs(self):
        """스케줄 작업 설정"""
        if not APSCHEDULER_AVAILABLE:
            logger.info("APScheduler 없음 - 기본 스케줄링 모드로 동작")
            return
        
        try:
            # 1. 정기적인 캐시 정리 (매시간)
            self.scheduler.add_job(
                self.regular_cache_cleanup,
                CronTrigger(minute=0),  # 매시 정각
                id='hourly_cache_cleanup',
                name='정기 캐시 정리 (매시간)'
            )
            
            # 2. 주기적인 캐시 정리 (설정된 간격)
            self.scheduler.add_job(
                self.periodic_cache_cleanup,
                IntervalTrigger(minutes=self.cache_cleanup_interval),
                id='periodic_cache_cleanup',
                name=f'주기적 캐시 정리 ({self.cache_cleanup_interval}분마다)'
            )
            
            # 3. 메모리 사용량 체크 (설정된 간격)
            self.scheduler.add_job(
                self.check_memory_usage,
                IntervalTrigger(minutes=self.memory_check_interval),
                id='memory_usage_check',
                name=f'메모리 사용량 체크 ({self.memory_check_interval}분마다)'
            )
            
            # 4. 일일 캐시 통계 (매일 새벽 2시)
            self.scheduler.add_job(
                self.daily_cache_stats,
                CronTrigger(hour=2, minute=0),
                id='daily_cache_stats',
                name='일일 캐시 통계 (매일 새벽 2시)'
            )
            
            # 5. 주간 캐시 최적화 (매주 일요일 새벽 3시)
            self.scheduler.add_job(
                self.weekly_cache_optimization,
                CronTrigger(day_of_week='sun', hour=3, minute=0),
                id='weekly_cache_optimization',
                name='주간 캐시 최적화 (매주 일요일 새벽 3시)'
            )
            
            logger.info(f"스케줄 작업 설정 완료: {len(self.scheduler.get_jobs())}개 작업")
            
        except Exception as e:
            logger.error(f"스케줄 작업 설정 실패: {e}")
    
    def check_and_run_tasks(self):
        """기본 스케줄링 모드에서 작업 체크 및 실행"""
        if APSCHEDULER_AVAILABLE:
            return  # APScheduler가 있으면 이 메서드 사용 안함
        
        current_time = time.time()
        
        # 주기적 캐시 정리 체크
        if current_time - self.last_cleanup_time >= self.cache_cleanup_interval * 60:
            self.periodic_cache_cleanup()
            self.last_cleanup_time = current_time
        
        # 메모리 사용량 체크
        if current_time - self.last_memory_check_time >= self.memory_check_interval * 60:
            self.check_memory_usage()
            self.last_memory_check_time = current_time
    
    def regular_cache_cleanup(self):
        """정기적인 캐시 정리 (매시간)"""
        try:
            logger.info("=== 정기 캐시 정리 시작 ===")
            
            # 1. 만료된 캐시 항목 정리
            if self.stock_data_service:
                expired_count = self.stock_data_service.cleanup_cache()
                logger.info(f"만료된 가격 데이터 캐시 정리: {expired_count}개")
            
            # 2. 메모리 상태 체크
            memory_status = self.memory_monitor.check_memory_status()
            logger.info(f"메모리 상태: {memory_status['status']} - {memory_status['message']}")
            
            # 3. 메모리가 경고 수준이면 강제 정리
            if memory_status['level'] in ['warning', 'critical']:
                logger.warning(f"메모리 경고 수준 - 강제 정리 실행: {memory_status['message']}")
                self.force_cleanup()
            
            logger.info("=== 정기 캐시 정리 완료 ===")
            
        except Exception as e:
            logger.error(f"정기 캐시 정리 실패: {e}")
    
    def periodic_cache_cleanup(self):
        """주기적인 캐시 정리 (설정된 간격)"""
        try:
            logger.debug("=== 주기적 캐시 정리 시작 ===")
            
            # 1. 만료된 캐시 정리
            if self.stock_data_service:
                expired_count = self.stock_data_service.cleanup_cache()
                if expired_count > 0:
                    logger.info(f"주기적 캐시 정리: {expired_count}개 만료 항목 제거")
            
            # 2. 메모리 사용량 체크
            memory_usage = self.memory_monitor.get_memory_usage()
            if 'error' not in memory_usage:
                process_rss = memory_usage['process']['rss_mb']
                logger.debug(f"현재 메모리 사용량: {process_rss:.1f}MB")
                
                # 임계값 초과 시 강제 정리
                if process_rss > self.force_cleanup_threshold:
                    logger.warning(f"메모리 임계값 초과 ({process_rss:.1f}MB > {self.force_cleanup_threshold}MB) - 강제 정리 실행")
                    self.force_cleanup()
            
            logger.debug("=== 주기적 캐시 정리 완료 ===")
            
        except Exception as e:
            logger.error(f"주기적 캐시 정리 실패: {e}")
    
    def check_memory_usage(self):
        """메모리 사용량 체크"""
        try:
            memory_status = self.memory_monitor.check_memory_status()
            
            if memory_status['level'] == 'critical':
                logger.critical(f"메모리 위험 수준: {memory_status['message']}")
                # 즉시 강제 정리 실행
                self.force_cleanup()
            elif memory_status['level'] == 'warning':
                logger.warning(f"메모리 경고 수준: {memory_status['message']}")
                # 경고 수준에서는 주기적 정리만 실행
                if self.stock_data_service:
                    self.stock_data_service.cleanup_cache()
            else:
                logger.debug(f"메모리 정상: {memory_status['message']}")
                
        except Exception as e:
            logger.error(f"메모리 사용량 체크 실패: {e}")
    
    def force_cleanup(self):
        """강제 메모리 정리"""
        try:
            logger.warning("=== 강제 메모리 정리 시작 ===")
            
            # 1. 모든 캐시 정리
            if self.stock_data_service:
                cleared_count = self.stock_data_service.clear_cache()
                logger.info(f"가격 데이터 캐시 전체 정리: {cleared_count}개")
            
            if self.stock_list_service:
                self.stock_list_service.refresh_cache()
                logger.info("주식 목록 캐시 강제 갱신")
            
            # 2. 시스템 메모리 정리
            cleanup_result = self.memory_monitor.force_cleanup()
            if 'error' not in cleanup_result:
                logger.info(f"시스템 메모리 정리: {cleanup_result['memory_reduction_mb']:.1f}MB 감소")
            
            # 3. 정리 후 상태 확인
            time.sleep(1)  # 정리 완료 대기
            memory_status = self.memory_monitor.check_memory_status()
            logger.info(f"정리 후 메모리 상태: {memory_status['status']}")
            
            logger.warning("=== 강제 메모리 정리 완료 ===")
            
        except Exception as e:
            logger.error(f"강제 메모리 정리 실패: {e}")
    
    def daily_cache_stats(self):
        """일일 캐시 통계 생성"""
        try:
            logger.info("=== 일일 캐시 통계 생성 시작 ===")
            
            # 1. 캐시 통계 수집
            stats = {
                'date': datetime.now().isoformat(),
                'environment': self.environment,
                'memory': self.memory_monitor.get_detailed_stats(),
                'cache': {}
            }
            
            # 2. 주식 목록 캐시 통계
            if self.stock_list_service:
                stock_list_stats = self.stock_list_service.get_cache_info()
                stats['cache']['stock_list'] = stock_list_stats
            
            # 3. 가격 데이터 캐시 통계
            if self.stock_data_service:
                price_cache_stats = self.stock_data_service.get_cache_info()
                stats['cache']['price_data'] = price_cache_stats
            
            # 4. 통계 로깅
            logger.info(f"일일 캐시 통계: {stats}")
            
            # 5. 메모리 히스토리 정리 (오래된 데이터 제거)
            self.memory_monitor.reset_history()
            
            logger.info("=== 일일 캐시 통계 생성 완료 ===")
            
        except Exception as e:
            logger.error(f"일일 캐시 통계 생성 실패: {e}")
    
    def weekly_cache_optimization(self):
        """주간 캐시 최적화"""
        try:
            logger.info("=== 주간 캐시 최적화 시작 ===")
            
            # 1. 전체 캐시 정리
            if self.stock_data_service:
                cleared_count = self.stock_data_service.clear_cache()
                logger.info(f"주간 캐시 정리: {cleared_count}개 항목 제거")
            
            # 2. 주식 목록 캐시 갱신
            if self.stock_list_service:
                self.stock_list_service.refresh_cache()
                logger.info("주식 목록 캐시 주간 갱신")
            
            # 3. 메모리 최적화
            cleanup_result = self.memory_monitor.force_cleanup()
            if 'error' not in cleanup_result:
                logger.info(f"주간 메모리 최적화: {cleanup_result['memory_reduction_mb']:.1f}MB 감소")
            
            # 4. 최적화 후 상태 확인
            memory_status = self.memory_monitor.check_memory_status()
            logger.info(f"주간 최적화 후 메모리 상태: {memory_status['status']}")
            
            logger.info("=== 주간 캐시 최적화 완료 ===")
            
        except Exception as e:
            logger.error(f"주간 캐시 최적화 실패: {e}")
    
    def get_scheduler_status(self) -> dict:
        """스케줄러 상태 정보 반환"""
        try:
            if not APSCHEDULER_AVAILABLE:
                return {
                    'scheduler_running': False,
                    'total_jobs': 0,
                    'jobs': [],
                    'environment': self.environment,
                    'mode': 'basic_scheduling',
                    'config': {
                        'cache_cleanup_interval_minutes': self.cache_cleanup_interval,
                        'memory_check_interval_minutes': self.memory_check_interval,
                        'force_cleanup_threshold_mb': self.force_cleanup_threshold
                    }
                }
            
            jobs = self.scheduler.get_jobs()
            job_info = []
            
            for job in jobs:
                job_info.append({
                    'id': job.id,
                    'name': job.name,
                    'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                    'trigger': str(job.trigger)
                })
            
            return {
                'scheduler_running': self.scheduler.running,
                'total_jobs': len(jobs),
                'jobs': job_info,
                'environment': self.environment,
                'mode': 'apscheduler',
                'config': {
                    'cache_cleanup_interval_minutes': self.cache_cleanup_interval,
                    'memory_check_interval_minutes': self.memory_check_interval,
                    'force_cleanup_threshold_mb': self.force_cleanup_threshold
                }
            }
            
        except Exception as e:
            logger.error(f"스케줄러 상태 조회 실패: {e}")
            return {'error': str(e)}
    
    def start(self):
        """스케줄러 시작"""
        try:
            if APSCHEDULER_AVAILABLE and self.scheduler:
                if not self.scheduler.running:
                    self.scheduler.start()
                    logger.info("캐시 스케줄러 시작됨 (APScheduler)")
                else:
                    logger.info("캐시 스케줄러가 이미 실행 중입니다")
            else:
                logger.info("기본 스케줄링 모드로 시작됨")
        except Exception as e:
            logger.error(f"캐시 스케줄러 시작 실패: {e}")
    
    def stop(self):
        """스케줄러 중지"""
        try:
            if APSCHEDULER_AVAILABLE and self.scheduler and self.scheduler.running:
                self.scheduler.shutdown()
                logger.info("캐시 스케줄러 중지됨")
            else:
                logger.info("캐시 스케줄러가 실행 중이 아닙니다")
        except Exception as e:
            logger.error(f"캐시 스케줄러 중지 실패: {e}")
    
    def __del__(self):
        """소멸자: 스케줄러 정리"""
        try:
            if hasattr(self, 'scheduler') and self.scheduler and self.scheduler.running:
                self.scheduler.shutdown()
        except:
            pass
