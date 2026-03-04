# 포트폴리오 조회 구현 계획서 (portfolio)

> 작성일: 2026-03-04 | 상태: 초안 | 범위: Phase 2 후반 (가상 거래 계좌 기반)

---

## 0. 전제 조건

- Phase 2 가상 거래 엔진 완료 (Account, Position, Fill 모델 존재)
- `virtual_accounts`, `virtual_positions`, `virtual_fills` 테이블 존재
- 백엔드: `backend/app/api/`, 프론트엔드: `frontend/src/`

---

## 1. 구현 단계

### Step 1 — 백엔드: 포트폴리오 집계 API

파일: `backend/app/api/portfolio.py` (신규)

```
GET /api/v1/portfolio/{account_id}
→ {
    "account_id": 1,
    "total_value": 10500000,     # 예수금 + 평가액
    "cash_balance": 5000000,
    "positions_value": 5500000,
    "total_pnl": 500000,
    "total_pnl_pct": 5.0,
    "positions": [
      {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "qty": 10,
        "avg_price": 150.0,
        "current_price": 155.0,
        "unrealized_pnl": 500000,
        "pnl_pct": 3.33,
        "weight_pct": 52.4
      }
    ]
  }

GET /api/v1/portfolio/{account_id}/equity-curve?period=30d
→ [
    { "date": "2026-02-03", "equity": 10000000 },
    ...
  ]

GET /api/v1/portfolio/{account_id}/sector-allocation
→ [
    { "sector": "Technology", "value": 5500000, "weight_pct": 52.4 },
    { "sector": "Cash",       "value": 5000000, "weight_pct": 47.6 }
  ]
```

**현재가 조회**: yfinance 실시간 호출 (캐시 5분)

**검증:**
- [ ] 포지션 있는 계좌 → 평가손익 포함 응답
- [ ] 빈 계좌 → positions: [], total_value = cash_balance
- [ ] equity-curve 30/90/180일 쿼리 파라미터 동작

### Step 2 — React 포트폴리오 페이지

파일: `frontend/src/pages/Portfolio.tsx`

```
┌──────────────────────────────────────────────────────────┐
│ 포트폴리오                            [계좌 #1 ▼]           │
├─────────────────┬────────────────────────────────────────┤
│ 총 자산          │  수익률 차트                             │
│ ₩10,500,000     │  [30일 ▼]                              │
│ +₩500,000 (5%)  │  [equity curve line chart]             │
├─────────────────┴────────────────────────────────────────┤
│ 보유 종목                              자산 배분 [파이차트] │
│ 종목    수량  평균가    현재가  손익     IT:52%  현금:48%  │
│ AAPL    10   $150     $155   +3.3%                      │
│ 현금                           $5,000                    │
└──────────────────────────────────────────────────────────┘
```

차트: Recharts (기존 프로젝트 표준)

**검증:**
- [ ] 포지션 목록 + 손익 표시
- [ ] equity-curve 차트 렌더링
- [ ] 섹터별 배분 파이차트

### Step 3 — 전략 기여도 분석

**목표**: 어떤 자동매매 규칙이 어떤 포지션을 만들었는지 표시

```
GET /api/v1/portfolio/{account_id}/attribution
→ [
    {
      "rule_id": 1,
      "rule_name": "RSI 매수 전략",
      "symbol": "AAPL",
      "realized_pnl": 200000,
      "unrealized_pnl": 150000
    }
  ]
```

> Phase 3에서 실전 연동 후 추가 구현. Phase 2에서는 기본 포지션 조회까지.

---

## 2. 파일 목록

| 파일 | 내용 |
|------|------|
| `backend/app/api/portfolio.py` | 포트폴리오 API (신규) |
| `backend/app/services/portfolio.py` | 집계 서비스 |
| `frontend/src/pages/Portfolio.tsx` | 포트폴리오 페이지 |
| `frontend/src/components/EquityCurve.tsx` | 수익률 차트 |
| `frontend/src/components/PositionTable.tsx` | 보유 종목 테이블 |
| `frontend/src/services/portfolio.ts` | API 클라이언트 |

---

## 3. 커밋 계획

| 커밋 | 메시지 |
|------|--------|
| 1 | `feat: Step 1 — 포트폴리오 집계 API` |
| 2 | `feat: Step 2 — React 포트폴리오 페이지 + 차트` |
