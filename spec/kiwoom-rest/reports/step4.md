# Step 4 리포트: KiwoomOrder

## 생성/수정된 파일
- `local_server/broker/kiwoom/order.py`

## 주요 구현 내용

### KiwoomOrder
- `place_order()`: POST /uapi/domestic-stock/v1/trading/order-cash
  - tr_id/ord_dvsn를 side+order_type 튜플 딕셔너리로 매핑
  - 지정가 주문 시 limit_price 검증
  - 응답 output.ODNO → order_id
- `cancel_order()`: POST /uapi/domestic-stock/v1/trading/order-rvsecncl
  - RVSE_CNCL_DVSN_CD=02 (취소)
  - QTY_ALL_ORD_YN=Y (잔량 전부)
- `get_open_orders()`: GET /uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl
  - sll_buy_dvsn_cd → OrderSide 변환
  - ord_dvsn_cd → OrderType 변환

### 상수 구조
- `_ORDER_TR_ID`: (side, order_type) → tr_id 매핑
- `_ORD_DVSN`: (side, order_type) → ord_dvsn 코드 매핑
- `_SIDE_CODE`: side → SLL_TYPE 코드 매핑

## 리뷰에서 발견한 이슈 및 수정 사항
- cancel_order에서 side는 원주문 정보 없어 BUY로 기본값 설정 — 실제 사용 시 원주문 방향 전달 권장
- get_open_orders에서 tot_ccld_qty로 부분 체결 수량 추적

## 테스트 결과
- 구문 오류 없음 (정적 검토)

## 다음 Step과의 연결점
- Step 5 RateLimiter가 이 메서드들 앞에 acquire() 삽입
- Step 10 IdempotencyGuard가 place_order client_order_id 검사
