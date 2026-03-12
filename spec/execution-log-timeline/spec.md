# 실행 로그 타임라인 (Execution Log Timeline)

> 작성일: 2026-03-12 | 상태: 확정 | Phase C (C3)

## 1. 배경

현재 실행 로그(`ExecutionLog.tsx`)는 테이블 뷰와 기본 타임라인 뷰가 있지만, 주문의 상태 전환(trigger→submit→fill/fail)을 하나의 흐름으로 보여주지 못한다. 사용자는 "주문이 왜 실패했는지", "제출과 체결 사이에 얼마나 걸렸는지"를 파악하기 어렵다.

System Trader Phase 1에서 정의한 실행 상태 모델(IntentState)이 이미 존재하나, 로그 저장과 표시에 충분히 반영되지 않았다.

## 2. 목표

실행 로그를 주문 단위로 묶어 상태 전환 타임라인으로 표시한다. 사용자는 각 주문이 "왜 발생했고 → 어떻게 처리되었고 → 결과가 무엇인지"를 한 눈에 읽을 수 있다.

## 3. 범위

### 3.1 포함

**A. 로그 데이터 구조화**
- 기존 `log_db` 로그에 `intent_id` 필드 추가 (주문 단위 그룹핑)
- 로그 타입별 의미 명확화:
  - `STRATEGY` → 평가 트리거 (규칙 조건 충족)
  - `ORDER` → 주문 제출 (place_order 호출)
  - `FILL` → 체결 확인
  - `ERROR` → 실패/거부/취소

**B. 타임라인 뷰 개선**
- 주문 단위 그룹핑: 같은 `intent_id`의 로그를 하나의 카드로 묶음
- 상태 전환 시각화: `PROPOSED → READY → SUBMITTED → FILLED` 진행 표시
- 각 단계별 시각 표시 (소요 시간)
- 실패 시 실패 사유 하이라이트 + 단계 표시 (어디서 멈췄는지)

**C. 상세 패널**
- 타임라인 항목 클릭 시 상세 정보 표시
  - 트리거 규칙 이름/조건
  - 브로커 응답 원문
  - 재시도 여부
  - 슬리피지 (체결가 vs 요청가)

### 3.2 제외

- 실행 로그 필터링 고도화 (기존 필터 유지)
- 종목별 성과 집계 (Phase D)
- 실시간 WS 스트리밍 타임라인 (기존 폴링 유지)

## 4. 의존성

| 의존 대상 | 상태 | 비고 |
|-----------|------|------|
| System Trader IntentState 모델 | 구현됨 | `spec/system-trader/spec.md` §9 |
| `log_db.py` | 구현됨 | 스키마 확장 필요 (intent_id 컬럼) |
| `ExecutionLog.tsx` | 구현됨 | 타임라인 뷰 존재, 개선 필요 |
| `routers/logs.py` | 구현됨 | 쿼리 확장 필요 |

## 5. 데이터 모델

### 5.1 로그 스키마 확장 (마이그레이션 필요)

현재 `log_db.py` 스키마: `id, ts, log_type, symbol, message, meta` — `intent_id` 컬럼 없음.
C3 구현의 **첫 단계**로 스키마 마이그레이션을 수행해야 한다.

```sql
-- 기존 logs 테이블에 컬럼 추가 (ALTER TABLE — 기존 데이터 유지)
ALTER TABLE logs ADD COLUMN intent_id TEXT;
CREATE INDEX IF NOT EXISTS idx_logs_intent ON logs(intent_id);
```

- `log_db.py`의 `_CREATE_TABLE_SQL`에 `intent_id TEXT` 컬럼 추가
- `write()` 메서드에 `intent_id` 파라미터 추가 (기본값 `None` — 하위 호환)
- 엔진의 로그 기록 호출부에서 `intent_id` 전달하도록 수정 필요
- 기존 로그는 `intent_id = NULL` — 타임라인 뷰에서 그룹핑 불가 (정상)

### 5.2 타임라인 항목 모델

```typescript
interface TimelineEntry {
  intent_id: string
  rule_id: number
  rule_name: string
  symbol: string
  side: 'BUY' | 'SELL'
  state: 'PROPOSED' | 'READY' | 'SUBMITTED' | 'FILLED' | 'FAILED' | 'CANCELLED' | 'BLOCKED'
  steps: TimelineStep[]
  started_at: string
  ended_at: string | null
  duration_ms: number | null
}

interface TimelineStep {
  state: string
  ts: string
  message: string
  meta?: Record<string, any>  // 브로커 응답, 실패 사유 등
}
```

## 6. API 설계

### 6.1 타임라인 조회

```
GET /api/logs/timeline?date_from=2026-03-12&limit=50&symbol=005930&rule_id=1&state=FILLED
```

- `date_from` (필수): 시작 날짜
- `limit` (선택, 기본 50): 최대 타임라인 항목 수
- `symbol` (선택): 종목 필터
- `rule_id` (선택): 규칙 필터
- `state` (선택): 최종 상태 필터 (FILLED, BLOCKED, FAILED 등)

응답:
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "intent_id": "abc12345",
        "rule_id": 1,
        "symbol": "005930",
        "side": "BUY",
        "state": "FILLED",
        "steps": [
          { "state": "PROPOSED", "ts": "2026-03-12T09:30:01Z", "message": "RSI < 30 조건 충족" },
          { "state": "READY", "ts": "2026-03-12T09:30:01Z", "message": "가격 검증 통과" },
          { "state": "SUBMITTED", "ts": "2026-03-12T09:30:02Z", "message": "주문 제출 (10주, 시장가)" },
          { "state": "FILLED", "ts": "2026-03-12T09:30:05Z", "message": "체결 완료 (72,400원)", "meta": { "fill_price": 72400, "slippage": 0.0 } }
        ],
        "started_at": "2026-03-12T09:30:01Z",
        "ended_at": "2026-03-12T09:30:05Z",
        "duration_ms": 4000
      }
    ],
    "total": 1
  },
  "count": 1
}
```

## 7. 프론트엔드 설계

### 7.1 타임라인 카드

```
┌─────────────────────────────────────────────────┐
│ ● 삼성전자 (005930) 매수 10주              FILLED │
│                                                   │
│  ○ 09:30:01  PROPOSED  RSI < 30 조건 충족        │
│  ○ 09:30:01  READY     가격 검증 통과             │
│  ○ 09:30:02  SUBMITTED 주문 제출 (시장가)         │
│  ● 09:30:05  FILLED    체결 72,400원 (4초)        │
│                                                   │
│  규칙: RSI 역추세 매수  │  슬리피지: 0.0%         │
└─────────────────────────────────────────────────┘
```

실패 시:
```
┌─────────────────────────────────────────────────┐
│ ✕ SK하이닉스 (000660) 매수 5주            BLOCKED │
│                                                   │
│  ○ 09:31:00  PROPOSED  MACD 골든크로스            │
│  ✕ 09:31:00  BLOCKED   일일 예산 초과             │
│                                                   │
│  규칙: MACD 추세 매수  │  차단 사유: DAILY_BUDGET │
└─────────────────────────────────────────────────┘
```

### 7.2 뷰 전환

기존 ExecutionLog 페이지에서:
- **테이블 뷰** (기존 유지)
- **타임라인 뷰** (개선) ← 이 spec의 대상

탭으로 전환.

## 8. 수용 기준

- [ ] 로그에 `intent_id`가 기록되어 주문 단위 그룹핑이 가능하다
- [ ] 타임라인 뷰에서 각 주문의 상태 전환 단계가 시각적으로 표시된다
- [ ] 실패/차단된 주문의 사유가 명확히 표시된다
- [ ] 각 단계의 소요 시간이 표시된다
- [ ] 체결 항목에서 슬리피지가 계산되어 표시된다
- [ ] 체결 여부와 주문 제출 여부를 혼동하지 않는다 (UX PRD 수용 기준)

## 9. 참고

- System Trader 상태 모델: `spec/system-trader/spec.md` §9
- 기존 실행 로그: `frontend/src/pages/ExecutionLog.tsx`
- 로그 DB: `local_server/storage/log_db.py`
- 로그 API: `local_server/routers/logs.py`
- UX PRD: `docs/product/frontend-ux-priority-prd-2026-03-10.md` §P2 실행 로그 타임라인화
