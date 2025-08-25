#!/usr/bin/env python3
"""
StockVision - 대량 주식 데이터 수집 스크립트
83개 주식의 기본 정보와 가격 데이터를 수집합니다.
"""

import time
import logging
from datetime import datetime
from app.services.data_collector import DataCollector
from stock_symbols import ALL_STOCKS, STOCKS_BY_SECTOR

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('stock_collection.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def collect_stocks_by_sector():
    """섹터별로 주식 데이터 수집"""
    collector = DataCollector()
    total_collected = 0
    total_failed = 0
    
    logger.info("=== 섹터별 주식 데이터 수집 시작 ===")
    
    for sector, symbols in STOCKS_BY_SECTOR.items():
        logger.info(f"\n--- {sector} 섹터 수집 시작 ({len(symbols)}개) ---")
        sector_collected = 0
        sector_failed = 0
        
        for i, symbol in enumerate(symbols, 1):
            try:
                logger.info(f"[{i}/{len(symbols)}] {symbol} 수집 중...")
                
                # 주식 정보 수집 및 저장
                stock_info = collector.collect_stock_info([symbol])
                if stock_info:
                    stock = collector.save_stock_to_db(stock_info[0])
                    if stock:
                        # 가격 데이터 수집 및 저장 (최근 1년)
                        prices_df = collector.collect_stock_prices(symbol, days=365)
                        if not prices_df.empty:
                            saved_count = collector.save_prices_to_db(stock.id, prices_df)
                            logger.info(f"✅ {symbol}: 주식 정보 + {saved_count}개 가격 데이터 저장 완료")
                            sector_collected += 1
                            total_collected += 1
                        else:
                            logger.warning(f"⚠️ {symbol}: 가격 데이터 없음")
                            sector_failed += 1
                            total_failed += 1
                    else:
                        logger.error(f"❌ {symbol}: 주식 저장 실패")
                        sector_failed += 1
                        total_failed += 1
                else:
                    logger.error(f"❌ {symbol}: 주식 정보 수집 실패")
                    sector_failed += 1
                    total_failed += 1
                
                # API 요청 제한 방지 (0.1초 대기)
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"❌ {symbol} 처리 중 오류: {str(e)}")
                sector_failed += 1
                total_failed += 1
                continue
        
        logger.info(f"--- {sector} 섹터 완료: {sector_collected}개 성공, {sector_failed}개 실패 ---")
    
    logger.info(f"\n=== 전체 수집 완료 ===")
    logger.info(f"총 성공: {total_collected}개")
    logger.info(f"총 실패: {total_failed}개")
    logger.info(f"성공률: {(total_collected / (total_collected + total_failed) * 100):.1f}%")
    
    return total_collected, total_failed

def collect_specific_stocks(symbols, days=365):
    """특정 주식들만 수집"""
    collector = DataCollector()
    collected = 0
    failed = 0
    
    logger.info(f"=== 특정 주식 수집 시작 ({len(symbols)}개) ===")
    
    for i, symbol in enumerate(symbols, 1):
        try:
            logger.info(f"[{i}/{len(symbols)}] {symbol} 수집 중...")
            
            # 주식 정보 수집 및 저장
            stock_info = collector.collect_stock_info([symbol])
            if stock_info:
                stock = collector.save_stock_to_db(stock_info[0])
                if stock:
                    # 가격 데이터 수집 및 저장
                    prices_df = collector.collect_stock_prices(symbol, days=days)
                    if not prices_df.empty:
                        saved_count = collector.save_prices_to_db(stock.id, prices_df)
                        logger.info(f"✅ {symbol}: 주식 정보 + {saved_count}개 가격 데이터 저장 완료")
                        collected += 1
                    else:
                        logger.warning(f"⚠️ {symbol}: 가격 데이터 없음")
                        failed += 1
                else:
                    logger.error(f"❌ {symbol}: 주식 저장 실패")
                    failed += 1
            else:
                logger.error(f"❌ {symbol}: 주식 정보 수집 실패")
                failed += 1
            
            # API 요청 제한 방지
            time.sleep(0.1)
            
        except Exception as e:
            logger.error(f"❌ {symbol} 처리 중 오류: {str(e)}")
            failed += 1
            continue
    
    logger.info(f"=== 특정 주식 수집 완료 ===")
    logger.info(f"성공: {collected}개, 실패: {failed}개")
    
    return collected, failed

def main():
    """메인 함수"""
    print("🚀 StockVision 대량 데이터 수집 시작")
    print("=" * 50)
    
    while True:
        print("\n📊 수집 옵션을 선택하세요:")
        print("1. 전체 주식 수집 (83개)")
        print("2. 특정 주식 수집")
        print("3. 섹터별 주식 수집")
        print("4. 현재 저장된 주식 확인")
        print("5. 종료")
        
        choice = input("\n선택 (1-5): ").strip()
        
        if choice == "1":
            print("\n⚠️ 전체 83개 주식 수집을 시작합니다. 시간이 오래 걸릴 수 있습니다.")
            confirm = input("계속하시겠습니까? (y/N): ").strip().lower()
            if confirm == 'y':
                start_time = time.time()
                collect_stocks_by_sector()
                end_time = time.time()
                print(f"\n⏱️ 총 소요 시간: {(end_time - start_time) / 60:.1f}분")
            else:
                print("취소되었습니다.")
                
        elif choice == "2":
            symbols_input = input("주식 심볼을 쉼표로 구분하여 입력 (예: AAPL,MSFT,GOOGL): ").strip()
            symbols = [s.strip().upper() for s in symbols_input.split(',') if s.strip()]
            if symbols:
                days = input("수집할 일수 (기본값: 365): ").strip()
                days = int(days) if days.isdigit() else 365
                collect_specific_stocks(symbols, days)
            else:
                print("올바른 심볼을 입력해주세요.")
                
        elif choice == "3":
            print("\n📋 사용 가능한 섹터:")
            for i, sector in enumerate(STOCKS_BY_SECTOR.keys(), 1):
                print(f"{i}. {sector}")
            
            sector_choice = input("\n섹터 번호를 선택하세요: ").strip()
            try:
                sector_index = int(sector_choice) - 1
                sectors = list(STOCKS_BY_SECTOR.keys())
                if 0 <= sector_index < len(sectors):
                    selected_sector = sectors[sector_index]
                    symbols = STOCKS_BY_SECTOR[selected_sector]
                    print(f"\n{selected_sector} 섹터 ({len(symbols)}개) 수집을 시작합니다.")
                    collect_specific_stocks(symbols)
                else:
                    print("올바른 섹터 번호를 선택해주세요.")
            except ValueError:
                print("올바른 숫자를 입력해주세요.")
                
        elif choice == "4":
            from app.core.database import SessionLocal
            from app.models.stock import Stock
            
            session = SessionLocal()
            stocks = session.query(Stock).all()
            session.close()
            
            print(f"\n📊 현재 저장된 주식: {len(stocks)}개")
            for stock in stocks:
                print(f"- {stock.symbol}: {stock.name} ({stock.sector})")
                
        elif choice == "5":
            print("👋 프로그램을 종료합니다.")
            break
            
        else:
            print("올바른 옵션을 선택해주세요.")

if __name__ == "__main__":
    main()
