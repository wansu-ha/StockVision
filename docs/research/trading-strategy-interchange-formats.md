# 트레이딩 전략 교환 포맷 리서치

> 작성일: 2026-03-28 | 목적: StockVision 전략 공유/마켓플레이스 설계를 위한 표준 포맷 조사

---

## 핵심 결론

**범용 표준 교환 포맷은 존재하지 않는다.**

거래 전략 공유를 위한 단일 범용 표준은 2026년 현재 없다. 가장 가까운 것은:
- **FIXatdl**: 기관 영역 — 매개변수/UI 정의 XML, 전략 로직 미포함
- **Pine Script**: 리테일 영역 — 사실상(de facto) 플랫폼 종속 표준
- **Python 클래스**: 오픈소스 생태계 — Freqtrade, Backtrader, Jesse 등 모두 Python 클래스 기반

---

## 1. 기관 표준 (Institutional Standards)

### 1.1 FIXatdl (FIX Algorithmic Trading Definition Language)

| 항목 | 내용 |
|------|------|
| 관리 기관 | FIX Trading Community |
| 버전 | 1.1 (2010, 최신) |
| 포맷 | XML (XSD 스키마 제공) |
| 범위 | 알고 전략의 **매개변수 정의 + UI 렌더링**만 커버 |
| 전략 로직 | **미포함** — 매개변수만 정의, 실제 로직은 브로커 서버에 존재 |
| 목적 | 증권사(sell-side)가 알고 전략 파라미터를 EMS/OMS에 XML로 기술 → 클라이언트가 UI 자동 생성 |

**구조 (4개 XML 카테고리):**
- `Core`: 데이터 컨텐츠, 타입, 제약 (Data Contract)
- `Layout`: UI 컨트롤 정의 (14종 위젯, 수직/수평 패널)
- `Flow`: 컨트롤 간 동적 show/hide/enable 규칙
- `Validation`: 입력값 검증 규칙

**핵심 특성:**
- Bloomberg EMSX, FlexTrade 등 주요 EMS 지원
- Java (`atdl4j`), .NET (`Atdl4net`) 오픈소스 구현 존재
- FIX 태그 957-960 (`StrategyParametersGrp`)에 name-value pair 매핑

**한계:** 전략 `로직`이 아닌 `인터페이스` 정의 표준. 전략 로직은 표준화되지 않음.

---

### 1.2 FpML (Financial Products Markup Language)

| 항목 | 내용 |
|------|------|
| 관리 기관 | ISDA (국제스왑파생상품협회) |
| 포맷 | XML |
| 범위 | OTC 파생상품 전체 (FX, 금리스왑, CDS, 에쿼티 파생상품 등) |
| 전략 지원 | **복합 구조 전략** 지원 — 여러 상품을 조합한 strategy 컴포지션 |

**전략 관련:**
- FpML 2.0부터 `product strategy` 도입 — 하나의 trade에 복수 상품 포함 가능
- 전략이 또 다른 전략을 포함하는 **재귀적 컴포지션** 패턴 지원
- 대표 예: 스트래들, 스트랭글, 델타헤지(FX 옵션 + 현물), 이종자산 조합
- 사전/중간/사후 거래 전 과정(전자 체결 → 중앙청산 → 거래 보고) 커버

**한계:** OTC 파생상품 특화. 시스템 트레이딩 전략 로직과는 별개.

---

### 1.3 FIXML

| 항목 | 내용 |
|------|------|
| 관리 기관 | FIX Trading Community |
| 포맷 | XML (FIX 메시지의 XML 인코딩) |
| 범위 | FIX 애플리케이션 메시지 전체 (주문, 체결, 거래보고 등) |
| 전략 관련성 | 간접적 — 주문 메시지 안에 알고 전략 파라미터가 포함됨 |

**핵심:** FIXML은 거래 메시지의 XML 표현이며, 알고 전략 정의는 FIXatdl이 담당.
Orchestra(차세대)로 발전 중 — 기계가 읽을 수 있는 Rules of Engagement 표준.

---

## 2. 리테일 플랫폼 표준 (Retail Platform Standards)

### 2.1 Pine Script (TradingView)

| 항목 | 내용 |
|------|------|
| 포맷 | 독점 스크립팅 언어 (텍스트 소스코드) |
| 현재 버전 | v6 |
| 공유 방식 | TradingView 플랫폼 내 "Publish Script" |
| 가시성 | Public / Private / Protected / Invite-only |
| 라이브러리 | `library()` 선언 → `import <username>/<name>/<version>` 으로 임포트 |

**공유 메커니즘:**
- 플랫폼 내부 Community Scripts 피드로만 공유
- **외부 Export 없음** — 코드 복사/붙여넣기가 유일한 이식 방법
- 데이터 내보내기: Alert + Webhook (JSON), Strategy Tester CSV Export
- 라이브러리 코드는 항상 오픈소스 의무 (public domain)

**사실상 표준화 현황:**
- 전세계 최대 리테일 알고 트레이딩 커뮤니티 (TradingView ~60M 사용자)
- 전략 공유 커뮤니티의 사실상(de facto) 표준이나 플랫폼 종속
- **타 플랫폼으로 직접 이식 불가** — 기능 호환 불일치

---

### 2.2 MQL4/MQL5 (MetaTrader 4/5)

| 항목 | 내용 |
|------|------|
| 포맷 | C++ 유사 독점 언어 |
| 파일 확장자 | 소스: `.mq5` / 컴파일: `.ex5` |
| 에디터 | MetaEditor |
| 마켓플레이스 | MQL5 Market (세계 최대 트레이딩 로봇 스토어) |

**Expert Advisor (EA) 구조:**
- `OnInit()`: 초기화
- `OnTick()` / `OnBar()`: 틱/봉 이벤트
- `GetIndicatorsData()`: 지표 데이터 읽기
- `EvaluateEntry()`: 진입 신호 평가
- `FileWriteStruct()` / `FileReadStruct()`: 파라미터 영속성

**공유 방식:**
- **소스코드 공유**: `.mq5` 파일 직접 배포
- **컴파일 배포**: `.ex5` (바이너리, 소스코드 숨김)
- MQL5 Market: 유료/무료 판매, 코드 비공개 가능
- MQL5 Code Base: 무료 오픈소스 공유
- Freelance: 주문 개발

---

### 2.3 NinjaScript (NinjaTrader 8)

| 항목 | 내용 |
|------|------|
| 포맷 | C# 기반 독점 언어 |
| 파일 위치 | `Documents/NinjaTrader 8/bin/Custom/Strategies/*.cs` |
| 에디터 | NinjaScript Editor (F5 컴파일) |

**Export/Import 형식:**
- Export: `Tools → Export → NinjaScript Add-on` → `.zip` 아카이브
  - **소스 포함**: `.cs` 파일
  - **컴파일 전용**: DLL (소스코드 숨김)
- Import: `Tools → Import → NinjaScript Add-On` → `.zip` 임포트
- NinjaTrader Ecosystem 벤더: 시간 제한 코드 보호 공유 지원

---

### 2.4 EasyLanguage (TradeStation)

| 항목 | 내용 |
|------|------|
| 포맷 | 독점 스크립팅 언어 (PowerBasic 계열) |
| 파일 확장자 | `.eld` (EasyLanguage Document), `.els`, `.ela` |
| 호환 플랫폼 | TradeStation, MultiCharts, OEC |

**Export/Import:**
- `File → Import/Export EasyLanguage`
- ELD: TradeStation 6 이상 전용 바이너리
- 보호 ELD: 소스코드 숨김 배포 가능
- EasyLanguage Library Forum: 커뮤니티 공유 허브

---

## 3. 오픈소스 프레임워크 포맷

### 3.1 Freqtrade

| 항목 | 내용 |
|------|------|
| 전략 포맷 | **Python 클래스** (`user_data/strategies/*.py`) |
| 설정 포맷 | **JSON** (`config.json`) |
| 실행 방법 | `--strategy ClassName` (클래스명 지정) |

**전략 구조 (Python):**
```python
class MyStrategy(IStrategy):
    # 파라미터
    minimal_roi = {"0": 0.1}
    stoploss = -0.05

    def populate_indicators(self, dataframe, metadata):
        # 지표 계산

    def populate_entry_trend(self, dataframe, metadata):
        # 진입 신호

    def populate_exit_trend(self, dataframe, metadata):
        # 청산 신호
```

**특징:**
- `strategy-updater` 도구: v3 호환성 자동 업데이트
- FreqAI: 머신러닝 기반 전략 확장 (`config_freqai.example.json`)
- 설정에 JSON 스키마 제공 → 에디터 자동완성/검증 가능

---

### 3.2 QuantConnect LEAN

| 항목 | 내용 |
|------|------|
| 전략 포맷 | **Python** 또는 **C#** 클래스 (`QCAlgorithm` 상속) |
| 설정 포맷 | JSON (`config.json` — 환경 모드 설정) |
| 엔진 | C# (Python.NET 브릿지) |

**Algorithm 구조:**
```python
class MyAlgorithm(QCAlgorithm):
    def Initialize(self):
        # 데이터 구독, 파라미터 설정

    def OnData(self, data):
        # 틱/바 처리, 주문 실행

    def OnOrderEvent(self, orderEvent):
        # 주문 이벤트 처리
```

**Alpha Marketplace (전략 공유):**
- Alpha = Insight 생성기 (방향, 크기, 기간 예측만)
- 포지션 사이징/리스크 관리는 Alpha 범위 외
- 소스코드 비공개 배포 지원
- Collective2 통합: `Collective2SignalExport(apiKey, systemId)` — 신호 자동 전송

---

### 3.3 Backtrader / Zipline / Jesse

모두 **Python 클래스 기반** 전략 정의. JSON/YAML 포맷 없음.

| 프레임워크 | 전략 포맷 | 특징 |
|-----------|----------|------|
| **Backtrader** | `Strategy` 서브클래스 | `next()`, `notify_order()`, `notify_trade()` |
| **Zipline** | Python 함수 (`initialize`, `handle_data`) | Pandas DataFrame 기반, bcolz 번들 |
| **Jesse** | Python 클래스 | 암호화폐 특화, 멀티타임프레임 |

---

## 4. 브로커 플랫폼

### 4.1 Interactive Brokers (IBKR)

**전략 Export 없음** — API 기반 프로그래밍 모델:
- `IBApi.Order.AlgoStrategy` + `IBApi.Order.AlgoParams`: 내장 알고 선택
- 내장 알고: TWAP, VWAP, Accumulate/Distribute, Percent of Volume, ScaleTrader, Dark Ice
- Python TWS API로 커스텀 전략 구현 (전략 정의 표준 없음)
- 전략 정의는 사용자 코드(Python/Java/C++) 안에 존재

---

## 5. 전략 마켓플레이스

| 플랫폼 | 공유 포맷 | 수익화 | 코드 공개 여부 |
|--------|----------|-------|--------------|
| **TradingView Community Scripts** | Pine Script 소스코드 | 없음 (무료 공유) | Public: 공개, Protected: 비공개 |
| **MQL5 Market** | `.ex5` 컴파일 바이너리 | 유료 판매 | 선택적 |
| **QuantConnect Alpha** | Python/C# (소스 비공개) | 리스 계약 | 비공개 |
| **Collective2** | 신호/거래 (소스 미공개) | 구독료/성과 배분 | 비공개 |
| **Darwinex** | 카피트레이딩 (실행 미러링) | 성과 기반 | 비공개 |

---

## 6. 한국 플랫폼

### 6.1 키움증권 영웅문4 조건검색

| 항목 | 내용 |
|------|------|
| 저장 위치 | 키움증권 **서버** (로컬 PC 아님) |
| PC 이전 방법 | `메뉴 → 기능 → 설정저장/불러오기` → 서버 업로드/다운로드 |
| Open API 연동 | HTS에서 작성한 조건식을 API로 불러와 실행 (API에서 직접 작성 불가) |
| 결과 데이터 형식 | `종목코드1^종목코드2...` 또는 `종목코드^현재가` (세미콜론 구분) |
| 실시간 제한 | 최대 10개 조건식, 100종목 이하, 1분에 1회 |
| 관심종목 Export | Excel 파일 |

**공유 특성:** 조건검색식은 플랫폼 내부 형식으로 외부 공유 표준 없음. 조건식 내용은 서버에 종속.

### 6.2 대신증권 CYBOS Plus

| 항목 | 내용 |
|------|------|
| API 방식 | COM Object (VB, C#, Excel, Python 지원) |
| 조건검색 | `#8537` 화면 기반 + 전략감시 실시간 처리 |
| 공유 방법 | 특허 기반 — 조건식 매도자/매수자 거래 시스템 (로직 비공개, 신호만 전달) |

**특이사항:** KR101789659B1 특허에서 조건검색식을 상품으로 거래하는 시스템을 확인. 구매자는 로직 없이 신호만 수신.

---

## 7. 종합 비교

### 7.1 전략 표현 방식별 분류

```
기관 표준         [전략 파라미터 정의]  FIXatdl (XML)
파생상품          [복합 상품 구조]      FpML (XML)
리테일 스크립트   [소스코드 공유]       Pine Script, MQL5, EasyLanguage, NinjaScript
오픈소스          [Python 클래스]       Freqtrade, Backtrader, Jesse, Zipline
퀀트 플랫폼       [Python/C# 클래스]    QuantConnect LEAN
브로커 API        [주문 파라미터]       IBKR AlgoStrategy
한국              [플랫폼 종속 형식]    키움 조건검색, CYBOS
```

### 7.2 "표준 교환 포맷"에 가장 가까운 것은?

1. **FIXatdl** — 기관 B2B 영역에서 유일한 실질적 표준이지만, 전략 로직은 정의하지 않음
2. **Python 클래스** — 오픈소스 생태계의 사실상 표준 (프레임워크별 인터페이스 상이)
3. **Pine Script** — 리테일 알고 커뮤니티의 사실상 표준이지만 플랫폼 종속

### 7.3 공통 패턴 (모든 플랫폼 공통)

전략이 공유될 때 공통적으로 포함되는 정보:
```
진입 조건   (Entry Conditions)
청산 조건   (Exit Conditions)
손절 규칙   (Stop Loss Rules)
익절 규칙   (Take Profit Rules)
포지션 크기 (Position Sizing)
대상 자산   (Target Instruments)
타임프레임  (Timeframe)
리스크 파라미터 (Risk Parameters)
```

---

## 8. StockVision 설계 시사점

### 전략 공유 포맷 설계 방향

1. **단순 JSON 스키마** 채택 권장 — FIXatdl의 복잡성 불필요
2. 전략 로직은 **DSL 또는 Python 클래스** 형태로 표현
3. 마켓플레이스에서 **로직 비공개 + 신호 공개** 모델(키움 특허 방식)이 한국 시장 현실적

### 참고할 만한 오픈소스 JSON 패턴

```json
{
  "strategy_id": "uuid",
  "name": "전략명",
  "version": "1.0.0",
  "author": "user_id",
  "target": {
    "market": "KRX",
    "instruments": ["005930", "000660"],
    "timeframe": "1d"
  },
  "parameters": {
    "fast_period": {"type": "int", "default": 5, "min": 1, "max": 50},
    "slow_period": {"type": "int", "default": 20, "min": 5, "max": 200}
  },
  "risk": {
    "stop_loss": 0.05,
    "take_profit": 0.10,
    "max_position_size": 0.1
  },
  "logic": "python_class_reference | dsl_expression | opaque_signal"
}
```

### 기존 spec 연계

- `/docs/research/rule-dsl-design.md` — 기존 DSL 설계 연구 참고
- `/spec/` — 전략 마켓플레이스 feature spec 작성 시 이 문서 참조

---

## 참고 자료

- [FIXatdl Wikipedia](https://en.wikipedia.org/wiki/FIXatdl)
- [FIX Trading Community - FIXatdl](https://www.fixtrading.org/online-specification/introduction/)
- [FpML Official](https://www.fpml.org/)
- [FpML Wikipedia](https://en.wikipedia.org/wiki/FpML)
- [FIXML Online - FIX Trading Community](https://www.fixtrading.org/standards/fixml-online/)
- [TradingView Pine Script Docs](https://www.tradingview.com/pine-script-docs/)
- [Pine Script Share/Import Guide](https://thefinanceshow.com/share-and-import-pine-script-strategies-with-other-traders/)
- [MQL5 Market](https://www.mql5.com/en/market)
- [MQL5 Expert Advisor Step-by-Step](https://www.mql5.com/en/articles/100)
- [Freqtrade Configuration](https://www.freqtrade.io/en/stable/configuration/)
- [Freqtrade Advanced Strategy](https://www.freqtrade.io/en/stable/strategy-advanced/)
- [QuantConnect Lean GitHub](https://github.com/QuantConnect/Lean)
- [QuantConnect Collective2 Integration](https://www.quantconnect.com/docs/v2/writing-algorithms/live-trading/signal-exports/collective2)
- [NinjaTrader Export Guide](https://ninjatrader.com/support/helpguides/nt8/export.htm)
- [TradeStation EasyLanguage Import/Export](https://help.tradestation.com/09_05/eng/tsdevhelp/el_editor/using_the_import_export_wizard.htm)
- [EasyLanguage ELD Format](https://help.tradestation.com/10_00/eng/tradestationhelp/el_procedures/el_documents_file_eld_.htm)
- [IBKR TWS API Algorithms](https://interactivebrokers.github.io/tws-api/ibalgos.html)
- [키움증권 조건검색 도움말](https://download.kiwoom.com/hero4_help_new/0150.htm)
- [키움증권 설정저장/불러오기](https://download.kiwoom.com/hero4_help_new/p021.htm)
- [대신증권 CYBOS Plus API](https://money2.daishin.com/E5/WTS/Customer/GuideTrading/DW_CybosPlus_Page.aspx?p=8812&v=8632&m=9508)
- [한국 조건검색식 거래 특허 KR101789659B1](https://patents.google.com/patent/KR101789659B1/ko)
- [Backtrader Strategy Docs](https://www.backtrader.com/docu/strategy/)
- [QuantConnect Alpha Marketplace](https://www.quantconnect.com/market/)
