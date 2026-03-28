# YouTube 플레이리스트 종합 분석 — StockVision 인사이트

> 작성일: 2026-03-29 | 원본: "주식" 플레이리스트 by grf fd (26개 영상)
> 배치 리서치: batch1~batch6 (docs/research/youtube-batch*.md)

---

## 1. 코드화 가능한 전략 (전략 엔진 v2 후보)

### Tier 1 — 즉시 구현 가능, 규칙 명확

| 전략 | 지표 | 핵심 규칙 | 출처 |
|------|------|-----------|------|
| **RSI+BB 쌍바닥** | RSI(14), BB(20,2) | RSI≤30 → BB하단 터치 음봉 → 쌍바닥 두번째가 BB안에서 형성 → 장악형 양봉 종가 매수 | batch3 #2 |
| **MACD 영선 돌파 복합** | MACD(12,26,9), RSI(14) | MACD 0선 상향돌파(5봉내) + RSI 50선 상향돌파 → 매수 | batch3 #3 |
| **WB 더블볼린저** | BB(20,2) + R1(4,4,Open) | 두 밴드 동시 터치 후 음봉마감 → 변곡 매도. 승률 78% | batch3 #5 |
| **변동성 돌파** (Larry Williams) | 전일 고저차 | 목표가 = 시가 + (전일고가-전일저가)×K(0.5). 15:15 강제청산 | batch1 #4 |
| **거래량 소진→돌파** (Steven Dux) | Vol MA(10) | 거래량폭발 → 박스권 → Vol<MA*0.5 → 저항돌파 양봉 매수. 손익비 1:3 | batch5 #1 |
| **FVG 감지** (ICT) | 3캔들 패턴 | Bullish: C1.high < C3.low. 가격이 FVG 진입 시 매수 | batch4 #1,2 |

### Tier 2 — 구현 가능하지만 파라미터 튜닝 필요

| 전략 | 지표 | 핵심 규칙 | 출처 |
|------|------|-----------|------|
| **VWMA 100 반등** | VWMA(100) | 가격이 VWMA100 하향이탈 후 재상향돌파 + 정배열 전환 → 매수. 손익비 6:1 | batch3 #4 |
| **RSI 페일류 스윙** | RSI(14), MACD | RSI 30이하에서 반복 돌파실패 → MACD선>시그널선일 때 진짜 돌파 = 매수 | batch3 #3 |
| **하이킨아시 추세전환** | HA캔들 | 하락중 도지 2+개 → 강세양봉 전환 → 매수. 스토캐스틱+거래량 보조 필수 | batch3 #1 |
| **RSI 다이버전스+MACD** | RSI, MACD | 가격 저점↓ RSI 저점↑ + MACD 골든크로스 → 장악형 양봉 종가 매수 | batch3 #2 |

### Tier 3 — 개념적, 추가 연구 필요

| 개념 | 설명 | 자동화 가능성 |
|------|------|--------------|
| ICT 4-질문 체크리스트 | 킬존 + 유동성스윕 + FVG형성 + FVG반응 = AND 로직 | 중간 (시간필터+패턴감지 조합) |
| Market Structure (BOS/ChoCH) | HH/HL 패턴으로 추세 방향 확정 | 높음 (스윙포인트 감지) |
| Order Block | 마지막 반대색 캔들 = 기관 주문 위치 | 중간 |
| PO3/AMD 패턴 | 축적→조작→분배 = 페이크아웃 감지 | 낮음 (사후적 판단) |
| Opening Range | 오픈 30분 고저점 → 이탈 방향 = 당일 방향 | 높음 |

---

## 2. 전략 엔진 설계 원칙 (26개 영상 공통)

### 2.1 모든 영상이 동의하는 원칙

1. **단일 지표 금지** — 반드시 2개 이상 복합 확인 (5/5 기술분석 영상 동의)
2. **손절 필수** — 손절 없는 전략 = 전략이 아님 (전 영상 동의)
3. **손익비 최소 1:1, 권장 1:2~1:3** (batch3, batch5)
4. **백테스팅 필수** — 수수료 포함, 타임프레임 일치 (batch1 #2 실패 사례)
5. **단순함이 복잡함을 이긴다** — 2~3개 규칙이 20개 규칙보다 강함 (batch4 #5, batch3 #4)

### 2.2 전략 조건 필수 구성 요소

```
모든 전략에 필수:
1. 진입 조건 (최소 2개 지표 AND)
2. 손절가 (필수, 미설정 시 전략 실행 불가)
3. 익절가 (분할 청산 비율 설정)
4. 포지션 크기 (포트폴리오 대비 최대 비중)
5. 타임프레임 (백테스트와 실전 일치 필수)
```

---

## 3. 플랫폼 기능 인사이트

### 3.1 자동매매 UX (높은 확신)

| 기능 | 근거 | 우선순위 |
|------|------|---------|
| **텔레그램 리모콘** (start/stop/report) | batch2 #1 키움영웅전 — 실제 사용 패턴 | 높음 |
| **전략 파라미터 hot-reload** | batch2 #1 — 장중 익절/손절 비율 변경 | 높음 |
| **Discord/텔레그램 알림** | batch1 #3,#4 — 매수/매도 + 헬스체크 분리 | 높음 |
| **자동 손절 강제 실행** | batch6 #4, batch5 #3 — 감정 배제 핵심 | 최우선 |
| **반익절 자동화** | batch6 #4 — 목표가 도달 시 절반 청산 + 본절 SL | 높음 |
| **당일 청산 옵션** | batch1 #4 — 15:15~15:20 강제 전량 매도 | 중간 |
| **매매 일지 자동 기록** | batch6 #4, batch5 #3 | 중간 |

### 3.2 종목 스크리닝 (명확한 미해결 니즈)

| 기능 | 근거 |
|------|------|
| **거래대금 + 등락률 + 뉴스 재료 스크리닝** | batch1 #3 공돌투자자 — "AI로 자동화 원하지만 미완성" |
| **MACD 영선돌파 + 52주 고점 -10% + 거래대금 상위** | batch3 #3 엘리트강사 조건검색식 |
| **순간체결량 ≥ 3,000만원 필터** | batch5 #3 방탄 (영웅전 1위) |
| **작전주 위험 필터** | batch5 #4 — 소형주+저거래량+투자경고 자동 제외 |
| **거래량 5패턴 자동 분류** | batch5 #2 — 패턴C(vol↓+price↑) = 가장 강한 매수 |

### 3.3 리스크 관리

| 기능 | 근거 |
|------|------|
| **포트폴리오 상관관계 리스크 점수** | batch6 #5 — 분산투자 수학적 원리 |
| **출금 권장 알림** | batch6 #4 — 수익 시 10~20% 인출 습관화 |
| **패닉 방지 팝업** | batch6 #2 — 급락 시 전략 원칙 상기 |
| **라운드넘버 손절 경고** | batch4 #3 — 1000/5000/10000 등 기관 스윕 위치 |
| **물타기 차단 옵션** | batch5 #3 — "물타기 절대 금지, 불타기만 허용" |

### 3.4 백테스팅 (Phase E 설계 참고)

| 요구사항 | 근거 |
|---------|------|
| **수수료+슬리피지 반드시 포함** | batch1 #2 노마드코더 — 미포함 시 실전 괴리 |
| **타임프레임 일관성 검증** | batch1 #2 — 30분봉 백테스트 → 1분봉 실전 = 실패 |
| **손익비 통계** | batch3 전체 — 모든 전략이 손익비 명시 |
| **승률 + 기대값 표시** | batch3 #5 — WB 전략 승률 78% 수치 검증 |

---

## 4. 구현 우선순위 제안

### Phase 1 — 전략 엔진 v2 핵심

```
1. 기술 지표 라이브러리
   - RSI(14), MACD(12,26,9), BB(20,2), VWMA, SMA/EMA
   - FVG 감지 (3캔들 패턴)
   - 거래량 MA 돌파/소진 감지

2. 전략 조건 빌더
   - 복합 조건 AND/OR 조합
   - 손절/익절 필수 설정
   - 반익절 + 본절SL 자동 전환

3. 기본 제공 전략 템플릿
   - 변동성 돌파 (입문자용, 가장 검증됨)
   - RSI+BB 쌍바닥 (중급)
   - MACD 영선 복합 (중급)
```

### Phase 2 — 스크리닝 + 알림

```
1. 조건 검색 엔진 (MACD 영선 + 거래대금 + 52주 고점)
2. 텔레그램/Discord 알림 통합
3. 거래량 패턴 자동 분류 (A~E)
4. 작전주 위험 필터
```

### Phase 3 — 고급 전략 + 백테스트

```
1. ICT/SMC 개념 (FVG, 유동성존, BOS/ChoCH)
2. WB 더블볼린저
3. 백테스팅 엔진 (수수료 포함)
4. 포트폴리오 리스크 점수
```

---

## 5. 핵심 코드 스니펫 (전략 엔진 구현 참고)

### FVG 감지
```python
def detect_fvg(candles):
    fvgs = []
    for i in range(len(candles) - 2):
        c1, c2, c3 = candles[i], candles[i+1], candles[i+2]
        if c1.high < c3.low:  # Bullish FVG
            fvgs.append({'type': 'bullish', 'top': c3.low, 'bottom': c1.high})
        elif c1.low > c3.high:  # Bearish FVG
            fvgs.append({'type': 'bearish', 'top': c1.low, 'bottom': c3.high})
    return fvgs
```

### WB 더블볼린저
```python
def double_bollinger(prices, opens):
    bb_mid = sma(prices, 20)
    bb_upper = bb_mid + 2 * std(prices, 20)
    bb_lower = bb_mid - 2 * std(prices, 20)
    r1_mid = sma(opens, 4)
    r1_upper = r1_mid + 4 * std(opens, 4)
    r1_lower = r1_mid - 4 * std(opens, 4)
    return bb_upper, bb_lower, r1_upper, r1_lower
```

### 거래량 패턴 분류
```python
def classify_volume_pattern(vol_change, price_change, threshold=0.01):
    vol_up = vol_change > 0
    price_up = price_change > threshold
    price_down = price_change < -threshold
    if vol_up and price_up: return 'A'      # 매물대 형성
    if vol_up and price_down: return 'B'     # 즉시 매도
    if not vol_up and price_up: return 'C'   # 강한 매수 (세력 관리)
    if not vol_up and price_down: return 'D' # 매도 경고
    return 'E'                                # 2차 상승 대기
```

### MACD 영선 돌파 조건검색
```python
def macd_zero_cross_scanner(stocks, n_bars=5):
    hits = []
    for stock in stocks:
        macd = stock.macd_line
        if any(macd[-i-2] < 0 and macd[-i-1] >= 0 for i in range(n_bars)):
            if stock.rsi[-1] >= 50:
                if stock.price >= stock.high_52w * 0.9:
                    if stock.avg_trade_value_rank <= 100:
                        hits.append(stock)
    return hits
```

---

## 6. 자주 언급된 외부 도구/서비스

| 도구 | 용도 | 언급 횟수 |
|------|------|----------|
| TradingView | 차트 분석, 하이킨아시, 볼린저 | 5회 |
| 텔레그램 봇 | 원격 제어, 뉴스 속보 | 3회 |
| Discord Webhook | 매매 알림, 헬스체크 | 2회 |
| Cursor IDE | AI 코딩 보조 | 2회 |
| 키움 REST API | 국내 주식 매매 | 4회 |
| KIS (한국투자증권) API | 국내+해외 주식 | 1회 |
| Yahoo Finance API | 글로벌 시세 데이터 | 1회 |

---

## 7. 시장 참여자 프로파일 (타겟 사용자 이해)

### 영상에 등장한 실제 트레이더

| 이름 | 스타일 | 운용 규모 | 핵심 도구 | StockVision 적합성 |
|------|--------|----------|----------|-------------------|
| 공돌투자자 | 시스템+수동 하이브리드 | 5억 | Python, 구글 원격 | **매우 높음** — 우리의 주 타겟 |
| 방탄 (영웅전1위) | 재료+스캘핑 | 500만 | HTS, 텔레그램 | 높음 — 스크리닝+알림 니즈 |
| 불장단타왕 | VWMA+이평선 | 월3~13억 | TradingView | 중간 — 지표 커스터마이징 |
| 김직선 | WB 더블볼린저 | $120만/월 | TradingView | 중간 — 전략 템플릿 |
| 스티븐 덕스 | 거래량 소형주 | $4,800만 누적 | 전용 플랫폼 | 참고 — 거래량 분석 로직 |

### 공통 페인포인트 (우리가 해결할 문제)

1. **감정 통제 실패** → 자동 손절/반익절로 해결
2. **원격 모니터링 불편** → 클라우드+로컬 아키텍처로 해결
3. **종목 스크리닝 수동** → AI+조건검색 엔진으로 해결
4. **뉴스 재료 분석 불가** → Claude API 통합으로 해결
5. **백테스팅 부재** → Phase E 백테스트 엔진으로 해결
6. **전략 파라미터 실시간 변경 불가** → hot-reload 기능으로 해결

---

*원본 배치 파일: docs/research/youtube-batch{1..6}*.md*
