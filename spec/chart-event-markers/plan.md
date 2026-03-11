# 차트 이벤트 마커 — 구현 계획

> 작성일: 2026-03-11 | 상태: 구현 완료 | spec: `spec/chart-event-markers/spec.md`

## 변경 파일

| 파일 | 변경 | 설명 |
|------|------|------|
| `frontend/src/components/main/PriceChart.tsx` | 수정 | 마커 로직 추가 (fetch, 변환, createSeriesMarkers) |

## 구현 단계

### Step 1: import 추가

`lightweight-charts`에서 `createSeriesMarkers` 추가 import.
`localClient`에서 HTTP client import (로그 fetch용).

```typescript
import { createSeriesMarkers } from 'lightweight-charts'
```

**verify**: 빌드 에러 없음

### Step 2: 로그 fetch

PriceChart 내부에 useQuery 추가. 기존 `LogFilter`에 `log_type`이 없으므로 `as never` 캐스트 (MainDashboard와 동일 패턴).

```typescript
const { data: fillLogs } = useQuery({
  queryKey: ['fillLogs', symbol],
  queryFn: () => symbol
    ? localLogs.get({ log_type: 'FILL', symbol, limit: 200 } as never)
    : Promise.resolve([]),
  enabled: !!symbol,
  refetchInterval: 30_000,
})
```

`localLogs.get`은 내부에서 `r.data.data ?? r.data`를 반환하므로 결과는 `{ items: [...] }` 객체 또는 배열.
각 item은 raw 로그: `{ ts, symbol, meta: { side, qty, status } }`.
MainDashboard와 동일한 파싱: `Array.isArray(raw) ? raw : (raw?.items ?? [])`.

**verify**: 데이터 없어도 빈 배열, 에러 시에도 빈 배열

### Step 3: 마커 변환 함수

모듈 스코프에 순수 함수 추가:

```typescript
interface FillLog {
  ts: string
  meta: { side: string; status: string; qty?: number }
}

function buildMarkers(logs: FillLog[], startDate: string) {
  return logs
    .filter(l => l.ts.slice(0, 10) >= startDate)
    .map(l => {
      const filled = l.meta.status === 'FILLED'
      const buy = l.meta.side === 'BUY'
      return {
        time: l.ts.slice(0, 10),
        position: buy ? 'belowBar' as const : 'aboveBar' as const,
        shape: filled ? (buy ? 'arrowUp' as const : 'arrowDown' as const) : 'circle' as const,
        color: !filled ? '#f59e0b' : buy ? '#3b82f6' : '#ef4444',
        text: !filled ? '실패' : buy ? '매수' : '매도',
      }
    })
    .sort((a, b) => a.time < b.time ? -1 : a.time > b.time ? 1 : 0)
}
```

**verify**: 빈 배열 → 빈 배열, BUY/SELL/REJECTED 각각 올바른 마커 생성

### Step 4: 마커 ref 및 갱신 로직

기존 데이터/타입 useEffect에서 마커를 관리한다.

```typescript
const markersRef = useRef<ReturnType<typeof createSeriesMarkers> | null>(null)
```

시리즈 전환 로직에서:
- 시리즈 교체 시(`typeChanged`): `markersRef.current = null` (기존 프리미티브 무효)
- 데이터 설정 후: `buildMarkers` → `createSeriesMarkers` 또는 `setMarkers`

```
if (!markersRef.current) {
  markersRef.current = createSeriesMarkers(mainSeriesRef.current, markers)
} else {
  markersRef.current.setMarkers(markers)
}
```

**주의**: 차트 init useEffect에서도 `markersRef.current = null` 리셋 필요 (StrictMode 대응).

**verify**: 타입 변경 시 마커 유지, 기간 변경 시 마커 업데이트

### Step 5: useEffect 의존성 업데이트

데이터/타입 useEffect의 의존성에 `fillLogs` 추가:

```typescript
useEffect(() => { ... }, [bars, chartType, fillLogs])
```

**verify**: 로그 데이터 갱신 시 마커 자동 업데이트

## 검증 계획

1. `npm run build` — 타입 에러/빌드 에러 없음
2. 체결 데이터 없는 종목 → 마커 없이 차트 정상 렌더링
3. 체결 데이터 있는 종목 → 해당 날짜에 마커 표시 (현재 테스트 데이터 없으므로 시각적 검증은 실매매 후)
4. 차트 타입 전환 → 마커 유지
5. 기간 변경 → 해당 기간 마커만 표시
