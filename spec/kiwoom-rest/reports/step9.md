# Step 9 리포트: Reconciler

## 생성/수정된 파일
- `local_server/broker/kiwoom/reconciler.py`

## 주요 구현 내용

### ReconcileEvent
- event_type: MISMATCH / ORPHAN / GHOST
- ORPHAN: 로컬에만 있고 서버에 없음 (체결/취소로 가정)
- GHOST: 서버에만 있고 로컬에 없음 (외부 주문 감지)
- MISMATCH: 양쪽 모두 있지만 상태 불일치

### Reconciler
- `_local_orders: dict[str, OrderResult]` — 인메모리 주문 상태 저장소
- `register_order(order)`: place_order 성공 시 호출
- `update_order(order_id, new_status)`: 상태 갱신
- `remove_order(order_id)`: 체결/취소 완료 시 제거
- `reconcile_once()`: 단건 대사, 이벤트 반환
- `start()` / `stop()`: 주기적 대사 태스크 시작/중지

### 대사 정책
- 종결 상태(FILLED/CANCELLED/REJECTED) 주문은 서버 없어도 ORPHAN 처리 안 함
- ORPHAN은 FILLED로 간주하여 로컬 상태 갱신
- GHOST는 서버 상태로 로컬에 추가

## 리뷰에서 발견한 이슈 및 수정 사항
- 대사 도중 get_open_orders 실패 시 빈 리스트 반환 (데이터 삭제 방지)
- 콜백 예외가 루프를 중단시키지 않도록 처리

## 테스트 결과
- 구문 오류 없음

## 다음 Step과의 연결점
- Step 11 KiwoomAdapter.place_order()에서 reconciler.register_order() 호출
