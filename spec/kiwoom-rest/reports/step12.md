# Step 12 리포트: MockAdapter

## 생성/수정된 파일
- `local_server/broker/mock/__init__.py`
- `local_server/broker/mock/adapter.py`

## 주요 구현 내용

### MockAdapter(BrokerAdapter)
9개 추상 메서드 완전 구현:

**잔고**: `_cash` + `_positions` 인메모리 관리
- get_balance(): 현재가 * 수량으로 실시간 평가

**시세**: `_prices` 딕셔너리 (기본값 포함)
- get_quote(): 고정 가격 반환
- subscribe_quotes(): 콜백 등록만 (실시간 없음)

**주문**: 즉시 체결 처리
- place_order(): 매수 → 잔고 차감 + 포지션 증가, 매도 → 포지션 감소 + 잔고 증가
- cancel_order(): SUBMITTED 상태 주문만 취소 가능
- get_open_orders(): SUBMITTED 상태 주문만 반환 (즉시 체결이라 보통 빈 리스트)

### 테스트 유틸
- `set_price(symbol, price)`: 가격 조작
- `reset(initial_cash)`: 상태 완전 초기화
- `fire_quote_event(event)`: 수동 시세 이벤트 발생

### 포지션 관리
- `_apply_buy()`: 평균 단가 재계산 (기존 포지션 + 신규)
- `_apply_sell()`: 수량 차감, 0이하면 포지션 제거

## 리뷰에서 발견한 이슈 및 수정 사항
- 매도 잔고 초과 검사 추가 (ValueError)
- 현금 부족 검사 추가 (ValueError)

## 테스트 결과
- 구문 오류 없음
- Step 13에서 전체 시나리오 테스트 수행

## 다음 Step과의 연결점
- Step 13 테스트에서 MockAdapter를 기본 어댑터로 사용
