# StockVision UX/UI 벤치마크 매핑

작성일: 2026-03-10

## 1. 범위

이 문서는 현재 실제로 연결된 StockVision 프론트만 기준으로 UX/UI를 벤치마킹한다.

분석 대상:
- 메인 대시보드: [`MainDashboard.tsx`](../../frontend/src/pages/MainDashboard.tsx)
- 헤더: [`Header.tsx`](../../frontend/src/components/main/Header.tsx)
- 리스트 뷰: [`ListView.tsx`](../../frontend/src/components/main/ListView.tsx)
- 상세 뷰: [`DetailView.tsx`](../../frontend/src/components/main/DetailView.tsx)
- 온보딩: [`Onboarding.tsx`](../../frontend/src/pages/Onboarding.tsx)
- 설정: [`Settings.tsx`](../../frontend/src/pages/Settings.tsx)

제외:
- 아직 연결되지 않은 레거시/구현 전 화면

핵심 관점:
- 차트 UX
- 전략 생성/수정 UX
- 자동매매 상태 가시성
- 신뢰와 안전장치 표현
- 온보딩과 설정 흐름

## 2. 현재 StockVision 해석

현재 연결된 UI의 성격은 다음에 가깝다.

- 종목 중심 싱글뷰
- 로컬 실행 기반의 신뢰형 자동매매 도구
- 목록 -> 확장 -> 상세로 이어지는 점진적 공개
- 차트와 규칙을 한 종목 컨텍스트 안에서 다루는 구조

즉 비교 축은 다음처럼 잡는 것이 가장 정확하다.

- 전략 편집: Composer, 3Commas
- 차트/분석: TradingView
- 쉬운 자동화/신뢰형 온보딩: Stoic
- 고급 확장성/전문가용 워크벤치: QuantConnect

## 3. 공식 공개 스크린샷 레퍼런스

주의:
- 아래 이미지는 모두 공식 공개 이미지 기준이다.
- 일부 서비스는 hotlink 제한 때문에 문서 렌더러에 따라 미리보기가 보이지 않을 수 있다.
- 그 경우 바로 아래 Source 링크에서 원본을 확인하면 된다.

### 3.1 Composer

왜 참고하는가:
- 전략 작성, 조건 수정, 백테스트, 포트폴리오 구성 흐름이 가장 직접적으로 유사하다.

#### 1. AI 생성
![Composer AI 생성](https://www.composer.trade/_next/image?q=75&url=%2F_next%2Fstatic%2Fmedia%2Faicreation.092ef698.png&w=3840)

Source:
- [Composer](https://www.composer.trade/)

#### 2. 전략 에디터
![Composer 전략 에디터](https://www.composer.trade/_next/image?q=75&url=%2F_next%2Fstatic%2Fmedia%2Feditor-preview.bb246a80.png&w=3840)

Source:
- [Composer](https://www.composer.trade/)

#### 3. 조건문 편집
![Composer 조건문 편집](https://www.composer.trade/_next/image?q=75&url=%2F_next%2Fstatic%2Fmedia%2Feditor-if.a501bdee.png&w=1920)

Source:
- [Composer](https://www.composer.trade/)

#### 4. 백테스트
![Composer 백테스트](https://www.composer.trade/_next/image?q=75&url=%2F_next%2Fstatic%2Fmedia%2Feditor-backtest-mock.8c7aea1b.png&w=3840)

Source:
- [Composer](https://www.composer.trade/)

#### 5. 포트폴리오 비중 그래프
![Composer 보유 비중 그래프](https://www.composer.trade/_next/image?q=75&url=%2F_next%2Fstatic%2Fmedia%2Feditor-allocationsgraph.4a4edbcc.png&w=2048)

Source:
- [Composer](https://www.composer.trade/)

### 3.2 QuantConnect

왜 참고하는가:
- 고급 사용자용 전략 연구, 데이터셋 탐색, 코드 워크벤치 구조를 참고하기 좋다.

#### 1. 알고리즘 랩
![QuantConnect 알고리즘 랩](https://cdn.quantconnect.com/i/tu/welcome-slide-1-img.png)

Source:
- [QuantConnect Strategies](https://www.quantconnect.com/strategies/)

#### 2. 데이터셋 탐색
![QuantConnect 데이터셋](https://cdn.quantconnect.com/i/tu/ds-welcome-img.webp)

Source:
- [QuantConnect Strategies](https://www.quantconnect.com/strategies/)

#### 3. 전략 탐색
![QuantConnect 전략 탐색](https://cdn.quantconnect.com/i/tu/ds-welcome-img-3.webp)

Source:
- [QuantConnect Strategies](https://www.quantconnect.com/strategies/)

#### 4. 코드 에디터
![QuantConnect 코드 에디터](https://cdn.quantconnect.com/i/tu/slider-code.webp)

Source:
- [QuantConnect Strategies](https://www.quantconnect.com/strategies/)

#### 5. 협업/조직 워크플로
![QuantConnect 조직 협업](https://cdn.quantconnect.com/i/tu/org-welcome-img.webp)

Source:
- [QuantConnect Strategies](https://www.quantconnect.com/strategies/)

### 3.3 TradingView

왜 참고하는가:
- 차트, Pine 편집기, 전략 테스터, 차트 위 액션 흐름의 기준점이다.

#### 1. 차트 워크스페이스
![TradingView 차트](https://static.tradingview.com/static/bundles/make-it-easy.a3c0a08eca5b128ecaca.svg)

Source:
- [TradingView Features](https://www.tradingview.com/features/)

#### 2. 기술분석 패널
![TradingView 기술분석 화면](https://static.tradingview.com/static/bundles/technical-analysis.7e4537cb42fc7e9d030f.svg)

Source:
- [TradingView Features](https://www.tradingview.com/features/)

#### 3. Pine Editor
![TradingView Pine Editor](https://static.tradingview.com/static/bundles/pine-editor.532d7ed6a278f3712091.svg)

Source:
- [TradingView Features](https://www.tradingview.com/features/)

#### 4. 전략 테스터
![TradingView 전략 테스터](https://static.tradingview.com/static/bundles/pine-strategy.e24f9c159563fb91df20.svg)

Source:
- [TradingView Features](https://www.tradingview.com/features/)

#### 5. 차트 트레이딩
![TradingView 차트 트레이딩](https://static.tradingview.com/static/bundles/chart-trading.9b9cdee934f097e3577d.svg)

Source:
- [TradingView Features](https://www.tradingview.com/features/)

### 3.4 3Commas

왜 참고하는가:
- 웹훅 기반 자동화, 보트 관리, 백테스트, 템플릿 운영 UX가 강하다.

#### 1. TradingView 자동화 연결
![3Commas TradingView 자동화](https://images.prismic.io/3commas/aQD2_7pReVYa3w4s_Frame2085663149.png?auto=format%2Ccompress&fit=max&w=3000)

Source:
- [3Commas TradingView](https://3commas.io/trading-view)

#### 2. 백테스트
![3Commas 백테스트](https://images.prismic.io/3commas/aQC6ZbpReVYa3vxQ_Frame1312318674.png?auto=format%2Ccompress&fit=max&w=2560)

Source:
- [3Commas TradingView](https://3commas.io/trading-view)

#### 3. 거래소 연결
![3Commas 거래소 연결](https://images.prismic.io/3commas/aQC8DLpReVYa3vx2_Group7.png?auto=format%2Ccompress&fit=max&w=1920)

Source:
- [3Commas TradingView](https://3commas.io/trading-view)

#### 4. 템플릿 라이브러리
![3Commas 템플릿 라이브러리](https://images.prismic.io/3commas/aQNXELpReVYa31bA_Frame2085663150.png?auto=format%2Ccompress&fit=max&w=2560)

Source:
- [3Commas TradingView](https://3commas.io/trading-view)

#### 5. 시각 규칙 빌더
![3Commas 시각 규칙 빌더](https://images.prismic.io/3commas/aO3YOJ5xUNkB16hM_Frame2085663031.png?auto=format%2Ccompress&fit=max&w=2560)

Source:
- [3Commas TradingView](https://3commas.io/trading-view)

### 3.5 Stoic AI

왜 참고하는가:
- 사용자가 복잡한 편집 대신 전략을 선택하고 운영 상태를 신뢰감 있게 보는 흐름이 강하다.

#### 1. 포트폴리오 화면
![Stoic 포트폴리오 화면](https://4e3b4ec81ff348812278.ucr.io/https%3A//stoic.ai/dist/home/app-portfolio-screen.svg)

Source:
- [Stoic AI](https://stoic.ai/)

#### 2. Meta 전략 화면
![Stoic Meta 전략 화면](https://4e3b4ec81ff348812278.ucr.io/https%3A//stoic.ai/dist/home/app-meta-screen.svg)

Source:
- [Stoic Meta](https://stoic.ai/meta)

#### 3. 인덱스 전략 화면
![Stoic 인덱스 전략 화면](https://4e3b4ec81ff348812278.ucr.io/https%3A//stoic.ai/dist/home/slider2-item1.svg)

Source:
- [Stoic AI](https://stoic.ai/)

#### 4. Fixed Income 화면
![Stoic Fixed Income 화면](https://4e3b4ec81ff348812278.ucr.io/https%3A//stoic.ai/dist/home/slider2-item4.svg)

Source:
- [Stoic AI](https://stoic.ai/)

#### 5. 전략 선택 단계
![Stoic 전략 선택 단계](https://4e3b4ec81ff348812278.ucr.io/https%3A//stoic.ai/dist/home/step2.svg)

Source:
- [Stoic AI](https://stoic.ai/)

## 4. 화면별 벤치마크 매핑표

| StockVision 화면 | 현재 기준 파일 | 가장 참고할 제품 | 가져올 패턴 | 적용 이유 | 우선순위 |
|---|---|---|---|---|---|
| 메인 헤더 | [`Header.tsx`](../../frontend/src/components/main/Header.tsx) | Stoic, 3Commas | 상태 요약을 단일 운영 바에 집약, 연결 상태를 아이콘과 텍스트로 동시 표시 | 지금도 신호등과 톱니는 좋지만 `로컬/브로커/클라우드/엔진/모의·실전`을 한 번에 읽히게 만들면 운영 신뢰감이 커진다 | P1 |
| 메인 리스트 뷰 | [`ListView.tsx`](../../frontend/src/components/main/ListView.tsx) | Composer, Stoic | 종목 카드 안에 `전략 수`, `활성 상태`, `위험 상태`, `최근 신호`를 태그형으로 표현 | 현재는 가격/등락/규칙 수까지는 좋지만 자동매매 상태 맥락이 얇다 | P1 |
| 종목 상세 차트 영역 | [`DetailView.tsx`](../../frontend/src/components/main/DetailView.tsx), [`PriceChart.tsx`](../../frontend/src/components/main/PriceChart.tsx) | TradingView | 차트 하단에 지표/전략/이벤트 레이어 탭 추가, 가격 위 주문/신호 마커 표시 | 상세 뷰의 차트가 현재는 "좋은 조회 도구" 수준이라서, 실행 맥락을 올리면 자동매매 툴 느낌이 강해진다 | P1 |
| 종목 상세 규칙 영역 | [`DetailView.tsx`](../../frontend/src/components/main/DetailView.tsx) | Composer, 3Commas | 규칙 카드를 `조건`, `실행`, `리스크`, `최근 실행 결과`로 나눠 보여주기 | 현재 인라인 편집은 빠르지만 구조가 평면적이라 복잡한 전략이 커질수록 이해가 어렵다 | P1 |
| 온보딩 | [`Onboarding.tsx`](../../frontend/src/pages/Onboarding.tsx) | Stoic | 단계별 카드형 셋업, 각 단계의 완료 기준과 상태 배지 표시 | 현재 단계 구조는 좋고, 여기에 "왜 필요한지"와 "완료 상태"를 더 선명하게 주면 이탈이 줄어든다 | P1 |
| 위험고지 | [`RiskDisclosure.tsx`](../../frontend/src/components/RiskDisclosure.tsx) | Stoic, 3Commas | 체크박스형 확인은 유지하되, "자동매매 책임 분리"를 요약 카드로 시각화 | StockVision의 차별점이 법적/신뢰 UX인데 이 부분을 더 브랜드 자산으로 키울 수 있다 | P1 |
| 브릿지 설치 단계 | [`BridgeInstaller.tsx`](../../frontend/src/components/BridgeInstaller.tsx) | 3Commas | 설치 -> 실행 -> 연결 확인 -> 다음 단계 흐름에 상태 피드백과 오류 대응 문구 추가 | 설치형 제품에서 가장 이탈이 큰 구간이라 운영 메시지를 더 강하게 줘야 한다 | P1 |
| 설정 화면 | [`Settings.tsx`](../../frontend/src/pages/Settings.tsx) | Stoic, QuantConnect | `계정`, `브로커`, `엔진`, `로컬 환경`, `보안` 섹션으로 분리 | 현재는 정보는 있지만 운영 제어판 느낌이 덜하다 | P2 |
| 미래 전략 빌더 | 연결 전, 현재 참조용 [`StrategyBuilder.tsx`](../../frontend/src/pages/StrategyBuilder.tsx) | Composer, 3Commas, TradingView | 위저드형 전략 빌더: 목표 -> 진입 -> 청산 -> 수량 -> 리스크 -> 백테스트 -> 활성화 | 폼 기반 편집보다 진입장벽이 낮고 현재 메인 대시보드의 종목 중심 UX와도 잘 맞는다 | P1 |
| 미래 전략 수정 | 연결 전, 현재 참조용 [`StrategyBuilder.tsx`](../../frontend/src/pages/StrategyBuilder.tsx) | Composer | 블록/문장 혼합 편집기, 변경 전후 diff, 백테스트 즉시 갱신 | 전략 수정 UX는 Composer가 가장 직접적인 레퍼런스다 | P1 |
| 미래 실행 로그 | 연결 전, 현재 참조용 [`ExecutionLog.tsx`](../../frontend/src/pages/ExecutionLog.tsx) | 3Commas, QuantConnect | 실행 단계별 타임라인: Triggered -> Submitted -> Filled/Failed | 자동매매 툴의 신뢰는 로그 해석 가능성에서 나온다 | P2 |

## 5. 화면별 바로 적용할 패턴

### 5.1 Main Dashboard

대상:
- [`MainDashboard.tsx`](../../frontend/src/pages/MainDashboard.tsx)
- [`Header.tsx`](../../frontend/src/components/main/Header.tsx)
- [`ListView.tsx`](../../frontend/src/components/main/ListView.tsx)

가져오면 좋은 패턴:
- Stoic의 `운영 상태 중심 헤더`
- 3Commas의 `연결/자동화 상태 배지`
- Composer의 `전략 존재감이 강한 카드 구조`

적용 방식:
- 헤더 톱니 드롭다운을 "운영 패널"로 격상
- 종목 행에 `활성`, `대기`, `오류`, `최근 신호` 태그 추가
- `내 종목` 탭 상단에 오늘의 자동매매 요약 배너 추가

### 5.2 Detail View

대상:
- [`DetailView.tsx`](../../frontend/src/components/main/DetailView.tsx)
- [`PriceChart.tsx`](../../frontend/src/components/main/PriceChart.tsx)

가져오면 좋은 패턴:
- TradingView의 `차트 중심 정보 레이아웃`
- Composer의 `조건/실행/백테스트 연결성`

적용 방식:
- 차트 아래에 `지표`, `전략`, `체결`, `컨텍스트` 탭 추가
- 차트 위에 매수/매도/규칙 트리거 마커 표시
- 규칙 카드에 `최근 실행 결과`, `최근 실패 이유`, `리스크 한도` 요약 추가

### 5.3 Onboarding

대상:
- [`Onboarding.tsx`](../../frontend/src/pages/Onboarding.tsx)
- [`RiskDisclosure.tsx`](../../frontend/src/components/RiskDisclosure.tsx)
- [`BridgeInstaller.tsx`](../../frontend/src/components/BridgeInstaller.tsx)

가져오면 좋은 패턴:
- Stoic의 `전략 선택 전 신뢰 형성`
- 3Commas의 `연결 단계 시각화`

적용 방식:
- 각 단계 카드에 `목적`, `필수 여부`, `완료 조건` 명시
- 브릿지 설치 단계에 실패 시 FAQ/재시도 버튼 추가
- 위험고지에서 "로컬 실행"과 "ID/PW 미보관"을 더 강하게 강조

### 5.4 Settings

대상:
- [`Settings.tsx`](../../frontend/src/pages/Settings.tsx)

가져오면 좋은 패턴:
- Stoic의 `간단하지만 신뢰감 있는 설정`
- QuantConnect의 `명확한 기능 구획`

적용 방식:
- `브로커`, `엔진`, `보안`, `계정` 4개 카드 구조로 재편
- API 키 저장 상태와 실전/모의 상태를 더 분명하게 표시
- 엔진 로그/최근 이벤트 미리보기 추가

### 5.5 Future Strategy Builder

대상:
- 현재 연결 전 참조 자산

가져오면 좋은 패턴:
- Composer의 `시각 에디터 + 백테스트`
- 3Commas의 `템플릿/자동화`
- TradingView의 `차트 옆 전략 튜닝`

적용 방식:
- 종목 선택 후 전략을 만드는 대신, 상세 뷰 안에서 "이 종목 전략 추가"로 들어가게 설계
- `조건 문장형 편집기`와 `고급 JSON/DSL 보기`를 병행
- 저장 전에 미니 백테스트와 예상 주문 예시를 보여주기

## 6. 우선순위 제안

### P1

- 헤더 운영 패널 강화
- 상세 차트에 신호/체결/규칙 레이어 추가
- 상세 규칙 카드를 구조화
- 온보딩과 브릿지 단계 상태 피드백 강화
- 미래 전략 빌더를 Composer형 위저드/문장형 에디터로 설계

### P2

- 설정 화면을 제어판형으로 재편
- 실행 로그를 단계형 타임라인으로 설계

## 7. 추천 조합

StockVision에 가장 잘 맞는 조합은 하나의 제품을 그대로 닮는 방식이 아니다.

- 차트와 분석 밀도는 TradingView를 따른다
- 전략 작성과 수정 흐름은 Composer를 따른다
- 운영 상태와 자동화 신뢰 표현은 Stoic와 3Commas를 따른다
- 고급 사용자 확장성은 QuantConnect의 정보 구조를 참고한다

즉 제품 포지셔닝은 다음처럼 정리할 수 있다.

`TradingView의 차트 밀도 + Composer의 전략 UX + Stoic의 신뢰형 자동화 + QuantConnect의 확장성`

## 8. 소스

- [Composer](https://www.composer.trade/)
- [QuantConnect Strategies](https://www.quantconnect.com/strategies/)
- [TradingView Features](https://www.tradingview.com/features/)
- [3Commas TradingView](https://3commas.io/trading-view)
- [Stoic AI](https://stoic.ai/)
- [Stoic Meta](https://stoic.ai/meta)
