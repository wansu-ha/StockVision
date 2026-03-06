# 사용자 대시보드 구현 계획서 (user-dashboard)

> 작성일: 2026-03-04 | 상태: **→ Unit 5 (frontend) plan에 통합**

---

## 0. 전제 조건

- 로컬 서버 REST API + WebSocket 동작 중
- 키움 계좌 연결 상태 API: `GET /api/kiwoom/status`
- 잔고/포지션 API: `GET /api/account`
- 실행 로그 API: `GET /api/logs/summary`, `GET /api/logs`

---

## 1. 구현 단계

### Step 1 — 백엔드 API 확인 / 추가

**목표**: 대시보드에 필요한 모든 데이터를 단일 API로 집계

파일: `local_server/routers/health.py` 확장

```
GET /api/dashboard
→ {
    "bridge_connected": true,
    "kiwoom_mode": "demo",
    "active_rules": 3,
    "today": {
      "executions": 2,
      "filled": 2,
      "errors": 0
    },
    "portfolio": {
      "total_value": 10000000,
      "today_pnl": 150000,
      "today_pnl_pct": 1.5
    },
    "market_context": {
      "summary": "KOSPI RSI 28 과매도 구간",
      "kospi_rsi_14": 28.3,
      "trend": "bearish"
    },
    "recent_logs": [...]   // 최근 5건
  }
```

**검증:**
- [ ] `GET /api/dashboard` 통합 응답 반환
- [ ] 로컬 서버 비연결 시 → 빈 포트폴리오 + 연결 없음 상태

### Step 2 — React 대시보드 페이지

파일: `frontend/src/pages/Dashboard.tsx`

```
┌─────────────────────────────────────────────────────────┐
│ StockVision 대시보드                          [설정] [로그] │
├────────────────────┬────────────────────────────────────┤
│ 브릿지 연결         │ 포트폴리오 요약                       │
│ 🟢 연결됨 (모의)    │  평가액: ₩10,000,000                │
│ 활성 전략: 3개      │  오늘 손익: +₩150,000 (+1.5%)       │
├────────────────────┼────────────────────────────────────┤
│ 오늘 실행 현황      │ 시장 컨텍스트                         │
│ 실행: 2건           │  KOSPI RSI(14): 28.3 (과매도)       │
│ 체결: 2건           │  시장 흐름: 하락 조정 중               │
│ 오류: 0건           │                                     │
├────────────────────┴────────────────────────────────────┤
│ 최근 실행 로그                                    [더 보기] │
│ 10:30 RSI 매수   삼성전자  10주  ✅ 체결  ₩72,500       │
│ 14:00 EMA 매도   삼성전자   5주  ✅ 체결  ₩73,100       │
└─────────────────────────────────────────────────────────┘
```

**업데이트 방식**: 10초 폴링 + WS `execution_result` 이벤트 실시간 반영

**검증:**
- [ ] 대시보드 데이터 표시
- [ ] 체결 이벤트 → 실행 현황 즉시 업데이트
- [ ] 브릿지 연결 끊김 → "연결 없음" 상태 표시

### Step 3 — 브릿지 연결 상태 카드

**목표**: 브릿지(로컬 서버) 연결 여부 + 키움 모드 표시

```
React 시작 시:
  ws://localhost:8765/ws 연결 시도 (3회, 백오프)
  → 성공: "🟢 연결됨 (모의투자)"
  → 실패: "🔴 브릿지 미설치 - [설치 가이드]" 버튼
```

**검증:**
- [ ] 로컬 서버 실행 중 → 녹색 상태
- [ ] 로컬 서버 없음 → 빨간 상태 + 설치 안내
- [ ] 재연결 성공 → 자동 상태 업데이트

---

## 2. 파일 목록

| 파일 | 내용 |
|------|------|
| `local_server/routers/health.py` | `GET /api/dashboard` 통합 API |
| `frontend/src/pages/Dashboard.tsx` | 대시보드 페이지 |
| `frontend/src/components/BridgeStatus.tsx` | 브릿지 연결 카드 |
| `frontend/src/components/PortfolioSummary.tsx` | 포트폴리오 요약 카드 |
| `frontend/src/components/MarketContext.tsx` | 시장 컨텍스트 카드 |
| `frontend/src/services/dashboard.ts` | API 클라이언트 |

---

## 3. 커밋 계획

| 커밋 | 메시지 |
|------|--------|
| 1 | `feat: Step 1 — /api/dashboard 통합 API` |
| 2 | `feat: Step 2 — React 대시보드 페이지` |
| 3 | `feat: Step 3 — 브릿지 연결 상태 카드 + WS 연동` |
