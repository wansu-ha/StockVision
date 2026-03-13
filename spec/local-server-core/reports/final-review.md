# 최종 리뷰 보고서: Unit 2 로컬 서버 코어

## 구현 완료 현황

| Step | 내용 | 상태 |
|------|------|------|
| 1 | FastAPI 스켈레톤 + 프로젝트 구조 | 완료 |
| 2 | 저장소 레이어 (keyring, JSON, SQLite) | 완료 |
| 3 | REST 라우터 (auth, config, status, trading, rules, logs) | 완료 |
| 4 | WebSocket 엔드포인트 (/ws) | 완료 |
| 5 | 시스템 트레이 아이콘 (pystray) | 완료 |
| 6 | 클라우드 서버 통신 클라이언트 | 완료 |
| 7 | 기동/종료 생명주기 | 완료 |
| 8 | CORS 미들웨어 | 완료 |
| 9 | 수면 방지 (SetThreadExecutionState) | 완료 |
| 10 | PyInstaller .exe 번들 설정 | 완료 |
| - | 테스트 파일 3개 | 완료 |

## 생성된 파일 전체 목록

```
sv_core/
  __init__.py
  broker/
    __init__.py
    base.py              — BrokerAdapter ABC (10개 추상 메서드)

local_server/
  __init__.py
  main.py                — FastAPI 앱, lifespan, CORS, 라우터 등록
  config.py              — Config 클래스, 점 표기법 get/set, 싱글턴
  requirements.txt

  storage/
    __init__.py
    credential.py        — keyring 래퍼 (save/load/delete/clear)
    rules_cache.py       — JSON 규칙 캐시 (sync/get_rules)
    config_store.py      — config API 헬퍼 (마스킹, keyring 분리)
    log_db.py            — SQLite 로그 (write/query)

  routers/
    __init__.py
    auth.py              — POST /api/auth/token, /logout, GET /api/auth/status
    config.py            — GET/PATCH /api/config
    status.py            — GET /api/status
    trading.py           — POST /api/strategy/start, /stop, /api/trading/order
    rules.py             — POST /api/rules/sync, GET /api/rules
    logs.py              — GET /api/logs
    ws.py                — WS /ws (ConnectionManager, 브로드캐스트)

  cloud/
    __init__.py
    client.py            — CloudClient (fetch_rules, send_heartbeat, health_check)
    heartbeat.py         — start_heartbeat() 코루틴

  tray/
    __init__.py
    tray_app.py          — pystray 트레이 (start_tray, stop_tray)

  utils/
    __init__.py
    sleep_prevent.py     — enable/disable_sleep_prevention

  pyinstaller.spec       — 단일 .exe 번들 설정

  tests/
    __init__.py
    test_storage.py      — Config, RulesCache, LogDB, Credential 테스트 (22개)
    test_routers.py      — REST 라우터, ConnectionManager 테스트 (18개)
    test_cloud_client.py — CloudClient 테스트 (8개)

spec/local-server-core/
  spec.md
  plan.md
  reports/
    step1.md ~ step10.md
    final-review.md
```

## API 엔드포인트 대조표

| 명세 | 구현 | 일치 |
|------|------|------|
| POST /api/auth/token | auth.py | OK |
| GET /api/config | config.py | OK |
| PATCH /api/config | config.py | OK |
| GET /api/status | status.py | OK |
| POST /api/strategy/start | trading.py | OK |
| POST /api/strategy/stop | trading.py | OK |
| POST /api/trading/order | trading.py | OK |
| POST /api/rules/sync | rules.py | OK |
| GET /api/logs | logs.py | OK |
| WS /ws | ws.py | OK |

## 응답 형식 일관성

모든 REST 엔드포인트가 `{ "success": bool, "data": ..., "count": int }` 형식을 준수한다.

## 보안 리뷰

| 항목 | 처리 방식 |
|------|-----------|
| API Key 저장 | Windows Keyring (암호화) |
| app_key 응답 노출 | read_config()에서 "****" 마스킹 |
| CORS | localhost:5173, localhost:3000만 허용 |
| 자격증명 없는 주문 | 400 Bad Request |
| 로컬 서버 인바운드 | localhost만 서빙 (0.0.0.0 미사용) |

## 주요 설계 결정 기록

### 1. keyring vs 환경변수
API Key를 환경변수나 .env에 저장하지 않고 Windows Keyring을 선택.
이유: 환경변수는 ps 명령 등으로 노출 가능, Keyring은 OS 수준 암호화.

### 2. 동기 SQLite vs aiosqlite
LogDB를 동기 sqlite3로 구현.
이유: 로그 쓰기는 빈도가 낮고 짧은 작업이며, 동기 I/O가 코드 단순성을 높임.
고빈도 체결 로그가 필요하면 aiosqlite로 전환 가능.

### 3. heartbeat 방식
asyncio.Task로 관리, CancelledError로 종료.
이유: uvicorn의 lifespan 훅이 async이므로 asyncio.Task가 자연스러운 패턴.

### 4. 트레이 아이콘 daemon 스레드
pystray는 blocking mainloop을 사용하므로 별도 daemon 스레드 필요.
daemon=True로 설정하여 FastAPI 메인 루프 종료 시 자동 정리.

### 5. 모듈 수준 app 인스턴스
`app = create_app()` 를 모듈 수준에 유지.
이유: uvicorn이 `local_server.main:app`으로 앱을 찾기 위해 필요.
테스트에서는 `create_app()`을 직접 호출하여 독립적 앱 인스턴스 생성.

## Unit 1 연동 시 TODO 목록

다음 항목은 Unit 1 BrokerAdapter 구현 완성 후 교체가 필요하다:

1. `routers/auth.py` — POST /api/auth/token: 더미 토큰 → BrokerAdapter.authenticate()
2. `routers/status.py` — broker.connected: 하드코딩 False → BrokerAdapter.is_authenticated()
3. `routers/trading.py` — POST /api/trading/order: stub → BrokerAdapter.send_order()
4. `routers/ws.py` — BrokerAdapter.listen() 이벤트를 manager.broadcast()로 연결

## 개선 가능 항목 (추후)

- LogDB: 파일 핸들러 추가 (PyInstaller .exe 배포 시 로그 확인용)
- CloudClient: 연결 풀 유지 (고빈도 요청 시 성능 개선)
- rules_cache.py: 동기화 타임스탬프 저장 (마지막 동기화 시간 표시)
- sleep_prevent.py: 전략 엔진 시작/중지 시 자동 활성화/해제 연동
