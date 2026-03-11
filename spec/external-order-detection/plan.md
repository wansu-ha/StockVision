# 외부 주문 감지 — 구현 계획

> 작성일: 2026-03-12 | 상태: 초안 | spec: `spec/external-order-detection/spec.md`
> **구현 보류**: System Trader Phase 3 (reconciler) 구현 후 착수

## 선행 작업

1. System Trader Phase 3 — `reconciler.py` 구현
   - 브로커 open order / fill 이벤트와 IntentStore 재조정
   - `REDUCING` 모드 도입
2. IntentStore 영속화 (현재 메모리 → SQLite 또는 log_db 연동)

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

### Step 2: Reconciler에 외부 주문 감지 로직 추가

**파일**: `local_server/engine/reconciler.py`

- 브로커 open orders 조회
- IntentStore + "기존 주문" 목록과 대조
- 매칭 안 되는 주문 → ExternalOrderEvent 발행
- 최초 기동 시: 모든 기존 주문 등록 (오탐지 방지)

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
| `local_server/engine/reconciler.py` | 외부 주문 감지 로직 |
| `local_server/engine/trader_policy.py` | ExternalOrderPolicy enum |
| `local_server/engine/system_trader.py` | 정책 적용 |
| `local_server/routers/trading.py` | 경고 해제 API |
| `frontend/src/components/main/OpsPanel.tsx` | 경고 배너 |
| `frontend/src/pages/Settings.tsx` | 정책 설정 UI |
