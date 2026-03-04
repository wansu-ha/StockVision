# 전략 빌더 구현 계획서 (strategy-builder)

> 작성일: 2026-03-04 | 상태: 초안 | 범위: Phase 3 UI | 의존: context-cloud, execution-engine

---

## 0. 전제 조건

- 컨텍스트 변수 API 존재 (`GET /api/context`)
- 로컬 서버 설정 API 존재 (`PATCH /api/config`)
- 실행 엔진에서 TradingRule JSON 포맷 확정 (`spec/execution-engine/plan.md`)

---

## 1. 규칙 JSON 포맷 (전략 빌더 ↔ 실행 엔진 공유)

```json
{
  "rule_id": 1,
  "name": "RSI 과매도 매수",
  "symbol": "005930",
  "side": "BUY",
  "conditions": [
    { "variable": "kospi_rsi_14", "operator": "<", "value": 30 },
    { "variable": "price",        "operator": ">", "value": 60000 }
  ],
  "quantity": 10,
  "is_active": true
}
```

---

## 2. 구현 단계

### Step 1 — 백엔드: 규칙 CRUD API (로컬 서버)

파일: `local_server/routers/config.py` (확장)

```
GET    /api/rules               활성/비활성 규칙 목록
POST   /api/rules               새 규칙 생성
PUT    /api/rules/{id}          규칙 수정
DELETE /api/rules/{id}          규칙 삭제
PATCH  /api/rules/{id}/toggle   is_active 토글
```

모든 변경은 `config_manager`를 통해 클라우드 동기화 (500ms debounce)

**검증:**
- [ ] 규칙 CRUD 정상 동작
- [ ] 규칙 변경 → 500ms 후 클라우드 `PUT /api/v1/config`

### Step 2 — 조건 변수 목록 API

**목표**: 전략 빌더에서 사용할 수 있는 컨텍스트 변수 목록 제공

파일: `local_server/routers/config.py`

```
GET /api/variables
→ {
    "market": ["kospi_rsi_14", "kospi_20d_volatility", "kosdaq_rsi_14"],
    "price": ["price", "volume", "ma_5", "ma_20"],
    "operators": [">", "<", ">=", "<=", "=="]
  }
```

**검증:**
- [ ] 변수 목록 반환
- [ ] 현재 컨텍스트 캐시의 실제 값도 포함 (미리보기용)

### Step 3 — React 전략 빌더 UI

파일: `frontend/src/pages/StrategyBuilder.tsx`

```
┌──────────────────────────────────────────────────────────┐
│ 새 전략 만들기                                              │
├──────────────────────────────────────────────────────────┤
│ 이름: [RSI 과매도 매수                        ]           │
│ 종목: [005930 삼성전자 ▼]  방향: [매수 ▼]  수량: [10]    │
├──────────────────────────────────────────────────────────┤
│ 조건 (모두 충족 시 실행)                          [+ 조건] │
│ [KOSPI RSI(14) ▼] [< ▼] [30    ]             [삭제]     │
│ [가격 ▼]          [> ▼] [60000 ]             [삭제]     │
├──────────────────────────────────────────────────────────┤
│ 현재 변수 값 (컨텍스트):                                    │
│   KOSPI RSI(14): 28.3  ← 조건 충족됩니다                  │
├──────────────────────────────────────────────────────────┤
│              [백테스팅으로 검증] [저장]                     │
└──────────────────────────────────────────────────────────┘
```

컴포넌트:
- `ConditionRow.tsx`: 변수 선택 + 연산자 + 값 입력
- `RuleList.tsx`: 저장된 규칙 목록 + ON/OFF 토글

**검증:**
- [ ] 규칙 생성 → 로컬 서버 저장 → 클라우드 동기화
- [ ] 현재 컨텍스트 값 표시 (조건 충족 여부 미리보기)
- [ ] 규칙 ON/OFF → 스케줄러 즉시 반영

### Step 4 — 백테스팅 연동

**목표**: 전략 저장 전 백테스팅 결과 미리보기

```
[백테스팅으로 검증] 클릭
  → POST /api/backtests/run (현재 규칙 JSON + 날짜 범위)
  → 결과: 수익률, 샤프비율, MDD, 거래 횟수
  → 미리보기 모달로 표시
```

> Phase 2 백테스팅 엔진 재사용 (기존 `spec/virtual-auto-trading`)

**검증:**
- [ ] 규칙 → 백테스트 실행 → 결과 모달 표시
- [ ] 결과 확인 후 [저장] → 규칙 생성

---

## 3. 파일 목록

| 파일 | 내용 |
|------|------|
| `local_server/routers/config.py` | 규칙 CRUD + 변수 목록 API |
| `frontend/src/pages/StrategyBuilder.tsx` | 전략 빌더 메인 페이지 |
| `frontend/src/components/ConditionRow.tsx` | 조건 행 컴포넌트 |
| `frontend/src/components/RuleList.tsx` | 규칙 목록 + 토글 |
| `frontend/src/services/rules.ts` | API 클라이언트 |

---

## 4. 커밋 계획

| 커밋 | 메시지 |
|------|--------|
| 1 | `feat: Step 1 — 규칙 CRUD API (로컬 서버)` |
| 2 | `feat: Step 2 — 조건 변수 목록 API` |
| 3 | `feat: Step 3 — React 전략 빌더 UI` |
| 4 | `feat: Step 4 — 백테스팅 연동` |
