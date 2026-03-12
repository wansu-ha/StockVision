# 실행 로그 타임라인 구현 계획

> 작성일: 2026-03-12 | 상태: 구현 완료 | Phase C (C3)

## 아키텍처

### 데이터 흐름

```
System Trader
  ├─ CandidateSignal 생성
  │  └─ Log: STRATEGY (규칙 조건 충족)
  │     └─ intent_id 생성 (UUID)
  │
  └─ TradeDecisionBatch 결과
     ├─ dropped 항목 (BlockReason)
     │  └─ Log: ERROR (차단 사유)
     │     └─ intent_id 전달
     │
     └─ selected 항목
        └─ OrderExecutor.execute()
           ├─ 검증 단계
           │  ├─ 중복 체크 (SignalManager)
           │  ├─ 한도 체크 (LimitChecker)
           │  ├─ 안전장치 (Safeguard)
           │  └─ 가격 검증 (PriceVerifier)
           │     └─ 각 단계마다 Log 기록 (intent_id 전달)
           │
           └─ place_order() → Broker
              └─ Log: ORDER (주문 제출)
              └─ Log: FILL (체결 확인)
              └─ intent_id 전달

LogDB (logs.db)
  └─ 저장: intent_id, ts, log_type, symbol, message, meta
     └─ 인덱스: idx_logs_intent (intent_id로 빠른 조회)

API: GET /api/logs/timeline
  └─ intent_id 기반 그룹핑
     └─ 같은 intent_id의 로그 모음 → TimelineEntry
        ├─ state 결정 (마지막 로그의 상태)
        ├─ steps 배열 (PROPOSED → READY → SUBMITTED → FILLED 시퀀스)
        └─ duration 계산 (started_at ~ ended_at)

Frontend: ExecutionLog.tsx (Timeline View)
  └─ TimelineEntry 배열 렌더링
     └─ TimelineCard
        ├─ 헤더: 종목, 규칙 이름, 최종 상태 (FILLED/BLOCKED/FAILED)
        ├─ 단계 시각화: 각 상태별 시간, 메시지, 아이콘
        ├─ 메타데이터: 슬리피지, 체결가, 실패 사유
        └─ 클릭 시: 상세 패널 (브로커 응답, 재시도 여부 등)
```

### 주요 설계 결정

1. **intent_id 선택**: UUID 기반 (signal_id 대신)
   - signal_id는 CandidateSignal 생성 단계(시스템매매 평가)에서만 존재
   - 차단된 후보(dropped)도 추적 필요 → intent_id는 PROPOSED 단계에서 생성
   - 로그 기록부터 intent_id 전달

2. **로그 타입 매핑**:
   - `STRATEGY`: 평가 결과 신호 (규칙 조건 충족, PROPOSED 상태)
   - `ORDER`: 주문 제출 (place_order 호출, SUBMITTED 상태)
   - `FILL`: 체결 확인 (broker response, FILLED 상태)
   - `ERROR`: 모든 실패/거부/차단 (BLOCKED, FAILED, REJECTED 상태)

3. **상태 정의**:
   - `PROPOSED`: 규칙 조건 충족 (STRATEGY 로그)
   - `READY`: 가격 검증 통과 (ORDER 로그)
   - `SUBMITTED`: 주문 제출 (ORDER 로그 후)
   - `FILLED`: 체결 완료 (FILL 로그)
   - `BLOCKED`: 포트폴리오 제약으로 거부 (ERROR 로그, BlockReason)
   - `FAILED`: 브로커 거부 또는 검증 실패 (ERROR 로그)
   - `CANCELLED`: 취소됨 (향후, 현재 미구현)

4. **API 응답 구조**:
   - 백엔드에서 intent_id 기반 그룹핑 수행 (프론트엔드 부담 줄임)
   - 각 TimelineEntry는 완결된 흐름 (started_at ~ ended_at)

---

## 수정 파일 목록

| 파일 | 변경 내용 | 우선순위 |
|------|----------|---------|
| `local_server/storage/log_db.py` | 스키마: `intent_id` 컬럼 추가 (NULLABLE)<br>메서드: `write()` 파라미터 `intent_id` 추가<br>메서드: `query()` → `query_by_intent_id()` 신규 | HIGH |
| `local_server/engine/system_trader.py` | intent_id 생성 (UUID)<br>dropped 항목 로깅 시 intent_id 전달 | HIGH |
| `local_server/engine/executor.py` | execute() 파라미터 `intent_id` 추가<br>각 검증 단계 로그에 intent_id 전달<br>place_order() 성공 시 intent_id 전달 | HIGH |
| `local_server/routers/logs.py` | `GET /api/logs/timeline` 엔드포인트 신규<br>intent_id 기반 그룹핑, TimelineEntry 반환 | HIGH |
| `frontend/src/pages/ExecutionLog.tsx` | 타임라인 뷰 로직 개선 (프롭 변경)<br>필터 추가 (symbol, rule_id, state) | MEDIUM |
| `frontend/src/components/main/ExecutionTimeline.tsx` | 기존 파일 구조 유지<br>TimelineCard 렌더링 로직 개선 | MEDIUM |
| `frontend/src/services/logs.ts` | API 클라이언트: getTimeline() 메서드 신규 | MEDIUM |
| `frontend/src/types/index.ts` | TypeScript 타입: TimelineEntry, TimelineStep 추가 | MEDIUM |

---

## 구현 순서

### Step 1: log_db.py 스키마 및 메서드 확장

**파일**: `local_server/storage/log_db.py`

**변경 사항**:

1. **스키마 마이그레이션**
   ```python
   _CREATE_TABLE_SQL = """
   CREATE TABLE IF NOT EXISTS logs (
       id        INTEGER PRIMARY KEY AUTOINCREMENT,
       ts        TEXT    NOT NULL,
       log_type  TEXT    NOT NULL,
       symbol    TEXT,
       message   TEXT    NOT NULL,
       meta      TEXT    DEFAULT '{}',
       intent_id TEXT                -- 추가: 주문 단위 그룹핑용
   );

   CREATE INDEX IF NOT EXISTS idx_logs_ts ON logs(ts);
   CREATE INDEX IF NOT EXISTS idx_logs_type ON logs(log_type);
   CREATE INDEX IF NOT EXISTS idx_logs_intent ON logs(intent_id);  -- 추가
   """
   ```

2. **write() 메서드 파라미터 추가**
   ```python
   def write(
       self,
       log_type: str,
       message: str,
       symbol: str | None = None,
       meta: dict[str, Any] | None = None,
       intent_id: str | None = None,  # 추가
   ) -> int:
       """..."""
       ts = datetime.now(timezone.utc).isoformat()
       meta_json = json.dumps(meta or {}, ensure_ascii=False)

       with sqlite3.connect(str(self._path)) as conn:
           cursor = conn.execute(
               "INSERT INTO logs (ts, log_type, symbol, message, meta, intent_id) VALUES (?, ?, ?, ?, ?, ?)",
               (ts, log_type, symbol, message, meta_json, intent_id),
           )
           return cursor.lastrowid
   ```

3. **신규 메서드**: query_by_intent_id()
   ```python
   def query_by_intent_id(self, intent_id: str) -> list[dict[str, Any]]:
       """intent_id로 모든 로그를 시간순 정렬로 조회한다."""
       with sqlite3.connect(str(self._path)) as conn:
           conn.row_factory = sqlite3.Row
           rows = conn.execute(
               "SELECT * FROM logs WHERE intent_id = ? ORDER BY ts ASC",
               (intent_id,),
           ).fetchall()

       return [
           {
               "id": row["id"],
               "ts": row["ts"],
               "log_type": row["log_type"],
               "symbol": row["symbol"],
               "message": row["message"],
               "meta": json.loads(row["meta"] or "{}"),
               "intent_id": row["intent_id"],
           }
           for row in rows
       ]
   ```

**검증 (Verify)**:
- [ ] 기존 로그 테이블이 있으면 ALTER TABLE로 컬럼 추가 (마이그레이션 스크립트 준비)
- [ ] `LogDB()` 인스턴스 생성 시 intent_id 컬럼이 존재하는지 확인
- [ ] write() 호출부 기존 호출 (intent_id=None)이 여전히 동작하는지 확인
- [ ] query_by_intent_id("test-uuid") 호출 시 해당 intent_id 로그만 반환되는지 테스트

---

### Step 2: system_trader.py 및 executor.py에서 intent_id 전달

**파일 1**: `local_server/engine/system_trader.py`

**변경 사항**:

1. **import 추가**
   ```python
   from uuid import uuid4
   from local_server.storage.log_db import get_log_db, LOG_TYPE_ERROR
   ```

2. **process_cycle() 메서드 수정**
   ```python
   def process_cycle(
       self,
       cycle_id: str,
       candidates: list[CandidateSignal],
       current_positions: set[str],
       cash: Decimal,
       today_executed: Decimal,
   ) -> TradeDecisionBatch:
       """..."""
       batch = TradeDecisionBatch(cycle_id=cycle_id)
       sorted_candidates = sorted(candidates, key=lambda c: c.priority, reverse=True)

       selected_buy_symbols: set[str] = set()
       added_positions = 0
       cycle_budget = today_executed
       max_daily = cash * self._budget_ratio

       for candidate in sorted_candidates:
           # intent_id 생성 (각 후보마다 고유)
           intent_id = str(uuid4())

           if candidate.side == "BUY":
               reason = self._check_buy(...)
               if reason is not None:
                   batch.dropped.append((candidate, reason))

                   # 차단된 후보 로깅
                   db = get_log_db()
                   db.write(
                       log_type=LOG_TYPE_ERROR,
                       symbol=candidate.symbol,
                       message=f"{reason.value}: {candidate.symbol} {candidate.side} 거부",
                       meta={"rule_id": candidate.rule_id, "block_reason": reason.value},
                       intent_id=intent_id,
                   )
                   continue

               batch.selected.append(candidate)
               # selected에도 intent_id 저장 (다음 단계 전달용)
               candidate.intent_id = intent_id  # CandidateSignal에 필드 추가 필요
               selected_buy_symbols.add(candidate.symbol)
               added_positions += 1
               cycle_budget += Decimal(str(candidate.latest_price)) * candidate.desired_qty

           elif candidate.side == "SELL":
               if candidate.symbol not in current_positions:
                   batch.dropped.append((candidate, BlockReason.SELL_NO_HOLDING))

                   db = get_log_db()
                   db.write(
                       log_type=LOG_TYPE_ERROR,
                       symbol=candidate.symbol,
                       message=f"SELL_NO_HOLDING: {candidate.symbol} 미보유 매도 거부",
                       meta={"rule_id": candidate.rule_id},
                       intent_id=intent_id,
                   )
                   continue

               batch.selected.append(candidate)
               candidate.intent_id = intent_id

       return batch
   ```

3. **CandidateSignal 필드 추가** (또는 TradeDecisionBatch.selected 항목에 intent_id 매핑 추가)
   ```python
   # trader_models.py
   @dataclass
   class CandidateSignal:
       signal_id: str
       cycle_id: str
       rule_id: int
       symbol: str
       side: str
       priority: int
       desired_qty: int
       detected_at: datetime
       latest_price: float
       reason: str
       raw_rule: dict[str, Any] = field(default_factory=dict)
       intent_id: str | None = None  # 추가: 로그 추적용
   ```

**파일 2**: `local_server/engine/executor.py`

**변경 사항**:

1. **execute() 메서드 파라미터 추가 + 로깅**
   ```python
   async def execute(
       self,
       rule: dict[str, Any],
       side: str,
       market_data: dict[str, Any],
       balance: BalanceResult,
       intent_id: str | None = None,  # 추가
   ) -> ExecutionResult:
       """..."""
       rule_id = int(rule.get("id", 0))
       symbol = str(rule.get("symbol", ""))

       # intent_id가 전달되지 않으면 생성 (하위 호환)
       if not intent_id:
           intent_id = str(uuid4())

       db = get_log_db()

       # 매도 보호 로깅
       if side == "SELL":
           holding = any(p.symbol == symbol for p in balance.positions)
           if not holding:
               db.write(
                   log_type=LOG_TYPE_ERROR,
                   symbol=symbol,
                   message="미보유 종목 매도 거부",
                   meta={"rule_id": rule_id},
                   intent_id=intent_id,
               )
               return ExecutionResult(...)

       # 각 검증 단계 로깅 (intent_id 전달)
       # 1. 중복 체크
       if not self._signal.can_trigger(rule_id, side):
           db.write(
               log_type=LOG_TYPE_ERROR,
               symbol=symbol,
               message=f"오늘 이미 실행된 규칙 ({side})",
               meta={"rule_id": rule_id},
               intent_id=intent_id,
           )
           return ExecutionResult(...)

       # 2. 한도 체크 (주요 로그만)
       ws_price = Decimal(str(market_data.get("price", 0)))
       order_amount = ws_price * qty

       if side == "BUY":
           budget_check = self._limit.check_budget(balance.cash, order_amount)
           if not budget_check.ok:
               db.write(
                   log_type=LOG_TYPE_ERROR,
                   symbol=symbol,
                   message=budget_check.reason,
                   meta={"rule_id": rule_id, "check": "budget"},
                   intent_id=intent_id,
               )
               return ExecutionResult(...)

           pos_check = self._limit.check_max_positions(len(balance.positions))
           if not pos_check.ok:
               db.write(
                   log_type=LOG_TYPE_ERROR,
                   symbol=symbol,
                   message=pos_check.reason,
                   meta={"rule_id": rule_id, "check": "max_positions"},
                   intent_id=intent_id,
               )
               return ExecutionResult(...)

       # 3. 안전장치 체크
       if not self._safeguard.is_trading_enabled():
           db.write(
               log_type=LOG_TYPE_ERROR,
               symbol=symbol,
               message="Trading Enabled = OFF",
               meta={"rule_id": rule_id},
               intent_id=intent_id,
           )
           return ExecutionResult(...)

       if not self._safeguard.check_order_speed():
           db.write(
               log_type=LOG_TYPE_ERROR,
               symbol=symbol,
               message="주문 속도 제한 초과",
               meta={"rule_id": rule_id},
               intent_id=intent_id,
           )
           return ExecutionResult(...)

       # 4. 가격 검증
       verify_result = await self._price.verify(symbol, ws_price)
       if not verify_result.ok:
           db.write(
               log_type=LOG_TYPE_ERROR,
               symbol=symbol,
               message=f"가격 검증 실패 (WS={ws_price}, REST={verify_result.actual_price})",
               meta={
                   "rule_id": rule_id,
                   "ws_price": float(ws_price),
                   "rest_price": float(verify_result.actual_price),
                   "diff_pct": float(verify_result.diff_pct),
               },
               intent_id=intent_id,
           )
           return ExecutionResult(...)

       # 5. 주문 제출 전 READY 상태 로깅
       db.write(
           log_type=LOG_TYPE_ORDER,
           symbol=symbol,
           message=f"주문 제출 대기 ({side} {qty}주, {order_type_str})",
           meta={"rule_id": rule_id, "qty": qty, "order_type": order_type_str},
           intent_id=intent_id,
       )

       # 6. 주문 실행
       self._signal.mark_triggered(rule_id, side)
       order_side = OrderSide.BUY if side == "BUY" else OrderSide.SELL
       order_type = OrderType.LIMIT if order_type_str == "LIMIT" else OrderType.MARKET
       limit_price = ...
       client_order_id = ...

       try:
           result = await self._broker.place_order(...)

           self._safeguard.increment_order_count()
           self._signal.mark_filled(rule_id, side, trigger_policy)
           self._limit.record_execution(order_amount)

           # SUBMITTED 상태 로깅
           db.write(
               log_type=LOG_TYPE_ORDER,
               symbol=symbol,
               message=f"주문 제출 완료 (order_id={result.order_id})",
               meta={
                   "rule_id": rule_id,
                   "order_id": result.order_id,
                   "qty": qty,
                   "price": float(ws_price),
               },
               intent_id=intent_id,
           )

           # 매도 시 실현손익
           pnl: Decimal | None = None
           if side == "SELL":
               pos = next((p for p in balance.positions if p.symbol == symbol), None)
               if pos and pos.avg_price:
                   pnl = (ws_price - pos.avg_price) * qty

           # FILL 상태 로깅
           db.write(
               log_type=LOG_TYPE_FILL,
               symbol=symbol,
               message=f"체결 완료 ({ws_price}원, {qty}주)",
               meta={
                   "rule_id": rule_id,
                   "order_id": result.order_id,
                   "fill_price": float(ws_price),
                   "qty": qty,
                   "realized_pnl": float(pnl) if pnl else None,
               },
               intent_id=intent_id,
           )

           return ExecutionResult(
               status=ExecutionStatus.SUCCESS,
               rule_id=rule_id, symbol=symbol, side=side,
               order_id=result.order_id,
               realized_pnl=pnl,
               cycle_id=None,
               signal_id=None,
           )

       except Exception as e:
           # 주문 실패 로깅
           db.write(
               log_type=LOG_TYPE_ERROR,
               symbol=symbol,
               message=f"주문 실패: {str(e)}",
               meta={"rule_id": rule_id, "error": str(e)},
               intent_id=intent_id,
           )
           logger.exception("주문 실행 오류")
           return ExecutionResult(
               status=ExecutionStatus.FAILED,
               rule_id=rule_id, symbol=symbol, side=side,
               message=str(e),
           )
   ```

2. **executor 호출부 수정** (engine 메인 루프에서 candidate.intent_id 전달)
   ```python
   # e.g., strategy_engine.py 또는 주문 실행 루프
   for candidate in selected_candidates:
       result = await executor.execute(
           rule=candidate.raw_rule,
           side=candidate.side,
           market_data=...,
           balance=...,
           intent_id=candidate.intent_id,  # 추가
       )
   ```

**검증 (Verify)**:
- [ ] system_trader.py 수정 후 dropped 항목 로깅 확인 (ERROR 로그 생성)
- [ ] CandidateSignal에 intent_id 필드 추가 후 컴파일 확인
- [ ] executor.py 수정 후 각 검증 단계 로깅 확인 (ORDER/ERROR 로그 생성)
- [ ] intent_id가 일관되게 전달되는지 로컬 서버 실행 후 logs.db 확인
- [ ] 기존 호출부 (intent_id=None)가 여전히 동작하는지 테스트

---

### Step 3: API 엔드포인트 GET /api/logs/timeline

**파일**: `local_server/routers/logs.py`

**변경 사항**:

1. **TypeScript 타입 정의 추가** (응답 형식 맞추기)
   ```python
   # TypeScript 형식으로 Python 데이터 클래스 정의
   from dataclasses import dataclass
   from typing import TypedDict

   class TimelineStep(TypedDict):
       state: str
       ts: str
       message: str
       meta: dict[str, Any]

   class TimelineEntry(TypedDict):
       intent_id: str
       rule_id: int
       rule_name: str
       symbol: str
       side: str
       state: str  # PROPOSED, READY, SUBMITTED, FILLED, BLOCKED, FAILED
       steps: list[TimelineStep]
       started_at: str
       ended_at: str | None
       duration_ms: int | None
   ```

2. **신규 라우트 추가**
   ```python
   @router.get(
       "/timeline",
       summary="타임라인 조회 (intent_id 기반 그룹핑)",
   )
   async def query_timeline(
       date_from: str = Query(
           ...,
           description="시작 날짜 필터 (YYYY-MM-DD, 필수)",
       ),
       limit: int = Query(50, ge=1, le=500, description="최대 타임라인 항목 수"),
       symbol: str | None = Query(None, description="종목 코드 필터"),
       rule_id: int | None = Query(None, description="규칙 ID 필터"),
       state: str | None = Query(None, description="최종 상태 필터 (FILLED, BLOCKED, FAILED)"),
       _: None = Depends(require_local_secret),
   ) -> dict[str, Any]:
       """intent_id 기반 타임라인 조회.

       같은 intent_id의 로그들을 하나의 TimelineEntry로 그룹핑.
       각 entry는 상태 전환 시퀀스를 포함한다.
       """
       db = get_log_db()

       # 1. intent_id 별 로그 조회
       all_logs, _ = db.query(date_from=date_from, limit=10000)  # 큰 범위로 조회

       # 2. intent_id 별 그룹핑
       intent_groups: dict[str, list[dict[str, Any]]] = {}
       for log in all_logs:
           intent_id = log.get("intent_id")
           if not intent_id:
               continue  # intent_id 없는 레거시 로그 스킵
           if intent_id not in intent_groups:
               intent_groups[intent_id] = []
           intent_groups[intent_id].append(log)

       # 3. TimelineEntry 변환
       timeline_entries: list[TimelineEntry] = []
       for intent_id, logs in intent_groups.items():
           # 시간순 정렬
           sorted_logs = sorted(logs, key=lambda x: x["ts"])

           # 상태 매핑
           def log_type_to_state(log_type: str, meta: dict) -> str:
               if log_type == "STRATEGY":
                   return "PROPOSED"
               elif log_type == "ORDER":
                   return "SUBMITTED"  # ORDER 로그 = SUBMITTED 상태
               elif log_type == "FILL":
                   return "FILLED"
               elif log_type == "ERROR":
                   reason = meta.get("block_reason", "")
                   if reason in ("DUPLICATE_SYMBOL", "MAX_POSITIONS", "DAILY_BUDGET_EXCEEDED", "SELL_NO_HOLDING"):
                       return "BLOCKED"
                   else:
                       return "FAILED"
               return "UNKNOWN"

           # steps 배열 구성
           steps: list[TimelineStep] = []
           final_state = "PROPOSED"
           rule_id = None
           rule_name = ""
           symbol = ""
           side = ""

           for log in sorted_logs:
               state = log_type_to_state(log["log_type"], log.get("meta", {}))
               steps.append({
                   "state": state,
                   "ts": log["ts"],
                   "message": log["message"],
                   "meta": log.get("meta", {}),
               })
               final_state = state

               # 메타데이터 추출
               if not rule_id:
                   rule_id = log.get("meta", {}).get("rule_id")
               if not symbol:
                   symbol = log.get("symbol", "")
               # side는 PROPOSED 로그의 메시지에서 파싱 또는 메타에서
               if not side and log["log_type"] == "ORDER":
                   # "주문 제출 대기 (BUY 10주, MARKET)" 형식에서 파싱
                   msg = log["message"]
                   if "BUY" in msg:
                       side = "BUY"
                   elif "SELL" in msg:
                       side = "SELL"

           # 필터 적용
           if symbol and log.get("symbol") != symbol:
               continue
           if rule_id and rule_id != rule_id:
               continue
           if state and final_state != state:
               continue

           # 소요 시간 계산
           started_at = sorted_logs[0]["ts"]
           ended_at = sorted_logs[-1]["ts"] if final_state in ("FILLED", "BLOCKED", "FAILED") else None
           duration_ms = None
           if ended_at:
               try:
                   start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                   end = datetime.fromisoformat(ended_at.replace("Z", "+00:00"))
                   duration_ms = int((end - start).total_seconds() * 1000)
               except:
                   pass

           timeline_entries.append({
               "intent_id": intent_id,
               "rule_id": rule_id or 0,
               "rule_name": rule_name,  # 향후: cloud_server에서 조회
               "symbol": symbol,
               "side": side or "BUY",
               "state": final_state,
               "steps": steps,
               "started_at": started_at,
               "ended_at": ended_at,
               "duration_ms": duration_ms,
           })

       # 4. 최신순 정렬 + limit
       timeline_entries.sort(key=lambda x: x["started_at"], reverse=True)
       timeline_entries = timeline_entries[:limit]

       return {
           "success": True,
           "data": {
               "items": timeline_entries,
               "total": len(timeline_entries),
           },
           "count": len(timeline_entries),
       }
   ```

**검증 (Verify)**:
- [ ] 로컬 서버 실행: `python -m uvicorn local_server.main:app --port 4020`
- [ ] curl 또는 Postman에서 `GET http://localhost:4020/api/logs/timeline?date_from=2026-03-12&local_secret=<SECRET>`
- [ ] 응답이 `{"success": true, "data": {"items": [...], "total": N}, "count": N}` 형식인지 확인
- [ ] intent_id 기반 그룹핑이 제대로 되는지 (같은 intent_id 로그가 하나의 entry로 묶였는지)
- [ ] 필터 (symbol, rule_id, state)가 정상 작동하는지 확인

---

### Step 4: 프론트엔드 타임라인 UI 컴포넌트 개선

**파일 1**: `frontend/src/services/logs.ts`

**변경 사항**:

```typescript
// 신규 메서드 추가
export const logsApi = {
  // 기존 메서드들...
  getLogs: async (filters: LogFilters) => { ... },
  getSummary: async () => { ... },

  // 신규: 타임라인 조회
  getTimeline: async (filters: {
    date_from: string
    limit?: number
    symbol?: string
    rule_id?: number
    state?: string
  }) => {
    const params = new URLSearchParams()
    params.append('date_from', filters.date_from)
    if (filters.limit) params.append('limit', String(filters.limit))
    if (filters.symbol) params.append('symbol', filters.symbol)
    if (filters.rule_id) params.append('rule_id', String(filters.rule_id))
    if (filters.state) params.append('state', filters.state)
    params.append('local_secret', localStorage.getItem('local_secret') || '')

    const response = await fetch(
      `${LOCAL_SERVER_URL}/api/logs/timeline?${params}`,
      { headers: { 'Content-Type': 'application/json' } }
    )
    if (!response.ok) throw new Error('Timeline API failed')
    return response.json()
  },
}
```

**파일 2**: `frontend/src/types/index.ts`

**변경 사항**:

```typescript
// 타임라인 관련 타입 추가
export interface TimelineStep {
  state: string
  ts: string
  message: string
  meta?: Record<string, any>
}

export interface TimelineEntry {
  intent_id: string
  rule_id: number
  rule_name: string
  symbol: string
  side: 'BUY' | 'SELL'
  state: 'PROPOSED' | 'READY' | 'SUBMITTED' | 'FILLED' | 'BLOCKED' | 'FAILED' | 'CANCELLED'
  steps: TimelineStep[]
  started_at: string
  ended_at: string | null
  duration_ms: number | null
}
```

**파일 3**: `frontend/src/pages/ExecutionLog.tsx`

**변경 사항** (기존 코드 유지, 타임라인 뷰 전달 프롭 개선):

```typescript
export default function ExecutionLog() {
  const [dateFrom, setDateFrom] = useState('')
  const [viewMode, setViewMode] = useState<'table' | 'timeline'>('table')
  const [symbolFilter, setSymbolFilter] = useState<string | undefined>()
  const [ruleIdFilter, setRuleIdFilter] = useState<number | undefined>()
  const [stateFilter, setStateFilter] = useState<string | undefined>()

  const { data, isLoading, error } = useQuery({
    queryKey: ['execution-logs', dateFrom],
    queryFn: () => logsApi.getLogs({
      date_from: dateFrom || undefined,
      limit: 200,
    }),
    refetchInterval: 10_000,
  })

  const { data: summaryData } = useQuery({
    queryKey: ['log-summary'],
    queryFn: () => logsApi.getSummary(),
    refetchInterval: 10_000,
  })

  // 타임라인 데이터 (별도 쿼리)
  const { data: timelineData, isLoading: timelineLoading } = useQuery({
    queryKey: ['execution-timeline', dateFrom, symbolFilter, ruleIdFilter, stateFilter],
    queryFn: () => logsApi.getTimeline({
      date_from: dateFrom || new Date().toISOString().split('T')[0],
      limit: 50,
      symbol: symbolFilter,
      rule_id: ruleIdFilter,
      state: stateFilter,
    }),
    enabled: viewMode === 'timeline' && !!dateFrom,  // 타임라인 뷰 활성 시만 조회
    refetchInterval: 10_000,
  })

  const logs: LogEntry[] = data?.data?.items ?? []
  const timeline: TimelineEntry[] = timelineData?.data?.items ?? []
  const sum = summaryData?.data

  return (
    <div className="max-w-6xl mx-auto p-4 sm:p-6">
      <h1 className="text-xl font-bold text-gray-100 mb-4">실행 로그</h1>

      {/* 요약 */}
      {sum && (
        <div className="grid grid-cols-4 gap-3 mb-5">
          {[
            { label: '신호', value: sum.signals, color: 'text-purple-400' },
            { label: '체결', value: sum.fills, color: 'text-green-400' },
            { label: '주문', value: sum.orders, color: 'text-blue-400' },
            { label: '오류', value: sum.errors, color: sum.errors > 0 ? 'text-red-400' : 'text-gray-500' },
          ].map(s => (
            <div key={s.label} className="bg-gray-900 border border-gray-800 rounded-lg p-3 text-center">
              <div className={`text-xl font-bold ${s.color}`}>{s.value}</div>
              <div className="text-xs text-gray-500 mt-1">{s.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* 필터 + 뷰 토글 */}
      <div className="flex items-end justify-between gap-3 mb-4">
        <div className="flex gap-3">
          <div>
            <label className="block text-xs text-gray-500 mb-1">시작일</label>
            <input
              type="date"
              value={dateFrom}
              onChange={e => setDateFrom(e.target.value)}
              className="bg-gray-900 border border-gray-700 rounded px-2 py-1 text-sm text-gray-300"
            />
          </div>
          {dateFrom && (
            <button
              onClick={() => setDateFrom('')}
              className="self-end text-sm text-gray-500 hover:text-gray-300"
            >
              초기화
            </button>
          )}

          {/* 타임라인 뷰 전용 필터 */}
          {viewMode === 'timeline' && (
            <>
              <div>
                <label className="block text-xs text-gray-500 mb-1">종목</label>
                <input
                  type="text"
                  placeholder="종목 코드"
                  value={symbolFilter || ''}
                  onChange={e => setSymbolFilter(e.target.value || undefined)}
                  className="bg-gray-900 border border-gray-700 rounded px-2 py-1 text-sm text-gray-300"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500 mb-1">상태</label>
                <select
                  value={stateFilter || ''}
                  onChange={e => setStateFilter(e.target.value || undefined)}
                  className="bg-gray-900 border border-gray-700 rounded px-2 py-1 text-sm text-gray-300"
                >
                  <option value="">전체</option>
                  <option value="FILLED">체결</option>
                  <option value="BLOCKED">차단</option>
                  <option value="FAILED">실패</option>
                </select>
              </div>
            </>
          )}
        </div>

        {/* 뷰 토글 */}
        <div className="flex bg-gray-900 border border-gray-700 rounded-lg overflow-hidden">
          <button
            onClick={() => setViewMode('table')}
            className={`px-3 py-1.5 text-xs ${viewMode === 'table' ? 'bg-gray-700 text-gray-200' : 'text-gray-500 hover:text-gray-300'}`}
          >
            테이블
          </button>
          <button
            onClick={() => setViewMode('timeline')}
            className={`px-3 py-1.5 text-xs ${viewMode === 'timeline' ? 'bg-gray-700 text-gray-200' : 'text-gray-500 hover:text-gray-300'}`}
          >
            타임라인
          </button>
        </div>
      </div>

      {/* 뷰 */}
      {viewMode === 'timeline' ? (
        <ExecutionTimeline
          items={timeline}
          isLoading={timelineLoading}
          error={!!error}
        />
      ) : (
        // 기존 테이블 뷰...
      )}
    </div>
  )
}
```

**파일 4**: `frontend/src/components/main/ExecutionTimeline.tsx`

**변경 사항** (기존 구조 유지, TimelineEntry 대응):

```typescript
import { useState } from 'react'
import type { TimelineEntry } from '../../types'

interface StateIconProps {
  state: string
}

function StateIcon({ state }: StateIconProps) {
  switch (state) {
    case 'PROPOSED':
    case 'READY':
      return <div className="w-2 h-2 rounded-full bg-gray-500" />
    case 'SUBMITTED':
      return <div className="w-2 h-2 rounded-full bg-blue-500" />
    case 'FILLED':
      return <div className="w-2 h-2 rounded-full bg-green-500 fill-green-500" />
    case 'BLOCKED':
    case 'FAILED':
      return <div className="w-2 h-2 rounded-full bg-red-500" />
    default:
      return <div className="w-2 h-2 rounded-full bg-gray-400" />
  }
}

function StateLabel({ state }: { state: string }) {
  const labels: Record<string, string> = {
    PROPOSED: '제안',
    READY: '준비',
    SUBMITTED: '제출',
    FILLED: '체결',
    BLOCKED: '차단',
    FAILED: '실패',
    CANCELLED: '취소',
  }
  return <span>{labels[state] || state}</span>
}

interface TimelineCardProps {
  entry: TimelineEntry
  onExpand?: (entry: TimelineEntry) => void
}

function TimelineCard({ entry, onExpand }: TimelineCardProps) {
  const [expanded, setExpanded] = useState(false)

  const statusColor = {
    FILLED: 'border-green-900 bg-green-900/10',
    BLOCKED: 'border-red-900 bg-red-900/10',
    FAILED: 'border-red-900 bg-red-900/10',
  }[entry.state] || 'border-gray-800 bg-gray-900/50'

  return (
    <div className={`border rounded-lg p-4 mb-3 cursor-pointer hover:bg-gray-800/20 transition ${statusColor}`}>
      <div onClick={() => setExpanded(!expanded)} className="flex items-center justify-between">
        <div className="flex items-center gap-3 flex-1">
          <StateIcon state={entry.state} />
          <div>
            <div className="font-medium text-gray-200">
              {entry.symbol} {entry.side} {entry.steps[0]?.message || ''}
            </div>
            <div className="text-xs text-gray-500 mt-1">{entry.rule_name || `규칙 #${entry.rule_id}`}</div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-400">{entry.duration_ms ? `${entry.duration_ms}ms` : '—'}</span>
          <span className={`px-2 py-1 rounded text-xs font-medium ${
            entry.state === 'FILLED' ? 'bg-green-900/50 text-green-400' :
            entry.state === 'BLOCKED' ? 'bg-yellow-900/50 text-yellow-400' :
            entry.state === 'FAILED' ? 'bg-red-900/50 text-red-400' :
            'bg-gray-800 text-gray-400'
          }`}>
            <StateLabel state={entry.state} />
          </span>
        </div>
      </div>

      {/* 확장 상세 정보 */}
      {expanded && (
        <div className="mt-4 pt-4 border-t border-gray-700/50">
          <div className="space-y-2">
            {entry.steps.map((step, idx) => (
              <div key={idx} className="flex gap-2 text-xs">
                <div className="text-gray-500 w-24">{new Date(step.ts).toLocaleTimeString('ko-KR')}</div>
                <div className="flex items-center gap-2 flex-1">
                  <StateIcon state={step.state} />
                  <div>
                    <div className="text-gray-400">{step.message}</div>
                    {Object.keys(step.meta || {}).length > 0 && (
                      <div className="text-gray-600 mt-1">
                        {Object.entries(step.meta || {})
                          .filter(([_, v]) => v !== null && v !== undefined)
                          .map(([k, v]) => `${k}=${v}`)
                          .join(' | ')}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* 슬리피지 계산 */}
          {entry.state === 'FILLED' && (
            <div className="mt-3 p-2 bg-gray-800/50 rounded text-xs text-gray-400">
              {/* 슬리피지 계산은 meta에서 추출 */}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

interface ExecutionTimelineProps {
  items: TimelineEntry[]
  isLoading: boolean
  error: boolean
}

export default function ExecutionTimeline({ items, isLoading, error }: ExecutionTimelineProps) {
  if (isLoading) {
    return <div className="p-8 text-center text-gray-500">로딩 중...</div>
  }

  if (error) {
    return <div className="p-8 text-center text-red-500">로컬 서버 연결 실패</div>
  }

  if (items.length === 0) {
    return <div className="p-8 text-center text-gray-500">타임라인 기록이 없습니다.</div>
  }

  return (
    <div className="space-y-2">
      {items.map(entry => (
        <TimelineCard key={entry.intent_id} entry={entry} />
      ))}
    </div>
  )
}
```

**검증 (Verify)**:
- [ ] 프론트엔드 빌드: `npm run build` (타입 에러 없는지 확인)
- [ ] 개발 서버 실행: `npm run dev`
- [ ] ExecutionLog 페이지 접속 후 "타임라인" 탭 클릭
- [ ] 시작일 입력 후 타임라인 카드 로드 확인
- [ ] 각 카드의 상태, 단계, 소요 시간이 정상 표시되는지 확인
- [ ] 카드 클릭 시 단계별 상세 정보 표시 확인

---

### Step 5: 통합 테스트 및 버그 수정

**검증 항목**:

1. **데이터 흐름 E2E**:
   - [ ] 로컬 서버 실행 + 엔진 사이클 1회 실행
   - [ ] logs.db 확인: intent_id가 기록되었는지
   - [ ] GET /api/logs/timeline 호출: 타임라인 entry 반환되는지

2. **마이그레이션 검증**:
   - [ ] 기존 logs.db 파일이 있을 경우 ALTER TABLE 수행 확인
   - [ ] intent_id = NULL 기존 로그는 timeline에서 필터링되는지

3. **프론트엔드 UI**:
   - [ ] 타임라인 카드 렌더링
   - [ ] 상태별 색상 구분 (FILLED/BLOCKED/FAILED)
   - [ ] 단계별 시간 표시
   - [ ] 필터 (종목, 상태) 작동

4. **에러 처리**:
   - [ ] 로컬 서버 연결 실패 시 프론트엔드 에러 메시지 표시
   - [ ] 잘못된 date_from 형식 → API 에러 응답 처리

---

## 검증 방법

### 로컬 서버 검증

```bash
# 1. 로컬 서버 실행
cd d:/Projects/StockVision
python -m uvicorn local_server.main:app --port 4020 --reload

# 2. logs.db 마이그레이션 확인
sqlite3 ~/.stockvision/logs.db
sqlite> PRAGMA table_info(logs);
# intent_id 컬럼이 있는지 확인

# 3. API 호출
curl -X GET "http://localhost:4020/api/logs/timeline?date_from=2026-03-12&local_secret=<SECRET>" \
  -H "Content-Type: application/json"

# 4. 응답 검증
# - success: true
# - data.items: TimelineEntry 배열
# - 각 entry에 intent_id, steps, state, duration_ms 포함
```

### 프론트엔드 검증

```bash
# 1. 빌드
cd frontend
npm run build
# 타입 에러 없음 확인

# 2. 개발 서버
npm run dev

# 3. 브라우저에서 http://localhost:5173
# - ExecutionLog 페이지
# - "타임라인" 탭 선택
# - 시작일 입력
# - 타임라인 카드 로드 확인

# 4. UI 확인 항목
# - 카드 헤더: 종목, 규칙 이름, 최종 상태
# - 단계 목록: 시간, 상태, 메시지
# - 색상: FILLED(초록), BLOCKED(빨강), FAILED(빨강)
# - 클릭 시 세부 정보 토글
```

### 수용 기준 체크리스트

- [ ] 로그에 `intent_id`가 기록되어 주문 단위 그룹핑이 가능하다
- [ ] 타임라인 뷰에서 각 주문의 상태 전환 단계가 시각적으로 표시된다
- [ ] 실패/차단된 주문의 사유가 명확히 표시된다
- [ ] 각 단계의 소요 시간이 표시된다
- [ ] 체결 항목에서 슬리피지가 계산되어 표시된다
- [ ] 체결 여부와 주문 제출 여부를 혼동하지 않는다 (UX PRD 수용 기준)

---

## 주요 변경 사항 요약

| 컴포넌트 | 변경 | 파일 수 |
|----------|------|--------|
| **Backend (local_server)** | intent_id 추가, 그룹핑 로직 | 4개 |
| **Frontend** | 타임라인 뷰, API 클라이언트, 타입 | 4개 |
| **총 변경 파일** | | 8개 |

**예상 소요 시간**: 4-6 시간 (Step 1-5 순차 구현)
