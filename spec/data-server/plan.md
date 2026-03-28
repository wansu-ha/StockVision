> 작성일: 2026-03-28 | 상태: 초안 | Oracle Cloud

# 데이터 서버 + 인프라 이전 구현 계획

## 아키텍처 (이전 후)

```
[Vercel 프론트] ──→ [Oracle Cloud VM (공인 IP)]
                      ├── :4010 클라우드 서버
                      ├── :4030 데이터 서버
                      ├── :4040 백테스트 서버
                      └── PostgreSQL :5432

[로컬 서버 Bridge] ──→ [Oracle VM :4010] (기존과 동일, URL만 변경)
```

**폐기 대상**: Render 서버, Render PostgreSQL, UptimeRobot

## 역할 분담

### Claude가 하는 것

| 작업 | 내용 |
|------|------|
| Docker Compose 작성 | PostgreSQL + 클라우드 서버 + 데이터 서버 + 백테스트 서버 |
| 설치 스크립트 작성 | `scripts/setup-oracle.sh` (VM에서 실행) |
| data_server/ 코드 작성 | 모델, API, 수집기, 스케줄러 |
| backtest_server/ 코드 작성 | Runner 이식, 큐, API |
| cloud_server 수정 | 시세→데이터 서버 프록시, 백테스트→백테스트 서버 프록시 |
| local_server 수정 | bar_sync 대상 URL 변경 |
| Render 데이터 백업 스크립트 | pg_dump로 기존 DB 덤프 |
| 환경변수 정리 | Oracle용 .env 템플릿 |
| Vercel 환경변수 변경 | VITE_CLOUD_API_URL → Oracle IP |
| Render 서비스 정리 | API로 서비스 삭제/중단 |
| UptimeRobot 모니터 삭제 | API로 삭제 |

### 사용자가 해야 하는 것

| 작업 | 이유 |
|------|------|
| **Oracle Cloud 계정 생성** | 카드 등록 필요 (본인 인증) |
| **ARM VM 생성** | 콘솔에서 클릭 (가이드 제공) |
| **VM SSH 키 등록** | 접근용 |
| **VM 공인 IP 확보** | 콘솔에서 클릭 |
| **방화벽 규칙 설정** | 포트 4010 열기 (가이드 제공) |
| **VM에서 설치 스크립트 실행** | `ssh` 접속 → `./scripts/setup-oracle.sh` |

## 구현 순서

### Phase 1: 코드 준비 (Claude — 이 PC에서)

#### Step 1: data_server 프로젝트 생성
- `data_server/` 디렉토리 구조
- `main.py`, `core/config.py`, `core/database.py`
- 모델 복사 (market.py, fundamental.py)
- `api/bars.py` — 봉 조회 + ingest
- `api/stocks.py` — 종목 마스터
- `api/financials.py` — 재무/배당
- `api/collection.py` — 동적 수집 상태
- `services/market_repository.py` — DB CRUD
- `services/collector.py` — yfinance + 키움 수집
- `services/scheduler.py` — 일봉 갱신 스케줄
- `services/dynamic_collector.py` — 동적 수집 + 태스크 관리
- Dockerfile
- verify: 로컬에서 단독 기동 테스트

#### Step 2: backtest_server 프로젝트 생성
- `backtest_server/` 디렉토리 구조
- `main.py`, `core/config.py`, `core/auth.py`
- `services/runner.py` — BacktestRunner 이식 (DB→API 호출)
- `services/queue_manager.py` — 큐 + ProcessPoolExecutor
- `services/data_client.py` — 데이터 서버 클라이언트
- `api/backtest.py` — POST /run, GET /jobs/{id}
- Dockerfile
- verify: 데이터 서버와 연동 테스트

#### Step 3: cloud_server 수정
- 시세 조회 API → 데이터 서버 프록시 (localhost:4030)
- 백테스트 API → 백테스트 서버 프록시 (localhost:4040) + job 관리
- AI 브리핑 시세 참조 → 데이터 서버 API
- 수집기(collector/) 제거
- `config.py`에 DATA_SERVER_URL, BACKTEST_SERVER_URL 추가
- verify: 기존 API 호환성 유지

#### Step 4: local_server 수정
- `bar_sync.py` 대상 URL 환경변수화 (CLOUD_URL → 자동)
- verify: 기존 동작 유지

#### Step 5: Docker Compose + 설치 스크립트
- `docker-compose.oracle.yml` — PostgreSQL + 3개 서버
- `scripts/setup-oracle.sh`:
  - Docker/Docker Compose 설치
  - 레포 클론
  - .env 생성 안내 (시크릿 입력)
  - docker-compose up -d
  - DB 마이그레이션
  - Render DB → Oracle DB 데이터 이관 (pg_dump → pg_restore)
  - 일봉 초기 적재 (yfinance)
  - 헬스체크
- `scripts/setup-oracle-guide.md` — 사용자 가이드 (스크린샷 포함 VM 생성 절차)
- verify: 스크립트 문법 검증

### Phase 2: Oracle VM 세팅 (사용자 + Claude 가이드)

#### Step 6: Oracle VM 생성 (사용자)
- Oracle Cloud 계정 생성
- ARM VM 생성 (VM.Standard.A1.Flex, 4 OCPU, 24GB)
- 공인 IP 할당
- 방화벽: 4010 포트 오픈
- SSH 접속 확인
- verify: `ssh opc@{공인IP}` 접속 성공

#### Step 7: 설치 스크립트 실행 (사용자)
- VM에서 `git clone` → `./scripts/setup-oracle.sh`
- .env 파일 설정 (기존 시크릿 복사)
- verify: `curl http://{공인IP}:4010/health` → 200

### Phase 3: 이전 + 정리 (Claude)

#### Step 8: 데이터 이관
- Render PostgreSQL → Oracle PostgreSQL (pg_dump/restore)
- 테이블별 행 수 검증
- verify: Oracle DB에서 기존 데이터 정상 조회

#### Step 9: 프론트엔드 전환
- Vercel 환경변수: `VITE_CLOUD_API_URL` → Oracle IP
- 프론트에서 기존 기능 동작 확인
- verify: 프론트 로그인, 시세 조회, 전략 관리 정상

#### Step 10: 기존 인프라 정리
- UptimeRobot 모니터 삭제 (API)
- Render 서비스 중단/삭제 (API)
- Render PostgreSQL은 만료일(4/11)에 자동 삭제되므로 방치 가능
- verify: Render 대시보드 확인

## 검증 방법

| 항목 | 방법 |
|------|------|
| 서버 기동 | 3개 서버 `/health` → 200 |
| 봉 조회 | GET /api/v1/bars/005930 → OHLCV |
| 분봉 ingest | POST /api/v1/bars/ingest → count |
| 백테스트 | 프론트에서 백테스트 요청 → 결과 |
| 로그인/인증 | 기존 계정 로그인 성공 |
| 데이터 이관 | 테이블별 행 수 일치 |
| 기존 인프라 정리 | Render 비활성, UptimeRobot 삭제 |
