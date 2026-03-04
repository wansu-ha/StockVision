# 키움 API 연동 구현 계획서 (kiwoom-integration)

> 작성일: 2026-03-04 | 상태: 초안 | 범위: 로컬 서버 COM API 레이어 | 의존: local-bridge

---

## 0. 전제 조건

- Windows 전용 (COM API는 Windows 환경 필수)
- 키움 OpenAPI+ 영웅문 HTS 설치 + 사용자 직접 로그인
- G5 제5조②: API 키/ID/PW 서버 저장 금지 — 로컬에서만 사용
- 의존: `spec/local-bridge/plan.md` (Step 1 완료 후 시작)

---

## 1. 구현 단계

### Step 1 — COM 클라이언트 기본 연결

**목표**: 이미 로그인된 영웅문 HTS에 COM 세션 연결

파일: `local_server/kiwoom/com_client.py`

```python
import win32com.client

class KiwoomCOMClient:
    def __init__(self):
        self._ocx = win32com.client.Dispatch("KHOPENAPI.KHOpenAPICtrl.1")

    def connect(self) -> bool:
        """이미 로그인된 HTS에 연결"""
        result = self._ocx.CommConnect()
        return result == 0

    def get_login_info(self, tag: str) -> str:
        return self._ocx.GetLoginInfo(tag)

    def is_connected(self) -> bool:
        return self._ocx.GetConnectState() == 1
```

**검증:**
- [ ] 영웅문 HTS 로그인 후 `connect()` → `is_connected()` True
- [ ] `GetLoginInfo("USER_NAME")` 사용자명 반환

### Step 2 — 계좌/잔고 조회

파일: `local_server/kiwoom/account.py`

```python
class KiwoomAccount:
    def get_account_list(self) -> list[str]:
        """보유 계좌 번호 목록"""
        ...

    def get_balance(self, account_no: str) -> dict:
        """잔고 조회 (예수금, 평가액, 수익률)"""
        ...

    def get_positions(self, account_no: str) -> list[dict]:
        """보유 종목 목록"""
        ...
```

**검증:**
- [ ] `GET /api/account` → 잔고/포지션 JSON 반환
- [ ] 모의투자 계좌 + 실계좌 각각 조회 확인

### Step 3 — 주문 실행

파일: `local_server/kiwoom/order.py`

```python
class KiwoomOrder:
    def send_order(self,
                   account_no: str,
                   symbol: str,
                   side: str,       # "BUY" | "SELL"
                   qty: int,
                   price: int,      # 0 = 시장가
                   order_type: str  # "01" = 지정가, "03" = 시장가
                   ) -> str:
        """주문 전송 → 주문번호 반환"""
        ...
```

**API 호출 제한 관리:**
- 조회 API: 초당 5건 → 조회 큐 + 200ms 간격
- 주문 API: 초당 5건 → FIFO 큐

**검증:**
- [ ] 모의투자 시장가 매수 → 체결 확인
- [ ] 주문 제한 초과 시 큐 대기 후 재전송

### Step 4 — 체결 이벤트 수신

파일: `local_server/kiwoom/com_client.py`

```python
# COM 이벤트 핸들러
def OnReceiveChejanData(self, gubun, item_cnt, fid_list):
    """체결 통보 이벤트"""
    if gubun == "0":  # 주문 체결
        # 체결 정보 파싱 → logs.db 저장 → WS로 React 전송
        ...
```

**검증:**
- [ ] 매수 주문 체결 → WS `execution_result` 이벤트 수신
- [ ] logs.db에 체결 기록 저장

### Step 5 — 세션 관리 (재연결 + 계정 전환)

파일: `local_server/kiwoom/session.py`

```python
class KiwoomSession:
    def reconnect(self, max_retries=3) -> bool:
        """자동 재연결 (3회 시도)"""
        ...

    def logout(self):
        """세션 종료 (계정 전환 전)"""
        ...
```

**에러 처리:**
- 세션 만료 → 자동 재연결 3회 → 실패 시 WS 알림
- 재연결 실패 → 전략 엔진 일시 정지 + 트레이 알림

**검증:**
- [ ] HTS 재시작 후 자동 재연결
- [ ] 계정 전환 플로우 (logout → 사용자 재로그인 → connect)

---

## 2. 파일 목록

| 파일 | 내용 |
|------|------|
| `local_server/kiwoom/com_client.py` | COM 객체 래퍼, 이벤트 핸들러 |
| `local_server/kiwoom/session.py` | 세션 관리, 재연결 |
| `local_server/kiwoom/order.py` | 주문 실행, 큐 관리 |
| `local_server/kiwoom/account.py` | 잔고, 포지션 조회 |
| `local_server/routers/kiwoom.py` | `GET /api/kiwoom/status`, `GET /api/account` |

---

## 3. 커밋 계획

| 커밋 | 메시지 |
|------|--------|
| 1 | `feat: Step 1 — 키움 COM 클라이언트 기본 연결` |
| 2 | `feat: Step 2 — 계좌/잔고/포지션 조회 API` |
| 3 | `feat: Step 3 — 주문 실행 + 큐 관리` |
| 4 | `feat: Step 4 — 체결 이벤트 수신 → WS 전송` |
| 5 | `feat: Step 5 — 세션 관리 + 자동 재연결` |
