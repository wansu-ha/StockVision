# 장중 실시간 경고 — 구현 계획

> 작성일: 2026-03-12 | 상태: 초안 | Phase D (D1)

## 아키텍처

```
┌─ StrategyEngine (evaluate_all, 1분) ──────────────┐
│  후보 수집 → SystemTrader → 실행                    │
│  └→ AlertMonitor.check_all(balance, open_orders)   │
│       ├─ check_position_loss()                     │
│       ├─ check_volatility()                        │
│       ├─ check_stale_orders()                      │
│       ├─ check_daily_loss_proximity()              │
│       └─ check_market_close_orders()               │
└────────────────────────────────────────────────────┘
         │ fire → WS broadcast + LogDB write
         ▼
┌─ HealthWatchdog (30초, 독립 asyncio 태스크) ───────┐
│  check_engine_heartbeat() — 마지막 evaluate 시각    │
│  check_broker_health()   — 브로커 API ping          │
└────────────────────────────────────────────────────┘
         │ fire → WS broadcast + LogDB write
         ▼
┌─ 프론트엔드 ───────────────────────────────────────┐
│  useLocalBridgeWS → alertsStore → OpsPanel 배지     │
│                   → 토스트 (critical = 수동 닫기)    │
│                   → Web Notification                │
│  Settings → alertsClient → PUT /api/settings/alerts │
│  ExecutionLog → 경고 탭 (LogDB ALERT 조회)          │
└────────────────────────────────────────────────────┘
```

## 수정/생성 파일 목록

### 새로 생성 (8개)

| 파일 | 역할 |
|------|------|
| `local_server/engine/alert_monitor.py` | AlertMonitor — 7종 경고 평가, 쿨다운, fire() 공개 인터페이스 |
| `local_server/engine/health_watchdog.py` | HealthWatchdog — 엔진/브로커 헬스 체크 (독립 태스크) |
| `local_server/routers/alerts.py` | GET/PUT `/api/settings/alerts` |
| `frontend/src/stores/alertsStore.ts` | 미확인 경고 목록, 배지 카운트 (Zustand) |
| `frontend/src/components/AlertsDropdown.tsx` | OpsPanel 내 경고 배지 + 드롭다운 |
| `frontend/src/components/AlertSettings.tsx` | Settings 내 알림 설정 섹션 |
| `frontend/src/components/AlertsTab.tsx` | ExecutionLog 내 경고 히스토리 탭 |
| `frontend/src/services/alertsClient.ts` | 경고 설정 API 클라이언트 |

### 수정 (10개)

| 파일 | 변경 내용 |
|------|----------|
| `local_server/config.py` | DEFAULT_CONFIG에 `alerts` 섹션 추가 |
| `local_server/storage/log_db.py` | `LOG_TYPE_ALERT = "ALERT"` 상수 추가 |
| `local_server/engine/engine.py` | evaluate_all()에 AlertMonitor.check_all() 호출 삽입 |
| `local_server/routers/ws.py` | alert 메시지 타입 상수 추가 |
| `local_server/api/main.py` | alerts 라우터 등록 + HealthWatchdog 태스크 시작 |
| `frontend/src/hooks/useLocalBridgeWS.ts` | alert 핸들러 확장 → alertsStore + 토스트 + Web Notification |
| `frontend/src/components/main/OpsPanel.tsx` | AlertsDropdown 삽입 |
| `frontend/src/pages/Settings.tsx` | AlertSettings 섹션 추가 |
| `frontend/src/pages/ExecutionLog.tsx` | 경고 탭 추가 |
| `frontend/src/stores/toastStore.ts` | critical 토스트 (자동 닫기 비활성화) 옵션 추가 |

## 구현 순서

### Step 1: 백엔드 기반 — AlertMonitor + 설정

**생성**: `alert_monitor.py`, **수정**: `config.py`, `log_db.py`

- AlertMonitor 클래스: `_should_fire()` 쿨다운, `fire()` 공개 인터페이스
- 5종 체커: position_loss, volatility, stale_orders, daily_loss_proximity, market_close_orders
- config.py에 alerts 기본 설정 추가
- log_db.py에 LOG_TYPE_ALERT 상수 추가

**verify**: `python -c "from local_server.engine.alert_monitor import AlertMonitor"` 성공

### Step 2: 백엔드 — HealthWatchdog

**생성**: `health_watchdog.py`

- 독립 asyncio 태스크, 30초 간격
- check_engine_heartbeat(): evaluate_all 마지막 실행 시각 3분 초과 시 critical
- check_broker_health(): 브로커 API ping 3회 연속 실패 시 critical
- AlertMonitor.fire()를 통해 경고 발송

**verify**: `python -c "from local_server.engine.health_watchdog import HealthWatchdog"` 성공

### Step 3: 백엔드 — 엔진 연동 + WS 브로드캐스트

**수정**: `engine.py`, `ws.py`

- engine.py: evaluate_all() 끝에 `self._alert_monitor.check_all(balance, open_orders)` 호출
- AlertMonitor에 WS broadcast 콜백 주입
- ws.py: alert 타입 상수 추가

**verify**: 로컬 서버 시작 → 로그에 "AlertMonitor initialized" 표시

### Step 4: 백엔드 — 경고 설정 API

**생성**: `routers/alerts.py`, **수정**: `api/main.py`

- GET /api/settings/alerts: 현재 설정 반환
- PUT /api/settings/alerts: 설정 변경 (Kill Switch/손실 락 편집 차단)
- main.py에 라우터 등록 + HealthWatchdog 태스크 시작

**verify**: `curl localhost:4020/api/settings/alerts` 응답 확인

### Step 5: 프론트엔드 — 경고 수신 인프라

**생성**: `alertsStore.ts`, `alertsClient.ts`, **수정**: `useLocalBridgeWS.ts`, `toastStore.ts`

- alertsStore (Zustand): alerts 배열, unreadCount, add(), markAllRead()
- alertsClient: getSettings(), updateSettings()
- useLocalBridgeWS: alert 핸들러 → alertsStore.add() + 토스트 + Web Notification
- toastStore: critical 토스트 옵션 (autoClose: false)

**verify**: `npm run build` 성공

### Step 6: 프론트엔드 — OpsPanel 경고 배지 + 드롭다운

**생성**: `AlertsDropdown.tsx`, **수정**: `OpsPanel.tsx`

- 🔔 배지 (unreadCount > 0일 때 숫자 표시)
- 드롭다운: 최근 경고 목록 (시간순, severity 아이콘)
- "전체 경고 보기" → `/logs?tab=alerts` 링크

**verify**: 브라우저에서 OpsPanel에 🔔 배지 표시, 클릭 시 드롭다운

### Step 7: 프론트엔드 — 알림 설정 UI

**생성**: `AlertSettings.tsx`, **수정**: `Settings.tsx`

- 마스터 ON/OFF 토글
- 규칙별 ON/OFF + 임계값 입력
- Kill Switch/손실 락은 disabled (끌 수 없음 표시)
- PUT /api/settings/alerts 호출

**verify**: 브라우저 Settings → 알림 설정 섹션 표시, 토글 동작

### Step 8: 프론트엔드 — 경고 히스토리 탭

**생성**: `AlertsTab.tsx`, **수정**: `ExecutionLog.tsx`

- /logs 페이지에 "경고" 탭 추가
- LogDB에서 log_type=ALERT 필터링
- 기존 타임라인 컴포넌트 재사용

**verify**: 브라우저 /logs → 경고 탭 클릭 → 경고 히스토리 표시

## 검증 방법

| 항목 | 방법 |
|------|------|
| 빌드 | `npm run build` + `python -m py_compile local_server/engine/alert_monitor.py` |
| 경고 생성 | 로컬 서버 시작 → evaluate_all 로그에 AlertMonitor 호출 확인 |
| WS 수신 | 브라우저 콘솔에서 WS alert 메시지 수신 확인 |
| 토스트 | warning → 5초 자동 닫힘, critical → 수동 닫기 |
| 배지 | OpsPanel 🔔 배지에 숫자 표시 |
| 설정 | Settings 페이지에서 토글 → API 호출 → config.json 반영 확인 |
| 히스토리 | /logs → 경고 탭 → ALERT 로그 표시 |
| Web Notification | 브라우저 알림 허용 후 경고 시 OS 알림 표시 |
| 쿨다운 | 동일 경고 30분 내 재발송 안 됨, 심각도 상승 시 재발송 |
| Kill Switch 보호 | PUT alerts에서 kill_switch enabled=false → 서버 거부 |
