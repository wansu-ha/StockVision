# E2E 프리셋 셀렉터 수정 명세서

> 작성일: 2026-03-31 | 상태: 초안

---

## 1. 문제

`frontend/e2e/strategy-v2.spec.ts`에서 5개 테스트가 실패한다.

**근본 원인**: `page.getByText('추세 추종')`이 두 요소에 매칭된다:
1. 프리셋 "추세 추종" (id: `trend-following`)
2. 프리셋 "EMA 크로스 **추세 추종**" (id: `ema-cross`)

Playwright strict mode에서 2개 이상 매칭은 에러. V1, V2, V4, V6에서 직접 발생하고, V3(DCA)은 같은 에러로 프리셋 패널이 안 열리면서 연쇄 실패.

**프리셋 이름 목록** (`frontend/src/data/strategyPresets.ts`, 15개):

| # | id | name |
|---|---|---|
| 1 | trend-following | 추세 추종 |
| 2 | multi-exit | 다단계 청산 + 트레일링 |
| 3 | dca | DCA (분할 매수) |
| 4 | breakeven-trail | 브레이크이븐 + 트레일링 |
| 5 | time-filter | 시간 필터 + 순차 조건 |
| 6 | atr-exit | ATR 동적 청산 |
| 7 | volume-divergence | 거래량 + 이격도 반등 |
| 8 | macd-golden | MACD 골든크로스 |
| 9 | bollinger-rsi | 볼린저밴드 + RSI 역추세 |
| 10 | stoch-bounce | 스토캐스틱 과매도 반등 |
| 11 | macd-divergence | MACD 히스토그램 다이버전스 |
| 12 | triple-ma | 삼선 정배열 (5/20/60) |
| 13 | bb-squeeze | 볼린저밴드 스퀴즈 돌파 |
| 14 | morning-momentum | 장 초반 급등 모멘텀 |
| 15 | ema-cross | EMA 크로스 추세 추종 |

## 2. 수정 방향

**테스트 셀렉터를 `getByText` → `getByText(exact)` 또는 `getByRole`로 교체.**

프리셋 이름 자체는 바꾸지 않는다. UI 컴포넌트에 test-id가 없으면 `{ exact: true }` 옵션으로 정확 매칭한다.

## 3. 영향 테스트 목록

| 테스트 | 실패 원인 | 수정 |
|--------|----------|------|
| V1 (line 27) | `getByText('추세 추종')` 2개 매칭 | `exact: true` 추가 |
| V2 (line 43, 46) | 동일 | `exact: true` 추가 |
| V3 (line 76) | V2와 같은 원인으로 프리셋 선택 실패 → textarea 비어있음 | V2 수정으로 해소 확인 필요 |
| V4 (line 86, 90) | 동일 | `exact: true` 추가 |
| V6 (line 126) | 동일 | `exact: true` 추가 |

## 4. 수용 기준

- [ ] `npx playwright test e2e/strategy-v2.spec.ts` 8개 전부 PASS
- [ ] 프리셋 이름 변경 없음
- [ ] UI 컴포넌트 변경 없음 (테스트만 수정)
