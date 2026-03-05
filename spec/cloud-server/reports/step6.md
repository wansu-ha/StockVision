# Step 6 보고서: 시세 저장 (DailyBar, MinuteBar, StockMaster)

> 완료일: 2026-03-05

## 구현 내용

### 생성된 파일

| 파일 | 설명 |
|------|------|
| `cloud_server/models/market.py` | StockMaster, DailyBar, MinuteBar |
| `cloud_server/services/market_repository.py` | 시장 데이터 레포지토리 |

### 데이터 모델

**DailyBar** - 일봉 (5년+ 보관)
- symbol, date (UniqueConstraint)
- open, high, low, close (int), volume (BigInteger), change_pct

**MinuteBar** - 분봉 (1년 보관)
- symbol, timestamp (UniqueConstraint)
- OHLCV (timestamp는 1분 단위 정규화)

**StockMaster** - 종목 마스터
- symbol (PK), name, market (KOSPI|KOSDAQ|OVERSEAS), sector

### MarketRepository 핵심 로직

**save_minute_bar(event)**:
1. timestamp를 1분 단위로 정규화 (replace(second=0, microsecond=0))
2. 같은 symbol+timestamp 기존 바가 있으면 high/low/close/volume 업데이트
3. 없으면 신규 생성

**save_daily_bar(symbol, date, ohlcv)**:
- upsert 방식 (기존 있으면 업데이트, 없으면 신규)

## 검증 결과

- [x] 3개 모델 정의 (인덱스, UniqueConstraint)
- [x] 분봉 1분 집계 로직 (OHLCV 업데이트)
- [x] 일봉 upsert
- [x] 결측 데이터 확인 (has_daily_bar)
