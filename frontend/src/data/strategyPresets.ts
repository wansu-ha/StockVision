export interface StrategyPreset {
  id: string
  name: string
  description: string
  category: '추세' | '역추세' | '청산' | '복합' | '돌파' | '모멘텀' | '추세전환'
  difficulty: '초보' | '중급' | '고급'
  marketCondition: string
  script: string
}

export const STRATEGY_PRESETS: StrategyPreset[] = [
  {
    id: 'trend-following',
    name: '추세 추종',
    description: 'MA 추세 확인 후 RSI 눌림목에서 진입, 고정 손절/익절',
    category: '추세',
    difficulty: '초보',
    marketCondition: '추세장',
    script: `기간 = 14

-- 추세 이탈 → 최우선 청산
MA(20) <= MA(60) AND 보유수량 > 0 → 매도 전량

-- 진입
RSI(기간) < 30 AND MA(20) > MA(60) AND 보유수량 == 0 → 매수 100%

-- 청산
수익률 <= -2 → 매도 전량
수익률 >= 5 → 매도 전량`,
  },
  {
    id: 'multi-exit',
    name: '다단계 청산 + 트레일링',
    description: '손절 우선, 1차 익절 50%, 잔여분 트레일링, 횡보 시간 청산',
    category: '청산',
    difficulty: '중급',
    marketCondition: '모든 장세',
    script: `-- 손절 (최우선)
수익률 <= -2 → 매도 전량

-- 1차 익절 (1회만 실행)
수익률 >= 3 AND 실행횟수 < 1 → 매도 50%

-- 잔여분 트레일링
고점 대비 <= -1.5 → 매도 나머지

-- 시간 청산 (횡보 방지)
보유일 >= 3 AND 수익률 BETWEEN -1 AND 1 → 매도 전량`,
  },
  {
    id: 'dca',
    name: 'DCA (분할 매수)',
    description: 'RSI 하락 시 분할 진입, 고정 손절/익절',
    category: '역추세',
    difficulty: '중급',
    marketCondition: '횡보/하락장',
    script: `기간 = 14

-- 1차 진입
RSI(기간) < 30 AND 보유수량 == 0 → 매수 50%

-- 2차 추가 매수 (더 떨어지면)
RSI(기간) < 20 AND 보유수량 > 0 → 매수 30%

-- 청산
수익률 >= 5 → 매도 전량
수익률 <= -5 → 매도 전량`,
  },
  {
    id: 'breakeven-trailing',
    name: '브레이크이븐 + 트레일링',
    description: '수익 2% 달성 후 본전 청산 안전장치 + 고점 트레일링',
    category: '청산',
    difficulty: '고급',
    marketCondition: '모든 장세',
    script: `-- 손절
수익률 <= -2 → 매도 전량

-- 브레이크이븐: 2% 달성한 적 있으면 본전에서 청산
횟수(수익률 >= 2, 보유봉) >= 1 AND 수익률 <= 0 → 매도 전량

-- 트레일링
고점 대비 <= -1.5 → 매도 전량`,
  },
  {
    id: 'time-sequential',
    name: '시간 필터 + 순차 조건',
    description: '장 시작 10분 후, 골든크로스 3봉 이내 RSI 눌림목 진입',
    category: '복합',
    difficulty: '고급',
    marketCondition: '추세장',
    script: `-- 장 시작 10분 후 + 골든크로스 3봉 이내 + RSI 눌림목
장시작후 >= 10 AND 횟수(골든크로스, 3) >= 1 AND RSI(14) < 35 AND 보유수량 == 0 → 매수 100%

-- 청산
수익률 <= -2 → 매도 전량
고점 대비 <= -1.5 → 매도 전량`,
  },
  {
    id: 'atr-dynamic',
    name: 'ATR 동적 청산',
    description: 'ATR 기반 변동성 적응형 손절/익절',
    category: '청산',
    difficulty: '고급',
    marketCondition: '변동성 장',
    script: `배수 = 2

-- ATR 기반 동적 손절
현재가 <= 진입가 - ATR(14) * 배수 → 매도 전량

-- ATR 기반 동적 익절
현재가 >= 진입가 + ATR(14) * 배수 * 1.5 → 매도 전량

-- 진입
RSI(14) < 30 AND 보유수량 == 0 → 매수 100%`,
  },
  {
    id: 'volume-disparity',
    name: '거래량 + 이격도 반등',
    description: '거래량 폭발 + 이격도 과매도에서 반등 매수',
    category: '역추세',
    difficulty: '중급',
    marketCondition: '횡보장',
    script: `-- 거래량 폭발 + 이격도 과매도 → 반등 매수
거래량 > 평균거래량(20) * 2 AND 이격도(20) < -5 AND 보유수량 == 0 → 매수 100%

-- 청산
이격도(20) > 3 → 매도 전량
수익률 <= -3 → 매도 전량`,
  },
  // ── 신규 프리셋 8개 ──
  {
    id: 'macd-golden',
    name: 'MACD 골든크로스',
    description: 'MACD 시그널 상향돌파 + RSI 추세 확인 진입',
    category: '추세',
    difficulty: '초보',
    marketCondition: '추세장',
    script: `MACD골든크로스 AND RSI(14) >= 50 AND 보유수량 == 0 → 매수 100%
MACD데드크로스 AND 보유수량 > 0 → 매도 전량
수익률 <= -3 → 매도 전량`,
  },
  {
    id: 'bb-rsi-reversal',
    name: '볼린저밴드 + RSI 역추세',
    description: '볼린저 하단 + RSI 과매도 이중 확인 후 반등 매수',
    category: '역추세',
    difficulty: '초보',
    marketCondition: '횡보장',
    script: `볼린저하단돌파 AND RSI과매도 AND 보유수량 == 0 → 매수 100%
볼린저상단돌파 OR RSI과매수 → 매도 전량
수익률 <= -4 → 매도 전량`,
  },
  {
    id: 'stochastic-bounce',
    name: '스토캐스틱 과매도 반등',
    description: '스토캐스틱 골든크로스 + MA 추세 확인 진입',
    category: '역추세',
    difficulty: '중급',
    marketCondition: '횡보/눌림목',
    script: `슬로잉 = 3

상향돌파(STOCH_K(5, 슬로잉), STOCH_D(5, 슬로잉)) AND STOCH_K(5, 슬로잉) <= 25 AND MA(20) > MA(60) AND 보유수량 == 0 → 매수 100%
수익률 >= 4 OR STOCH_K(5, 슬로잉) >= 80 → 매도 전량
수익률 <= -3 → 매도 전량`,
  },
  {
    id: 'macd-divergence',
    name: 'MACD 히스토그램 다이버전스',
    description: '가격과 MACD 히스토그램의 다이버전스로 추세 전환 포착',
    category: '추세전환',
    difficulty: '고급',
    marketCondition: '추세 말기',
    script: `기간 = 20

강세다이버전스(MACD_HIST(), 기간) AND RSI(14) < 50 AND 보유수량 == 0 → 매수 100%
약세다이버전스(MACD_HIST(), 기간) AND 보유수량 > 0 → 매도 전량
수익률 <= -3 → 매도 전량`,
  },
  {
    id: 'triple-ma',
    name: '삼선 정배열 (5/20/60)',
    description: 'MA 5>20>60 정배열 달성 시 진입, 역배열 시 청산',
    category: '추세',
    difficulty: '초보',
    marketCondition: '강 상승장',
    script: `MA(5) > MA(20) AND MA(20) > MA(60) AND RSI(14) < 60 AND 보유수량 == 0 → 매수 100%
MA(5) < MA(20) AND 보유수량 > 0 → 매도 전량
수익률 <= -3 → 매도 전량`,
  },
  {
    id: 'bb-squeeze-breakout',
    name: '볼린저밴드 스퀴즈 돌파',
    description: '볼린저 상단 돌파 + 거래량 확인으로 박스권 탈출 포착',
    category: '돌파',
    difficulty: '중급',
    marketCondition: '박스권 탈출',
    script: `배수 = 1.5

상향돌파(현재가, 볼린저_상단(20)) AND 거래량 > 평균거래량(20) * 배수 AND 보유수량 == 0 → 매수 100%
고점 대비 <= -2 → 매도 전량
수익률 <= -3 → 매도 전량`,
  },
  {
    id: 'morning-momentum',
    name: '장 초반 급등 모멘텀',
    description: '장 시작 30분 이내 급등 + 거래량 폭발 종목 포착',
    category: '모멘텀',
    difficulty: '중급',
    marketCondition: '테마/이슈',
    script: `시간제한 = 30
목표수익 = 3
손절 = -2

등락률 >= 3 AND 장시작후 <= 시간제한 AND 거래량 > 평균거래량(20) * 3 AND 보유수량 == 0 → 매수 100%
수익률 >= 목표수익 → 매도 전량
수익률 <= 손절 → 매도 전량
장시작후 >= 180 AND 보유수량 > 0 → 매도 전량`,
  },
  {
    id: 'ema-cross',
    name: 'EMA 크로스 추세 추종',
    description: 'EMA 12/26 교차로 추세 전환 감지, MA보다 빠른 반응',
    category: '추세',
    difficulty: '초보',
    marketCondition: '추세장',
    script: `단기 = 12
장기 = 26

상향돌파(EMA(단기), EMA(장기)) AND 보유수량 == 0 → 매수 100%
하향돌파(EMA(단기), EMA(장기)) AND 보유수량 > 0 → 매도 전량
수익률 <= -3 → 매도 전량`,
  },
]
