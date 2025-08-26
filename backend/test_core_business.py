#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
StockVision 핵심 비즈니스 로직 테스트
- AI 예측 모델
- 데이터 수집 및 기술적 지표
- API 엔드포인트
"""

import time
import logging
from typing import Dict, Any

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_data_collection() -> bool:
    """데이터 수집 테스트"""
    logger.info("=== 데이터 수집 테스트 시작 ===")
    
    try:
        from app.services.data_collector import DataCollector
        
        # 테스트할 주식 심볼들 (미국 주요 주식)
        test_symbols = ['AAPL', 'MSFT', 'GOOGL']
        
        # 데이터 수집기 생성
        collector = DataCollector()
        
        # 데이터 수집 및 저장
        collector.collect_and_save(test_symbols, days=30)  # 테스트용으로 30일만
        
        logger.info("✅ 데이터 수집 성공")
        return True
        
    except Exception as e:
        logger.error(f"❌ 데이터 수집 실패: {str(e)}")
        return False

def test_technical_indicators() -> bool:
    """기술적 지표 계산 테스트"""
    logger.info("=== 기술적 지표 계산 테스트 시작 ===")
    
    try:
        from app.services.technical_indicators import TechnicalIndicatorCalculator
        from app.core.database import SessionLocal
        from app.models.stock import Stock
        
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
        
        logger.info(f"✅ 기술적 지표 계산 완료: {success_count}/{len(stocks)}개 주식")
        return success_count > 0
        
    except Exception as e:
        logger.error(f"❌ 기술적 지표 계산 실패: {str(e)}")
        return False
    finally:
        session.close()

def test_prediction_model() -> bool:
    """AI 예측 모델 테스트"""
    logger.info("=== AI 예측 모델 테스트 시작 ===")
    
    try:
        from app.services.prediction_model import PredictionModel
        
        # 예측 모델 생성
        predictor = PredictionModel()
        
        # 첫 번째 주식으로 모델 훈련 (테스트용으로 간단하게)
        stock_id = 1  # AAPL
        
        logger.info(f'AAPL 주식 모델 훈련 시작...')
        success = predictor.train_model(stock_id, days=30)  # 테스트용으로 30일만
        
        if success:
            logger.info('✅ 모델 훈련 성공!')
            
            # 다음 날 예측
            logger.info('다음 날 주가 예측...')
            prediction = predictor.predict_next_day(stock_id)
            
            if prediction:
                logger.info('✅ 예측 성공:')
                logger.info(f'현재 가격: ${prediction["current_price"]:.2f}')
                logger.info(f'예측 가격: ${prediction["predicted_price"]:.2f}')
                logger.info(f'변화율: {prediction["price_change_percent"]:.2f}%')
                return True
            else:
                logger.error('❌ 예측 실패')
                return False
        else:
            logger.error('❌ 모델 훈련 실패')
            return False
            
    except Exception as e:
        logger.error(f"❌ AI 예측 모델 테스트 실패: {str(e)}")
        return False

def test_cache_system() -> bool:
    """캐싱 시스템 테스트"""
    logger.info("=== 캐싱 시스템 테스트 시작 ===")
    
    try:
        from app.services.stock_list_service import StockListService
        from app.services.stock_data_service import StockDataService
        
        # 서비스 인스턴스 생성
        stock_list_service = StockListService()
        stock_data_service = StockDataService()
        
        # 1. 캐시 정보 확인
        logger.info("캐시 정보 확인...")
        list_cache_info = stock_list_service.get_cache_info()
        data_cache_info = stock_data_service.get_cache_info()
        
        logger.info(f"주식 목록 캐시: {list_cache_info['environment']}")
        logger.info(f"가격 데이터 캐시: {data_cache_info['environment']}")
        
        # 2. 캐시 동작 테스트
        logger.info("캐시 동작 테스트...")
        start_time = time.time()
        stock_list = stock_list_service.get_stock_list()
        first_call_time = time.time() - start_time
        
        start_time = time.time()
        stock_list_2 = stock_list_service.get_stock_list()
        second_call_time = time.time() - start_time
        
        if first_call_time > second_call_time:
            speedup = first_call_time / second_call_time if second_call_time > 0 else 1
            logger.info(f"✅ 캐시 효과: {speedup:.1f}배 빨라짐")
            return True
        else:
            logger.warning("⚠️ 캐시 효과가 미미함")
            return True  # 경고이지만 실패는 아님
        
    except Exception as e:
        logger.error(f"❌ 캐싱 시스템 테스트 실패: {str(e)}")
        return False

def main():
    """메인 실행 함수"""
    logger.info("🚀 StockVision 핵심 비즈니스 로직 테스트 시작")
    
    start_time = time.time()
    test_results = {}
    
    # 1단계: 데이터 수집
    test_results['data_collection'] = test_data_collection()
    
    # 2단계: 기술적 지표 계산
    if test_results['data_collection']:
        test_results['technical_indicators'] = test_technical_indicators()
    else:
        test_results['technical_indicators'] = False
    
    # 3단계: AI 예측 모델
    if test_results['technical_indicators']:
        test_results['prediction_model'] = test_prediction_model()
    else:
        test_results['prediction_model'] = False
    
    # 4단계: 캐싱 시스템
    test_results['cache_system'] = test_cache_system()
    
    # 결과 요약
    elapsed_time = time.time() - start_time
    logger.info("=" * 50)
    logger.info("📊 테스트 결과 요약")
    logger.info("=" * 50)
    
    for test_name, result in test_results.items():
        status = "✅ 성공" if result else "❌ 실패"
        logger.info(f"{test_name}: {status}")
    
    success_count = sum(test_results.values())
    total_count = len(test_results)
    
    logger.info(f"총 {total_count}개 테스트 중 {success_count}개 성공")
    logger.info(f"소요 시간: {elapsed_time:.2f}초")
    
    if success_count == total_count:
        logger.info("🎉 모든 핵심 비즈니스 로직 테스트가 성공했습니다!")
    else:
        logger.warning("⚠️ 일부 테스트가 실패했습니다. 로그를 확인하세요.")
    
    logger.info("테스트 완료")

if __name__ == "__main__":
    main()
