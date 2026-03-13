# 릴레이 인프라 (Relay Infrastructure)

> 작성일: 2026-03-12 | 상태: 초안 | Phase C (C6-a)
>
> 대체: `spec/remote-control/spec.md` §5 통신 경로 부분을 대체

## 1. 배경

원격 제어(C6-c)를 구현하려면 클라우드와 로컬 서버 간 양방향 통신 채널이 필요하다. 현재는 로컬→클라우드 방향의 30초 하트비트(HTTP POST)만 존재하며, 클라우드→로컬 명령 전달 경로가 없다.

논의 결과 결정된 사항:
- **WS 상시 연결** (하트비트 폴링 대신)
- **E2E 암호화** (클라우드가 금융 데이터를 읽을 수 없도록)
- **디바이스별 암호화 키** (기기 분실 시 해당 기기만 차단)
- **메시지 큐** (로컬 일시 단절 시 클라우드가 명령을 큐잉, 재연결 시 flush)

이 spec은 원격 제어의 **통신 파이프라인**만 정의한다. 파이프 위에서 동작하는 인증(C6-b)과 실제 기능(C6-c)은 별도 spec.

## 2. 목표

로컬 서버와 클라우드 서버 간 안전한 양방향 실시간 통신 채널을 구축한다.

## 3. 범위

### 3.1 포함

**A. 로컬→클라우드 WebSocket 상시 연결**
- 로컬 서버 시작 시 클라우드 WS에 연결
- 클라우드는 연결 레지스트리만 관리
- 끊김 시 재연결은 로컬 서버 책임 (exponential backoff)
- 기존 하트비트(HTTP POST)는 WS 연결 내 heartbeat 메시지로 대체

**B. E2E 암호화**
- AES-256-GCM (인증 + 암호화 동시)
- 디바이스별 별도 키 (페어링 시 생성)
- 금융 데이터만 암호화 (잔고, 보유종목, 손익, 미체결, 체결 결과)
- 시스템 상태는 평문 (엔진 상태, kill switch, 연결 상태, 경고)

**C. 메시지 프로토콜**
- 버전 관리 가능한 envelope 형식
- 타입: command, state, alert, ack
- 각 메시지에 고유 ID + 타임스탬프

**D. 메시지 큐 (오프라인 명령)**
- 로컬 WS 끊김 시 클라우드 DB에 pending 명령 저장 (평문, 비금융)
- 재연결 시 큐 flush → WS로 전송
- 로컬 ACK 후 큐에서 제거

**E. 세션 관리**
- 디바이스 ID + JWT 기반 WS 세션 인증
- 동시 디바이스 제한 (기본 5대)
- WS ping/pong (30초 무응답 → 세션 종료)
- JWT 만료 시 WS 내 재인증 요구
- 디바이스별 세션 강제 종료 (로컬 PC에서)

**F. 감사 로그**
- 모든 명령에 대해 기록: 누가, 언제, 어디서(디바이스), 무슨 명령
- 클라우드 DB 저장 (명령 내용은 평문 — 금융 데이터 아님)

**G. Rate Limiting**
- 원격 명령: 분당 N건 제한
- WS 메시지: 초당 N건 제한
- 초과 시 429 응답 + 일시 차단

### 3.2 제외

- 디바이스 등록/페어링 UX → C6-b (인증 확장)
- 원격 상태 조회/킬스위치/arm 기능 → C6-c (원격 제어)
- FCM 푸시 → C6-c
- 메신저 봇 → Phase D

## 4. 의존성

| 의존 대상 | 상태 | 비고 |
|-----------|------|------|
| 하트비트 (`local_server/cloud/heartbeat.py`) | 구현됨 | WS로 대체/통합. HTTP POST 엔드포인트는 WS 안정화 후 폐기 예정. 전환기에는 WS 실패 시 HTTP 폴백 유지 |
| CloudClient (`local_server/cloud/client.py`) | 구현됨 | WS 클라이언트 추가 |
| 클라우드 인증 (`cloud_server/api/auth.py`) | 구현됨 | JWT 기반 WS 인증 |
| config.json | 구현됨 | `cloud.ws_url` 추가 |

## 5. 설계

### 5.1 WS 연결 수명주기

```
로컬 서버 시작
  → cloud WS 연결 (wss://cloud/ws/relay)
  → 첫 메시지로 인증: { type: "auth", payload: { token: "JWT" } }
  → 인증 성공 → 연결 유지
  → (JWT를 query string에 넣지 않음 — 서버 로그 노출 방지)
  → 30초마다 heartbeat 메시지 전송 (기존 하트비트 데이터 포함)
  → 클라우드 응답에 version 정보 포함 (기존 규칙/컨텍스트 버전 체크)

끊김 감지 (ping/pong 실패 또는 네트워크 에러)
  → 즉시 재연결 시도
  → 실패 시 exponential backoff (1s → 2s → 4s → ... → 최대 60s)
  → 재연결 성공 시 backoff 리셋
  → 재연결 시 클라우드가 pending 큐 flush

클라우드 서버
  → 연결 레지스트리: { user_id → WebSocket } 매핑
  → 연결/끊김 이벤트 로깅
  → 로컬 오프라인 판정: 마지막 heartbeat 후 90초 무응답
```

### 5.2 E2E 암호화

**알고리즘**: AES-256-GCM
- 키: 256bit (32바이트), 디바이스 페어링 시 생성
- IV: 매 메시지마다 랜덤 12바이트
- Python: `cryptography` 라이브러리
- Frontend: Web Crypto API (브라우저 내장)

**암호화 범위**:

| 암호화 O (금융 데이터) | 암호화 X (시스템 상태) |
|----------------------|---------------------|
| 잔고, 보유종목, 평가손익 | 엔진 상태 (running/stopped) |
| 미체결 주문 | Kill Switch / 손실 락 상태 |
| 체결 결과 | 경고 알림 |
| 당일 실현손익 | 연결 상태, 버전 정보 |

**메시지 내 암호화 필드**:

로컬 서버가 상태를 보낼 때, 등록된 디바이스 수만큼 암호화 블록을 생성:

```json
{
  "v": 1,
  "type": "state",
  "id": "uuid",
  "ts": "ISO8601",
  "payload": {
    "engine_state": "running",
    "broker_connected": true,
    "encrypted_for": {
      "device-A-id": { "iv": "base64-iv", "ciphertext": "base64-ciphertext", "tag": "base64-auth-tag" },
      "device-B-id": { "iv": "base64-iv", "ciphertext": "base64-ciphertext", "tag": "base64-auth-tag" }
    }
  }
}
```

클라우드는 `encrypted_for` 블록을 읽을 수 없다. 각 디바이스가 자신의 키로 자기 블록만 복호화.
디바이스가 5대를 넘지 않으므로 성능 이슈 없음. 등록된 디바이스가 없으면 `encrypted_for`는 빈 객체.

### 5.3 메시지 프로토콜

**Envelope 형식** (고정, 확장 가능):

```json
{
  "v": 1,
  "type": "command | state | alert | ack | heartbeat",
  "id": "uuid-v4",
  "ts": "2026-03-12T10:30:00Z",
  "payload": { ... }
}
```

**초기 지원 타입**:

| type | 방향 | 용도 |
|------|------|------|
| `heartbeat` | 로컬→클라우드 | 30초 주기 상태 보고 (기존 하트비트 대체) |
| `heartbeat_ack` | 클라우드→로컬 | 버전 정보 응답 |
| `state` | 로컬→클라우드→디바이스 | 상태 변경 브로드캐스트 |
| `command` | 디바이스→클라우드→로컬 | 킬스위치, arm 등 명령 |
| `command_ack` | 로컬→클라우드→디바이스 | 명령 실행 결과 |
| `alert` | 로컬→클라우드→디바이스 | 경고/알림 |
| `ack` | 양방향 | 메시지 수신 확인 |

**타입은 개발 중 추가될 수 있다.** envelope 형식만 고정이고 payload 스키마는 타입별로 자유롭게 확장.

### 5.4 메시지 동기화 (디바이스 오프라인 복구)

디바이스가 오프라인이었다가 재연결할 때:

1. 디바이스가 `last_received_ts` 전송
2. 클라우드가 릴레이만 하므로 메시지를 보관하지 않음
3. 클라우드→로컬 WS로 `{ type: "sync_request", payload: { device_id, last_received_ts } }` 전달
4. 로컬 서버가 해당 시점 이후의 상태/이벤트를 재전송
5. 디바이스가 수신하며 로컬 저장 (IndexedDB)

> 로컬 서버가 꺼져 있으면 갭 채우기 불가. 로컬 복귀 후 자동 재시도.

### 5.5 오프라인 명령 큐

로컬 WS가 끊겨 있을 때 원격에서 명령(킬스위치 등)을 보내면:

1. 클라우드 DB `pending_commands` 테이블에 저장
2. 저장 내용: `user_id, command_type, payload, created_at, status`
3. 명령은 비금융 데이터이므로 평문 저장 OK
4. 로컬 WS 재연결 시 클라우드가 pending 큐 flush
5. 로컬 실행 후 ACK → 클라우드가 `status = 'executed'`로 업데이트

### 5.6 세션 관리

```
디바이스 WS 연결
  → Authorization: Bearer JWT
  → 클라우드가 JWT 검증 + 디바이스 ID 확인
  → 동시 세션 수 체크 (초과 시 가장 오래된 세션 종료)
  → 세션 레지스트리에 등록

세션 유지
  → 30초마다 ping/pong
  → 무응답 시 세션 종료 + 레지스트리에서 제거

JWT 만료 (세션 중)
  → 클라우드가 { type: "auth_required" } 전송
  → 디바이스가 새 JWT로 재인증
  → 실패 시 60초 후 세션 종료

강제 종료
  → 로컬 PC에서 디바이스 관리 UI → 특정 디바이스 세션 kill
  → 클라우드가 해당 WS 연결 종료
```

### 5.7 감사 로그 스키마

클라우드 DB `audit_logs` 테이블:

```sql
id          SERIAL PRIMARY KEY
user_id     UUID NOT NULL
device_id   VARCHAR(50)
action      VARCHAR(50) NOT NULL  -- 'kill', 'arm', 'disarm', 'device_register', ...
detail      JSONB
ip_address  VARCHAR(45)
created_at  TIMESTAMP DEFAULT NOW()
```

### 5.8 Rate Limiting

| 대상 | 제한 | 초과 시 |
|------|------|--------|
| 명령 (command) | 10건/분/사용자 | 429 + 60초 차단 |
| 상태 요청 (state) | 30건/분/사용자 | 429 + 30초 차단 |
| WS 메시지 전체 | 60건/분/연결 | 경고 후 연결 종료 |

## 6. API / 엔드포인트

### 클라우드 서버

```
WS  /ws/relay           — 로컬 서버 전용 WS (JWT 인증)
WS  /ws/remote           — 원격 디바이스 전용 WS (JWT + device_id 인증)
```

### 로컬 서버

기존 `/ws` 엔드포인트는 유지 (같은 PC 프론트용). 클라우드 WS는 별도 클라이언트로 연결.

## 7. 수용 기준

### WS 연결
- [ ] 로컬 서버 시작 시 클라우드 WS에 자동 연결된다
- [ ] 연결 끊김 시 exponential backoff로 자동 재연결된다
- [ ] 기존 하트비트 데이터가 WS heartbeat 메시지로 전달된다
- [ ] 클라우드가 하트비트 응답에 버전 정보를 포함한다 (기존 기능 유지)

### E2E 암호화
- [ ] 금융 데이터(잔고, 손익 등)가 암호화되어 전송된다
- [ ] 클라우드 서버가 암호화된 데이터를 복호화할 수 없다
- [ ] 디바이스별 별도 키가 사용된다
- [ ] 시스템 상태(엔진, 킬스위치)는 평문으로 전달된다

### 메시지 프로토콜
- [ ] 모든 메시지가 envelope 형식(v, type, id, ts, payload)을 따른다
- [ ] 디바이스 오프라인 후 재연결 시 last_received_ts 기반 갭 채우기가 동작한다

### 오프라인 명령 큐
- [ ] 로컬 오프라인 시 명령이 클라우드 DB에 저장된다
- [ ] 로컬 재연결 시 pending 명령이 WS로 flush된다
- [ ] 실행 후 ACK로 큐에서 제거된다

### 세션 관리
- [ ] 동시 디바이스 수가 제한된다 (기본 5대)
- [ ] ping/pong 무응답 시 세션이 종료된다
- [ ] JWT 만료 시 재인증이 요구된다
- [ ] 특정 디바이스 세션을 강제 종료할 수 있다

### 감사 로그
- [ ] 모든 명령이 감사 로그에 기록된다 (사용자, 디바이스, 시각, IP)

### Rate Limiting
- [ ] 명령 초과 시 429 응답이 반환된다

## 8. 참고

- 기존 하트비트: `local_server/cloud/heartbeat.py`
- 기존 CloudClient: `local_server/cloud/client.py`
- 기존 WS (로컬): `local_server/routers/ws.py`
- 권한 모델: `docs/product/remote-permission-model.md`
- 기존 원격 제어 spec (대체됨): `spec/remote-control/spec.md`
