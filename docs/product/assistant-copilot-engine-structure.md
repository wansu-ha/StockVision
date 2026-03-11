# Assistant / Strategy Copilot / System Trader / Execution Layer 구조
작성일: 2026-03-10
상태: 초안 v2
관련 문서:
- `docs/product/product-direction-log.md`
- `docs/product/assistant-system-prompt-draft.md`
- `docs/product/llm-permission-policy.md`
- `docs/product/remote-permission-model.md`
- `docs/product/system-trader-definition.md`
- `docs/product/system-trader-benchmark.md`
- `docs/product/system-trader-state-model.md`

## 1. 목적

이 문서는 StockVision 안에서 서로 다른 네 가지 주체의 책임과 경계를 정리한다.

- `Assistant`: 사용자와 대화하는 운영 비서
- `Strategy Copilot`: 전략 DSL을 만들어주는 코딩 보조
- `System Trader`: 여러 전략 신호를 모아 포트폴리오 차원에서 최종 매매 의도를 정리하는 결정 모듈
- `Execution Layer`: 주문 실행, 리스크 차단, 브로커 상태 동기화를 담당하는 실행 계층

핵심 목표는 두 가지다.

- 말하는 LLM과 실제 거래 결정을 명확히 분리한다.
- 전략 평가와 주문 실행 사이에 `System Trader`라는 포트폴리오 판단 계층을 둔다.

## 2. 왜 4단 구조인가

`Assistant`, `Strategy Copilot`, `Execution Engine`만 두면 중간이 비게 된다.

- Assistant는 사용자 의도를 이해하지만 포트폴리오 결정을 하면 안 된다.
- Strategy Copilot은 DSL을 잘 만들어도 실시간 자금 배분을 하면 안 된다.
- Execution Layer는 이미 정해진 주문을 정확히 실행하는 쪽이어야지, 어떤 주문을 우선할지 결정하면 안 된다.

그 사이에서 아래 일을 맡는 별도 계층이 필요하다.

- 여러 전략이 동시에 낸 신호를 모으기
- 종목 중복과 전략 충돌을 정리하기
- 포지션 수, 자금, 우선순위, 분할 규칙을 적용하기
- 실제 주문으로 보내기 전 `order intent`를 만들기

이 계층이 바로 `System Trader`다.

## 3. 각 주체의 정의

### 3.1 Assistant

Assistant는 사용자의 계좌 상태, 관심 종목, 경고, 브리핑, 복기를 다루는 운영 비서다.

주요 역할:

- 계좌/전략 상태 요약
- 아침 브리핑, 장중 경고, 장마감 복기
- 주문 초안 설명
- 위험 요청을 안전한 초안으로 변환

하지 않는 일:

- 직접 주문 실행
- 개인별 종목 추천
- 전략 자동 활성화

### 3.2 Strategy Copilot

Strategy Copilot은 자연어를 전략 DSL 초안으로 바꾸고, 기존 전략을 수정하는 코딩 보조다.

주요 역할:

- 자연어 -> DSL 초안 생성
- DSL 수정과 문법 보정
- 백테스트용 템플릿 생성
- 전략 설명과 리팩터링

하지 않는 일:

- 계좌를 보고 무엇을 사야 할지 판단
- 주문 초안 없이 실주문으로 연결
- 장기 메모리 기반 사용자 대리 판단

### 3.3 System Trader

System Trader는 활성 전략들이 만든 신호를 입력으로 받아, 포트폴리오 수준에서 최종 매매 의도를 결정하는 규칙형 모듈이다.

주요 역할:

- 신호 수집과 정규화
- 전략 우선순위 적용
- 종목 중복/충돌 해소
- 포지션 크기와 자금 배분
- 진입/청산 의도 생성
- 주문 의도의 상태 관리

하지 않는 일:

- 사용자와 대화
- 자연어 해석
- 브로커 API 직접 호출

### 3.4 Execution Layer

Execution Layer는 이미 생성된 주문 의도를 안전하게 시장 주문으로 옮기는 실행 계층이다.

구성 예시:

- `Execution Engine`: 주문 제출, 취소, 재시도, 체결 추적
- `Risk Guard`: 킬스위치, 주문 속도 제한, 손실 한도, 원격 권한 제한
- `Broker Adapter`: 키움/KIS/모의 브로커와의 실제 통신
- `Reconciler`: 미체결/체결/외부 주문 감지와 상태 정합

## 4. 책임 비교표

| 구분 | Assistant | Strategy Copilot | System Trader | Execution Layer |
|---|---|---|---|---|
| 정체성 | 운영 비서 | 전략 코딩 보조 | 포트폴리오 판단 모듈 | 실행 계층 |
| 입력 | 계좌 상태, 알림, 메모리, 로그 | 전략 파일, DSL 스키마, 에러 | 전략 신호, 계좌, 포지션, 규칙 | 주문 의도, 리스크 상태, 브로커 응답 |
| 출력 | 브리핑, 경고, 주문 초안 설명 | DSL 초안, 수정안, 테스트 준비 | order intent, skip 이유, 우선순위 결과 | 주문 접수, 취소, 체결, 차단, 로그 |
| 장기 메모리 | 중요 | 거의 불필요 | 불필요 | 불필요 |
| 작업 컨텍스트 | 중요 | 매우 중요 | 중요 | 중요 |
| 직접 주문 | 금지 | 금지 | 금지 | 허용 |
| 사용자 대화 | 직접 담당 | 간접 담당 | 담당 안 함 | 담당 안 함 |
| 설명 가능성 | 사용자 설명 | 코드 설명 | 결정 이유 기록 | 실행/차단 이유 기록 |

## 5. 메모리 모델

### 5.1 Assistant

Assistant는 `메모리 중심`이다.

기억해야 하는 예:

- 사용자 투자 성향
- 관심 종목
- 금지 규칙
- 최근 경고와 복기
- 비서 톤과 브리핑 방식

### 5.2 Strategy Copilot

Strategy Copilot은 `작업 컨텍스트 중심`이다.

필요한 정보:

- 현재 전략 DSL
- DSL 문법과 스키마
- 최근 오류
- 현재 백테스트 설정

장기적으로 기억할 필요는 거의 없다.

### 5.3 System Trader

System Trader는 `실시간 상태 중심`이다.

필요한 상태:

- 활성 전략 목록
- 전략별 후보 신호
- 현재 포지션과 현금
- 미체결 주문
- 일일 예산 사용량
- 종목별, 전략별, 포트폴리오별 한도
- 외부 주문/체결 감지 결과

중요한 점은, System Trader는 사람의 취향을 기억하는 메모리 모듈이 아니라 `현재 포트폴리오의 상태 기계`라는 점이다.

### 5.4 Execution Layer

Execution Layer는 `브로커와의 정합 상태`를 가진다.

필요한 상태:

- 주문 접수 상태
- 부분 체결/완전 체결 상태
- 취소 가능 여부
- 브로커 연결 상태
- 재시도/실패 이력

## 6. System Trader가 있어야만 가능한 것

아래가 가능해야 `System Trader`라고 부를 수 있다.

1. 전략 평가 결과를 바로 주문하지 않고 먼저 `후보 의도`로 모은다.
2. 한 평가 주기 안에서 포트폴리오 상태를 반영해 우선순위를 정한다.
3. 동일 종목에 여러 전략이 진입하려 할 때 충돌 규칙을 적용한다.
4. 포지션 수, 종목별 한도, 예산, 분할 규칙을 함께 본다.
5. `주문 접수`, `부분 체결`, `완전 체결`, `취소`, `실패`를 구분한다.
6. 외부 주문이나 수동 체결을 감지하면 상태를 다시 맞춘다.
7. 왜 특정 신호를 채택했고 왜 버렸는지 로그로 남긴다.

위 기능이 없으면, 더 정확한 이름은 `Strategy Engine` 또는 `Execution Engine`에 가깝다.

## 7. 추천 흐름

### 7.1 운영 질문

사용자: `오늘 내 계좌 상태 어때?`

흐름:

1. Assistant가 계좌 상태와 최근 경고를 읽는다.
2. 필요하면 System Trader의 결정 로그를 참고한다.
3. Assistant가 사용자 친화적인 문장으로 답한다.

### 7.2 전략 생성 요청

사용자: `반도체 눌림목 전략 짜줘`

흐름:

1. Assistant가 요청을 전략 작업으로 해석한다.
2. Strategy Copilot이 DSL 초안을 생성한다.
3. Assistant가 초안을 요약하고 저장/백테스트 옵션을 제안한다.

### 7.3 자동매매 실행

흐름:

1. Rule Evaluator가 각 전략의 BUY/SELL 후보 신호를 만든다.
2. System Trader가 후보 신호를 한 곳에 모은다.
3. System Trader가 충돌 해소, 포지션 관리, 자금 배분을 적용해 `order intent`를 만든다.
4. Execution Layer가 intent를 실제 주문으로 제출한다.
5. 체결/미체결/취소 결과가 다시 System Trader와 Assistant에 전달된다.

## 8. 권장 구현 순서

현재 MVP 기준으로는 아래 순서가 현실적이다.

1. `Execution Layer`를 안정화한다.
2. `System Trader`를 Engine 내부 모듈로 먼저 만든다.
3. 포트폴리오 우선순위와 order intent 모델을 도입한다.
4. 그 다음에 Assistant와 Strategy Copilot을 얹는다.

즉 초기에는 폴더가 분리되지 않아도 되지만, 개념적으로는 지금부터 분리해 두는 것이 맞다.

## 9. 한 줄 정리

StockVision은 `말하는 비서`, `전략을 써주는 코파일럿`, `포트폴리오를 판단하는 System Trader`, `실제 주문을 수행하는 Execution Layer`를 분리할수록 제품과 구현이 모두 더 단단해진다.