> 작성일: 2026-03-12 | Phase C 분석 F: 전략 생성 UX

# F. 전략 생성/편집/배포 흐름 분석

## F-1. 전략 생성 흐름

### StrategyBuilder.tsx (pages/)
**폼 구조:**
```typescript
interface FormState {
  name: string              // 전략명
  symbol: string            // 종목 코드
  buyConditions: Condition[]  // 매수 조건 (AND)
  sellConditions: Condition[] // 매도 조건 (AND)
  qty: number               // 고정 수량
  is_active: boolean
}

interface Condition {
  variable: string  // rsi_14, ema_20, price 등
  operator: '>' | '<' | '>=' | '<=' | '=='
  value: number
}
```

**API 호출:**
- 생성: `cloudRules.create(payload)` → POST `/api/v1/rules`
- 수정: `cloudRules.update(id, payload)` → PUT `/api/v1/rules/{id}`
- 저장 후 로컬 동기화: `localRules.sync(rules)` → POST `/api/rules/sync`

**DSL 변환:** `conditionsToDsl()` — 조건 배열 → DSL 스크립트
```
예: "매수: rsi_14 < 30 AND price > 50000\n매도: rsi_14 > 70"
```

**미구현:** DSL → 폼 역파싱 (TODO)

### StrategyList.tsx (pages/)
- 규칙 목록: `cloudRules.list()` (10s refetch)
- 실행 결과: `localRules.lastResults()` (로컬 메모리)
- 종목명: `cloudStocks.get(symbol)` (캐시)
- ON/OFF 토글: `cloudRules.update(id, { is_active })` → 로컬 sync

### RuleCard.tsx — 4블록 구조
| 블록 | 필드 | 출처 |
|------|------|------|
| 조건 | DSL 요약 또는 JSON | `rule.script` / `rule.buy/sell_conditions` |
| 실행 | 주문유형, 수량, 빈도 | `rule.execution`, `rule.trigger_policy` |
| 리스크 | 최대 포지션, 예산 비율 | `rule.max_position_count`, `rule.budget_ratio` |
| 최근결과 | 상태+사유 | `lastResult.status`, `lastResult.reason` |

## F-2. 전략 관련 API

### 클라우드 서버 — `/api/v1/rules`

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/api/v1/rules` | 규칙 목록 (version 포함) |
| POST | `/api/v1/rules` | 규칙 생성 |
| GET | `/api/v1/rules/{id}` | 규칙 상세 |
| PUT | `/api/v1/rules/{id}` | 규칙 수정 (version 증가) |
| DELETE | `/api/v1/rules/{id}` | 규칙 삭제 |

**요청 스키마 (RuleCreateBody):**
```
name, symbol, script?, execution?, trigger_policy?, priority,
buy_conditions?, sell_conditions? (v1 호환),
order_type, qty, max_position_count, budget_ratio, is_active
```

### 로컬 서버 — `/api/rules`

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/api/rules/sync` | 클라우드 규칙 → 로컬 캐시 동기화 |
| GET | `/api/rules` | 캐시된 규칙 조회 |
| GET | `/api/rules/last-results` | 최근 실행 결과 |

## F-3. DB 모델 (TradingRule)

```python
class TradingRule(Base):
    __tablename__ = "trading_rules"
    id, user_id, name, symbol
    script            # v2 DSL (Text, nullable)
    buy_conditions    # v1 (JSON, nullable)
    sell_conditions   # v1 (JSON, nullable)
    execution         # JSON: { order_type, qty_type, qty_value }
    trigger_policy    # JSON: { frequency: ONCE_PER_DAY | ONCE }
    priority          # Integer
    order_type, qty, max_position_count, budget_ratio  # v1 개별 컬럼
    is_active, version, created_at, updated_at
```

## F-4. 전체 플로우

```
[StrategyBuilder] → cloudRules.create/update → Cloud DB 저장
                  → cloudRules.list → localRules.sync → 로컬 메모리 캐시
                                                         ↓
[엔진 시작] POST /api/strategy/start → 브로커 연결 + 시세 구독
                                         ↓
[실행 사이클] (매분)
  RuleEvaluator.evaluate(rule, market_data, context)
    ├─ script → DSL 평가
    └─ JSON → v1 폴백
  → CandidateSignal 생성
  → SystemTrader.process_cycle() — 포트폴리오 제약 적용
    ├─ DUPLICATE_SYMBOL, MAX_POSITIONS, DAILY_BUDGET_EXCEEDED, SELL_NO_HOLDING
  → OrderExecutor.execute() — 브로커 주문
  → ResultStore.record_result() — 결과 저장 (메모리)
                                         ↓
[결과 조회] localRules.lastResults() → { rule_id, status, reason, at }
```

## F-5. 증권사 의존성 분석

### 증권사 불필요 (가입만으로 가능)
- 규칙 생성/편집/삭제 — 클라우드 DB 저장
- 규칙 목록 조회 — 클라우드 API
- 종목 검색/선택 — 클라우드 API

### 증권사 필요
- 엔진 시작 — broker.connect()
- 실시간 시세 — broker.subscribe_quotes()
- 주문 실행 — broker.place_order()
- 계좌 잔고/보유종목 — broker.get_balance()

### 핵심 발견
**전략 생성 → 저장 → (나중에) 배포 흐름은 이미 자연스러움.**
- 규칙은 클라우드에 저장되므로 증권사 없이도 만들 수 있음
- "배포"(로컬 sync + 엔진 시작)만 증권사+로컬 필요
- 온보딩에서 "전략 만들기"를 첫 체험으로 제공 가능

## F-6. 미구현/미검증

| 항목 | 상태 |
|------|------|
| DSL 역파싱 (script → 폼) | TODO |
| 복잡한 DSL (cross-over, 상태 추적) | 엔진 지원, UI 미지원 |
| 샘플/템플릿 전략 | 미구현 |
| 모의투자 전환 | is_mock 설정으로 가능하나 UX 미설계 |
| KIS 실계정 주문 | 미검증 |
