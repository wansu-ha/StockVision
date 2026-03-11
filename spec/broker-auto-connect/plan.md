> 작성일: 2026-03-11 | 상태: 구현 완료 | spec: broker-auto-connect

# broker-auto-connect 구현 계획

## 현재 상태 요약

### 브로커 생명주기 (변경 전)
- 브로커는 `POST /api/strategy/start`에서 생성·연결되고,
  `POST /api/strategy/stop`에서 `disconnect()` 후 `app.state.broker = None`으로 소멸
- `local_server/main.py` lifespan에는 브로커 관련 코드 없음
- 결과: 엔진 미시작 시 계좌 조회 불가

### account.py 구조
- `_get_broker()`가 이미 `app.state.broker`를 참조하는 구조
- 에러 메시지만 변경하면 됨

### status.py 버그
- `"has_credentials": has_credential(KEY_CLOUD_ACCESS_TOKEN)` — 클라우드 토큰을 보고 있음 (잘못됨)
- `reason` 필드 없음

### BrokerAdapter.get_quote() 반환 타입
- `QuoteEvent` 필드: `symbol`, `price`, `volume`, `bid_price`, `ask_price`, `timestamp`
- 스펙의 `change`, `change_pct`는 QuoteEvent에 없음 → 응답에서 제외

### create_broker_from_config()
- 키 미등록 시 `ValueError` raise — lifespan에서 try/except로 처리

## 구현 단계

### Step 1: lifespan에 브로커 자동 연결 추가
- 변경 파일: `local_server/main.py`
- 변경 내용:
  - lifespan `yield` 이전에 브로커 자동 연결 로직 추가 (하트비트 코드 다음)
  - `app.state.broker = None`, `app.state.broker_reason = "disconnected"` 초기화
  - try/except로 `create_broker_from_config()` + `broker.connect()` 실행
  - `ValueError` → `broker_reason = "no_credentials"` (키 미등록, 정상)
  - 기타 예외 → `broker_reason = "connect_failed"`
  - lifespan 종료 훅(`yield` 이후)에 `broker.disconnect()` 추가
- 검증: 키 있는 환경에서 서버 시작 → `GET /api/status` → `broker.connected: true`

### Step 2: trading.py — 브로커 생명주기 분리
- 변경 파일: `local_server/routers/trading.py`
- 변경 내용:
  - `stop_strategy()`: broker disconnect + `app.state.broker = None` 블록 제거. 엔진만 정지
  - `start_strategy()`: `app.state.broker` 존재하면 재사용, 없으면 새로 생성+연결
- 검증: start → stop → `GET /api/account/balance` → 잔고 정상 반환

### Step 3: account.py — 에러 메시지 수정
- 변경 파일: `local_server/routers/account.py`
- 변경 내용: `_get_broker()` 에러 메시지 "전략 엔진을 먼저 시작하세요" → "브로커 미연결. 증권사 키를 확인하세요."
- 검증: 브로커 미연결 시 새 메시지 확인

### Step 4: status.py — reason 필드 + has_credentials 버그 수정
- 변경 파일: `local_server/routers/status.py`
- 변경 내용:
  - `broker.reason` 필드 추가 (`app.state.broker_reason` 읽기)
  - `has_credentials` 수정: `KEY_CLOUD_ACCESS_TOKEN` → 실제 broker type에 맞는 키 확인
- 검증: `GET /api/status` 응답에 `broker.reason` 존재, `has_credentials` 정확

### Step 5: quote.py — 단건 시세 라우터 (신규)
- 변경 파일: `local_server/routers/quote.py` (신규)
- 변경 내용: `GET /api/quote/{symbol}` → `broker.get_quote(symbol)` → QuoteEvent 기반 응답
- 검증: `GET /api/quote/005930` → 현재가 반환

### Step 6: broker.py — reconnect 라우터 (신규)
- 변경 파일: `local_server/routers/broker.py` (신규)
- 변경 내용:
  - `POST /api/broker/reconnect` — 기존 broker disconnect → 새 broker 생성+연결
  - 엔진 실행 중이면 `409 Conflict` 반환
- 검증: 엔진 미실행 시 200, 엔진 실행 중 409

### Step 7: main.py에 신규 라우터 등록
- 변경 파일: `local_server/main.py`
- 변경 내용: `quote.router` (prefix `/api/quote`), `broker_router.router` (prefix `/api/broker`) 등록
- 검증: `/docs`에서 엔드포인트 확인

## 변경 파일 목록

| 파일 | 변경 유형 | 주요 내용 |
|------|---------|---------|
| `local_server/main.py` | 수정 | lifespan 자동 연결 + 종료 disconnect + 라우터 등록 |
| `local_server/routers/trading.py` | 수정 | start 브로커 재사용, stop disconnect 제거 |
| `local_server/routers/account.py` | 수정 | 에러 메시지 변경 |
| `local_server/routers/status.py` | 수정 | reason 필드 + has_credentials 버그 수정 |
| `local_server/routers/quote.py` | 신규 | GET /api/quote/{symbol} |
| `local_server/routers/broker.py` | 신규 | POST /api/broker/reconnect |

## 구현 순서

Step 1 → 2 → 7이 핵심 (lifespan + stop 수정 + 라우터 등록). Step 3~6은 독립적.

## 프론트엔드 연동 (이 plan 범위 밖, 참고용)

백엔드 완료 후 프론트엔드에서 필요한 작업:
- `localClient.ts`에 `localBroker.reconnect()` 함수 추가
- `Settings.tsx`의 `handleSaveKeys` 성공 후 `POST /api/broker/reconnect` 호출 (spec F8)
- `useAccountStatus`의 `LocalStatusData.broker` 타입에 `reason?: string` 추가
- 키 미등록 시 계좌 카드에 설정 페이지 유도 CTA 추가

위 항목은 frontend-ux-v2 plan에서 함께 처리.

## 주의사항

- F7 (자동 재시도 30초 3회)은 이 plan에서 제외. 서버 재시작이나 reconnect로 대체 가능
- QuoteEvent에 `change`, `change_pct` 없음 — 응답에서 제외 (스펙도 수정 완료)
- `trading.py`의 `place_order()` 에러 메시지도 수정하면 일관적이지만 스펙 범위 외
