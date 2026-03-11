# 차트 타입 전환 — 구현 계획

> 작성일: 2026-03-11 | 상태: 구현 완료 | spec: `spec/chart-type-switcher/spec.md`

## 변경 파일

| 파일 | 변경 | 설명 |
|------|------|------|
| `frontend/src/components/main/PriceChart.tsx` | 수정 | 유일한 변경 파일. 타입 상태, 전환 UI, 시리즈 로직, 변환 함수 |

## 구현 단계

### Step 1: 타입 정의 및 상수

`PriceChart.tsx` 모듈 스코프에 추가:

```typescript
type ChartType = 'candle' | 'hollow' | 'heikin' | 'ohlc' | 'line'

const CHART_TYPES: { id: ChartType; label: string }[] = [
  { id: 'candle', label: '캔들' },
  { id: 'hollow', label: '속빈' },
  { id: 'heikin', label: '하이킨' },
  { id: 'ohlc',   label: 'OHLC' },
  { id: 'line',   label: '라인' },
]
```

**verify**: 타입 에러 없음

### Step 2: 하이킨 아시 변환 함수

모듈 스코프에 순수 함수 추가:

```typescript
function toHeikinAshi(bars: DailyBar[]): { time: string; open: number; high: number; low: number; close: number }[] {
  // HA 공식 적용, 첫 봉은 (O+C)/2로 HA Open 초기화
}
```

**verify**: 빈 배열 → 빈 배열, 단일 봉 → 정상 변환

### Step 3: 시리즈 타입별 옵션 맵

타입별 시리즈 생성 로직을 함수로 분리:

```typescript
function createMainSeries(chart: IChartApi, type: ChartType): ISeriesApi<...>
```

- `candle`: CandlestickSeries, 현재 색상
- `hollow`: CandlestickSeries, upColor transparent, borderVisible true
- `heikin`: CandlestickSeries, 현재 색상 (데이터만 다름)
- `ohlc`: BarSeries, 동일 색상
- `line`: LineSeries, violet-400

**verify**: 각 타입에 맞는 시리즈 객체 반환

### Step 4: 데이터 변환 디스패치

타입에 따라 시리즈에 넣을 데이터를 결정하는 함수:

```typescript
function transformData(bars: DailyBar[], type: ChartType): CandlestickData[] | LineData[]
```

- `candle`, `hollow`, `ohlc`: OHLC 매핑
- `heikin`: `toHeikinAshi(bars)`
- `line`: `{ time, value: close }` 매핑

**verify**: 각 타입별 출력 형식 정확

### Step 5: 컴포넌트 상태 및 시리즈 전환 로직

1. `chartType` state 추가
2. `chartType` 또는 `bars` 변경 시 useEffect:
   - 기존 메인 시리즈 제거
   - 새 메인 시리즈 생성 + 데이터 설정
   - `candleSeriesRef` 업데이트
3. 초기 차트 생성 useEffect에서 메인 시리즈 생성 로직을 제거하고, 데이터 useEffect로 통합

**핵심 변경**: 기존에 분리되어 있던 "차트 생성 (한 번)"과 "데이터 업데이트" useEffect를 재구성:
- 차트 생성 useEffect(`[]`): chart + volume만 생성. 메인 시리즈는 생성하지 않음.
- 데이터/타입 useEffect(`[chartType, bars]`):
  - `prevTypeRef`로 이전 타입 추적
  - 타입 변경 시에만 기존 시리즈 제거 → 새 시리즈 생성
  - 데이터만 변경 시 기존 시리즈에 setData만 호출
  - 볼륨 색상은 항상 원본 OHLC 기준 (HA 변환과 무관)

**ref 타입**: `candleSeriesRef`는 `ReturnType<IChartApi['addSeries']> | null`로 유지 (현재와 동일). CandlestickSeries, BarSeries, LineSeries 모두 호환.

**verify**: 타입 전환 시 차트 정상 렌더링, 기간 변경 시에도 정상, 불필요한 시리즈 재생성 없음

### Step 6: 전환 UI 렌더링

기간 선택 버튼 왼쪽에 차트 타입 버튼 그룹 추가:

```tsx
<div className="flex items-center gap-1" role="group" aria-label="차트 타입">
  {CHART_TYPES.map(t => (
    <button key={t.id} onClick={() => setChartType(t.id)} aria-pressed={chartType === t.id}
      className={`px-2.5 py-1 text-xs rounded-md transition ${...}`}>
      {t.label}
    </button>
  ))}
</div>
<div className="w-px h-4 bg-gray-700 mx-1" />  {/* 구분선 */}
{/* 기존 기간 선택 그룹 */}
```

**verify**: 5개 버튼 렌더링, 활성 상태 표시, 기간 선택과 시각적 분리

### Step 7: import 추가

`lightweight-charts`에서 `BarSeries`, `LineSeries` 추가 import.

**verify**: 빌드 에러 없음

## 검증 계획

1. `npm run build` — 타입 에러/빌드 에러 없음
2. 브라우저에서 5가지 타입 모두 전환 확인
3. 하이킨 아시: 양봉 비율이 원본 캔들보다 높은지 시각적 확인 (노이즈 감소 특성)
4. 속빈 캔들: 양봉 몸통이 비어 있는지 확인
5. 타입 변경 후 기간 변경 → 정상 동작
6. 타입 변경 후 줌/스크롤 → 위치 유지
