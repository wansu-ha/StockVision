# 차트 타임프레임 — 구현 계획

> 작성일: 2026-03-15 | 상태: 확정 | 갱신: 2026-03-18 (Stage 1+2 구현 완료) | spec: `spec/chart-timeframe/spec.md`

## 의존관계

```
Stage 1 (로컬 서버 분봉 API) ─── 독립
Stage 2 (클라우드 주봉/월봉)  ─── 독립
     └── Stage 1, 2 병렬 가능
                │
Stage 3 (프론트엔드)        ─── Stage 1 + 2 완료 후
     └── Step 3a (해상도 UI)
     └── Step 3b (데이터 분기)
     └── Step 3c (lazy load)
```

---

## Stage 1: 로컬 서버 분봉 API

### Step 1-1: 분봉 저장 모델 + SQLite 테이블

**파일**: `local_server/storage/minute_bar.py` (신규)

로컬 SQLite에 1분봉 저장/조회/정리 담당.

```python
class MinuteBarStore:
    """로컬 SQLite 분봉 저장소."""

    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._ensure_table()

    def _ensure_table(self) -> None:
        """minute_bars 테이블 생성 (없으면)."""
        # CREATE TABLE IF NOT EXISTS minute_bars (
        #   symbol TEXT, timestamp TEXT,
        #   open REAL, high REAL, low REAL, close REAL, volume INTEGER,
        #   PRIMARY KEY (symbol, timestamp)
        # )

    def save_bars(self, symbol: str, bars: list[dict]) -> int:
        """분봉 목록 upsert. 저장 건수 반환."""

    def get_bars(self, symbol: str, start: str, end: str) -> list[dict]:
        """기간 내 1분봉 조회. ISO 타임스탬프 기준."""

    def get_range(self, symbol: str) -> tuple[str, str] | None:
        """저장된 데이터 범위 반환 (최소~최대 timestamp)."""

    def purge_old(self, days: int = 30) -> int:
        """N일 이전 데이터 삭제. 삭제 건수 반환."""
```

**검증**:
- [ ] 테이블 자동 생성
- [ ] upsert 중복 방지
- [ ] 30일 이전 데이터 정리

### Step 1-2: BarBuilder 영속화

**파일**: `local_server/engine/bar_builder.py` (수정)

현재 BarBuilder는 완성된 1분봉을 메모리에만 보관. SQLite에도 저장하도록 확장.

```python
# bar_builder.py 수정
class BarBuilder:
    def __init__(self, ..., minute_bar_store: MinuteBarStore | None = None):
        self._store = minute_bar_store

    def _complete_bar(self, symbol: str) -> Bar:
        bar = ...  # 기존 로직
        if self._store:
            self._store.save_bars(symbol, [bar.to_dict()])
        return bar
```

**검증**:
- [ ] WS 틱 수신 → 1분봉 완성 시 SQLite에 저장
- [ ] store 없을 때 기존 동작 유지 (하위 호환)

### Step 1-3: KIS REST 분봉 조회

**파일**: `local_server/broker/kis/quote.py` (수정)

KIS REST API로 과거 분봉 조회 기능 추가.

```python
async def get_minute_bars(
    self, symbol: str, start: str, end: str
) -> list[dict]:
    """KIS REST 분봉 조회.

    - API: 국내주식 당일분봉조회 (FHKST03010200)
    - 최대 30일, 1회 최대 30건 → 페이지네이션 필요
    """
```

**검증**:
- [ ] KIS REST 분봉 API 호출 성공
- [ ] 페이지네이션으로 전체 구간 조회
- [ ] mock 어댑터에서 stub 데이터 반환

### Step 1-4: 분봉 집계 로직

**파일**: `local_server/storage/minute_bar.py` (확장)

1분봉 → 5분/15분/시봉 집계 함수.

```python
def aggregate_bars(
    bars_1m: list[dict], resolution: str
) -> list[dict]:
    """1분봉 리스트를 지정 해상도로 집계.

    resolution: '5m' | '15m' | '1h'
    각 구간의 open=첫봉open, high=max, low=min, close=마지막봉close, volume=sum.
    """
```

**검증**:
- [ ] 60개 1분봉 → 1개 시봉 정확
- [ ] 구간 경계 정확 (09:00~09:04 = 5분봉 1개)
- [ ] 불완전 구간(장 마감 등) 처리

### Step 1-5: 분봉 API 엔드포인트

**파일**: `local_server/routers/bars.py` (신규), `local_server/main.py` (수정)

```python
# routers/bars.py
router = APIRouter(prefix="/api/v1/bars", tags=["bars"])

@router.get("/{symbol}")
async def get_bars(
    symbol: str,
    resolution: str = Query("1m", regex="^(1m|5m|15m|1h)$"),
    start: str | None = Query(None),
    end: str | None = Query(None),
):
    """분봉 조회.

    데이터 소스 우선순위:
    1. 로컬 SQLite (BarBuilder가 수집한 분봉)
    2. KIS REST API (과거 분봉 조회, 캐시 미스 시)
    3. 데이터 없으면 빈 배열

    5m/15m/1h는 1분봉을 집계하여 반환.
    """
    # 1. SQLite에서 1분봉 조회
    # 2. 캐시 미스 구간 → KIS REST로 보충 → SQLite 저장
    # 3. resolution != '1m' → aggregate_bars()
    # 4. 응답 반환
```

응답 형식:
```json
{
  "success": true,
  "data": [{ "time": "...", "open": ..., "high": ..., "low": ..., "close": ..., "volume": ... }],
  "count": 360,
  "resolution": "1m",
  "source": "local_db"
}
```

**검증**:
- [ ] `GET /api/v1/bars/005930?resolution=1m` 정상 응답
- [ ] `resolution=5m` → 집계된 데이터 반환
- [ ] KIS REST 캐시 미스 시 보충 후 저장
- [ ] 브로커 미연결 시 로컬 DB만 반환

---

## Stage 2: 클라우드 서버 주봉/월봉

### Step 2-1: bars API resolution 파라미터 추가

**파일**: `cloud_server/api/market_data.py` (수정)

```python
@router.get("/{symbol}/bars")
async def get_bars(
    symbol: str,
    start: str | None = None,
    end: str | None = None,
    resolution: str = Query("1d", regex="^(1d|1w|1mo)$"),  # 신규
    ...
):
    if resolution == "1d":
        # 기존 로직 그대로
        ...
    elif resolution in ("1w", "1mo"):
        daily_bars = # 일봉 조회 (기존 로직)
        return aggregate_daily_bars(daily_bars, resolution)
```

### Step 2-2: 일봉 → 주봉/월봉 집계

**파일**: `cloud_server/services/market_service.py` (수정 또는 신규 함수)

```python
def aggregate_daily_bars(
    bars: list[DailyBar], resolution: str
) -> list[dict]:
    """일봉 → 주봉(1w) 또는 월봉(1mo) 집계.

    주봉: 월~금 기준 (ISO week)
    월봉: 해당 월 전체
    """
```

**검증**:
- [ ] `?resolution=1w` → 주봉 데이터 반환
- [ ] `?resolution=1mo` → 월봉 데이터 반환
- [ ] `resolution` 미지정 → 일봉 (기존 호환)
- [ ] 주봉 경계가 ISO week 기준 정확

---

## Stage 3: 프론트엔드

### Step 3-1: 타입 및 상수 정의

**파일**: `frontend/src/types/chart.ts` (신규 또는 기존 확장)

```typescript
export type Resolution = '1m' | '5m' | '15m' | '1h' | '1d' | '1w' | '1mo'

export const RESOLUTION_CONFIG: Record<Resolution, {
  label: string
  source: 'local' | 'cloud'
  periods: { label: string; value: string }[]
  defaultPeriod: string
}> = {
  '1m':  { label: '1분', source: 'local',  defaultPeriod: '1D',
           periods: [{ label: '1D', value: '1D' }, { label: '3D', value: '3D' }, { label: '1W', value: '1W' }, { label: '2W', value: '2W' }, { label: '1M', value: '1M' }] },
  '5m':  { label: '5분', source: 'local',  defaultPeriod: '3D',  periods: /* 1m과 동일 */ },
  '15m': { label: '15분', source: 'local', defaultPeriod: '1W',  periods: /* 1m과 동일 */ },
  '1h':  { label: '1시간', source: 'local', defaultPeriod: '2W', periods: [/* 1W, 2W, 1M */] },
  '1d':  { label: '일',  source: 'cloud',  defaultPeriod: '3M',
           periods: [{ label: '1M', value: '1M' }, { label: '3M', value: '3M' }, { label: '6M', value: '6M' }, { label: '1Y', value: '1Y' }, { label: 'ALL', value: 'ALL' }] },
  '1w':  { label: '주',  source: 'cloud',  defaultPeriod: '1Y',  periods: [/* 6M, 1Y, 3Y, ALL */] },
  '1mo': { label: '월',  source: 'cloud',  defaultPeriod: '3Y',  periods: [/* 1Y, 3Y, 5Y, ALL */] },
}
```

### Step 3-2: 로컬 서버 bars 클라이언트

**파일**: `frontend/src/services/localClient.ts` (수정)

```typescript
export const localBars = {
  get: async (symbol: string, resolution: string, start?: string, end?: string) => {
    const { data } = await localApi.get<{
      data: BarData[]; resolution: string; source: string
    }>(`/api/v1/bars/${symbol}`, { params: { resolution, start, end } })
    return data
  },
}
```

### Step 3-3: 클라우드 bars 클라이언트 확장

**파일**: `frontend/src/services/cloudClient.ts` (수정)

```typescript
export const cloudBars = {
  get: async (symbol: string, start?: string, end?: string, resolution: string = '1d') => {
    const { data } = await cloudApi.get<{ data: DailyBar[] }>(
      `/api/v1/stocks/${symbol}/bars`,
      { params: { start, end, resolution } },
    )
    return data.data ?? []
  },
}
```

기존 호출부(`PriceChart.tsx`)는 `resolution` 미전달 시 `'1d'` 기본값 → 하위 호환.

### Step 3-4: PriceChart 해상도 UI

**파일**: `frontend/src/components/main/PriceChart.tsx` (수정)

```tsx
// 새 상태
const [resolution, setResolution] = useState<Resolution>('1d')
const config = RESOLUTION_CONFIG[resolution]

// 해상도 버튼 그룹
<div className="flex gap-1">
  {/* 장중 그룹 */}
  <div className="flex gap-1 border-r border-gray-700 pr-2 mr-2">
    {(['1m', '5m', '15m', '1h'] as Resolution[]).map(r => (
      <button
        key={r}
        disabled={!isLocalConnected && RESOLUTION_CONFIG[r].source === 'local'}
        onClick={() => handleResolutionChange(r)}
        className={/* 선택/비활성 스타일 */}
        title={!isLocalConnected ? '브릿지 연결 필요' : undefined}
      >
        {RESOLUTION_CONFIG[r].label}
      </button>
    ))}
  </div>
  {/* 장기 그룹 */}
  <div className="flex gap-1">
    {(['1d', '1w', '1mo'] as Resolution[]).map(r => (
      <button key={r} onClick={() => handleResolutionChange(r)} ...>
        {RESOLUTION_CONFIG[r].label}
      </button>
    ))}
  </div>
</div>

// 기간 버튼: config.periods에서 동적 생성
<div className="flex gap-1">
  {config.periods.map(p => (
    <button key={p.value} onClick={() => setPeriod(p.value)} ...>
      {p.label}
    </button>
  ))}
</div>
```

**검증**:
- [ ] 해상도 버튼 7개 표시
- [ ] 장중 버튼: 로컬 미연결 시 비활성 + 툴팁
- [ ] 해상도 변경 → 기간 버튼 세트 전환
- [ ] 현재 선택 해상도/기간 하이라이트

### Step 3-5: 데이터 소스 분기

**파일**: `frontend/src/components/main/PriceChart.tsx` (수정 — 쿼리 로직)

```tsx
const { data: bars } = useQuery({
  queryKey: ['bars', symbol, resolution, period, startStr, endStr],
  queryFn: async () => {
    if (RESOLUTION_CONFIG[resolution].source === 'local') {
      const res = await localBars.get(symbol, resolution, startStr, endStr)
      return res.data
    } else {
      return cloudBars.get(symbol, startStr, endStr, resolution)
    }
  },
  enabled: !!symbol,
  staleTime: resolution === '1d' ? 60_000 : 10_000,
})
```

**검증**:
- [ ] 일봉/주봉/월봉 → 클라우드 호출
- [ ] 분봉/시봉 → 로컬 서버 호출
- [ ] 로컬 미연결 + 분봉 선택 → 에러 처리

### Step 3-6: 과거 데이터 Lazy Load

**파일**: `frontend/src/components/main/PriceChart.tsx` (수정)

```tsx
// 로드 범위 추적
const loadedRangeRef = useRef<{ start: string; end: string } | null>(null)

// lightweight-charts onVisibleTimeRangeChanged 콜백
const handleVisibleRangeChange = useMemo(
  () => debounce((range: { from: number; to: number }) => {
    const visibleStart = new Date(range.from * 1000).toISOString()
    if (loadedRangeRef.current && visibleStart < loadedRangeRef.current.start) {
      // 좌측 끝에 도달 → 추가 데이터 요청
      fetchMoreBars(visibleStart, loadedRangeRef.current.start)
    }
  }, 250),
  [resolution, symbol]
)
```

**검증**:
- [ ] 좌측 스크롤 → 디바운스 200~300ms 후 과거 데이터 요청
- [ ] 이미 로드된 구간 재요청 방지
- [ ] 줌 인/아웃이 데이터 요청을 트리거하지 않음

---

## 변경 파일 요약

| 파일 | Stage | 변경 |
|------|-------|------|
| `local_server/storage/minute_bar.py` | 1-1 | **신규** — SQLite 분봉 저장소 |
| `local_server/engine/bar_builder.py` | 1-2 | 완성 바 → SQLite 영속화 |
| `local_server/broker/kis/quote.py` | 1-3 | KIS REST 분봉 조회 추가 |
| `local_server/routers/bars.py` | 1-5 | **신규** — 분봉 API 엔드포인트 |
| `local_server/main.py` | 1-5 | 라우터 등록 |
| `cloud_server/api/market_data.py` | 2-1 | resolution 파라미터 추가 |
| `cloud_server/services/market_service.py` | 2-2 | 주봉/월봉 집계 함수 |
| `frontend/src/types/chart.ts` | 3-1 | **신규** — Resolution 타입/상수 |
| `frontend/src/services/localClient.ts` | 3-2 | localBars 추가 |
| `frontend/src/services/cloudClient.ts` | 3-3 | cloudBars.get resolution 파라미터 |
| `frontend/src/components/main/PriceChart.tsx` | 3-4~6 | 해상도 UI + 데이터 분기 + lazy load |

**총 11개 파일** (신규 3, 수정 8)

---

## 블로커 & 리스크

| 항목 | 상세 | 대응 |
|------|------|------|
| KIS REST 분봉 API | TR ID: FHKST03010200, 30건/회 제한 | 페이지네이션 구현, mock 테스트 |
| 분봉 데이터 법적 제약 | 클라우드에서 분봉 수집/재배포 불가 | 로컬 서버에서만 조회 (spec 설계 준수) |
| lightweight-charts lazy load | `onVisibleTimeRangeChanged` 콜백 지원 확인 필요 | 라이브러리 문서 확인 |
| 분봉 디스크 사용량 | 종목당 1분봉 30일 ≈ 0.5MB | 자동 정리 (purge_old) |
