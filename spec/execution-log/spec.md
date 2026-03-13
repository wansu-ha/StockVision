# 실행 로그 명세서 (execution-log)

> 작성일: 2026-03-04 | 상태: **→ Unit 5 (frontend)에 통합**
>
> 이 spec의 내용은 `spec/frontend/`에서 통합 구현합니다.

---

## 1. 개요

### 1.1 목표

StockVision 시스템에서 **자동매매 규칙이 실행될 때마다 상세한 로그를 기록하고, 사용자가 웹 UI에서 투명하게 조회할 수 있는 시스템**을 구축한다.

실행 로그는 다음 세 가지 목적을 동시에 충족한다:
1. **투명성**: 어떤 조건이 충족되어 어떤 주문이 실행됐는지 명확히 보여주기
2. **법적 근거**: "투자판단 = 사용자의 사전 정의된 규칙"을 로그로 증명
3. **디버깅**: 전략이 예상대로 작동하는지 확인하고, 실패 원인 추적

### 1.2 핵심 개념

- **실행**: 자동매매 규칙의 조건이 충족되어 매수/매도 신호가 발동하는 순간
- **로그 항목**: 한 번의 실행에 대한 스냅샷 (규칙 ID, 시각, 조건, 결과 등)
- **실행 로그**: 모든 실행 항목의 시계열 기록 (월별, 일별, 규칙별 조회 가능)

### 1.3 법적 포지션

StockVision은 **시스템매매 서비스**로 분류된다:
- 사용자가 **사전에 정의한 규칙**(자동매매 규칙)을 시스템이 실행
- **투자 판단의 주체 = 사용자** (시스템은 도구)
- 실행 로그는 이를 증명하는 기술적 근거

따라서 실행 로그는:
- 규칙의 모든 조건을 기록 (조건 문자열, 임계값 등)
- 조건 충족 여부를 기록 (TRUE/FALSE)
- 사용된 시점의 시장 데이터를 기록 (가격, 지표값 등)
- 최종 거래 결과를 기록 (체결 여부, 체결가, 수량 등)

---

## 2. 로그 데이터 구조

### 2.1 ExecutionLog 데이터 모델

```python
class ExecutionLog(Base):
    """
    실행 로그: 자동매매 규칙 실행 기록

    한 번의 매수/매도 신호 발동부터 거래 완료(또는 실패)까지의 전과정을 기록.
    """
    __tablename__ = "execution_logs"

    # 기본 ID
    id = Column(Integer, primary_key=True, index=True)

    # 규칙 & 계좌 정보
    rule_id = Column(Integer, ForeignKey("auto_trading_rules.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("virtual_accounts.id"), nullable=False)
    symbol = Column(String(10), nullable=False)  # "005930" (삼성전자)

    # 신호 메타데이터
    signal_id = Column(String(50), unique=True, nullable=False)  # "sig_20260304_001"
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)  # 신호 발동 시각

    # 거래 방향
    side = Column(String(10), nullable=False)  # "BUY" or "SELL"

    # === 조건 평가 결과 ===
    buy_conditions_met = Column(Boolean)  # 매수 조건 충족 여부 (side=BUY일 때)
    sell_conditions_met = Column(Boolean) # 매도 조건 충족 여부 (side=SELL일 때)

    # 조건식 원문 (투명성을 위해 저장)
    conditions_json = Column(JSON, nullable=False)
    # 예:
    # {
    #   "buy_conditions": [
    #     {"type": "rsi_14", "operator": "<", "value": 30, "current_value": 28},
    #     {"type": "volume_ratio", "operator": ">", "value": 2.0, "current_value": 2.1}
    #   ],
    #   "operator": "AND"
    # }

    # === 트리거된 조건들 (상세) ===
    triggered_conditions = Column(JSON)  # 실제로 충족된 조건들만 필터링
    # 예:
    # [
    #   {"index": 0, "condition": "RSI(14) < 30", "actual_value": 28, "met": true},
    #   {"index": 1, "condition": "거래량배수 > 2.0", "actual_value": 2.1, "met": true}
    # ]

    # === 실행 시점의 시장 스냅샷 ===
    market_snapshot = Column(JSON, nullable=False)
    # 예:
    # {
    #   "current_price": 59800,
    #   "rsi_14": 28,
    #   "ema_20": 59500,
    #   "macd": 250,
    #   "volume": 1200000,
    #   "volume_sma_20": 900000,
    #   "volume_ratio": 2.1,
    #   "bid": 59700,
    #   "ask": 59900,
    #   "timestamp": "2026-03-04T10:30:00Z"
    # }

    # === 거래 실행 정보 ===
    order_quantity = Column(Integer, nullable=False)  # 주문 수량
    order_type = Column(String(20))  # "MARKET", "LIMIT"
    order_price = Column(Float)  # 지정가 주문 시만 기입

    # === 거래 결과 ===
    status = Column(String(20), nullable=False)  # "PENDING", "EXECUTED", "PARTIAL", "FAILED", "CANCELLED"
    filled_quantity = Column(Integer)  # 체결 수량
    filled_price = Column(Float)  # 체결가
    filled_amount = Column(Float)  # 체결 금액 (filled_quantity × filled_price)

    # === 거래 수수료 & 세금 ===
    commission = Column(Float, default=0.0)  # 수수료 (원화)
    tax = Column(Float, default=0.0)  # 세금 (원화, 매도 시만)
    net_amount = Column(Float)  # 순거래금액 (filled_amount - commission - tax)

    # === 손익 정보 ===
    realized_pnl = Column(Float)  # 실현 손익 (매도 시에만 기입)
    realized_pnl_rate = Column(Float)  # 실현 수익률 (%)

    # === 거래소 응답 ===
    broker_order_id = Column(String(50))  # 거래소 주문 ID (키움증권 반환값)
    broker_order_status = Column(String(50))  # 거래소 주문 상태

    # === 에러 처리 ===
    error_code = Column(String(50))  # 에러 코드 (K001, K002 등)
    error_message = Column(String(500))  # 에러 메시지

    # === 메타데이터 ===
    rule_name = Column(String(100))  # 규칙명 (조회 편의)
    strategy_version = Column(Integer)  # 규칙 버전 (수정 이력 추적)
    bridge_id = Column(String(50), default="primary")  # 로컬 브릿지 ID
    retry_count = Column(Integer, default=0)  # 재시도 횟수

    # === 타임스탬프 ===
    created_at = Column(DateTime, default=datetime.utcnow)  # 로그 기록 시각
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    response_timestamp = Column(DateTime)  # 거래소 응답 시각

    __table_args__ = (
        Index('idx_rule_timestamp', 'rule_id', 'timestamp'),
        Index('idx_account_date', 'account_id', 'created_at'),
        Index('idx_symbol_side', 'symbol', 'side'),
        Index('idx_status', 'status'),
    )
```

### 2.2 데이터 레코드 예시

#### 예시 1: 매수 신호 성공

```json
{
  "id": 1,
  "rule_id": 42,
  "account_id": 1,
  "symbol": "005930",
  "signal_id": "sig_20260304_001",
  "timestamp": "2026-03-04T10:30:00Z",
  "side": "BUY",
  "buy_conditions_met": true,
  "sell_conditions_met": null,
  "conditions_json": {
    "buy_conditions": [
      {
        "type": "indicator",
        "field": "rsi_14",
        "operator": "<",
        "value": 30,
        "current_value": 28
      },
      {
        "type": "volume",
        "field": "volume_ratio",
        "operator": ">",
        "value": 2.0,
        "current_value": 2.1
      }
    ],
    "operator": "AND"
  },
  "triggered_conditions": [
    {
      "index": 0,
      "description": "RSI(14) < 30",
      "actual_value": 28,
      "met": true
    },
    {
      "index": 1,
      "description": "거래량배수 > 2.0",
      "actual_value": 2.1,
      "met": true
    }
  ],
  "market_snapshot": {
    "current_price": 59800,
    "rsi_14": 28,
    "ema_20": 59500,
    "macd": 250,
    "volume": 1200000,
    "volume_sma_20": 900000,
    "bid": 59700,
    "ask": 59900,
    "timestamp": "2026-03-04T10:30:00Z"
  },
  "order_quantity": 10,
  "order_type": "MARKET",
  "order_price": null,
  "status": "EXECUTED",
  "filled_quantity": 10,
  "filled_price": 59800,
  "filled_amount": 598000,
  "commission": 89.7,
  "tax": 0,
  "net_amount": 597910.3,
  "realized_pnl": null,
  "realized_pnl_rate": null,
  "broker_order_id": "10000123",
  "broker_order_status": "COMPLETED",
  "error_code": null,
  "error_message": null,
  "rule_name": "RSI-Volume Breakout",
  "strategy_version": 1,
  "bridge_id": "primary",
  "retry_count": 0,
  "created_at": "2026-03-04T10:30:00Z",
  "updated_at": "2026-03-04T10:30:15Z",
  "response_timestamp": "2026-03-04T10:30:15Z"
}
```

#### 예시 2: 매도 신호 성공 + 손익 계산

```json
{
  "id": 2,
  "rule_id": 42,
  "account_id": 1,
  "symbol": "005930",
  "signal_id": "sig_20260305_001",
  "timestamp": "2026-03-05T14:00:00Z",
  "side": "SELL",
  "buy_conditions_met": null,
  "sell_conditions_met": true,
  "conditions_json": {
    "sell_conditions": [
      {
        "type": "profit_rate",
        "field": "profit_rate",
        "operator": ">=",
        "value": 5.0,
        "current_value": 5.3
      }
    ]
  },
  "triggered_conditions": [
    {
      "index": 0,
      "description": "수익률 >= +5%",
      "actual_value": 5.3,
      "met": true
    }
  ],
  "market_snapshot": {
    "current_price": 62965,
    "rsi_14": 55,
    "ema_20": 61500,
    "macd": 450,
    "volume": 900000,
    "volume_sma_20": 900000,
    "bid": 62960,
    "ask": 62970,
    "timestamp": "2026-03-05T14:00:00Z"
  },
  "order_quantity": 10,
  "order_type": "MARKET",
  "order_price": null,
  "status": "EXECUTED",
  "filled_quantity": 10,
  "filled_price": 62965,
  "filled_amount": 629650,
  "commission": 94.45,
  "tax": 1448.99,
  "net_amount": 628106.56,
  "realized_pnl": 30196.56,
  "realized_pnl_rate": 5.06,
  "broker_order_id": "10000456",
  "broker_order_status": "COMPLETED",
  "error_code": null,
  "error_message": null,
  "rule_name": "RSI-Volume Breakout",
  "strategy_version": 1,
  "bridge_id": "primary",
  "retry_count": 0,
  "created_at": "2026-03-05T14:00:00Z",
  "updated_at": "2026-03-05T14:00:20Z",
  "response_timestamp": "2026-03-05T14:00:20Z"
}
```

#### 예시 3: 매수 신호 실패 (충분한 자금 없음)

```json
{
  "id": 3,
  "rule_id": 42,
  "account_id": 1,
  "symbol": "000660",
  "signal_id": "sig_20260304_002",
  "timestamp": "2026-03-04T11:00:00Z",
  "side": "BUY",
  "buy_conditions_met": true,
  "sell_conditions_met": null,
  "conditions_json": { /* ... */ },
  "triggered_conditions": [ /* ... */ ],
  "market_snapshot": { /* ... */ },
  "order_quantity": 5,
  "order_type": "MARKET",
  "order_price": null,
  "status": "FAILED",
  "filled_quantity": 0,
  "filled_price": null,
  "filled_amount": null,
  "commission": 0,
  "tax": 0,
  "net_amount": null,
  "realized_pnl": null,
  "realized_pnl_rate": null,
  "broker_order_id": null,
  "broker_order_status": null,
  "error_code": "INSUFFICIENT_FUNDS",
  "error_message": "계좌 잔고 부족: 필요 300,000원 > 보유 50,000원",
  "rule_name": "RSI-Volume Breakout",
  "strategy_version": 1,
  "bridge_id": "primary",
  "retry_count": 0,
  "created_at": "2026-03-04T11:00:00Z",
  "updated_at": "2026-03-04T11:00:05Z",
  "response_timestamp": null
}
```

---

## 3. 화면 구성 (필터, 검색, 정렬)

### 3.1 실행 로그 페이지 레이아웃

```
┌─────────────────────────────────────────────────────────────────┐
│ Execution Logs (실행 로그)                                       │
├─────────────────────────────────────────────────────────────────┤
│ [필터 & 검색]                                                    │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │ 규칙: [RSI-Volume ▼]                                       │ │
│ │ 계좌: [All ▼]                                              │ │
│ │ 상태: [All ▼] [성공] [실패] [부분체결]                     │ │
│ │ 거래유형: [All ▼] [매수] [매도]                            │ │
│ │ 기간: [지난 7일 ▼] [Custom: 2026-02-24 ~ 2026-03-04]    │ │
│ │ 종목 검색: [______]                                       │ │
│ │ [적용] [초기화]                                           │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│ [정렬: 최신순▼] [보기: 확장▼] [내보내기▼]                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│ 2026-03-05 | RSI-Volume | 삼성전자 (005930) | 매도 | EXECUTED   │
│   신호: sig_20260305_001 | 수익률: +5.06%                       │
│   조건: 수익률 >= +5%                                            │
│   체결: 10주 × 62,965원 = 629,650원 | 순이익: 30,196.56원      │
│   [상세보기▼]                                                     │
│                                                                   │
│ 2026-03-04 | RSI-Volume | 삼성전자 (005930) | 매수 | EXECUTED   │
│   신호: sig_20260304_001                                        │
│   조건: RSI < 30 (28) AND 거래량배수 > 2.0 (2.1)                │
│   체결: 10주 × 59,800원 = 598,000원                             │
│   [상세보기▼]                                                     │
│                                                                   │
│ 2026-03-04 | RSI-Volume | SK하이닉스 (000660) | 매수 | FAILED   │
│   신호: sig_20260304_002                                        │
│   오류: INSUFFICIENT_FUNDS (계좌 잔고 부족)                     │
│   [상세보기▼]                                                     │
│                                                                   │
│ [◀ 이전] [1] [2] [3] [다음 ▶]                                    │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 상세보기 (모달 또는 펼침)

```
┌─────────────────────────────────────────────────────────────────┐
│ 실행 로그 상세 — sig_20260305_001                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│ [기본 정보]                                                       │
│ ├─ 신호 ID: sig_20260305_001                                    │
│ ├─ 규칙명: RSI-Volume Breakout (v1)                            │
│ ├─ 계좌: 가상계좌 #1 (잔고: 7,000,000원)                        │
│ ├─ 거래 시간: 2026-03-05 14:00:00 (응답: 14:00:20)           │
│ └─ 상태: ✓ EXECUTED (정상 완료)                                 │
│                                                                   │
│ [조건식 평가]                                                     │
│ ├─ 매도 조건: 수익률 >= +5%                                     │
│ │  ✓ 조건 충족: YES (현재 수익률 5.3%)                          │
│ ├─ 이전 매수가: 59,800원 (2026-03-04)                         │
│ └─ 현재가: 62,965원                                            │
│                                                                   │
│ [실행 시점 시장 정보]                                             │
│ ├─ 종목: 삼성전자 (005930)                                      │
│ ├─ 시가: 62,500원                                              │
│ ├─ 현재가: 62,965원 (▲465원, +0.74%)                          │
│ ├─ 호가: 62,960 / 62,970 (실시간)                             │
│ ├─ 거래량: 900,000주 (평균: 900,000주) — 거래량배수: 1.0      │
│ ├─ RSI(14): 55 | EMA(20): 61,500원 | MACD: 450               │
│ └─ 수집시각: 2026-03-05 13:59:50Z                             │
│                                                                   │
│ [주문 정보]                                                       │
│ ├─ 거래 종류: SELL (매도)                                       │
│ ├─ 주문 유형: MARKET (시장가)                                   │
│ ├─ 주문 수량: 10주                                              │
│ ├─ 주문 시각: 2026-03-05 14:00:00                             │
│ └─ 거래소 주문 ID: 10000456                                     │
│                                                                   │
│ [체결 결과]                                                       │
│ ├─ 체결 수량: 10주 ✓ (100% 체결)                                │
│ ├─ 체결가: 62,965원 (시가대비 +0.74%)                          │
│ ├─ 체결 금액: 629,650원                                        │
│ ├─ 수수료: 94.45원 (0.015%)                                    │
│ ├─ 세금: 1,448.99원 (0.23%)                                    │
│ └─ 순 거래액: 628,106.56원                                     │
│                                                                   │
│ [손익 계산]                                                       │
│ ├─ 매수가 (평균): 59,800원                                      │
│ ├─ 매도가: 62,965원                                            │
│ ├─ 기간: 1일                                                    │
│ ├─ 실현 손익: +30,196.56원                                     │
│ ├─ 실현 수익률: +5.06%                                         │
│ └─ 연 환산 수익률: +1,847% (참고용)                             │
│                                                                   │
│ [거래소 응답]                                                     │
│ ├─ 응답 상태: 성공                                              │
│ ├─ 응답 시각: 2026-03-05 14:00:15Z                            │
│ ├─ API 응답 시간: 200ms                                        │
│ └─ 키움 API 호출 횟수: 1회 (한도 5,000/1일 중 남은 횟수: 4999) │
│                                                                   │
│ [기타]                                                           │
│ └─ 브릿지: primary (정상)                                      │
│                                                                   │
│ [액션]                                                           │
│ [복사] [내보내기 (JSON/CSV)] [닫기]                              │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 필터 & 검색 옵션

| 필터명 | 타입 | 옵션 | 설명 |
|--------|------|------|------|
| **규칙** | Select | [All], 규칙 목록 | 자동매매 규칙별 필터 |
| **계좌** | Select | [All], 계좌 목록 | 가상계좌별 필터 |
| **상태** | Checkbox | EXECUTED, FAILED, PARTIAL, CANCELLED | 거래 성공/실패 여부 |
| **거래유형** | Radio | All, BUY, SELL | 매수/매도 구분 |
| **기간** | DateRange | "지난 7일", "이번 달", "Custom" | 조회 기간 |
| **종목** | Text | 자유 입력 | 종목명 또는 코드 검색 |
| **수익률** | Range | Min ~ Max (%) | 수익률 범위 필터 (매도만) |
| **체결 금액** | Range | Min ~ Max (원) | 거래액 범위 필터 |

### 3.4 정렬 옵션

- **최신순** (기본): timestamp DESC
- **오래된순**: timestamp ASC
- **수익률높음**: realized_pnl_rate DESC (매도만)
- **거래액큼**: filled_amount DESC
- **규칙명**: rule_name ASC

### 3.5 내보내기

- **CSV**: 기본 정보 + 조건 + 시장데이터 + 결과
- **JSON**: 전체 레코드 원본
- **PDF**: 요약 보고서 (시간대별 집계, 차트 포함)

---

## 4. 트리거 조건 시각화

### 4.1 조건 평가 과정 시각화

```
┌──────────────────────────────────────────────────────┐
│ 규칙: RSI-Volume Breakout                              │
│ 매도 조건: (수익률 >= +5%) OR (손실 <= -3%)            │
└──────────────────────────────────────────────────────┘
            ↓
┌──────────────────────────────────────────────────────┐
│ 실행 시점 시장 데이터 (2026-03-05 14:00:00)            │
│                                                       │
│ 종목: 삼성전자 (005930)                               │
│ 매입가: 59,800원 | 현재가: 62,965원                   │
│ 수익률: (62,965 - 59,800) / 59,800 × 100 = +5.30%  │
│ 손실: -2.15% (경우 가정)                             │
└──────────────────────────────────────────────────────┘
            ↓
┌──────────────────────────────────────────────────────┐
│ 조건식 평가                                            │
│                                                       │
│ 조건 1: 수익률 >= +5%                                 │
│        ✓ TRUE (실제: +5.30%)                         │
│                                                       │
│ 조건 2: 손실 <= -3%                                   │
│        ✗ FALSE (실제: -2.15%)                        │
│                                                       │
│ 결합 연산자: OR                                        │
│ ✓ 결과: TRUE (조건 1 만족)                            │
└──────────────────────────────────────────────────────┘
            ↓
┌──────────────────────────────────────────────────────┐
│ ✓ 신호 발동!                                          │
│ → 매도 신호 전송 → 거래 실행 → ExecutionLog 기록     │
└──────────────────────────────────────────────────────┘
```

### 4.2 복합 조건식 예시 (UI 표현)

```
매수 조건:
┌────────────────────────────────────────────┐
│ AND                                         │
├─┬──────────────────────────────────────────┤
│ │ ◆ RSI(14) < 30                           │
│ │   현재: 28 ✓ 충족                        │
│ │   [평가: TRUE]                           │
├─┤ AND                                      │
│ │ ◆ 거래량배수 > 2.0                       │
│ │   현재: 2.1 ✓ 충족                       │
│ │   [평가: TRUE]                           │
├─┤ AND                                      │
│ │ ◆ 시장_변동성 < 25                       │
│ │   현재: 18.5 ✓ 충족                      │
│ │   [평가: TRUE]                           │
└─┴──────────────────────────────────────────┘
  → 모두 TRUE → 조건식 평가: ✓ TRUE

매도 조건:
┌────────────────────────────────────────────┐
│ OR                                          │
├─┬──────────────────────────────────────────┤
│ │ ◆ 수익률 > +5%                           │
│ │   현재: +5.3% ✓ 충족                     │
│ │   [평가: TRUE]                           │
├─┤ OR                                       │
│ │ ◆ 손실 < -3%                             │
│ │   현재: -2.15% ✗ 미충족                  │
│ │   [평가: FALSE]                          │
└─┴──────────────────────────────────────────┘
  → 하나라도 TRUE → 조건식 평가: ✓ TRUE
```

---

## 5. 기술 요구사항

### 5.1 데이터베이스

**테이블**: `execution_logs`
- 파티셔닝 전략: 월별 (created_at 기준)
- 보관 기간: 3년
- 인덱스: rule_id, account_id, status, timestamp

```sql
-- 마이그레이션 예
CREATE TABLE execution_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    rule_id INT NOT NULL,
    account_id INT NOT NULL,
    symbol VARCHAR(10) NOT NULL,
    signal_id VARCHAR(50) UNIQUE NOT NULL,
    timestamp DATETIME NOT NULL,
    side VARCHAR(10) NOT NULL,
    status VARCHAR(20) NOT NULL,
    conditions_json JSON NOT NULL,
    market_snapshot JSON NOT NULL,
    filled_quantity INT,
    filled_price DECIMAL(10,2),
    realized_pnl DECIMAL(15,2),
    realized_pnl_rate DECIMAL(5,2),
    error_message VARCHAR(500),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (rule_id) REFERENCES auto_trading_rules(id),
    FOREIGN KEY (account_id) REFERENCES virtual_accounts(id),

    INDEX idx_rule_timestamp (rule_id, timestamp),
    INDEX idx_account_date (account_id, created_at),
    INDEX idx_status (status)
);
```

### 5.2 API 엔드포인트

#### 5.2.1 로그 조회

```http
GET /api/v1/execution/logs
  Query Parameters:
    - rule_id: int (옵션)
    - account_id: int (옵션)
    - status: string (옵션, 쉼표 구분: "EXECUTED,FAILED")
    - side: string (옵션, "BUY" or "SELL")
    - from_date: date (옵션, YYYY-MM-DD)
    - to_date: date (옵션, YYYY-MM-DD)
    - symbol: string (옵션, 검색)
    - sort_by: string (옵션, "timestamp", "realized_pnl_rate")
    - sort_order: string ("asc" or "desc")
    - limit: int (default: 50, max: 500)
    - offset: int (default: 0)

  Response:
  {
    "success": true,
    "data": [
      {
        "id": 1,
        "signal_id": "sig_20260305_001",
        "rule_name": "RSI-Volume Breakout",
        "symbol": "005930",
        "timestamp": "2026-03-05T14:00:00Z",
        "side": "SELL",
        "status": "EXECUTED",
        "filled_quantity": 10,
        "filled_price": 62965,
        "realized_pnl": 30196.56,
        "realized_pnl_rate": 5.06
      },
      ...
    ],
    "count": 150,
    "total": 500
  }
```

#### 5.2.2 로그 상세 조회

```http
GET /api/v1/execution/logs/{signal_id}

  Response:
  {
    "success": true,
    "data": {
      "id": 1,
      "signal_id": "sig_20260305_001",
      "rule_id": 42,
      "account_id": 1,
      "symbol": "005930",
      "timestamp": "2026-03-05T14:00:00Z",
      "side": "SELL",
      "buy_conditions_met": null,
      "sell_conditions_met": true,
      "conditions_json": { /* ... */ },
      "triggered_conditions": [ /* ... */ ],
      "market_snapshot": { /* ... */ },
      "status": "EXECUTED",
      "filled_quantity": 10,
      "filled_price": 62965,
      "filled_amount": 629650,
      "commission": 94.45,
      "tax": 1448.99,
      "net_amount": 628106.56,
      "realized_pnl": 30196.56,
      "realized_pnl_rate": 5.06,
      "broker_order_id": "10000456",
      "error_code": null,
      "error_message": null,
      "created_at": "2026-03-05T14:00:00Z",
      "updated_at": "2026-03-05T14:00:20Z",
      "response_timestamp": "2026-03-05T14:00:20Z"
    }
  }
```

#### 5.2.3 규칙별 통계

```http
GET /api/v1/execution/stats?rule_id={id}&from_date={date}&to_date={date}

  Response:
  {
    "success": true,
    "data": {
      "rule_id": 42,
      "rule_name": "RSI-Volume Breakout",
      "period": {
        "from": "2026-02-04",
        "to": "2026-03-05"
      },
      "summary": {
        "total_executions": 15,
        "successful_executions": 14,
        "failed_executions": 1,
        "success_rate": 93.33,
        "buy_count": 8,
        "sell_count": 7
      },
      "profit_loss": {
        "total_realized_pnl": 152845.30,
        "total_realized_pnl_rate": 6.82,
        "best_trade": {
          "realized_pnl": 45000,
          "realized_pnl_rate": 8.5
        },
        "worst_trade": {
          "realized_pnl": -5000,
          "realized_pnl_rate": -1.2
        }
      },
      "trading_stats": {
        "avg_holding_period_days": 1.2,
        "win_rate": 78.6,
        "avg_win": 12500,
        "avg_loss": -3500
      }
    }
  }
```

#### 5.2.4 내보내기

```http
GET /api/v1/execution/logs/export?format={csv|json|pdf}&rule_id={id}&from_date={date}&to_date={date}

  Response:
  - Content-Type: application/csv (또는 application/json, application/pdf)
  - Content-Disposition: attachment; filename="execution_logs_20260304.csv"
  - Body: CSV/JSON/PDF 데이터
```

### 5.3 백엔드 서비스 (신규/확장)

#### 5.3.1 ExecutionLogService

```python
# 위치: backend/app/services/execution_log_service.py (신규)

class ExecutionLogService:
    """실행 로그 관리"""

    def create_log(
        self,
        rule_id: int,
        account_id: int,
        symbol: str,
        signal_id: str,
        side: str,
        conditions_met: bool,
        conditions_json: dict,
        market_snapshot: dict,
        order_quantity: int,
        order_type: str,
        order_price: float = None,
    ) -> ExecutionLog:
        """신호 발동 시 로그 생성 (PENDING 상태)"""
        ...

    def update_with_execution_result(
        self,
        signal_id: str,
        status: str,
        filled_quantity: int,
        filled_price: float,
        broker_order_id: str,
        error_code: str = None,
        error_message: str = None,
    ) -> ExecutionLog:
        """거래소 응답 후 로그 업데이트"""
        ...

    def calculate_pnl(
        self,
        sell_log: ExecutionLog,
        buy_log: ExecutionLog
    ) -> tuple[float, float]:
        """손익 계산 (매도 시)"""
        realized_pnl = sell_log.net_amount - buy_log.net_amount
        realized_pnl_rate = (realized_pnl / buy_log.net_amount) * 100
        return realized_pnl, realized_pnl_rate

    def get_logs(
        self,
        rule_id: int = None,
        account_id: int = None,
        status: list[str] = None,
        from_date: date = None,
        to_date: date = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ExecutionLog]:
        """필터 조건에 따른 로그 조회"""
        ...

    def get_rule_stats(
        self,
        rule_id: int,
        from_date: date,
        to_date: date,
    ) -> dict:
        """규칙별 통계 계산"""
        ...
```

#### 5.3.2 Execution Engine과의 통합

```python
# backend/app/services/execution_engine.py (기존) — 확장

async def execute_rule_safe(rule: AutoTradingRule):
    """규칙 실행 (로깅 포함)"""

    try:
        # ... 기존 로직 ...

        # 신호 생성
        signal = create_execution_signal(rule)

        # ★ 로그 생성 (PENDING 상태)
        log = execution_log_service.create_log(
            rule_id=rule.id,
            account_id=rule.account_id,
            symbol=rule.symbol,
            signal_id=signal.signal_id,
            side=signal.side,
            conditions_met=conditions_met,
            conditions_json=rule.buy_conditions if conditions_met else {},
            market_snapshot=current_market_data,
            order_quantity=order_quantity,
            order_type="MARKET",
        )

        # 신호 전송
        response = await send_signal_to_bridge(signal)

        # ★ 로그 업데이트 (응답 결과 반영)
        execution_log_service.update_with_execution_result(
            signal_id=signal.signal_id,
            status="EXECUTED" if response.success else "FAILED",
            filled_quantity=response.filled_quantity,
            filled_price=response.filled_price,
            broker_order_id=response.order_id,
            error_code=response.error_code if not response.success else None,
            error_message=response.error_message if not response.success else None,
        )

    except Exception as e:
        logger.error(f"Rule execution error: {e}")
        # 로그에 에러 기록
        execution_log_service.update_with_execution_result(
            signal_id=signal.signal_id,
            status="FAILED",
            filled_quantity=0,
            filled_price=None,
            broker_order_id=None,
            error_code="SYSTEM_ERROR",
            error_message=str(e),
        )
```

### 5.4 프론트엔드 구현

#### 5.4.1 컴포넌트 구조

```
frontend/src/pages/ExecutionLog.tsx
  ├── ExecutionLogTable.tsx (목록 테이블)
  │   ├── FilterBar.tsx (필터 & 검색)
  │   ├── LogRow.tsx (개별 행)
  │   └── Pagination.tsx (페이지네이션)
  ├── ExecutionLogDetail.tsx (상세보기 모달)
  │   ├── BasicInfo.tsx
  │   ├── ConditionEvaluation.tsx (조건식 평가 시각화)
  │   ├── MarketSnapshot.tsx
  │   ├── OrderInfo.tsx
  │   └── ProfitLossDisplay.tsx
  └── ExecutionLogStats.tsx (통계 차트)
```

#### 5.4.2 필터 상태 관리

```typescript
interface ExecutionLogFilters {
  ruleId?: number;
  accountId?: number;
  status?: string[];  // "EXECUTED", "FAILED", etc.
  side?: "BUY" | "SELL";
  fromDate?: Date;
  toDate?: Date;
  symbol?: string;
  sortBy?: "timestamp" | "realized_pnl_rate";
  sortOrder?: "asc" | "desc";
  page?: number;
  limit?: number;
}
```

#### 5.4.3 데이터 페칭 (React Query)

```typescript
const { data, isLoading, error } = useQuery(
  ["executionLogs", filters],
  () => fetchExecutionLogs(filters),
  { refetchInterval: 60000 }  // 1분 주기 새로고침
);
```

### 5.5 성능 요구사항

| 항목 | 목표 | 방법 |
|------|------|------|
| 로그 조회 (50개) | < 500ms | DB 인덱스, 페이지네이션 |
| 통계 계산 | < 2초 | 배치 집계, 캐싱 |
| 로그 저장 | < 100ms | 비동기 INSERT |
| 상세보기 렌더링 | < 200ms | 데이터 사전 로드, 메모이제이션 |

---

## 6. 미결 사항

### 6.1 설계 결정 대기

1. **손익 계산 시점**
   - 현재 계획: 매도 시에만 손익 기록
   - 검토: 미실현 손익(매수 후 현재가 기준)도 기록할지?
   - **결정**: MVP는 실현 손익만. 미실현 손익은 별도 API 추가

2. **조건식 저장 형식**
   - 조건식을 JSON vs 텍스트로 저장?
   - 현재: JSON (구조화, 버전 관리용)
   - 추후: 사용자 친화적 텍스트 포맷도 함께 (UI 표시용)

3. **로그 보관 기간**
   - 계획: 3년
   - 법적 요구사항 검토 필요 (금융위원회 기준)

4. **실시간 알림**
   - 거래 실행 시 사용자에게 실시간 알림?
   - 이메일, 인앱, 푸시 중 어느 것?
   - **결정**: MVP는 UI 조회만. 알림은 Phase 3

### 6.2 구현 세부사항 정리 필요

- [ ] market_snapshot 필드의 정확한 항목 리스트 (종목별 지표 확인)
- [ ] 손익률 계산 공식 (수수료, 세금 포함 정확성)
- [ ] 거래소 응답 메시지 매핑 (키움 API 에러 코드)
- [ ] 멀티 계좌 시 규칙 공유 로직
- [ ] 신호 중복 방지 로직 (로그 레벨에서의 검증)

### 6.3 이전 단계 완료 필수

- Execution Engine spec (execution-engine/spec.md) 확정
- ExecutionLog DB 모델 설계
- Virtual Trading Engine 안정성 검증 (거래 결과 정확성)

---

## 7. 참고 자료

### 7.1 관련 문서

- `docs/architecture.md` — 시스템 전체 아키텍처
- `spec/execution-engine/spec.md` — 실행 엔진 (신호 생성)
- `spec/virtual-auto-trading/spec.md` — 가상 거래 시스템
- `spec/strategy-builder/spec.md` — 전략 빌더 (규칙 정의)

### 7.2 기존 코드 경로

| 모듈 | 경로 | 역할 |
|------|------|------|
| Auto Trading Rule 모델 | `backend/app/models/auto_trading.py` | AutoTradingRule, BacktestResult |
| Virtual Account 모델 | `backend/app/models/virtual_trading.py` | VirtualAccount, VirtualPosition, VirtualTrade |
| Execution Engine | `backend/app/services/execution_engine.py` (신규) | 규칙 평가 & 신호 전송 |
| Trading API | `backend/app/api/trading.py` | 거래 관련 엔드포인트 |
| Database | `backend/app/core/database.py` | DB 연결 설정 |

### 7.3 데이터 흐름도

```
[AutoTradingRule]
    ↓
[Execution Engine] (1분 주기)
    ├─ 조건 평가
    ├─ 신호 생성 → ★ ExecutionLog 기록 (PENDING)
    └─ 신호 전송
        ↓
[Local Bridge] → Kiwoom API
    ↓
[거래 결과] → ★ ExecutionLog 업데이트 (EXECUTED/FAILED)
    ↓
[ExecutionLog Table] (DB 저장)
    ↓
[Frontend UI] ← API 조회
    └─ 로그 열람, 필터, 통계
```

---

## 8. 수용 기준 (Acceptance Criteria)

### Phase 1: 기본 로깅

- [ ] ExecutionLog 테이블이 생성되고, 모든 필드가 정상 저장된다
- [ ] 신호 발동 시 PENDING 상태로 로그가 생성된다
- [ ] 거래 결과 후 EXECUTED/FAILED 상태로 업데이트된다
- [ ] 조건식(conditions_json)과 시장 스냅샷(market_snapshot)이 정확히 저장된다

### Phase 2: API 제공

- [ ] `GET /api/v1/execution/logs` 엔드포인트가 동작한다 (필터, 페이지네이션)
- [ ] `GET /api/v1/execution/logs/{signal_id}` 상세 조회가 동작한다
- [ ] `GET /api/v1/execution/stats` 통계 조회가 동작한다
- [ ] 모든 API가 200ms 이내 응답한다

### Phase 3: UI 구현

- [ ] 실행 로그 목록 페이지가 렌더링된다
- [ ] 필터(규칙, 상태, 기간, 종목)가 정상 동작한다
- [ ] 상세보기 모달에서 조건 평가 과정이 시각화된다
- [ ] 손익 정보(수익률, 실현손익)가 정확히 표시된다

### Phase 4: E2E 검증

- [ ] "규칙 생성 → 신호 발동 → 로그 기록 → UI 조회"의 전체 흐름이 동작한다
- [ ] 100개 거래의 로그 조회 응답이 1초 이내다
- [ ] CSV 내보내기가 정상 작동한다

---

**문서 히스토리:**

| 버전 | 날짜 | 내용 |
|------|------|------|
| 1.0 | 2026-03-04 | 초안 작성 (데이터 구조, 화면, API 설계) |

