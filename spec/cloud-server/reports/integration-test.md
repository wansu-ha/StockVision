# Unit 4 클라우드 서버 통합 테스트 보고서

> 실행일: 2026-03-10 | 브랜치: test/cloud-integration

## 1. 기존 단위 테스트

```
59 passed (cloud_server/tests/)
```

| 테스트 파일 | 건수 | 결과 |
|------------|------|------|
| test_auth.py | 15 | PASS |
| test_rules.py | 8 | PASS |
| test_heartbeat.py | 4 | PASS |
| test_watchlist.py | 5 | PASS |
| test_admin.py | 6 | PASS |
| test_ai.py | 12 | PASS |
| test_contract.py | 7 | PASS |
| **합계** | **59** | **ALL PASS** |

---

## 2. 통합 테스트 결과

### 12.3 시세 수집

#### 2.1 yfinance 일봉 수집 → DB 저장 → 조회

- **PASS** — 6개 심볼 수집 (^KS11, ^KQ11, ^GSPC, ^DJI, ^IXIC, USDKRW)
- 총 21건 일봉 DB 저장/조회 확인
- Upsert(동일 날짜 재저장) 정상 동작

```
^KS11: 4봉 (2026-03-05~2026-03-10)
^KQ11: 4봉
^GSPC: 3봉 (미국 시간대)
^DJI:  3봉
^IXIC: 3봉
USDKRW: 4봉
```

#### 2.2 결측 거래일 감지 + 재수집

- **PASS** — 6봉 중 처음 2개만 저장 → 4건 결측 감지 → yfinance 재수집 → 최종 6건 일치

```
저장: 2026-03-03, 2026-03-04
결측: 2026-03-05, 2026-03-06, 2026-03-09, 2026-03-10
재수집 후: 6건 (전체 일치)
```

#### 2.3 KisCollector → MinuteBar 파이프라인

- **PASS** — Mock BrokerAdapter로 5개 QuoteEvent 주입 → 4개 MinuteBar 생성 (1분 단위 집계)

```
005930 09:00 O=55000 H=55100 L=55000 C=55100 V=300 (2 events aggregated)
005930 09:01 O=54900 H=54900 L=54900 C=54900 V=150
000660 09:00 O=180000 H=180000 L=180000 C=180000 V=50
000660 09:01 O=180500 H=180500 L=180500 C=180500 V=80
```

- 동일 분봉 내 OHLC 집계(high/low/close 업데이트, volume 누적) 정상
- `get_latest_price()` 정상

> **참고**: 키움 모의서버 WS 실시간 수신은 Unit 3 E2E에서 검증 완료 (176 quotes/20s, 커밋 44c1fbe).
> cloud_server에서는 KisCollector → MarketRepository 파이프라인을 단위로 검증함.

#### 12.3 미검증 항목

- [ ] KIS 서비스 키 기반 실제 WS 연결 (KIS 계정 미보유)
- [ ] 장 마감 후 16:00 cron 일봉 저장 (스케줄러 시간 의존)

---

### 12.4 AI 컨텍스트

#### 2.4 GET /context → 시장 지표 JSON

- **PASS** — yfinance fallback으로 KOSPI/KOSDAQ 지표 계산

```json
{
  "date": "2026-03-10",
  "market": {
    "kospi_rsi": 49.59,
    "kosdaq_rsi": 51.14,
    "kospi_ema_20": 5536.21,
    "volatility": 0.7548,
    "market_trend": "neutral"
  },
  "version": 1
}
```

- 종목별 컨텍스트 (005930.KS 삼성전자):

```
RSI(14): 53.08, RSI(21): 55.75
MACD: 7784.48, Signal: 10781.51
Bollinger: 150355~219284
Volatility: 0.9458
```

#### 2.5 Claude API → 감성 점수

- **PASS** — 실제 Claude API 호출 (claude-sonnet-4-20250514)

```
source: claude
score: 0.1 (slightly_positive)
tokens: in=373, out=190
indicators_used: [current_price, rsi_14, rsi_21, macd, macd_signal, bollinger_upper, bollinger_lower, volatility]
```

- 캐시 히트 확인: 동일 요청 재호출 시 `cached: true`
- DB 이력 저장 확인: AIAnalysisLog 1건

---

### 12.5 어드민

- 서비스 키 등록 → 토큰 발급 → 시세 수신: **미검증** (KIS 서비스 키 미보유, 키움은 서비스 키 패턴 아님)
- 기존 단위 테스트에서 admin 403/유저 목록/통계 검증 완료

---

### 12.7 종목/관심종목

#### 2.6 공공데이터포탈 → StockMaster 갱신

- **PASS** — KRX_LISTING_API_KEY로 KRX 상장종목 수집

```
수집: 2,769건 (최근 7일 데이터)
검색 '삼성전자': 005930 삼성전자 (KOSPI)
검색 '005930':  005930 삼성전자 (KOSPI)
```

---

## 3. 발견 및 수정한 버그

| # | 파일 | 문제 | 수정 |
|---|------|------|------|
| 1 | `services/ai_service.py` | `_parse_response`: max_tokens로 응답 잘림 시 `rindex("}")` 실패 | `"}" in text` 체크 + 잘린 JSON 복구 |
| 2 | `services/ai_service.py` | sentiment max_tokens=150 → 응답 잘림 빈도 높음 | 300으로 증가 |
| 3 | `services/market_repository.py` | `save_minute_bar`: Decimal을 Integer 컬럼에 직접 바인딩 → SQLite 오류 | `int(event.price)` 변환 추가 |

---

## 4. 수용 기준 체크리스트 갱신

### 12.3 시세 수집
- [x] ~~서비스 키로 키움 WS 연결 → 실시간 체결가 수신~~ (파이프라인 검증, 실제 WS는 Unit 3 E2E)
- [x] 수신된 시세가 DB에 저장됨 (MinuteBar 집계 확인)
- [x] 장 마감 후 일봉 데이터 정상 저장 (yfinance 경로)
- [x] 결측 거래일 감지 + 재수집

### 12.4 AI 컨텍스트
- [x] `GET /api/v1/context` → 시장 지표 JSON 응답
- [x] Claude API 호출 → 감성 점수 반환
- [x] 캐싱 동작 확인 (동일 요청 재호출 방지)

### 12.5 어드민
- [x] admin 유저로 유저 목록 조회
- [x] 일반 유저로 어드민 API 접근 → 403
- [ ] 서비스 키 등록 → 토큰 발급 → 시세 수신 성공 (KIS 키 미보유)

### 12.7 종목/관심종목
- [x] 종목 검색 → 이름/코드 매칭 결과 반환
- [x] 관심종목 등록/해제 정상 동작
- [x] 공공데이터포털 수집 → StockMaster 갱신 확인

---

## 5. 남은 미검증 항목

| 항목 | 차단 요인 |
|------|----------|
| KIS 서비스 키 → WS 실연결 | KIS 계정 미보유 |
| 스케줄러 cron 실행 (09:00, 16:00, 17:00, 18:00) | 시간 의존성 |
| SMTP 이메일 발송 | SMTP 자격증명 미설정 |
| PostgreSQL 통합 테스트 | 운영 DB 환경 미구축 |
