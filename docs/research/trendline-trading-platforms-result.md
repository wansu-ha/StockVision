# 리서치: 추세선 기반 자동매매 플랫폼

> 작성일: 2026-03-28 | 목적: StockVision 차트 조건 매매 기능 설계 참고

---

## 핵심 질문

"차트에 선을 그어서 가격이 그 선을 돌파하면 매수/매도" 기능을 제공하는 플랫폼은?

---

## 플랫폼별 요약

### 1. TrendSpider (trendspider.com) — 가장 완성도 높음

**자동 추세선 탐지:**
- 알고리즘이 swing high/low를 연결하여 수학적으로 추세선 자동 생성
- 모든 추세선을 스코어링(바운스/돌파 횟수 상위 1%만 표시)
- 단기/중기/장기 자동 탐지

**브레이크아웃 감지:**
- 자동/수동 추세선 모두 브레이크아웃 마킹 지원
- 유효 조건: 해당 타임프레임의 캔들 1개가 추세선 반대편에 완전히 닫혀야 유효
- 상향 돌파(빨간 원) / 하향 돌파 시각 표시

**자동매매 연동:**
- "Alerts & Bots" 시스템으로 브로커 API와 연결, 실제 주문 실행 가능
- 조건 예시: "가격이 저항 추세선 위로 돌파 + RSI 30~70 + 거래량 10일 평균 2배"
- Sidekick AI: 자연어로 조건 설정 가능 (2025년 추가)
- 멀티타임프레임 추세선 동시 표시 및 컨플루언스 감지

**결론: 알림 + 실제 주문 실행 모두 가능. 가장 기능이 완성된 플랫폼.**

---

### 2. TradingView (tradingview.com) — 알림만, 실행은 3rd-party 필요

**수동 추세선 알림:**
- 수평선/추세선에 우클릭 → "Add Alert" → Crossing / Crossing Up / Crossing Down 조건 설정
- 이메일, SMS, 웹훅 알림 지원

**자동 추세선 스크립트 (Pine Script):**
- `Auto Trendline & Breakout Alert (BobRivera990)`: 돌파 시 즉시 알림, Cross-Over/Under 선택 가능
- `Auto Trend Lines Breakouts & Bounces`: EMA 위/아래에 따라 LONG/SHORT 신호 필터
- 거래량 확인 필터 내장 (20기간 SMA 이상일 때만 신호)

**실제 주문 실행:**
- TradingView 자체는 실행 불가
- **PickMyTrade**, **Webhooks + 브로커 API** 연동 필요

**결론: 알림 전용. 실행은 외부 도구 필수.**

---

### 3. ProRealTime / ProRealTrend (prorealtime.com) — 직접 실행 지원

- ProRealTrend 선(수평/경사 모두)에 직접 주문 연결 가능
- 가격이 선을 돌파하는 순간 시장에 주문 자동 전송
- 지지/저항선 접근 중인 종목 스캐너 내장
- **결론: "선 그리기 → 주문 실행" 가장 직접적인 워크플로우**

---

### 4. MetaTrader 4/5 + FXSSI AutoTrendLines

- MT4/MT5 차트에 자동 추세선 플로팅 + 브레이크아웃/바운스 시각화
- 전략: 상승추세선 터치 → 매수, 하락추세선 터치 → 매도
- Expert Advisor(EA)로 자동 주문 실행 가능 (FX 중심)
- **결론: FX/CFD 특화, 자동 실행 가능**

---

### 5. cTrader — Polynomial Regression Channel 네이티브 지원

- Polynomial Regression Channel (PRC) 인디케이터 기본 내장
- cBot(자동매매 봇)으로 PRC 신호 기반 자동 주문 가능
- **결론: 회귀선 채널 기반 자동매매 지원**

---

## 선 종류별 지원 현황

| 선 종류 | TrendSpider | TradingView | ProRealTime | cTrader/MT4 |
|---------|-------------|-------------|-------------|-------------|
| 수동 추세선 | ✅ | ✅ | ✅ | ✅ |
| 자동 추세선 | ✅ (AI 스코어링) | ✅ (Pine Script) | ✅ | ✅ |
| 선형 회귀선 | ✅ | ✅ | ✅ | ✅ |
| 이차/다항 회귀 | ❌ | ✅ (스크립트) | ❌ | ✅ (네이티브) |
| 채널 (상/하단) | ✅ | ✅ | ✅ | ✅ |
| 지지/저항 | ✅ | ✅ | ✅ | ✅ |

---

## Polynomial/Quadratic Regression 플랫폼

**TradingView (Pine Script):**
- `Polynomial Regression Channel [ChartPrime]`: 행렬 기반 n차 회귀, 미래 연장선 투영
- `Polynomial Regression Bands + Channel [DW]`: 사용자 설정 표준편차 밴드
- `Quadratic Regression Trend Channel`: 2차 포물선 피팅
- 스캐너에서 조건 검색 가능 (ThinkorSwim)

**cTrader:**
- PRC 인디케이터 기본 내장, cBot으로 자동 실행

**한계:**
- 3차 이상 다항식은 과적합 위험 (bias-variance tradeoff)
- 급격한 뉴스 이벤트에 후행 (lagging)

---

## 한국 플랫폼

### 키움증권 영웅문 HTS

**차트 추세선:**
- 직선 추세선 수동 그리기 지원
- 자동 추세선: [단기/중기/장기] 버튼으로 자동 작도 (파동전향수 기반)
- 피보나치 아크 지원

**조건검색:**
- 이동평균 크로스, MACD, RSI 등 내장 조건
- 수식관리자로 커스텀 지표/함수 작성 가능
- **추세선 돌파를 조건으로 쓰는 내장 기능은 없음** (지표 기반만)

**자동매매 — 시그널 메이커:**
- 자연어 유사 프로그래밍으로 매수/매도 전략 작성
- 자동/반자동 주문 실행 가능
- 영웅문G HTS 내 사용 등록 필요
- Windows 전용

**한계:** 추세선을 직접 조건으로 연결하는 기능 없음. 조건검색은 지표값 기반.

### 대신증권 (Cybos)
- 검색 결과에서 추세선 자동매매 관련 정보 미발견
- Cybos Plus API로 커스텀 자동매매 구현 가능하나 추세선 연동은 별도 구현 필요

---

## StockVision 설계 시사점

1. **핵심 차별화**: 국내 플랫폼에는 "추세선 돌파 → 자동주문" 직접 연결 기능이 없음. 구현 시 강력한 차별점.

2. **추세선 표현 방식**:
   - 두 점(timestamp, price)으로 정의되는 선분 + 연장
   - 기울기(slope)와 y-절편으로 저장 → 현재 가격과 비교

3. **돌파 조건 판정**:
   - TrendSpider 방식: 캔들 완전 종가 기준 (intraday 부분 돌파 제외)
   - 또는 종가 + n틱 버퍼 방식

4. **회귀선 우선순위**:
   - 1단계: 선형 회귀 (단순, 직관적)
   - 2단계: 이차 회귀 (포물선 추세)
   - 3차 이상은 과적합 위험 → 제외 또는 선택적

5. **알림 vs 실행**:
   - TradingView는 알림만, ProRealTime/TrendSpider는 실행까지
   - StockVision은 KIS/키움 API 직접 연동으로 실행까지 지원 가능

---

## 참고 링크

- [TrendSpider Automated Trendline Detection](https://help.trendspider.com/kb/automated-technical-analysis/automated-trendline-detection)
- [TrendSpider Breakout Detection](https://help.trendspider.com/kb/automated-technical-analysis/breakout-detection)
- [TradingView Auto Trendline & Breakout Alert](https://www.tradingview.com/script/TmcfwWKU-Auto-Trendline-Breakout-Alert-Linear-Log-Full-Version/)
- [ProRealTime ProRealTrend](https://www.prorealtime.com/en/automatic-support-resistance-trendlines)
- [cTrader Polynomial Regression Channel](https://clickalgo.com/polynomial-regression-channels)
- [cTrader PRC cBot](https://ctrader.com/algos/cbots/show/1940/)
- [키움증권 종합차트 도움말](https://download.kiwoom.com/hero4_help_new/0600.htm)
- [키움증권 시그널 메이커](https://www.kiwoom.com/m/invest/premium/VSignalMakerInfoView)
- [PickMyTrade TradingView 자동화](https://blog.pickmytrade.trade/tradovate-auto-trendline-trade-automation/)
