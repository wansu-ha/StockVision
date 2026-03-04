# execution-log 구현 보고서

> 작성일: 2026-03-04 | 커밋 대기

## 생성/수정 파일 목록

| 파일 | 내용 |
|------|------|
| `local_server/storage/log_db.py` | 스키마 확장 + `log_fill()` + `query_logs()` 필터 + `query_summary_today()` |
| `local_server/routers/logs.py` | `GET /api/logs`, `GET /api/logs/summary` |
| `local_server/main.py` | `init_db()` lifespan 호출 + logs 라우터 등록 |
| `frontend/src/services/logs.ts` | 로컬 서버 API 클라이언트 |
| `frontend/src/pages/ExecutionLog.tsx` | 실행 로그 UI (요약 카드, 날짜 필터, 테이블, 조건 스냅샷 토글) |
| `frontend/src/App.tsx` | `/logs` 라우트 추가 |

## 주요 기능

### 로그 DB
- `log_execution()`: SENT 로그 INSERT (signal.py에서 호출)
- `log_fill()`: 체결 시 filled_price/filled_qty UPDATE + status='FILLED' (com_client 체결 콜백에서 호출)
- 마이그레이션: 구버전 컬럼(symbol, order_no 등) ALTER TABLE ADD COLUMN으로 안전하게 추가

### API
- `GET /api/logs` — rule_id, date_from, date_to, limit, offset 파라미터
- `GET /api/logs/summary` — 오늘 날짜 기준 total/filled/failed 카운트

### React UI
- 오늘 실행 요약 카드 3개 (전체 / 체결 / 오류)
- 날짜 범위 필터
- 10초 폴링 자동 갱신
- 조건 스냅샷 토글 (JSON 파싱 → key=value 표시)
- 상태 배지 색상: 체결(green), 전송(blue), 스킵(gray), 오류(red)

## 비고
- `log_fill()` 자동 호출은 com_client.on_receive_chejan_data()에서 order_no 기반 연결 필요 (추후 보완)
- WS push 방식 갱신은 `execution_result` 이벤트 수신 시 React Query invalidate로 구현 예정
