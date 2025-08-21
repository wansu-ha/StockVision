#!/usr/bin/env python3
"""
데이터 수집 및 기술적 지표 계산 테스트 스크립트
"""

from app.services.data_collector import DataCollector
from app.services.technical_indicators import TechnicalIndicatorCalculator
from app.core.database import SessionLocal
from app.models.stock import Stock
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_data_collection():
    """데이터 수집 테스트"""
    logger.info("=== 데이터 수집 테스트 시작 ===")
    
    # 테스트할 주식 심볼들 (미국 주요 주식)
    test_symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']
    
    try:
        # 데이터 수집기 생성
        collector = DataCollector()
        
        # 데이터 수집 및 저장
        collector.collect_and_save(test_symbols, days=365)
        
        logger.info("데이터 수집 테스트 완료")
        return True
        
    except Exception as e:
        logger.error(f"데이터 수집 테스트 실패: {str(e)}")
        return False

def test_technical_indicators():
    """기술적 지표 계산 테스트"""
    logger.info("=== 기술적 지표 계산 테스트 시작 ===")
    
    try:
        # 데이터베이스 세션 생성
        session = SessionLocal()
        
        # 저장된 주식들 조회
        stocks = session.query(Stock).all()
        
        if not stocks:
            logger.warning("저장된 주식이 없습니다. 데이터 수집을 먼저 실행하세요.")
            return False
        
        # 기술적 지표 계산기 생성
        calculator = TechnicalIndicatorCalculator()
        
        success_count = 0
        for stock in stocks:
            logger.info(f"주식 지표 계산 중: {stock.symbol}")
            if calculator.process_stock_indicators(stock.id):
                success_count += 1
        
        logger.info(f"기술적 지표 계산 완료: {success_count}/{len(stocks)}개 주식")
        return success_count > 0
        
    except Exception as e:
        logger.error(f"기술적 지표 계산 테스트 실패: {str(e)}")
        return False
    finally:
        session.close()

def main():
    """메인 실행 함수"""
    logger.info("StockVision 데이터 수집 및 지표 계산 테스트 시작")
    
    # 1단계: 데이터 수집
    if test_data_collection():
        logger.info("✅ 데이터 수집 성공")
        
        # 2단계: 기술적 지표 계산
        if test_technical_indicators():
            logger.info("✅ 기술적 지표 계산 성공")
            logger.info("🎉 모든 테스트가 성공적으로 완료되었습니다!")
        else:
            logger.error("❌ 기술적 지표 계산 실패")
    else:
        logger.error("❌ 데이터 수집 실패")
    
    logger.info("테스트 완료")

if __name__ == "__main__":
    main()
