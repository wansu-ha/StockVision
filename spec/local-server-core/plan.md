# 로컬 서버 코어 구현 계획서 (local-server-core)

> 작성일: 2026-03-05 | Phase 3-A Unit 2 | 상태: 초안

---

## 0. 현황

### 기존 코드 상태

**로컬 서버 관련 기존 파일:**
- `backend/app/` — 클라우드 서버 FastAPI 앱 (로컬 서버 아님)
- 로컬 서버 전담 디렉토리 **미존재** → 신규 구축

**참고**:
- Phase 1-2에서는 클라우드 서버만 구현 (가상 거래, ML 예측)
- Phase 3에서 로컬 서버 신규 추가 (프로젝트 핵심 실행 환경)

### 아키텍처 확정 (2026-03-04)
- `docs/architecture.md` §4.4 — 로컬 서버의 역할 정의
- `docs/development-plan-v2.md` Unit 2 — 본 spec의 범위

### 의존성 관계

```
Unit 2 (로컬 서버 코어)
  ├── 입력: Unit 1 (BrokerAdapter)
  │   └─ KiwoomAdapter: 시세 수신, 주문 실행, 토큰 갱신
  │
  ├── 입력: Unit 3 (전략 엔진)
  │   └─ 규칙 평가 → 주문 신호 생성
  │
  └── 소비처: Unit 4 (API 서버), 프론트엔드
      └─ HTTP 폴링 (하트비트, 규칙 sync)
      └─ localhost HTTP/WS 제공
```

---

## 1. 구현 단계

### Step 1: 프로젝트 구조 + FastAPI 스켈레톤

**목표**: 로컬 서버의 디렉토리 구조 확립 및 기본 FastAPI 앱 구동

**파일**:
```
local_server/
├── main.py                     # 진입점 + uvicorn 스타트
├── requirements.txt            # 의존성
├── app/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py          # 설정 로더
│   │   └── security.py        # JWT, CORS
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py            # JWT 수신
│   │   ├── config.py          # 설정 API
│   │   ├── status.py          # 상태 API
│   │   ├── trading.py         # 전략 실행 API
│   │   ├── logs.py            # 로그 조회
│   │   └── ws.py              # WebSocket
│   └── models/                # (빈 디렉토리, 나중에 사용)
├── tests/
│   └── __init__.py
└── .gitignore
```

**구현 내용**:
1. FastAPI 앱 초기화 (127.0.0.1:4020 바인딩)
2. CORS 미들웨어 설정 (allowlist: localhost:5173, 127.0.0.1:4020)
3. 기본 health check 엔드포인트 (`GET /api/status` stub)
4. 로거 설정 (uvicorn 호환)
5. uvicorn 설정 (127.0.0.1만, 0.0.0.0 금지)

**검증**:
- [ ] `python main.py` → 5초 이내 127.0.0.1:4020 서빙 시작
- [ ] `GET http://127.0.0.1:4020/api/status` → 응답 확인
- [ ] 0.0.0.0 바인딩 확인 금지 (netstat)

---

### Step 2: 저장소 계층 (CredentialManager, RuleCache, ConfigManager, LogDB)

**목표**: 민감 데이터 및 설정 저장/로드 인프라 구축

**파일**:
```
local_server/app/storage/
├── __init__.py
├── credential.py        # keyring (API Key + Refresh Token)
├── rule_cache.py              # JSON 규칙 캐시
├── watchlist_cache.py         # 관심종목 캐시 (JSON)
├── stock_master_cache.py      # 종목 마스터 캐시 (JSON)
├── sync_queue.py              # 오프라인 변경 큐 (JSON)
├── config_manager.py          # config.json
└── log_db.py                  # SQLite logs.db
```

**구현 내용**:

1. **CredentialManager** (`credential.py`)
   - `save_api_key(app_key, app_secret)` → Credential Manager
   - `get_api_key()` → tuple[str, str] | None
   - `delete_api_key()`
   - `save_refresh_token(token)` → Credential Manager
   - `get_refresh_token()` → str | None
   - `delete_refresh_token()`

2. **RuleCache** (`rule_cache.py`)
   - `load()` → list[dict] | None (JSON 파일에서)
   - `save(rules: list[dict])` → JSON 파일 저장
   - 파일 경로: `~/.stockvision/strategies.json`
   - 인코딩: UTF-8

3. **ConfigManager** (`config_manager.py`)
   - 파일 경로: `~/.stockvision/config.json`
   - `get(key: str, default=None)` → Any
   - `set(key: str, value)` → None
   - `save()` → 파일에 반영
   - 기본 스키마: `local_server/config.py` DEFAULT_CONFIG 참조
     ```json
     {
       "server": { "host": "127.0.0.1", "port": 4020 },
       "broker": { "type": "kiwoom", "is_mock": true },
       "cloud": { "url": "", "heartbeat_interval": 30 },
       "cors": { "origins": ["http://localhost:5173"] }
     }
     ```

4. **WatchlistCache** (`watchlist_cache.py`)
   - `load()` → list[dict] | None
   - `save(watchlist: list[dict])` → JSON 파일 저장
   - 파일 경로: `~/.stockvision/watchlist.json`

5. **StockMasterCache** (`stock_master_cache.py`)
   - `load()` → list[dict] | None
   - `save(stocks: list[dict])` → JSON 파일 저장
   - `search(query: str)` → list[dict] (로컬 검색)
   - 파일 경로: `~/.stockvision/stock_master.json`
   - `stock_detail_cache.json`: 한번이라도 상세 조회한 종목 정보

6. **SyncQueue** (`sync_queue.py`)
   - `enqueue(action: dict)` → 큐에 추가
   - `dequeue()` → 하나 꺼냄
   - `peek_all()` → 전체 조회
   - `flush()` → 클라우드 연결 시 전부 전송
   - 파일 경로: `~/.stockvision/sync_queue.json`
   - action 형식: `{ "type": "rule_create|rule_update|watchlist_add|watchlist_delete", "data": {...}, "timestamp": "..." }`
   - last-write-wins 충돌 해결 (timestamp 기반)

7. **LogDB** (`log_db.py`)
   - SQLite 파일: `~/.stockvision/logs.db`
   - 모델 (SQLAlchemy):
     ```python
     class ExecutionLog:
         __tablename__ = "execution_logs"
         id: int                 # PK
         timestamp: datetime
         rule_id: int
         symbol: str
         side: str               # BUY | SELL
         qty: int
         price: int
         status: str             # FILLED | FAILED | REJECTED
         error_message: str
         raw_response: str       # JSON

     class ErrorLog:
         __tablename__ = "error_logs"
         id: int
         timestamp: datetime
         source: str             # kiwoom | engine | server
         severity: str           # INFO | WARNING | ERROR | CRITICAL
         message: str
         details: str
     ```
   - 메서드:
     - `log_execution(rule_id, symbol, side, qty, price, status, error_msg, raw_resp)` → None
     - `log_error(source, severity, message, details)` → None
     - `get_recent_logs(limit=100)` → list[ExecutionLog | ErrorLog]
     - DB 초기화 (자동 마이그레이션)

**검증**:
- [ ] API Key 저장 → Credential Manager에서 조회 가능
- [ ] Refresh Token 저장/로드 테스트
- [ ] strategies.json 생성/로드 테스트
- [ ] config.json 읽기/쓰기 테스트
- [ ] logs.db 테이블 생성 및 레코드 삽입 테스트
- [ ] watchlist.json 생성/로드 테스트
- [ ] stock_master.json 검색 테스트
- [ ] sync_queue.json enqueue/dequeue 테스트
- [ ] sync_queue flush 후 파일 비어있는지 확인

---

### Step 3: REST API 라우터 (auth, config, status, trading, logs)

**목표**: 프론트엔드 및 시스템에서 호출하는 HTTP 엔드포인트 구현

**파일**:
```
local_server/app/routers/
├── __init__.py
├── auth.py                    # POST /api/auth/token
├── config.py                  # GET/PATCH /api/config
├── status.py                  # GET /api/status
├── trading.py                 # POST /api/strategy/*
├── rules.py                   # POST /api/rules/sync
├── watchlist.py               # GET/POST/DELETE /api/watchlist
├── stocks.py                  # GET /api/stocks/search
└── logs.py                    # GET /api/logs
```

**구현 내용**:

1. **auth.py** — JWT 및 Refresh Token 수신
   ```
   POST /api/auth/token
     요청: { "access_token": "...", "refresh_token": "..." }
     응답: { "success": true, "data": {"message": "Token stored"} }
     동작:
       - Refresh Token → Credential Manager 저장
       - access_token → 메모리 저장 (전역 변수 또는 AppState)
   ```

2. **config.py** — 설정 관리
   ```
   GET /api/config
     응답: { "success": true, "data": config }

   PATCH /api/config
     요청: { "broker": { "is_mock": false } }
     응답: { "success": true, "data": updated_config }

   POST /api/config/kiwoom
     요청: { "app_key": "...", "app_secret": "..." }
     응답: { "success": true }
     동작: CredentialManager에 저장
   ```

3. **status.py** — 서버 + 키움 + 엔진 상태
   ```
   GET /api/status
     응답:
     {
       "success": true,
       "data": {
         "server": "running",
         "uptime_sec": 3600,
         "kiwoom": "connected",    # "connected" | "disconnected"
         "engine": "idle",         # "idle" | "running" | "error"
         "cloud_server": "ok",     # 하트비트 기반
         "last_heartbeat": "2026-03-05T10:00:00Z"
       }
     }
   ```

4. **trading.py** — 전략 엔진 제어
   ```
   POST /api/strategy/start
     응답: { "success": true, "data": {"message": "Engine started"} }

   POST /api/strategy/stop
     응답: { "success": true, "data": {"message": "Engine stopped"} }

   POST /api/strategy/kill
     요청: { "mode": "STOP_NEW" | "CANCEL_OPEN" }
     응답: { "success": true }
     동작: 신규 주문 차단 + TradingEnabled=OFF

   POST /api/strategy/unlock
     응답: { "success": true }
     동작: 손실 락 해제 (수동만 허용)
   ```

5. **rules.py** — 규칙 동기화 (프론트엔드 → 로컬)
   ```
   POST /api/rules/sync
     요청: { "rules": [ { "id": "...", "symbol": "005930", ... } ] }
     응답: { "success": true, "data": {"synced": 3} }
     동작: 전달받은 규칙을 rules.json 캐시에 덮어쓰기
           엔진 실행 중이면 즉시 규칙 리로드
   ```
   > 프론트엔드가 클라우드에 규칙 저장 후 localhost에 즉시 push.
   > 하트비트 sync와 별개로 사용자 즉시 반영용.

6. **watchlist.py** — 관심종목 (로컬 캐시 기반, 오프라인 가능)
   ```
   GET /api/watchlist
     응답: { "success": true, "data": [...] }
     동작: WatchlistCache에서 로드

   POST /api/watchlist
     요청: { "symbol": "005930", "name": "삼성전자" }
     응답: { "success": true }
     동작: WatchlistCache에 추가 + SyncQueue에 enqueue (클라우드 미연결 대비)

   DELETE /api/watchlist/{symbol}
     응답: { "success": true }
     동작: WatchlistCache에서 삭제 + SyncQueue에 enqueue
   ```

7. **stocks.py** — 종목 검색 (로컬 캐시 fallback)
   ```
   GET /api/stocks/search?q=삼성
     응답: { "success": true, "data": [...], "count": 5 }
     동작: 클라우드 primary → 실패 시 StockMasterCache.search() fallback
   ```

8. **logs.py** — 체결/오류 로그 조회
   ```
   GET /api/logs?limit=100&offset=0
     응답:
     {
       "success": true,
       "data": [
         {
           "id": 1,
           "timestamp": "2026-03-05T10:00:00Z",
           "type": "execution",
           "rule_id": 5,
           "symbol": "005930",
           "side": "BUY",
           "qty": 10,
           "price": 70000,
           "status": "FILLED"
         },
         ...
       ],
       "count": 100
     }
   ```

**검증**:
- [ ] POST /api/auth/token → Refresh Token Credential Manager 저장 확인
- [ ] GET /api/config → 현재 설정 반환
- [ ] PATCH /api/config → 설정 변경 + 저장 확인
- [ ] POST /api/config/kiwoom → API Key 저장 확인
- [ ] GET /api/status → 모든 필드 포함 확인
- [ ] GET /api/logs → 레코드 조회 확인

---

### Step 4: WebSocket 엔드포인트 (/ws)

**목표**: 프론트엔드에게 실시간 시세 + 체결 이벤트 브로드캐스트

**파일**: `local_server/app/routers/ws.py`

**구현 내용**:
```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    # 연결 관리
    manager = ConnectionManager()
    manager.connect(websocket)

    try:
        while True:
            # 시세 + 체결 이벤트 수신
            message = {
                "type": "quote",      # "quote" | "fill" | "status"
                "symbol": "005930",
                "price": 70000,
                "timestamp": datetime.now().isoformat()
            }
            await websocket.send_json(message)
    except Exception as e:
        manager.disconnect(websocket)
```

**메시지 형식**:
1. 시세 (BrokerAdapter에서 수신)
   ```json
   {
     "type": "quote",
     "symbol": "005930",
     "price": 70000,
     "volume": 1000,
     "timestamp": "2026-03-05T10:00:00Z"
   }
   ```

2. 체결 (엔진에서 발생)
   ```json
   {
     "type": "fill",
     "rule_id": 5,
     "symbol": "005930",
     "side": "BUY",
     "qty": 10,
     "price": 70000,
     "status": "FILLED",
     "timestamp": "2026-03-05T10:00:00Z"
   }
   ```

3. 상태 변경 (트레이/엔진)
   ```json
   {
     "type": "status",
     "kiwoom": "connected",
     "engine": "running",
     "cloud": "ok"
   }
   ```

**검증**:
- [ ] WS 연결 후 메시지 수신 확인
- [ ] 다중 클라이언트 동시 연결 가능 확인
- [ ] 연결 해제 시 manager 정리 확인

---

### Step 5: pystray 시스템 트레이

**목표**: Windows 시스템 트레이에 백그라운드 실행 아이콘 표시 + 기본 제어

**파일**: `local_server/app/tray.py`

**구현 내용**:

```python
import pystray
from PIL import Image, ImageDraw

class SystemTray:
    def __init__(self, status_provider):
        """status_provider: { ok, text, engine_running, today_fills, active_rules }"""
        self._status = status_provider
        self._icon: pystray.Icon = None

    def start(self):
        """메인 스레드에서 실행. FastAPI는 별도 스레드."""
        self._icon = pystray.Icon(
            "StockVision",
            icon=self._create_icon("green"),
            menu=self._create_menu(),
        )
        self._icon.run()

    def update_status(self, status: str):
        """status: "ok" | "warning" | "error"""
        color = {"ok": "green", "warning": "yellow", "error": "red"}[status]
        self._icon.icon = self._create_icon(color)

    def _create_icon(self, color: str) -> Image.Image:
        """색상 원형 아이콘 생성 (64x64)"""
        img = Image.new("RGB", (64, 64), "white")
        draw = ImageDraw.Draw(img)
        draw.ellipse([0, 0, 63, 63], fill=color)
        return img

    def _create_menu(self) -> pystray.Menu:
        """우클릭 메뉴"""
        return pystray.Menu(
            pystray.MenuItem("StockVision v1.0", None, enabled=False),
            pystray.MenuItem(
                lambda _: f"{'🟢' if self._status['ok'] else '🔴'} {self._status['text']}",
                None, enabled=False,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("대시보드 열기", self._open_dashboard),
            pystray.MenuItem(
                lambda _: f"{'엔진 중지' if self._status['engine_running'] else '엔진 시작'}",
                self._toggle_engine,
            ),
            pystray.MenuItem("⚠ 긴급 정지 (Kill Switch)", self._kill_switch),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                lambda _: f"오늘 체결: {self._status['today_fills']}건",
                None, enabled=False,
            ),
            pystray.MenuItem(
                lambda _: f"활성 규칙: {self._status['active_rules']}개",
                None, enabled=False,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("종료", self._quit),
        )

    def _open_dashboard(self, icon, item):
        """더블클릭/메뉴 → 브라우저에서 대시보드 열기"""
        import webbrowser
        webbrowser.open("http://localhost:5173")

    def _toggle_engine(self, icon, item):
        """엔진 시작/중지"""
        # 나중에 엔진 상태 관리와 연결
        pass

    def _kill_switch(self, icon, item):
        """긴급 정지"""
        # 나중에 TradingEnabled=OFF 설정
        pass

    def _quit(self, icon, item):
        """종료"""
        import sys
        sys.exit(0)
```

**스레드 구조**:
- **메인 스레드**: pystray 실행 (이벤트 루프 차단)
- **FastAPI 스레드**: uvicorn 실행 (별도 스레드에서 시작)

```python
# main.py
import threading

def run_uvicorn():
    uvicorn.run(app, host="127.0.0.1", port=8765)

if __name__ == "__main__":
    # FastAPI 스레드 시작
    api_thread = threading.Thread(target=run_uvicorn, daemon=False)
    api_thread.start()

    # 메인 스레드: 트레이 실행 (차단)
    tray = SystemTray(...)
    tray.start()
```

**검증**:
- [ ] 트레이 아이콘이 시스템 트레이에 표시됨
- [ ] 더블클릭 → 브라우저 열림
- [ ] 우클릭 → 메뉴 표시
- [ ] "종료" → 서버 정상 종료

---

### Step 6: 클라우드 클라이언트 (heartbeat, rule_syncer, context_fetcher)

**목표**: 로컬 서버가 클라우드 서버와 주기적으로 통신 (JWT 인증 + 버전 감지 + fetch/sync)

**파일**:
```
local_server/app/cloud_client/
├── __init__.py
├── client.py                  # HTTP 클라이언트 (JWT 관리)
├── heartbeat.py               # 하트비트 폴링
├── rule_syncer.py             # 규칙 fetch/upload
├── context_fetcher.py         # 컨텍스트 fetch
├── watchlist_syncer.py        # 관심종목 fetch/sync
└── stock_master_syncer.py     # 종목 마스터 fetch
```

**구현 내용**:

1. **client.py** — HTTP 클라이언트 래퍼
   ```python
   class CloudClient:
       def __init__(self, base_url: str, cred_store: CredentialManager):
           self._base_url = base_url        # "https://api.stockvision.app"
           self._cred_store = cred_store
           self._access_token = None        # 메모리 저장
           self._http = httpx.AsyncClient()

       async def set_access_token(self, token: str):
           """프론트에서 전달받은 JWT"""
           self._access_token = token

       async def _get_headers(self) -> dict:
           """Authorization 헤더 + JWT 자동 갱신"""
           if not self._access_token:
               # Refresh Token으로 자동 로그인
               refresh_token = self._cred_store.get_refresh_token()
               if not refresh_token:
                   raise AuthError("Refresh Token not found")

               resp = await self._refresh_token(refresh_token)
               self._access_token = resp["access_token"]
               self._cred_store.save_refresh_token(resp.get("refresh_token", refresh_token))

           return {"Authorization": f"Bearer {self._access_token}"}

       async def _refresh_token(self, refresh_token: str) -> dict:
           """POST /api/v1/auth/refresh"""
           resp = await self._http.post(
               f"{self._base_url}/api/v1/auth/refresh",
               json={"refresh_token": refresh_token},
           )
           resp.raise_for_status()
           return resp.json()["data"]

       async def post(self, endpoint: str, json: dict = None) -> dict:
           """JWT 자동 포함 POST"""
           headers = await self._get_headers()
           resp = await self._http.post(
               f"{self._base_url}{endpoint}",
               json=json,
               headers=headers,
           )
           resp.raise_for_status()
           return resp.json()["data"]

       async def get(self, endpoint: str) -> dict:
           """JWT 자동 포함 GET"""
           headers = await self._get_headers()
           resp = await self._http.get(
               f"{self._base_url}{endpoint}",
               headers=headers,
           )
           resp.raise_for_status()
           return resp.json()["data"]
   ```

2. **heartbeat.py** — 주기적 하트비트 + 버전 감지
   ```python
   class HeartbeatClient:
       def __init__(self, cloud_client: CloudClient, rule_cache: RuleCache,
                    context_cache: dict, rule_syncer, context_fetcher,
                    watchlist_syncer=None, stock_master_syncer=None):
           self._cloud = cloud_client
           self._rule_cache = rule_cache
           self._context_cache = context_cache
           self._rule_syncer = rule_syncer
           self._context_fetcher = context_fetcher
           self._watchlist_syncer = watchlist_syncer
           self._stock_master_syncer = stock_master_syncer
           self._last_rules_version = None
           self._last_context_version = None
           self._last_watchlist_version = None
           self._last_stock_master_version = None
           self._consecutive_failures = 0

       async def start(self, interval_sec=60):
           """주기적 하트비트 폴링"""
           while True:
               try:
                   resp = await self._cloud.post("/api/v1/heartbeat", {})

                   # 버전 감지 → fetch
                   if resp.get("rules_version") != self._last_rules_version:
                       await self._rule_syncer.fetch()
                       self._last_rules_version = resp["rules_version"]

                   if resp.get("context_version") != self._last_context_version:
                       await self._context_fetcher.fetch()
                       self._last_context_version = resp["context_version"]

                   if resp.get("watchlist_version") != self._last_watchlist_version:
                       await self._watchlist_syncer.fetch()
                       self._last_watchlist_version = resp["watchlist_version"]

                   if resp.get("stock_master_version") != self._last_stock_master_version:
                       await self._stock_master_syncer.fetch()
                       self._last_stock_master_version = resp["stock_master_version"]

                   # 최소/최신 버전 확인
                   if resp.get("min_version"):
                       # 버전 업데이트 강제
                       pass
                   if resp.get("latest_version"):
                       # 업데이트 권고
                       pass

                   self._consecutive_failures = 0

               except Exception as e:
                   self._consecutive_failures += 1
                   logger.error(f"Heartbeat failed: {e}")

                   # 트레이 상태 업데이트 (5분+ 🟡, 30분+ 🔴)
                   if self._consecutive_failures >= 30:  # 30 * 60s = 30분
                       # 트레이 🔴
                       pass
                   elif self._consecutive_failures >= 5:  # 5 * 60s = 5분
                       # 트레이 🟡
                       pass

               await asyncio.sleep(interval_sec)
   ```

3. **rule_syncer.py** — 규칙 fetch/sync
   ```python
   class RuleSyncer:
       def __init__(self, cloud_client: CloudClient, rule_cache: RuleCache):
           self._cloud = cloud_client
           self._cache = rule_cache

       async def fetch(self):
           """클라우드에서 규칙 fetch → 로컬 JSON 캐시"""
           resp = await self._cloud.get("/api/v1/rules")
           rules = resp["rules"]
           self._cache.save(rules)
           logger.info(f"Rules fetched: {len(rules)} rules")

       async def sync_local(self, rule_id: int, rule_data: dict):
           """로컬 규칙 변경 → 클라우드 sync"""
           await self._cloud.post(f"/api/v1/rules/{rule_id}", rule_data)
           logger.info(f"Rule {rule_id} synced to cloud")
   ```

4. **context_fetcher.py** — 컨텍스트 fetch
   ```python
   class ContextFetcher:
       def __init__(self, cloud_client: CloudClient):
           self._cloud = cloud_client
           self._context_cache = {}

       async def fetch(self):
           """AI 컨텍스트 fetch → 메모리 캐시"""
           resp = await self._cloud.get("/api/v1/context")
           self._context_cache = resp
           logger.info("Context fetched")

       def get(self) -> dict:
           """캐시된 컨텍스트 반환"""
           return self._context_cache
   ```

5. **watchlist_syncer.py** — 관심종목 fetch/sync
   ```python
   class WatchlistSyncer:
       def __init__(self, cloud_client: CloudClient, watchlist_cache: WatchlistCache,
                    sync_queue: SyncQueue):
           self._cloud = cloud_client
           self._cache = watchlist_cache
           self._sync_queue = sync_queue

       async def fetch(self):
           """클라우드에서 관심종목 fetch → 로컬 JSON 캐시"""
           resp = await self._cloud.get("/api/v1/watchlist")
           watchlist = resp["watchlist"]
           self._cache.save(watchlist)
           logger.info(f"Watchlist fetched: {len(watchlist)} items")

       async def flush_queue(self):
           """SyncQueue에 쌓인 watchlist 변경사항을 클라우드에 전송"""
           # sync_queue에서 watchlist 관련 action만 처리
           pass
   ```

6. **stock_master_syncer.py** — 종목 마스터 fetch
   ```python
   class StockMasterSyncer:
       def __init__(self, cloud_client: CloudClient, stock_master_cache: StockMasterCache):
           self._cloud = cloud_client
           self._cache = stock_master_cache

       async def fetch(self):
           """클라우드에서 종목 마스터 fetch → 로컬 JSON 캐시"""
           resp = await self._cloud.get("/api/v1/stocks/master")
           stocks = resp["stocks"]
           self._cache.save(stocks)
           logger.info(f"Stock master fetched: {len(stocks)} stocks")
   ```

**검증**:
- [ ] JWT 전달 → `_access_token` 메모리 저장 확인
- [ ] 하트비트 주기적 전송 확인
- [ ] 규칙 버전 변경 감지 → fetch 확인
- [ ] 컨텍스트 버전 변경 감지 → fetch 확인
- [ ] JWT 만료 → Refresh Token으로 자동 갱신 확인
- [ ] Refresh Token 만료 → 로그인 필요 상태로 전환 확인

---

### Step 7: 시작/종료 시퀀스 (자동 로그인, BrokerAdapter 주입)

**목표**: 프로세스 시작 시 초기화 순서 정의 및 종료 정리 로직

**파일**: `local_server/main.py` (수정), `local_server/app/startup.py` (신규)

**구현 내용**:

1. **시작 순서** (main.py)
   ```python
   async def lifespan(app: FastAPI):
       # 시작 (startup)
       logger.info("Initializing local server...")

       # 1. 저장소 초기화
       cred_store = CredentialManager()
       rule_cache = RuleCache()
       config_manager = ConfigManager()
       log_db = LogDB()

       # 2. config.json 로드
       config = config_manager.get_all()

       # 3. FastAPI 앱 설정 (의존성 주입)
       app.state.cred_store = cred_store
       app.state.rule_cache = rule_cache
       app.state.config_manager = config_manager
       app.state.log_db = log_db

       # 4. 클라우드 클라이언트 초기화
       cloud_client = CloudClient("https://api.stockvision.app", cred_store)
       app.state.cloud_client = cloud_client

       # 5. 자동 로그인 시도
       try:
           refresh_token = cred_store.get_refresh_token()
           if refresh_token:
               resp = await cloud_client._refresh_token(refresh_token)
               cloud_client._access_token = resp["access_token"]
               logger.info("Auto-login success")
           else:
               logger.warning("Refresh Token not found - manual login required")
       except Exception as e:
           logger.error(f"Auto-login failed: {e}")

       # 6. BrokerAdapter 초기화 (팩토리)
       broker_name = config.get("broker", "kiwoom")
       if broker_name == "kiwoom":
           # Unit 1에서 정의한 KiwoomAdapter 주입
           broker = KiwoomAdapter(cred_store, config)
           try:
               await broker.authenticate()
           except Exception as e:
               logger.warning(f"Broker auth failed: {e}")
       app.state.broker = broker

       # 7. 규칙 캐시 로드
       rules = rule_cache.load()
       if rules:
           logger.info(f"Loaded {len(rules)} rules from cache")
       app.state.rules = rules or []

       # 8. 하트비트 클라이언트 시작
       heartbeat = HeartbeatClient(cloud_client, rule_cache, {}, ...)
       asyncio.create_task(heartbeat.start(interval_sec=60))
       app.state.heartbeat = heartbeat

       # 9. 트레이 상태 초기화 (나중에 정의)
       app.state.tray_status = {"ok": True, "text": "정상 운영 중"}

       logger.info("Local server ready")

       yield  # 앱 실행 중

       # 종료 (shutdown)
       logger.info("Shutting down local server...")

       # 1. 엔진 중지
       # 2. WS 연결 닫기
       # 3. BrokerAdapter 정리
       await broker.disconnect()
       # 4. 미저장 로그 flush
       log_db.commit()
       # 5. uvicorn shutdown (자동)
       logger.info("Shutdown complete")

   @app.get("/api/status")
   async def status():
       return {
           "success": True,
           "data": {
               "server": "running",
               "uptime_sec": ...,
               "broker": app.state.broker.is_authenticated()
           }
       }
   ```

2. **종료 신호 처리**
   - Ctrl+C (KeyboardInterrupt) → 자동으로 lifespan shutdown 호출
   - 트레이 "종료" → 별도 처리 필요 (pystray 이벤트)

**검증**:
- [ ] 서버 시작 → Refresh Token 있으면 자동 로그인
- [ ] Refresh Token 없으면 "재로그인 필요" 로그
- [ ] config.json의 broker 필드 → KiwoomAdapter 주입 확인
- [ ] 규칙 캐시 로드 확인
- [ ] 하트비트 시작 확인
- [ ] Ctrl+C → 정상 종료 확인

---

### Step 8: CORS + 보안 미들웨어

**목표**: 동일 출처만 허용 (Origin 검증) + 보안 헤더

**파일**: `local_server/app/core/middleware.py` (신규)

**구현 내용**:

```python
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

# 환경별 allowlist
CORS_ALLOWLIST = {
    "dev": ["http://localhost:5173"],
    "prod": ["https://stockvision.app"],  # 프론트 호스팅 도메인
}

def add_cors_middleware(app: FastAPI, env: str = "dev"):
    """CORS 미들웨어 추가"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ALLOWLIST[env],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["*"],
    )

def add_security_middleware(app: FastAPI):
    """보안 헤더 추가"""
    class SecurityHeadersMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            response = await call_next(request)
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["X-XSS-Protection"] = "1; mode=block"
            return response

    app.add_middleware(SecurityHeadersMiddleware)
```

**검증**:
- [ ] 허용된 Origin (localhost:5173) → 정상 응답
- [ ] 비허용 Origin (예: evil.com) → CORS 거부
- [ ] WS도 Origin 검증 적용 확인

---

### Step 9: 절전 방지 (SetThreadExecutionState)

**목표**: PC 장시간 작동 시 자동 절전 금지

**파일**: `local_server/app/utils/power_management.py` (신규)

**구현 내용**:

```python
import ctypes
import threading
from enum import IntEnum

class ExecutionState(IntEnum):
    ES_CONTINUOUS = 0x80000000
    ES_SYSTEM_REQUIRED = 0x00000001

def prevent_sleep():
    """Windows SetThreadExecutionState 호출"""
    try:
        ctypes.windll.kernel32.SetThreadExecutionState(
            ExecutionState.ES_CONTINUOUS | ExecutionState.ES_SYSTEM_REQUIRED
        )
        logger.info("Power sleep prevention enabled")
    except AttributeError:
        logger.warning("SetThreadExecutionState not available (non-Windows)")

def allow_sleep():
    """절전 허용"""
    try:
        ctypes.windll.kernel32.SetThreadExecutionState(ExecutionState.ES_CONTINUOUS)
        logger.info("Power sleep prevention disabled")
    except AttributeError:
        pass
```

**연결**:
```python
# main.py lifespan
async def lifespan(app: FastAPI):
    prevent_sleep()
    # ...
    yield
    # ...
    allow_sleep()
```

**검증**:
- [ ] 서버 실행 중 PC 절전 안 됨 (수동 테스트)

---

### Step 10: PyInstaller 빌드 + 레지스트리 자동시작

**목표**: 단일 .exe 생성 및 Windows 시작프로그램 등록

**파일**:
```
local_server/
├── build_exe.spec                 # PyInstaller 설정
└── scripts/
    ├── build.py                   # PyInstaller 빌드
    └── register_autostart.py       # 레지스트리 등록
```

**구현 내용**:

1. **build_exe.spec** (PyInstaller)
   ```spec
   # -*- mode: python ; coding: utf-8 -*-
   a = Analysis(
       ['main.py'],
       pathex=[],
       binaries=[],
       datas=[
           ('app', 'app'),
           ('config.json.example', '.'),
       ],
       hiddenimports=[
           'pystray',
           'PIL',
           'httpx',
           'keyring',
           'aiosqlite',
           'fastapi',
           'uvicorn',
       ],
       hookspath=[],
       hooksconfig={},
       runtime_hooks=[],
       excludedimports=[],
       noarchive=False,
   )
   pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
   exe = EXE(
       pyz,
       a.scripts,
       [],
       exclude_binaries=True,
       name='stockvision',
       debug=False,
       bootloader_ignore_signals=False,
       strip=False,
       upx=True,
       console=False,  # GUI 모드 (콘솔 숨김)
       icon='icon.ico',
   )
   coll = COLLECT(
       exe,
       a.binaries,
       a.zipfiles,
       a.datas,
       strip=False,
       upx=True,
       upx_exclude=[],
       name='stockvision',
   )
   ```

2. **build.py** — 빌드 스크립트
   ```python
   import subprocess
   import os

   def build_exe():
       os.chdir("local_server")
       result = subprocess.run([
           "pyinstaller",
           "--onefile",
           "--windowed",
           "--icon=icon.ico",
           "--hidden-import=pystray",
           "--hidden-import=PIL",
           "--name=stockvision",
           "main.py"
       ], check=True)
       print("Build complete: dist/stockvision.exe")
   ```

3. **register_autostart.py** — 레지스트리 등록
   ```python
   import winreg
   import os

   def register_autostart():
       """HKCU\Software\Microsoft\Windows\CurrentVersion\Run에 등록"""
       exe_path = os.path.abspath("dist/stockvision.exe")

       key = winreg.OpenKey(
           winreg.HKEY_CURRENT_USER,
           r"Software\Microsoft\Windows\CurrentVersion\Run",
           0,
           winreg.KEY_SET_VALUE,
       )
       winreg.SetValueEx(key, "StockVision", 0, winreg.REG_SZ, exe_path)
       winreg.CloseKey(key)
       print(f"Registered autostart: {exe_path}")

   def unregister_autostart():
       """레지스트리에서 제거"""
       key = winreg.OpenKey(
           winreg.HKEY_CURRENT_USER,
           r"Software\Microsoft\Windows\CurrentVersion\Run",
           0,
           winreg.KEY_SET_VALUE,
       )
       try:
           winreg.DeleteValue(key, "StockVision")
       except WindowsError:
           pass
       winreg.CloseKey(key)
   ```

**requirements.txt** (필수 패키지):
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
pystray==0.19.5
Pillow==10.1.0
httpx==0.25.2
keyring==24.3.0
aiosqlite==0.19.0
sqlalchemy==2.0.23
PyInstaller==6.2
pywin32==305
```

**검증**:
- [ ] `pyinstaller build_exe.spec` → stockvision.exe 생성 확인
- [ ] .exe 실행 → 정상 작동 (127.0.0.1:4020 서빙)
- [ ] .exe 파일 크기 < 100MB
- [ ] 레지스트리 등록 후 PC 재부팅 → 자동 실행 확인

---

## 2. 의존성 명세

### 내부 의존성

| 모듈 | 역할 | 상태 |
|------|------|------|
| Unit 1 (BrokerAdapter) | 시세 수신, 주문 실행 | 별도 구현 (spec/kiwoom-rest) |
| Unit 3 (전략 엔진) | 규칙 평가 → 주문 신호 | 별도 구현 (spec/strategy-engine) |
| Unit 4 (클라우드 API) | 인증, 규칙 sync | 기존 backend 확장 |

**로컬 서버의 위치**:
```
backend/                 ← 클라우드 서버 (기존)
local_server/            ← 로컬 서버 (신규)
  ├── main.py
  ├── app/
  │   ├── routers/       # auth, config, status, trading, rules, watchlist, stocks, logs, ws
  │   ├── storage/       # cred_store, rule_cache, watchlist_cache, stock_master_cache, sync_queue, config_manager, log_db
  │   ├── cloud_client/  # client, heartbeat, rule_syncer, context_fetcher, watchlist_syncer, stock_master_syncer
  │   ├── tray.py
  │   └── core/
  ├── requirements.txt
  └── tests/
```

### 외부 의존성

| 패키지 | 용도 | 버전 |
|--------|------|------|
| fastapi | 웹 프레임워크 | 0.104.1 |
| uvicorn | ASGI 서버 | 0.24.0 |
| httpx | 비동기 HTTP 클라이언트 | 0.25.2 |
| keyring | Windows Credential Manager | 24.3.0 |
| aiosqlite | 비동기 SQLite | 0.19.0 |
| sqlalchemy | ORM | 2.0.23 |
| pystray | 시스템 트레이 | 0.19.5 |
| Pillow | 이미지 처리 (아이콘) | 10.1.0 |
| pywin32 | Windows API (SetThreadExecutionState) | 305 |
| PyInstaller | .exe 번들 | 6.2 |

---

## 3. 파일 구조 최종

```
local_server/
├── main.py                                # 진입점
├── requirements.txt                       # 의존성
├── config.json.example                    # 설정 예시
├── icon.ico                               # 트레이 아이콘
├── build_exe.spec                         # PyInstaller 설정
├── app/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py                      # 설정 로더
│   │   ├── security.py                    # JWT, CORS
│   │   └── middleware.py                  # CORS, 보안 헤더
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py                        # POST /api/auth/token
│   │   ├── config.py                      # GET/PATCH /api/config
│   │   ├── status.py                      # GET /api/status
│   │   ├── trading.py                     # POST /api/strategy/*
│   │   ├── rules.py                       # POST /api/rules/sync
│   │   ├── watchlist.py                   # GET/POST/DELETE /api/watchlist
│   │   ├── stocks.py                      # GET /api/stocks/search
│   │   ├── logs.py                        # GET /api/logs
│   │   └── ws.py                          # WebSocket /ws
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── credential.py            # keyring
│   │   ├── rule_cache.py                  # JSON
│   │   ├── watchlist_cache.py             # 관심종목 JSON 캐시
│   │   ├── stock_master_cache.py          # 종목 마스터 JSON 캐시
│   │   ├── sync_queue.py                  # 오프라인 변경 큐
│   │   ├── config_manager.py              # config.json
│   │   └── log_db.py                      # SQLite
│   ├── cloud_client/
│   │   ├── __init__.py
│   │   ├── client.py                      # HTTP + JWT
│   │   ├── heartbeat.py                   # 폴링
│   │   ├── rule_syncer.py                 # fetch/sync
│   │   ├── context_fetcher.py             # fetch
│   │   ├── watchlist_syncer.py            # 관심종목 fetch/sync
│   │   └── stock_master_syncer.py         # 종목 마스터 fetch
│   ├── models/
│   │   └── __init__.py
│   ├── tray.py                            # pystray
│   └── utils/
│       ├── __init__.py
│       └── power_management.py            # SetThreadExecutionState
├── scripts/
│   ├── build.py                           # PyInstaller 빌드
│   └── register_autostart.py              # 레지스트리 등록
└── tests/
    ├── __init__.py
    ├── test_storage.py                    # 저장소 테스트
    ├── test_routers.py                    # API 테스트
    ├── test_cloud_client.py               # 클라우드 통신 테스트
    └── test_integration.py                # 통합 테스트
```

---

## 4. 미결 사항 처리

| 항목 | 상태 | 처리 방안 |
|------|------|----------|
| FastAPI ↔ pystray 이벤트 루프 | 미정 | Step 7에서 스레드 분리로 해결 |
| .exe 시 Pillow 이미지 포함 | 미정 | PyInstaller의 datas로 icon.ico 포함 |
| 레지스트리 경로 | 확정 | `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` |
| logs.db 정리 정책 | 미정 | 나중에 결정 (예: 30일 이상 삭제) |
| config.json 스키마 버전 | 미정 | v1부터 시작, 마이그레이션 나중에 추가 |
| 엔진 객체 주입 | 미정 | Unit 3 구현 시 정의 |
| BrokerAdapter 모의 | 미정 | Unit 1에서 정의된 인터페이스 사용 |

---

## 5. 커밋 계획

각 Step 완료 후 커밋:

| Step | 커밋 메시지 |
|------|-----------|
| 1 | `feat: Step 1 — 로컬 서버 구조 + FastAPI 스켈레톤` |
| 2 | `feat: Step 2 — 저장소 계층 (CredentialManager, RuleCache, ConfigManager, LogDB)` |
| 3 | `feat: Step 3 — REST API 라우터 (auth, config, status, trading, logs)` |
| 4 | `feat: Step 4 — WebSocket 엔드포인트 (/ws)` |
| 5 | `feat: Step 5 — pystray 시스템 트레이` |
| 6 | `feat: Step 6 — 클라우드 클라이언트 (heartbeat, rule_syncer, context_fetcher)` |
| 7 | `feat: Step 7 — 시작/종료 시퀀스 (자동 로그인, BrokerAdapter 주입)` |
| 8 | `feat: Step 8 — CORS + 보안 미들웨어` |
| 9 | `feat: Step 9 — 절전 방지 (SetThreadExecutionState)` |
| 10 | `feat: Step 10 — PyInstaller 빌드 + 레지스트리 자동시작` |

---

## 참고

- 아키텍처: `docs/architecture.md` §4.4 (로컬 서버)
- 명세: `spec/local-server-core/spec.md`
- 개발 계획: `docs/development-plan-v2.md` Unit 2
- 기존 계획: `spec/data-source/plan.md` (포맷 참조)

---

**작성**: 2026-03-05
