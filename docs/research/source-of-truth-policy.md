# 데이터 정본(Source of Truth) 우선순위 정책

> 작성일: 2026-03-07

StockVision이 수집하는 모든 데이터 도메인에 대해,
어떤 소스를 정본으로 삼고, 어떤 소스를 보조/대체로 두는지 정의한다.

기반: `docs/research/collectible-data-inventory.md`

---

## 0. 용어 정의

| 용어 | 의미 |
|------|------|
| **정본** | 해당 데이터의 법적/제도적 원천, 또는 가장 정확한 1차 소스 |
| **보조 소스** | 정본 불가 시 사용하는 대체 소스 (정확도/신선도 열위) |
| **편의 소스** | 정본이 아니나 접근이 쉬워 개발/테스트에 활용. 운영에서는 폴백만 |
| **콘텐츠 소스** | 정본이 존재하지 않는 비구조화 데이터 (뉴스, 감성, 리포트) |
| **DataProvider** | 구조화된 수치 데이터 수집 ABC (`cloud_server/data/`) |
| **BrokerAdapter** | 실시간 시세 + 주문 실행 ABC (`sv_core/broker/`) |
| **ContentProvider** | 비구조화 데이터 수집 ABC (향후, v2+) |

---

## 1. 소스별 성격 분류

각 소스가 StockVision에서 어떤 위치인지 먼저 분류한다.

| 소스 | 성격 | 근거 |
|------|------|------|
| **DART (OpenDart)** | 법정 정본 | 금감원 전자공시시스템. 재무제표·배당·공시의 법적 원천 |
| **KRX 정보데이터** | 제도 정본 | 한국거래소 공식 데이터. 종가·거래량·수급의 확정 원천 |
| **한국은행 ECOS** | 제도 정본 | 한국은행 공식 통계. 거시경제 지표의 유일한 원천 |
| **공공데이터포털** | 공식 유통 채널 | 원천은 금융위/KRX. 메타데이터(상장종목)의 유통 창구 |
| **KIS REST API** | 증권사 정본 | 한국투자증권 공식 API. 실시간 시세·주문의 정본 (해당 증권사) |
| **키움 REST/WS** | 증권사 정본 | 키움증권 공식 API. 실시간 시세·주문의 정본 (해당 증권사) |
| **SEIBro (한국예탁결제원)** | 제도 정본 (배당 지급/기업행위) | 한국예탁결제원이 실배당 지급 처리. 기업행위 확정 데이터 보유. API 미확인 (P1 조사) |
| **yfinance** | 편의 소스 | Yahoo Finance 비공식 래퍼. 한국 주식은 지연·불완전. 글로벌 지수/환율에는 유용 |
| **네이버 금융** | 콘텐츠/보조 | 스크래핑 기반. 법적 리스크. 커뮤니티·뉴스 링크 소스 |
| **Google Trends** | 콘텐츠 소스 | 관심도 지표. 정본 개념 없음 |

### 핵심 판단

1. **한국 주식 재무 데이터의 정본은 DART다.**
   - 법적 공시 의무에 따라 제출되는 원천 데이터
   - yfinance 한국 재무는 대형주만 부분 지원, 신뢰도 낮음 → 폴백조차 비권장

2. **실시간 현재가/호가/체결/주문의 정본은 증권사 API다.**
   - KIS 또는 키움. 유저 키로 로컬 서버에서 직접 접근
   - cloud_server의 서비스 키 시세는 내부 수집용이지, 유저 실거래용이 아님

3. **KRX 데이터는 종가 확정 후 집계 데이터의 정본이다.**
   - 일봉 종가, 거래량, 투자자별 매매동향, 시가총액 순위 등
   - 실시간 데이터는 제공하지 않음 → 장중 시세의 정본이 아님

4. **공공데이터포털은 메타데이터 유통 채널이다.**
   - 원천은 금융위원회/KRX. 공공데이터포털은 API 형태로 재가공하여 배포
   - StockMaster(상장종목 목록)의 소스로 적합. 시세/재무 데이터는 미제공

5. **yfinance는 한국 주식에서 편의/폴백 소스로만 허용한다.**
   - 글로벌 지수(S&P 500, NASDAQ 등), 환율, 해외 주식: 1차 소스로 사용 가능
   - 한국 주식 가격: KIS/키움 미가용 시 폴백. 15~20분 지연, 종가 불일치 가능
   - 한국 주식 재무: 사용 금지 (대형주만 부분 지원, 오류 빈번)

6. **네이버 금융/커뮤니티 데이터는 콘텐츠 소스로 분리한다.**
   - 정본이 아님. 스크래핑 기반으로 법적 리스크 존재
   - ContentProvider(향후) 영역. DataProvider에 넣지 않음

---

## 2. 도메인별 정본 정의

> **"정본"과 "수집 경로"는 다르다.**
> 정본 = 누가 데이터를 확정/인증하는가 (변하지 않음).
> 수집 경로 = 우리가 실제로 어디서 가져오는가 (구현 단계에 따라 바뀜).
> 이 섹션은 **정본**만 정의한다. 수집 경로는 §5(폴백 정책)와 §6(단계별 적용)에서 다룬다.

### 2.1 가격/시세

| 데이터 항목 | 정본 (확정 주체) | 정본 근거 | 허용 지연 | 책임 | 범위 | 단계 |
|------------|-----------------|----------|----------|------|------|------|
| **일봉 OHLCV** (한국) | KRX | KRX가 종가 확정. 증권사/yfinance는 KRX 확정가를 재배포 | T+1 (장 마감 후) | cloud | DataProvider | P0 |
| **일봉 OHLCV** (글로벌) | 각국 거래소 | yfinance가 유일한 무료 접근 경로 | T+1 | cloud | DataProvider | P0 |
| **현재가 (실시간)** | KRX (체결 원천) | 증권사 WS는 KRX 체결 데이터를 유저에게 중계 | 0 (틱) | **local** | BrokerAdapter | P0 |
| **현재가 (지연 스냅샷)** | KRX (체결 원천) | cloud는 종가/캐시 기반 스냅샷만 제공 (아래 주의사항 참조) | 수분~T+1 | cloud | DataProvider | P0 |
| **분봉** | KRX (체결 원천) | 증권사가 KRX 체결을 집계하여 제공 | 분 단위 | cloud/local | DataProvider | P1 |
| **호가 (10호가)** | KRX (호가 원천) | 증권사만 실시간 제공 | 0 (실시간) | **local** | BrokerAdapter | P1 |
| **체결 내역** | KRX (체결 원천) | 증권사만 실시간 제공 | 0 (실시간) | **local** | BrokerAdapter | P1 |
| **시간외 호가** | KRX | 키움 WS만 제공 | 0 | **local** | BrokerAdapter | P2 |
| **52주 고저** | KRX | 일봉에서 계산 가능 | 일 단위 | cloud | DataProvider | P0 |

**주의사항:**
- **정본 vs 수집 경로**: 한국 주식 일봉의 정본은 KRX이지만, KRX API를 직접 사용하지 않을 수 있다. 증권사 REST나 yfinance로 수집한 값도 KRX 확정가의 재배포이므로 정본 체인은 유지된다. 단, yfinance는 1~2원 반올림 오차 가능
- **cloud 지연 스냅샷의 정의**: cloud_server가 제공하는 "현재가"는 **장 마감 후 종가 캐시 또는 수분 이상 지연된 REST 조회 결과**다. 실시간 시세 스트리밍이 아니며, 매매 판단 근거로 사용할 수 없다. 용도는 종목 상세 페이지 표시와 AI 분석 입력에 한정
- 장중 가격 수집은 증권사 API 필수. KRX는 사후 데이터만 제공

### 2.2 지수/시장

| 데이터 항목 | 정본 (확정 주체) | 정본 근거 | 허용 지연 | 책임 | 범위 | 단계 |
|------------|-----------------|----------|----------|------|------|------|
| **코스피/코스닥 지수** | KRX | KRX가 산출·발표. 증권사/yfinance는 KRX 산출값 재배포 | T+1 (종가) / 실시간 (WS) | cloud (종가) / local (실시간) | DataProvider (종가) | P0 |
| **업종별 지수** | KRX | KRX가 산출. 증권사 API로 수집 가능 | T+1 | cloud | DataProvider | P1 |
| **해외 지수** (S&P, NASDAQ 등) | 각국 거래소 | yfinance가 유일한 무료 접근 경로 | 15~20분 | cloud | DataProvider | P0 |
| **환율 (기준)** | 한국은행 | 한국은행이 매매기준율 고시 | 일 단위 | cloud | DataProvider | P0 |
| **환율 (장중 근사)** | 각 FX 마켓 | yfinance로 추적 (편의). 공식 환율 아님 | 15~20분 | cloud | DataProvider | P0 |
| **원자재 (원유/금)** | 각 상품거래소 | yfinance가 유일한 무료 접근 경로 | 15~20분 | cloud | DataProvider | P1 |
| **테마 정보** | 해당 없음 | 키움 독자 분류 (정본 개념 없음, 독점 데이터) | 일 단위 | cloud | DataProvider | P2 |

### 2.3 재무

| 데이터 항목 | 정본 (확정 주체) | 정본 근거 | 허용 지연 | 책임 | 범위 | 단계 |
|------------|-----------------|----------|----------|------|------|------|
| **손익계산서** | DART (금감원) | 자본시장법에 의한 법정 공시. 유일한 원천 | 분기 | cloud | DataProvider | P0 |
| **재무상태표** | DART (금감원) | 동일 | 분기 | cloud | DataProvider | P0 |
| **현금흐름표** | DART (금감원) | 동일 | 분기 | cloud | DataProvider | P0 |
| **PER/PBR/ROE/EPS** | DART (계산) | DART 재무제표 + KRX 시가총액으로 산출 | 분기 | cloud | DataProvider | P0 |
| **시가총액** | KRX | KRX가 공식 산출·발표 | 일 단위 | cloud | DataProvider | P1 |
| **발행주식수** | DART/KRX | DART 공시 또는 KRX 종목정보 | 이벤트 시 | cloud | DataProvider | P1 |

**주의사항:**
- yfinance 한국 재무 데이터는 **사용 금지** — 대형주만 부분 지원, 데이터 불일치 빈번
- PER/PBR 등 비율 지표는 DART 재무제표 원본에서 직접 계산하거나 DART DS003 API 사용
- yfinance 재무는 미국 주식에 한해서만 1차 소스로 허용 (한국은 폴백으로도 불가)

### 2.4 수급/투자자

| 데이터 항목 | 정본 (확정 주체) | 정본 근거 | 허용 지연 | 책임 | 범위 | 단계 |
|------------|-----------------|----------|----------|------|------|------|
| **기관/외국인 매매동향** | KRX | KRX가 투자자별 매매 집계·발표 | T+1 | cloud | DataProvider | P1 |
| **개인 매매동향** | KRX | KRX 집계 | T+1 | cloud | DataProvider | P1 |
| **공매도 잔고** | KRX | KRX가 공시 의무 | T+1 | cloud | DataProvider | P2 |
| **대차거래** | 금융투자협회/증권사 | 증권사별 집계. 통합 정본 없음 | T+1 | cloud | DataProvider | P2 |
| **내부자 거래** | DART (금감원) | 법정 공시 (임원·주요주주 특정증권 거래보고) | 이벤트 시 | cloud | DataProvider | P2 |
| **대량보유 변동** | DART (금감원) | 법정 공시 (5% 이상 보유 변동) | 이벤트 시 | cloud | DataProvider | P2 |
| **프로그램 매매** | KRX | KRX 집계 | T+1 | cloud | DataProvider | P2 |

### 2.5 배당/기업행위

| 데이터 항목 | 정본 (확정 주체) | 정본 근거 | 허용 지연 | 책임 | 범위 | 단계 |
|------------|-----------------|----------|----------|------|------|------|
| **배당 결의 (금액/비율)** | DART (금감원) | 법정 공시 (배당에 관한 사항). 주주총회 결의 후 공시 | 분기 | cloud | DataProvider | P0 |
| **배당락일** | KRX | KRX가 배당락일 확정·고시 | 이벤트 시 | cloud | DataProvider | P0 |
| **배당 지급일/지급 내역** | SEIBro (예탁원) | 한국예탁결제원이 실배당 지급 처리. 향후 정본 후보 | 이벤트 시 | cloud | DataProvider | P1 |
| **배당수익률** | 계산 (DART + KRX) | DART 배당금 ÷ KRX 주가. StockVision 내부 산출 | 분기 | cloud | DataProvider | P0 |
| **주식 분할/병합** | DART (금감원) | 법정 공시 | 이벤트 시 | cloud | DataProvider | P1 |
| **유상/무상증자** | DART (금감원) | 법정 공시 (주요사항보고서) | 이벤트 시 | cloud | DataProvider | P1 |
| **합병/분할 등 구조변경** | DART (금감원) | 법정 공시 | 이벤트 시 | cloud | DataProvider | P2 |
| **실적발표일** | DART | 공시 일정 | 분기 | cloud | DataProvider | P1 |
| **VI 발동/해제** | KRX (변동성완화장치) | 증권사 WS로만 실시간 수신 가능 | 0 (실시간) | **local** | BrokerAdapter | P2 |
| **장시작시간** | KRX | 증권사 WS로 수신 | 0 | **local** | BrokerAdapter | P2 |

**주의사항:**
- **기업행위(corporate actions)**: 배당, 분할, 증자, 합병 등 주가에 영향을 미치는 이벤트 포괄. 정본은 DART 공시
- **SEIBro (한국예탁결제원)**: 실배당 지급 데이터의 정본. 현재 API 미확인. P1에서 조사 후 수집 경로 결정
- **배당락일과 배당 결의는 정본이 다르다**: 결의는 DART 공시, 배당락일은 KRX가 확정

### 2.6 공시

| 데이터 항목 | 정본 (확정 주체) | 정본 근거 | 허용 지연 | 책임 | 범위 | 단계 |
|------------|-----------------|----------|----------|------|------|------|
| **기업 공시 (전체)** | DART (금감원) | 자본시장법에 의한 법적 전자공시 시스템 | 시간 단위 | cloud | DataProvider | P2 |
| **사업/감사보고서** | DART (금감원) | 법정 공시 | 분기 | cloud | DataProvider | P2 |
| **주요사항보고** | DART (금감원) | 법정 공시 | 이벤트 시 | cloud | DataProvider | P2 |

**주의사항:**
- 공시 메타데이터(제목, 일시, 종류) → DataProvider로 수집 (구조화)
- 공시 본문의 자연어 분석 → AI 파이프라인(ContentProvider 영역)

### 2.7 거시경제

| 데이터 항목 | 정본 (확정 주체) | 정본 근거 | 허용 지연 | 책임 | 범위 | 단계 |
|------------|-----------------|----------|----------|------|------|------|
| **기준금리** | 한국은행 | 한국은행 금융통화위원회가 결정·발표 | 이벤트 시 | cloud | DataProvider | P2 |
| **CPI/GDP/실업률** | 한국은행/통계청 | 한국은행 ECOS 또는 통계청이 공식 발표 | 월/분기 | cloud | DataProvider | P2 |
| **환율 (매매기준율)** | 한국은행 | 한국은행이 매매기준율 고시 | 일 단위 | cloud | DataProvider | P0 |
| **통화량 (M2)** | 한국은행 | 한국은행 통계 | 월 | cloud | DataProvider | P2 |
| **미국 국채 수익률** | 미 재무부 | yfinance가 유일한 무료 접근 경로 | 15~20분 | cloud | DataProvider | P2 |
| **한국 국채 수익률** | 한국은행 | 한국은행 ECOS 통계 | 일 단위 | cloud | DataProvider | P2 |

**주의사항:**
- 환율(장중 근사)은 §2.2에서 다룸 (정본이 아닌 편의 추적)

### 2.8 플랫폼 동향

| 데이터 항목 | 정본 (확정 주체) | 정본 근거 | 허용 지연 | 책임 | 범위 | 단계 |
|------------|-----------------|----------|----------|------|------|------|
| **거래대금 순위** | KRX | KRX가 집계·발표 | T+1 | cloud | DataProvider | P2 |
| **시가총액 순위** | KRX | KRX 공식 산출 | T+1 | cloud | DataProvider | P2 |
| **상한가/하한가** | KRX | KRX가 가격제한폭 확정 | T+1 | cloud | DataProvider | P2 |
| **신고가/신저가** | KRX | 일봉 기반 KRX 계산 | T+1 | cloud | DataProvider | P2 |
| **거래량 급증** | 계산 (StockVision) | 일봉 데이터에서 내부 산출. 정본 없음 | T+1 | cloud | DataProvider | P2 |
| **외국인 순매수 상위** | KRX | KRX 투자자별 매매 집계 | T+1 | cloud | DataProvider | P2 |
| **ETF 자금 유출입** | KRX | KRX 집계 | T+1 | cloud | DataProvider | P2 |

### 2.9 콘텐츠/감성 (정본 없음 — ContentProvider 영역)

| 데이터 항목 | 소스 | 수집 방법 | 정본 여부 | 책임 | 범위 | 단계 |
|------------|------|----------|----------|------|------|------|
| **한국어 뉴스** | 네이버 뉴스 등 | 크롤링/API | 정본 없음 (집합) | cloud | ContentProvider | P3 |
| **영문 뉴스** | yfinance `news` | API | 편의 소스 | cloud | ContentProvider | P3 |
| **증권사 리포트** | 네이버 금융 | 스크래핑 | 정본 없음 (집합) | cloud | ContentProvider | P3 |
| **목표가/추천** | 증권사 리포트 | 크롤링 | 출처별 상이 | cloud | ContentProvider | P3 |
| **네이버 종목토론방** | 네이버 금융 | 스크래핑 | 정본 없음 | cloud | ContentProvider | P3 |
| **DC 주식갤** | DCInside | 스크래핑 | 정본 없음 | cloud | ContentProvider | P3 |
| **검색량 추이** | Google Trends | API | Google 독점 | cloud | ContentProvider | P3 |
| **EPS 추정치** | FnGuide | 유료/크롤링 | FnGuide 독점 | cloud | ContentProvider | P3 |
| **ESG 점수** | KCGS | 유료/크롤링 | KCGS 독점 | cloud | ContentProvider | P3 |

**원칙**: 이 영역은 "정본"이 아니라 "분석 입력" 데이터. 수집 시 출처·시점을 반드시 기록.

### 2.10 종목 메타데이터

| 데이터 항목 | 정본 (확정 주체) | 정본 근거 | 허용 지연 | 책임 | 범위 | 단계 |
|------------|-----------------|----------|----------|------|------|------|
| **상장종목 목록** | KRX | KRX가 상장 승인·유지·폐지 결정 | 일 단위 | cloud | 기존 서비스 | P0 |
| **종목 코드/이름** | KRX | KRX가 부여 | 일 단위 | cloud | 기존 서비스 | P0 |
| **시장 구분 (KOSPI/KOSDAQ)** | KRX | KRX가 결정 | 이벤트 시 | cloud | 기존 서비스 | P0 |
| **관리종목/투자주의 지정** | KRX | KRX가 지정·해제 | 이벤트 시 | cloud | DataProvider | P1 |
| **상장폐지 사유/일정** | KRX | KRX가 결정 | 이벤트 시 | cloud | DataProvider | P1 |
| **업종 분류** | KRX | KRX가 GICS/KSIC 기반 분류 | 이벤트 시 | cloud | DataProvider | P1 |
| **ISIN** | KRX (한국예탁결제원 발급) | 국제 표준 (ISO 6166) | 이벤트 시 | cloud | 기존 서비스 | P1 |

**주의사항:**
- **공공데이터포털은 유통 채널이지 정본이 아니다**: 원천은 KRX(금융위원회 인가). 공공데이터포털은 KRX 데이터를 API로 재가공·배포
- **KRX KIND**: 상장법인 관리종목/투자주의/거래정지 등 시장조치 정보의 정본. P1에서 수집 경로 조사
- 현재 StockMaster는 공공데이터포털에서 수집 (P0). 정본 체인: KRX → 금융위 → 공공데이터포털 → StockVision

---

## 3. 책임 분리

### cloud_server가 수집/정규화할 데이터

| 데이터 | 소스 | 수집 주기 | 저장 |
|--------|------|----------|------|
| 종목 메타데이터 (StockMaster) | 공공데이터포털 | 일 1회 (08:00) | DB 영구 |
| corp_code 매핑 | DART 고유번호 API | 주 1회 | DB 영구 |
| 일봉 OHLCV | KIS/키움 REST → yfinance 폴백 | 일 1회 (16:00) | DB 5년+ |
| 지수/환율 (6종목) | yfinance | 일 1회 (17:00) | DB 5년+ |
| 재무제표 | DART DS003 | 분기 (실적 시즌) | DB 영구 |
| 배당 정보 | DART DS002 | 분기 | DB 영구 |
| 공시 메타 | DART DS001 | 시간 단위 (P2) | DB 영구 |
| 거시경제 | ECOS | 월 1회 (P2) | DB 영구 |
| 수급/동향 | KRX/키움 | 일 1회 (P1-P2) | DB 1년+ |
| 현재가 (지연, 캐시) | KIS/키움 REST → yfinance | on-demand (API 요청 시) | 캐시 TTL 30초 |

### local_server에서만 다룰 데이터

| 데이터 | 소스 | 근거 |
|--------|------|------|
| 실시간 현재가/호가/체결 | 키움 WS (유저 키) | 유저 인증 필요, 실시간 스트리밍 |
| 주문 실행/취소 | 키움 REST (유저 키) | 유저 계좌 접근, 매매 판단은 로컬 |
| 잔고/포지션 | 키움 REST (유저 키) | 유저 계좌 |
| VI 발동/해제 | 키움 WS (유저 키) | 실시간 이벤트 |
| 장시작시간 | 키움 WS (유저 키) | 실시간 이벤트 |
| 시간외 호가 | 키움 WS (유저 키) | 실시간 |
| 체결 로그 | 로컬 SQLite | 로컬 전용 |

**분리 원칙**: 유저 키가 필요하거나 실시간 스트리밍인 데이터는 local_server.
서비스 키 또는 키 불필요한 배치/조회 데이터는 cloud_server.

---

## 4. 내부 표준 식별자

| 식별자 | 용도 | 형식 | 정본 소스 | 비고 |
|--------|------|------|----------|------|
| **symbol** | 종목 코드 (가격 데이터의 키) | 6자리 숫자 (`005930`) | 공공데이터포털/KRX | StockMaster PK |
| **corp_code** | 기업 고유번호 (재무 데이터의 키) | 8자리 숫자 (`00126380`) | DART 고유번호 API | StockMaster.corp_code FK |
| **ISIN** | 국제증권식별번호 | 12자 (`KR7005930003`) | KRX/공공데이터포털 | 현재 미사용, 향후 확장 시 |
| **yf_symbol** | yfinance 심볼 | `005930.KS` | 프로바이더 내부 변환 | 외부 노출 안 함 |
| **broker_symbol** | 증권사 내부 코드 | 증권사마다 다름 | 프로바이더 내부 변환 | 외부 노출 안 함 |

**규칙**:
- 외부 API 호출 시 프로바이더 내부에서 변환 (symbol → yf_symbol 등)
- DB 저장 및 API 응답은 항상 내부 표준 식별자 사용
- 기업 단위 데이터(재무, 배당, 공시)는 `corp_code`, 종목 단위 데이터(가격, 시세)는 `symbol`

---

## 5. 폴백 정책

### 가격 데이터 폴백 체인

```
한국 주식 일봉:
  KIS REST → 키움 REST → yfinance (.KS/.KQ) → 실패 (로그 + 빈값)

한국 주식 현재가 (cloud, 지연):
  KIS REST → 키움 REST → yfinance → DB 최신 종가 (stale)

글로벌 지수/환율:
  yfinance → 실패 (로그 + 빈값)

실시간 시세 (local):
  BrokerAdapter.subscribe_quotes() → 실패 시 재연결 (폴백 없음)
```

### 재무/배당 폴백 체인

```
한국 재무:
  DART → 실패 (로그 + 빈값)
  yfinance 한국 재무는 폴백으로도 사용하지 않음 (신뢰도 부족)

한국 배당 (결의/금액):
  DART → yfinance (교차 검증용) → 실패

한국 배당 (지급 내역):
  SEIBro (P1 조사 후) → DART → 실패

기업행위 (분할/증자/합병):
  DART → 실패 (유일한 공시 원천)

미국 주식 재무/배당 (향후):
  yfinance → 실패
```

### 폴백 공통 규칙

1. **타임아웃**: 프로바이더별 10초. 초과 시 다음으로 폴백
2. **로깅**: 폴백 발생 시 `logger.warning(provider, error, symbol)`. 모니터링 대상
3. **stale 캐시**: DB에 이전 수집 데이터 있으면 `collected_at`과 함께 반환. 호출부가 신선도 판단
4. **전체 실패**: 빈값 반환 + `logger.error`. 클라이언트에 에러 전파하지 않음 (graceful degradation)

---

## 6. P0~P3 단계별 수집 경로

> §2의 "정본"은 데이터를 누가 확정하는가. 이 섹션은 **우리가 실제로 어디서 가져오는가**(수집 경로)를 정의한다.
> 수집 경로는 구현 단계와 비용에 따라 바뀔 수 있다. 정본은 바뀌지 않는다.

### P0 — 현재 DataProvider spec 범위

| 도메인 | 수집 경로 | 폴백 | 구현 모듈 | 비고 |
|--------|----------|------|----------|------|
| 일봉 OHLCV (한국) | yfinance | 없음 | YFinanceProvider | **임시**. KIS/키움 서비스 키 확보 후 교체 (P1) |
| 일봉 OHLCV (글로벌) | yfinance | 없음 | YFinanceProvider | |
| 현재가 (지연 스냅샷) | yfinance | DB 최신 종가 | YFinanceProvider | 임시. P1에서 KIS/키움으로 전환 |
| 재무제표 | DART DS003 | 없음 | DartProvider | |
| 배당 | DART DS002 | yfinance (교차검증) | DartProvider | |
| 지수/환율 (6종목) | yfinance | 없음 | 기존 YFinanceService | |
| 종목 메타 | 공공데이터포털 | stale 캐시 | 기존 stock_service | |
| corp_code 매핑 | DART 고유번호 ZIP | 없음 | DartProvider | |

### P1 — v1 확장

| 도메인 | 수집 경로 | 폴백 | 구현 모듈 | 비고 |
|--------|----------|------|----------|------|
| 일봉 (한국, 전환) | KIS/키움 REST | yfinance | KISProvider, KiwoomProvider | 정본 체인 정상화 |
| 분봉 | KIS/키움 REST | 없음 | KISProvider, KiwoomProvider | |
| 호가 10호가 | 키움/KIS WS (유저 키) | 없음 | BrokerAdapter (local) | |
| 투자자별 매매동향 | KRX 정보데이터 | 키움 `frgnistt` | KRXProvider (신규) | |
| 업종 지수 | KRX/키움 `sect` | 없음 | KRXProvider | |
| 관리종목/시장조치 | KRX KIND | 없음 | KRXProvider | |
| 배당 지급 내역 | SEIBro (조사 후 결정) | DART | 미정 | API 확인 필요 |

### P2 — AI 분석 파이프라인

| 도메인 | 수집 경로 | 폴백 | 구현 모듈 |
|--------|----------|------|----------|
| 기업 공시 (메타) | DART DS001 | 없음 | DartProvider 확장 |
| 거시경제 | 한국은행 ECOS API | 없음 | ECOSProvider (신규) |
| 공매도/대차 | KRX/키움 | 없음 | KRXProvider/KiwoomProvider 확장 |
| 테마/순위 | 키움 `thme`/`rkinfo` | 없음 | KiwoomProvider 확장 |
| VI 발동 | 키움 WS `1h` (유저 키) | 없음 | BrokerAdapter (local) |
| 플랫폼 동향 | KRX | 키움 | KRXProvider |

### P3 — ContentProvider 영역

| 도메인 | 수집 경로 | 방법 | 구현 모듈 |
|--------|----------|------|----------|
| 한국어 뉴스 | 네이버 뉴스 등 | 크롤링 | NewsProvider |
| 커뮤니티 감성 | 네이버 종토방, DC | 스크래핑 | CommunityProvider |
| 검색량 추이 | Google Trends | API | TrendsProvider |
| 증권사 리포트/목표가 | 네이버 금융 | 스크래핑 | 미정 |

---

## 7. 리스크와 예외 규칙

### 리스크

| 리스크 | 영향 | 대응 |
|--------|------|------|
| yfinance 한국 주식 종가 불일치 | 일봉 데이터 부정확 | P1에서 KIS/키움으로 교체. 교차 검증 로직 |
| DART API 분당 1000건 제한 | 대량 수집 시 throttle | 분기별 배치 수집, 관심종목 우선 |
| KIS 100거래일 일봉 제한 | 장기 히스토리 수집 불가 | 기간 분할 요청 또는 yfinance 보완 |
| 키움 5 CPS 제한 | 동시 요청 병목 | rate limiter 적용 |
| 네이버 스크래핑 법적 리스크 | 서비스 차단, 법적 분쟁 | P3에서만 사용, robots.txt 준수, 과도 요청 금지 |
| 공공데이터포털 서버 불안정 | 종목 메타 갱신 실패 | stale 캐시 사용 + 재시도 |

### 예외 규칙

1. **yfinance 한국 재무 사용 금지**: 폴백으로도 사용하지 않음. DART가 유일한 정본.
2. **실시간 데이터 cloud 중계 금지**: 아키텍처 원칙. cloud_server는 실시간 시세를 유저에게 중계하지 않음.
3. **콘텐츠 소스를 DataProvider에 넣지 않음**: 뉴스·감성·리포트는 별도 ContentProvider ABC.
4. **식별자 변환은 프로바이더 내부**: 외부 API에는 내부 symbol/corp_code만 노출. yf_symbol, broker_symbol은 내부 변환.
5. **stale 캐시 반환 시 collected_at 필수**: 호출부가 데이터 신선도를 판단할 수 있어야 함.

---

## 8. 요약 매트릭스

```
도메인           정본 (확정 주체)       P0 수집 경로   범위            단계
─────────────────────────────────────────────────────────────────────────────────
가격(한국)       KRX                   yfinance(임시) DataProvider    P0→P1 전환
가격(글로벌)     각국 거래소           yfinance       DataProvider    P0
지수(한국)       KRX                   yfinance       DataProvider    P0
지수(해외)       각국 거래소           yfinance       DataProvider    P0
재무             DART (금감원)         DART DS003     DataProvider    P0
배당/기업행위   DART/KRX/SEIBro       DART DS002     DataProvider    P0-P1
수급             KRX                   —              DataProvider    P1-P2
공시             DART (금감원)         —              DataProvider    P2
거시경제         한국은행              —              DataProvider    P2
플랫폼 동향     KRX                   —              DataProvider    P2
종목 메타       KRX                   공공데이터포털 기존 서비스     P0
실시간 시세     KRX (증권사 중계)     키움/KIS WS    BrokerAdapter   P0
주문/잔고       증권사                키움/KIS REST  BrokerAdapter   P0
뉴스/감성       정본 없음             —              ContentProvider P3
```

---

## 관련 문서

- `docs/research/collectible-data-inventory.md` — 전체 수집 가능 데이터 인벤토리
- `spec/data-provider/spec.md` — DataProvider 명세서
- `spec/data-provider/plan.md` — DataProvider 구현 계획서
- `docs/architecture.md` — 3프로세스 아키텍처
- `sv_core/broker/base.py` — BrokerAdapter ABC
