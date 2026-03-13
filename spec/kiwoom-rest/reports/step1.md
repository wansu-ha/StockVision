# Step 1 리포트: sv_core 공유 패키지

## 생성/수정된 파일
- `sv_core/__init__.py` — 패키지 진입점
- `sv_core/broker/__init__.py` — 브로커 서브패키지, 공개 심볼 재내보내기
- `sv_core/broker/models.py` — 공통 데이터 모델
- `sv_core/broker/base.py` — BrokerAdapter ABC

## 주요 구현 내용

### models.py
- `OrderSide`: BUY/SELL enum
- `OrderType`: MARKET/LIMIT enum
- `OrderStatus`: NEW/SUBMITTED/PARTIAL_FILLED/FILLED/CANCELLED/REJECTED enum
- `ErrorCategory`: TRANSIENT/PERMANENT/RATE_LIMIT/AUTH/UNKNOWN enum
- `OrderResult`: 주문 결과 dataclass (order_id, client_order_id, symbol, side, qty 등)
- `BalanceResult`: 잔고 dataclass (cash, total_eval, positions)
- `Position`: 포지션 dataclass (symbol, qty, avg_price, unrealized_pnl 등)
- `QuoteEvent`: 시세 이벤트 dataclass (symbol, price, volume, bid/ask)

### base.py
- `BrokerAdapter(ABC)` — 9개 추상 메서드:
  - `connect()`, `disconnect()`, `is_connected` (라이프사이클)
  - `get_balance()` (잔고 조회)
  - `get_quote()`, `subscribe_quotes()`, `unsubscribe_quotes()` (시세)
  - `place_order()`, `cancel_order()`, `get_open_orders()` (주문)

## 리뷰에서 발견한 이슈 및 수정 사항
- `Decimal` 사용으로 부동소수점 정밀도 문제 방지
- `client_order_id` 필드 추가 (멱등성 보장, Step 10 IdempotencyGuard 연동)
- `raw: dict` 필드로 원본 응답 보존 (디버깅 용이)

## 테스트 결과
- 타입 힌트 검증: 완료 (Python 3.13 호환)
- import 체인 검증: `sv_core.broker` → `base`, `models` 정상

## 다음 Step과의 연결점
- Step 2 KiwoomAuth는 `httpx.AsyncClient` 기반으로 구현, sv_core 의존 없음
- Step 11 KiwoomAdapter가 `BrokerAdapter` 구현체로 연결됨
