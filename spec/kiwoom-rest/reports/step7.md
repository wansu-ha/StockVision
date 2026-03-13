# Step 7 리포트: StateMachine

## 생성/수정된 파일
- `local_server/broker/kiwoom/state_machine.py`

## 주요 구현 내용

### ConnectionState
DISCONNECTED → CONNECTING → CONNECTED → AUTHENTICATED → SUBSCRIBED
각 상태에서 ERROR, DISCONNECTED로 전환 가능

### StateMachine
- `VALID_TRANSITIONS`: 딕셔너리로 유효 전환 관계 정의
- `transition(new_state)`: 유효성 검사 후 상태 전환, 콜백 호출
- `on_change(callback)`: (old, new) 상태 변경 콜백 등록
- `is_operational()`: AUTHENTICATED 또는 SUBSCRIBED 상태인지 확인
- `reset()`: 강제 DISCONNECTED 초기화 (비상 복구용)
- asyncio.Lock으로 동시 전환 방지

### InvalidStateTransitionError
- 유효하지 않은 전환 시 명확한 에러 메시지 포함

## 리뷰에서 발견한 이슈 및 수정 사항
- 콜백 호출을 Lock 밖에서 실행 (데드락 방지)
- ERROR 상태에서 CONNECTING 직접 전환 가능 (재연결 지원)

## 테스트 결과
- 구문 오류 없음

## 다음 Step과의 연결점
- Step 8 ReconnectManager가 StateMachine 상태 변경 콜백으로 ERROR 감지 후 재연결 시도
