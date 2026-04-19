# 외부 주문 감지 — 구현 계획

> 작성일: 2026-03-12 | 상태: 보류 (GHOST 감지만 구현, 외부 주문 경고 미착수) | spec: `spec/external-order-detection/spec.md`
> 갱신일: 2026-03-15 | 선행 조건 해소 — 착수 가능

## 현황 (2026-03-15 점검)

기존 KIS Reconciler(`local_server/broker/kis/reconciler.py`)가 GHOST 감지를 이미 수행 중.
조용히 흡수하는 현재 동작을 **경고 + 정책 적용**으로 확장하면 됨.

### 추가로 필요한 작업
- GHOST 이벤트 → ExternalOrderEvent 변환 + 정책 적용
- 최초 기동 시 기존 주문 오탐 방지 (초기 스캔 → 기존 주문 등록)
- `_local_orders` 영속화 (재시작 대비)
- 키움 어댑터에도 Reconciler 추가

## 구현 단계 (개요)

### Step 1: ExternalOrderEvent 모델 정의

**파일**: `local_server/engine/trader_models.py`

```python
@dataclass
class ExternalOrderEvent:
    detected_at: datetime
    broker_order_id: str
    symbol: str
    side: Literal["BUY", "SELL"]
    qty: int
    price: Decimal
    status: str
    source: str = "UNKNOWN"
```

### Step 2: 기존 KIS Reconciler 확장

**파일**: `local_server/broker/kis/reconciler.py` (수정)

- GHOST 감지 시 조용히 흡수 → ExternalOrderEvent 발행으로 변경
- 최초 기동 플래그: 첫 `reconcile_once()` 실행 시 기존 주문 등록 (오탐지 방지)
- `_local_orders` 영속화: SQLite 또는 JSON 파일 (재시작 대비)
- 키움 어댑터에도 동일 Reconciler 연결

### Step 3: 외부 주문 감지 정책

**파일**: `local_server/engine/trader_policy.py`

```python
class ExternalOrderPolicy(str, Enum):
    WARN_ONLY = "WARN_ONLY"
    PAUSE_NEW = "PAUSE_NEW"
    HALT_ENGINE = "HALT_ENGINE"
```

사용자 설정에서 선택 가능. 기본값: WARN_ONLY.

### Step 4: System Trader에 정책 적용

**파일**: `local_server/engine/system_trader.py`

- PortfolioSnapshot.external_order_detected 플래그 반영
- PAUSE_NEW → REDUCING 유사 동작 (신규 BUY 차단)
- HALT_ENGINE → 엔진 정지 + ArmSession 해제

### Step 5: 프론트엔드 경고 UI

**파일**: `frontend/src/`

- OpsPanel에 외부 주문 경고 배너
- 알림 센터에 감지 이벤트 추가
- 설정에 정책 선택 드롭다운

### Step 6: 경고 해제 + 재동기화

- 사용자 "확인" → 경고 해제
- 현재 포트폴리오 스냅샷으로 재동기화

## 변경 파일 요약 (예상)

| 파일 | 변경 |
|------|------|
| `local_server/engine/trader_models.py` | ExternalOrderEvent 추가 |
| `local_server/broker/kis/reconciler.py` | 외부 주문 감지 로직 (기존 GHOST 확장) |
| `local_server/engine/trader_policy.py` | ExternalOrderPolicy enum |
| `local_server/engine/system_trader.py` | 정책 적용 |
| `local_server/routers/trading.py` | 경고 해제 API |
| `frontend/src/components/main/OpsPanel.tsx` | 경고 배너 |
| `frontend/src/pages/Settings.tsx` | 정책 설정 UI |
