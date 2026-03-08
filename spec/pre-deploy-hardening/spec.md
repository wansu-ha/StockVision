# 배포 전 내실 강화 명세서 (pre-deploy-hardening)

> 작성일: 2026-03-09 | 상태: 초안

---

## 1. 목표

코드 리뷰에서 발견된 CRITICAL/WARNING 문제를 수정하여
클라우드 서버 배포 + 로컬 서버 패키징이 가능한 상태로 만든다.

---

## 2. 문제 목록

### CRITICAL — 배포 불가

| ID | 문제 | 영향 |
|----|------|------|
| C1 | 로컬↔클라우드 API 경로 불일치 | 하트비트 404, 규칙 sync 404. 연동 전체 불능 |
| C3 | Alembic 마이그레이션 없음 | PostgreSQL에서 스키마 변경 반영 불가 |
| C4 | CORS에 프로덕션 도메인 없음 | 배포 시 프론트 연결 불가 |

### WARNING — 배포에 영향

| ID | 문제 | 영향 |
|----|------|------|
| W1 | cloud_server Dockerfile 없음 | 컨테이너 배포 불가 |
| W3 | 트레이 엔진 토글이 플래그만 변경 | 사용자 혼란 (시작 눌러도 엔진 안 돌아감) |
| W5 | CONFIG_ENCRYPTION_KEY 미검증 | 장 시작 시(09:00) 조용히 실패 |

### 제외 (v2 이후)

| ID | 사유 |
|----|------|
| C2 | `.env`는 git 미추적 확인됨. 리뷰어 오판 |
| W2 | 단일 프로세스 운영 시 기본 풀 충분 |
| W4 | 단일 프로세스, 재시작 빈도 낮음 |

---

## 3. 요구사항

### C1: API 경로 + payload 정합성

**현황** (전부 불일치):

| 기능 | 클라이언트 경로 | 서버 경로 | 상태 |
|------|----------------|----------|------|
| 하트비트 | `/api/local/heartbeat` | `/api/v1/heartbeat` | 404 |
| 규칙 fetch | `/api/rules` | `/api/v1/rules` | 404 |

하트비트 payload 불일치:

| 필드 | 클라이언트 | 서버 (HeartbeatBody) |
|------|-----------|---------------------|
| uuid | 미전송 | **필수** |
| timestamp | 미전송 | **필수** |
| strategy_engine | "running"/"stopped" | 없음 (engine_running: bool) |
| version | 미전송 | Optional |
| os | 미전송 | Optional |

**수정 방향**: 클라이언트(`local_server/cloud/client.py`, `heartbeat.py`)를 서버 스키마에 맞춘다.
서버 API 경로가 `/api/v1/` prefix로 통일되어 있으므로, 클라이언트가 서버에 맞춘다.

- `send_heartbeat()` 경로: `/api/local/heartbeat` → `/api/v1/heartbeat`
- `fetch_rules()` 경로: `/api/rules` → `/api/v1/rules`
- `_build_heartbeat_payload()`: 서버 `HeartbeatBody` 스키마에 맞게 필드 추가
  - `uuid`: 로컬 서버 고유 식별자 (config에서 생성/저장)
  - `timestamp`: `datetime.utcnow().isoformat()`
  - `engine_running`: bool
  - `version`: config의 `server.version`
  - `os`: `platform.system()`

### C3: Alembic 마이그레이션 초기화

**현황**: `Base.metadata.create_all()` — 테이블 생성만, 컬럼 변경 무시.

**수정 방향**:
- `alembic init cloud_server/alembic`
- 현재 모델 기반 초기 마이그레이션 생성
- `init_db()`에서 `create_all()` 유지 (개발/테스트용)
- 프로덕션은 `alembic upgrade head`로 전환

### C4: CORS 환경변수화

**현황**: `CORS_ORIGINS`가 하드코딩 리스트 `["http://localhost:5173"]`.

**수정 방향**:
- `CORS_ORIGINS` 환경변수를 콤마 구분 문자열로 파싱
- 기본값은 현재 개발 서버 유지
- 예: `CORS_ORIGINS=https://stockvision.com,https://www.stockvision.com`

### W1: cloud_server Dockerfile

**현황**: `docker-compose.yml`에 PostgreSQL/Redis만 정의.

**수정 방향**:
- `cloud_server/Dockerfile` 생성 (Python 3.13, pip install, uvicorn)
- `docker-compose.yml`에 `cloud_server` 서비스 추가
- 환경변수를 `docker-compose.yml`의 `environment`/`.env`로 주입

### W3: 트레이 엔진 토글 → 실제 API 호출

**현황**: `_on_toggle_engine()`이 `set_engine_running()` 플래그만 변경.
실제 엔진 시작/중지는 `/api/strategy/start`, `/api/strategy/stop` 엔드포인트만 처리.

**수정 방향**:
- 트레이 토글에서 `httpx.post("http://127.0.0.1:{port}/api/strategy/start")` 호출
- shared secret 헤더 포함
- 비동기 호출이 필요하므로 별도 스레드에서 `requests` 사용 (pystray는 동기 콜백)

### W5: CONFIG_ENCRYPTION_KEY 시작 시 검증

**현황**: `validate_settings()`가 `SECRET_KEY`만 검증. `CONFIG_ENCRYPTION_KEY`는 런타임에 `_get_key()` 호출 시 실패.

**수정 방향**:
- `validate_settings()`에 `CONFIG_ENCRYPTION_KEY` 검증 추가
- 단, 개발 환경에서는 암호화 기능을 사용하지 않을 수 있으므로 WARNING 로그 + 선택적 차단

---

## 4. 수용 기준

### C1: API 정합성

- [ ] `local_server` → `cloud_server` 하트비트 전송 시 200 응답
- [ ] 하트비트 payload가 서버 `HeartbeatBody` 스키마와 일치
- [ ] `local_server` → `cloud_server` 규칙 fetch 시 200 + 규칙 리스트 반환
- [ ] 양쪽 테스트에서 동일한 URL/payload 사용 (계약 테스트 갱신)

### C3: Alembic

- [ ] `alembic.ini` + `cloud_server/alembic/` 디렉토리 존재
- [ ] `alembic revision --autogenerate` 실행 가능
- [ ] `alembic upgrade head` → 빈 DB에 전체 테이블 생성

### C4: CORS

- [ ] `CORS_ORIGINS` 환경변수로 허용 도메인 설정 가능
- [ ] 환경변수 미설정 시 기본값 `http://localhost:5173` 유지
- [ ] 클라우드 서버 테스트 통과 (기존 38개 유지)

### W1: Docker

- [ ] `cloud_server/Dockerfile` 존재
- [ ] `docker-compose up` → cloud_server + PostgreSQL + Redis 전체 기동
- [ ] 헬스체크 엔드포인트 응답 확인

### W3: 트레이 엔진 토글

- [ ] 트레이 "엔진 시작" → 실제 `/api/strategy/start` 호출
- [ ] 트레이 "엔진 중지" → 실제 `/api/strategy/stop` 호출
- [ ] 브로커 미설정 시 토스트 에러 알림

### W5: 암호화 키 검증

- [ ] 서버 시작 시 `CONFIG_ENCRYPTION_KEY` 미설정이면 WARNING 로그
- [ ] 암호화 기능 호출 시 키 없으면 명확한 에러 메시지

---

## 5. 범위

### 포함

- API 경로/payload 정합성 (C1)
- Alembic 초기화 (C3)
- CORS 환경변수화 (C4)
- Dockerfile + docker-compose 앱 서비스 (W1)
- 트레이 엔진 토글 실제 동작 (W3)
- CONFIG_ENCRYPTION_KEY 검증 (W5)

### 미포함

- PostgreSQL 커넥션 풀 튜닝 (W2 → v2)
- Redis Rate Limiter (W4 → v2)
- .env git 히스토리 정리 (C2 → 오판 확인, 불필요)
- JWT 자동 갱신 검증 (별도 작업)
- PyInstaller 빌드 (별도 작업)
- 프론트엔드 (별도 Unit)

---

## 6. 변경 파일 (예상)

| 파일 | 변경 |
|------|------|
| `local_server/cloud/client.py` | 하트비트/규칙 URL 수정 |
| `local_server/cloud/heartbeat.py` | payload 필드 서버 스키마 대응 |
| `local_server/tests/test_cloud_client.py` | 계약 테스트 URL/payload 갱신 |
| `cloud_server/core/config.py` | CORS_ORIGINS 환경변수 파싱 |
| `cloud_server/core/config.py` | validate_settings() 확장 |
| `cloud_server/alembic/` | 신규 — Alembic 설정 + 초기 마이그레이션 |
| `cloud_server/Dockerfile` | 신규 |
| `docker-compose.yml` | cloud_server 서비스 추가 |
| `local_server/tray/tray_app.py` | 엔진 토글 → API 호출 |
| `cloud_server/tests/` | 기존 테스트 유지 확인 |

---

## 7. 참고

- `docs/architecture.md` §4 (3프로세스 구조)
- `cloud_server/api/heartbeat.py` — 서버 하트비트 스키마
- `local_server/cloud/client.py` — 클라이언트 HTTP 메서드
- `spec/security-hardening/` — shared secret 인증 관련
