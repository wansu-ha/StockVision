export interface StrategyPreset {
  id: string
  name: string
  description: string
  category: '추세' | '역추세' | '청산' | '복합'
  script: string
}

export const STRATEGY_PRESETS: StrategyPreset[] = [
  {
    id: 'trend-following',
    name: '추세 추종',
    description: 'MA 추세 확인 후 RSI 눌림목에서 진입, 고정 손절/익절',
    category: '추세',
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
    script: `-- 거래량 폭발 + 이격도 과매도 → 반등 매수
거래량 > 평균거래량(20) * 2 AND 이격도(20) < -5 AND 보유수량 == 0 → 매수 100%

-- 청산
이격도(20) > 3 → 매도 전량
수익률 <= -3 → 매도 전량`,
  },
]
