# System Trader 벤치마크 조사
작성일: 2026-03-10
상태: 초안
관련 문서:
- `docs/product/system-trader-definition.md`
- `docs/product/system-trader-state-model.md`
- `docs/product/assistant-copilot-engine-structure.md`

## 1. 조사 목적

이 문서는 StockVision에서 말하는 `System Trader`가 업계의 어떤 개념들과 닮아 있는지 확인하고, 어떤 책임을 가져야 하는지 벤치마킹하기 위해 작성했다.

핵심 질문은 세 가지다.

1. 업계에서 `System Trader`와 비슷한 역할은 보통 어떤 이름으로 불리는가
2. 전략 평가와 주문 실행 사이에는 어떤 중간 계층이 존재하는가
3. StockVision은 어디까지를 `System Trader`로 보고 어디부터를 `Execution Layer`로 분리해야 하는가

## 2. 조사 결론 요약

결론부터 말하면, 업계에서 정확히 `System Trader`라는 이름이 표준처럼 쓰이진 않는다.
대신 비슷한 책임은 아래 조합으로 분리되어 있다.

- `Portfolio Construction`
- `Risk Management`
- `OMS / EMS`
- `Execution Engine`
- `Portfolio / Trader`

즉 StockVision의 `System Trader`는 기존 업계 용어로 보면 아래를 섞은 내부 개념에 가깝다.

- 전략 신호를 포트폴리오 목표로 바꾸는 `Portfolio Construction`
- 주문 전 차단과 축소를 수행하는 `Risk / Trader`
- 실제 주문으로 보내기 전 의도를 관리하는 `OMS 전단`

그래서 `System Trader`는 다음처럼 정의하는 것이 가장 자연스럽다.

`여러 전략이 만든 신호를 모아, 포트폴리오 상태와 리스크 규칙을 반영해 실제 주문 의도(order intent)로 정리하는 결정 모듈`

## 3. 벤치마크 사례

### 3.1 QuantConnect

관찰 포인트:

- QuantConnect는 `Alpha -> Portfolio Construction -> Risk Management -> Execution` 흐름을 명확히 분리한다.
- 공식 문서는 Alpha가 만든 `Insights`를 Portfolio Construction이 `PortfolioTarget`으로 바꾸고, Risk가 이를 조정한 뒤, Execution이 목표 포지션을 채운다고 설명한다.
- 또 `PortfolioTarget`은 곧바로 체결된 주문이 아니며, Execution은 목표 수량을 향해 나아가는 단계라고 본다.

StockVision에 주는 시사점:

- 전략의 BUY/SELL 신호와 실제 주문은 같은 것이 아니다.
- `System Trader`는 각 전략 신호를 바로 주문으로 바꾸지 말고 먼저 `portfolio target` 또는 `order intent`로 바꿔야 한다.
- Risk는 주문 후가 아니라 주문 전에도 개입할 수 있어야 한다.

벤치마킹 포인트:

- `signal -> target -> execution` 분리
- 포트폴리오 차원의 목표 수량 개념
- `submitted != filled` 전제

### 3.2 NautilusTrader

관찰 포인트:

- NautilusTrader는 `Strategy -> OrderEmulator -> ExecAlgorithm -> RiskEngine -> ExecutionEngine -> ExecutionClient` 흐름을 둔다.
- 모든 주문 명령과 이벤트가 `RiskEngine`을 통과할 수 있게 설계되어 있다.
- `TradingState`를 `ACTIVE`, `HALTED`, `REDUCING`으로 나누고, 실시간 이벤트와 정기 reconciliation을 함께 사용한다.
- 자체 주문 장부(own order books)를 유지하며, 주문이 `submitted/accepted/modified/filled/canceled/rejected/expired`를 거치며 관리된다고 설명한다.

StockVision에 주는 시사점:

- `System Trader`와 `Execution Layer` 사이에 강한 상태 기계가 필요하다.
- 실시간 체결 이벤트만 믿지 말고, polling 기반 재조정이 같이 있어야 한다.
- `HALTED`, `REDUCING` 같은 글로벌 거래 상태는 실전에서 매우 유용하다.

벤치마킹 포인트:

- 리스크 엔진을 모든 주문 흐름 앞에 배치
- 거래 상태 모드 분리
- 실시간 이벤트 + reconciliation 이중 경로
- inflight order와 closed order를 분리 관리

### 3.3 Hummingbot Strategy V2

관찰 포인트:

- Hummingbot은 `Controller`가 전략 논리를 만들고, `Executor`가 실제 주문과 포지션 관리를 담당한다.
- `ExecutorOrchestrator`가 여러 executor를 생성하고 중지하고 관리하는 유틸리티 역할을 맡는다.
- 공식 문서는 Executors가 스스로 주문 상태를 관리하며, 생성/갱신/취소/종료를 수행한다고 설명한다.

StockVision에 주는 시사점:

- 전략 단위 실행기라는 개념은 유용하지만, StockVision은 그 위에 포트폴리오 통합 계층이 하나 더 필요하다.
- 즉 Hummingbot의 Controller/Executor 구조는 참고할 만하지만, StockVision의 `System Trader`는 단일 executor보다 상위의 `executor orchestrator + portfolio selector`에 더 가깝다.

벤치마킹 포인트:

- 전략 논리와 주문 관리 분리
- self-managing execution unit 개념
- 다중 실행 유닛 오케스트레이션

### 3.4 Backtrader + IBKR 주문 상태

관찰 포인트:

- Backtrader 문서는 주문 상태를 `Submitted`, `Accepted`, `Partial`, `Complete`, `Rejected`, `Cancelled`, `Expired` 등으로 구분한다.
- IBKR 문서도 `PendingSubmit`, `PreSubmitted`, `Submitted`, `Cancelled`, `Filled`, `Inactive` 등 더 세밀한 상태를 둔다.
- 두 문서 모두 `주문이 제출되었다`와 `완전히 체결되었다`를 명확히 구분한다.

StockVision에 주는 시사점:

- 현재 구현의 가장 큰 약점 중 하나인 `place_order -> 곧바로 filled 취급`은 고쳐야 한다.
- `System Trader`와 `Execution Layer`는 최소한 `submitted / partial_filled / filled / cancelled / rejected`를 분리해야 한다.

벤치마킹 포인트:

- 실브로커 기준 주문 수명주기
- partial fill 기본 전제
- cancel 요청과 cancel 확정의 분리

### 3.5 TT OMS / EMS

관찰 포인트:

- TT OMS는 `Accept, manage and execute orders`와 post-trade allocation을 한 플랫폼에서 다루고, `Separate the trading decision from the mechanics of execution`을 강조한다.
- 주문을 staging하고 ownership을 넘기고 execution tools로 채우는 구조를 보여준다.

StockVision에 주는 시사점:

- `무엇을 할지 정하는 것`과 `어떻게 집행할지`는 분리해야 한다.
- StockVision에서 `System Trader`는 의사결정과 의도 생성 쪽, `Execution Layer`는 실행 기계 쪽으로 두는 게 자연스럽다.

벤치마킹 포인트:

- decision / execution 분리
- staged order / care order 개념
- execution mechanics를 별도 계층으로 두기

## 4. 비교 정리

| 시스템 | 신호 계층 | 포트폴리오 판단 | 리스크 계층 | 실행 계층 | 상태/정합성 |
|---|---|---|---|---|---|
| QuantConnect | Alpha | Portfolio Construction | Risk Model | Execution Model | 목표 수량 중심 |
| NautilusTrader | Strategy / ExecAlgorithm | Portfolio / Strategy 조합 | RiskEngine | ExecutionEngine / Client | 강함 |
| Hummingbot | Controller | 약함 또는 전략 내부 | 제한적 | Executors | 실행 유닛 중심 |
| Backtrader | Strategy | 약함 | 브로커/사용자 로직 | Broker | 주문 상태 모델 참고용 |
| TT OMS/EMS | Order staging | Desk/OMS | 운영 규칙 | EMS / algos | 기관형 워크플로 강함 |

## 5. StockVision에 맞는 해석

StockVision의 `System Trader`는 아래 셋을 합친 내부 개념으로 보는 게 좋다.

1. `Portfolio Construction`
전략 신호를 목표 보유/주문 의도로 변환

2. `Pre-trade Risk Selection`
종목 중복, 자금 부족, 포지션 수 초과, 전략 충돌 등을 반영해 무엇을 버릴지 결정

3. `Intent Manager`
실제 브로커 주문 전에 `order intent`를 만들고 추적

반대로 아래는 `System Trader`가 아니다.

- 자연어 비서
- 전략 DSL 생성기
- 브로커 어댑터 자체
- 단순 주문 전송기

## 6. StockVision용 벤치마크 결론

### 6.1 System Trader란 무엇인가

StockVision에서 `System Trader`는 다음처럼 정의하는 것이 적절하다.

`전략 평가 결과를 바로 주문하지 않고, 포트폴리오 상태와 리스크 제약을 반영해 order intent로 바꾸는 포트폴리오 결정 계층`

### 6.2 반드시 가져야 할 기능

- 후보 신호 수집
- 포트폴리오 스냅샷 기반 선택
- 종목 중복/전략 충돌 해소
- 포지션 수, 예산, 분할 규칙 적용
- order intent 상태 기계
- 체결/미체결/외부 주문 정합성 재조정
- 차단 이유와 선택 이유 로그

### 6.3 MVP에서 최소한 해야 할 것

- `signal -> order` 직결 제거
- `candidate signal -> order intent -> broker order` 3단계 도입
- `submitted != filled` 분리
- 같은 주기 내 포트폴리오 상태 갱신
- 외부 주문/체결 반영용 reconciliation 훅 준비

## 7. 명명 권고

현재 수준의 구현이라면 이름은 아래처럼 보수적으로 가는 편이 맞다.

- 현재 구현: `Strategy Engine` 또는 `Execution Engine`
- 다음 단계 구현: `System Trader`
- 최종 구조: `System Trader + Execution Layer`

즉 `System Trader`는 지금 붙이는 마케팅 이름이라기보다, 다음 리팩터링 목표 이름으로 쓰는 것이 가장 정확하다.

## 8. 참고 자료

- [QuantConnect Algorithm Framework Overview](https://www.quantconnect.com/docs/v1/algorithm-framework/overview)
- [QuantConnect Portfolio Construction](https://www.quantconnect.com/docs/v1/algorithm-framework/portfolio-construction)
- [QuantConnect Execution](https://www.quantconnect.com/docs/v1/algorithm-framework/execution)
- [QuantConnect Risk Management](https://www.quantconnect.com/docs/v1/algorithm-framework/risk-management)
- [NautilusTrader Execution Concepts](https://nautilustrader.io/docs/nightly/concepts/execution/)
- [Hummingbot Strategy V2 Architecture](https://hummingbot.org/strategies/v2-strategies/)
- [Hummingbot Executors](https://hummingbot.org/strategies/v2-strategies/executors/)
- [Backtrader Order Documentation](https://www.backtrader.com/docu/order/)
- [Interactive Brokers Order Submission](https://interactivebrokers.github.io/tws-api/order_submission.html)
- [TT OMS](https://tradingtechnologies.com/trading/oms/)