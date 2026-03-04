# execution-engine 구현 보고서

> 작성일: 2026-03-04 | 커밋 대기

## 생성/수정 파일 목록

| 파일 | 내용 |
|------|------|
| `local_server/engine/models.py` | TradingRule, Condition 데이터클래스 + `rule_from_dict()` |
| `local_server/engine/evaluator.py` | RuleEvaluator (AND 조건 평가, 변수 resolve) + `evaluate_rule()` |
| `local_server/engine/signal.py` | SignalManager (중복 방지 + 상태머신) + 주문 큐 전송 |
| `local_server/storage/config_manager.py` | `set_config_manager()` / `get_config_manager()` 싱글톤 추가 |
| `local_server/main.py` | `set_config_manager()` 등록 + order_manager 워커 시작 |
| `local_server/routers/trading.py` | `app.state` 참조 → `get_scheduler()` 싱글톤으로 교체 |

## 주요 설계

### 규칙 평가 흐름
```
scheduler._tick()
  → evaluator.evaluate_rule(rule_dict)
      → rule_from_dict() → TradingRule
      → get_context() → ctx dict
      → RuleEvaluator(ctx, prices={}).evaluate(rule)
          → _resolve(variable, symbol): ctx 조회 or 가격
          → 연산자 비교 (>, <, >=, <=, ==)
      → 조건 충족 시 signal_manager.process(rule)
```

### 신호 상태 머신
```
NEW → SENT (process() 호출)
SENT → FILLED (com_client.on_receive_chejan_data() 후 mark_filled())
SENT → NEW (주문 실패 시 자동 rollback — 재시도 허용)
```

### 중복 실행 방지
- 동일 rule_id가 SENT 상태이면 재전송 스킵
- 당일(`date.today()`) 이미 실행된 규칙 스킵

### 지원 변수
- `"price"`: `prices` dict에서 조회 (현재 빈 dict — context-cloud spec에서 확장 예정)
- 그 외: cloud context dict에서 직접 조회 (`rsi_14`, `kospi_change`, 등)

## 미완성 항목
- `prices` dict 실시간 가격 조회 → context-cloud spec에서 키움 실시간 시세 연동
- `mark_filled()` 자동 호출 → com_client.on_receive_chejan_data() 에서 rule_id 매핑 필요
