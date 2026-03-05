# P0 수정 보고서 — Unit 2 (local_server) API 계약 + WS 타입 + sv_core 정합성

날짜: 2026-03-05
대상 워크트리: `d:/Projects/StockVision/.claude/worktrees/agent-a643a319/`

---

## 수정 항목 요약

| ID  | 파일                                      | 내용                                         | 상태 |
|-----|-------------------------------------------|----------------------------------------------|------|
| A1  | `local_server/routers/auth.py`            | `/api/auth/token` 용도 수정 — 클라우드 JWT 등록 | 완료 |
| A2  | `local_server/routers/config.py`          | `POST /api/config/kiwoom` 엔드포인트 추가     | 완료 |
| A3  | `local_server/routers/trading.py`         | `POST /api/strategy/kill` 엔드포인트 추가     | 완료 |
| A4  | `local_server/routers/trading.py`         | `POST /api/strategy/unlock` 엔드포인트 추가   | 완료 |
| W1  | `local_server/routers/ws.py`              | WS 메시지 타입명 수정 + 상수 추가             | 완료 |
| S1  | `sv_core/broker/base.py`                  | BrokerAdapter ABC 정본 인터페이스에 맞게 재작성 | 완료 |
| S2  | `local_server/storage/credential.py`      | 클라우드 JWT / 계좌번호 키 상수 및 헬퍼 추가  | 완료 |

---

## A1 — `POST /api/auth/token` 용도 수정

**파일**: `local_server/routers/auth.py`

### 변경 전
- 요청 바디: `{ app_key, app_secret }` (키움 API Key 저장 용도)
- `TokenRequest` 모델 사용
- 키움 API Key를 keyring에 저장 후 더미 토큰 반환

### 변경 후
- 요청 바디: `{ access_token, refresh_token }` (클라우드 JWT 전달 용도)
- `CloudTokenRequest` 모델 사용
- 클라우드 JWT 쌍을 keyring에 `sv_cloud_access_token`, `sv_cloud_refresh_token`으로 저장
- `GET /api/auth/status` 도 클라우드 토큰 존재 여부를 반환하도록 업데이트

---

## A2 — `POST /api/config/kiwoom` 추가

**파일**: `local_server/routers/config.py`

### 추가 내용
```
POST /api/config/kiwoom
요청: { app_key: str, app_secret: str, account_no: str }
응답: { success, data: { message, has_key }, count }
```
- 키움 앱 키, 앱 시크릿 → `credential.save_api_keys()`
- 계좌번호 → `credential.save_account_no()`
- 저장 실패 시 500 반환

---

## A3 — `POST /api/strategy/kill` 추가

**파일**: `local_server/routers/trading.py`

### 추가 내용
```
POST /api/strategy/kill
요청: { mode: "STOP_NEW" | "CANCEL_OPEN" }
```
- `STOP_NEW`: 전략 엔진 중지 상태 전환. 미체결 주문 유지.
- `CANCEL_OPEN`: 전략 엔진 중지 + 미체결 전량 취소 (Unit 1 BrokerAdapter.cancel_order() 연동 전까지 stub).

---

## A4 — `POST /api/strategy/unlock` 추가

**파일**: `local_server/routers/trading.py`

### 추가 내용
```
POST /api/strategy/unlock
요청: 없음
응답: { success, data: { message }, count }
```
- 손실 한도 초과로 잠긴 전략 엔진 락 해제
- 해제 후 재시작은 `/api/strategy/start` 별도 호출 필요
- Unit 3 손실 락 상태 관리 연동 전까지 log 기록만 수행

---

## W1 — WS 메시지 타입명 수정

**파일**: `local_server/routers/ws.py`

### 변경 내용

| 구 타입명 | 신 타입명      |
|-----------|----------------|
| `quote`   | `price_update` |
| `fill`    | `execution`    |
| `status`  | `status_change`|

- side 값 규칙 명문화: `buy` / `sell` (소문자)
- 모듈 레벨 상수 추가:
  ```python
  WS_TYPE_PRICE_UPDATE = "price_update"
  WS_TYPE_EXECUTION = "execution"
  WS_TYPE_STATUS_CHANGE = "status_change"
  ```
- 다른 모듈이 브로드캐스트 시 이 상수를 `import`하여 사용

---

## S1 — `sv_core/broker/base.py` 정본 인터페이스로 재작성

**파일**: `sv_core/broker/base.py`

### 메서드 매핑

| 구 stub               | 정본 (Unit 1 ABC)                              |
|-----------------------|------------------------------------------------|
| `authenticate()`      | `connect() -> None`                            |
| `is_authenticated()`  | `is_connected: bool` (property)                |
| `send_order(**kwargs)`| `place_order(client_order_id, symbol, side, order_type, qty, limit_price) -> OrderResult` |
| `get_current_price()` | `get_quote(symbol) -> QuoteEvent`              |
| `subscribe()`         | `subscribe_quotes(symbols, callback) -> None`  |
| `unsubscribe()`       | `unsubscribe_quotes(symbols) -> None`          |
| `listen()`            | 제거 (callback 패턴으로 대체)                  |
| `get_positions()`     | 제거 (`get_balance()`의 `positions` 필드로 통합)|
| (없음)                | `get_open_orders() -> list[OrderResult]` 추가  |
| `cancel_order()`      | `cancel_order(order_id) -> OrderResult` (시그니처 수정) |

### 모델 stub 추가
- `QuoteEvent`, `BalanceResult`, `OrderResult`, `Position` 클래스를 `base.py`에 인라인 정의
- Unit 1이 `sv_core.broker.models`를 정식 제공하면 이 stub을 import로 대체

---

## S2 — `credential.py` — 키 상수 및 헬퍼 추가

**파일**: `local_server/storage/credential.py`

### 추가된 상수
```python
KEY_ACCOUNT_NO = "kiwoom_account_no"
KEY_CLOUD_ACCESS_TOKEN = "sv_cloud_access_token"
KEY_CLOUD_REFRESH_TOKEN = "sv_cloud_refresh_token"
```

### 추가된 함수
```python
save_cloud_tokens(access_token, refresh_token) -> None
load_cloud_tokens() -> tuple[str | None, str | None]
save_account_no(account_no) -> None
load_account_no() -> str | None
```

### `clear_all_credentials()` 업데이트
- 새 키 3개(account_no, cloud_access_token, cloud_refresh_token)도 포함하여 삭제

---

## 연쇄 수정 (stale 참조 정리)

- `trading.py` L184: `BrokerAdapter.send_order()` → `BrokerAdapter.place_order()` 로 TODO 주석 수정
- `auth.py` 전체 재작성으로 구 `KEY_APP_KEY`, `save_api_keys` import 제거, 클라우드 토큰 import로 교체
