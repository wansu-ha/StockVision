# 차트 타입 전환 (Chart Type Switcher)

> 작성일: 2026-03-11 | 상태: 구현 완료 | Phase B

## 1. 배경

PriceChart 컴포넌트는 현재 캔들스틱 한 가지 형식만 지원한다.
사용자가 차트 표시 형식을 전환하며 다른 관점에서 가격 데이터를 볼 수 있어야 한다.

## 2. 목표

PriceChart에서 5가지 차트 타입을 전환할 수 있다.

## 3. 범위

### 포함

- 차트 타입 5종 지원: 캔들스틱, 속빈 캔들, 하이킨 아시, OHLC 바, 라인
- 타입 전환 UI (기간 선택과 동일한 버튼 그룹 패턴)
- 타입별 데이터 변환 (하이킨 아시)
- 볼륨 히스토그램은 모든 타입에서 유지

### 제외

- 차트 이벤트 마커 (별도 Phase B 항목)
- 사용자별 기본 타입 저장 (Phase E 개인화)
- Renko, Kagi, Point & Figure 등 시간축 비호환 타입

## 4. 차트 타입 정의

| ID | 라벨 | lightweight-charts 시리즈 | 데이터 형식 | 비고 |
|----|-------|--------------------------|-------------|------|
| `candle` | 캔들 | CandlestickSeries | OHLC 원본 | 현재 기본값 |
| `hollow` | 속빈 | CandlestickSeries | OHLC 원본 | 양봉: upColor transparent, borderVisible true |
| `heikin` | 하이킨 | CandlestickSeries | HA 변환 OHLC | HA 공식 적용 |
| `ohlc` | OHLC | BarSeries | OHLC 원본 | 미국식 틱마크 바 |
| `line` | 라인 | LineSeries | 종가만 | 종가 연결선 |

### 4.1 하이킨 아시 변환 공식

```
HA Close = (O + H + L + C) / 4
HA Open  = (prev HA Open + prev HA Close) / 2  (첫 봉: (O + C) / 2)
HA High  = max(H, HA Open, HA Close)
HA Low   = min(L, HA Open, HA Close)
```

### 4.2 속빈 캔들 스타일링

- 양봉 (close > open): `upColor: 'transparent'`, `borderUpColor: '#ef4444'`, `wickUpColor: '#ef4444'`
- 음봉 (close < open): `downColor: '#3b82f6'`, `borderDownColor: '#3b82f6'`, `wickDownColor: '#3b82f6'`
- `borderVisible: true` 필수

### 4.3 라인 스타일링

- `color: '#a78bfa'` (indigo 계열, 기존 accent와 구분)
- `lineWidth: 2`

## 5. UI 설계

### 5.1 전환 버튼 위치

기간 선택 버튼 그룹 **왼쪽**에 차트 타입 버튼 그룹을 배치한다.
두 그룹 사이에 구분선(`border-r border-gray-700`)을 넣는다.

```
[ 캔들 | 속빈 | 하이킨 | OHLC | 라인 ]  |  [ 1W | 1M | 3M | 6M | 1Y ]     전체 보기
```

### 5.2 버튼 스타일

기존 기간 선택 패턴과 동일:
- 활성: `bg-indigo-600 text-white`
- 비활성: `text-gray-500 hover:text-gray-300 hover:bg-gray-800`
- `role="group"`, `aria-label="차트 타입"`, `aria-pressed`

### 5.3 기본값

`candle` (현재 동작과 동일)

## 6. 기술 설계

### 6.1 상태 관리

`PriceChart` 내부에 `chartType` state 추가. 외부 prop 불필요.

```typescript
type ChartType = 'candle' | 'hollow' | 'heikin' | 'ohlc' | 'line'
const [chartType, setChartType] = useState<ChartType>('candle')
```

### 6.2 시리즈 전환 로직

타입 변경 시:
1. 기존 메인 시리즈 제거 (`chart.removeSeries`)
2. 새 시리즈 추가 (`chart.addSeries`) — 볼륨 위에 그려짐 (z-order 정상)
3. 변환된 데이터 설정 (`series.setData`)
4. 볼륨 시리즈는 유지 (제거/재추가 불필요)
5. `fitContent` 호출하지 않음 — 현재 스크롤/줌 위치 유지

### 6.3 데이터 변환

- `candle`, `hollow`, `ohlc`: 원본 OHLC 그대로 사용
- `heikin`: 순수 함수 `toHeikinAshi(bars: DailyBar[]): OhlcData[]`로 변환
- `line`: `{ time, value: close }` 매핑

변환 함수는 `PriceChart.tsx` 내 모듈 스코프에 정의한다 (별도 파일 불필요).

## 7. 수용 기준

- [ ] 5가지 차트 타입이 모두 렌더링된다
- [ ] 타입 전환 시 차트가 깜빡임 없이 부드럽게 전환된다
- [ ] 하이킨 아시 데이터가 공식대로 변환된다
- [ ] 속빈 캔들에서 양봉 몸통이 비어 있다
- [ ] 볼륨 히스토그램이 모든 타입에서 표시된다
- [ ] 기간 변경/줌 리셋이 모든 타입에서 동작한다
- [ ] 타입 변경 후 기간 유지 (리셋 안 됨)
