# kiwoom-integration 구현 보고서

> 작성일: 2026-03-04 | 커밋 대기

## 생성/수정 파일 목록

| 파일 | 내용 |
|------|------|
| `local_server/kiwoom/com_client.py` | COM 래퍼 (CommConnect, TR 조회, SendOrder, 체결 이벤트) |
| `local_server/kiwoom/fid_map.py` | CHEJAN_FID / BALANCE_FID 매핑 |
| `local_server/kiwoom/account.py` | 예수금(opw00001), 보유잔고(opw00018) TR 조회 |
| `local_server/kiwoom/order.py` | asyncio.Queue FIFO + 200ms 간격 주문 큐 |
| `local_server/kiwoom/session.py` | 연결/재연결(지수 백오프) + 단절 감지 + 알림 |
| `local_server/engine/scheduler.py` | `set_scheduler()` / `get_scheduler()` 싱글톤 추가 |
| `local_server/main.py` | `set_scheduler()` 등록 추가 |
| `local_server/routers/kiwoom.py` | `/api/kiwoom/account` 실제 잔고 조회로 교체 |

## 주요 설계

### COM 연결 흐름
```
HTS 로그인(사용자) → session.connect() → KiwoomCOMClient.connect()
                                         → win32com.Dispatch + CommConnect
```

### 재연결 정책
- 단절 감지: `status()` 호출 시 `GetConnectState()` 비교
- 백오프: 5s → 10s → 15s (최대 3회)
- 실패 시: 트레이 알림 + 스케줄러 pause + WS 브로드캐스트

### 주문 큐
- `asyncio.Queue` FIFO, 200ms 간격 (초당 5건 API 제한 준수)
- BUY/SELL → `SendOrder()` order_type 1/2

### TR 조회 (동기 방식)
- `comm_rq_data()` + `time.sleep(0.2)` + `get_comm_data()`
- 키움 TR은 이벤트 콜백 기반이나, COM 동기 호출로 단순화

## 비고
- `pywin32` 미설치 환경 (macOS/Linux): try/except로 graceful fallback
- 계좌 비밀번호: 빈 문자열 전달 (HTS에서 이미 인증된 세션 사용)
- execution-engine spec에서 evaluator → order.enqueue() 연결 예정
