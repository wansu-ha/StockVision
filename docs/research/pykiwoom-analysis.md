# pykiwoom 라이브러리 API 스펙 분석

> 작성일: 2026-03-04
> 참고: [PyPI](https://pypi.org/project/pykiwoom/), [GitHub](https://github.com/sharebook-kr/pykiwoom), [WikiDocs](https://wikidocs.net/book/1173)

---

## 1. 설치 및 환경

### 1.1 pip install

```bash
pip install pykiwoom
```

- 최신 버전: **0.1.6** (2024년 1월 5일)
- 라이선스: Apache-2.0
- 유지관리자: Lukas Yoo, Brayden Jo

### 1.2 Python 버전 및 32bit 제약

**키움 OpenAPI+는 32bit COM OCX 컴포넌트**이다. 따라서 Python도 반드시 32bit 빌드여야 한다.

| 항목 | 요구사항 |
|------|----------|
| Python | 3.8 ~ 3.11 (32bit 빌드 필수) |
| OS | Windows 전용 |
| 아키텍처 | x86 (32bit) 필수 |

**Conda로 32bit 환경 구성:**

```bash
conda create -n kiwoom32
conda activate kiwoom32
conda config --env --set subdir win-32     # 현재 환경을 32bit로 고정
conda install python=3.10
conda install 'pandas<2.0'                 # 32bit용 pandas
pip install pykiwoom
pip install PyQt5 pywin32
```

> 주의: 64bit Python에서는 OCX 로드 자체가 실패한다.

### 1.3 PyQt5 의존성

pykiwoom은 내부적으로 `QAxWidget`을 사용해 키움 OCX를 로드한다.

```python
from PyQt5.QAxContainer import QAxWidget
self.ocx = QAxWidget("KHOPENAPI.KHOpenAPICtrl.1")
```

**필수 패키지:**
- `PyQt5` — Qt 이벤트 루프 및 COM 브릿지
- `pywin32` (`pythoncom`, `win32com`) — Windows COM 메시지 펌핑
- `pandas` — `block_request()` 반환값이 DataFrame

### 1.4 키움 OpenAPI+ 사전 요구사항

1. 키움증권 계좌 개설 (모의투자 가능)
2. [키움 OpenAPI+](https://www.kiwoom.com/h/customer/download/VOpenApiInfoView) 설치 (32bit OCX)
3. OpenAPI 사용 신청 (키움HTS에서 신청)
4. Microsoft Visual C++ Redistributable (32bit) 설치

---

## 2. 핵심 API — Kiwoom 클래스

### 2.1 클래스 초기화

```python
from pykiwoom.kiwoom import Kiwoom

kiwoom = Kiwoom()
# 또는 큐 기반 멀티프로세스용
from multiprocessing import Queue
kiwoom = Kiwoom(
    login=Queue(),
    tr_dqueue=Queue(),
    real_dqueues={},
    tr_cond_dqueue=Queue(),
    real_cond_dqueue=Queue(),
    chejan_dqueue=Queue()
)
```

내부 `__init__`에서 OCX 인스턴스를 생성하고 `_set_signals_slots()`로 이벤트를 연결한다.

### 2.2 이벤트 핸들러 등록 방식

**데코레이터가 아닌 PyQt5 시그널-슬롯 패턴**을 사용한다.

```python
def _set_signals_slots(self):
    self.ocx.OnEventConnect.connect(self.OnEventConnect)
    self.ocx.OnReceiveTrData.connect(self.OnReceiveTrData)
    self.ocx.OnReceiveRealData.connect(self.OnReceiveRealData)
    self.ocx.OnReceiveChejanData.connect(self.OnReceiveChejanData)
    self.ocx.OnReceiveMsg.connect(self.OnReceiveMsg)
    self.ocx.OnReceiveConditionVer.connect(self.OnReceiveConditionVer)
    self.ocx.OnReceiveTrCondition.connect(self.OnReceiveTrCondition)
    self.ocx.OnReceiveRealCondition.connect(self.OnReceiveRealCondition)
```

OCX의 COM 이벤트가 발생하면 연결된 Python 메서드가 자동 호출된다.

**이벤트 핸들러 목록:**

| 핸들러 | 트리거 조건 |
|--------|------------|
| `OnEventConnect(err_code)` | 로그인 완료 또는 실패 |
| `OnReceiveTrData(screen, rqname, trcode, record, next, ...)` | TR 조회 응답 수신 |
| `OnReceiveRealData(code, real_type, real_data)` | 실시간 시세 수신 |
| `OnReceiveChejanData(gubun, item_cnt, fid_list)` | 주문접수/체결/잔고 변경 |
| `OnReceiveMsg(screen, rqname, trcode, msg)` | 서버 메시지 수신 |
| `OnReceiveConditionVer(ret, msg)` | 조건식 로드 완료 |
| `OnReceiveTrCondition(screen, code_list, cond_name, index, next)` | 조건식 검색 결과 |
| `OnReceiveRealCondition(code, type, cond_name, cond_index)` | 실시간 조건 편입/이탈 |

### 2.3 로그인

```python
# 시그니처
def CommConnect(self, block=True) -> None

# 사용법
kiwoom = Kiwoom()
kiwoom.CommConnect(block=True)   # 로그인 창이 뜨고 완료될 때까지 블로킹
```

**내부 구현:**

```python
def CommConnect(self, block=True):
    self.ocx.dynamicCall("CommConnect()")
    if block:
        while not self.connected:
            pythoncom.PumpWaitingMessages()   # COM 메시지 루프 수동 펌핑
```

- `block=True`: `OnEventConnect` 콜백이 올 때까지 busy-wait
- `block=False`: 즉시 반환, 별도 콜백 처리 필요
- 자동로그인: 키움 HTS의 자동로그인 옵션을 켜면 `CommConnect()` 호출 시 자격증명 없이 자동 로그인

**로그인 정보 조회:**

```python
def GetLoginInfo(self, tag: str) -> str | list

# 사용 예시
user_id   = kiwoom.GetLoginInfo("USER_ID")      # 사용자 ID
user_name = kiwoom.GetLoginInfo("USER_NAME")    # 사용자명
accounts  = kiwoom.GetLoginInfo("ACCNO")        # 계좌번호 리스트로 반환
server    = kiwoom.GetLoginInfo("GetServerGubun")  # "1" = 모의투자
```

| tag 값 | 반환값 |
|--------|--------|
| `USER_ID` | 사용자 ID 문자열 |
| `USER_NAME` | 사용자명 |
| `ACCOUNT_CNT` | 계좌 수 |
| `ACCNO` | 계좌번호 리스트 (`;` 구분 후 파싱) |
| `GetServerGubun` | `"1"` = 모의투자, `""` = 실서버 |

### 2.4 TR 조회

#### 저수준 API (수동 방식)

```python
# 입력값 설정
def SetInputValue(self, id: str, value: str) -> None

# TR 전송
def CommRqData(self, rqname: str, trcode: str, next: int, screen: str) -> int

# 결과 조회 (OnReceiveTrData 콜백 내에서 호출)
def GetCommData(self, trcode: str, rqname: str, index: int, item: str) -> str

# 멀티데이터 행 수
def GetRepeatCnt(self, trcode: str, rqname: str) -> int
```

**수동 방식 예시:**

```python
kiwoom.SetInputValue("종목코드", "005930")
kiwoom.SetInputValue("기준일자", "20240101")
kiwoom.SetInputValue("수정주가구분", "1")
kiwoom.CommRqData("일봉조회", "opt10081", 0, "0101")

# OnReceiveTrData 콜백 내에서:
def OnReceiveTrData(self, screen, rqname, trcode, record, next, ...):
    cnt = self.GetRepeatCnt(trcode, rqname)
    for i in range(cnt):
        date  = self.GetCommData(trcode, rqname, i, "일자").strip()
        close = self.GetCommData(trcode, rqname, i, "현재가").strip()
```

#### 고수준 API — `block_request()` (권장)

```python
def block_request(self, trcode: str, **kwargs) -> pd.DataFrame
```

`SetInputValue` + `CommRqData` + `GetCommData`를 하나로 묶은 동기 래퍼. `output` TR 레코드를 pandas DataFrame으로 반환한다.

```python
# 주식 일봉 조회 (opt10081)
df = kiwoom.block_request(
    "opt10081",
    종목코드="005930",
    기준일자="20240101",
    수정주가구분=1,
    output="주식일봉차트",   # TR의 OUTPUT 레코드 이름
    next=0                   # 0: 첫 페이지, 2: 연속 조회
)

# 연속 조회
df2 = kiwoom.block_request(
    "opt10081",
    종목코드="005930",
    기준일자="20240101",
    수정주가구분=1,
    output="주식일봉차트",
    next=2   # 이전 응답의 tr_remained가 True일 때 사용
)
```

**내부 구현 흐름:**

```python
def block_request(self, *args, **kwargs):
    trcode = args[0].lower()
    # TR 메타데이터(.enc 파일) 파싱
    lines = parser.read_enc(trcode)
    self.tr_items = parser.parse_dat(trcode, lines)
    self.tr_record = kwargs["output"]
    next = kwargs["next"]

    for id in kwargs:
        if id.lower() not in ("output", "next"):
            self.SetInputValue(id, kwargs[id])

    self.received = False
    self.tr_remained = False
    self.CommRqData(trcode, trcode, next, "0101")

    # 응답 올 때까지 COM 메시지 루프 수동 실행
    while not self.received:
        pythoncom.PumpWaitingMessages()

    return self.tr_data   # pandas DataFrame
```

**연속 조회 패턴:**

```python
df_list = []
next = 0
while True:
    df = kiwoom.block_request("opt10081",
        종목코드="005930",
        기준일자="20240101",
        수정주가구분=1,
        output="주식일봉차트",
        next=next)
    df_list.append(df)
    if kiwoom.tr_remained:
        next = 2
        time.sleep(0.2)   # 1초 5회 제한 대응
    else:
        break
result = pd.concat(df_list)
```

### 2.5 주문 — `SendOrder()`

```python
def SendOrder(
    self,
    rqname: str,      # 요청명 (임의 문자열, OnReceiveTrData 식별용)
    screen: str,      # 화면번호 (4자리 문자열, e.g. "1000")
    accno: str,       # 계좌번호
    order_type: int,  # 주문 유형 (아래 표 참고)
    code: str,        # 종목코드 (e.g. "005930")
    quantity: int,    # 주문 수량
    price: int,       # 주문 가격 (시장가일 때 0)
    hoga: str,        # 호가구분 (아래 표 참고)
    order_no: str     # 원주문번호 (취소/정정 시, 신규는 "")
) -> int              # 성공: 0, 실패: 음수 에러코드
```

**order_type 값:**

| 값 | 의미 |
|----|------|
| 1 | 신규매수 |
| 2 | 신규매도 |
| 3 | 매수취소 |
| 4 | 매도취소 |
| 5 | 매수정정 |
| 6 | 매도정정 |

**hoga (호가구분) 값:**

| 값 | 의미 |
|----|------|
| `"00"` | 지정가 |
| `"03"` | 시장가 |
| `"05"` | 조건부지정가 |
| `"06"` | 최유리지정가 |
| `"07"` | 최우선지정가 |
| `"10"` | 지정가IOC |
| `"13"` | 시장가IOC |
| `"16"` | 최유리IOC |
| `"20"` | 지정가FOK |
| `"23"` | 시장가FOK |
| `"26"` | 최유리FOK |

**사용 예시:**

```python
# 삼성전자 지정가 매수 2주 @ 18,000원
ret = kiwoom.SendOrder(
    rqname="지정가매수",
    screen="1000",
    accno="1234567811",
    order_type=1,
    code="005930",
    quantity=2,
    price=18000,
    hoga="00",
    order_no=""
)

# 시장가 매수
ret = kiwoom.SendOrder("시장가매수", "0101", accno, 1, "005930", 10, 0, "03", "")
```

### 2.6 실시간 데이터

```python
# 실시간 등록
def SetRealReg(
    self,
    screen: str,      # 화면번호
    code_list: str,   # 종목코드 (복수 시 ";" 구분, e.g. "005930;000660")
    fid_list: str,    # FID 목록 (e.g. "10;11;12" — 현재가;거래량;체결시간)
    opt_type: str     # "0": 기존 목록 교체, "1": 기존 목록에 추가
) -> None

# 실시간 해제
def SetRealRemove(self, screen: str, del_code: str) -> None

# 실시간 데이터 읽기 (OnReceiveRealData 콜백 내에서 사용)
def GetCommRealData(self, code: str, fid: int) -> str

# 화면 단위 실시간 해제
def DisconnectRealData(self, screen: str) -> None
```

**주요 FID 번호:**

| FID | 항목 |
|-----|------|
| 10 | 현재가 |
| 11 | 전일대비 |
| 12 | 등락율 |
| 13 | 누적거래량 |
| 15 | 거래량 |
| 20 | 체결시간 |
| 228 | 체결강도 |

**사용 예시:**

```python
# 실시간 등록
kiwoom.SetRealReg("9000", "005930;000660", "10;11;12;15", "0")

# OnReceiveRealData 콜백 — kiwoom.py 내부에서 처리됨
def OnReceiveRealData(self, code, real_type, real_data):
    if real_dqueues is not None and code in real_dqueues:
        # 큐에 데이터 전달
        ...

# 외부에서 실시간 데이터 읽기 (콜백 후)
current_price = kiwoom.GetCommRealData("005930", 10)
```

### 2.7 체결/잔고 — `OnReceiveChejanData`

```python
def OnReceiveChejanData(self, gubun: str, item_cnt: int, fid_list: str) -> None
```

**gubun 값:**

| 값 | 의미 |
|----|------|
| `"0"` | 주문접수 / 체결 |
| `"1"` | 잔고 변경 |
| `"4"` | 파생상품 잔고 변경 |

**구현 내용:**

```python
def OnReceiveChejanData(self, gubun, item_cnt, fid_list):
    if self.chejan_dqueue is not None:
        output = {'gubun': gubun}
        for fid in fid_list.split(';'):
            data = self.GetChejanData(fid)
            output[fid] = data
        self.chejan_dqueue.put(output)
```

**주요 FID (gubun=0 체결):**

| FID | 항목 |
|-----|------|
| 9203 | 주문번호 |
| 302 | 종목명 |
| 900 | 주문수량 |
| 901 | 주문가격 |
| 902 | 미체결수량 |
| 904 | 체결누계금액 |
| 913 | 주문상태 (접수/체결) |
| 917 | 신용구분 |

**이벤트 흐름:** 주문 → 접수(gubun=0) → 체결1(gubun=0) → 잔고변경(gubun=1) → ...

---

## 3. 동기/비동기 패턴

### 3.1 내부 이벤트 루프 처리 방식

pykiwoom은 **asyncio를 사용하지 않는다.** 대신 COM 메시지 펌핑(`pythoncom.PumpWaitingMessages()`)으로 Qt 이벤트 루프를 수동 처리한다.

```
[Python 코드]
    ↓ CommRqData() 호출
[키움 OCX] → 서버 요청 전송
    ...서버 응답 대기...
[Windows 메시지 큐] ← COM 이벤트 수신
    ↑ pythoncom.PumpWaitingMessages()  ← 이것이 이벤트 루프
[OnReceiveTrData 콜백] → self.received = True
[block_request() while 루프 탈출]
    ↓
[DataFrame 반환]
```

### 3.2 블로킹 vs 논블로킹

| 메서드 | 방식 | 설명 |
|--------|------|------|
| `CommConnect(block=True)` | 블로킹 | 로그인 완료 시까지 busy-wait |
| `CommConnect(block=False)` | 논블로킹 | 즉시 반환, 콜백 직접 처리 |
| `block_request()` | 블로킹 | TR 응답 시까지 busy-wait + DataFrame 반환 |
| `CommRqData()` | 논블로킹 | TR 전송만, 응답은 콜백 `OnReceiveTrData`로 수신 |
| `SendOrder()` | 논블로킹 | 주문 전송만, 체결은 `OnReceiveChejanData`로 수신 |
| `GetConditionLoad(block=True)` | 블로킹 | 조건식 로드 완료 시까지 busy-wait |
| `SendCondition(block=True)` | 블로킹 | 조건 검색 결과 수신 시까지 busy-wait |

### 3.3 `block_request()` — 동기 래퍼 존재 확인

**있다.** `block_request()`가 공식 동기 래퍼이며 내부 구현은:

```python
self.CommRqData(trcode, trcode, next, "0101")
while not self.received:
    pythoncom.PumpWaitingMessages()   # 블로킹 busy-wait
return self.tr_data                   # pandas DataFrame
```

---

## 4. 주요 메서드 시그니처 정리

### 4.1 연결 / 로그인

```python
CommConnect(block: bool = True) -> None
GetLoginInfo(tag: str) -> str | list[str]
GetConnectState() -> int   # 0: 미연결, 1: 연결
```

### 4.2 TR 조회

```python
SetInputValue(id: str, value: str) -> None
CommRqData(rqname: str, trcode: str, next: int, screen: str) -> int
GetCommData(trcode: str, rqname: str, index: int, item: str) -> str
GetRepeatCnt(trcode: str, rqname: str) -> int
block_request(trcode: str, **kwargs) -> pd.DataFrame
    # kwargs: 입력값들, output="레코드명", next=0|2
CommKwRqData(arr_code: str, next: int, code_count: int,
             type: int, rqname: str, screen: str) -> int
```

### 4.3 주문

```python
SendOrder(rqname: str, screen: str, accno: str, order_type: int,
          code: str, quantity: int, price: int,
          hoga: str, order_no: str) -> int
```

### 4.4 실시간

```python
SetRealReg(screen: str, code_list: str, fid_list: str, opt_type: str) -> None
SetRealRemove(screen: str, del_code: str) -> None
GetCommRealData(code: str, fid: int) -> str
DisconnectRealData(screen: str) -> None
```

### 4.5 체결/잔고

```python
GetChejanData(fid: int) -> str   # OnReceiveChejanData 콜백 내에서 사용
```

### 4.6 마스터 데이터

```python
GetMasterCodeName(code: str) -> str
GetMasterLastPrice(code: str) -> str
GetMasterStockState(code: str) -> str
GetCodeListByMarket(market: str) -> list[str]
    # market: "0" = 코스피, "10" = 코스닥, "8" = ETF
```

### 4.7 조건식

```python
GetConditionLoad(block: bool = True) -> None
GetConditionNameList() -> list[tuple[int, str]]
SendCondition(screen: str, cond_name: str, cond_index: int,
              search: int, block: bool = True) -> list | None
SendConditionStop(screen: str, cond_name: str, index: int) -> None
```

### 4.8 KiwoomManager (멀티프로세스)

```python
from pykiwoom.kiwoom import KiwoomManager

km = KiwoomManager()
km.put_method(("GetMasterCodeName", "005930"))
data = km.get_method()   # 반환값 수신 (블로킹)

km.put_tr(tr_params_dict)
df = km.get_tr()         # DataFrame 수신
```

---

## 5. 한계점

### 5.1 asyncio 통합 제약

**핵심 문제:** pykiwoom의 블로킹 방식(`pythoncom.PumpWaitingMessages()` busy-wait)은 asyncio 이벤트 루프와 **직접 통합이 불가능**하다.

```
asyncio event loop (단일 스레드)
    ↓ await kiwoom.block_request(...)   ← 여기서 스레드 점유
    → pythoncom.PumpWaitingMessages()   ← 무한 루프 (COM 메시지 펌핑)
    → asyncio 이벤트 루프가 멈춤        ← 다른 coroutine 실행 불가
```

**우회 방법:**

```python
import asyncio

# asyncio 스레드풀에서 블로킹 호출 분리
loop = asyncio.get_event_loop()
df = await loop.run_in_executor(None, lambda: kiwoom.block_request(
    "opt10081", 종목코드="005930", output="주식일봉차트", next=0
))
```

단, `pythoncom.PumpWaitingMessages()`가 COM 스레드 친화적이지 않아 이 방법도 불안정할 수 있다. COM 초기화(`pythoncom.CoInitialize()`)를 스레드마다 호출해야 한다.

### 5.2 32bit 전용 제약

- 64bit Python에서는 키움 OCX가 로드되지 않는다.
- 메모리 상한 약 2GB (32bit 프로세스 한계).
- 대용량 데이터 처리 시 메모리 부족 가능성.

### 5.3 Windows 전용

- COM/OCX 기반이므로 Linux/macOS에서 실행 불가.
- 개발 환경과 운영 환경 모두 Windows 필수.

### 5.4 TR 조회 Rate Limit

- 초당 최대 **5회** TR 요청 제한
- 분당, 시간당 유동적 제한 추가 적용 (키움 정책에 따라 변경됨)
- `time.sleep(0.2)` 이상 간격 권장

### 5.5 별도 스레드/프로세스 권장 패턴

64bit Python 메인 프로세스에서 키움 API를 사용해야 한다면 **KiwoomManager**를 활용해 32bit 서브프로세스를 분리하는 구조가 현실적이다:

```
[64bit 메인 프로세스]          [32bit 서브프로세스]
  FastAPI 서버          ←IPC→   KiwoomManager
  asyncio 루프                  Kiwoom OCX
  pandas 처리                   COM 이벤트 루프
```

KOAPY 라이브러리는 이 문제를 gRPC(서버-클라이언트) 구조로 해결했으며, 더 완성도 높은 대안이다.

### 5.6 기타 한계

- 장 운영 시간(09:00~15:30)에만 실시간 데이터 수신 가능
- 동시 실행 프로세스 수 제한 (키움 정책)
- 조건식 최대 등록 수 제한

---

## 6. StockVision 연동 시 고려사항

| 항목 | 현재 StockVision | pykiwoom 연동 시 |
|------|-----------------|-----------------|
| 언어 | Python 3.13 (64bit) | 32bit Python 별도 환경 필요 |
| 데이터 수집 | yfinance (비실시간) | 실시간 시세 가능 |
| 주문 | 없음 | `SendOrder()` 직접 연동 |
| 아키텍처 | FastAPI 단일 프로세스 | 32bit 서브프로세스 분리 필요 |
| asyncio | 사용 | pykiwoom과 직접 통합 불가 → IPC 필요 |

**권장 아키텍처 (연동 필요 시):**

```
FastAPI (64bit, asyncio)
    ↕ Queue / gRPC / socket IPC
pykiwoom subprocess (32bit, Windows, COM 루프)
    ↕ COM OCX
키움 OpenAPI+
```

---

## 참고 자료

- [pykiwoom PyPI](https://pypi.org/project/pykiwoom/)
- [pykiwoom GitHub](https://github.com/sharebook-kr/pykiwoom)
- [pykiwoom kiwoom.py 소스](https://github.com/sharebook-kr/pykiwoom/blob/master/pykiwoom/kiwoom.py)
- [WikiDocs: 퀀트투자를 위한 키움증권 API](https://wikidocs.net/book/1173)
- [키움 OpenAPI+ 개발가이드 PDF](https://download.kiwoom.com/web/openapi/kiwoom_openapi_plus_devguide_ver_1.5.pdf)
- [Conda 32bit 환경 구성](https://losskatsu.github.io/it-infra/conda32/)
- [KOAPY GitHub (gRPC 기반 대안)](https://github.com/elbakramer/koapy)
- [키움 OpenAPI+ 다운로드](https://www.kiwoom.com/h/customer/download/VOpenApiInfoView)
