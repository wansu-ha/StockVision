> 작성일: 2026-03-30 | 상태: 구현 완료

# v1 완성 — 구현 계획서

spec: `spec/v1-completion/spec.md`

## 아키텍처

```
┌────────────────────────────────────────────────────────┐
│ MainDashboard                                          │
│  ListView: 내 종목 | 관심 종목 | [전략] ← F4          │
│  전략 탭 → 규칙 목록 → 클릭 → 빌더 페이지 이동        │
└───────────────────────┬────────────────────────────────┘
                        │
    ┌───────────────────┼───────────────────────┐
    ▼                   ▼                       ▼
┌────────┐      ┌──────────────┐        ┌──────────────┐
│ F2     │      │ F1           │        │ F3           │
│ Sentry │      │ 비서 tool    │        │ 포지션 동기화 │
│ (cloud)│      │ + BYO 키     │        │ (엔진)       │
│        │      │ (cloud+front)│        │              │
└────────┘      └──────────────┘        └──────────────┘
                        │
        ┌───────────────┼──────────────┐
        ▼               ▼              ▼
   프론트 컨텍스트   Claude tool_use   BYO 키 라우팅
   (로컬 데이터)     (7개 tool)       (설정 UI)
```

## 수정 파일 목록

| 파일 | 변경 | Step |
|------|------|------|
| `cloud_server/main.py` | Sentry SDK 초기화 | F2 |
| `requirements.txt` | sentry-sdk 추가 | F2 |
| `frontend/src/components/main/ListView.tsx` | "전략" 탭 추가 | F4 |
| `frontend/src/pages/MainDashboard.tsx` | 탭 상태 `'strategy'` 추가 | F4 |
| `local_server/engine/engine.py` | `_sync_positions()` + 호출 3곳 | F3 |
| `local_server/config.py` | `position_sync.interval` 기본값 | F3 |
| `cloud_server/services/ai_chat_service.py` | assistant tool 정의 + 실행 핸들러 | F1 |
| `cloud_server/services/ai_tool_executor.py` | **신규** — tool 실행 로직 | F1 |
| `frontend/src/components/ai/AIChatPanel.tsx` | 로컬 데이터 컨텍스트 주입 | F1 |
| `frontend/src/pages/Settings.tsx` | "AI LLM 소스" 드롭다운 | F1 |

## 구현 순서

### Step 1: F2 — Sentry 에러 모니터링

가장 작고 독립적. 파일 2개.

**변경:**
- `requirements.txt` — `sentry-sdk[fastapi]` 추가
- `cloud_server/main.py` — lifespan 시작에 Sentry 초기화
  ```python
  import sentry_sdk
  dsn = os.getenv("SENTRY_DSN")
  if dsn:
      sentry_sdk.init(dsn=dsn, traces_sample_rate=0.1)
  ```

**verify:**
- `pip install -r requirements.txt` — 설치 성공
- DSN 없이 서버 시작 → Sentry 비활성, 에러 없음
- 기존 테스트 통과

---

### Step 2: F4 — 대시보드 전략 탭

F1 비서의 전제 (전략 접근 경로). 프론트 2파일.

**변경:**
- `MainDashboard.tsx`
  - 탭 상태 타입: `'my' | 'watch'` → `'my' | 'watch' | 'strategy'`
  - strategy 탭일 때 ListView 대신 전략 목록 렌더링
  - 규칙 데이터는 기존 `useStockData().rules`에서 이미 가져오고 있음

- `ListView.tsx`
  - 탭 버튼 3개: "내 종목 | 관심 종목 | 전략"
  - strategy 탭 선택 시 → 전체 규칙 목록 표시
  - 각 규칙: 종목명, DSL 요약(첫 줄), ON/OFF 토글, 실행 상태
  - 규칙 클릭 → `/strategies/{id}/edit` 페이지 이동 (모달은 추후)

**verify:**
- `cd frontend && npm run build` — 빌드 성공
- 브라우저: "내 종목 | 관심 종목 | 전략" 세 탭 전환
- 전략 탭에서 규칙 목록 표시 확인

---

### Step 3: F3 — 포지션 동기화

엔진 안전. 로컬 서버 2파일.

**변경:**
- `engine.py` — `_sync_positions()` 메서드 추가:
  ```python
  async def _sync_positions(self) -> None:
      if not self._broker or not self._broker.is_connected:
          return  # 브로커 미연결 시 스킵
      balance = await self._broker.get_balance()
      broker_positions = {p.symbol: p for p in balance.positions}
      # 엔진 등록 종목만 비교
      for symbol, ps in self._position_states.items():
          bp = broker_positions.get(symbol)
          if bp is None:
              # 잔고에 없음 → 전량 매도됨
              ps.record_sell(ps.total_qty)
          elif bp.qty != ps.total_qty or bp.avg_price != ps.entry_price:
              ps.total_qty = bp.qty
              ps.entry_price = bp.avg_price
              logger.debug("포지션 동기화: %s qty=%d price=%.0f", symbol, bp.qty, bp.avg_price)
  ```
- 호출 시점 3곳:
  1. `start()` 끝에 `await self._sync_positions()`
  2. `_on_fill()` (체결 콜백) 후 동기화
  3. `evaluate_all()` 시작에서 60초 경과 시 동기화
- `config.py` — `position_sync.interval` 기본값 60 추가

**verify:**
- `pytest local_server/tests/test_engine.py` — 기존 테스트 통과
- 수동: 엔진 시작 → 로그에 "포지션 동기화" 확인

---

### Step 4: F1-2 — BYO 키 빌더 연동

F1의 작은 부분. 설정 UI.

**변경:**
- `Settings.tsx` — "AI LLM 소스" 드롭다운 추가
  - 옵션: `플랫폼 (기본)` / `내 API 키`
  - BYO 키 미등록 시 "내 API 키" 비활성
  - 선택값 → 프론트 로컬 스토리지 또는 사용자 프로필에 저장
- `AIChatPanel.tsx` — 대화 요청 시 `use_byo_key: true/false` 파라미터 전달
- `ai_chat_service.py` — `use_byo_key` 파라미터에 따라 키 선택
  - 현재 이미 `get_byo_key()` → 플랫폼 키 폴백 로직 있음
  - builder 모드에서도 BYO 키 사용 가능하도록 조건 확장

**verify:**
- BYO 키 등록 → 설정에서 "내 API 키" 선택 → 빌더 대화 → 크레딧 미차감 확인
- 키 미등록 → "내 API 키" 비활성 확인

---

### Step 5: F1-1 — 비서 tool 확장

가장 큰 작업. 클라우드 + 프론트.

**변경:**

**5-1. tool 정의 (ai_chat_service.py)**
- assistant 모드일 때 `create_kwargs`에 `tools` 파라미터 추가
- 7개 tool 스키마 정의 (Claude tool_use 형식)

**5-2. tool 실행기 (ai_tool_executor.py 신규)**
- `execute_tool(tool_name, tool_input, user_id, context)` 함수
- 두 종류 tool 구분:
  - **클라우드 직접 호출**: `list_rules`, `get_rule`, `update_rule_dsl`, `get_backtest_result` → 내부 서비스/DB 직접 접근
  - **프론트 컨텍스트 기반**: `get_execution_logs`, `get_daily_pnl`, `get_positions` → 프론트가 주입한 `context` dict에서 읽기

**5-3. 대화 루프 확장 (ai_chat_service.py)**
- Claude 응답에 `tool_use` 블록 있으면:
  1. tool 실행
  2. tool 결과를 `tool_result` 메시지로 추가
  3. Claude에 재호출 (tool 결과 포함)
  4. 최종 텍스트 응답 스트리밍
- SSE 이벤트에 `tool_call`, `tool_result` 타입 추가

**5-4. 프론트 컨텍스트 주입 (AIChatPanel.tsx)**
- assistant 모드 대화 시작 시 로컬 데이터 수집:
  - `localLogs.summary()` → 오늘 신호/체결/오류
  - `localLogs.dailyPnl()` → 실현 P&L
  - `localHealth.check()` → 서버 상태
- 수집한 데이터를 `POST /api/v1/ai/chat` 요청에 `context` 필드로 첨부
- `ai_chat_service.py`에서 `context`를 시스템 메시지에 주입

**verify:**
- 비서에게 "전체 규칙 목록 보여줘" → list_rules tool → 규칙 목록 반환
- 비서에게 "삼성전자 규칙 수정해줘" → get_rule + update_rule_dsl tool
- 비서에게 "오늘 성과 요약해줘" → 컨텍스트 기반 답변
- `pytest cloud_server/tests/` — 기존 테스트 통과
- `cd frontend && npm run build` — 빌드 성공

---

## 검증 방법 (전체)

| 검증 | 명령 |
|------|------|
| Python 테스트 (cloud) | `pytest cloud_server/tests/ -v` |
| Python 테스트 (local) | `pytest local_server/tests/ -v` |
| Frontend 빌드 | `cd frontend && npm run build` |
| Frontend lint | `cd frontend && npm run lint` |
| 서버 기동 (cloud) | `python -m uvicorn cloud_server.main:app --port 4010` |
| 서버 기동 (local) | `python -m uvicorn local_server.main:app --port 4020` |
| 브라우저 | 대시보드 전략 탭 + 비서 대화 + 설정 AI 소스 |

## 커밋 계획

| # | 메시지 | 포함 파일 |
|---|--------|----------|
| 1 | `docs: v1-completion spec 확정 + plan` | spec.md, plan.md |
| 2 | `feat(cloud): Sentry 에러 모니터링` | main.py, requirements.txt |
| 3 | `feat(frontend): 대시보드 전략 탭` | ListView.tsx, MainDashboard.tsx |
| 4 | `feat(engine): 포지션 동기화 — 브로커 잔고 ↔ PositionState` | engine.py, config.py |
| 5 | `feat(settings): BYO API 키 빌더 연동` | Settings.tsx, AIChatPanel.tsx, ai_chat_service.py |
| 6 | `feat(ai): 비서 tool 확장 — 7개 tool + 컨텍스트 주입` | ai_chat_service.py, ai_tool_executor.py, AIChatPanel.tsx |
