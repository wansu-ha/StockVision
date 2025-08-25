# StockVision - 주식 심볼 목록
# 다양한 섹터와 시가총액을 가진 인기 주식들

# Technology (기술)
TECH_STOCKS = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA',  # 현재 포함된 주식들
    'NVDA', 'META', 'NFLX', 'ADBE', 'CRM',    # 추가 기술주
    'ORCL', 'INTC', 'AMD', 'QCOM', 'AVGO'     # 반도체 및 하드웨어
]

# Healthcare (헬스케어)
HEALTHCARE_STOCKS = [
    'JNJ', 'PFE', 'UNH', 'ABBV', 'TMO',      # 제약 및 의료기기
    'DHR', 'LLY', 'ABT', 'BMY', 'AMGN'       # 바이오테크
]

# Financial (금융)
FINANCIAL_STOCKS = [
    'JPM', 'BAC', 'WFC', 'GS', 'MS',         # 은행 및 투자은행
    'BRK-B', 'V', 'MA', 'AXP', 'C'           # 보험 및 신용카드
]

# Consumer (소비재)
CONSUMER_STOCKS = [
    'PG', 'KO', 'PEP', 'WMT', 'HD',          # 생활용품 및 소매
    'MCD', 'SBUX', 'NKE', 'DIS', 'NFLX'      # 엔터테인먼트
]

# Industrial (산업재)
INDUSTRIAL_STOCKS = [
    'BA', 'CAT', 'GE', 'MMM', 'HON',         # 항공, 건설, 제조
    'UPS', 'FDX', 'LMT', 'RTX', 'DE'         # 물류 및 방산
]

# Energy (에너지)
ENERGY_STOCKS = [
    'XOM', 'CVX', 'COP', 'EOG', 'SLB',       # 석유 및 가스
    'NEE', 'DUK', 'SO', 'D', 'AEP'           # 전력 및 재생에너지
]

# Communication (통신)
COMMUNICATION_STOCKS = [
    'T', 'VZ', 'CMCSA', 'CHTR', 'TMUS',      # 통신사
    'FOX', 'PARA', 'NWSA', 'NWS'             # 미디어
]

# Real Estate (부동산)
REAL_ESTATE_STOCKS = [
    'PLD', 'AMT', 'CCI', 'EQIX', 'DLR',      # REIT 및 부동산
    'SPG', 'O', 'EQR', 'AVB', 'MAA'          # 상업용 부동산
]

# 모든 주식 심볼 통합
ALL_STOCKS = (
    TECH_STOCKS + 
    HEALTHCARE_STOCKS + 
    FINANCIAL_STOCKS + 
    CONSUMER_STOCKS + 
    INDUSTRIAL_STOCKS + 
    ENERGY_STOCKS + 
    COMMUNICATION_STOCKS + 
    REAL_ESTATE_STOCKS
)

# 중복 제거 및 정렬
ALL_STOCKS = sorted(list(set(ALL_STOCKS)))

# 섹터별 주식 딕셔너리
STOCKS_BY_SECTOR = {
    'Technology': TECH_STOCKS,
    'Healthcare': HEALTHCARE_STOCKS,
    'Financial': FINANCIAL_STOCKS,
    'Consumer': CONSUMER_STOCKS,
    'Industrial': INDUSTRIAL_STOCKS,
    'Energy': ENERGY_STOCKS,
    'Communication': COMMUNICATION_STOCKS,
    'Real Estate': REAL_ESTATE_STOCKS
}

if __name__ == "__main__":
    print(f"총 주식 수: {len(ALL_STOCKS)}개")
    print("\n섹터별 주식 수:")
    for sector, stocks in STOCKS_BY_SECTOR.items():
        print(f"{sector}: {len(stocks)}개")
    
    print(f"\n전체 주식 목록:")
    for i, symbol in enumerate(ALL_STOCKS, 1):
        print(f"{i:2d}. {symbol}")
