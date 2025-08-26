import logging
import logging.handlers
import os
from datetime import datetime
from pathlib import Path

# 로그 디렉토리 생성
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# 하위 디렉토리 생성
(LOG_DIR / "api").mkdir(exist_ok=True)
(LOG_DIR / "yahoo_finance").mkdir(exist_ok=True)
(LOG_DIR / "combined").mkdir(exist_ok=True)

def setup_logger(name: str, log_file: str, level=logging.INFO):
    """로거 설정 및 반환"""
    
    # 로거 생성
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 이미 핸들러가 설정되어 있으면 추가하지 않음
    if logger.handlers:
        return logger
    
    # 파일 핸들러 (일별 로테이션)
    file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=LOG_DIR / log_file,
        when='midnight',
        interval=1,
        backupCount=30,
        encoding='utf-8'
    )
    
    # 포맷터 설정
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    
    # 콘솔 핸들러 (개발 환경용)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # 핸들러 추가
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# 주요 로거들
api_logger = setup_logger('api', 'api/api.log')
yahoo_logger = setup_logger('yahoo_finance', 'yahoo_finance/yahoo.log')
combined_logger = setup_logger('combined', 'combined/combined.log')

def get_current_log_files():
    """현재 로그 파일 목록 반환"""
    today = datetime.now().strftime('%Y-%m-%d')
    return {
        'api': f'logs/api/api.log',
        'yahoo_finance': f'logs/yahoo_finance/yahoo.log',
        'combined': f'logs/combined/combined.log'
    }
