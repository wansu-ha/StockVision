# 규칙 카드 구조화 명세서

> 작성일: 2026-03-11 | 상태: 초안

---

## 1. 목표

상세 화면의 규칙 카드를 `빠른 편집` 중심에서 `구조적 이해 + 빠른 편집`으로 끌어올린다.

사용자는 규칙 편집 화면을 열지 않고도 카드 한 장만 보고:
- 이 규칙이 무엇을 하는 규칙인지 이해할 수 있어야 한다.
- 최근에 성공했는지 실패했는지, 실패 이유가 무엇인지 알 수 있어야 한다.
- 실패한 규칙이 활성 규칙 사이에 묻히지 않아야 한다.

---

## 2. 비목표

- 규칙 편집 UI 자체의 변경 (StrategyBuilder, ConditionRow는 건드리지 않는다)
- 실행 로그 타임라인 화면 구현 (별도 P2 항목)
- 규칙 실행 이력의 서버 측 집계 API 신규 설계 (Phase B System Trader 완성 이후)
- 차트와의 이벤트 연결 (상세 차트 워크벤치화는 별도 P1 항목)

---

## 3. 현재 상태

### 3.1 RuleCard.tsx 현재 구조

`frontend/src/components/RuleCard.tsx`는 다음만 보여준다:

- 규칙명 (`rule.name`)
- 종목코드 + 종목명 (`rule.symbol`, `symbolName`)
- 매매 방향 배지 (매수/매도/양방향 — `parseDirection` 함수로 script에서 파싱)
- 활성 상태 표시 ("실행 중" / "OFF")
- 조건 요약 — `rule.script` 줄을 `|` 구분자로 flat하게 이어붙임. DSL이 없으면 "(JSON 조건)"
- ON/OFF 토글 버튼
- 수정/삭제 버튼

**부재 항목:**
- 조건/실행/리스크 블록 구분 없음
- 최근 실행 결과 없음
- 실패 이유 없음
- 주문 유형, 수량 등 실행 설정 미노출

### 3.2 RuleList.tsx 현재 구조

`frontend/src/components/RuleList.tsx`는 카드 형태가 아닌 `<ul>` 리스트로 규칙을 나열한다. 보여주는 정보는 RuleCard와 거의 동일하다. 카드 뷰(`RuleCard`)와 리스트 뷰(`RuleList`) 두 형태가 병존한다.

### 3.3 Rule 타입 현재 구조

`frontend/src/types/strategy.ts`의 `Rule`:

```ts
interface Rule {
  id, name, symbol, is_active, priority, version
  created_at, updated_at
  // v2 DSL
  script: string | null
  execution: Execution | null          // { order_type, qty_type, qty_value, limit_price }
  trigger_policy: TriggerPolicy | null // { frequency, cooldown_minutes }
  // v1 하위 호환
  buy_conditions, sell_conditions
  order_type, qty, max_position_count, budget_ratio
}
```

### 3.4 서버 측 TradingRule 모델 현재 구조

`cloud_server/models/rule.py`의 `TradingRule` 컬럼:

```
id, user_id, name, symbol
script (Text)
buy_conditions, sell_conditions (JSON)
execution (JSON), trigger_policy (JSON)
priority, order_type, qty, max_position_count, budget_ratio
is_active, version, created_at, updated_at
```

실행 이력 관련 컬럼 없음. 현재 서버 DB에는 규칙 실행 결과가 전혀 저장되지 않는다.

---

## 4. 요구사항

### 4.1 4블록 카드 구조

규칙 카드를 아래 4개 블록으로 분리한다:

| 블록 | 표시 내용 |
|------|----------|
| **조건** | 조건 요약 문장 (script 파싱 또는 JSON 조건 요약) |
| **실행** | 매매 방향, 주문 유형(시장가/지정가), 수량/수량 비율, 트리거 빈도 |
| **리스크** | 최대 포지션 수 (`max_position_count`), 예산 비율 (`budget_ratio`) |
| **최근 결과** | 마지막 실행 상태 (성공/실패/미실행), 실패 이유 |

### 4.2 조건 요약 문장

- `rule.script`가 있으면: 주석(`--`) 제외 비어있지 않은 줄을 의미 단위로 파싱해 문장형으로 보여준다.
  - 예: `"RSI(14) < 30일 때 매수"`, `"EMA(20) > EMA(60)이면 매수"`
- v1 JSON 조건(`buy_conditions`, `sell_conditions`)이 있으면: 블록 수 기준으로 간단 요약한다.
  - 예: `"매수 조건 3개"`, `"매도 조건 2개"`
- 조건이 없으면: `"조건 없음"` 표시

편집 버튼을 누르기 전에도 이 요약이 카드에서 읽혀야 한다.

### 4.3 최근 실행 결과 표시

| 상태 | 표시 |
|------|------|
| `SUCCESS` | 초록 배지 + 실행 시각 |
| `BLOCKED` | 주황 배지 + 차단 이유 (예: "포지션 한도 초과") |
| `FAILED` | 빨간 배지 + 실패 이유 |
| 이력 없음 | 회색 "미실행" 표시 |

- 실패 이유가 있으면 카드에서 바로 읽힌다. 별도 화면 이동 불필요.
- 실패 배지는 is_active=true인 카드에서도 시각적으로 구분된다.

### 4.4 카드 헤더 구조 유지

- 규칙명, 종목, 매매 방향 배지, ON/OFF 토글, 수정/삭제 버튼은 현재 위치에 유지한다.
- 활성 상태("실행 중" / "OFF") 표시는 헤더 영역에 유지한다.

---

## 5. 데이터 요구사항

### 5.1 현재 있는 데이터 (즉시 표시 가능)

아래 항목은 현재 `Rule` 타입에 이미 존재하므로 프론트엔드 렌더링 로직만 추가하면 된다:

| 블록 | 필드 | 출처 |
|------|------|------|
| 조건 | `script`, `buy_conditions`, `sell_conditions` | Rule |
| 실행 | `execution.order_type`, `execution.qty_value`, `trigger_policy.frequency` | Rule |
| 실행 (v1 폴백) | `order_type`, `qty`, `budget_ratio` | Rule |
| 리스크 | `max_position_count`, `budget_ratio` | Rule |

### 5.2 현재 없는 데이터 (최근 결과 블록)

최근 실행 결과는 현재 서버에 존재하지 않는다. 아래 두 가지 접근을 단계적으로 구현한다:

#### Phase B-1: 로컬 메모리 기반 (System Trader 완성 전)

로컬 서버가 규칙 평가 결과를 메모리에 보유하고 있는 경우, 로컬 서버 API에서 `rule_id`별 마지막 결과를 반환하는 엔드포인트를 추가한다.

```
GET /api/v1/rules/last-results
Response: {
  success: true,
  data: {
    [rule_id: number]: {
      status: "SUCCESS" | "BLOCKED" | "FAILED" | "NONE"
      reason: string | null
      at: string | null  // ISO 8601
    }
  }
}
```

이 엔드포인트는 로컬 서버 재시작 시 초기화된다. 영구 저장 아님.

#### Phase B-2: System Trader DecisionLog 기반

System Trader 구현 완료 후 (`spec/system-trader/spec.md`), `OrderIntent`와 `TradeDecisionBatch`의 결정 이유(`blocked_reason`)를 활용한다.

`DecisionLog` 또는 `OrderIntent` 목록에서 `rule_id`별 최신 항목을 조회해 카드에 표시한다. 이 단계에서는 로컬 서버 `intent_store`의 조회 API로 대체한다.

### 5.3 데이터 흐름 요약

```
RuleCard
  ├── 조건/실행/리스크 → Rule 타입 (클라우드 서버, 이미 존재)
  └── 최근 결과       → 로컬 서버 last-results 엔드포인트 (신규)
                        Phase B-2 이후: intent_store 조회
```

---

## 6. 수용 기준

- [ ] 규칙 카드가 `조건`, `실행`, `리스크`, `최근 결과` 4개 블록으로 시각적으로 분리된다.
- [ ] 편집 버튼을 누르기 전에도 조건 요약 문장이 카드에서 읽힌다.
- [ ] `execution.order_type`과 `execution.qty_value`가 실행 블록에 표시된다.
- [ ] `max_position_count`와 `budget_ratio`가 리스크 블록에 표시된다.
- [ ] 최근 실행 결과 블록이 SUCCESS/BLOCKED/FAILED/미실행 중 하나를 배지로 표시한다.
- [ ] FAILED/BLOCKED 상태일 때 이유가 배지 아래 또는 툴팁으로 카드에서 바로 읽힌다.
- [ ] is_active=true인 카드에 FAILED 배지가 있을 때 시각적으로 구분된다.
- [ ] RuleList.tsx (리스트 뷰)도 최소한 최근 결과 배지를 인라인으로 표시한다.
