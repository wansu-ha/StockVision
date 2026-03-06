# 자동매매 플랫폼 벤치마크 조사

> 작성일: 2026-03-06 | 목적: rule-model 설계 참고 + v2 로드맵 근거

---

## 1. 한국 플랫폼

### 1.1 키움 영웅문 (조건검색 + 시스템트레이딩)

| 항목 | 방식 |
|------|------|
| 조건 정의 | 수식관리자 — 데이터 함수 + 산술/관계 연산자 조합 |
| 조건 개수 | 최대 20개 지표 조합 |
| 매수/매도 | 별도 신호검색식 (매수신호, 매도신호 분리) |
| 주문 설정 | 포지션 설정 + 신호시 주문처리 + 강제 청산 |
| 실행 방식 | HTS 내장 (PC 켜져있어야 함) |
| 스크리닝 | 조건검색식으로 전종목 실시간 스캔 가능 |
| 교차 조건 | 수식으로 골든크로스/데드크로스 구현 가능 |

**장점**: HTS 내장이라 별도 설치 불필요, 실시간 조건검색 강력
**단점**: HTS 종속 (PC 필수), 코딩 불가, 조건 공유 어려움, REST API로는 조건검색 미지원

> 참고: [키움 조건검색](https://download.kiwoom.com/hero4_help_new/0150.htm), [수식관리자](https://download.kiwoom.com/hero4_help_new/012.htm), [시스템트레이딩](https://download.kiwoom.com/hero4_help_new/011.htm)

### 1.2 젠포트 (인텔리퀀트)

| 항목 | 방식 |
|------|------|
| 조건 정의 | GUI 팩터 조합 (재무, 기술적, 모멘텀 등) |
| 매수 대상 | 유니버스/업종/테마/관심종목 중 선택 |
| 매수 조건 | 팩터 조건식 조합 → 전종목 필터링 → 우선순위 상위 N개 |
| 매도 조건 | 보유일 기반 + 퇴출(stop) 조건 + 만기매도 |
| 매수 가격 | 전일종가 외 17개 옵션 (시가, VWAP 등) |
| 최적화 | 백테스팅 전 최적값 추출 (최대 5개 파라미터) |
| 실행 방식 | 클라우드 자동매매 (PC 안 켜도 됨) |
| 수수료 | 월 구독 + 수익 기반 수수료 |

**조건 설정 구조**:
```
STEP 1: 기본 설정 (최대 종목 수, 보유일, 재매수 방지)
STEP 2: 유니버스 선택 (코스피/코스닥/전체)
STEP 3: 조건식 (팩터 조합, AND 로직)
STEP 4: 우선순위 (정렬 기준으로 상위 N개 선정)
STEP 5: 매수/매도 가격 기준
```

**장점**: 노코드 GUI, 클라우드 실행 (PC 불필요), 백테스팅 내장, 전종목 스크리닝
**단점**: 종목 선정형 (실시간 조건 매매 약함), 월 구독료, 법적 리스크 (클라우드가 매매)

> 참고: [젠포트 조건 설정](https://wikidocs.net/162074), [새포트 만들기](https://wikidocs.net/8686)

---

## 2. 해외 플랫폼

### 2.1 3Commas (Signal Bot)

| 항목 | 방식 |
|------|------|
| 조건 정의 | JSON 시그널 (`action: "buy"/"sell"`, `trigger_price`) |
| 조건 로직 | AND 로직 — 모든 파라미터 충족해야 실행 |
| 주문 설정 | `order: { amount, currency_type }` |
| 봇 유형 | Signal Bot, DCA Bot, Grid Bot |
| 트리거 | TradingView alert -> webhook -> 3Commas |
| DCA | 가격 하락 시 자동 추가 매수 (물타기), Safety Order 설정 |

**Signal Bot JSON 예시**:
```json
{
  "secret": "...",
  "timestamp": "{{timenow}}",
  "trigger_price": "{{close}}",
  "tv_exchange": "{{exchange}}",
  "tv_instrument": "{{ticker}}",
  "action": "enter_long",
  "bot_uuid": "...",
  "order": { "amount": "100", "currency_type": "quote" }
}
```

**장점**: TradingView 연동 강력, DCA/Grid 전략 내장, 멀티 거래소
**단점**: 자체 조건 빌더 약함 (TradingView 의존), 클라우드 실행, 월 구독료

> 참고: [3Commas Signal Bot JSON](https://help.3commas.io/en/articles/9374557-signal-bot-json-file-for-strategy-type), [Custom Signal](https://help.3commas.io/en/articles/8894481-signal-bot-json-file-in-custom-signal-type)

### 2.2 TradingView + Pineify (노코드 빌더)

| 항목 | 방식 |
|------|------|
| 조건 정의 | 비주얼 빌더로 지표 조합 -> Pine Script 자동 생성 |
| 조건 로직 | AND 조합 (모든 지표 충족 시 발동) |
| 실행 방식 | alert -> webhook -> 외부 봇 (3Commas, Alpaca 등) |
| 자체 실행 | 없음 (차트/분석 도구, 주문은 외부) |

**장점**: 가장 풍부한 차트/지표 라이브러리, 커뮤니티 스크립트
**단점**: 자체 주문 실행 없음, Pine Script 학습 곡선, 외부 브로커 연동 필요

> 참고: [Pineify](https://pineify.app/), [PineConnector No-code](https://docs.pineconnector.com/no-code)

### 2.3 Level2 (비주얼 전략 빌더)

| 항목 | 방식 |
|------|------|
| 조건 정의 | 드래그앤드롭 노드 기반 캔버스 |
| UI 패턴 | 블록을 캔버스에 놓고 연결선으로 로직 구성 |
| 백테스팅 | 실시간 + 히스토리컬 데이터 |
| 실행 방식 | 브로커 직접 연결 (Public 등) |
| 사용자 | 50,000+ 트레이더 |

**장점**: 진정한 비주얼 빌더 (드롭다운/텍스트 한계 극복), 직관적 UX
**단점**: 미국 주식 위주, 한국 증권사 미지원

> 참고: [Level2](https://www.trylevel2.com/), [Visual Strategy Builder](https://learn.trylevel2.com/docs/Broker/visual-strategy-builder)

### 2.4 오픈소스 (QuantConnect / Backtrader / Zipline)

| 항목 | QuantConnect | Backtrader | Zipline |
|------|-------------|------------|---------|
| 언어 | Python, C# | Python | Python |
| 전략 정의 | 클래스 기반 코드 | 클래스 기반 코드 | 함수 기반 코드 |
| 실행 | 클라우드 + 로컬 | 로컬 | 로컬 |
| 데이터 | 내장 (글로벌) | 외부 연결 | 외부 연결 |
| 한국 주식 | X | X (직접 연동) | X (직접 연동) |
| 자유도 | 최대 | 최대 | 최대 |

**장점**: 어떤 로직이든 구현 가능, 무료
**단점**: 코딩 필수, 한국 주식 데이터 직접 구축 필요

> 참고: [Backtrader vs QuantConnect vs Zipline](https://dev.to/tildalice/backtrader-vs-quantconnect-vs-zipline-setup-speed-test-4k01)

---

## 3. StockVision 포지셔닝 비교

| 비교 항목 | 키움 HTS | 젠포트 | 3Commas | Level2 | StockVision |
|-----------|---------|--------|---------|--------|-------------|
| 매수/매도 분리 | O (별도 신호) | O (별도 설정) | O (action) | O | O (buy/sell_conditions) |
| 조건 조합 | AND만 | AND | AND만 | AND/OR | **AND/OR** |
| 조건 타입 | 지표+가격 | 재무+기술 | 외부 시그널 | 지표+가격 | 가격+지표+거래량+컨텍스트 |
| cross 연산자 | O (수식) | X | X | O | **O (cross_above/below)** |
| 트리거 정책 | 고정 | 일 단위 | 시그널마다 | 커스텀 | **JSON (ONCE_PER_DAY, ONCE)** |
| 주문 설정 | GUI | GUI | JSON | GUI | **JSON (execution)** |
| 우선순위 | X | O (순위) | X | X | **O (priority)** |
| 노코드 | O (GUI) | O (GUI) | X (JSON) | O (드래그앤드롭) | v1: JSON, v2: 프론트 빌더 |
| 스크리닝 | O (전종목) | O (전종목) | X | O | **v1: X, v2: O** |
| DCA 전략 | X | X | O | X | **v2: O** |
| 실행 위치 | HTS (PC) | 클라우드 | 클라우드 | 클라우드 | **로컬 PC** |
| 법적 안전성 | O (본인 PC) | X (투자일임?) | X (해외) | X (해외) | **O (시스템매매)** |

### StockVision v1 차별점
- **AND/OR 조합**: 대부분 AND만 지원
- **로컬 실행**: 투자일임 회피 (젠포트/3Commas는 클라우드가 매매)
- **cross 연산자**: 골든크로스/데드크로스 1급 지원
- **trigger_policy**: 규칙 단위로 트리거 정책 설정
- **AI 컨텍스트**: 조건에 AI 분석 결과를 변수로 사용 (v2)

---

## 4. v2 따라잡기 과제

### 4.1 전종목 스크리닝

**현재**: 종목 지정형 (사용자가 종목 선택 + 조건 설정)
**목표**: 전 종목 대상 조건 필터링 -> 조건 부합 종목 자동 추출

**문제점**:
- 키움 REST API 초당 5건 제한 -> 2,500개 종목 스캔 시 약 8분
- 실시간 스크리닝 불가능 (키움 조건검색은 HTS 전용, REST 미지원)

**해결 방안**:

| 방안 | 데이터 소스 | 장점 | 단점 |
|------|-----------|------|------|
| A. 공공데이터 | 공공데이터포털 + FinanceDataReader | 무료, 약관 부담 제로 | 실시간 아님 (일봉 기준) |
| B. KRX 데이터 | data.krx.co.kr | 공식 데이터 | API 제한, 실시간 아님 |
| C. 클라우드 시세 활용 | 서비스 키 시세 DB | 이미 수집 중 | 유저에게 직접 제공 불가 (제5조3) |
| D. FinanceDataReader | 오픈소스 크롤러 | KRX 전종목 지원 | 크롤링 안정성 |

**권장 (방안 A+C 혼합)**:
1. 클라우드 서버가 서비스 키 시세 + 공공데이터로 **일봉 기반 스크리닝** 수행
2. 조건 부합 종목 목록을 컨텍스트로 로컬에 전달
3. 로컬은 해당 종목만 실시간 감시 + 주문
4. 유저에게 원시 시세 미제공 (가공된 "조건 부합 종목 목록"만 전달)

> 키움 제5조3 준수: 시세 원본이 아닌 "조건 부합 여부" (boolean)만 전달

**젠포트 참고**:
- 유니버스 선택 -> 팩터 조건 -> 우선순위 정렬 -> 상위 N개 구조
- 일 단위 리밸런싱 (장전 동시호가 매수)
- StockVision도 유사하게 "일봉 기반 종목 추천 + 실시간 진입 타이밍"으로 구성 가능

### 4.2 DCA (물타기/분할매수) 전략

**현재**: 고정 수량 1회 매수 (qty_type: "FIXED")
**목표**: 가격 하락 시 자동 추가 매수, 분할 매수/매도

**3Commas DCA 구조**:
```
초기 매수 (Base Order)
  -> 가격 -1% 하락 -> Safety Order 1 (추가 매수)
  -> 가격 -2.5% 하락 -> Safety Order 2 (추가 매수, 더 큰 금액)
  -> 가격 -5% 하락 -> Safety Order 3
  -> 목표가 도달 -> 전량 매도 (Take Profit)
```

**rule-model 확장안**:

```json
{
  "execution": {
    "order_type": "MARKET",
    "qty_type": "RATIO",
    "qty_value": 0.2,
    "dca": {
      "enabled": true,
      "max_safety_orders": 3,
      "price_deviation_pct": [1.0, 2.5, 5.0],
      "volume_scale": 1.5,
      "take_profit_pct": 3.0
    }
  }
}
```

**구현 고려사항**:
- `qty_type: "RATIO"` — 예산 비율 기반 수량 계산 (잔고 조회 필요)
- `qty_type: "AMOUNT"` — 금액 기반 수량 계산
- Safety Order별 가격 편차 + 수량 배율 설정
- Take Profit / Stop Loss 통합
- 평균 단가 계산 (DCA 특성)

### 4.3 비주얼 전략 빌더 (노코드)

**현재**: JSON 기반 규칙 (프론트에서 폼으로 입력)
**목표**: 드래그앤드롭 비주얼 빌더

**업계 UI 패턴 3가지**:

| 패턴 | 대표 | 설명 | 적합도 |
|------|------|------|--------|
| A. 폼 기반 | 젠포트, 키움 | 드롭다운 + 입력필드 조합 | v1 적합 |
| B. 블록 연결 | Level2, Scratch | 캔버스에 블록 배치 + 연결선 | 직관적이나 복잡 |
| C. 노드 그래프 | Unreal Blueprint, n8n | 노드 + 간선 그래프 | 자유도 최대, 러닝커브 |

**v1 (폼 기반) 구현**:
```
[조건 추가] 버튼
  -> 조건 카드:
     [타입: 지표 v] [필드: RSI(14) v] [연산자: <= v] [값: 30]
  -> [AND/OR 토글]
  -> 조건 카드:
     [타입: 가격 v] [필드: 현재가 v] [연산자: <= v] [값: 50000]
```

**v2 (블록 기반) 확장**:
- Level2 스타일의 드래그앤드롭 캔버스
- 조건 블록, 연산자 블록, 실행 블록을 연결
- 중첩 그룹 지원: `(A AND B) OR (C AND D)`
- 라이브러리: React Flow, Rete.js 등 노드 기반 에디터

**참고 프레임워크**:
- [React Flow](https://reactflow.dev/) — React 노드 기반 에디터
- [Rete.js](https://rete.js.org/) — 비주얼 프로그래밍 프레임워크
- [Blockly](https://developers.google.com/blockly) — Google의 블록 기반 에디터 (Scratch 스타일)

---

## 5. v2 로드맵 우선순위 제안

| 순위 | 기능 | 난이도 | 사용자 가치 | 근거 |
|------|------|--------|-----------|------|
| 1 | qty_type 확장 (RATIO, AMOUNT) | 낮음 | 높음 | execution JSON 수정만으로 가능 |
| 2 | 폼 기반 전략 빌더 고도화 | 중간 | 높음 | v1 프론트 빌더를 더 직관적으로 |
| 3 | 일봉 기반 스크리닝 | 높음 | 높음 | 클라우드 서버 + 공공데이터 연동 |
| 4 | DCA/분할매수 | 중간 | 중간 | execution에 dca 옵션 추가 |
| 5 | 비주얼 블록 빌더 | 높음 | 중간 | React Flow 기반, v2 후반 |
| 6 | 시간 조건 | 낮음 | 중간 | condition type에 "time" 추가 |
| 7 | 조건 그룹 중첩 | 중간 | 낮음 | (A AND B) OR (C AND D) |
| 8 | 규칙 체이닝 | 높음 | 낮음 | 규칙 A 체결 -> 규칙 B 활성화 |

---

## Sources

- [키움 조건검색](https://download.kiwoom.com/hero4_help_new/0150.htm)
- [키움 수식관리자](https://download.kiwoom.com/hero4_help_new/012.htm)
- [키움 시스템트레이딩](https://download.kiwoom.com/hero4_help_new/011.htm)
- [젠포트 조건 설정](https://wikidocs.net/162074)
- [젠포트 새포트 만들기](https://wikidocs.net/8686)
- [3Commas Signal Bot JSON](https://help.3commas.io/en/articles/9374557-signal-bot-json-file-for-strategy-type)
- [3Commas Custom Signal](https://help.3commas.io/en/articles/8894481-signal-bot-json-file-in-custom-signal-type)
- [3Commas DCA Bot](https://wundertrading.com/en/dca-trading)
- [DCA vs Grid Trading](https://medium.com/@alsgladkikh/comparing-strategies-dca-vs-grid-trading-2724fa809576)
- [Level2 Visual Strategy Builder](https://learn.trylevel2.com/docs/Broker/visual-strategy-builder)
- [Pineify](https://pineify.app/)
- [FinanceDataReader](https://github.com/FinanceData/FinanceDataReader)
- [KRX Data Marketplace](https://data.krx.co.kr/)
- [Backtrader vs QuantConnect vs Zipline](https://dev.to/tildalice/backtrader-vs-quantconnect-vs-zipline-setup-speed-test-4k01)
- [WunderTrading Bot 비교](https://wundertrading.com/journal/en/reviews/article/top-profitable-trading-bots)
- [React Flow](https://reactflow.dev/)
