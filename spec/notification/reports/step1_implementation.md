# notification 구현 보고서

> 작성일: 2026-03-04 | 커밋 대기

## 생성/수정 파일 목록

| 파일 | 내용 |
|------|------|
| `frontend/src/hooks/useLocalBridgeWS.ts` | WS 훅 + useNotifStore (Zustand) |
| `frontend/src/components/NotificationCenter.tsx` | 벨 아이콘 + 읽지않음 배지 + 드롭다운 |
| `frontend/src/components/Layout.tsx` | WS 훅 호출 + NotificationCenter + 새 nav 링크 |
| `local_server/kiwoom/com_client.py` | 체결 시 트레이 알림 + log_fill 호출 |
| `local_server/cloud/email_reporter.py` | 일일 실행 요약 이메일 발송 |
| `local_server/engine/scheduler.py` | 16:00 KST 이메일 리포트 트리거 |

## 주요 기능

### WS 알림 훅
- `useLocalBridgeWS`: `ws://127.0.0.1:8765/ws` 연결, 재시도 3회 지수 백오프
- 처리 이벤트: `signal_sent`, `execution_result`, `kiwoom_disconnected`, `alert`
- `useNotifStore`: Zustand 스토어, items(max 50) / unread 카운트 / markAllRead

### NotificationCenter
- 벨 아이콘 + 빨간 배지(읽지 않은 수, 9+ 초과 시 '9+')
- 드롭다운: 최근 50개, 타입별 색상(error=red, success=green)
- 열 때 markAllRead 자동 호출

### Layout 변경
- `useLocalBridgeWS()` 훅을 Layout에서 호출 → 앱 전역 WS 연결
- nav 링크 추가: 전략(/strategy), 포트폴리오(/portfolio), 실행 로그(/logs)

### 체결 알림 (com_client)
- `on_receive_chejan_data()`: 체결 이벤트 시 트레이 알림 + `log_fill()` 호출
- order_no 기반으로 execution_logs 레코드 업데이트

### 이메일 리포트
- `cloud/email_reporter.py`: `send_daily_summary(jwt)` — 오늘 실행 요약(total/filled/failed) → 클라우드 `/api/notify/email` POST
- 실행 건수 0이면 이메일 스킵
- scheduler 16:00~16:01 KST 창에 1회 발송, `_email_reported` 플래그로 중복 방지

## 스케줄러 트리거 요약

| 시각 (KST) | 동작 |
|-----------|------|
| 09:00~15:30 | 1분 주기 규칙 평가 (`_tick`) |
| 15:35~15:36 | 컨텍스트 갱신 (`_refresh_context`) |
| 16:00~16:01 | 이메일 리포트 발송 (`_send_email_report`) |
