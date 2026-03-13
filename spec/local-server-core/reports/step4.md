# Step 4 보고서: WebSocket 엔드포인트

## 생성/수정된 파일

- `local_server/routers/ws.py` — WS /ws 엔드포인트

## 구현 내용 요약

### ConnectionManager 클래스
- connect(): WebSocket 수락 후 목록 추가
- disconnect(): 목록 제거
- broadcast(): 모든 클라이언트에 JSON 전송, 실패 클라이언트 자동 제거
- connection_count(): 현재 연결 수

### websocket_endpoint 함수
- WS /ws 경로
- 연결 즉시 system 타입 welcome 메시지 전송
- 60초 타임아웃으로 receive_text() 대기
- ping/pong 처리
- WebSocketDisconnect 예외로 정상 해제 처리
- 전역 manager를 get_connection_manager()로 외부 접근 가능

### 메시지 형식
```json
{
  "type": "price" | "order" | "balance" | "system" | "ping" | "pong",
  "data": { ... }
}
```

## 리뷰 발견 사항

- broadcast()에서 전송 실패 클라이언트를 collect 후 일괄 제거 (반복 중 목록 수정 방지)
- 60초 무활동 시 서버에서 ping 전송 (연결 유지 목적)
- 전략 엔진 이벤트는 Unit 3에서 manager.broadcast()를 호출하는 방식으로 확장

## 테스트 결과

- 문법 검증: 정상
- ConnectionManager 단위 테스트는 test_routers.py에서 수행
