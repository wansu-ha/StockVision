# 배포 전 내실 강화 구현 계획 (pre-deploy-hardening)

> 작성일: 2026-03-09 | 상태: 구현 완료

---

## 1. 아키텍처

```
┌────────────────┐         ┌────────────────┐
│  local_server  │──HTTP──▶│  cloud_server  │
│  :4020         │         │  :4010         │
│                │         │                │
│ cloud/client   │         │ api/heartbeat  │  ← C1: URL+payload 정합
│ cloud/heartbeat│         │ api/rules      │
│ tray/tray_app  │         │ core/config    │  ← C4: CORS, W5: 키 검증
│                │         │ core/init_db   │  ← C3: Alembic
│                │         │ Dockerfile     │  ← W1: 신규
└────────────────┘         └────────────────┘
```

데이터 흐름 (하트비트):
1. `heartbeat.py` → `_build_heartbeat_payload()` — payload 생성
2. `client.py` → `send_heartbeat()` — POST 전송
3. `cloud_server/api/heartbeat.py` — `HeartbeatBody` 검증 → 저장 → 응답

---

## 2. 구현 순서

의존성 없는 것부터, 의존성 있는 것 나중으로.

### Step 1: C4 — CORS 환경변수화

**변경 파일**: `cloud_server/core/config.py`

**변경 내용**:
```python
# before
CORS_ORIGINS: list[str] = [
    "http://localhost:5173",
]

# after
CORS_ORIGINS: list[str] = [
    origin.strip()
    for origin in os.environ.get(
        "CORS_ORIGINS", "http://localhost:5173"
    ).split(",")
    if origin.strip()
]
```

**verify**: 클라우드 서버 테스트 38개 통과 (`pytest cloud_server/`)

---

### Step 2: W5 — CONFIG_ENCRYPTION_KEY 시작 시 검증

**변경 파일**: `cloud_server/core/config.py`

**변경 내용**: `validate_settings()`에 CONFIG_ENCRYPTION_KEY 경고 추가
```python
def validate_settings() -> None:
    if not settings.SECRET_KEY:
        raise RuntimeError("SECRET_KEY 환경 변수가 설정되지 않았습니다.")
    if not settings.CONFIG_ENCRYPTION_KEY:
        import logging
        logging.getLogger(__name__).warning(
            "CONFIG_ENCRYPTION_KEY 미설정 — 암호화 기능 사용 시 오류 발생"
        )
```

- 서버 시작은 차단하지 않음 (개발 환경에서 불필요할 수 있음)
- 실제 암호화 호출 시 `_get_key()`에서 RuntimeError — 이건 기존 동작 유지

**verify**: 서버 시작 시 WARNING 로그 출력 확인 + 테스트 38개 통과

---

### Step 3: C1 — API 경로 + payload 정합성

**변경 파일**:
| 파일 | 변경 |
|------|------|
| `local_server/cloud/client.py` | URL 경로 수정 |
| `local_server/cloud/heartbeat.py` | payload 필드 서버 스키마 대응 |
| `local_server/config.py` | UUID 자동 생성/저장 |
| `local_server/tests/test_cloud_client.py` | 계약 테스트 갱신 |

#### 3-1. client.py URL 수정

```python
# send_heartbeat(): "/api/local/heartbeat" → "/api/v1/heartbeat"
# fetch_rules(): "/api/rules" → "/api/v1/rules"
```

#### 3-2. heartbeat.py payload 수정

서버 `HeartbeatBody` 스키마에 맞춤:

```python
def _build_heartbeat_payload() -> dict[str, Any]:
    from datetime import datetime, timezone
    import platform
    cfg = get_config()

    # UUID: 최초 생성 후 config에 저장
    uuid = cfg.get("server.uuid")
    if not uuid:
        from uuid import uuid4
        uuid = str(uuid4())
        cfg.set("server.uuid", uuid)
        cfg.save()

    return {
        "uuid": uuid,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "engine_running": _engine_running,
        "version": cfg.get("server.version", "1.0.0"),
        "os": platform.system(),
    }
```

삭제 필드: `status`, `strategy_engine` (서버에 없음)

#### 3-3. 테스트 갱신

- `TestCloudClientSendHeartbeat`: URL `/api/v1/heartbeat` 검증
- `TestCloudClientFetchRules`: URL `/api/v1/rules` 검증
- 하트비트 payload 계약 테스트: 새 필드(`uuid`, `timestamp`, `engine_running`) 검증
- `_build_heartbeat_payload()` 단위 테스트 추가

**verify**: `pytest local_server/tests/` 전체 통과 + `pytest cloud_server/tests/` 통과

---

### Step 4: W3 — 트레이 엔진 토글 → 실제 API 호출

**변경 파일**: `local_server/tray/tray_app.py`

**현재 문제**: `_on_toggle_engine()`이 `set_engine_running()` 플래그만 설정. 실제 엔진 시작/중지 안 됨.

**해결 방향**:
- pystray 콜백은 동기(일반 스레드) → `httpx` 동기 클라이언트 사용
- 로컬 서버 포트 + local_secret 필요 → 모듈 수준 변수로 주입

```python
# 모듈 수준 (main.py lifespan에서 설정)
_local_secret: str | None = None
_local_port: int = 4020

def set_tray_auth(port: int, secret: str) -> None:
    """main.py lifespan에서 호출. 트레이 → API 호출에 필요한 인증 정보 설정."""
    global _local_secret, _local_port
    _local_secret, _local_port = secret, port

def _on_toggle_engine(icon: Any, item: Any) -> None:
    from local_server.cloud.heartbeat import _engine_running
    action = "stop" if _engine_running else "start"
    threading.Thread(
        target=_call_engine_api,
        args=(action,),
        daemon=True,
    ).start()

def _call_engine_api(action: str) -> None:
    import httpx
    url = f"http://127.0.0.1:{_local_port}/api/strategy/{action}"
    headers = {"X-Local-Secret": _local_secret or ""}
    try:
        resp = httpx.post(url, headers=headers, timeout=10)
        resp.raise_for_status()
        logger.info("트레이 엔진 %s 성공", action)
    except Exception as e:
        logger.error("트레이 엔진 %s 실패: %s", action, e)
        _send_toast("엔진 제어 실패", str(e))
```

**추가 변경**: `local_server/main.py` — lifespan에서 `set_tray_auth(port, secret)` 호출

**verify**: 수동 확인 (트레이 → 엔진 시작/중지 → 로그 확인)

---

### Step 5: C3 — Alembic 마이그레이션 초기화

**변경 파일**:
| 파일 | 변경 |
|------|------|
| `alembic.ini` | 신규 — Alembic 설정 |
| `cloud_server/alembic/env.py` | 신규 — 모델 import + DB URL |
| `cloud_server/alembic/versions/001_initial.py` | 신규 — 초기 마이그레이션 |

**구현 내용**:

```bash
# 1. Alembic 초기화
cd cloud_server
alembic init alembic

# 2. alembic.ini 수정
#    sqlalchemy.url = sqlite:///./cloud_server.db  (기본)
#    → env.py에서 settings.DATABASE_URL로 오버라이드

# 3. env.py 수정
#    - cloud_server.core.database.Base.metadata를 target_metadata로 설정
#    - 모든 모델 import (init_db.py와 동일)
#    - settings.DATABASE_URL로 URL 오버라이드

# 4. 초기 마이그레이션 생성
alembic revision --autogenerate -m "initial schema"

# 5. init_db()는 유지 (개발/테스트용)
```

**verify**:
- `alembic upgrade head` → 빈 DB에 전체 13 모델 테이블 생성
- `alembic downgrade base` → 전체 삭제
- `alembic revision --autogenerate` → "No changes" 출력 (현재 스키마와 동일)

---

### Step 6: W1 — Dockerfile + docker-compose

**변경 파일**:
| 파일 | 변경 |
|------|------|
| `cloud_server/Dockerfile` | 신규 |
| `docker-compose.yml` | cloud_server 서비스 추가 |

**Dockerfile**:
```dockerfile
FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 4010

CMD ["uvicorn", "cloud_server.main:app", "--host", "0.0.0.0", "--port", "4010"]
```

**docker-compose.yml 추가**:
```yaml
services:
  cloud_server:
    build:
      context: .
      dockerfile: cloud_server/Dockerfile
    ports:
      - "4010:4010"
    environment:
      - DATABASE_URL=postgresql://stockvision_user:stockvision_pass@postgres:5432/stockvision
      - SECRET_KEY=${SECRET_KEY}
      - CORS_ORIGINS=${CORS_ORIGINS:-http://localhost:5173}
    depends_on:
      - postgres
      - redis
    restart: unless-stopped
```

**주의**: Dockerfile의 `COPY . .`은 프로젝트 루트에서 빌드해야 하므로 context는 `.` (루트), dockerfile 경로를 지정.

**verify**: `docker-compose config` 문법 검증 (Docker 환경 없으면 여기까지)

---

## 3. 수정 파일 목록 (전체)

| 파일 | Step | 변경 |
|------|------|------|
| `cloud_server/core/config.py` | 1, 2 | CORS 환경변수 + CONFIG_ENCRYPTION_KEY 경고 |
| `local_server/cloud/client.py` | 3 | 하트비트/규칙 URL 수정 |
| `local_server/cloud/heartbeat.py` | 3 | payload 필드 서버 스키마 대응 |
| `local_server/tests/test_cloud_client.py` | 3 | 계약 테스트 URL/payload 갱신 + payload 계약 2개 추가 |
| `local_server/tray/tray_app.py` | 4 | 엔진 토글 → API 호출 |
| `local_server/main.py` | 4 | `set_tray_auth()` 호출 추가 |
| `alembic.ini` | 5 | 신규 — Alembic 설정 |
| `cloud_server/alembic/env.py` | 5 | 신규 — 모델 메타데이터 연결 |
| `cloud_server/alembic/script.py.mako` | 5 | 신규 — 마이그레이션 템플릿 |
| `cloud_server/alembic/versions/__init__.py` | 5 | 신규 — 빈 패키지 |
| `cloud_server/Dockerfile` | 6 | 신규 |
| `docker-compose.yml` | 6 | cloud_server 서비스 추가 |

---

## 4. 검증 체크리스트

- [x] Step 1: `CORS_ORIGINS` 환경변수 파싱, 미설정 시 기본값 유지
- [x] Step 2: 서버 시작 시 CONFIG_ENCRYPTION_KEY 미설정 WARNING 로그
- [x] Step 3: `send_heartbeat()` → `/api/v1/heartbeat` 200 응답
- [x] Step 3: `fetch_rules()` → `/api/v1/rules` 200 응답
- [x] Step 3: payload에 `uuid`, `timestamp`, `engine_running` 포함
- [x] Step 4: 트레이 "엔진 시작" → `/api/strategy/start` 호출
- [x] Step 4: 트레이 "엔진 중지" → `/api/strategy/stop` 호출
- [ ] Step 5: `alembic upgrade head` → 전체 테이블 생성 (초기 마이그레이션 미생성 — 배포 시 실행)
- [x] Step 6: `cloud_server/Dockerfile` 존재
- [x] Step 6: `docker-compose.yml`에 cloud_server 서비스 포함
- [x] 전체: `pytest cloud_server/` 38 passed
- [x] 전체: `pytest local_server/` 109 passed (계약 테스트 2개 추가)

---

## 5. 참고

- 서버 하트비트 스키마: `cloud_server/api/heartbeat.py` — `HeartbeatBody`
- 클라이언트 HTTP: `local_server/cloud/client.py`
- 트레이 인증: `local_server/core/local_auth.py` — `X-Local-Secret` 헤더
- DB 모델 13개: `cloud_server/models/` (user, rule, market, fundamental, template, heartbeat)
- 기존 init_db: `cloud_server/core/init_db.py` — `Base.metadata.create_all()`
