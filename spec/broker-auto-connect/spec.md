> 작성일: 2026-03-11 | 상태: 확정

# 브로커 자동 연결 — 거래와 조회 분리

## 목표

로컬 서버가 시작되면 증권사 API 키가 있는 경우 **자동으로 브로커에 연결**하여, 전략 엔진 시작 없이도 계좌 잔고·보유종목·미체결 주문·개별 종목 시세를 조회할 수 있게 한다.

현재 문제:
- 잔고 조회(`GET /api/account/balance`)가 전략 엔진 시작에 묶여 있음
- 사용자가 "전략 실행"을 누르지 않으면 자기 계좌도 못 봄
- 계좌 조회와 자동매매는 관계없는 기능인데 결합되어 있음

## 요구사항

### 기능적 요구사항

| ID | 요구사항 | 우선순위 |
|----|---------|---------|
| F1 | 로컬 서버 시작 시 증권사 키가 있으면 자동으로 `broker.connect()` 실행 | P0 |
| F2 | 엔진 미시작 상태에서 `GET /api/account/balance` 정상 응답 | P0 |
| F3 | 엔진 미시작 상태에서 `GET /api/account/orders` 정상 응답 | P0 |
| F4 | 엔진 미시작 상태에서 `GET /api/quote/{symbol}` 단건 시세 조회 (REST) | P1 |
| F5 | 전략 엔진 시작/중지가 브로커 연결에 영향 없음 (엔진 중지해도 브로커 유지) | P0 |
| F6 | 키가 없으면 연결 시도 안 함. `GET /api/status`에 `"broker.connected": false, "reason": "no_credentials"` 표시 | P0 |
| F7 | 연결 실패 시 재시도 (30초 간격, 최대 3회). 실패 사유 status에 노출 | P1 |
| F8 | 설정 페이지에서 키 등록 후 즉시 연결 시도 (서버 재시작 불필요) | P1 |

### 비기능적 요구사항

| 항목 | 목표 |
|------|------|
| 서버 시작 지연 | 브로커 연결은 비동기, 서버 응답은 즉시 |
| 토큰 갱신 | 키움 토큰 만료 시 자동 재발급 (기존 어댑터 로직 활용) |

## 설계

### 브로커 생명주기 변경

**현재**: `엔진 시작` → `broker 생성 + connect` → `엔진 중지` → `broker disconnect + 삭제`

**변경**: `서버 시작` → `broker 생성 + connect (키 있으면)` → 서버 종료까지 유지

```
서버 시작 (lifespan)
  └─ 키 존재? ─Y─→ create_broker_from_config() → broker.connect()
               │     → app.state.broker = broker
               N─→ app.state.broker = None
                     (status: no_credentials)

엔진 시작 (POST /api/strategy/start)
  └─ app.state.broker 있으면 재사용
     없으면 → create + connect (키 등록 후 첫 시작인 경우)
  └─ StrategyEngine(broker)
  └─ engine.start()

엔진 중지 (POST /api/strategy/stop)
  └─ engine.stop()
  └─ app.state.engine = None
  └─ broker는 유지 (disconnect 하지 않음)

서버 종료 (lifespan shutdown)
  └─ broker.disconnect()
```

### 단건 시세 조회 엔드포인트 (신규)

```
GET /api/quote/{symbol}
→ broker.get_quote(symbol)
→ { success, data: { symbol, price, volume, bid_price, ask_price, timestamp } }
```

엔진의 WS 시세 구독과 별도. 브로커 REST API로 단건 조회.

## API 변경

### 변경되는 엔드포인트

| 엔드포인트 | 변경 내용 |
|-----------|----------|
| `POST /api/strategy/start` | 신규 broker 생성 대신 `app.state.broker` 재사용. 없으면 생성 |
| `POST /api/strategy/stop` | `broker.disconnect()` 제거. 엔진만 정지 |
| `GET /api/account/balance` | 에러 메시지 변경: "전략 엔진을 먼저 시작하세요" → "브로커 미연결. 증권사 키를 확인하세요" |
| `GET /api/account/orders` | 동일 (에러 메시지 변경) |
| `GET /api/status` | broker 상태에 `reason` 필드 추가 |

### 신규 엔드포인트

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/api/quote/{symbol}` | GET | 단건 시세 조회 (브로커 REST) |
| `/api/broker/reconnect` | POST | 수동 재연결 (키 변경 후 등). **엔진 실행 중이면 409 거부** |

### reconnect 안전 규칙

- 엔진이 `app.state.broker`를 참조 중이므로, 엔진 실행 중 reconnect는 거부한다.
- 순서: 기존 broker `disconnect()` → 새 broker `create_broker_from_config()` → `connect()` → `app.state.broker` 교체
- 엔진 실행 중 호출 시: `409 Conflict` + `"엔진 실행 중에는 재연결할 수 없습니다. 먼저 중지하세요."` 반환

### status reason 값 목록

| reason | 의미 |
|--------|------|
| `connected` | 정상 연결 |
| `no_credentials` | 증권사 키 미등록 |
| `connect_failed` | 연결 시도 실패 (네트워크, 인증 등) |
| `token_expired` | 토큰 만료 (재발급 시도 중) |
| `disconnected` | 명시적 해제 또는 서버 종료 중 |

## 수용 기준

- [ ] 서버 시작 → 키 있으면 broker 자동 연결 (`GET /api/status`에서 `connected: true`)
- [ ] 엔진 미시작 상태에서 `GET /api/account/balance` → 잔고 반환
- [ ] 엔진 미시작 상태에서 `GET /api/account/orders` → 미체결 주문 반환
- [ ] `POST /api/strategy/start` → 기존 broker 재사용, 중복 연결 없음
- [ ] `POST /api/strategy/stop` → broker 연결 유지, 잔고 조회 계속 가능
- [ ] 키 없으면 서버 정상 시작, status에 `no_credentials` 표시
- [ ] `POST /api/broker/reconnect` → 키 변경 후 즉시 재연결
- [ ] `GET /api/quote/{symbol}` → 단건 시세 반환

## 범위

**포함**: 로컬 서버 브로커 생명주기 변경, account/trading 라우터 수정, 단건 시세 엔드포인트, status 응답 확장

**미포함**: 프론트엔드 UI 변경 (별도 spec), WS 시세 구독 (엔진 전용으로 유지), 멀티 브로커 동시 연결

## 참고

| 파일 | 역할 |
|------|------|
| `local_server/main.py` | lifespan — 브로커 자동 연결 추가 위치 |
| `local_server/broker/factory.py` | `create_broker_from_config()` — 기존 팩토리 재사용 |
| `local_server/routers/trading.py` | 엔진 시작/중지 — broker 생명주기 분리 |
| `local_server/routers/account.py` | `_get_broker()` — 이미 `app.state.broker` 참조 |
| `local_server/routers/status.py` | status 응답 확장 |
| `sv_core/broker/base.py` | `BrokerAdapter` ABC — `connect()`, `get_balance()`, `get_quote()` |
