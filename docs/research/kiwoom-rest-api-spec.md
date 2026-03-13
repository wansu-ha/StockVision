# 키움증권 REST API 명세 (리서치 결과)

> 출처: KiwoomRestApi.Net (.NET 래퍼 소스코드 역공학) + 공식 가이드 페이지
> 작성일: 2026-03-07

## 1. 기본 정보

| 항목 | 실전 | 모의투자 |
|------|------|----------|
| REST | `https://api.kiwoom.com` | `https://mockapi.kiwoom.com` |
| WebSocket | `wss://api.kiwoom.com:10000` | `wss://mockapi.kiwoom.com:10000` |
| 가이드 | https://openapi.kiwoom.com/guide/apiguide?dummyVal=0 | |

## 2. 인증

### POST /oauth2/token (api-id: au10001)

**요청 헤더:**
```
Content-Type: application/json;charset=UTF-8
```

**요청 Body:**
```json
{
  "grant_type": "client_credentials",
  "appkey": "발급받은 앱키",
  "secretkey": "발급받은 시크릿키"
}
```

**응답:**
```json
{
  "return_code": 0,
  "return_msg": "정상적으로 처리되었습니다",
  "expires_dt": "20241107083713",
  "token_type": "bearer",
  "token": "WQJCwyqInphKnR3bSRtB9NE1lv..."
}
```

### POST /oauth2/revoke (api-id: au10002)
Body: `{ "appkey", "secretkey", "token" }`

## 3. 공통 요청/응답 패턴

### 요청 헤더 (토큰 발급 후 모든 API 공통)
```
api-id: {api별 고유 ID}
authorization: Bearer {token}
cont-yn: {연속조회 여부}
next-key: {연속조회 키}
Content-Type: application/json
```

> **KIS와 핵심 차이**: KIS는 `tr_id` 헤더 + GET/POST 혼용, 키움은 `api-id` 헤더 + **전부 POST**

### 응답 공통 구조
```json
{
  "return_code": 0,
  "return_msg": "정상적으로 처리되었습니다",
  ...데이터 필드들
}
```

**응답 헤더:**
- `api-id`: 호출된 API ID
- `cont-yn`: "Y" | "N" (연속조회 가능 여부)
- `next-key`: 다음 페이지 키

## 4. 엔드포인트 목록

### 4.1 URL 경로

| 카테고리 | 경로 |
|----------|------|
| OAuth | `/oauth2/token`, `/oauth2/revoke` |
| 계좌 | `/api/dostk/acnt` |
| 주문 | `/api/dostk/ordr` |
| 시세 | `/api/dostk/mrkcond` |
| 종목정보 | `/api/dostk/stkinfo` |
| 차트 | `/api/dostk/chart` |
| 업종 | `/api/dostk/sect` |
| 테마 | `/api/dostk/thme` |
| 순위 | `/api/dostk/rkinfo` |
| 기관/외국인 | `/api/dostk/frgnistt` |
| ELW | `/api/dostk/elw` |
| ETF | `/api/dostk/etf` |
| 공매도 | `/api/dostk/shsa` |
| 대차거래 | `/api/dostk/slb` |
| 신용주문 | `/api/dostk/crdordr` |
| WebSocket | `/api/dostk/websocket` |

### 4.2 주문 API (POST /api/dostk/ordr)

#### 매수 (kt10000) / 매도 (kt10001)
```json
{
  "dmst_stex_tp": "01",
  "stk_cd": "005930",
  "ord_qty": 10,
  "trde_tp": "00",
  "ord_uv": 70000,
  "cond_uv": null
}
```

| 필드 | 설명 | 값 |
|------|------|----|
| `dmst_stex_tp` | 거래소 구분 | "01" KOSPI, "02" KOSDAQ, "03" KONEX |
| `stk_cd` | 종목코드 | 6자리 |
| `ord_qty` | 주문수량 | |
| `trde_tp` | 주문유형 | "00" 지정가, "01" 시장가, ... |
| `ord_uv` | 주문가격 | 시장가면 null/0 |
| `cond_uv` | 조건가격 | 선택 |

**응답:**
```json
{
  "return_code": 0,
  "return_msg": "...",
  "ord_no": "주문번호",
  "dmst_stex_tp": "01"
}
```

#### 정정 (kt10002)
```json
{
  "dmst_stex_tp": "01",
  "orig_ord_no": "원주문번호",
  "stk_cd": "005930",
  "mdfy_qty": 5,
  "mdfy_uv": 71000,
  "mdfy_cond_uv": null
}
```

**응답:** `{ "ord_no", "base_orig_ord_no", "mdfy_qty", "dmst_stex_tp" }`

#### 취소 (kt10003)
```json
{
  "dmst_stex_tp": "01",
  "orig_ord_no": "원주문번호",
  "stk_cd": "005930",
  "cncl_qty": 0
}
```
> `cncl_qty`=0 → 잔량 전부 취소

**응답:** `{ "ord_no", "base_orig_ord_no", "cncl_qty" }`

### 4.3 시세 API (POST /api/dostk/mrkcond)

#### 시세표성정보 (ka10007) — 현재가
```json
{ "stk_cd": "005930" }
```

**응답 주요 필드:**
| 필드 | 설명 |
|------|------|
| `stk_nm` | 종목명 |
| `stk_cd` | 종목코드 |
| `cur_prc` | 현재가 |
| `open_pric` | 시가 |
| `high_pric` | 고가 |
| `low_pric` | 저가 |
| `flu_rt` | 등락률 |
| `pred_close_pric` | 전일종가 |
| `pred_trde_qty` | 전일거래량 |
| `flo_stkcnt` | 상장주식수 |
| `upl_pric` | 상한가 |
| `lst_pric` | 하한가 |

#### 호가 (ka10004)
```json
{ "stk_cd": "005930" }
```

#### 일별주가 (ka10086)
```json
{ "stk_cd": "005930", "qry_dt": "20260307", "indc_tp": "..." }
```

### 4.4 계좌 API (POST /api/dostk/acnt)

#### 예수금 (kt00001)
```json
{ "qry_tp": "..." }
```
**응답:** `{ "entr" (예수금), "profa_ch" (증거금현금), ... }`

#### 계좌평가현황 (kt00004)
```json
{ "qry_tp": false, "dmst_stex_tp": "..." }
```
**응답:** `{ "tot_pur_amt", "tot_evlt_amt", "tot_evlt_pl", ... }`

#### 계좌평가잔고내역 (kt00018) — 잔고 + 보유종목
```json
{ "qry_tp": "...", "dmst_stex_tp": "..." }
```
**응답:** `{ "tot_pur_amt", "tot_evlt_amt", "tot_evlt_pl", ...종목별 내역 }`

#### 미체결 (ka10075)
```json
{
  "all_stk_tp": "...",
  "trde_tp": "...",
  "stex_tp": "...",
  "stk_cd": ""
}
```
**응답:** `{ "oso": [{ "acnt_no", "ord_no", "stk_cd", ... }] }`

#### 체결 (ka10076)
```json
{
  "qry_tp": "...",
  "sell_tp": "...",
  "stex_tp": "...",
  "stk_cd": "",
  "ord_no": ""
}
```

## 5. WebSocket 실시간 시세

**URL:** `wss://api.kiwoom.com:10000/api/dostk/websocket`

### 구독 메시지
```json
{
  "ServiceName": "REG",
  "GroupId": "1",
  "Refresh": "1",
  "Data": [{
    "Item": ["005930", "000660"],
    "Type": ["0B", "0D"]
  }]
}
```

### 서비스 코드
| 코드 | 설명 |
|------|------|
| `00` | 주문체결 |
| `04` | 잔고 |
| `0A` | 주식기세 |
| `0B` | 주식체결 |
| `0C` | 주식우선호가 |
| `0D` | 주식호가잔량 |
| `0E` | 주식시간외호가 |
| `0H` | 주식예상체결 |
| `0J` | 업종지수 |
| `0s` | 장시작시간 |
| `1h` | VI발동/해제 |

### 구독 해제
```json
{ "ServiceName": "REMOVE", "GroupId": "1", "Refresh": "1", "Data": [...] }
```

## 6. KIS vs 키움 비교

| 항목 | KIS | 키움 |
|------|-----|------|
| HTTP Method | GET/POST 혼용 | **전부 POST** |
| API 식별 | `tr_id` 헤더 | `api-id` 헤더 |
| 인증 Body | `appkey` + `appsecret` | `appkey` + `secretkey` |
| 토큰 응답 | `access_token` | `token` |
| 토큰 만료 | `expires_in` (초) | `expires_dt` (날짜문자열) |
| 계좌번호 | Body에 `CANO`+`ACNT_PRDT_CD` | **불필요** (서버에서 계좌 자동 매핑) |
| 종목코드 필드 | `PDNO`, `FID_INPUT_ISCD` 등 | `stk_cd` (통일) |
| 현재가 필드 | `stck_prpr` | `cur_prc` |
| 주문번호 필드 | `ODNO` | `ord_no` |
| 응답 구조 | `{ "output": {...} }` | `{ "return_code": 0, ...flat }` |
| WS 포트 | 기본 | `:10000` |
| 연속조회 | 별도 파라미터 | `cont-yn`/`next-key` 헤더 |

## 7. API 호출 제한 (이용약관 제11조)

- 조회: **초당 5건**
- 주문: **초당 5건**
- 실시간 조건검색: 로그인당 10건

> KIS는 초당 20건이었으므로, 키움은 rate_limiter를 5 CPS로 설정해야 함

## 8. 미확인 사항 (공식 가이드에서 확인 필요)

- [ ] 주문 응답에 체결 상태(submitted/filled) 필드가 있는지
- [x] ~~호출 제한 (초당 N건) 수치~~ → 조회 5건/초, 주문 5건/초
- [ ] 모의투자 시 api-id가 동일한지 또는 별도인지
- [ ] WebSocket 체결 통보(00) 응답 필드 구조
- [ ] 토큰 만료 시간 (24시간? 다른 값?)
