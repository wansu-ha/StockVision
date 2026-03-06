# 실행 로그 구현 계획서 (execution-log)

> 작성일: 2026-03-04 | 상태: **→ Unit 5 (frontend) plan에 통합**

---

## 0. 전제 조건

- 로컬 서버 logs.db (SQLite) 기반
- 의존: `spec/execution-engine/plan.md` (실행 엔진이 로그 기록)
- 클라우드 서버에 로그 전송 없음 (개인정보 최소화)

---

## 1. 구현 단계

### Step 1 — logs.db 스키마 + 기록 레이어

파일: `local_server/storage/log_db.py`

```python
# logs.db 스키마
CREATE TABLE execution_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id     INTEGER NOT NULL,
    rule_name   TEXT,
    symbol      TEXT NOT NULL,
    side        TEXT NOT NULL,       -- "BUY" | "SELL"
    qty         INTEGER NOT NULL,
    order_no    TEXT,
    filled_price REAL,
    filled_qty  INTEGER,
    status      TEXT NOT NULL,       -- "SENT" | "FILLED" | "FAILED" | "SKIPPED"
    condition_snapshot TEXT,         -- JSON: 평가 시점 조건 값들
    error_msg   TEXT,
    created_at  TEXT NOT NULL        -- ISO 8601
);

class LogDB:
    def log_execution(self, rule_id, rule_name, symbol, side, qty,
                      order_no, status, condition_snapshot=None, error_msg=None):
        ...

    def log_fill(self, order_no, filled_price, filled_qty):
        """체결 콜백에서 업데이트"""
        ...

    def query_logs(self, rule_id=None, date_from=None, date_to=None,
                   limit=100, offset=0) -> list[dict]:
        ...
```

**검증:**
- [ ] 실행 시 로그 INSERT
- [ ] 체결 시 filled_price, filled_qty 업데이트
- [ ] 날짜 범위 필터 조회 정상 동작

### Step 2 — 조회 REST API

파일: `local_server/routers/logs.py` (또는 `health.py` 확장)

```
GET /api/logs
  Query: rule_id?, date_from?, date_to?, limit=100, offset=0
  → 200 { success: true, data: [...], count: N }

GET /api/logs/summary
  → 오늘 실행 수, 체결 수, 오류 수 요약
```

**검증:**
- [ ] `GET /api/logs` 기본 조회 (최근 100건)
- [ ] `rule_id` 필터 정상 동작
- [ ] `GET /api/logs/summary` 오늘 통계 반환

### Step 3 — React 실행 로그 UI

파일: `frontend/src/pages/ExecutionLog.tsx` 또는 `Dashboard.tsx` 탭

```
실행 로그 페이지:
┌─────────────────────────────────────────────────────┐
│ 실행 로그                              [날짜 범위 선택] │
├─────────────────────────────────────────────────────┤
│ 시각       규칙명         종목    수량  상태  체결가  │
│ 10:30:15  RSI 매수 전략  삼성전자  10   체결  72,500 │
│ 11:05:00  RSI 매수 전략  삼성전자  10   스킵  —      │
│ 14:00:30  EMA 매도 전략  삼성전자   5   오류  —      │
└─────────────────────────────────────────────────────┘
│ 조건 스냅샷: RSI=28.3, EMA_5=71800, EMA_20=70200  [접기] │
```

- 상태별 색상: 체결(green), 스킵(gray), 오류(red)
- 조건 스냅샷 토글 (어떤 조건값으로 실행됐는지)
- 실시간 갱신: 10초 폴링 (또는 WS push)

**검증:**
- [ ] 로그 테이블 렌더링
- [ ] 조건 스냅샷 토글
- [ ] 날짜 필터 적용
- [ ] WS `execution_result` 이벤트 → 즉시 목록 갱신

---

## 2. 파일 목록

| 파일 | 내용 |
|------|------|
| `local_server/storage/log_db.py` | logs.db 스키마 + CRUD |
| `local_server/routers/logs.py` | `GET /api/logs`, `GET /api/logs/summary` |
| `frontend/src/pages/ExecutionLog.tsx` | 실행 로그 UI |
| `frontend/src/services/logs.ts` | API 클라이언트 |

---

## 3. 커밋 계획

| 커밋 | 메시지 |
|------|--------|
| 1 | `feat: Step 1 — logs.db 스키마 + LogDB CRUD` |
| 2 | `feat: Step 2 — 실행 로그 조회 API` |
| 3 | `feat: Step 3 — React 실행 로그 UI` |
