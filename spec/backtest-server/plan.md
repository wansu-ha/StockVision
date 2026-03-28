> 작성일: 2026-03-28 | 상태: 초안 | Oracle Cloud

# 백테스트 서버 구현 계획

## 아키텍처

```
[프론트] → [:4010 클라우드] ──localhost──→ [:4040 백테스트]
                │                              │
                │                              │ localhost
                │                              ↓
                │                         [:4030 데이터 서버]
                │                              │
           [PostgreSQL]  ←─────────────────────┘
           ├── 서비스 데이터 (users, rules, jobs...)
           └── 시장 데이터 (bars, stocks...)
```

## 역할 분담

data-server plan에 통합 — 이 plan은 백테스트 서버 고유 구현 상세.

**Claude가 작성**: backtest_server/ 전체 코드, cloud_server 백테스트 프록시 수정
**사용자 액션**: 없음 (data-server plan의 VM 세팅에 포함)

## 구현 순서

data-server plan의 Step 2에 해당. 상세 내역:

### Step 2-1: 프로젝트 골격
- `backtest_server/main.py` — FastAPI 앱
- `backtest_server/core/config.py` — DATA_SERVER_URL (localhost:4030)
- `backtest_server/core/auth.py` — 내부 인증 (localhost 허용 + API Key)
- Dockerfile
- verify: 서버 기동 → /health 응답

### Step 2-2: 데이터 서버 클라이언트
- `backtest_server/services/data_client.py`
  - `get_bars(symbol, timeframe, start, end) -> list[dict]`
  - `check_collection_status(task_id) -> dict`
- verify: 데이터 서버 기동 상태에서 봉 조회 성공

### Step 2-3: BacktestRunner 이식
- `backtest_server/services/runner.py`
  - 기존 `cloud_server/services/backtest_runner.py` 복사
  - DB 직접 조회 → `data_client.get_bars()` 호출로 변경
  - sv_core 의존성 (parser, evaluator, calculator) 그대로 사용
- verify: 일봉 백테스트 단독 실행 → 결과 정상

### Step 2-4: 큐잉 시스템
- `backtest_server/services/queue_manager.py`
  - `asyncio.Queue(maxsize=20)` — 대기열
  - `ProcessPoolExecutor(max_workers=3)` — 병렬 실행
  - job 상태: queued → collecting → running → done/failed
  - 대기순번 계산
  - 타임아웃 5분
- verify: 동시 4개 요청 → 3 running + 1 queued

### Step 2-5: API 엔드포인트
- `backtest_server/api/backtest.py`
  - `POST /api/v1/backtest/run` → 202 + job_id
  - `GET /api/v1/backtest/jobs/{job_id}` → 상태/결과
- `backtest_server/api/health.py`
  - `GET /health` → active_jobs, queued_jobs, max_workers
- verify: curl로 전체 흐름 확인

### Step 2-6: 데이터 미존재 → 동적 수집 연동
- 데이터 서버 404 + task_id → 수집 대기 → 재조회 → 실행
- job 상태에 "데이터 수집중..." 메시지 반영
- verify: 없는 종목 요청 → 수집 → 백테스트 완료

### Step 3에 포함: 클라우드 서버 백테스트 프록시
- `cloud_server/api/backtest.py` 수정
  - 직접 실행 → localhost:4040 프록시
  - job 테이블에 상태 저장 (프론트 폴링용)
  - 캐시 판단 (동일 조건 hash)
- `cloud_server/models/backtest.py` 수정
  - status, queue_position, message, progress 필드 추가
- verify: 프론트 → 클라우드 → 백테스트 서버 → 결과 반환

## 검증 방법

| 항목 | 방법 |
|------|------|
| 서버 기동 | GET /health → { active_jobs, queued_jobs } |
| 일봉 백테스트 | POST /run → ~1초 → 결과 |
| 분봉 백테스트 | POST /run → ~10-30초 → 결과 |
| 동시 실행 | 4개 동시 → 3 running + 1 queued |
| 대기순번 | GET /jobs/{id} → queue_position 감소 |
| 타임아웃 | 5분 초과 → status: "failed" |
| 캐시 히트 | 동일 조건 재요청 → 즉시 반환 |
| 프론트 E2E | 백테스트 → 상태 표시 → 결과 차트 |
