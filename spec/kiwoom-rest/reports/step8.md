# Step 8 리포트: ReconnectManager

## 생성/수정된 파일
- `local_server/broker/kiwoom/reconnect.py`

## 주요 구현 내용

### ReconnectManager
- `on_state_change(old, new)`: StateMachine 콜백으로 등록, ERROR/DISCONNECTED 감지
- `_reconnect_loop()`: 지수 백오프 재시도 (initial_delay * multiplier^n, max_delay 상한)
- `enable()`/`disable()`: 의도적 종료 시 비활성화 (false-positive 재연결 방지)
- `_reset_backoff()`: 재연결 성공 후 카운터/딜레이 초기화

### 설정값
- 기본 초기 딜레이: 1초
- 기본 최대 딜레이: 60초
- 기본 배수: 2.0 (지수 증가)
- 기본 최대 재시도: 10회 (0=무제한)

### ConnectFn 타입
- `Callable[[], Awaitable[None]]` — KiwoomAdapter._do_connect 등 주입

## 리뷰에서 발견한 이슈 및 수정 사항
- 재연결 태스크 중복 실행 방지: `_reconnect_task.done()` 확인
- disable() 호출 시 진행 중인 태스크 취소

## 테스트 결과
- 구문 오류 없음

## 다음 Step과의 연결점
- Step 11 KiwoomAdapter에서 StateMachine.on_change()에 ReconnectManager.on_state_change 등록
