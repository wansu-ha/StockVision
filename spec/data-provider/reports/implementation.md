# DataProvider 구현 보고서

> 작성일: 2026-03-08

## 요약

DataProvider ABC + YFinance/DART 프로바이더 + Aggregator + REST API + 스케줄러 통합.
Plan Step 1~7 구현 완료. Step 8~9(KIS/키움)는 서비스 키 미등록으로 보류. Step 10(프론트엔드)은 별도.

## 구현 파일

### 신규 (9파일)

| 파일 | 내용 |
|------|------|
| `cloud_server/data/__init__.py` | 패키지 초기화 |
| `cloud_server/data/provider.py` | DataProvider ABC + DailyBar, ProviderQuote, FinancialData, DividendData |
| `cloud_server/data/yfinance_provider.py` | YFinanceProvider (price, quote, dividends) |
| `cloud_server/data/dart_provider.py` | DartProvider (financials, dividends, corp_code 매핑) |
| `cloud_server/data/aggregator.py` | DataAggregator (우선순위 기반 라우팅, 타임아웃, 폴백) |
| `cloud_server/data/factory.py` | create_aggregator(), get/set_aggregator() |
| `cloud_server/api/market_data.py` | /bars, /quote, /financials, /dividends 엔드포인트 |
| `cloud_server/models/fundamental.py` | CompanyFinancial, CompanyDividend DB 모델 |
| `spec/data-provider/reports/implementation.md` | 본 보고서 |

### 수정 (5파일)

| 파일 | 변경 |
|------|------|
| `cloud_server/models/market.py` | StockMaster에 corp_code 컬럼 + 인덱스 추가 |
| `cloud_server/core/init_db.py` | CompanyFinancial, CompanyDividend import 추가 |
| `cloud_server/core/config.py` | DART_API_KEY 설정 추가 |
| `cloud_server/main.py` | market_data_router 등록, DataAggregator lifespan 초기화 |
| `cloud_server/collector/scheduler.py` | save_daily_bars → Aggregator 경유, update_corp_codes 주 1회 작업 추가 |

## 설계 결정

### Aggregator 라우팅
- price → yfinance만 (DART에 가격 없음)
- financials → dart만 (유일한 정본)
- dividends → dart 우선 → yfinance 폴백

### 심볼 변환 (YFinance)
- market_lookup dict 주입 패턴 (StockMaster.market 참조)
- 기본값: `.KS` (KOSPI, 더 큰 시장)

### API — DB 캐시 + on-demand 수집
- `/bars`: DB에 캐시 있으면 반환, 없으면 Aggregator → 수집 → DB 저장 → 반환
- `/financials`, `/dividends`: 동일 패턴

### corp_code 매핑
- DART 고유번호 API → ZIP → XML 파싱 → {stock_code: corp_code}
- 스케줄러: 매주 월요일 08:30 KST에 NULL인 종목 대상 갱신

## 검증

- 전체 모듈 import chain: OK
- Aggregator routing: price→yfinance, financials→dart, dividends→dart+yfinance
- API routes: 4개 엔드포인트 정상 등록

## plan과의 차이

| plan | 실제 | 이유 |
|------|------|------|
| Step 8~9 KIS/키움 프로바이더 | 미구현 | 서비스 키 미등록 |
| Step 10 프론트엔드 전환 | 미구현 | 사용자 지시로 프론트엔드 스킵 |
| `cloud_server/data/factory.py` | plan에 없음 | Aggregator 생명주기 관리 필요 |
