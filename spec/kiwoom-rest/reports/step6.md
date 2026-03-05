# Step 6 리포트: KiwoomWS

## 생성/수정된 파일
- `local_server/broker/kiwoom/ws.py`

## 주요 구현 내용

### KiwoomWS
- `connect()`: websockets.connect() 로 WS 연결, _recv_loop 태스크 시작
- `disconnect()`: 태스크 취소 → ws.close() → 구독 목록 초기화
- `subscribe(symbols)`: 종목별 구독 메시지 전송 (tr_type="1")
- `unsubscribe(symbols)`: 구독 해제 메시지 전송 (tr_type="2")
- `_recv_loop()`: async for 메시지 수신, ConnectionClosed 처리
- `_handle_message()`: PINGPONG 필터링, JSON/비JSON 분기
- `_handle_realtime_data()`: "|" 구분 체결 데이터 파싱 → QuoteEvent 생성

### 메시지 형식
- 구독 요청: JSON (header + body)
- 수신 데이터: "H0STCNT0|종목코드|필드수|^구분필드..."
- 주요 필드 인덱스: [10]=현재가, [12]=누적거래량, [7]=매도호가, [8]=매수호가

### 콜백 등록
- `add_callback(fn)`: 동기 함수 등록 가능

## 리뷰에서 발견한 이슈 및 수정 사항
- websockets를 optional import로 처리 (ImportError시 명확한 에러)
- 콜백 내부 예외가 수신 루프를 중단시키지 않도록 try/except 처리
- 배열 bounds 체크로 파싱 실패 방지

## 테스트 결과
- 구문 오류 없음

## 다음 Step과의 연결점
- Step 7 StateMachine에서 WS 연결 상태를 추적
- Step 8 ReconnectManager에서 연결 끊김 시 KiwoomWS.connect() 재호출
