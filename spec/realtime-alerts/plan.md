# 장중 실시간 경고 — 구현 계획

> 작성일: 2026-03-12 | 상태: 초안 | Phase D (D1)

## 아키텍처

```
┌─ StrategyEngine (evaluate_all, 1분) ──────────────┐
│  잔고 조회 → 미체결 조회                             │
│  └→ AlertMonitor.check_all(balance, open_orders)   │
│       ├─ check_position_loss()                     │
│       ├─ check_volatility()                        │
│       ├─ check_daily_loss_proximity()              │
│       ├─ check_stale_orders()                      │
│       └─ check_market_close_orders()               │
│  (경고 평가 후) 후보 수집 → SystemTrader → 실행      │
└────────────────────────────────────────────────────┘
         │ fire → WS broadcast + LogDB write
         ▼
┌─ HealthWatchdog (30초, 독립 asyncio 태스크) ───────┐
│  check_engine_heartbeat() — 마지막 evaluate 시각    │
│  check_broker_health()   — 브로커 API ping          │
│  ※ 시작 후 grace period 5분 (오탐 방지)             │
│  ※ 장 시간(09:00~15:30) 외에는 하트비트 체크 비활성  │
└────────────────────────────────────────────────────┘
         │ fire → WS broadcast + LogDB write
         ▼
┌─ 프론트엔드 ───────────────────────────────────────┐
│  useLocalBridgeWS → useNotifStore 확장 (severity)   │
│                   → 토스트 (critical = 수동 닫기)    │
│                   → Web Notification                │
│  Settings → alertsClient → PUT /api/settings/alerts │
│  ExecutionLog → 경고 탭 (LogDB ALERT 조회)          │
└────────────────────────────────────────────────────┘
```

### 핵심 설계 결정

1. **AlertMonitor 호출 위치**: evaluate_all()에서 잔고 조회 직후, `trading_enabled` 체크 **앞**에 배치. Kill Switch/손실 락 발동 상태에서도 경고 평가가 실행되어야 하기 때문.
2. **open_orders / today_pnl 조회**: evaluate_all()에서 `broker.get_open_orders()`와 `get_log_db().today_realized_pnl()`을 **무조건** 먼저 조회. 현재 코드는 today_pnl을 `is_trading_enabled()` 분기 안에서만 계산하므로, AlertMonitor 호출 전에 조건 없이 계산하도록 변경.
3. **HealthWatchdog 오탐 방지**: (a) 시작 후 5분 grace period — evaluate_all()이 아직 실행되지 않았을 때 거짓 경고 방지, (b) 장 시간(09:00~15:30) 외에는 하트비트 체크 비활성화 — 장 마감 후 정상 중단을 장애로 오인하지 않음.
4. **HealthWatchdog 엔진 접근**: 엔진은 main.py lifespan이 아닌 API(/api/engine/start)에서 생성됨. HealthWatchdog는 `app.state`에서 엔진 인스턴스를 참조. 엔진이 없으면 하트비트 체크 건너뜀. 엔진은 evaluate_all() 완료 시 `self._last_evaluate_ts`를 갱신.
5. **Kill Switch/손실 락 통합**: 기존 `_notify_loss_lock()`과 kill_switch 상태 변경을 AlertMonitor.fire()로 통합. safeguard.py는 수정하지 않고, engine.py에서 safeguard 상태를 읽어 AlertMonitor.fire()를 호출.
6. **프론트엔드 스토어**: 별도 alertsStore를 만들지 않고, 기존 `useNotifStore`(useLocalBridgeWS.ts 내)를 확장. `severity` 필드 추가 + alert 전용 필터 메서드. 기존 `alertStore.ts`(UI 액션 피드백용)와 역할 분리 유지.
7. **WS 메시지 형식 통합**: 기존 `alert` 핸들러의 `{ level, message }` → spec의 `{ id, alert_type, severity, ... }` 형식으로 교체. 기존 `level` 필드는 사용처가 없으므로 하위 호환 불필요.

## 수정/생성 파일 목록

### 새로 생성 (6개)

| 파일 | 역할 |
|------|------|
| `local_server/engine/alert_monitor.py` | AlertMonitor — 5종 경고 평가, 쿨다운, fire() 공개 인터페이스 |
| `local_server/engine/health_watchdog.py` | HealthWatchdog — 엔진/브로커 헬스 체크 (독립 태스크, grace period) |
| `local_server/routers/alerts.py` | GET/PUT `/api/settings/alerts` |
| `frontend/src/components/AlertsDropdown.tsx` | OpsPanel 내 경고 배지 + 드롭다운 |
| `frontend/src/components/AlertSettings.tsx` | Settings 내 알림 설정 섹션 |
| `frontend/src/services/alertsClient.ts` | 경고 설정 API 클라이언트 |

### 수정 (10개)

| 파일 | 변경 내용 |
|------|----------|
| `local_server/config.py` | DEFAULT_CONFIG에 `alerts` 섹션 추가 |
| `local_server/storage/log_db.py` | `LOG_TYPE_ALERT = "ALERT"` 상수 + count_by_type에 ALERT 추가 |
| `local_server/engine/engine.py` | evaluate_all()에서 open_orders 조회 + AlertMonitor.check_all() 호출 (trading_enabled 체크 앞) |
| `local_server/routers/ws.py` | `WS_TYPE_ALERT = "alert"` 상수 추가 |
| `local_server/main.py` | alerts 라우터 등록 + HealthWatchdog 태스크 시작 |
| `frontend/src/hooks/useLocalBridgeWS.ts` | alert 핸들러를 spec 형식으로 교체, useNotifStore에 severity 필드 추가 |
| `frontend/src/components/main/OpsPanel.tsx` | AlertsDropdown 삽입 |
| `frontend/src/pages/Settings.tsx` | AlertSettings 섹션 추가 |
| `frontend/src/pages/ExecutionLog.tsx` | 경고 탭 추가 (3탭: 테이블/타임라인/경고) |
| `frontend/src/stores/toastStore.ts` | critical 토스트 옵션 (autoClose 파라미터 추가, 기존 호출부 영향 없음) |

## 구현 순서

### Step 1: 백엔드 기반 — AlertMonitor + 설정

**생성**: `alert_monitor.py`, **수정**: `config.py`, `log_db.py`

- AlertMonitor 클래스: `_should_fire()` 쿨다운, `fire()` 공개 인터페이스
- 5종 체커: position_loss, volatility, stale_orders, daily_loss_proximity, market_close_orders
- config.py에 alerts 기본 설정 추가
- log_db.py에 LOG_TYPE_ALERT 상수 추가 + count_by_type 결과에 포함

**verify**: `python -c "from local_server.engine.alert_monitor import AlertMonitor"` 성공

### Step 2: 백엔드 — HealthWatchdog

**생성**: `health_watchdog.py`

- 독립 asyncio 태스크, 30초 간격
- check_engine_heartbeat(): evaluate_all 마지막 실행 시각 3분 초과 시 critical
  - **grace period**: 시작 후 5분간은 하트비트 체크 건너뜀
  - **장 시간 제한**: 09:00~15:30 외에는 하트비트 체크 비활성화
- check_broker_health(): 브로커 API ping 3회 연속 실패 시 critical
- AlertMonitor.fire()를 통해 경고 발송

**verify**: `python -c "from local_server.engine.health_watchdog import HealthWatchdog"` 성공

### Step 3: 백엔드 — 엔진 연동 + WS 브로드캐스트

**수정**: `engine.py`, `ws.py`

- engine.py 변경사항:
  - evaluate_all()에서 잔고 조회 후 `open_orders = await self._broker.get_open_orders()` 추가
  - `today_pnl = get_log_db().today_realized_pnl()`을 조건 없이 상위로 이동
  - `trading_enabled` 체크 **앞**에 `await self._alert_monitor.check_all(balance, open_orders, today_pnl)` 호출
  - AlertMonitor는 `__init__`에서 생성, WS broadcast 콜백 주입
  - `_last_evaluate_ts` 속성 추가 (evaluate_all 완료 시 갱신 → HealthWatchdog가 참조)
  - 기존 `_notify_loss_lock()` → AlertMonitor.fire() 경유로 교체
  - safeguard.kill_switch 상태 변경 시에도 AlertMonitor.fire() 호출
- ws.py: `WS_TYPE_ALERT = "alert"` 상수 추가

**verify**: 로컬 서버 시작 → 로그에 "AlertMonitor initialized" 표시

### Step 4: 백엔드 — 경고 설정 API

**생성**: `routers/alerts.py`, **수정**: `main.py`

- GET /api/settings/alerts: 현재 설정 반환
- PUT /api/settings/alerts: 설정 변경 (Kill Switch/손실 락 편집 차단)
- main.py에 라우터 등록 + HealthWatchdog 태스크를 lifespan에서 시작 (heartbeat_task와 동일 패턴, `app.state`에서 엔진/브로커 참조)

**verify**: `curl localhost:4020/api/settings/alerts` 응답 확인

### Step 5: 프론트엔드 — 경고 수신 인프라

**생성**: `alertsClient.ts`, **수정**: `useLocalBridgeWS.ts`, `toastStore.ts`

- useNotifStore 확장: Notification 타입에 `severity?: 'warning' | 'critical'`, `alertType?: string`, `action?: { label, route }` 필드 추가
- alertsClient: getSettings(), updateSettings()
- useLocalBridgeWS의 alert 핸들러: spec 형식 `{ id, alert_type, severity, ... }` 파싱 → useNotifStore.add() + 토스트 + Web Notification
- toastStore: `showToast(message, type, options?)` — options.persistent로 autoClose 제어, 기존 호출부는 영향 없음 (옵셔널 파라미터)

**verify**: `npm run build` 성공

### Step 6: 프론트엔드 — OpsPanel 경고 배지 + 드롭다운

**생성**: `AlertsDropdown.tsx`, **수정**: `OpsPanel.tsx`

- 배지: severity가 있는 알림의 unread 수 표시
- 드롭다운: 최근 경고 목록 (시간순, severity 아이콘)
- "전체 경고 보기" → `/logs?tab=alerts` 링크

**verify**: 브라우저에서 OpsPanel에 배지 표시, 클릭 시 드롭다운

### Step 7: 프론트엔드 — 알림 설정 UI

**생성**: `AlertSettings.tsx`, **수정**: `Settings.tsx`

- 마스터 ON/OFF 토글
- 규칙별 ON/OFF + 임계값 입력
- Kill Switch/손실 락은 disabled (끌 수 없음 표시)
- PUT /api/settings/alerts 호출

**verify**: 브라우저 Settings → 알림 설정 섹션 표시, 토글 동작

### Step 8: 프론트엔드 — 경고 히스토리 탭

**수정**: `ExecutionLog.tsx`

- 기존 2탭(테이블/타임라인) → 3탭(테이블/타임라인/경고)으로 확장
- 경고 탭: LogDB에서 log_type=ALERT 필터링하여 표시
- 기존 로그 테이블 컴포넌트 재사용 (ALERT 타입 스타일 추가)

**verify**: 브라우저 /logs → 경고 탭 클릭 → 경고 히스토리 표시

## 검증 방법

| 항목 | 방법 |
|------|------|
| 빌드 | `npm run build` + `python -m py_compile local_server/engine/alert_monitor.py` |
| 경고 생성 | 로컬 서버 시작 → evaluate_all 로그에 AlertMonitor 호출 확인 |
| WS 수신 | 브라우저 콘솔에서 WS alert 메시지 수신 확인 |
| 토스트 | warning → 4초 자동 닫힘, critical → 수동 닫기 |
| 배지 | OpsPanel 배지에 숫자 표시 |
| 설정 | Settings 페이지에서 토글 → API 호출 → config.json 반영 확인 |
| 히스토리 | /logs → 경고 탭 → ALERT 로그 표시 |
| Web Notification | 브라우저 알림 허용 후 경고 시 OS 알림 표시 |
| 쿨다운 | 동일 경고 30분 내 재발송 안 됨, 심각도 상승 시 재발송 |
| Kill Switch 보호 | PUT alerts에서 kill_switch enabled=false → 서버 거부 |
| HealthWatchdog grace | 서버 시작 후 5분간 하트비트 경고 없음 |
| 장 마감 후 | 15:30 이후 하트비트 경고 없음 (정상 중단) |
