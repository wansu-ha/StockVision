# Step 7 보고서: 수집 스케줄러 (APScheduler)

> 완료일: 2026-03-05

## 구현 내용

### 생성된 파일

| 파일 | 설명 |
|------|------|
| `cloud_server/collector/scheduler.py` | APScheduler 스케줄러 |
| `cloud_server/services/yfinance_service.py` | yfinance 보조 수집 |

### 스케줄 목록

| 시간 (KST) | 작업 | ID |
|----------|------|-----|
| 09:00 | 키움 WS 시작 (장 시작) | kiwoom_ws_start |
| 16:00 | 일봉 저장 (장 마감 후) | daily_bars |
| 08:00 | 종목 마스터 갱신 | stock_master |
| 17:00 | yfinance 보조 수집 | yfinance |
| 18:00 | 데이터 정합성 체크 | integrity_check |

### YFinanceService

- 대상: ^KS11 (KOSPI), ^KQ11 (KOSDAQ), ^GSPC, USDKRW=X 등
- fetch_daily(symbols, start_date, end_date) → Dict[symbol, bars]
- fetch_recent(symbols, days) → 최근 N일 데이터

### 수집기 상태 관리

`_collector_status` 전역 dict로 상태 추적:
- status: running | stopped | error
- last_quote_time: 마지막 시세 수신 시각
- error_count: 누적 오류 수
- total_quotes: 총 수신 건수

### 정합성 체크

- 어제 날짜 DailyBar 존재 확인 (주말 제외)
- 누락 시 yfinance로 재수집 + 경고 로그

## 검증 결과

- [x] APScheduler KST timezone 설정
- [x] 5개 스케줄 등록 (cron trigger)
- [x] yfinance 수집 + DailyBar 저장
- [x] 정합성 체크 + 재수집 로직
- [x] 스케줄러 start/stop (lifespan 연동)
- [ ] 키움 WS 실제 연결 (Unit 1 대기)
