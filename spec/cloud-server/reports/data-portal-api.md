# 공공데이터포털 KRX 상장종목정보 API

> 참조: 금융위원회_KRX상장종목정보 오픈API 활용가이드

## API 정보

| 항목 | 값 |
|------|---|
| API명 | GetKrxListedInfoService |
| 오퍼레이션 | getItemInfo (종목정보) |
| 엔드포인트 | `https://apis.data.go.kr/1160100/service/GetKrxListedInfoService/getItemInfo` |
| 인증 | serviceKey (공공데이터포털 인증키) |
| 전송 | REST (GET), SSL |
| 응답형식 | XML (기본) / JSON (`resultType=json`) |
| 갱신주기 | 일 1회 |
| 평균 응답 | 500ms, 30 tps |

## 요청 파라미터

| 파라미터 | 설명 | 필수 | 예시 |
|---------|------|------|------|
| serviceKey | 인증키 | O | (인코딩된 서비스키) |
| numOfRows | 한 페이지 결과 수 | | 1000 |
| pageNo | 페이지 번호 | | 1 |
| resultType | xml / json | | json |
| basDt | 기준일자 (정확히 일치) | | 20220919 |
| beginBasDt | 기준일자 >= 검색값 | | 20220919 |
| endBasDt | 기준일자 < 검색값 | | 20220920 |
| likeSrtnCd | 단축코드 부분 매칭 | | A000020 |
| itmsNm | 종목명 (정확히 일치) | | 동화약품 |
| likeItmsNm | 종목명 부분 매칭 | | 동화 |

## 응답 필드

| 필드 | 설명 | 예시 |
|------|------|------|
| basDt | 기준일자 (YYYYMMDD) | 20220919 |
| srtnCd | 단축코드 (앞에 알파벳 접두어) | A000020 |
| isinCd | ISIN 코드 | KR7000020008 |
| mrktCtg | 시장 구분 | KOSPI / KOSDAQ / KONEX |
| itmsNm | 종목명 | 동화약품 |
| crno | 법인등록번호 (외국회사 미제공) | 1101110043870 |
| corpNm | 법인명 | 동화약품(주) |

## 주의사항

1. **날짜 필터 필수** — 필터 없이 호출하면 전체 이력(160만건+) 반환. `beginBasDt`로 최근 날짜 필터 필요.
2. **srtnCd 접두어** — `A005930` 형태. StockMaster에는 `005930`(6자리)으로 저장하므로 앞 알파벳 제거.
3. **중복 데이터** — 여러 기준일자에 같은 종목이 반복 반환. dedup 처리 필요.
4. **외국회사** — `crno`(법인등록번호) 미제공.

## 에러 코드

| 코드 | 메시지 | 설명 |
|------|--------|------|
| 00 | NORMAL SERVICE | 정상 |
| 1 | APPLICATION_ERROR | 어플리케이션 에러 |
| 10 | INVALID_REQUEST_PARAMETER_ERROR | 잘못된 요청 파라미터 |
| 22 | LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR | 요청 횟수 초과 |
| 30 | SERVICE_KEY_IS_NOT_REGISTERED_ERROR | 미등록 서비스키 |
| 31 | DEADLINE_HAS_EXPIRED_ERROR | 기한만료 서비스키 |

## 구현 위치

- 수집 로직: `cloud_server/services/stock_service.py` → `fetch_krx_listed()`
- 스케줄: `cloud_server/collector/scheduler.py` → 매일 08:00 KST
- 환경변수: `KRX_LISTING_API_KEY` (`.env`)
