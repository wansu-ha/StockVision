# local_server 코드 리뷰

> 작성일: 2026-03-13 | 대상: local_server/ 전체

---

## 요약

| 분류 | 건수 |
|------|------|
| Critical | 5 |
| High | 9 |
| Medium | 7 |
| 미완성 기능 | 5 |

전반적으로 구조는 견고하다. 핵심 문제는 (1) 트레이 Kill Switch가 엔진에 실제 명령을 보내지 않고 상태 변수만 수정한다는 보안/안전 버그, (2) 인증 없이 호출 가능한 경고 설정 엔드포인트, (3) LogDB의 동기 SQLite 연결이 asyncio 루프를 블로킹할 수 있는 구조 문제, (4) 재연결 성공 후 WS 시세 재구독이 이루어지지 않아 엔진이 시세 없이 동작하는 문제이다.

---

## Critical

### C1: 트레이 Kill Switch가 실제 엔진에 명령을 전달하지 않는다

**파일**: `local_server/tray/tray_app.py` — `_on_kill_switch()` (L135-146)

`set_engine_running(False)`는 하트비트 페이로드의 `engine_running` 플래그를 바꿀 뿐이다. `engine.safeguard.set_kill_switch()`는 전혀 호출되지 않는다. 트레이에서 "긴급 정지"를 누르더라도 실제 주문은 계속 나간다.

- **심각도**: Critical
- **신뢰도**: 100%

### C2: POST /api/settings/alerts — 인증 없이 경고 설정 변경 가능

**파일**: `local_server/routers/alerts.py` — `update_alert_settings()` (L31-69)

`Depends(require_local_secret)`가 없다. `master_enabled`를 `false`로 바꾸거나 임계값을 극단적으로 조정하는 것이 인증 없이 가능하다.

- **심각도**: Critical
- **신뢰도**: 100%

### C3: 재연결 후 WS 시세 재구독 없음 → 엔진이 빈 시세로 동작

**파일**: `local_server/broker/kis/reconnect.py` — `_reconnect_loop()` (L85-119)

`ReconnectManager._reconnect_loop()`는 인증과 WS 연결을 복원하지만 `subscribe_quotes()`를 다시 호출하지 않는다. 재연결 후 엔진은 평가는 돌지만 시세가 없어 아무 주문도 내지 않는다.

- **심각도**: Critical
- **신뢰도**: 95%

### C4: LogDB.write()가 asyncio 루프를 블로킹한다

**파일**: `local_server/storage/log_db.py` — `write()` (L66-94)

동기 함수이며 직접 `sqlite3.connect()`를 호출한다. 엔진 평가 루프 내부에서 매 사이클 반복 호출되어 asyncio 이벤트 루프가 블로킹된다.

- **심각도**: Critical
- **신뢰도**: 90%

### C5: WS 인증 — `sec` query param이 URL 로그에 노출

**파일**: `local_server/routers/ws.py` — `websocket_endpoint()` (L101)

`local_secret`이 URL query string으로 전달된다. 브라우저 History API, 서버 로그에 평문으로 기록된다.

- **심각도**: Critical (보안)
- **신뢰도**: 85%

---

## High

### H1: POST /api/auth/token — 인증 없이 cloud token 교체 가능

**파일**: `local_server/routers/auth.py` — `register_cloud_token()` (L43-86)

`Depends(require_local_secret)` 없음. 이 엔드포인트에 임의 JWT를 POST하면 `local_secret`을 획득하고 이후 모든 보호 엔드포인트를 호출할 수 있다.

- **심각도**: High
- **신뢰도**: 85%

### H2: KIS WebSocket approval_key — access_token 그대로 사용

**파일**: `local_server/broker/kis/ws.py` — `_get_approval_key()` (L146-152)

KIS WebSocket은 별도 `/oauth2/Approval` 엔드포인트에서 발급받은 접속키가 필요하다. 실거래 시 WS 시세가 전혀 수신되지 않는다.

- **심각도**: High
- **신뢰도**: 95%

### H3: KIS order.py — 매도 시장가 TR ID가 잘못될 수 있음

**파일**: `local_server/broker/kis/order.py` — `place_order()` (L112)

KIS 실전 API에서 매도 시장가의 올바른 `tr_id`는 `TTTC0801U`가 아니라 `TTTC0802U`이다. 실거래에서 주문 거부나 잘못된 방향의 주문이 나갈 위험이 있다.

- **심각도**: High
- **신뢰도**: 85%

### H4: LimitChecker.today_executed — 재시작 시 0으로 리셋됨

**파일**: `local_server/engine/limit_checker.py` — L29

당일 누적 거래금액이 인메모리에만 유지. 장중 재시작 시 동일 규칙이 중복 실행되고 예산이 초과될 수 있다.

- **심각도**: High
- **신뢰도**: 90%

### H5: config.py — Config 인스턴스가 스레드 안전하지 않음

**파일**: `local_server/config.py`

트레이 스레드와 asyncio 루프에서 동시에 `save()` 호출 가능. 파일이 부분 기록된 상태로 남을 수 있다.

- **심각도**: High
- **신뢰도**: 82%

### H6: HealthWatchdog — get_balance() 호출이 API rate limit에 산입

**파일**: `local_server/engine/health_watchdog.py` — `_check_broker_health()` (L127-149)

브로커 ping으로 30초마다 `get_balance()` 호출. 엔진 평가 루프에서도 동일 API를 호출하므로 rate limit 초과 위험.

- **심각도**: High
- **신뢰도**: 82%

### H7: Watchdog에 엔진 참조가 주입되지 않음

**파일**: `local_server/main.py`, `local_server/routers/trading.py`

`watchdog.set_engine(engine)` 호출이 없다. `_check_engine_heartbeat()`의 `self._engine`은 항상 None이며 엔진 하트비트 체크가 동작하지 않는다.

- **심각도**: High
- **신뢰도**: 88%

### H8: cloud/context.py — 동기 httpx 호출

**파일**: `local_server/cloud/context.py` — `fetch_and_cache()` (L27-43)

동기 blocking 호출 + `_CLOUD_URL` 하드코딩 기본값. 이중 캐시(`_mem_cache` vs `engine.ContextCache`) 동기화 안 됨.

- **심각도**: High
- **신뢰도**: 80%

### H9: FILL 로그가 주문 제출 즉시 기록됨 (실제 체결 아님)

**파일**: `local_server/engine/executor.py` — L232-237

`place_order()`가 `OrderStatus.SUBMITTED`를 반환하는 즉시 `LOG_TYPE_FILL`을 기록. 미체결 주문도 당일 실현손익에 포함되어 손실 제한 계산이 부정확하다.

- **심각도**: High
- **신뢰도**: 95%

---

## Medium

### M1: WS 릴레이 heartbeat_ack 버전 처리 안 됨
`local_server/cloud/ws_relay_client.py` L189-193. WS 연결 상태에서는 규칙/컨텍스트 자동 갱신이 동작하지 않는다.

### M2: 15:30 이후 스케줄러/엔진 이중 체크
`local_server/engine/engine.py` L179-182. 기능 문제는 없지만 단일 진실 원천 위반.

### M3: IndicatorProvider — KOSDAQ 종목 .KS 오분류
`local_server/engine/indicator_provider.py` L90-98. KOSDAQ 종목에 `.KS` 대신 `.KQ`를 써야 함.

### M4: devices/pair/init — 인증 없이 E2E 키 생성
`local_server/routers/devices.py` L24-42. `require_local_secret` 없음.

### M5: RulesCache.sync() — 규칙 유효성 검사 없음
`local_server/storage/rules_cache.py` L52-56. 악성 규칙(qty 음수 등) 방어 없음.

### M6: timeline 조회 5000건 고정 limit
`local_server/routers/logs.py` L146. 대용량 메모리 로드 + 블로킹 SQLite.

### M7: uvicorn Config에 host/port 이중 지정
`local_server/main.py` L373-390. `sockets=[sock]` 전달 시 host/port는 불필요.

---

## 미완성 기능

| ID | 내용 | 파일 |
|----|------|------|
| I1 | KIS WS approval_key 발급 미구현 | `broker/kis/ws.py` L146 |
| I2 | KIS 모의/실전 자동 감지 미구현 | `routers/config.py` L98 |
| I3 | WS heartbeat_ack 버전 처리 미구현 | `cloud/ws_relay_client.py` L190 |
| I4 | 오프라인 내성 (6AC) 미구현 | 클라우드 단절 시 로컬 캐시만으로 동작 |
| I5 | 하트비트 WS ↔ HTTP 응답 통합 | `cloud/heartbeat.py` L99 |
