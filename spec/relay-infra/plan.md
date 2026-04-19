# 릴레이 인프라 구현 계획

> 작성일: 2026-03-12 | 상태: 구현 완료 | 갱신: 2026-03-18 (Step 1~4 구현 완료, Step 5~8 감사 완료 — ping/pong+JWT re-auth 구현) | Phase C (C6-a)

## 아키텍처

```
로컬 서버                        클라우드 서버                     원격 디바이스
┌──────────────┐              ┌─────────────────┐              ┌──────────────┐
│ WsRelayClient │─── WS ────►│ /ws/relay        │              │              │
│ (cloud연결)   │◄── WS ─────│ RelayManager     │              │              │
│              │              │   ├ registry     │              │              │
│ E2ECrypto    │              │   ├ pending_queue │              │              │
│ (encrypt)    │              │   └ audit_log    │──── WS ────►│ WS client    │
│              │              │ /ws/remote       │◄── WS ─────│ E2ECrypto    │
│ heartbeat.py │              │ SessionManager   │              │ (decrypt)    │
│ (WS로 대체)  │              │ RateLimiter      │              │              │
└──────────────┘              └─────────────────┘              └──────────────┘
```

**데이터 흐름**:
- 상태: 로컬 → encrypt → 클라우드(릴레이) → 디바이스 → decrypt
- 명령: 디바이스 → 클라우드(릴레이/큐) → 로컬 → ACK → 디바이스
- heartbeat: 로컬 → 클라우드(버전 체크) → heartbeat_ack → 로컬(규칙 sync)

## 수정 파일 목록

### 클라우드 서버 (신규 5, 수정 2)

| 파일 | 변경 | 내용 |
|------|------|------|
| `cloud_server/api/ws_relay.py` | 신규 | `/ws/relay` 로컬 서버 전용 WS, `/ws/remote` 디바이스 전용 WS |
| `cloud_server/services/relay_manager.py` | 신규 | 연결 레지스트리, 메시지 라우팅, pending 큐 관리 |
| `cloud_server/services/session_manager.py` | 신규 | 디바이스 세션 관리, 동시 접속 제한, ping/pong |
| `cloud_server/models/pending_command.py` | 신규 | `pending_commands` 테이블 |
| `cloud_server/models/audit_log.py` | 신규 | `audit_logs` 테이블 |
| `cloud_server/main.py` | 수정 | WS 라우터 등록 |
| `cloud_server/core/init_db.py` | 수정 | 신규 모델 import |

### 로컬 서버 (신규 2, 수정 3)

| 파일 | 변경 | 내용 |
|------|------|------|
| `local_server/cloud/ws_relay_client.py` | 신규 | 클라우드 WS 연결, 재연결, 메시지 송수신 |
| `local_server/cloud/e2e_crypto.py` | 신규 | AES-256-GCM 암호화/복호화, 키 관리 |
| `local_server/cloud/heartbeat.py` | 수정 | WS heartbeat로 전환, HTTP 폴백 유지 |
| `local_server/main.py` | 수정 | WS 클라이언트 시작 |
| `local_server/config.py` | 수정 | `cloud.ws_url` 기본값 추가 |

### 프론트엔드 (신규 1)

| 파일 | 변경 | 내용 |
|------|------|------|
| `frontend/src/utils/e2eCrypto.ts` | 신규 | Web Crypto API 기반 AES-256-GCM 복호화 |

## 구현 순서

### Step 1: 클라우드 WS 엔드포인트 — `/ws/relay` ✅

로컬 서버 전용 WS 엔드포인트. 인증 + 연결 레지스트리.

**파일**:
1. `cloud_server/api/ws_relay.py`
   - `@app.websocket("/ws/relay")` 엔드포인트
   - 첫 메시지 `{ type: "auth", payload: { token } }` → JWT 검증
   - 인증 실패 → close(4001)
   - 인증 성공 → `RelayManager.register(user_id, ws)`
   - 메시지 루프: 수신 → `RelayManager.handle_message()`
   - 연결 종료 → `RelayManager.unregister(user_id)`

2. `cloud_server/services/relay_manager.py`
   - `_local_connections: dict[str, WebSocket]` — user_id → WS
   - `register(user_id, ws)` / `unregister(user_id)`
   - `is_local_online(user_id) → bool`
   - `send_to_local(user_id, message) → bool`
   - `handle_message(user_id, message)` — heartbeat 처리, state 릴레이

3. `cloud_server/main.py` — WS 라우터 등록

**verify**: 클라우드 서버 시작 → `wscat -c ws://localhost:4010/ws/relay` → auth 메시지 전송 → 연결 유지 확인

---

### Step 2: 로컬 WS 클라이언트 ✅

클라우드 WS에 연결하고 유지하는 클라이언트.

**파일**:
1. `local_server/cloud/ws_relay_client.py`
   - `WsRelayClient` 클래스
   - `async start(cloud_ws_url, jwt_token)`
   - `async _connect()` — `websockets` 라이브러리로 연결
   - `async _auth()` — 첫 메시지로 JWT 전송
   - `async _recv_loop()` — 메시지 수신 → 핸들러 디스패치
   - `async _reconnect()` — exponential backoff (1s → 60s max)
   - `async send(message: dict)` — JSON 직렬화 + 전송
   - `async stop()`
   - `is_connected → bool`

2. `local_server/main.py`
   - lifespan에서 `WsRelayClient.start()` 호출 (하트비트 시작 직후)
   - shutdown에서 `WsRelayClient.stop()`

3. `local_server/config.py`
   - `cloud.ws_url` 기본값: `ws://localhost:4010/ws/relay`

**verify**: 로컬+클라우드 동시 시작 → 로컬 로그에 "Cloud WS connected" → 클라우드 로그에 "Local registered: {user_id}" → 클라우드 강제 종료 → 로컬 로그에 재연결 시도 확인

---

### Step 3: Heartbeat WS 전환 ✅

기존 HTTP POST 하트비트를 WS 메시지로 전환.

**파일**:
1. `local_server/cloud/heartbeat.py` 수정
   - `_send_heartbeat()` → WS 연결 시 WS로 전송, 끊김 시 HTTP 폴백
   - 메시지 형식: `{ v: 1, type: "heartbeat", id, ts, payload: { 기존 하트비트 필드 } }`
   - HTTP 폴백: 기존 `_post("/api/v1/heartbeat", payload)` 유지

2. `cloud_server/services/relay_manager.py` 수정
   - `handle_message()` — `type: "heartbeat"` 수신 시:
     - 기존 `HeartbeatService.process()` 호출
     - `heartbeat_ack` 응답 (버전 정보 포함)

3. `local_server/cloud/heartbeat.py` 수정
   - `heartbeat_ack` 수신 시 기존 버전 체크 로직 실행 (규칙/컨텍스트 sync)

**verify**: 로컬 시작 → 클라우드 DB heartbeats 테이블 업데이트 확인 → 규칙 변경 → 로컬 자동 sync 확인

---

### Step 4: 메시지 프로토콜 + 라우팅 ✅

envelope 형식 정의 + 클라우드의 메시지 라우팅.

**파일**:
1. `cloud_server/services/relay_manager.py` 수정
   - `handle_local_message(user_id, msg)`:
     - `type: "state"` → 등록된 디바이스 WS로 브로드캐스트
     - `type: "alert"` → 디바이스 WS로 브로드캐스트 + FCM 트리거 (C6-c)
     - `type: "command_ack"` → 해당 디바이스 WS로 전달
   - `handle_device_message(user_id, device_id, msg)`:
     - `type: "command"` → 로컬 WS로 전달 (또는 pending 큐)
     - `type: "sync_request"` → 로컬 WS로 전달
     - `type: "ack"` → 로깅만

**verify**: 로컬에서 `{ type: "state", payload: { engine_state: "running" } }` 전송 → 클라우드 로그에 라우팅 확인

---

### Step 5: 클라우드 WS 엔드포인트 — `/ws/remote`

원격 디바이스 전용 WS.

**파일**:
1. `cloud_server/api/ws_relay.py` 추가
   - `@app.websocket("/ws/remote")` 엔드포인트
   - 첫 메시지: `{ type: "auth", payload: { token, device_id } }`
   - JWT + device_id 검증 (디바이스 테이블 확인은 C6-b 의존, 초기에는 JWT만)
   - `SessionManager.register(user_id, device_id, ws)`

2. `cloud_server/services/session_manager.py`
   - `_device_sessions: dict[str, dict[str, WebSocket]]` — user_id → { device_id → WS }
   - `register(user_id, device_id, ws)` — 동시 세션 5대 체크
   - `unregister(user_id, device_id)`
   - `broadcast_to_devices(user_id, message)` — 해당 사용자의 모든 디바이스에 전송
   - `send_to_device(user_id, device_id, message)`
   - `kill_session(user_id, device_id)` — 강제 종료
   - ping/pong 태스크 (30초)

**verify**: `wscat -c ws://localhost:4010/ws/remote` → auth → 연결 유지 → 로컬에서 state 전송 → 디바이스에서 수신 확인

---

### Step 6: E2E 암호화 모듈

Python(로컬) + TypeScript(프론트) 양쪽 구현.

**파일**:
1. `local_server/cloud/e2e_crypto.py`
   ```python
   class E2ECrypto:
       def __init__(self, key_store_path: str):
           # ~/.stockvision/device_keys/ 디렉토리에서 키 로드
       def encrypt(self, plaintext: dict, device_id: str) -> dict:
           # { iv, ciphertext, tag } 반환
       def encrypt_for_all(self, plaintext: dict) -> dict:
           # 등록된 모든 디바이스용 { device_id: { iv, ciphertext, tag } }
       def generate_key(self) -> tuple[str, bytes]:
           # (device_id, key_bytes) 반환
       def register_key(self, device_id: str, key: bytes)
       def revoke_key(self, device_id: str)
   ```

2. `frontend/src/utils/e2eCrypto.ts`
   ```typescript
   export async function decrypt(
     encrypted: { iv: string; ciphertext: string; tag: string },
     keyBase64: string
   ): Promise<object>
   // Web Crypto API — AES-256-GCM
   ```

**verify**: Python에서 암호화 → base64 출력 → JS에서 같은 키로 복호화 → 원본 일치 단위 테스트

---

### Step 7: 오프라인 명령 큐

로컬 오프라인 시 명령 저장 + 재연결 시 flush.

**파일**:
1. `cloud_server/models/pending_command.py`
   ```python
   class PendingCommand(Base):
       __tablename__ = "pending_commands"
       id         = Column(Integer, primary_key=True)
       user_id    = Column(UUID, nullable=False, index=True)
       command_type = Column(String(50))  # 'kill', 'arm', ...
       payload    = Column(JSONB)
       status     = Column(String(20), default='pending')  # pending/executed/expired
       created_at = Column(DateTime, default=now)
       executed_at = Column(DateTime)
   ```

2. `cloud_server/services/relay_manager.py` 수정
   - `send_to_local()` 실패 시 → `PendingCommand` 저장
   - `on_local_connect(user_id)` → pending 큐 조회 → flush → ACK 대기

3. `cloud_server/core/init_db.py` — PendingCommand import

**verify**: 로컬 오프라인 → 디바이스에서 kill 명령 → DB에 pending 저장 확인 → 로컬 재연결 → 명령 수신 + 실행 + DB status='executed' 확인

---

### Step 8: 감사 로그 + Rate Limiting

**파일**:
1. `cloud_server/models/audit_log.py`
   ```python
   class AuditLog(Base):
       __tablename__ = "audit_logs"
       id         = Column(Integer, primary_key=True)
       user_id    = Column(UUID, nullable=False, index=True)
       device_id  = Column(String(50))
       action     = Column(String(50), nullable=False)
       detail     = Column(JSONB)
       ip_address = Column(String(45))
       created_at = Column(DateTime, default=now)
   ```

2. `cloud_server/services/relay_manager.py` 수정
   - 모든 command 처리 시 `AuditLog` 저장

3. `cloud_server/services/relay_manager.py` 또는 별도 미들웨어
   - `RateLimiter` 클래스: in-memory counter (user_id 기반)
   - command 10건/분, 전체 60건/분/연결
   - 초과 시 `{ type: "error", payload: { code: 429 } }` 전송

**verify**: 감사 로그 — kill 명령 → DB audit_logs 확인. Rate limit — 빠르게 11건 command → 11번째에서 429 확인.

## 의존성 그래프

```
Step 1 (클라우드 WS /relay)
  └→ Step 2 (로컬 WS 클라이언트)
       └→ Step 3 (Heartbeat WS 전환)
       └→ Step 4 (메시지 프로토콜)
            └→ Step 5 (클라우드 WS /remote)
            └→ Step 6 (E2E 암호화)
            └→ Step 7 (오프라인 큐)
  Step 8 (감사 로그 + Rate limit) — Step 4 이후 언제든
```

## 검증 방법

- Python: `pytest` 단위 테스트 (E2E 암호화, 메시지 직렬화)
- 통합: 로컬+클라우드 동시 실행 → WS 연결 → heartbeat → state 릴레이
- E2E: Python encrypt → JS decrypt 크로스 플랫폼 테스트
- 재연결: 클라우드 강제 종료 → 로컬 재연결 → pending flush
