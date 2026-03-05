# 규칙 데이터 모델 명세서 (rule-model)

> 작성일: 2026-03-06 | 상태: 초안 | Phase 3
>
> **의존**: `spec/strategy-engine/spec.md` (엔진이 규칙을 소비), `spec/cloud-server/spec.md` (규칙 CRUD/저장)

---

## 1. 목표

전략 엔진이 평가하는 **규칙(Rule)의 데이터 모델**을 정의한다.
매수/매도 분리, 조건 타입 확장, 트리거 정책을 포함한다.

**분리 사유**: 규칙 모델은 클라우드(저장/CRUD)와 로컬(평가/실행) 양쪽에 걸쳐 있어,
별도 spec으로 분리하여 양쪽이 동일한 모델을 참조하도록 한다.

---

## 2. 현재 모델의 한계

| 문제 | 설명 |
|------|------|
| 매수/매도 미분리 | `side` 필드 하나로 구분 → 하나의 규칙이 매수 또는 매도만 가능 |
| 조건 타입 제한 | `price`, `indicator`, `volume`, `context` 4종만 |
| 고정 수량 | `qty` 고정 → 비율 기반/금액 기반 불가 |
| 트리거 1회 제한 | `SignalManager`가 하루 1회만 허용 → 반복 매매 불가 |
| 우선순위 미활용 | `priority` 필드 존재하나 엔진에서 미사용 |

---

## 3. 규칙 모델 v1

### 3.1 규칙 구조

```
TradingRule
├── id, name, symbol, is_active
├── buy_conditions    # 매수 조건 블록
├── sell_conditions   # 매도 조건 블록 (선택)
├── execution         # 주문 설정
├── trigger_policy    # 트리거 정책
└── priority          # 평가 순서 (높을수록 먼저)
```

**매수/매도 분리:**
- 하나의 규칙이 매수 조건과 매도 조건을 각각 보유
- 매도 조건이 없으면 → 매수 전용 규칙 (수동 매도)
- 매수 조건이 없으면 → 매도 전용 규칙 (보유 종목 대상)
- 양쪽 모두 있으면 → 매수 후 매도 조건 감시 (짝 거래)

### 3.2 조건 블록

```json
{
  "operator": "AND",
  "conditions": [
    {
      "type": "price",
      "field": "current_price",
      "op": "<=",
      "value": 50000
    },
    {
      "type": "indicator",
      "field": "rsi_14",
      "op": "<=",
      "value": 30
    }
  ]
}
```

### 3.3 조건 타입 (v1)

| type | field 예시 | 설명 |
|------|-----------|------|
| `price` | `current_price` | 현재가 비교 |
| `indicator` | `rsi_14`, `ma_20`, `macd` | 기술적 지표 |
| `volume` | `volume`, `volume_ratio` | 거래량 |
| `context` | `market_kospi_rsi` | AI 컨텍스트 (v2) |

### 3.4 비교 연산자

| op | 의미 |
|----|------|
| `==` | 같음 |
| `!=` | 다름 |
| `>` | 초과 |
| `>=` | 이상 |
| `<` | 미만 |
| `<=` | 이하 |
| `cross_above` | 교차 상향 (직전 < value, 현재 >= value) |
| `cross_below` | 교차 하향 (직전 > value, 현재 <= value) |

> `cross_above`, `cross_below`는 직전 분봉 데이터 필요 → BarBuilder 연동

### 3.5 주문 설정 (execution)

```json
{
  "order_type": "MARKET",
  "qty_type": "FIXED",
  "qty_value": 10,
  "limit_price": null
}
```

| 필드 | 값 | 설명 |
|------|----|------|
| `order_type` | `MARKET`, `LIMIT` | 시장가/지정가 |
| `qty_type` | `FIXED` | 고정 수량 (v1) |
| `qty_value` | 정수 | 주문 수량 |
| `limit_price` | 숫자 or null | 지정가 주문 시 가격 |

### 3.6 트리거 정책 (trigger_policy)

```json
{
  "frequency": "ONCE_PER_DAY",
  "cooldown_minutes": null
}
```

| frequency | 설명 |
|-----------|------|
| `ONCE_PER_DAY` | 하루 1회 (v1 기본, 현재 동작과 동일) |
| `ONCE` | 1회 실행 후 규칙 비활성화 |

### 3.7 전체 JSON 예시

```json
{
  "id": 1,
  "name": "삼성전자 RSI 역행",
  "symbol": "005930",
  "is_active": true,
  "priority": 10,
  "buy_conditions": {
    "operator": "AND",
    "conditions": [
      { "type": "indicator", "field": "rsi_14", "op": "<=", "value": 30 },
      { "type": "price", "field": "current_price", "op": "<=", "value": 55000 }
    ]
  },
  "sell_conditions": {
    "operator": "OR",
    "conditions": [
      { "type": "indicator", "field": "rsi_14", "op": ">=", "value": 70 },
      { "type": "price", "field": "current_price", "op": ">=", "value": 65000 }
    ]
  },
  "execution": {
    "order_type": "MARKET",
    "qty_type": "FIXED",
    "qty_value": 10,
    "limit_price": null
  },
  "trigger_policy": {
    "frequency": "ONCE_PER_DAY",
    "cooldown_minutes": null
  }
}
```

---

## 4. 클라우드 DB 모델

```python
class TradingRule(Base):
    __tablename__ = "trading_rules"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    symbol = Column(String(10), nullable=False)

    # 조건 (JSON)
    buy_conditions = Column(JSON)     # 조건 블록 (operator + conditions[])
    sell_conditions = Column(JSON)    # 조건 블록 (선택)

    # 주문 설정 (JSON)
    execution = Column(JSON, nullable=False)  # { order_type, qty_type, qty_value, limit_price }

    # 트리거 정책 (JSON)
    trigger_policy = Column(JSON, nullable=False, default={"frequency": "ONCE_PER_DAY"})

    # 메타
    priority = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
```

> `cloud-server/spec.md` §5.2의 `TradingRule`을 대체한다.
> 기존 `max_position_count`, `budget_ratio`는 규칙 단위가 아닌 사용자 설정으로 이동.

---

## 5. 로컬 엔진 모델

```python
@dataclass
class RuleConfig:
    """규칙 JSON → 파싱 구조체."""

    id: int
    name: str
    symbol: str
    is_active: bool = True
    priority: int = 0

    buy_conditions: dict | None = None    # 조건 블록
    sell_conditions: dict | None = None   # 조건 블록

    execution: dict = field(default_factory=lambda: {
        "order_type": "MARKET", "qty_type": "FIXED", "qty_value": 1
    })
    trigger_policy: dict = field(default_factory=lambda: {
        "frequency": "ONCE_PER_DAY"
    })
```

> `local_server/engine/models.py`의 기존 `RuleConfig`를 대체한다.
> 기존 `side`, `operator`, `conditions`, `qty`, `order_type`, `limit_price` 필드는
> `buy_conditions`, `sell_conditions`, `execution` 구조로 통합.

---

## 6. 엔진 평가 로직 변경

### 6.1 매수/매도 분리 평가

```
매 1분:
  for rule in rules (priority 내림차순):
    if rule.buy_conditions and not 이미_보유(rule.symbol):
      → buy_conditions 평가 → True면 매수 주문
    if rule.sell_conditions and 이미_보유(rule.symbol):
      → sell_conditions 평가 → True면 매도 주문
```

- **보유 여부**: 당일 체결 로그(logs.db) + 엔진 내 메모리 상태로 판단
- 매수 후 같은 규칙의 매도 조건이 즉시 감시 시작
- 매도 전용 규칙: 사용자가 수동으로 보유한 종목에도 적용 가능

### 6.2 cross_above / cross_below

```python
def _eval_cross(self, field, op, value, current, previous):
    if op == "cross_above":
        return previous.get(field, 0) < value and current.get(field, 0) >= value
    if op == "cross_below":
        return previous.get(field, 0) > value and current.get(field, 0) <= value
```

- `previous`: 직전 분봉 데이터 (BarBuilder에서 제공)
- 분봉 2개 이상 축적 후 사용 가능

---

## 7. 사용자 전역 설정 (규칙 밖)

규칙 단위가 아닌 사용자 단위 설정:

| 설정 | 기본값 | 설명 |
|------|--------|------|
| `max_position_count` | 5 | 동시 보유 최대 종목 수 |
| `budget_ratio` | 0.2 | 1회 주문 최대 예산 비율 |
| `daily_loss_limit` | 사용자 정의 | 당일 최대 손실 (원) |
| `order_rate_limit` | 10 | 분당 최대 주문 수 |

> 이 설정들은 `local_server/config/settings.json`에 저장하며,
> 클라우드에도 동기화한다 (사용자 설정 sync).

---

## 8. v2 확장 계획

| 항목 | 설명 |
|------|------|
| `qty_type: "RATIO"` | 예산 비율 기반 수량 계산 (잔고 조회 필요) |
| `qty_type: "AMOUNT"` | 금액 기반 수량 계산 |
| `frequency: "COOLDOWN"` | N분 쿨다운 후 재실행 |
| `frequency: "UNLIMITED"` | 조건 충족 시 매번 실행 |
| 조건 그룹 중첩 | `(A AND B) OR (C AND D)` 형태 |
| `context` 조건 타입 | AI 컨텍스트 필드 참조 |
| `custom_formula` | 사용자 정의 수식 (안전한 파서 필요) |
| 규칙 체이닝 | 규칙 A 체결 → 규칙 B 활성화 |
| 시간 조건 | 특정 시간대만 활성화 (e.g., 09:30~10:00) |
| 손절/익절 | `sell_conditions`에 수익률 기반 조건 추가 |

---

## 9. 수용 기준

### 9.1 데이터 모델

- [ ] 매수 조건만 있는 규칙 생성/저장/조회
- [ ] 매도 조건만 있는 규칙 생성/저장/조회
- [ ] 매수+매도 모두 있는 규칙 생성/저장/조회
- [ ] `cross_above`, `cross_below` 연산자 포함 조건 저장

### 9.2 엔진 평가

- [ ] 매수 조건 충족 + 미보유 → 매수 주문
- [ ] 매도 조건 충족 + 보유 중 → 매도 주문
- [ ] 보유 중 매수 조건 충족 → 스킵 (중복 매수 방지)
- [ ] 미보유 매도 조건 충족 → 스킵
- [ ] `ONCE` 트리거 → 1회 실행 후 `is_active=false`

### 9.3 호환성

- [ ] 클라우드 DB 모델과 로컬 JSON 캐시 스키마 일치
- [ ] 기존 `side` 기반 규칙 → 새 모델로 마이그레이션 가능

---

## 10. 범위

### 포함

- 규칙 JSON 스키마 정의
- 클라우드 DB 모델 (TradingRule)
- 로컬 엔진 모델 (RuleConfig)
- 조건 타입/연산자 정의
- 트리거 정책 정의
- 매수/매도 분리 평가 로직 명세

### 미포함

- 프론트엔드 규칙 빌더 UI (Unit 5)
- 백테스팅 (v2)
- 규칙 체이닝 (v2)
- 커뮤니티 규칙 공유 (v2)

---

## 참고

- `spec/strategy-engine/spec.md` §4.2 (조건 평가)
- `spec/cloud-server/spec.md` §5 (규칙 API)
- `local_server/engine/models.py` (현재 RuleConfig)
- `docs/architecture.md` §4.4 (로컬 서버)

---

**마지막 갱신**: 2026-03-06
