# 차트 이벤트 마커 (Chart Event Markers)

> 작성일: 2026-03-11 | 상태: 구현 완료 | Phase B

## 1. 배경

PriceChart에 매수/매도/실패 이벤트를 시각적으로 표시하여 전략 실행 결과를 차트에서 직관적으로 확인할 수 있어야 한다.

## 2. 목표

PriceChart에 체결/거부 이벤트가 마커로 표시된다.

## 3. 범위

### 포함

- 체결 로그(FILL)를 PriceChart에 마커로 표시
- 매수(BUY) / 매도(SELL) / 실패(REJECTED) 마커 구분
- lightweight-charts v5 `createSeriesMarkers` API 사용

### 제외

- 실행 로그 타임라인 (Phase C 항목)
- 마커 클릭 상세 팝업

## 4. 데이터 소스

### 4.1 기존 API

`GET /api/logs?log_type=fill&symbol={symbol}&limit=200`

응답 구조 (기존):
```json
{
  "items": [{
    "ts": "2026-03-11T14:30:45.123456+00:00",
    "log_type": "FILL",
    "symbol": "005930",
    "message": "BUY 100주 005930 — FILLED",
    "meta": {
      "side": "BUY",
      "qty": 100,
      "status": "FILLED",
      "rule_id": 42
    }
  }]
}
```

### 4.2 날짜 매핑

로그 `ts`(ISO datetime)에서 날짜 부분(`YYYY-MM-DD`)을 추출하여 캔들 `time`과 매칭.
같은 날 여러 이벤트가 있으면 모두 표시.

## 5. 마커 디자인

| 이벤트 | shape | position | color | text |
|--------|-------|----------|-------|------|
| BUY 체결 | `arrowUp` | `belowBar` | `#3b82f6` (blue) | `매수` |
| SELL 체결 | `arrowDown` | `aboveBar` | `#ef4444` (red) | `매도` |
| 거부/실패 | `circle` | `aboveBar` | `#f59e0b` (amber) | `실패` |

## 6. 기술 설계

### 6.1 PriceChart 변경

PriceChart가 직접 로그를 fetch한다 (prop으로 받지 않음).
- `useQuery`로 로그 호출. 기존 `LogFilter`에 `log_type`이 없으므로 params를 직접 전달:
  `client.get('/logs', { params: { log_type: 'FILL', symbol, limit: 200 } })`
- API 응답은 `{ data: { items: [{ ts, meta: { side, status } }] } }` 구조 (raw 로그)
- `createSeriesMarkers(mainSeries, markers)` 로 마커 설정

### 6.2 마커 갱신 타이밍

- 메인 시리즈가 교체될 때 (차트 타입 변경) → 마커 재생성
- 데이터(bars)가 변경될 때 → 마커 업데이트
- 로그 데이터가 변경될 때 → 마커 업데이트

### 6.3 마커 생성 로직

```typescript
function buildMarkers(logs: LogItem[], startDate: string): SeriesMarker[] {
  return logs
    .filter(log => log.ts.slice(0, 10) >= startDate)
    .map(log => ({
      time: log.ts.slice(0, 10),
      position: log.meta.side === 'BUY' ? 'belowBar' : 'aboveBar',
      shape: log.meta.status === 'FILLED'
        ? (log.meta.side === 'BUY' ? 'arrowUp' : 'arrowDown')
        : 'circle',
      color: log.meta.status !== 'FILLED' ? '#f59e0b'
        : log.meta.side === 'BUY' ? '#3b82f6' : '#ef4444',
      text: log.meta.status !== 'FILLED' ? '실패'
        : log.meta.side === 'BUY' ? '매수' : '매도',
    }))
    .sort((a, b) => (a.time < b.time ? -1 : a.time > b.time ? 1 : 0))
}
```

### 6.4 createSeriesMarkers 관리

`createSeriesMarkers`는 시리즈에 바인딩된다. 시리즈가 교체되면(차트 타입 변경) 기존 마커 프리미티브는 무효화되므로 새로 생성해야 한다.

```
markersRef = useRef<ReturnType<typeof createSeriesMarkers> | null>(null)
```

시리즈 교체 시: 마커 ref도 null로 리셋 → 데이터 설정 후 재생성.

## 7. 수용 기준

- [ ] BUY 체결 시 파란 arrowUp 마커가 봉 아래에 표시된다
- [ ] SELL 체결 시 빨간 arrowDown 마커가 봉 위에 표시된다
- [ ] 거부/실패 시 노란 circle 마커가 표시된다
- [ ] 차트 타입 전환 후에도 마커가 유지된다
- [ ] 기간 변경 시 해당 기간의 마커만 표시된다
- [ ] 체결 데이터가 없으면 마커 없이 정상 렌더링된다
