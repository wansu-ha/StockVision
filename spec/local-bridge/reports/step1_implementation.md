# local-bridge 구현 보고서

> 작성일: 2026-03-04 | 커밋 대기

## 생성 파일 목록

| 파일 | 내용 |
|------|------|
| `local_server/main.py` | FastAPI app, lifespan (자동시작 + 스케줄러) |
| `local_server/requirements.txt` | 의존 패키지 목록 |
| `local_server/tray.py` | Windows 시스템 트레이 (pystray) |
| `local_server/routers/health.py` | GET /api/health |
| `local_server/routers/ws.py` | WebSocket /ws (broadcast, 메시지 핸들러) |
| `local_server/routers/config.py` | GET/PATCH /api/config, POST /api/config/unlock |
| `local_server/routers/kiwoom.py` | GET /api/kiwoom/status, /api/kiwoom/account |
| `local_server/routers/trading.py` | POST /api/strategy/start|stop |
| `local_server/engine/scheduler.py` | 1분 주기 장시간 평가 루프 |
| `local_server/engine/evaluator.py` | 규칙 평가 (스텁, execution-engine에서 완성) |
| `local_server/engine/signal.py` | 신호 전송 (스텁) |
| `local_server/kiwoom/session.py` | 키움 COM 연결 상태 관리 |
| `local_server/storage/config_manager.py` | 메모리 설정 + 500ms debounce 클라우드 업로드 |
| `local_server/storage/log_db.py` | logs.db SQLite (execution-log에서 확장) |
| `local_server/cloud/context.py` | 시장 컨텍스트 fetch + 5분 캐시 |
| `local_server/cloud/heartbeat.py` | 5분 주기 익명 하트비트 |

## 스텁 처리 항목 (후속 spec에서 완성)
- `engine/evaluator.py` → execution-engine spec
- `engine/signal.py` → execution-engine spec
- `kiwoom/session.py` COM 연결 → kiwoom-integration spec
- `storage/log_db.py` 확장 → execution-log spec

## 포트
- 로컬 서버: `127.0.0.1:8765`
- React 개발: `localhost:5173`
