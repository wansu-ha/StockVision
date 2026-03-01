"""개발용 시드 데이터 스크립트

사용법:
    cd backend
    python -m scripts.seed_data

기본 한국 주식 5종목을 등록하고 가격/지표 데이터를 수집합니다.
"""
import asyncio
import sys
import os

# backend/ 디렉토리를 PYTHONPATH에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.data_collector import DataCollector


# 기본 시드 종목 (코스피 대형주)
DEFAULT_SYMBOLS = [
    "005930",  # 삼성전자
    "000660",  # SK하이닉스
    "035420",  # NAVER
    "005380",  # 현대자동차
    "051910",  # LG화학
]


async def seed():
    print(f"시드 데이터 등록 시작: {len(DEFAULT_SYMBOLS)}개 종목")
    print(f"종목: {', '.join(DEFAULT_SYMBOLS)}")
    print("-" * 50)

    collector = DataCollector()
    results = await collector.register_stocks(DEFAULT_SYMBOLS, days=730)

    print("-" * 50)
    print(f"등록 성공: {len(results['registered'])}개")
    for item in results['registered']:
        print(f"  {item['symbol']} ({item['name']}) - 가격: {item['prices']}개, 지표: {item['indicators']}개")

    if results['failed']:
        print(f"등록 실패: {len(results['failed'])}개")
        for item in results['failed']:
            print(f"  {item['symbol']}: {item['reason']}")

    print(f"총 가격 데이터: {results['total_prices']}개")
    print(f"총 지표 데이터: {results['total_indicators']}개")


if __name__ == "__main__":
    asyncio.run(seed())
