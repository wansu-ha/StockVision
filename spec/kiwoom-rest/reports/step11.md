# Step 11 리포트: KiwoomAdapter

## 생성/수정된 파일
- `local_server/broker/kiwoom/adapter.py`

## 주요 구현 내용

### KiwoomAdapter(BrokerAdapter)
모든 kiwoom 모듈을 조합하여 BrokerAdapter ABC 9개 메서드를 구현:

**라이프사이클**
- `connect()`: StateMachine CONNECTING → _do_connect()
- `_do_connect()`: 토큰 발급 → AUTHENTICATED → WS 연결 → SUBSCRIBED → Reconciler 시작
- `disconnect()`: ReconnectManager 비활성화 → Reconciler 중지 → WS 종료 → 상태 리셋

**잔고/시세**
- `get_balance()`: rate_limiter.acquire("balance") → quote_client.get_balance()
- `get_quote()`: rate_limiter.acquire("quote") → quote_client.get_price()
- `subscribe_quotes()`: ws.add_callback() → ws.subscribe()

**주문**
- `place_order()`: 멱등성 체크 → rate_limiter → order_client.place_order() → 등록
- `cancel_order()`: local_orders에서 symbol/qty 조회 → order_client.cancel_order()
- `get_open_orders()`: rate_limiter → order_client.get_open_orders()

**오류 처리**
- 주문 실패 시 ErrorClassifier로 분류
- AUTH 에러면 auth.invalidate() 호출 (다음 요청 시 재발급)

### 조합 구조
```
KiwoomAdapter
├── KiwoomAuth         (인증)
├── KiwoomQuote        (시세/잔고 REST)
├── KiwoomOrder        (주문 REST)
├── KiwoomWS           (실시간 WebSocket)
├── MultiEndpointRateLimiter (속도 제한)
├── StateMachine       (연결 상태)
├── IdempotencyGuard   (중복 방지)
├── ErrorClassifier    (에러 분류)
├── Reconciler         (대사)
└── ReconnectManager   (자동 재연결)
```

## 리뷰에서 발견한 이슈 및 수정 사항
- cancel_order에서 reconciler._local_orders 직접 접근: 내부 구현 노출 — 향후 Reconciler에 get_order(id) 메서드 추가 권장 (현재는 단순화)
- _do_connect는 CONNECTING 상태에서만 호출되어야 하나, ReconnectManager는 ERROR에서도 재호출함 → StateMachine.reset()을 통해 처리

## 테스트 결과
- 구문 오류 없음

## 다음 Step과의 연결점
- Step 12 MockAdapter는 동일 인터페이스를 메모리로 구현
- Step 13 AdapterFactory에서 환경변수로 선택
