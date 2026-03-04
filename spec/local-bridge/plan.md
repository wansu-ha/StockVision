# 로컬 서버 구현 계획서 (local-bridge)

> 작성일: 2026-03-04 | 상태: 초안 | 범위: Phase 3 로컬 서버 전체

---

## 0. 전제 조건

- Python 3.13 + FastAPI (uvicorn) — Windows 전용
- `spec/auth/plan.md`: auth 클라이언트(token.dat, JWT) 먼저 구현
- `spec/kiwoom-integration/plan.md`: COM API 래퍼
- PyInstaller로 단일 .exe 번들링

---

## 1. 구현 단계

### Step 1 — 프로젝트 스캐폴딩

```
local_server/
  main.py               # FastAPI app + uvicorn 진입점
  routers/
    ws.py               # WebSocket /ws
    config.py           # GET/PATCH /api/config, POST /api/config/unlock
    kiwoom.py           # GET /api/kiwoom/status, GET /api/account
    trading.py          # POST /api/strategy/start|stop
    health.py           # GET /api/health
  engine/
    scheduler.py        # 1분 주기 규칙 평가 루프
    evaluator.py        # 조건 평가 로직
    signal.py           # 신호 생성 → kiwoom.order 호출
  kiwoom/
    com_client.py       # COM 객체 래퍼 (pywin32)
    session.py          # connect/disconnect/status
    order.py            # send_order()
    account.py          # 잔고/포지션 조회
  storage/
    config_manager.py   # config blob 동기화 (GET/PUT /api/v1/config)
    log_db.py           # logs.db SQLite
  cloud/
    auth_client.py      # token.dat, refresh_jwt, get_config
    context.py          # 컨텍스트 fetch + 캐시
    heartbeat.py        # 5분 주기 UUID 전송
```

**검증:**
- [ ] `python main.py` 실행 → localhost:8765 응답
- [ ] `GET /api/health` → `{ "status": "ok" }` 반환

### Step 2 — WebSocket 서버

**목표**: React ↔ 로컬 서버 양방향 실시간 통신

파일: `routers/ws.py`

```python
# 수신 메시지 (React → 로컬)
{ "type": "strategy_toggle", "data": { "rule_id": 1, "is_active": true } }
{ "type": "config_update",   "data": { "kiwoom.mode": "demo" } }
{ "type": "jwt_unlock",      "data": { "jwt": "eyJ..." } }

# 송신 메시지 (로컬 → React)
{ "type": "execution_result", "data": { ... } }
{ "type": "kiwoom_status",    "data": { "connected": true, "mode": "demo" } }
{ "type": "alert",            "data": { "level": "warn", "message": "..." } }
```

**검증:**
- [ ] React WS 연결 → 상태 업데이트 수신
- [ ] 연결 끊김 → React 자동 재연결 (백오프)

### Step 3 — 설정 동기화

**목표**: React ↔ 로컬 서버 ↔ 클라우드 설정 동기화

파일: `storage/config_manager.py`, `routers/config.py`

```
React → PATCH /api/config (설정 변경)
    → 500ms debounce
    → PUT /api/v1/config (클라우드 업로드, JWT 필요)
    → 로컬 메모리 업데이트

POST /api/config/unlock { jwt }
    → AuthClient.get_config(jwt)
    → 설정 로컬 메모리 로드
    → WS로 React에 "config_loaded" 이벤트 전송
```

**검증:**
- [ ] 설정 변경 → 500ms debounce 후 클라우드 업로드
- [ ] 재시작 후 token.dat 기반 자동 설정 로드

### Step 4 — 자동 시작 흐름

**목표**: 부팅 시 사용자 개입 없이 전략 엔진 시작

파일: `main.py` (startup 이벤트)

```python
@app.on_event("startup")
async def startup():
    try:
        jwt = auth_client.refresh_jwt()        # token.dat → 새 JWT
        config = auth_client.get_config(jwt)   # 설정 로드
        config_manager.load(config)            # 전략 메모리 로드
        scheduler.start()                      # 규칙 평가 루프 시작
    except NeedsLoginError:
        tray.notify("StockVision", "재로그인이 필요합니다")
```

**검증:**
- [ ] token.dat 있음 → 자동 시작 (입력 없음)
- [ ] token.dat 없음 → 트레이 알림

### Step 5 — 시스템 트레이 + exe 패키징

파일: `tray.py`, `build.spec` (PyInstaller)

```
시스템 트레이 아이콘:
  - 좌클릭: 브라우저 열기 (stockvision.app)
  - 우클릭 메뉴: 상태 보기 | 재시작 | 종료
```

**검증:**
- [ ] PyInstaller 빌드 → 단일 .exe 생성
- [ ] .exe 실행 → 트레이 아이콘 표시 + 서버 시작

---

## 2. 파일 목록 (신규 생성)

`local_server/` 디렉토리 전체 신규 생성.

---

## 3. 의존 패키지

```
fastapi, uvicorn, websockets
httpx                    # 클라우드 API 클라이언트
pywin32                  # COM API (Windows 전용)
schedule                 # 1분 주기 스케줄러
sqlite3                  # 내장
pystray, Pillow          # 시스템 트레이
pyinstaller              # .exe 패키징
argon2-cffi, cryptography, python-jose  # auth (auth_client)
```

---

## 4. 커밋 계획

| 커밋 | 메시지 |
|------|--------|
| 1 | `feat: Step 1 — 로컬 서버 스캐폴딩 + health API` |
| 2 | `feat: Step 2 — WebSocket 서버` |
| 3 | `feat: Step 3 — 설정 동기화 (config_manager + unlock)` |
| 4 | `feat: Step 4 — 자동 시작 흐름 (token.dat + startup)` |
| 5 | `feat: Step 5 — 시스템 트레이 + PyInstaller 빌드` |
