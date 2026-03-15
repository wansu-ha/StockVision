# 로컬 서버 코어 명세서 (local-server-core)

> 작성일: 2026-03-04 | 상태: 구현 완료 | Unit 2 (Phase 3-A)
>
> **이전 spec**: `spec/local-bridge/` → 본 spec으로 대체.
> 로컬 서버의 **기반 구조**(서버, 트레이, 저장소, 패키징)를 정의.
> 브로커 API(Unit 1, BrokerAdapter), 전략 엔진(Unit 3)은 별도 spec.

---

## 1. 목표

사용자 PC에서 실행되는 FastAPI 기반 로컬 서버의 기반 구조를 구현한다.
**프로젝트의 핵심 실행 환경**으로, 키움 연동·전략 엔진·로그 저장의 토대.

**해결하는 문제:**
- 로컬 서버 프로세스 관리 (시작, 종료, 백그라운드)
- 시스템 트레이 아이콘으로 UX 제공 (상태 확인 + 최소 제어)
- 민감 데이터 안전 저장 (API Key, Refresh Token → Credential Manager)
- BrokerAdapter 주입 (config.json의 `broker` 필드로 구현체 선택)
- 클라우드 서버 HTTP 폴링 (하트비트 → 버전 감지 → fetch)
- PC 재부팅 시 자동 로그인 (Refresh Token)
- 단일 .exe 배포

---

## 2. 요구사항

### 2.1 기능적 요구사항

| ID | 요구사항 | 우선순위 |
|----|---------|---------|
| F1 | FastAPI 서버를 localhost:4020에서 실행한다 | P0 |
| F2 | 시스템 트레이 아이콘으로 백그라운드 실행한다 | P0 |
| F3 | 트레이 우클릭 메뉴: 상태 표시, 대시보드 열기, 종료 | P0 |
| F4 | 트레이 아이콘 색상으로 전체 상태를 표시한다 (🟢🟡🔴) | P0 |
| F5 | API Key/Secret을 Windows Credential Manager에 저장한다 | P0 |
| F6 | 전략 규칙을 평문 JSON 파일로 캐시한다 | P0 |
| F7 | 설정을 config.json으로 관리한다 | P0 |
| F8 | 체결/오류 로그를 SQLite(logs.db)에 저장한다 | P0 |
| F9 | 클라우드 서버와 HTTP 폴링으로 통신한다 (JWT 인증, 하트비트 → 버전 감지 → fetch) | P0 |
| F10 | Refresh Token을 Credential Manager에 저장하여 자동 로그인한다 | P0 |
| F11 | PyInstaller로 단일 .exe 번들을 생성한다 | P1 |
| F12 | 레지스트리 Run 키로 Windows 자동 시작을 지원한다 | P1 |
| F13 | 장 시간 절전 방지 (SetThreadExecutionState) | P0 |
| F14 | Kill Switch 트레이 메뉴 항목 (긴급 정지 → 엔진 즉시 중지) | P0 |
| F15 | 하트비트 실패 임계값별 트레이 상태 전환 (🟢→🟡→🔴) | P1 |
| F15b | 체결 시 Windows 토스트 알림 (브라우저 없어도 알림) | P0 |
| F16 | localhost API CORS allowlist (Origin 검증 겸용, 허용 출처만 응답) | P1 |
| F17 | 하트비트 응답에서 latest_version + min_version 감지 → 업데이트 알림 | P2 |
| F18 | 127.0.0.1만 바인딩 (0.0.0.0 금지) | P0 |
| F19 | 관심종목을 JSON 파일로 캐시한다 (watchlist.json) | P0 |
| F20 | 종목 메타데이터를 JSON 파일로 캐시한다 (stock_master.json, ~150KB) | P0 |
| F21 | 조회한 종목 상세를 온디맨드 캐시한다 (stock_detail_cache.json) | P1 |
| F22 | 클라우드 미연결 시 변경사항을 sync 큐에 저장한다 (sync_queue.json) | P0 |

### 2.2 비기능적 요구사항

| 항목 | 목표 |
|------|------|
| 서버 시작 시간 | < 5초 (.exe 실행 → HTTP 서빙) |
| 메모리 사용 | < 200MB (전체 로컬 서버) |
| 가동률 | > 99% (장 시간 기준) |
| .exe 파일 크기 | < 100MB |
| 서버 바인딩 | 127.0.0.1만 (0.0.0.0 금지) |
| Access Token 저장 | 메모리만 (localStorage/sessionStorage 금지) |
| CORS allowlist | 환경별 설정 (dev: localhost:5173 / prod: 프론트 호스팅 도메인 포함) |

---

## 3. 아키텍처

### 3.1 프로세스 구조

```
stockvision.exe (PyInstaller 번들)
├── main.py                        # 진입점
│   ├── FastAPI + uvicorn          # localhost:4020
│   │   ├── routers/ws.py          # WebSocket 엔드포인트
│   │   ├── routers/config.py      # 설정 API
│   │   ├── routers/status.py      # 상태 API
│   │   ├── routers/auth.py        # JWT 수신 API
│   │   └── routers/trading.py     # 전략 실행 API
│   │
│   ├── tray.py                    # pystray 시스템 트레이
│   │   ├── 더블클릭 → 대시보드 열기
│   │   ├── 아이콘 색상 (상태 반영)
│   │   └── 우클릭 메뉴 (상태, 엔진 토글, 종료)
│   │
│   ├── cloud_client/
│   │   ├── client.py              # 클라우드 서버 HTTP 클라이언트
│   │   ├── heartbeat.py           # 하트비트 (30초~1분) + 버전 감지
│   │   ├── rule_syncer.py         # 규칙 fetch/upload (버전 변경 시)
│   │   └── context_fetcher.py     # 컨텍스트 fetch (버전 변경 시)
│   │
│   └── storage/
│       ├── credential.py          # keyring (API Key + 클라우드 JWT)
│       ├── rule_cache.py          # 평문 JSON 파일
│       ├── watchlist_cache.py     # 관심종목 JSON 캐시
│       ├── stock_master_cache.py  # 종목 메타 JSON 캐시
│       ├── sync_queue.py          # 오프라인 변경사항 큐
│       ├── config_manager.py      # 클라우드 수신 설정 (규칙 관리)
│       └── log_db.py              # SQLite logs.db
```

### 3.2 시작 순서

```
1. .exe 실행
2. 저장소 초기화 (~/.stockvision/ 디렉토리 확인/생성)
3. config.json 로드
4. FastAPI + uvicorn 시작 (127.0.0.1:4020, 별도 스레드) — 0.0.0.0 금지
5. pystray 트레이 아이콘 생성 (메인 스레드) → 🔴
6. 자동 로그인 시도:
   ├── Credential Manager에서 Refresh Token 읽기
   ├── 클라우드 서버에 POST /auth/refresh → 새 JWT 발급
   └── 실패 시 → 🔴 "재로그인 필요" (브라우저에서 로그인 대기)
7. BrokerAdapter 초기화 (config.broker → 팩토리 → 인스턴스 주입)
   └── 키움: 토큰 자동 갱신 시도 (API Key 있으면)
8. 전략 규칙 캐시 로드 (strategies.json 있으면)
9. 하트비트 폴링 시작 (30초~1분 주기, 버전 감지 → 규칙/컨텍스트 fetch)
10. 준비 완료 → 트레이 아이콘 🟢
```

### 3.3 종료 순서

```
1. 트레이 "종료" 클릭 또는 시스템 종료 시그널
2. 실행 중인 전략 엔진 중지
3. 연결 정리 (BrokerAdapter WS, 프론트엔드 WS, 하트비트 폴링)
4. 미저장 로그 flush → logs.db
5. uvicorn shutdown
6. 트레이 아이콘 제거
7. 프로세스 종료
```

---

## 4. 상세 설계

### 4.1 시스템 트레이 (pystray)

```python
import pystray
from PIL import Image

class SystemTray:
    def __init__(self, status_provider):
        self._status = status_provider
        self._icon: pystray.Icon = None

    def start(self):
        """메인 스레드에서 트레이 아이콘 실행."""
        self._icon = pystray.Icon(
            "StockVision",
            icon=self._create_icon("green"),
            menu=self._create_menu(),
        )
        self._icon.run()

    def update_status(self, status: str):
        """아이콘 색상 업데이트.

        🟢 ok      — 정상 (키움 연결 + 하트비트 정상)
        🟡 warning  — 하트비트 연속 실패 5분+ 또는 Kill Switch 활성
        🔴 error    — 키움 끊김 또는 하트비트 실패 30분+
        """
        color = {"ok": "green", "warning": "yellow", "error": "red"}[status]
        self._icon.icon = self._create_icon(color)

    def on_double_click(self):
        """더블클릭 → 브라우저에서 대시보드 열기."""
        import webbrowser
        webbrowser.open("http://localhost:5173")

    def _create_menu(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem("StockVision v1.0", None, enabled=False),
            pystray.MenuItem(
                lambda _: f"{'🟢' if self._status.ok else '🔴'} {self._status.text}",
                None, enabled=False,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("대시보드 열기", self._open_dashboard),
            pystray.MenuItem(
                lambda _: "엔진 중지" if self._status.engine_running else "엔진 시작",
                self._toggle_engine,
            ),
            pystray.MenuItem(
                "⚠ 긴급 정지 (Kill Switch)",
                self._kill_switch,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                lambda _: f"오늘 체결: {self._status.today_fills}건",
                None, enabled=False,
            ),
            pystray.MenuItem(
                lambda _: f"활성 규칙: {self._status.active_rules}개",
                None, enabled=False,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("종료", self._quit),
        )
```

### 4.2 자격증명 저장 (keyring)

> 구현: `local_server/storage/credential.py`

```python
import keyring

# 서비스 이름: stockvision:{user_id} — user_id별 격리
_SERVICE_PREFIX = "stockvision"
_DEFAULT_USER = "default"

def _service_name(user_id: str = _DEFAULT_USER) -> str:
    return f"{_SERVICE_PREFIX}:{user_id}"

# keyring 키 이름 상수
KEY_APP_KEY = "kis_app_key"           # KIS 앱 키
KEY_APP_SECRET = "kis_app_secret"     # KIS 시크릿
KEY_ACCESS_TOKEN = "kis_access_token" # KIS 액세스 토큰
KEY_ACCOUNT_NO = "kis_account_no"     # KIS 계좌번호
KEY_KIWOOM_APP_KEY = "kiwoom_app_key"       # 키움 앱 키
KEY_KIWOOM_SECRET_KEY = "kiwoom_secret_key" # 키움 시크릿
KEY_CLOUD_ACCESS_TOKEN = "sv_cloud_access_token"   # 클라우드 JWT
KEY_CLOUD_REFRESH_TOKEN = "sv_cloud_refresh_token" # 클라우드 Refresh Token

def save_credential(name: str, value: str, user_id: str = _DEFAULT_USER) -> None:
    keyring.set_password(_service_name(user_id), name, value)

def load_credential(name: str, user_id: str = _DEFAULT_USER) -> str | None:
    return keyring.get_password(_service_name(user_id), name)
```

**네임스페이스 격리**: 동일 PC 내 멀티유저 지원. Windows Credential Manager DPAPI 암호화.

### 4.3 전략 규칙 캐시 (JSON)

```python
import json
from pathlib import Path

class RuleCache:
    """전략 규칙을 평문 JSON 파일로 캐시.

    암호화하지 않는 이유:
    - 클라우드 DB에도 평문으로 저장됨 (조건/지표일 뿐, 개인정보 아님)
    - 평문이면 공유/백업/디버깅 편의
    - 민감 데이터(API Key)는 Credential Manager가 담당
    """

    CACHE_PATH = Path.home() / ".stockvision/strategies.json"

    def save(self, rules: list[dict]):
        """규칙을 JSON 파일에 저장."""
        self.CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.CACHE_PATH.write_text(
            json.dumps(rules, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load(self) -> list[dict] | None:
        """JSON 파일에서 규칙 로드. 없으면 None."""
        try:
            return json.loads(self.CACHE_PATH.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
```

### 4.4 설정 관리 (config.json)

> 구현: `local_server/config.py`

```python
DEFAULT_CONFIG_PATH = Path.home() / ".stockvision" / "config.json"

DEFAULT_CONFIG = {
    "server": {
        "host": "127.0.0.1",
        "port": 4020,
    },
    "cloud": {
        "url": "",                     # 클라우드 서버 URL
        "heartbeat_interval": 30,      # 하트비트 전송 간격 (초)
    },
    "broker": {
        "type": "kiwoom",              # "kis" | "kiwoom" | "mock"
        "is_mock": True,               # 모의투자 여부
    },
    "kis": {
        "account_no": "",              # 계좌번호 (앱 키/시크릿은 keyring)
    },
    "cors": {
        "origins": ["http://localhost:5173"],
    },
    "sleep_prevent": True,
    "log_level": "INFO",
}

class Config:
    """config.json 읽기/쓰기. 점 표기법 지원 (예: 'server.port')."""

    def get(self, key: str, default=None) -> Any: ...
    def set(self, key: str, value: Any) -> None: ...
    def save(self) -> None: ...
```

**중첩 병합**: 파일 로드 시 `DEFAULT_CONFIG` 위에 사용자 설정을 재귀 병합.

### 4.5 로그 DB (SQLite)

```python
# logs.db 스키마

class ExecutionLog:
    """체결 로그."""
    __tablename__ = "execution_logs"

    id: int                 # PK
    timestamp: datetime     # 실행 시각
    rule_id: int            # 규칙 ID
    symbol: str             # 종목코드
    side: str               # BUY | SELL
    qty: int                # 수량
    price: int              # 체결가
    status: str             # FILLED | FAILED | REJECTED
    error_message: str      # 실패 시 사유
    raw_response: str       # 키움 원본 응답 JSON

class ErrorLog:
    """오류 로그."""
    __tablename__ = "error_logs"

    id: int
    timestamp: datetime
    source: str             # kiwoom | engine | server
    severity: str           # INFO | WARNING | ERROR | CRITICAL
    message: str
    details: str            # 스택 트레이스 등
```

### 4.6 WebSocket 메시지 스키마

> 구현: `local_server/routers/ws.py`

```python
# WS 메시지 타입 상수
WS_TYPE_PRICE_UPDATE = "price_update"    # 호가/현재가 갱신 (QuoteEvent)
WS_TYPE_EXECUTION = "execution"          # 체결 이벤트
WS_TYPE_STATUS_CHANGE = "status_change"  # 주문 상태 변경

# 모든 메시지 형식:
{
    "type": "price_update" | "execution" | "status_change" | "system",
    "data": { ... }
}
```

| type | 용도 | data 예시 |
|------|------|----------|
| `price_update` | 호가/현재가 갱신 | `{ symbol, price, volume, ... }` |
| `execution` | 주문 체결 | `{ rule_id, symbol, side, status, order_id, message }` |
| `status_change` | 주문 상태 변경 | `{ order_id, prev_status, new_status }` |
| `system` | 서버 시스템 메시지 | `{ message, connections }` |
| `ping`/`pong` | 하트비트 | `{}` |

- `side` 값: `"buy"` | `"sell"` (소문자)
- 연결 인증: `ws://localhost:4020/ws?sec={local_secret}` (shared secret)
- 60초 무메시지 → 서버가 `ping` 전송

### 4.7 오프라인 Sync 큐

> 구현: `local_server/storage/sync_queue.py`

```python
DEFAULT_QUEUE_PATH = Path.home() / ".stockvision" / "sync_queue.json"

ActionType = Literal[
    "rule_create",
    "rule_update",
    "rule_delete",
    "watchlist_add",
    "watchlist_remove",
]

# 큐 항목 형식:
{
    "type": ActionType,
    "data": { ... },          # 변경 내용
    "timestamp": "ISO 8601",  # 충돌 해결용 (last-write-wins)
}
```

- FIFO 순서 처리 (enqueue → dequeue)
- 클라우드 복구 시 flush → 서버 반영
- 충돌 해소: `timestamp` 비교 (LWW — Last Write Wins)

---

## 5. REST API (로컬 서버)

```
# 인증 (프론트엔드가 JWT 전달)
POST /api/auth/token          → JWT + Refresh Token 수신
                                 → Refresh Token → Credential Manager 저장
                                 → JWT → 메모리 보관

# 상태
GET  /api/status              → 서버 + 키움 + 엔진 + 클라우드 서버 연결 상태

# 설정
POST /api/config/kiwoom       → API Key 등록 (→ Credential Manager)
GET  /api/config              → 현재 설정 조회
PATCH /api/config             → 설정 변경

# 규칙 (프론트엔드에서 저장 → 로컬 캐시 + 클라우드 sync)
POST /api/rules/sync          → 규칙 수신 → JSON 캐시 저장 + 클라우드 upload

# 전략 실행
POST /api/strategy/start      → 전략 엔진 시작
POST /api/strategy/stop       → 전략 엔진 중지
POST /api/strategy/kill        → Kill Switch (즉시 전체 중지, 신규 주문 차단)
POST /api/strategy/unlock      → 손실 락 해제 (수동 해제만 허용)

# 로그
GET  /api/logs?limit=100      → 체결/오류 로그 조회

# WebSocket (프론트엔드용)
WS   /ws                      → 실시간 시세 + 체결 이벤트 + 상태 변경
```

> **참고**: 컨텍스트 sync, 하트비트 전송은 로컬 서버가 클라우드 서버에 직접 통신.
> 프론트엔드 경유 불필요.

---

## 6. 저장 구조

```
~/.stockvision/
├── strategies.json         # 전략 규칙 캐시 (평문 JSON)
├── watchlist.json          # 관심종목 캐시 (오프라인 대응)
├── stock_master.json       # 종목 메타데이터 캐시 (전체 ~150KB, 오프라인 검색)
├── stock_detail_cache.json # 조회한 종목 상세 캐시 (온디맨드)
├── config.json             # 설정 (§4.4 참조)
├── sync_queue.json         # 오프라인 변경사항 큐 (§4.7 참조)
├── logs.db                 # SQLite — 체결 로그, 오류 로그
└── Windows Credential Manager (keyring):
    서비스명: stockvision:{user_id} (§4.2 참조)
    ├── kis_app_key              # KIS API Key
    ├── kis_app_secret           # KIS API Secret
    ├── kis_access_token         # KIS 액세스 토큰
    ├── kis_account_no           # KIS 계좌번호
    ├── kiwoom_app_key           # 키움 API Key
    ├── kiwoom_secret_key        # 키움 API Secret
    ├── sv_cloud_access_token    # 클라우드 JWT
    └── sv_cloud_refresh_token   # 클라우드 Refresh Token
```

---

## 7. 수용 기준

### 7.1 서버

- [ ] `stockvision.exe` 실행 → localhost:4020 서빙 시작 (< 5초)
- [x] `GET /api/status` → `{ "server": "running", "uptime": ... }` 응답
- [x] 트레이 아이콘이 시스템 트레이에 표시됨

### 7.2 트레이

- [x] 더블클릭 → 기본 브라우저로 대시보드 열림
- [x] 우클릭 메뉴: 상태, 대시보드 열기, 엔진 토글, 체결/규칙 수, 종료
- [x] "종료" → 서버 정상 종료
- [x] 상태 변경 시 아이콘 색상 즉시 반영 (🟢🟡🔴)

### 7.3 저장소

- [x] API Key 등록 → Credential Manager에 저장 확인
- [x] API Key 조회 → 저장된 값 정상 반환
- [x] Refresh Token 저장 → Credential Manager 확인
- [x] 규칙 sync → strategies.json 파일 생성
- [x] 서버 재시작 → strategies.json에서 규칙 복원

### 7.4 클라우드 서버 직접 통신

- [x] JWT 전달(POST /api/auth/token) → Refresh Token Credential Manager 저장
- [x] 로컬 서버가 클라우드 서버에 컨텍스트 fetch 성공 (JWT 인증)
- [x] 하트비트 주기적 전송 확인
- [ ] JWT 만료 → Refresh Token으로 자동 갱신
- [ ] PC 재부팅 → Refresh Token으로 자동 로그인 → 트레이 🟢

### 7.5 하트비트 폴링 + 버전 감지

- [x] 하트비트 응답에서 rules_version 변경 감지 → 규칙 자동 fetch + JSON 캐시 갱신
- [ ] 규칙 fetch 응답에 version + updated_at 포함, 로컬은 마지막 적용 version/updated_at 저장 → 정합성 검증
- [x] 하트비트 응답에서 context_version 변경 감지 → 컨텍스트 자동 fetch
- [x] 하트비트 연속 실패 5분 → 트레이 🟡 (캐시 규칙으로 계속 실행)
- [x] 하트비트 연속 실패 30분 → 트레이 🔴 + 토스트 알림
- [x] 하트비트 응답에 latest_version 포함 시 현재 버전과 비교 → 업데이트 권고 알림
- [x] 하트비트 응답에 min_version 포함 시 현재 < min_version → 트레이 🔴 + "업데이트 필수" 알림

### 7.6 안전장치

- [x] 트레이 "긴급 정지" 클릭 → Trading Enabled=OFF + 트레이 🟡
- [x] `POST /api/strategy/kill` → Trading Enabled=OFF (STOP_NEW / CANCEL_OPEN 선택)
- [x] CORS 미들웨어가 Origin 검증 겸용 (별도 Origin 미들웨어 불필요, 환경별 allowlist: dev=localhost / prod=호스팅 도메인)
- [x] uvicorn 바인딩이 127.0.0.1만 사용 (0.0.0.0 아님)
- [ ] Access Token이 localStorage/sessionStorage에 저장되지 않음 (메모리만)

### 7.7 로그

- [x] 체결 발생 → logs.db에 ExecutionLog 기록
- [x] `GET /api/logs?limit=10` → 최근 10건 반환

### 7.9 오프라인 내성

- [ ] 클라우드 미연결 시 규칙 생성/수정 → strategies.json에 저장 + sync_queue.json에 큐 적재
- [ ] 클라우드 미연결 시 관심종목 등록/해제 → watchlist.json에 저장 + sync_queue.json에 큐 적재
- [ ] 클라우드 복구 → sync_queue.json flush → 클라우드 반영
- [ ] 충돌 해소: updated_at 비교 (last-write-wins)
- [ ] stock_master.json으로 오프라인 종목 검색 가능
- [ ] stock_detail_cache.json에 조회한 종목 상세 캐시 유지

### 7.8 패키징

- [ ] PyInstaller → 단일 .exe 생성
- [ ] .exe 실행 → 정상 동작 (의존성 번들 확인)

---

## 8. 범위

### 포함

- FastAPI 서버 구조 (routers, middleware)
- pystray 시스템 트레이 (더블클릭, 우클릭 메뉴, 색상)
- keyring (Credential Manager) 연동 (API Key + Refresh Token)
- JSON 규칙 캐시
- config.json 관리
- SQLite logs.db
- 클라우드 서버 HTTP 폴링 (하트비트 + 버전 감지 + fetch/sync)
- REST API 엔드포인트 정의
- WebSocket 엔드포인트 (프론트엔드용: 시세 + 체결)
- 레지스트리 Run 키 자동 시작
- 체결 토스트 알림 (Windows 알림)
- PyInstaller 빌드 설정

### 미포함

- 키움 REST API 클라이언트 (Unit 1)
- 전략 평가 엔진 (Unit 3)
- 프론트엔드 UI (Unit 5)
- 자동 업데이트 (v2)

---

## 9. 기존 spec과의 관계

| 기존 | 상태 |
|------|------|
| `spec/local-bridge/` | **대체됨** — 서버 구조 부분은 본 spec, 키움 부분은 Unit 1 |

---

## 10. 기술 요구사항

| 항목 | 선택 |
|------|------|
| Python | 3.13 |
| 웹 프레임워크 | FastAPI + uvicorn |
| 트레이 | pystray + Pillow |
| 자격증명 | keyring (Windows Credential Manager) |
| HTTP 클라이언트 | httpx (클라우드 서버 통신) |
| 로컬 DB | SQLite (aiosqlite) |
| 패키징 | PyInstaller |

---

## 11. 미결 사항

- [x] FastAPI와 pystray 이벤트 루프 통합 방식 → 별도 데몬 스레드 분리
- [ ] .exe 번들 시 Pillow 이미지 포함 방법
- [x] Windows 시작프로그램 등록 레지스트리 키 경로 → `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`
- [ ] logs.db 자동 정리 정책 (보관 기간, 최대 크기)
- [ ] config.json 스키마 버전 관리 (마이그레이션)

---

## 참고

- `docs/architecture.md` §4.4, §5.1, §7
- `spec/local-bridge/spec.md` (이전 버전)
- `docs/development-plan-v2.md` Unit 2

---

**마지막 갱신**: 2026-03-09
