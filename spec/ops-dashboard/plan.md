# 운영 대시보드 강화 — 구현 계획

> 작성일: 2026-03-12 | 상태: 구현 완료 | spec: `spec/ops-dashboard/spec.md`

## 전제 조건 확인

| 항목 | 현재 상태 |
|------|----------|
| `GET /api/logs` 날짜 필터 | ❌ 없음 — `log_db.query()`에 date 파라미터 없음 |
| `GET /api/logs/summary` | ❌ 없음 |
| 로그 meta에 intent_id/cycle_id | ⚠️ cycle_id 생성됨, 로그 기록 시 포함 여부 미확인 |
| 상태 API (`GET /api/status`) | ✅ broker, engine, credentials 포함 |
| `localHealth.check()` | ✅ 동작 |
| `cloudHealth.check()` | ✅ 동작 |

## 구현 순서

A파트(운영 패널)를 먼저 완성하고, B파트(실행 로그 타임라인)는 백엔드 변경 후 진행.

---

## Part A: 운영 패널 강화

### Step 1: 로그 날짜 필터 + 요약 API 추가

**파일**: `local_server/storage/log_db.py`, `local_server/routers/logs.py`

log_db.py 변경:
```python
def query(
    self,
    log_type: str | None = None,
    symbol: str | None = None,
    limit: int = 100,
    offset: int = 0,
    date_from: str | None = None,  # 추가: 'YYYY-MM-DD'
) -> tuple[list[dict[str, Any]], int]:
```

WHERE 절에 `ts >= ?` 조건 추가 (date_from이 있을 때).

요약 전용 메서드 추가:
```python
def count_by_type(self, date_from: str) -> dict[str, int]:
    """오늘 날짜 기준 log_type별 건수 반환."""
    # → { 'STRATEGY': 12, 'FILL': 3, 'ERROR': 0, ... }
```

logs.py 라우터 변경:
- `query_logs`에 `date_from` 파라미터 추가
- 새 엔드포인트 `GET /api/logs/summary?date=YYYY-MM-DD` 추가

**verify**: curl로 `/api/logs?date_from=2026-03-12` 및 `/api/logs/summary?date=2026-03-12` 테스트

### Step 2: 프론트엔드 localClient에 API 추가

**파일**: `frontend/src/services/localClient.ts`

```typescript
localLogs.summary: (date: string) => client.get('/logs/summary', { params: { date } }).then(...)
```

기존 `localLogs.get`에 `date_from` 옵션 추가.

**verify**: 타입 에러 없음

### Step 3: OpsPanel 컴포넌트 생성

**파일**: `frontend/src/components/main/OpsPanel.tsx` (신규)

기존 데이터 활용:
- `useAccountStatus()` → broker, engine, credentials, is_mock
- cloud 상태 → TrafficLightStatus와 중복 폴링 방지를 위해 공유 hook(`useSystemHealth`) 도입 또는 TrafficLightStatus를 OpsPanel로 대체
- `localLogs.summary(today)` → 오늘 신호/체결/오류 수

**TrafficLightStatus 처리**: OpsPanel이 TrafficLightStatus의 역할을 흡수. 기존 TrafficLightStatus는 OpsPanel 내부에 통합하거나 제거.

레이아웃:
```
┌─────────────────────────────────────────────────┐
│ 🟢 로컬 연결됨  🟢 브로커 연결 (모의)  🟢 클라우드  🟢 엔진 실행 중 │
│ 신호 12건 · 체결 3건 · 오류 0건                         │
├─────────────────────────────────────────────────┤
│ ⚠️ 브로커 미연결 — 설정에서 API 키를 확인하세요 (비정상 시만) │
└─────────────────────────────────────────────────┘
```

**verify**: npm run build, 브라우저에서 4개 상태 + 요약 표시 확인

### Step 4: ListView에 OpsPanel 배치

**파일**: `frontend/src/components/main/ListView.tsx`

기존 계좌 요약 패널 위에 OpsPanel 삽입.
기존 ListView 내부의 engine 상태 표시 (녹색 점, "실행 중"/"정지" 라벨, 토글 버튼)와 broker 연결 상태 점은 OpsPanel이 대체하므로 제거.
계좌 잔고/평가액/손익 등 수치 정보는 유지.

**verify**: 메인 화면에서 OpsPanel + 계좌 수치 정보 자연스럽게 표시, 상태 중복 표시 없음

---

## Part B: 실행 로그 타임라인

### Step 5: 로그 meta에 intent_id/cycle_id 보장

**파일**: `local_server/engine/engine.py`, `local_server/routers/trading.py`

현재 로그 기록 경로 점검:
1. `engine.py` → `result_store.record_result()` — cycle_id, signal_id 포함 여부 확인
2. `trading.py` → `_on_execution()` → FILL 로그 — intent_id 포함 여부 확인

미포함 시 meta에 추가:
```python
log_db.write(
    log_type=LOG_TYPE_FILL,
    message=f"...",
    symbol=symbol,
    meta={
        "intent_id": result.intent_id,
        "cycle_id": result.cycle_id,
        "side": side,
        "qty": qty,
        "status": status,
        ...
    },
)
```

**verify**: 엔진 실행 후 로그 조회 시 meta에 intent_id/cycle_id 존재

### Step 6: ExecutionTimeline 컴포넌트 생성

**파일**: `frontend/src/components/main/ExecutionTimeline.tsx` (신규)

로그 데이터를 intent_id로 그룹핑하여 타임라인 카드 렌더링.
같은 intent_id가 없는 로그(기존 데이터, Step 5 이전 로그)는 개별 카드로 표시 (폴백).

타임라인 아이템:
```typescript
interface TimelineItem {
  intentId: string | null
  events: { ts: string; state: string; message: string }[]
  symbol: string
  side: string
  finalState: string  // FILLED, REJECTED, etc.
}
```

**verify**: 빌드 에러 없음, mock 데이터로 렌더링 확인

### Step 7: ExecutionLog 페이지에 뷰 토글 추가

**파일**: `frontend/src/pages/ExecutionLog.tsx`

테이블/타임라인 뷰 전환 토글 버튼 추가.
기존 테이블 뷰 유지, 타임라인 뷰는 ExecutionTimeline 컴포넌트 사용.

**verify**: 두 뷰 전환 동작, 각 뷰에서 데이터 정상 표시

### Step 8: DetailView에 종목별 타임라인 위젯 추가

**파일**: `frontend/src/components/main/DetailView.tsx`

해당 종목의 최근 실행 타임라인 5건을 간략 표시.
`localLogs.get({ log_type: 'FILL', symbol, limit: 5 })` 활용.

**verify**: 종목 상세에서 최근 실행 이벤트 표시

---

## 변경 파일 요약

| 파일 | 변경 | Step |
|------|------|------|
| `local_server/storage/log_db.py` | `date_from` 파라미터, `count_by_type` 메서드 추가 | 1 |
| `local_server/routers/logs.py` | `date_from` 쿼리, `/summary` 엔드포인트 추가 | 1 |
| `frontend/src/services/localClient.ts` | `localLogs.summary()` 추가 | 2 |
| `frontend/src/components/main/OpsPanel.tsx` | 신규 — 운영 요약 패널 | 3 |
| `frontend/src/components/main/ListView.tsx` | OpsPanel 삽입, 기존 상태 중복 정리 | 4 |
| `local_server/engine/engine.py` | 로그 meta에 intent_id/cycle_id 보장 | 5 |
| `local_server/routers/trading.py` | FILL 로그 meta 확인/보강 | 5 |
| `frontend/src/components/main/ExecutionTimeline.tsx` | 신규 — 타임라인 뷰 | 6 |
| `frontend/src/pages/ExecutionLog.tsx` | 뷰 토글 추가 | 7 |
| `frontend/src/components/main/DetailView.tsx` | 종목별 타임라인 위젯 | 8 |

## 검증 계획

1. `npm run build` — 프론트 빌드 에러 없음
2. 백엔드 서버 구동 → `/api/logs/summary` 응답 확인
3. 메인 화면에서 OpsPanel 4개 상태 표시 확인
4. 비정상 상태 시뮬레이션 (브로커 미연결) → 경고 배너 확인
5. ExecutionLog 페이지 → 테이블/타임라인 뷰 전환 확인
6. 종목 상세 → 최근 실행 타임라인 표시 확인
