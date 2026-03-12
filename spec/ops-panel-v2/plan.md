# OpsPanel v2 구현 계획

> 작성일: 2026-03-12 | 상태: 확정 | Phase C (C1 + C2)

## 아키텍처

데이터 흐름:
```
로컬 서버
├── LogDB (logs.db)
│   └── FILL 로그 (meta.realized_pnl)
└── GET /api/logs/daily-pnl (신규)
    └── 일일 실현손익 합산
        └── Response: { realized_pnl, fill_count, win_count, loss_count, win_rate }

프론트엔드
├── OpsPanel 컴포넌트
│   ├── 상태 도트 4개 (로컬/브로커/클라우드/엔진) — C2에서 클릭 드롭다운 추가
│   ├── 일일 P&L 표시 (신규) — "오늘: +32,000원"
│   ├── 요약 — 신호/체결/오류
│   └── 경고 배너 — C2에서 복구 액션 버튼 추가
└── AccountBar 컴포넌트
    └── 일일 P&L 표시 (신규) — "오늘 +32,000 (+0.26%)"
```

## 수정 파일 목록

| 파일 경로 | 변경 내용 |
|----------|---------|
| `local_server/routers/logs.py` | `GET /api/logs/daily-pnl` 엔드포인트 추가 (C1) |
| `local_server/routers/status.py` | 상태 응답에 필드 추가: `uptime_seconds`, `broker.connected_at`, `strategy_engine.active_rules`, `strategy_engine.last_eval_at` (C2) |
| `frontend/src/services/localClient.ts` | `localLogs.dailyPnl()` 메서드 추가, `LogSummary` 타입 확장 (C1, C2) |
| `frontend/src/components/main/OpsPanel.tsx` | 일일 P&L 표시, 상태 드롭다운, 경고 버튼 추가 (C1 + C2) |
| `frontend/src/components/AccountBar.tsx` (또는 `ListView.tsx`) | 일일 P&L 표시 추가 (C1) |

## 구현 순서

### Step 1: `GET /api/logs/daily-pnl` 엔드포인트 구현

**파일**: `local_server/routers/logs.py`

**변경 내용**:
- `/daily-pnl` GET 엔드포인트 추가
- 쿼리 파라미터: `date` (optional, 기본값: 오늘)
- 응답 형식:
  ```python
  {
    "success": True,
    "data": {
      "date": "2026-03-12",
      "realized_pnl": 32000,  # Decimal → int/float 변환
      "fill_count": 3,
      "win_count": 2,
      "loss_count": 1,
      "win_rate": 0.667,  # win_count / fill_count (fill_count > 0일 때)
    },
    "count": 1,
  }
  ```

**구현 로직**:
```python
@router.get("/daily-pnl", summary="일일 실현손익")
async def daily_pnl(
    date: str | None = Query(None, description="기준 날짜 (YYYY-MM-DD). 미지정 시 오늘."),
    _: None = Depends(require_local_secret),
) -> dict[str, Any]:
    """당일 FILL 로그의 실현손익을 합산하여 반환한다."""
    if not date:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    db = get_log_db()

    # FILL 로그 조회
    fills, total = db.query(
        log_type=LOG_TYPE_FILL,
        limit=1000,  # 일일 최대 체결 건수 상정
        date_from=date,
    )

    # 당일 FILL만 필터링 (시간대 확인)
    today_fills = [
        f for f in fills
        if f['ts'].startswith(date)
    ]

    # 손익 계산
    realized_pnl = Decimal("0")
    win_count = 0
    for fill in today_fills:
        meta = fill.get("meta", {})
        pnl = meta.get("realized_pnl")
        if pnl:
            pnl_dec = Decimal(str(pnl))
            realized_pnl += pnl_dec
            if pnl_dec > 0:
                win_count += 1

    fill_count = len(today_fills)
    loss_count = fill_count - win_count
    win_rate = (win_count / fill_count) if fill_count > 0 else 0.0

    return {
        "success": True,
        "data": {
            "date": date,
            "realized_pnl": float(realized_pnl),
            "fill_count": fill_count,
            "win_count": win_count,
            "loss_count": loss_count,
            "win_rate": round(win_rate, 3),
        },
        "count": 1,
    }
```

**Verify**:
- 로컬 서버 실행 후 `curl http://localhost:4020/api/logs/daily-pnl?local_secret=...` 호출
- 응답: `{ success: true, data: { realized_pnl: 0, fill_count: 0, ... } }` (아직 FILL 로그 없음 → 0)
- 로그 기록 후 재조회: 정상적인 손익 값 반환 확인

---

### Step 2: 프론트엔드 API 클라이언트 및 OpsPanel에 일일 P&L 표시

**파일**: `frontend/src/services/localClient.ts`

**변경 내용**:
- 타입 추가:
  ```typescript
  export interface DailyPnL {
    date: string;
    realized_pnl: number;
    fill_count: number;
    win_count: number;
    loss_count: number;
    win_rate: number;
  }

  export interface LogSummary {
    date: string;
    signals: number;
    fills: number;
    orders: number;
    errors: number;
    // C2에서 추가
    pnl?: number;
    pnl_pct?: number;
  }
  ```

- 메서드 추가:
  ```typescript
  export const localLogs = {
    async summary(): Promise<LogSummary | null> {
      // 기존 코드
    },

    async dailyPnl(date?: string): Promise<DailyPnL | null> {
      const url = new URL(`${LOCAL_URL}/api/logs/daily-pnl`);
      if (date) url.searchParams.set('date', date);
      const res = await fetch(url.toString(), {
        headers: { 'X-Local-Secret': getLocalSecret() },
      });
      if (!res.ok) return null;
      const json = await res.json();
      return json.success ? json.data : null;
    },
  };
  ```

**파일**: `frontend/src/components/main/OpsPanel.tsx`

**변경 내용**:
- 일일 P&L 쿼리 추가:
  ```typescript
  const { data: dailyPnl } = useQuery<DailyPnL | null>({
    queryKey: ['dailyPnl'],
    queryFn: () => localLogs.dailyPnl(),
    enabled: localConnected,
    refetchInterval: 30_000,
    retry: false,
  });
  ```

- 요약 섹션(오른쪽) 수정:
  ```typescript
  {/* 오늘의 요약 */}
  <div className="flex items-center gap-3 text-xs text-gray-400 shrink-0">
    {/* 신규: 일일 P&L */}
    {dailyPnl && (
      <span className={dailyPnl.realized_pnl > 0 ? 'text-green-400 font-medium' : dailyPnl.realized_pnl < 0 ? 'text-red-400 font-medium' : 'text-gray-400'}>
        오늘: {dailyPnl.realized_pnl >= 0 ? '+' : ''}{(dailyPnl.realized_pnl / 1000).toFixed(1)}k원
      </span>
    )}

    {/* 기존: 신호/체결/오류 */}
    {summary && (
      <>
        <span>신호 <span className="font-mono text-gray-300">{summary.signals}</span></span>
        <span>체결 <span className="font-mono text-gray-300">{summary.fills}</span></span>
        <span className={summary.errors > 0 ? 'text-red-400' : ''}>
          오류 <span className="font-mono">{summary.errors}</span>
        </span>
      </>
    )}
  </div>
  ```

**Verify**:
- 프론트엔드 개발 서버 실행 후 OpsPanel 렌더링 확인
- "오늘: 0원" 표시됨 (FILL 로그 없음)
- 브라우저 DevTools Network 탭에서 `GET /api/logs/daily-pnl` 호출 확인
- 응답 데이터가 OpsPanel에 표시되는지 확인

---

### Step 3: 계좌바(AccountBar)에 일일 P&L 표시

**파일**: `frontend/src/components/AccountBar.tsx` (또는 `ListView.tsx` 상단)

**변경 내용**:
- 계좌 정보 표시 부분에 일일 P&L 추가:
  ```typescript
  {/* 기존 잔고 표시 */}
  <span>잔고: {formatKRW(balance)}</span>

  {/* 신규: 일일 P&L */}
  {dailyPnl && dailyPnl.realized_pnl !== 0 && (
    <span className={dailyPnl.realized_pnl > 0 ? 'text-green-400' : 'text-red-400'}>
      오늘 {dailyPnl.realized_pnl >= 0 ? '+' : ''}{formatKRW(dailyPnl.realized_pnl)}
      ({dailyPnl.realized_pnl >= 0 ? '+' : ''}{pnl_pct.toFixed(2)}%)
    </span>
  )}
  ```

**주의**:
- `pnl_pct` = `dailyPnl.realized_pnl / 총평가금액 * 100`
- 총평가금액은 브로커 API에서 조회한 잔고 데이터 활용

**Verify**:
- 프론트엔드에서 계좌바 렌더링 확인
- "오늘 +32,000 (+0.26%)" 형태로 표시되는지 확인
- 양수/음수/0일 때 색상 구분 확인

---

### Step 4: 상태 도트 드롭다운 추가 (C2)

**파일**: `frontend/src/components/main/OpsPanel.tsx`

**변경 내용**:
- 상태 도트를 클릭 가능한 버튼으로 변경
- HeroUI `Popover` 또는 `Dropdown` 사용:
  ```typescript
  import { Popover, PopoverContent, PopoverTrigger } from '@heroui/react'

  {statuses.map((s) => (
    <Popover key={s.label} placement="bottom">
      <PopoverTrigger asChild>
        <button className="flex items-center gap-1.5 cursor-pointer hover:opacity-80 transition">
          <div className={`w-2 h-2 rounded-full ${s.color} ${s.ok && s.label === '엔진' ? 'animate-pulse' : ''}`} />
          <span className="text-xs text-gray-400">{s.label}</span>
          <span className={`text-xs ${s.ok ? 'text-gray-300' : 'text-gray-500'}`}>{s.text}</span>
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-48 bg-gray-800 border border-gray-700 rounded-lg p-3">
        {/* 상태별 상세 정보 렌더링 */}
        <StatusDetailsPopover
          label={s.label}
          localHp={localHp}
          broker={brokerStatus}
          cloudOk={cloudOk}
          engineStatus={engineStatus}
        />
      </PopoverContent>
    </Popover>
  ))}
  ```

- 상세 정보 컴포넌트 추가:
  ```typescript
  function StatusDetailsPopover({ label, localHp, broker, cloudOk, engineStatus }) {
    switch (label) {
      case '로컬':
        return (
          <div className="text-xs text-gray-300 space-y-1">
            <div>서버: {localHp?.server || 'N/A'}</div>
            <div>버전: {localHp?.version || 'N/A'}</div>
            <div>가동: {localHp?.uptime_seconds ? formatUptime(localHp.uptime_seconds) : 'N/A'}</div>
            <div>하트비트: {localHp?.last_heartbeat || 'N/A'}</div>
          </div>
        );
      case '브로커':
        return (
          <div className="text-xs text-gray-300 space-y-1">
            <div>증권사: {broker?.type || 'N/A'}</div>
            <div>모드: {broker?.is_mock ? '모의' : '실전'}</div>
            <div>연결: {broker?.connected_at || 'N/A'}</div>
          </div>
        );
      case '클라우드':
        return (
          <div className="text-xs text-gray-300 space-y-1">
            <div>상태: {cloudOk ? '정상' : '연결 불가'}</div>
            <div>응답시간: N/A</div>
          </div>
        );
      case '엔진':
        return (
          <div className="text-xs text-gray-300 space-y-1">
            <div>상태: {engineStatus?.running ? '실행 중' : '정지'}</div>
            <div>활성 전략: {engineStatus?.active_rules || 0}</div>
            <div>마지막 평가: {engineStatus?.last_eval_at || 'N/A'}</div>
          </div>
        );
      default:
        return null;
    }
  }
  ```

**Verify**:
- 각 상태 도트 클릭 → 드롭다운 표시 확인
- 상세 정보 정확성 확인 (버전, 가동 시간, 모드 등)

---

### Step 5: 경고 배너에 복구 액션 버튼 추가 (C2)

**파일**: `frontend/src/components/main/OpsPanel.tsx`

**변경 내용**:
- 경고 배너 각 메시지에 버튼 추가:
  ```typescript
  {/* 경고 배너 */}
  {warnings.length > 0 && (
    <div className="mt-2 pt-2 border-t border-gray-800/50 space-y-1">
      {warnings.map((w) => (
        <div key={w.message} className="flex items-center justify-between gap-2 text-xs text-yellow-400/80">
          <div className="flex items-center gap-1.5">
            <svg className="w-3.5 h-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              {/* 경고 아이콘 */}
            </svg>
            <span>{w.message}</span>
          </div>
          {w.action && (
            <button
              onClick={w.action.onClick}
              className="px-2 py-1 bg-yellow-900/30 hover:bg-yellow-900/50 rounded text-yellow-400 text-xs font-medium transition"
            >
              {w.action.label}
            </button>
          )}
        </div>
      ))}
    </div>
  )}
  ```

- 경고 메시지 객체 구조 변경:
  ```typescript
  interface Warning {
    message: string;
    action?: {
      label: string;
      onClick: () => void | Promise<void>;
    };
  }

  const warnings: Warning[] = []
  if (!isLocalUp) warnings.push({
    message: '로컬 서버 연결 불가 — 서버를 시작하세요',
    action: { label: '설정', onClick: () => navigate('/settings') },
  })
  if (isLocalUp && !brokerConnected) warnings.push({
    message: '브로커 미연결 — 설정에서 API 키를 확인하세요',
    action: { label: '설정', onClick: () => navigate('/settings') },
  })
  // ... 이하 동일
  ```

**Verify**:
- 경고 배너의 각 메시지 옆에 "설정" 버튼 표시 확인
- 버튼 클릭 시 Settings 페이지로 이동 확인

---

## 검증 방법

### 빌드 검증
1. **로컬 서버 기동**:
   ```bash
   cd /d/Projects/StockVision
   python -m uvicorn local_server.main:app --port 4020 --reload
   ```
   - 콘솔 로그 확인: "Uvicorn running on ..."

2. **프론트엔드 개발 서버**:
   ```bash
   cd frontend
   npm run dev
   ```
   - 브라우저 자동 열림: http://localhost:5173

3. **빌드 검증**:
   ```bash
   cd frontend
   npm run build
   ```
   - `dist/` 디렉토리 생성 확인
   - 빌드 에러 없음 확인

### 브라우저 확인 항목

#### C1 (일일 P&L)
- [ ] OpsPanel 우측 "오늘: 0원" (또는 실제 손익) 표시됨
- [ ] 양수: 초록색 (`text-green-400`)
- [ ] 음수: 빨강색 (`text-red-400`)
- [ ] 0: 회색 (`text-gray-400`)
- [ ] 계좌바에 "오늘 +32,000 (+0.26%)" 형태로 표시됨
- [ ] DevTools Network: `GET /api/logs/daily-pnl` 호출 확인 (Status 200)
- [ ] 응답 JSON: `{ success: true, data: { realized_pnl, fill_count, ... } }`

#### C2 (운영 패널 확장)
- [ ] 각 상태 도트 호버: 커서 변경 (pointer)
- [ ] 상태 도트 클릭: Popover/Dropdown 표시
  - 로컬: 버전, 가동 시간, 하트비트 표시
  - 브로커: 증권사, 모의/실전, 연결 시각 표시
  - 클라우드: 상태, 응답 시간 표시
  - 엔진: 실행 상태, 활성 전략 수, 마지막 평가 시각 표시
- [ ] 경고 배너 "설정" 버튼 클릭 → Settings 페이지 이동
- [ ] 경고 메시지 다양성 확인:
  - 로컬 미연결 시: "로컬 서버 연결 불가"
  - 브로커 미연결 시: "브로커 미연결"
  - 클라우드 미연결 시: "클라우드 연결 불가"
  - 엔진 정지 시: "엔진 정지됨"

### 서버 통합 검증
- [ ] 로그 DB에 FILL 레코드 기록됨 (`meta.realized_pnl` 포함)
- [ ] `/api/logs/daily-pnl` 응답:
  ```json
  {
    "success": true,
    "data": {
      "date": "2026-03-12",
      "realized_pnl": 32000,
      "fill_count": 3,
      "win_count": 2,
      "loss_count": 1,
      "win_rate": 0.667
    },
    "count": 1
  }
  ```
- [ ] `/api/status` 응답에 `uptime_seconds`, `connected_at`, `active_rules`, `last_eval_at` 필드 포함

### 성능 검증
- [ ] 초기 로딩: 3초 이내에 OpsPanel 렌더링
- [ ] 새로고침: F5 후 OpsPanel 상태/일일 P&L 정상 표시
- [ ] 리팩치: 30초 주기로 일일 P&L 업데이트 (요약과 동일)

### 엣지 케이스
- [ ] FILL 로그 0건: `fill_count=0, win_rate=0`, 오류 없음
- [ ] 모든 손실(음수): `loss_count=N, win_count=0, win_rate=0`
- [ ] 혼합된 가양/손실: `win_rate` 정확히 계산됨 (예: 2/3 = 0.667)
- [ ] 일일 P&L 0원: "오늘: 0원" (회색)으로 표시

---

## 참고

- 기존 상태 쿼리 주기: 10초 (`refetchInterval: 10_000`)
- 로그 요약 쿼리 주기: 30초 (`refetchInterval: 30_000`)
- OpsPanel 위치: `frontend/src/components/main/OpsPanel.tsx`
- 로컬 클라이언트: `frontend/src/services/localClient.ts`
- 로그 DB API: `local_server/routers/logs.py`
- 상태 API: `local_server/routers/status.py`
