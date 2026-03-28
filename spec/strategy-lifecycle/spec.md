# 전략 수명주기 통합 — Strategy Lifecycle

> 작성일: 2026-03-28 | 상태: 초안

---

## 목표

전략의 생성→백테스트→배포→모니터링 흐름을 끊김 없이 연결한다.
백테스트 결과를 저장하고, 실전 성과와 비교할 수 있게 한다.

---

## 범위

### 포함

1. **StrategyBuilder → 백테스트 연동** — 규칙 편집에서 바로 백테스트
2. **백테스트 결과 DB 저장** — 이력 조회, 전략 간 비교
3. **전략 카드 백테스트 요약** — 목록에서 "수익률 +12%, MDD -5%" 표시
4. **OpsPanel 백테스트 기준선** — 실전 P&L 옆에 백테스트 예상치 표시
5. **분봉 IndicatorProvider 확장** — 라이브 엔진 분봉 지표

### 미포함

- C6-C8 원격 제어 (PWA/FCM) — 별도 spec
- 멀티종목 포트폴리오 백테스트 — v2
- 자동 파라미터 최적화 — v2

---

## SL-1: StrategyBuilder → 백테스트 버튼

**현상**: 백테스트 페이지(`/backtest`)가 독립 존재. StrategyBuilder에서 직접 접근 불가. 네비게이션 메뉴에도 없음.

**수용 기준**:
- [ ] Layout.tsx 네비게이션에 "백테스트" 메뉴 추가
- [ ] StrategyBuilder 폼에 "백테스트" 버튼 추가 (저장 버튼 옆)
- [ ] 클릭 시 현재 script + symbol로 백테스트 실행
- [ ] 결과를 인라인 모달 또는 하단 패널로 표시
- [ ] 저장하지 않은 규칙도 inline script로 백테스트 가능
- [ ] RuleCard에도 "백테스트" 아이콘 버튼 추가
- [ ] Backtest.tsx에 저장된 규칙 선택 드롭다운 추가 (rule_id)

**파일**:
- `frontend/src/pages/StrategyBuilder.tsx` (수정)
- `frontend/src/pages/Backtest.tsx` (수정 — 규칙 선택기)
- `frontend/src/components/RuleCard.tsx` (수정)
- `frontend/src/components/Layout.tsx` (수정 — nav 추가)

---

## SL-2: 백테스트 결과 DB 저장

**현상**: 백테스트 결과가 1회성 (메모리에서 반환 후 소멸).

**수용 기준**:
- [ ] `backtest_executions` 테이블 생성
- [ ] 백테스트 실행 시 결과 자동 저장 (summary + trades JSON)
- [ ] `GET /api/v1/backtest/history` — 사용자별 이력 조회
- [ ] `GET /api/v1/backtest/{id}` — 특정 결과 상세
- [ ] 규칙별 최근 백테스트 조회 (`rule_id` 필터)
- [ ] equity_curve는 다운샘플하여 저장 (500포인트 이하)

**모델**:
```python
class BacktestExecution(Base):
    id            = Integer PK
    user_id       = String(36)
    rule_id       = Integer FK (nullable — inline script일 때)
    symbol        = String(10)
    start_date    = Date
    end_date      = Date
    timeframe     = String(5)
    initial_cash  = Float
    summary       = JSON   # {total_return_pct, mdd, win_rate, ...}
    trade_count   = Integer
    executed_at   = DateTime
```

**파일**:
- `cloud_server/models/backtest.py` (신규)
- `cloud_server/api/backtest.py` (수정)
- `cloud_server/services/backtest_runner.py` (수정)
- alembic 마이그레이션

---

## SL-3: 전략 카드 백테스트 요약 표시

**현상**: RuleCard에 "최근 결과"(실행 성공/실패)만 표시. 백테스트 지표 없음.

**수용 기준**:
- [ ] RuleCard에 "백테스트" 블록 추가 (또는 기존 4블록 → 5블록)
- [ ] 최근 백테스트 요약: 수익률, MDD, 승률
- [ ] 백테스트 미실행 시 "아직 백테스트 없음" 표시
- [ ] 클릭 시 상세 결과 페이지로 이동

**파일**:
- `frontend/src/components/RuleCard.tsx` (수정)
- `frontend/src/services/backtest.ts` (수정 — history API 호출)

---

## SL-4: OpsPanel 백테스트 배지

**현상**: OpsPanel에 오늘 실전 P&L만 표시. 전략의 기대 성과 비교 불가.

**수용 기준**:
- [ ] OpsPanel "엔진" 상태 팝오버에 활성 규칙의 백테스트 요약 표시
- [ ] 규칙별: 최근 백테스트 수익률 + MDD (한 줄 요약)
- [ ] 백테스트 없는 규칙은 "미검증" 배지
- [ ] 전체 비교 차트는 v2 (equity_curve에 timestamp 필요)

**참고**: 실전 "오늘 P&L"과 백테스트 "기간 수익률"은 단위가 다름.
일별 기대치 비교는 equity_curve에 날짜를 포함한 후 v2에서 구현.

**파일**:
- `frontend/src/components/main/OpsPanel.tsx` (수정)

---

## SL-5: 타임프레임 인자 실제 반영 + 분봉 IndicatorProvider

**현상**: DSL에 `RSI(14, "5m")` 문법은 파싱되지만, 백테스트 Runner와 라이브 Evaluator 모두 TF 인자를 **무시**. 일봉 지표만 반환.

**선행 조건**: 분봉 데이터 축적 (키움 실계좌 수집 또는 모의서버 3일치)

**수용 기준**:

백테스트 Runner (cloud):
- [ ] DSL AST에서 사용된 타임프레임 목록 추출
- [ ] 타임프레임별 바 데이터 로드 + 지표 사전 계산
- [ ] context 람다에서 TF 인자를 실제로 사용하여 해당 TF 지표 조회

라이브 엔진 (local):
- [ ] 타임프레임별 독립 캐시: `indicators["5m"]["rsi_14"]`
- [ ] 로컬 MinuteBarStore에서 분봉 데이터 읽기
- [ ] Evaluator context에 타임프레임 인자 전달
- [ ] 기존 `RSI(14)` = `RSI(14, "1d")` 하위 호환

**파일**:
- `cloud_server/services/backtest_runner.py` (수정 — TF 실제 반영)
- `local_server/engine/indicator_provider.py` (수정 — 멀티 TF)
- `local_server/engine/evaluator.py` (수정 — TF context)

---

## 데이터 흐름

```
StrategyBuilder
  │ "백테스트" 클릭
  ▼
POST /api/v1/backtest/run (script, symbol, timeframe)
  │
  ▼
BacktestRunner → BacktestResult
  │ 자동 저장
  ▼
backtest_executions DB
  │
  ├──→ RuleCard (최근 백테스트 요약)
  ├──→ OpsPanel (백테스트 기준선)
  └──→ /backtest/{id} (상세 결과)
```

---

## 미래 확장 (이번 scope 밖, 참고용)

이 spec은 "생성→백테스트→배포→모니터링" 중 백테스트↔운영 연결에 집중.
아래는 roadmap Phase E의 나머지 수명주기 항목으로, 이번 구현 위에 쌓인다.

| 항목 | 의존 | 시점 |
|------|------|------|
| 드라이런 (페이퍼 트레이딩) | MockAdapter + 라이브 엔진 | 이번 이후 |
| 장마감 복기 (AI 리뷰) | D2/D3 브리핑 + 실행 로그 | Phase E |
| BYO LLM 코파일럿 | DSL 파서 + Claude API | Phase E |
| 전략 빌더 위저드 (자연어 → DSL) | 코파일럿 | Phase E |
| 백테스트 equity_curve에 timestamp 포함 | SL-2 확장 | SL-4 v2 |
| 실전 vs 백테스트 일별 비교 차트 | timestamp equity_curve | SL-4 v2 |
| BacktestResult.tsx CAGR/평균보유기간 표시 | UI만 | SL-3과 함께 |
