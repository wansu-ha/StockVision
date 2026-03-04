# 전략 템플릿 구현 계획서 (strategy-template)

> 작성일: 2026-03-04 | 상태: 초안 | 범위: Phase 3 | 의존: strategy-builder

---

## 0. 전제 조건

- 전략 빌더 UI 구현 완료 (`spec/strategy-builder/plan.md`)
- 관리자 권한 체계 (`spec/admin-dashboard/plan.md`)
- 클라우드 서버 `GET /api/templates` 엔드포인트

---

## 1. 구현 단계

### Step 1 — 클라우드 API: 템플릿 CRUD

파일: `backend/app/api/templates.py`

```
# 공개 API (인증 불필요)
GET /api/templates
  → [
      {
        "id": 1,
        "name": "RSI 과매도 역추세",
        "description": "KOSPI RSI가 30 미만일 때 매수하는 단순 역추세 전략",
        "category": "기술적 지표",
        "difficulty": "초급",
        "backtest_summary": { "cagr": 12.3, "mdd": -18.5, "sharpe": 0.85 },
        "conditions": [
          { "variable": "kospi_rsi_14", "operator": "<", "value": 30 }
        ],
        "side": "BUY",
        "tags": ["RSI", "역추세", "초급"]
      }
    ]

GET /api/templates/{id}
  → 상세 (백테스트 전체 결과 + 설명 포함)

# 관리자 전용 (JWT + admin role)
POST   /api/admin/templates        템플릿 생성
PUT    /api/admin/templates/{id}   템플릿 수정
DELETE /api/admin/templates/{id}   템플릿 삭제
```

**DB 모델:**
```python
class StrategyTemplate(Base):
    __tablename__ = "strategy_templates"
    id          = Column(Integer, primary_key=True)
    name        = Column(String, nullable=False)
    description = Column(Text)
    category    = Column(String)
    difficulty  = Column(String)  # "초급" | "중급" | "고급"
    rule_json   = Column(JSON)    # TradingRule 포맷
    backtest_summary = Column(JSON)
    tags        = Column(ARRAY(String))
    is_active   = Column(Boolean, default=True)
    created_at  = Column(DateTime)
```

**검증:**
- [ ] `GET /api/templates` 템플릿 목록 반환
- [ ] 비활성 템플릿 미포함

### Step 2 — 초기 템플릿 데이터 시딩

파일: `backend/scripts/seed_templates.py`

초기 템플릿 (3~5개):
1. **RSI 과매도 역추세** — KOSPI RSI < 30 → 매수
2. **EMA 골든크로스** — EMA5 > EMA20 상향 교차 → 매수
3. **변동성 돌파** — 전일 변동성 × 0.5 이상 상승 → 매수
4. **고가 모멘텀 매도** — RSI > 70 → 매도

**검증:**
- [ ] seed 실행 후 `GET /api/templates` → 4개 이상 반환
- [ ] 각 템플릿 백테스트 요약 포함

### Step 3 — React 템플릿 브라우저 UI

파일: `frontend/src/pages/Templates.tsx`

```
┌──────────────────────────────────────────────────────────┐
│ 전략 템플릿                     [카테고리 ▼] [난이도 ▼]    │
├──────────────────────────────────────────────────────────┤
│ ┌─────────────────────┐  ┌─────────────────────┐        │
│ │ RSI 과매도 역추세    │  │ EMA 골든크로스        │        │
│ │ 초급 · 기술적 지표   │  │ 중급 · 추세추종       │        │
│ │ CAGR 12.3%          │  │ CAGR 8.5%           │        │
│ │ MDD -18.5%          │  │ MDD -22.1%          │        │
│ │           [사용하기] │  │           [사용하기] │        │
│ └─────────────────────┘  └─────────────────────┘        │
└──────────────────────────────────────────────────────────┘
```

[사용하기] 클릭 → 전략 빌더로 이동, 조건 자동 채워짐

**검증:**
- [ ] 템플릿 카드 목록 표시
- [ ] 카테고리/난이도 필터
- [ ] [사용하기] → 전략 빌더 자동 채우기

---

## 2. 파일 목록

| 파일 | 내용 |
|------|------|
| `backend/app/models/templates.py` | StrategyTemplate 모델 |
| `backend/app/api/templates.py` | GET /api/templates |
| `backend/scripts/seed_templates.py` | 초기 데이터 시딩 |
| `frontend/src/pages/Templates.tsx` | 템플릿 브라우저 |
| `frontend/src/components/TemplateCard.tsx` | 템플릿 카드 |
| `frontend/src/services/templates.ts` | API 클라이언트 |

---

## 3. 커밋 계획

| 커밋 | 메시지 |
|------|--------|
| 1 | `feat: Step 1 — 전략 템플릿 DB 모델 + API` |
| 2 | `feat: Step 2 — 초기 템플릿 데이터 시딩` |
| 3 | `feat: Step 3 — React 템플릿 브라우저 UI` |
