> 작성일: 2026-03-28 | 상태: 구현 완료 | Strategy Lifecycle

# 전략 수명주기 통합 구현 계획서

## 개요

Spec: `spec/strategy-lifecycle/spec.md` (SL-1 ~ SL-5)

전략의 생성→백테스트→배포→모니터링 흐름을 통합한다.

---

## 의존성

```
SL-2 (DB 저장) ──→ SL-3 (카드 요약) ──→ SL-4 (OpsPanel 기준선)
                     ↑
SL-1 (Builder 버튼) ─┘

SL-5 (분봉 지표) ── 독립 (라이브 엔진 전용)
```

---

## 수정 파일 목록

### 백엔드

| 파일 | 변경 | 설명 |
|------|------|------|
| `cloud_server/models/backtest.py` | 신규 | BacktestExecution 모델 |
| `cloud_server/api/backtest.py` | 수정 | 결과 저장 + history/detail API |
| `cloud_server/services/backtest_runner.py` | 수정 | 실행 후 DB 저장 |
| `alembic/versions/xxx_backtest_table.py` | 신규 | 마이그레이션 |

### 프론트엔드

| 파일 | 변경 | 설명 |
|------|------|------|
| `frontend/src/pages/StrategyBuilder.tsx` | 수정 | 백테스트 버튼 + 결과 패널 |
| `frontend/src/components/RuleCard.tsx` | 수정 | 백테스트 요약 블록 + 아이콘 |
| `frontend/src/components/main/OpsPanel.tsx` | 수정 | 백테스트 기준선 |
| `frontend/src/services/backtest.ts` | 수정 | history API 추가 |

### 라이브 엔진

| 파일 | 변경 | 설명 |
|------|------|------|
| `local_server/engine/indicator_provider.py` | 수정 | 멀티 타임프레임 |
| `local_server/engine/evaluator.py` | 수정 | TF 인자 context 주입 |

---

## 구현 순서

### Step 1: BacktestExecution 모델 + DB 저장 (SL-2)
1. `cloud_server/models/backtest.py` — BacktestExecution 모델
2. alembic 마이그레이션 (또는 init_db에서 create_all)
3. `backtest_runner.py` — run() 완료 후 결과 DB 저장
4. `backtest.py` — 응답에 execution_id 포함
5. `GET /api/v1/backtest/history` — 사용자별 이력 (최근 20건)
6. `GET /api/v1/backtest/{id}` — 상세 결과
7. verify: API 호출 → DB 저장 → history 조회 확인

### Step 2: 네비게이션 + StrategyBuilder 백테스트 버튼 (SL-1)
1. Layout.tsx navItems에 `{ path: '/backtest', label: '백테스트' }` 추가
2. Backtest.tsx에 저장된 규칙 선택 드롭다운 (cloudRules.list → select)
3. StrategyBuilder에 "백테스트" 버튼 추가 (저장 옆)
4. 클릭 시 현재 script + symbol로 backtest API 호출
5. 결과를 하단 패널로 표시 (BacktestResult 컴포넌트 재사용)
6. RuleCard에 "백테스트" 아이콘 추가 → 클릭 시 `/backtest?rule_id={id}`
7. BacktestResult.tsx에 CAGR, 평균 보유기간 카드 추가
8. verify: 네비게이션에서 백테스트 접근 + Builder에서 실행 + 결과 표시

### Step 3: 전략 카드 백테스트 요약 (SL-3)
1. `backtest.ts`에 `getLatestBacktest(ruleId)` API 추가
2. StrategyList에서 규칙별 최근 백테스트 fetch
3. RuleCard에 백테스트 요약 행: 수익률 / MDD / 승률
4. 미실행 시 "백테스트 없음" 표시
5. verify: 전략 목록에서 백테스트 지표 표시

### Step 4: OpsPanel 백테스트 기준선 (SL-4)
1. OpsPanel에서 활성 규칙의 최근 백테스트 조회
2. "오늘 요약" 옆에 "백테스트 기준" 표시
3. 실전 P&L vs 백테스트 기대치 비교
4. verify: OpsPanel에 백테스트 기준 표시

### Step 5: 타임프레임 인자 반영 + 분봉 IndicatorProvider (SL-5)
1. `backtest_runner.py` — DSL AST에서 사용된 TF 추출, TF별 지표 계산, context 람다에서 TF 실사용
2. `indicator_provider.py`에 멀티 타임프레임 캐시 추가
3. 로컬 MinuteBarStore에서 분봉 읽기
4. `evaluator.py` context에 TF 인자 전달
5. verify: 백테스트 RSI(14, "5m") ≠ RSI(14) + 엔진 테스트 통과
6. **선행 조건**: 분봉 데이터 존재 (없으면 TF 미지정 = 일봉 폴백으로 동작)

---

## 검증 체크리스트

- [ ] backtest_executions 테이블 생성
- [ ] 백테스트 실행 시 결과 DB 저장
- [ ] history/detail API 동작
- [ ] Layout.tsx 네비게이션에 백테스트 메뉴
- [ ] Backtest.tsx에서 저장된 규칙 선택 가능
- [ ] StrategyBuilder에서 백테스트 버튼 동작
- [ ] BacktestResult.tsx에 CAGR, 평균 보유기간 표시
- [ ] RuleCard에 백테스트 아이콘 + 요약 표시
- [ ] OpsPanel 엔진 팝오버에 백테스트 배지 표시
- [ ] 백테스트 Runner에서 TF 인자 실제 사용 (데이터 있을 때)
- [ ] 분봉 IndicatorProvider 멀티 TF 동작 (데이터 있을 때)
- [ ] 기존 테스트 전체 통과
- [ ] npm run build 성공
