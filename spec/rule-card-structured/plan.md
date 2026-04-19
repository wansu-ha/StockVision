# 규칙 카드 구조화 구현 계획

> 작성일: 2026-03-11 | 상태: 구현 완료 | spec: spec/rule-card-structured/spec.md

---

## 개요

총 3단계로 구현한다.

- **Step 1**: 조건/실행/리스크 블록 (현재 Rule 타입 데이터만 사용, 서버 변경 없음)
- **Step 2**: 로컬 서버 last-results 엔드포인트 추가 (최근 결과 블록의 데이터 소스)
- **Step 3**: 최근 결과 블록 연결 + RuleList 인라인 배지

Step 1은 즉시 구현 가능하다. Step 2-3은 System Trader 완성 전 임시 구현으로, Phase B-2에서 `intent_store` 기반으로 교체한다.

---

## Step 1: 조건/실행/리스크 블록 구조화

**파일**: `frontend/src/components/RuleCard.tsx`

**변경**:

1. 카드 레이아웃을 헤더 + 4블록 구조로 재작성한다.

2. **조건 블록** — `summarizeConditions(rule: Rule): string` 헬퍼 함수 추가
   - `rule.script`가 있으면: `--` 주석과 빈 줄 제거 후 줄별로 파싱해 요약 문장 반환
     - `매수:` 섹션이 있으면 첫 조건 줄을 "RSI(14) < 30일 때 매수" 형태로 변환
     - `매도:` 섹션이 있으면 마찬가지 처리
     - 복수 조건은 첫 번째만 표시 + `외 N개` 표기
   - `buy_conditions`/`sell_conditions` JSON이 있으면:
     - 조건 배열 길이 기반으로 "매수 조건 N개" 형태 반환
   - 둘 다 없으면 `"조건 없음"` 반환

3. **실행 블록** — `Execution | null`에서 읽음
   - `execution?.order_type ?? rule.order_type` → "시장가" / "지정가"
   - `execution?.qty_value ?? rule.qty` → 수량
   - `trigger_policy?.frequency` → "1일 1회" (`ONCE_PER_DAY`) / "1회" (`ONCE`)
   - v1 폴백: `execution`이 null이면 `rule.order_type`, `rule.qty` 사용

4. **리스크 블록** — `Rule`에서 직접 읽음
   - `rule.max_position_count` → "최대 N포지션"
   - `rule.budget_ratio` → 퍼센트 표시 (예: 20%)

5. **최근 결과 블록** — Step 3에서 채움. 이 단계에서는 `"미실행"` 회색 배지로 플레이스홀더만 표시한다.

6. Props 인터페이스에 `lastResult?: LastResult` 선택적 프로퍼티 추가 (타입은 Step 2에서 정의)

**변경 없는 파일**: `RuleList.tsx`, `StrategyBuilder.tsx`, `types/strategy.ts`, 서버 측 파일

---

## Step 2: 로컬 서버 last-results 엔드포인트 추가

**파일**: `local_server/routers/rules.py` (신규 또는 기존 라우터에 추가)

**변경**:

1. 로컬 서버 엔진이 규칙 평가 결과를 메모리에 보관하는 저장소 객체를 추가한다.

   ```python
   # local_server/engine/result_store.py (신규)
   # rule_id → LastRuleResult 딕셔너리 (메모리)
   # 재시작 시 초기화
   ```

   ```python
   @dataclass
   class LastRuleResult:
       rule_id: int
       status: Literal["SUCCESS", "BLOCKED", "FAILED"]
       reason: str | None
       at: datetime
   ```

2. `RuleEvaluator` 또는 `Executor`가 평가/실행 후 `result_store`에 결과를 기록한다.
   - System Trader 완성 전: `Executor` 성공/실패 시점에 저장
   - System Trader 완성 후: `TradeDecisionBatch`의 `dropped_signals`의 `blocked_reason`으로 교체

3. 로컬 서버 API 엔드포인트 추가:

   ```
   GET /api/v1/rules/last-results
   ```

   응답:
   ```json
   {
     "success": true,
     "data": {
       "12": { "status": "FAILED", "reason": "주문 수량 부족", "at": "2026-03-11T09:30:00" },
       "15": { "status": "SUCCESS", "reason": null, "at": "2026-03-11T09:30:05" }
     }
   }
   ```

   - 결과 없는 rule_id는 포함하지 않는다. 프론트에서 없으면 "미실행"으로 표시.
   - 인증 불필요 (로컬 서버는 로컬호스트 접근만 허용됨)

**파일 목록**:
- `local_server/engine/result_store.py` (신규)
- `local_server/routers/rules.py` 또는 `local_server/routers/engine.py` (엔드포인트 추가)
- 기존 `Executor` 또는 평가 루프 코드 (result_store 기록 추가)

---

## Step 3: 최근 결과 블록 연결 + RuleList 인라인 배지

**파일**:
- `frontend/src/types/rule-result.ts` (신규)
- `frontend/src/services/localClient.ts` (엔드포인트 호출 추가)
- `frontend/src/components/RuleCard.tsx` (Step 1 이어서)
- `frontend/src/components/RuleList.tsx`
- 규칙 카드를 사용하는 상위 컴포넌트 (StrategyBuilder 또는 종목 상세 페이지)

**변경**:

1. 타입 정의 (`frontend/src/types/rule-result.ts`):

   ```ts
   export type RuleResultStatus = 'SUCCESS' | 'BLOCKED' | 'FAILED' | 'NONE'

   export interface LastRuleResult {
     status: RuleResultStatus
     reason: string | null
     at: string | null
   }

   export type LastResultsMap = Record<number, LastRuleResult>
   ```

2. `localClient.ts`에 `lastRuleResults()` 함수 추가:
   - `GET /api/v1/rules/last-results` 호출
   - 로컬 서버 미연결 시 빈 객체 반환 (에러 무시)
   - 캐시 키: `['local', 'rule-last-results']`, staleTime 30초

3. `RuleCard.tsx` 최근 결과 블록 완성:
   - Props `lastResult?: LastRuleResult` 수신
   - 상태별 배지 색상:
     - `SUCCESS`: 초록 (`text-green-600 bg-green-50`)
     - `BLOCKED`: 주황 (`text-orange-600 bg-orange-50`)
     - `FAILED`: 빨간 (`text-red-600 bg-red-50`)
     - `NONE` 또는 미전달: 회색 "미실행"
   - `reason`이 있으면 배지 아래에 작은 텍스트로 표시
   - `at`이 있으면 상대 시각 표시 (예: "3분 전")

4. `RuleList.tsx` 인라인 배지:
   - 각 리스트 항목 오른쪽(수정/삭제 버튼 왼쪽)에 최근 결과 배지 추가
   - FAILED/BLOCKED만 표시. SUCCESS는 공간 절약을 위해 생략 (선택적 — 구현 시 결정)

5. 상위 컴포넌트에서 `useQuery`로 `lastRuleResults()` 호출 후 결과 맵을 각 카드에 전달.
   - 로컬 서버가 꺼져있으면 조용히 실패. 최근 결과 블록은 "미실행" 상태로 표시.

---

## Phase B-2 교체 메모 (구현 시점: System Trader 완성 후)

Step 2에서 추가한 `result_store.py` 기반 `last-results` 엔드포인트를
`intent_store`의 `OrderIntent` 목록 조회로 교체한다.

- `OrderIntent.rule_id` + `OrderIntent.state` (`FILLED` / `BLOCKED` / `FAILED`) 기반
- `OrderIntent.blocked_reason` → `LastRuleResult.reason`
- 프론트엔드 타입과 API 응답 형식은 동일하게 유지해 Step 3 코드 변경 최소화

교체 시 변경 파일:
- `local_server/engine/result_store.py` (또는 삭제)
- `local_server/routers/rules.py` (또는 engine.py) 의 엔드포인트 구현부만 교체
