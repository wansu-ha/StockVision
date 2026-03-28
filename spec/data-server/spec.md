> 작성일: 2026-03-28 | 상태: 초안 | v3 (Oracle Cloud)
>
> v1: 클라우드 통합 (SUPERSEDED)
> v2: PC 온프레미스 (SUPERSEDED → Oracle Cloud로 변경)

# 데이터 서버 (Data Server) v3

## 목표

시장 데이터(시세, 재무, 종목 메타)를 전담 저장·수집·제공하는 독립 서버.
Oracle Cloud Always Free VM에서 클라우드 서버, 백테스트 서버와 함께 운영.
Render/Neon 무료 플랜의 용량·sleep 제약을 완전히 해소한다.

## 배경

- Render Free: 512MB 메모리, 15분 sleep, PostgreSQL 30일 만료
- Neon Free: 500MB 스토리지 제한
- Oracle Cloud Always Free: ARM 4코어/24GB RAM/200GB 스토리지, 만료 없음
- 전종목 시세 데이터는 전용 인프라 필요 (일봉 수GB, 분봉 수십GB)
- 시장 데이터(객관적 사실)와 서비스 데이터(유저/규칙/결과)를 논리적 분리

## 인프라 구성

```
[Vercel 프론트] ──→ [Oracle Cloud VM (공인 IP)]
                      ├── :4010 클라우드 서버 (메인 API)
                      ├── :4030 데이터 서버 (시세 API)
                      ├── :4040 백테스트 서버 (연산)
                      └── PostgreSQL :5432 (단일 DB, 스키마 분리)
```

- 모든 서버가 같은 VM → localhost 통신, 터널 불필요
- 공인 IP → Vercel에서 직접 접근
- Render, Neon, UptimeRobot 전부 불필요

## 요구사항

### 기능적 요구사항

| ID | 요구사항 | 우선순위 |
|----|---------|---------|
| F1 | 전종목 일봉, 관심 종목 분봉을 PostgreSQL에 저장 | P0 |
| F2 | REST API로 봉 데이터 조회 (종목, 기간, 타임프레임 필터) | P0 |
| F3 | 종목 마스터(거래소 목록, 업종, 시가총액) 관리 | P0 |
| F4 | 일봉 초기 적재 (yfinance) + 매일 장 마감 후 갱신 | P0 |
| F5 | 분봉 초기 적재 (키움 REST API, 1년치) | P1 |
| F6 | 분봉 실시간 누적 (로컬 서버 Bridge 수집분 동기화 수신) | P1 |
| F7 | 요청 데이터 미존재 시 동적 수집 + 진행 상태 반환 | P1 |
| F8 | 재무제표, 배당 정보 저장·조회 | P2 |
| F9 | 하트비트/상태 API | P1 |

### 비기능적 요구사항

| 항목 | 목표 |
|------|------|
| 가용성 | Docker restart policy로 자동 복구 |
| 접근 제어 | 클라우드 서버(localhost)와 외부 인증된 요청만 |
| 로깅 | Docker 볼륨에 저장 |
| 데이터 보관 | 일봉 무제한, 분봉 보관 정책 운영 후 결정 |

## 수용 기준

- [ ] Oracle VM에서 FastAPI 서버 기동 (:4030)
- [ ] PostgreSQL에 시장 데이터 테이블 생성
- [ ] 봉 데이터 조회 REST API 동작
- [ ] yfinance 일봉 초기 적재 동작
- [ ] 키움 REST API 분봉 초기 적재 동작
- [ ] 데이터 미존재 시 동적 수집 → 진행 상태 반환
- [ ] 클라우드 서버에서 localhost:4030 접근 가능
- [ ] Docker Compose로 자동 시작

## 범위

### 포함

- 시세 데이터 저장·조회·수집 REST API
- PostgreSQL 스키마 (기존 클라우드 시세 테이블 이관)
- yfinance / 키움 REST 수집기
- 동적 수집 + 상태 반환

### 미포함

- 백테스트 연산 (`backtest-server` spec 범위)
- 유저/규칙/인증 등 서비스 데이터 (클라우드 서버가 관리)
- 대신증권 API 연동 (향후 확장)

## API 설계

### 봉 데이터 조회

```
GET /api/v1/bars/{symbol}
  ?timeframe=1d|1m|5m|15m|1h
  &start=2025-01-01
  &end=2026-03-28
  &limit=1000

200: { success: true, data: [ {date, open, high, low, close, volume}, ... ], count: N }
404: { success: false, message: "데이터 없음", collection_task_id: "task-xxx" }
```

### 동적 수집 상태

```
GET /api/v1/collection/{task_id}

200: { status: "collecting", message: "005930 분봉 수집중...", progress: 57 }
200: { status: "done", message: "수집 완료", data_count: 24500 }
```

### 종목 마스터

```
GET /api/v1/stocks?market=KOSPI|KOSDAQ&search=삼성
GET /api/v1/stocks/{symbol}
```

### 재무 데이터

```
GET /api/v1/stocks/{symbol}/financials
GET /api/v1/stocks/{symbol}/dividends
```

### 분봉 ingest (로컬 서버 → 데이터 서버)

```
POST /api/v1/bars/ingest
Body: { bars: [ {symbol, timestamp, open, high, low, close, volume}, ... ] }
```

### 서버 상태

```
GET /health
```

## DB 스키마

기존 클라우드 테이블을 이관 (같은 PostgreSQL 인스턴스, 별도 스키마 또는 동일 DB):

| 테이블 | 원본 모델 |
|--------|----------|
| stock_master | cloud_server/models/market.py |
| daily_bars | cloud_server/models/market.py |
| minute_bars | cloud_server/models/market.py |
| company_financials | cloud_server/models/fundamental.py |
| company_dividends | cloud_server/models/fundamental.py |

## 클라우드 서버 변경사항

| 항목 | 변경 |
|------|------|
| 시세 조회 API | localhost:4030 프록시로 변경 |
| AI 브리핑 시세 참조 | localhost:4030 API 호출 |
| KIS collector | 데이터 서버로 이관, 클라우드에서 제거 |
| DATABASE_URL | Oracle PostgreSQL로 변경 |

## 참고

- 기존 클라우드 시세 모델: `cloud_server/models/market.py`
- 기존 수집기: `cloud_server/collector/scheduler.py`, `cloud_server/collector/kis_collector.py`
- 로컬 분봉 저장: `local_server/storage/minute_bar.py`
- 로컬 분봉 동기화: `local_server/cloud/bar_sync.py`
