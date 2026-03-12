# 장중 실시간 경고 (Realtime Alerts)

> 작성일: 2026-03-12 | 상태: 확정 | Phase D (D1)

## 1. 배경

현재 엔진에는 Kill Switch와 손실 락이 자동 안전장치로 구현되어 있다. 하지만 이 두 가지는 **이미 문제가 발생한 후** 동작하는 사후 조치다.

사용자에게 필요한 것은 "아직 괜찮지만 **곧 위험해질 수 있다**"는 사전 경고다. 예를 들어:
- 보유종목 평가손익이 -3% 이하일 때 → "삼성전자 평가손익 -3.2%"
- 특정 종목이 전일 대비 ±5% 급변동 → "NAVER 급등 +5.3%"
- 미체결 주문이 10분째 방치됨 → "주문 #123 미체결 10분 경과"

이 경고들은 **전략과 무관하게** 시스템 레벨에서 감지되며, 사용자가 어떤 전략을 쓰든 동일하게 작동한다.

## 2. 목표

장중에 사용자가 앱을 보고 있지 않아도, 위험 상황을 실시간으로 감지하고 즉시 알린다.

## 3. 범위

### 3.1 포함

**A. 경고 규칙 (엔진 내장, 설정 불필요)**

| 경고 | 트리거 조건 | 심각도 |
|------|-----------|--------|
| 종목 손실 경고 | 보유종목 평가손익률 ≤ -N% (기본 -3%) | warning |
| 급변동 | 보유종목 현재가 전일 대비 ±5% | warning |
| 미체결 장기 방치 | 주문 제출 후 10분 경과 미체결 | warning |
| 엔진 비정상 정지 | evaluate_all 2회 연속 예외 | critical |
| 브로커 연결 단절 | 브로커 API 응답 실패 3회 연속 | critical |
| 일일 손실 한도 근접 | 당일 실현손익이 max_loss_pct의 80% 도달 | warning |
| 장 종료 임박 미체결 | 15:20 이후 미체결 주문 존재 | warning |
| Kill Switch 발동 | safeguard.kill_switch != OFF | critical |
| 손실 락 발동 | safeguard.loss_lock 활성화 | critical |

> Kill Switch/손실 락은 이미 구현됨. 여기서는 **통합 경고 프레임워크**로 묶어서 일관된 UI와 저장 구조를 제공한다.

**B. 경고 전달 경로**
- WS 브로드캐스트 (`type: "alert"`) → 앱이 열려 있으면 즉시 표시
- 브라우저 Web Notification → 앱이 백그라운드여도 OS 알림
- LogDB 저장 (`LOG_TYPE_ALERT`) → 히스토리 조회 가능

**C. 경고 UI**
- OpsPanel에 경고 배지 (미확인 경고 수)
- 경고 드롭다운 (최근 경고 목록, 시간순)
- "전체 경고 보기" → `/logs` 페이지에 경고 탭 추가 (기존 실행 로그 옆)
- 토스트 알림 (critical은 자동 닫히지 않음)

**D. 경고 설정 (Settings → 알림 설정)**
- 경고 마스터 ON/OFF (전체 끄기)
- 경고 유형별 개별 ON/OFF 토글
  - 종목 손실 경고: ON/OFF + 임계값 조정 (기본: -3%)
  - 급변동 경고: ON/OFF + 임계값 조정 (기본: ±5%)
  - 미체결 방치 경고: ON/OFF + 시간 조정 (기본: 10분)
  - 일일 손실 한도 근접: ON/OFF (기본: ON)
  - 장 종료 임박 미체결: ON/OFF (기본: ON)
  - 엔진/브로커 장애: ON/OFF (기본: ON, 끄기 비권장)
  - Kill Switch/손실 락: 항상 ON (끌 수 없음, config.json에서도 비활성화 불가)
- 브라우저 알림 허용 요청
- 설정은 로컬 서버에 저장 (`~/.stockvision/config.json`)

### 3.2 제외

- 종목별 가격 알림 — "삼성전자 5만원 이하면 알림" (D1 이후 확장)
- 복합 조건 커스텀 경고 — "RSI 70 이상 + 거래량 3배" (Phase E, 전략 DSL 필요)
- 외부 알림 채널 (텔레그램, 이메일, FCM 푸시)
- LLM 기반 경고 해석/요약
- 경고 기반 자동 매매 (경고 → 자동 손절 등)

### 3.3 확장 포인트 (D1에서 설계만, 구현은 이후)

**전략 DSL `alert()` 함수** (Phase E)

전략 코드에서 `alert()`를 호출하면 같은 경고 프레임워크로 전달:

```python
# 전략 규칙 예시
if rsi > 80:
    alert("RSI 과열", severity="warning")
if volume > sma_volume * 3:
    alert("거래량 급증", severity="warning")
```

D1에서 AlertMonitor를 설계할 때 외부에서 경고를 주입할 수 있는 `fire()` 메서드를 공개 인터페이스로 노출한다. `alert_type = "strategy"` 카테고리를 예약한다.

**종목별 가격 알림** (D1 이후)

사용자가 "삼성전자 5만원 이하면 알림" 같은 단순 가격 조건을 설정. AlertMonitor에 `check_price_alerts()` 체커 추가로 구현 가능. 저장: `~/.stockvision/config.json`의 `price_alerts` 배열.

## 4. 의존성

| 의존 대상 | 상태 | 비고 |
|-----------|------|------|
| StrategyEngine (`engine.py`) | 구현됨 | evaluate_all 루프에 경고 평가 삽입 |
| Safeguard (`safeguard.py`) | 구현됨 | Kill Switch / 손실 락 상태 읽기 |
| WS 브로드캐스트 (`routers/ws.py`) | 구현됨 | `type: "alert"` 메시지 추가 |
| LogDB (`storage/log_db.py`) | 구현됨 | `LOG_TYPE_ALERT` 추가 |
| useLocalBridgeWS | 구현됨 | `alert` 타입 핸들러 이미 존재 |
| 잔고 API (`routers/account.py`) | 구현됨 | 보유종목, 평가손익률 |

## 5. 설계

### 5.1 경고 평가 위치

**메인 경고 (evaluate_all 내부, 1분마다)**

```
evaluate_all() (1분마다)
  ├─ 기존: 후보 수집 → SystemTrader → 실행
  └─ 신규: AlertMonitor.check_all(balance, open_orders)
            ├─ check_position_loss(positions)
            ├─ check_volatility(positions)
            ├─ check_stale_orders(open_orders)
            ├─ check_daily_loss_proximity(today_pnl, total_equity)
            └─ check_market_close_orders(open_orders)
```

**헬스 watchdog (evaluate_all과 독립, 별도 태스크)**

엔진이 죽으면 evaluate_all 안의 경고도 죽는다. 엔진/브로커 헬스 체크는 별도 asyncio 태스크로 분리:

```
HealthWatchdog (30초마다, evaluate_all과 독립)
  ├─ check_engine_heartbeat()  — evaluate_all 마지막 실행 시각 확인, 3분 초과 시 critical
  └─ check_broker_health()     — 브로커 API ping, 3회 연속 실패 시 critical
```

### 5.2 중복 방지

같은 경고를 1분마다 반복 발송하면 안 된다.

```python
class AlertMonitor:
    _fired: dict[str, tuple[datetime, float]]  # alert_key → (마지막 발송 시각, 발송 시 값)
    _cooldown = timedelta(minutes=30)

    def _should_fire(self, key: str, current_value: float | None = None) -> bool:
        last = self._fired.get(key)
        if last:
            last_ts, last_val = last
            # 쿨다운 내지만 심각도 상승 시 재발송 (예: -3% → -5%)
            if datetime.now() - last_ts < self._cooldown:
                if current_value is not None and last_val is not None:
                    if abs(current_value) > abs(last_val) * 1.5:
                        pass  # 쿨다운 무시, 재발송
                    else:
                        return False
                else:
                    return False
        self._fired[key] = (datetime.now(), current_value)
        return True

    def fire(self, alert_type: str, **kwargs):
        """외부에서 경고 주입 (전략 DSL alert() 용)"""
        ...
```

`alert_key` 예: `"position_loss:005930"`, `"volatility:035420"`, `"stale_order:sv-1-abc"`, `"strategy:rule_1:RSI 과열"`

### 5.3 경고 설정 API

```
GET  /api/settings/alerts        → 현재 경고 설정 반환
PUT  /api/settings/alerts        → 경고 설정 변경 (config.json에 저장)
```

요청 예:
```json
{
  "master_enabled": true,
  "rules": {
    "position_loss": { "enabled": true, "threshold_pct": -3.0 },
    "volatility": { "enabled": true, "threshold_pct": 5.0 },
    "stale_order": { "enabled": true, "threshold_min": 10 },
    "daily_loss_proximity": { "enabled": true },
    "market_close_orders": { "enabled": true },
    "engine_health": { "enabled": true },
    "broker_health": { "enabled": true }
  }
}
```

> Kill Switch/손실 락은 응답에 포함되지만 `enabled: false`로 변경 불가 (서버가 거부).

### 5.4 WS 메시지 형식

```json
{
  "type": "alert",
  "data": {
    "id": "alert-uuid",
    "alert_type": "position_loss",
    "severity": "warning",
    "symbol": "005930",
    "title": "종목 손실 경고",
    "message": "삼성전자 평가손익 -3.2% (임계값 -3%)",
    "ts": "2026-03-12T10:30:00",
    "action": {
      "label": "잔고 확인",
      "route": "/portfolio"
    }
  }
}
```

> `action.route`는 프론트에서 허용 경로 화이트리스트(`/`, `/portfolio`, `/logs`, `/settings`)로 검증한다.

### 5.5 LogDB 스키마

기존 `logs` 테이블 사용. `log_type = "ALERT"`, meta에 구조화 데이터:

```json
{
  "alert_type": "position_loss",
  "severity": "warning",
  "symbol": "005930",
  "threshold": -3.0,
  "current_value": -3.2,
  "cooldown_until": "2026-03-12T11:00:00"
}
```

### 5.6 프론트엔드 UI

```
┌─ OpsPanel ──────────────────────────────────┐
│ ● 엔진 실행중   ● 브로커 연결됨   🔔 3      │
│                                              │
│ ┌─ 경고 드롭다운 ─────────────────────────┐  │
│ │ ⚠ 삼성전자 평가손익 -3.2%   10:30  │  │
│ │ ⚠ NAVER 급등 +5.3%              10:15  │  │
│ │ 🔴 브로커 연결 단절               10:05  │  │
│ │                                         │  │
│ │ [전체 경고 보기]                         │  │
│ └─────────────────────────────────────────┘  │
└──────────────────────────────────────────────┘
```

토스트:
- `warning`: 5초 후 자동 닫힘
- `critical`: 수동 닫기 필요, 빨간색 강조

## 6. 수용 기준

- [ ] evaluate_all 루프에서 경고 평가가 1분마다 실행된다
- [ ] 보유종목 평가손익이 임계값(-3%) 이하일 때 WS 경고가 전송된다
- [ ] 보유종목 ±5% 급변동 시 WS 경고가 전송된다
- [ ] 미체결 주문 10분 방치 시 WS 경고가 전송된다
- [ ] 동일 경고는 30분 간격으로 중복 방지된다
- [ ] OpsPanel에 경고 배지와 드롭다운이 표시된다
- [ ] critical 경고는 토스트가 자동으로 닫히지 않는다
- [ ] 경고가 LogDB에 저장되고 히스토리 조회가 가능하다
- [ ] 브라우저 Web Notification이 지원된다 (사용자 허용 시)
- [ ] Settings 페이지에서 경고 유형별 ON/OFF 토글이 가능하다
- [ ] 임계값(손실%, 급변동%, 미체결 시간)을 Settings에서 조정할 수 있다
- [ ] Kill Switch/손실 락 경고는 끌 수 없다 (config.json 직접 편집으로도 불가)
- [ ] 일일 손실 한도 80% 도달 시 경고가 전송된다
- [ ] 15:20 이후 미체결 주문 존재 시 경고가 전송된다
- [ ] 심각도 상승 시 (예: -3% → -5%) 쿨다운을 무시하고 재발송된다
- [ ] AlertMonitor.fire() 공개 인터페이스가 존재한다 (전략 DSL 확장용)
- [ ] action.route는 허용 경로 화이트리스트로 검증된다

## 7. 참고

- 엔진 루프: `local_server/engine/engine.py` — `evaluate_all()`
- 안전장치: `local_server/engine/safeguard.py`
- WS 브로드캐스트: `local_server/routers/ws.py`
- 프론트 알림 스토어: `frontend/src/hooks/useLocalBridgeWS.ts`
- OpsPanel: `frontend/src/components/main/OpsPanel.tsx`
