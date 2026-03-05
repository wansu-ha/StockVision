# 키움 API 연동 명세서 (kiwoom-integration) v2

> 작성일: 2026-03-04 | 상태: v2 개정 | 담당: 로컬 브릿지 아키텍처
>
> **v2 변경 사유**: v1은 pywin32 직접 COM 래핑 방식이었으나,
> 분석 결과 이벤트 루프 미구현·동기 sleep 패턴 등 **동작 불가** 판정.
> pykiwoom 기반 32bit 서브프로세스 분리 아키텍처로 전면 개정.

---

## 1. 목표

영웅문 HTS에 로그인만 되어 있으면, 로컬 서버가 **pykiwoom**을 통해
키움 OpenAPI+ COM 세션에 연결하여 주문·잔고·체결 조회를 수행한다.

**해결하는 문제:**
- 현재 `local_server/kiwoom/` 코드가 COM 이벤트 루프 없이 작성되어 동작 불가
- 64bit Python(FastAPI) + 32bit COM(키움 OCX) 아키텍처 충돌
- 연결 상태를 사용자가 실시간으로 확인할 수단 부재

---

## 2. 아키텍처

### 2.1 프로세스 분리 구조

```
┌─────────────────────────────────────────┐
│  local_server/main.py (64bit Python)    │
│  FastAPI + asyncio (localhost:8765)      │
│  ├── routers/ (REST + WS)               │
│  ├── engine/ (스케줄러, 평가)            │
│  └── kiwoom/bridge.py  ← IPC 클라이언트 │
└───────────┬─────────────────────────────┘
            │ multiprocessing.Queue (양방향)
            │   CMD Queue: 명령 (connect, order, balance, ...)
            │   EVT Queue: 이벤트 (connected, fill, balance_result, ...)
┌───────────┴─────────────────────────────┐
│  kiwoom_worker.py (32bit Python 3.10)   │
│  pykiwoom + PyQt5 + pythoncom           │
│  ├── Kiwoom 인스턴스                     │
│  ├── COM 메시지 루프                     │
│  └── 체결/잔고 이벤트 → EVT Queue 전달   │
└───────────┬─────────────────────────────┘
            │ COM/OCX
┌───────────┴─────────────────────────────┐
│  영웅문 HTS (로그인 상태)                │
│  키움 OpenAPI+ OCX                      │
└─────────────────────────────────────────┘
```

### 2.2 왜 프로세스 분리인가

| 제약 | 원인 |
|------|------|
| 32bit Python 필수 | 키움 OCX가 32bit COM 컴포넌트 |
| 64bit Python 필수 | FastAPI + 대부분 pip 패키지가 64bit |
| COM 메시지 루프 | `pythoncom.PumpWaitingMessages()` 가 asyncio와 충돌 |

→ **별도 32bit 프로세스** + `multiprocessing.Queue` IPC가 유일한 해법.

### 2.3 IPC 프로토콜 (Queue 메시지)

**CMD Queue (64bit → 32bit):**

```python
# 연결
{"cmd": "connect"}

# 연결 해제
{"cmd": "disconnect"}

# 잔고 조회
{"cmd": "balance", "account_no": "1234567890"}

# 보유 종목 조회
{"cmd": "positions", "account_no": "1234567890"}

# 주문
{"cmd": "order", "req_id": "uuid",
 "account_no": "1234567890", "code": "005930",
 "order_type": 1, "qty": 10, "price": 0, "hoga": "03"}

# 현재가 조회
{"cmd": "price", "code": "005930"}

# 종료
{"cmd": "shutdown"}
```

**EVT Queue (32bit → 64bit):**

```python
# 연결 결과
{"evt": "connected", "mode": "demo", "user_id": "user01",
 "accounts": ["1234567890"]}
{"evt": "connect_failed", "error": "HTS 미로그인"}

# 잔고 결과
{"evt": "balance_result", "data": {"deposit": 5000000, "total_eval": 12000000}}

# 보유 종목 결과
{"evt": "positions_result", "data": [
  {"code": "005930", "name": "삼성전자", "qty": 10, "avg_price": 70000, ...}
]}

# 주문 접수
{"evt": "order_accepted", "req_id": "uuid", "order_no": "00123"}

# 체결 통보 (OnReceiveChejanData → Queue)
{"evt": "fill", "order_no": "00123", "code": "005930",
 "side": "BUY", "qty": 10, "price": 70000}

# 잔고 변동 (gubun=1)
{"evt": "balance_changed", "code": "005930", "qty": 10, "avg_price": 70000}

# 현재가 결과
{"evt": "price_result", "code": "005930", "price": 71000}

# 연결 끊김
{"evt": "disconnected", "reason": "COM session lost"}

# 에러
{"evt": "error", "cmd": "order", "message": "자금 부족"}
```

---

## 3. 요구사항

### 3.1 기능적 요구사항

| ID | 요구사항 | 우선순위 |
|----|---------|---------|
| F1 | 32bit 워커 프로세스를 시작/종료할 수 있다 | P0 |
| F2 | `CommConnect(block=True)` → HTS COM 세션에 연결한다 | P0 |
| F3 | 연결 성공 시 모의투자/실거래 모드를 자동 감지한다 | P0 |
| F4 | 잔고(예수금, 총평가)를 조회할 수 있다 (TR: opw00001) | P0 |
| F5 | 보유 종목 목록을 조회할 수 있다 (TR: opw00018) | P0 |
| F6 | 시장가/지정가 매수·매도 주문을 실행할 수 있다 | P0 |
| F7 | 체결 통보(OnReceiveChejanData)를 수신하여 EVT Queue로 전달한다 | P0 |
| F8 | 프론트엔드에 연결 상태 신호등을 표시한다 | P0 |
| F9 | 연결 끊김 시 자동 재연결을 시도한다 (최대 3회, 지수 백오프) | P1 |
| F10 | 현재가를 조회할 수 있다 (TR: opt10001) | P1 |
| F11 | 주문 큐(초당 5건 제한)를 관리한다 | P1 |
| F12 | 미체결 주문 상태를 추적한다 | P2 |
| F13 | 정정/취소 주문을 지원한다 | P2 |

### 3.2 비기능적 요구사항

| 항목 | 목표 |
|------|------|
| 워커 시작 시간 | < 5초 (프로세스 spawn + COM 초기화) |
| IPC 지연 | < 50ms (Queue put → get) |
| 주문 → 키움 전송 | < 200ms |
| 메모리 (32bit 워커) | < 150MB |
| 재연결 시간 | < 30초 (3회 시도 포함) |

---

## 4. 연결 상태 신호등

### 4.1 상태 정의

| 색상 | 상태 | 조건 |
|------|------|------|
| 🟢 녹색 | 정상 연결 | 키움 COM 연결 성공 + 워커 alive |
| 🟡 노란색 | 연결 중 / 재연결 중 | connect 명령 전송 후 응답 대기 중 |
| 🔴 빨간색 | 미연결 | 워커 미시작 또는 연결 실패 또는 HTS 미로그인 |
| ⚫ 회색 | 워커 없음 | 32bit 환경 미설정 (개발 중 표시) |

### 4.2 UI 위치

- **Layout 헤더** 우측 상단에 작은 원형 아이콘 + 텍스트
- 클릭 시 상세 정보 팝오버: 모드(모의/실거래), 계좌번호, 마지막 연결 시각
- BridgeStatus 위젯(대시보드)에도 동일 상태 반영

### 4.3 상태 갱신 방식

```
로컬 서버 → WS → React
{"type": "kiwoom_status", "data": {
  "state": "connected",   // "connected" | "connecting" | "disconnected" | "unavailable"
  "mode": "demo",         // "demo" | "real" | null
  "account_no": "123...", // 마스킹 가능
  "last_connected": "2026-03-04T09:01:00+09:00"
}}
```

- 워커 EVT Queue 수신 시마다 WS 브로드캐스트
- React는 WS 메시지로 즉시 상태 업데이트 (폴링 없음)

---

## 5. 수용 기준

### 5.1 연결

- [ ] 영웅문 HTS 로그인 상태에서 "키움 연결" 클릭 → 🟢 녹색으로 변경
- [ ] HTS 미로그인 상태에서 연결 시도 → 🔴 빨간색 + 에러 메시지
- [ ] 모의투자/실거래 모드가 자동 감지되어 표시됨
- [ ] 연결 중 HTS가 종료되면 → 🔴 빨간색 + 자동 재연결 시도

### 5.2 조회

- [ ] 잔고 조회 → 예수금, 총평가금액이 표시됨
- [ ] 보유 종목 → 종목명, 수량, 매입가, 현재가, 수익률 표시
- [ ] `block_request()` 사용, 1초 5회 제한 준수

### 5.3 주문

- [ ] 시장가 매수 10주 주문 → 체결 통보 수신 → logs.db 기록
- [ ] 주문 실패(자금 부족 등) → 에러 메시지 + 로그 기록
- [ ] 동일 규칙 중복 실행 방지 (SignalManager 연동)

### 5.4 신호등

- [ ] 헤더에 연결 상태 아이콘이 항상 표시됨
- [ ] 상태 변경 시 즉시 반영 (< 1초)
- [ ] 클릭 시 상세 정보(모드, 계좌) 확인 가능

---

## 6. 범위

### 포함

- `kiwoom_worker.py` — 32bit 서브프로세스 (pykiwoom 래핑)
- `kiwoom/bridge.py` — 64bit 측 IPC 클라이언트 (Queue 관리)
- `kiwoom/session.py` 개정 — bridge.py 위임으로 단순화
- `kiwoom/order.py` 개정 — bridge.py 위임으로 단순화
- `kiwoom/account.py` 개정 — bridge.py 위임으로 단순화
- `routers/kiwoom.py` 개정 — connect/disconnect 엔드포인트 추가
- 프론트엔드 연결 상태 신호등 (헤더 + BridgeStatus 연동)

### 미포함

- 실시간 시세 스트리밍 (SetRealReg) — 별도 spec
- 조건식 검색 — 별도 spec
- PyInstaller exe 빌드 — 별도 spec
- KOSCOM 연동 — 별도 spec (koscom-integration)

---

## 7. 파일 변경 계획

### 7.1 신규 파일

| 파일 | 역할 |
|------|------|
| `local_server/kiwoom_worker.py` | 32bit 서브프로세스 진입점 (pykiwoom Kiwoom 인스턴스 + CMD 수신 루프) |
| `local_server/kiwoom/bridge.py` | 64bit 측 IPC 클라이언트 (워커 spawn, Queue send/recv, 상태 관리) |
| `frontend/src/components/KiwoomStatus.tsx` | 헤더 연결 상태 신호등 컴포넌트 |

### 7.2 수정 파일

| 파일 | 변경 내용 |
|------|----------|
| `local_server/kiwoom/com_client.py` | 삭제 또는 비활성화 (bridge.py로 대체) |
| `local_server/kiwoom/session.py` | bridge.py 위임으로 단순화 (connect/disconnect/status) |
| `local_server/kiwoom/order.py` | bridge.py 위임으로 단순화 (enqueue → CMD Queue) |
| `local_server/kiwoom/account.py` | bridge.py 위임으로 단순화 (balance/positions → CMD Queue) |
| `local_server/routers/kiwoom.py` | POST /api/kiwoom/connect, POST /api/kiwoom/disconnect 추가 |
| `local_server/main.py` | lifespan에서 bridge 시작/종료 관리 |
| `local_server/engine/signal.py` | order 호출을 bridge 기반으로 변경 |
| `frontend/src/components/Layout.tsx` | 헤더에 KiwoomStatus 삽입 |
| `frontend/src/components/BridgeStatus.tsx` | kiwoom_status WS 메시지 연동 |
| `local_server/requirements.txt` | 변경 없음 (pykiwoom은 32bit 환경 전용) |

### 7.3 32bit 환경 별도 구성

```
local_server/
├── kiwoom_worker.py         # 32bit 진입점
├── kiwoom_worker_requirements.txt  # pykiwoom, PyQt5, pywin32, pandas
└── setup_32bit.md           # 32bit conda 환경 구성 가이드
```

> 64bit 측(`local_server/requirements.txt`)에는 pykiwoom 의존성을 추가하지 않음.
> 32bit 워커는 별도 Python 인터프리터로 실행.

---

## 8. 32bit 워커 내부 설계

### 8.1 kiwoom_worker.py 구조

```python
"""
32bit Python에서 실행 — pykiwoom + PyQt5 환경
64bit local_server/main.py가 subprocess로 spawn
"""
import sys
from multiprocessing import Queue
from pykiwoom.kiwoom import Kiwoom
import pythoncom

def main(cmd_queue: Queue, evt_queue: Queue):
    kiwoom = Kiwoom()

    while True:
        # 1. CMD Queue에서 명령 수신 (non-blocking)
        cmd = cmd_queue.get(timeout=0.05)  # 50ms 타임아웃

        # 2. 명령 처리
        if cmd["cmd"] == "connect":
            kiwoom.CommConnect(block=True)
            mode = kiwoom.GetLoginInfo("GetServerGubun")
            evt_queue.put({"evt": "connected", "mode": ...})

        elif cmd["cmd"] == "balance":
            df = kiwoom.block_request("opw00001", ...)
            evt_queue.put({"evt": "balance_result", "data": ...})

        elif cmd["cmd"] == "order":
            ret = kiwoom.SendOrder(...)
            evt_queue.put({"evt": "order_accepted" if ret == 0 else "error", ...})

        # 3. COM 메시지 펌핑 (체결 이벤트 수신)
        pythoncom.PumpWaitingMessages()
```

### 8.2 체결 이벤트 수신

pykiwoom의 `chejan_dqueue` 생성자 파라미터를 활용:

```python
chejan_q = Queue()
kiwoom = Kiwoom(chejan_dqueue=chejan_q)

# 메인 루프에서 chejan_q도 함께 폴링
if not chejan_q.empty():
    chejan_data = chejan_q.get_nowait()
    evt_queue.put({"evt": "fill", ...})
```

### 8.3 Rate Limit 관리

- TR 조회: `block_request()` 호출 사이 `time.sleep(0.2)` (200ms)
- 주문: `SendOrder()` 호출 사이 `time.sleep(0.2)`
- 워커 내부에서 관리 (64bit 측은 신경 쓸 필요 없음)

---

## 9. 64bit 측 bridge.py 설계

```python
class KiwoomBridge:
    """64bit FastAPI 프로세스에서 32bit 워커를 관리"""

    def __init__(self):
        self._cmd_queue: Queue   # 명령 전송용
        self._evt_queue: Queue   # 이벤트 수신용
        self._process: Process   # 32bit 워커 프로세스
        self._state: str = "unavailable"  # connected | connecting | disconnected | unavailable

    def start_worker(self, python32_path: str):
        """32bit Python 경로로 워커 서브프로세스 시작"""

    def stop_worker(self):
        """워커 종료"""

    async def connect(self) -> dict:
        """CMD: connect 전송 → EVT: connected 대기"""

    async def disconnect(self):
        """CMD: disconnect 전송"""

    async def get_balance(self, account_no: str) -> dict:
        """CMD: balance → EVT: balance_result"""

    async def get_positions(self, account_no: str) -> list[dict]:
        """CMD: positions → EVT: positions_result"""

    async def send_order(self, ...) -> dict:
        """CMD: order → EVT: order_accepted | error"""

    async def poll_events(self):
        """백그라운드 태스크: EVT Queue 폴링 → WS 브로드캐스트"""
```

- `poll_events()`는 `asyncio.create_task()`로 시작
- `asyncio.get_event_loop().run_in_executor()`로 Queue.get() 블로킹 회피

---

## 10. 키움 OpenAPI+ 제약 사항 (유지)

| 항목 | 제약 |
|------|------|
| 플랫폼 | Windows 전용, 32bit COM |
| 인증 | 영웅문 HTS 자동로그인 위임 (우리 앱은 자격증명 미보관) |
| 조회 제한 | 초당 5건 |
| 주문 제한 | 초당 5건 |
| 실시간 등록 | 최대 200종목 |
| 거래 시간 | 평일 09:00~15:30 KST |

---

## 11. 미결 사항

- [ ] 32bit Python 경로를 config에서 관리할지 자동 탐지할지
- [ ] PyInstaller 번들 시 32bit 워커를 어떻게 포함할지
- [ ] pykiwoom `KiwoomManager` (내장 IPC)를 쓸지, 직접 Queue IPC를 구현할지
- [ ] 실시간 시세 스트리밍 범위 (별도 spec 분리 여부)
- [ ] 모의투자 ↔ 실거래 전환 시 워커 재시작 필요 여부

---

## 참고

- [pykiwoom 분석 보고서](../../docs/research/pykiwoom-analysis.md)
- [로컬 브릿지 spec](../local-bridge/spec.md)
- [실행 엔진 spec](../execution-engine/spec.md)
- [키움 OpenAPI+ 개발가이드 PDF](https://download.kiwoom.com/web/openapi/kiwoom_openapi_plus_devguide_ver_1.5.pdf)
- [pykiwoom GitHub](https://github.com/sharebook-kr/pykiwoom)
- [WikiDocs: 퀀트투자를 위한 키움증권 API](https://wikidocs.net/book/1173)

---

**마지막 갱신**: 2026-03-04 (v2: pykiwoom + 32bit 서브프로세스 아키텍처)
