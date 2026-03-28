> 작성일: 2026-03-28 | 상태: 초안 | Oracle Cloud

# 백테스트 서버 (Backtest Server)

## 목표

백테스트 연산을 전담하는 독립 서버.
Oracle Cloud VM에서 데이터 서버와 같은 호스트에서 운영.
데이터 서버에서 시세를 조회하고, DSL 전략을 평가하여 결과를 반환한다.

## 배경

- Render Free tier: 512MB 메모리 → 분봉 백테스트 불가
- Oracle Cloud Always Free: 24GB RAM → 충분
- 기존 BacktestRunner는 순수 Python → 이식 용이
- sv_core (DSL 파서 + 지표)는 이미 독립 패키지

## 인프라 구성

```
[프론트] → [Oracle VM :4010 클라우드 서버]
               │
               │  백테스트 요청
               ↓
          [:4040 백테스트 서버]
               │
               │  봉 데이터 조회 (localhost)
               ↓
          [:4030 데이터 서버] → [PostgreSQL :5432]
```

모든 통신이 localhost — 지연 거의 없음.

## 요구사항

### 기능적 요구사항

| ID | 요구사항 | 우선순위 |
|----|---------|---------|
| F1 | 클라우드 서버로부터 백테스트 요청 수신 (localhost HTTP) | P0 |
| F2 | 데이터 서버 API에서 봉 데이터 조회 (localhost) | P0 |
| F3 | sv_core DSL 파서 + 지표로 백테스트 실행 | P0 |
| F4 | 결과를 클라우드 서버에 반환 | P0 |
| F5 | 동시 실행 제한 + 메모리 큐 + 대기번호 관리 | P0 |
| F6 | 작업 진행 상태 조회 API (대기순번, 진행률, 메시지) | P1 |
| F7 | 데이터 미존재 시 데이터 서버에 수집 요청 → 완료 후 실행 | P1 |
| F8 | 작업 타임아웃 (5분) | P1 |

### 비기능적 요구사항

| 항목 | 목표 |
|------|------|
| 동시 실행 | 최대 3개 (ProcessPoolExecutor) |
| 큐 크기 | 최대 20개, 초과 시 "서버 바쁨" 반환 |
| 일봉 백테스트 | ~1초 |
| 분봉 백테스트 1년 | ~10-30초 |
| 가용성 | Docker restart policy로 자동 복구 |

## 수용 기준

- [ ] Oracle VM에서 FastAPI 서버 기동 (:4040)
- [ ] 클라우드 서버에서 백테스트 요청 → 실행 → 결과 반환
- [ ] 데이터 서버 API로 봉 데이터 조회하여 백테스트 수행
- [ ] 동시 3개 실행 + 초과분 큐 대기
- [ ] 대기순번/진행률 상태 조회 API
- [ ] 데이터 미존재 시 수집 → "데이터 수집중..." → 완료 후 자동 실행
- [ ] 작업당 5분 타임아웃

## 범위

### 포함

- 백테스트 실행 엔진 (기존 BacktestRunner 이식)
- 큐잉 시스템 (메모리 큐 + ProcessPoolExecutor)
- 작업 상태 조회 API
- 데이터 서버 연동 (localhost HTTP)

### 미포함

- 시세 데이터 저장/수집 (`data-server` spec 범위)
- 백테스트 결과 영구 저장 (클라우드 서버 DB에 저장)
- 결과 캐싱 (클라우드 서버에서 판단)
- 스크리닝/AI 분석 등 추가 연산 (향후 확장)

## 통신 흐름

### 기본 흐름

```
1. [프론트] → [클라우드 :4010]: 백테스트 요청 + DSL 스크립트 + 설정
2. [클라우드]: 캐시 확인 → 없으면 백테스트 서버에 전달
3. [클라우드] → [백테스트 :4040]: POST /run (localhost)
4. [백테스트] → [데이터 :4030]: 봉 조회 (localhost)
5. [백테스트]: 연산 실행
6. [백테스트] → [클라우드]: 결과 반환
7. [클라우드]: DB에 결과 저장 + 프론트에 반환
```

### 데이터 미존재 시

```
1. [백테스트] → [데이터]: 봉 요청 → 404 + task_id
2. [백테스트]: 상태를 "데이터 수집중..." 으로 변경, 폴링 대기
3. [데이터]: 수집 완료
4. [백테스트]: 재조회 → 백테스트 실행
```

### 프론트 상태 조회 (폴링)

```
프론트: 3초 간격 GET /api/v1/backtest/jobs/{job_id}

응답 예시:
  { status: "queued",      queue_position: 2, message: "대기중 (2번째)" }
  { status: "collecting",  progress: 57,      message: "005930 분봉 수집중..." }
  { status: "running",     progress: 45,      message: "백테스트 실행중..." }
  { status: "done",        result: { ... } }
  { status: "failed",      error: "타임아웃" }
```

## API 설계

### 백테스트 요청

```
POST /api/v1/backtest/run

Body: {
  symbol: "005930",
  timeframe: "1d",
  start_date: "2025-01-01",
  end_date: "2026-03-28",
  script: "RSI(14) < 30이면 매수...",
  initial_cash: 10000000,
  commission_rate: 0.00015,
  tax_rate: 0.0018,
  slippage_rate: 0.001
}

202: { job_id: "job-xxx", status: "queued", queue_position: 0 }
503: { error: "서버 바쁨", queue_size: 20 }
```

### 작업 상태 조회

```
GET /api/v1/backtest/jobs/{job_id}

200: { status: "running", progress: 45, message: "백테스트 실행중..." }
```

### 서버 상태

```
GET /health

200: { status: "healthy", active_jobs: 2, queued_jobs: 3, max_workers: 3 }
```

## 클라우드 서버 변경사항

| 항목 | 변경 |
|------|------|
| POST /api/v1/backtest/run | 직접 실행 → localhost:4040 프록시 + job 생성 |
| GET /api/v1/backtest/jobs/{id} | 신규 엔드포인트 (job 상태 조회) |
| backtest_executions 테이블 | job 상태 필드 추가 |
| BacktestRunner | 클라우드 서버에서 제거 (백테스트 서버로 이관) |
| 캐시 판단 로직 | 동일 조건 hash 비교 후 기존 결과 반환 |

## 로드밸런싱 (향후)

클라우드 서버가 job 테이블로 큐를 관리하므로,
나중에 워커 추가 시 분배 구조로 확장 가능.

## 참고

- 기존 BacktestRunner: `cloud_server/services/backtest_runner.py`
- 기존 백테스트 API: `cloud_server/api/backtest.py`
- sv_core 파서/지표: `sv_core/parsing/`, `sv_core/indicators/`
- 백테스트 모델: `cloud_server/models/backtest.py`
