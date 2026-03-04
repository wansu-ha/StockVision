# 사용자 대시보드 명세서 (user-dashboard)

> 작성일: 2026-03-04 | 상태: 초안 | 대상: Phase 2 후반 (Step 16~18)

## 1. 개요

**목표**: 사용자가 StockVision에 로그인했을 때 자신의 시스템매매 자동화 현황을 한눈에 파악할 수 있는 **대시보드**를 제공한다.

**법적 포지션**: 본 대시보드는 정보제공 및 상태 모니터링만 수행하며, 투자 권유(AI 추천 종목 등)를 포함하지 않는다. 모든 투자 의사결정의 주체는 사용자이다.

**핵심 요구사항**:
- 로컬 브릿지(Kiwoom API 연동) 연결 상태 표시
- 활성 자동매매 전략 수, 오늘 실행된 거래 수
- 포트폴리오 요약 (총 평가액, 오늘 손익, 수익률)
- 시장 컨텍스트 요약 (LLM이 생성한 자연어 시장 설명)
- 최근 실행 로그 미리보기 (타임스탬프, 거래/스케줄 이벤트)

**제외 기능**:
- AI 추천 종목 피드 (투자권유 경계)
- 소셜 기능 (댓글, 공유, 팔로우)
- 실시간 WebSocket 데이터 스트리밍 (폴링 사용)

---

## 2. 레이아웃 구조

### 2.1 정보 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│  사용자 대시보드                                           │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  [A] 시스템 상태 요약                                     │
│      • 로컬 브릿지 연결 상태 (🟢 연결됨 / 🔴 끊김)         │
│      • 활성 전략 수 (n개)                                 │
│      • 오늘 거래 수 (n건)                                 │
│                                                           │
│  [B] 포트폴리오 요약 (주요 지표)                           │
│      • 총 평가액: ₩ 10,234,560                           │
│      • 오늘 손익: ₩ +123,450 (1.23%)                     │
│      • 수익률: 2.34% (YTD)                               │
│      • 잔고: ₩ 2,345,000                                 │
│                                                           │
│  [C] 시장 컨텍스트 요약                                   │
│      LLM이 생성한 자연어 설명:                            │
│      "오늘 코스피는 3% 상승했으며, 기술주와 소재주가      │
│       주도했습니다. 금리 인하 기대감이 작용..."           │
│                                                           │
│  [D] 최근 실행 로그 (타임라인)                            │
│      • 10:30 - 자동매매 규칙 #1 실행 (RSI 전략)         │
│      • 09:45 - 매수 주문 10주 @ ₩50,000                │
│      • 08:15 - 시스템 시작                              │
│      [더보기] → Logs 페이지로 이동                        │
│                                                           │
│  [E] 빠른 이동 버튼                                       │
│      [전략 관리] [거래 기록] [백테스트] [설정]             │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

### 2.2 반응형 요구사항

| 디바이스 | 레이아웃 | 비고 |
|---------|---------|------|
| Desktop (>1200px) | 2열 그리드 (A+B / C, D / E) | 섹션별 카드 배치 |
| Tablet (768~1199px) | 1열 스택 (A→B→C→D→E) | 세로 배열, 모바일 스크롤 |
| Mobile (<768px) | 1열 스택, 컴팩트 | 탭/아코디언으로 섹션 축약 |

---

## 3. 위젯별 상세 명세

### 3.1 [A] 시스템 상태 요약 (System Status Card)

**위치**: 대시보드 상단
**크기**: 전폭, 높이 120px
**배경**: Gradient (파란색 → 보라색)
**상호작용**: 읽기 전용

#### 필드

| 필드명 | 타입 | 값 | 설명 |
|-------|------|-----|------|
| `bridge_status` | `enum` | `connected` \| `disconnected` | 로컬 브릿지 연결 상태 |
| `bridge_last_check` | `timestamp` | ISO8601 | 마지막 상태 확인 시간 |
| `active_rules_count` | `integer` | 0~n | 활성 자동매매 규칙 수 |
| `today_trades_count` | `integer` | 0~n | 오늘 실행된 거래 수 |

#### UI 컴포넌트

```
┌────────────────────────────────────────────────┐
│  ⚡ 시스템 상태                                  │
├────────────────────────────────────────────────┤
│  🟢 로컬 브릿지: 연결됨  | 활성 전략: 3개      │
│  🕐 마지막 확인: 10:32   | 오늘 거래: 12건     │
│  [↻ 새로고침] [⚙️ 설정]                        │
└────────────────────────────────────────────────┘
```

#### API 호출

```typescript
GET /api/v1/dashboard/system-status
Response: {
  "success": true,
  "data": {
    "bridge_status": "connected" | "disconnected",
    "bridge_last_check": "2026-03-04T10:32:00Z",
    "active_rules_count": 3,
    "today_trades_count": 12
  }
}
```

#### 오류 처리

| 오류 | 메시지 | 색상 |
|------|--------|------|
| 브릿지 미연결 | "🔴 로컬 브릿지 연결 불가. 계좌 자동매매가 중지됩니다." | 빨간색 경고 |
| 타임아웃 | "⏱️ 상태 확인 중..." | 노란색 |
| API 실패 | "시스템 상태를 불러올 수 없습니다." | 회색 (재시도) |

---

### 3.2 [B] 포트폴리오 요약 (Portfolio Summary)

**위치**: 대시보드 상단우측 (Desktop) / 두 번째 섹션 (Mobile)
**크기**: 카드 형식, 최소 300px 너비
**배경**: 흰색 (스트로크 회색)
**상호작용**: 클릭 시 Trading 페이지의 Positions 탭으로 이동

#### 필드

| 필드명 | 타입 | 소수점 | 설명 |
|-------|------|--------|------|
| `total_valuation` | `float` | 2자리 | 총 평가액 (현금 + 주식 평가액) |
| `daily_profit_loss` | `float` | 2자리 | 오늘 실현/미실현 손익 합계 |
| `daily_return_pct` | `float` | 2자리 | 오늘 수익률 (%) |
| `ytd_return_pct` | `float` | 2자리 | YTD 누적 수익률 (%) |
| `cash_balance` | `float` | 2자리 | 현금 잔고 |
| `stock_valuation` | `float` | 2자리 | 주식 평가액 |
| `asset_allocation` | `object` | - | 자산 배분 (현금 %, 주식 %) |

#### UI 컴포넌트

```
┌─────────────────────────┐
│  포트폴리오 요약         │
├─────────────────────────┤
│  총 평가액              │
│  ₩ 10,234,560           │
│                         │
│  오늘 손익              │
│  ₩ +123,450 (+1.23%)   │
│                         │
│  YTD 수익률: 2.34%     │
│  현금: ₩2,345,000      │
│  주식: ₩7,889,560      │
│                         │
│  [자세히 보기 →]        │
└─────────────────────────┘
```

#### API 호출

```typescript
GET /api/v1/dashboard/portfolio-summary
Response: {
  "success": true,
  "data": {
    "total_valuation": 10234560.00,
    "daily_profit_loss": 123450.00,
    "daily_return_pct": 1.23,
    "ytd_return_pct": 2.34,
    "cash_balance": 2345000.00,
    "stock_valuation": 7889560.00,
    "asset_allocation": {
      "cash_pct": 22.91,
      "stocks_pct": 77.09
    }
  }
}
```

#### 계산 로직

```python
# 백엔드에서 계산 (실시간 매가 기반)
total_valuation = cash_balance + SUM(position.quantity * current_price)
daily_profit_loss = SUM(realized_pnl 오늘) + SUM(unrealized_pnl 현재)
daily_return_pct = (daily_profit_loss / initial_balance) * 100
ytd_return_pct = ((total_valuation - initial_balance) / initial_balance) * 100
```

---

### 3.3 [C] 시장 컨텍스트 요약 (Market Context)

**위치**: 대시보드 중단 (전폭)
**크기**: 카드 형식, 최소 높이 180px
**배경**: 라이트 블루 (#F0F9FF)
**상호작용**: 텍스트만 표시 (링크 없음)

#### 필드

| 필드명 | 타입 | 길이 | 설명 |
|-------|------|------|------|
| `market_summary` | `string` | 200~400자 | LLM이 생성한 시장 설명 |
| `generated_at` | `timestamp` | - | 생성 시간 |
| `data_sources` | `array[string]` | - | 참고 데이터 (예: KOSPI, KOSDAQ) |

#### UI 컴포넌트

```
┌───────────────────────────────────────┐
│  📊 시장 컨텍스트                      │
├───────────────────────────────────────┤
│  "오늘 코스피는 3% 상승했으며, 기술주 │
│   와 소재주가 주도했습니다. 금리 인하 │
│   기대감이 작용했고, 반도체주는 5%    │
│   상승률을 기록했습니다."              │
│                                       │
│  🕐 생성시간: 10:30  | 데이터: KOSPI │
│  [AI 분석 자세히 보기 →]              │
└───────────────────────────────────────┘
```

#### API 호출

```typescript
GET /api/v1/dashboard/market-context
Response: {
  "success": true,
  "data": {
    "market_summary": "오늘 코스피는 3% 상승했으며...",
    "generated_at": "2026-03-04T10:30:00Z",
    "data_sources": ["KOSPI", "KOSDAQ", "기술주지수"]
  }
}
```

#### LLM 생성 로직 (백엔드)

**트리거**: 장 시작 후 1회, 이후 30분마다 갱신 (또는 사용자 새로고침)

**프롬프트**:
```
You are a financial market analyst.
Analyze today's market data and provide a brief (200-400 chars) natural language summary in Korean.
Include:
- Main index changes (KOSPI, KOSDAQ)
- Sector highlights (strongest/weakest)
- Key drivers (rates, earnings, geopolitical)

Format: Natural paragraph, no bullet points.
```

**입력**:
- KOSPI 지수, 변화율
- 종목 섹터별 평균 수익률
- 기술적 지표 요약 (공포/탐욕 지수)

---

### 3.4 [D] 최근 실행 로그 (Execution Timeline)

**위치**: 대시보드 하단 (전폭)
**크기**: 카드 형식, 최소 높이 250px
**배경**: 흰색 (스트로크 회색)
**상호작용**:
- 각 로그 항목 클릭 시 상세 보기 모달
- [더보기] 버튼 클릭 → Logs 페이지로 이동

#### 필드

| 필드명 | 타입 | 설명 |
|-------|------|------|
| `timestamp` | `datetime` | 이벤트 발생 시간 |
| `event_type` | `enum` | `RULE_EXECUTED`, `BUY_ORDER`, `SELL_ORDER`, `ERROR`, `SYSTEM_START`, `SYSTEM_STOP` |
| `summary` | `string` | 한 줄 설명 |
| `details` | `object` | 추가 정보 (JSON) |
| `status` | `enum` | `SUCCESS`, `PARTIAL`, `FAILED` |

#### UI 컴포넌트

```
┌─────────────────────────────────────────┐
│  📋 최근 실행 로그 (최근 24시간)        │
├─────────────────────────────────────────┤
│  10:32  ✅ 규칙 #1 실행: RSI 매수 신호 │
│         매수: 10주 @ ₩50,000            │
│                                         │
│  10:15  ✅ 매도 주문 완료: 5주 @ ₩51,000│
│         손익: +₩5,000                   │
│                                         │
│  09:45  ⚠️ 규칙 #2 실행 실패            │
│         사유: 잔고 부족                 │
│                                         │
│  09:00  🔔 시스템 시작                  │
│         모니터링 시작 (3개 규칙 활성)    │
│                                         │
│  [더보기 →]  (Logs 페이지로 이동)      │
└─────────────────────────────────────────┘
```

#### API 호출

```typescript
GET /api/v1/dashboard/execution-logs?limit=5
Response: {
  "success": true,
  "data": [
    {
      "id": 1001,
      "timestamp": "2026-03-04T10:32:00Z",
      "event_type": "RULE_EXECUTED",
      "summary": "규칙 #1 실행: RSI 매수 신호",
      "details": {
        "rule_id": 1,
        "rule_name": "RSI 전략",
        "action": "BUY",
        "symbol": "005930",
        "quantity": 10,
        "price": 50000.00
      },
      "status": "SUCCESS"
    },
    // ... 더 많은 로그
  ],
  "count": 5
}
```

#### 아이콘 매핑

| event_type | 아이콘 | 색상 |
|-----------|--------|------|
| RULE_EXECUTED | ⚡ | 파란색 |
| BUY_ORDER | 📈 | 초록색 |
| SELL_ORDER | 📉 | 빨간색 |
| ERROR | ⚠️ | 황색 |
| SYSTEM_START | 🔔 | 보라색 |
| SYSTEM_STOP | 🛑 | 회색 |

---

### 3.5 [E] 빠른 이동 버튼 (Quick Actions)

**위치**: 대시보드 하단
**크기**: 버튼 행, 각 버튼 120px
**배경**: 투명 (호버 시 배경색 변경)
**상호작용**: 클릭 시 해당 페이지로 이동

#### 버튼 목록

| 버튼 | 이동 대상 | 설명 |
|------|---------|------|
| 전략 관리 | `/trading/rules` | AutoTradingRule 관리 페이지 |
| 거래 기록 | `/trading/history` | VirtualTrade 목록 페이지 |
| 백테스트 | `/trading/backtest` | BacktestResult 분석 페이지 |
| 설정 | `/settings/account` | 사용자 설정 페이지 |

---

## 4. 데이터 갱신 주기

### 4.1 폴링 전략

| 위젯 | 갱신 주기 | 방식 | 비고 |
|------|---------|------|------|
| 시스템 상태 | 1분 | Background Polling | 브릿지 연결 상태 모니터링 |
| 포트폴리오 요약 | 5초 (거래 시) / 1분 (비거래 시) | Conditional Polling | 장중은 짧은 주기, 장외 긴 주기 |
| 시장 컨텍스트 | 30분 | Fixed Interval | 장 시작 후 1회, 이후 30분마다 |
| 최근 로그 | 10초 | Continuous Polling | 새 거래/이벤트 모니터링 |

### 4.2 캐싱 정책

| 엔드포인트 | Cache-Control | 설명 |
|----------|--------------|------|
| `/api/v1/dashboard/system-status` | max-age=30 | 30초 캐시 |
| `/api/v1/dashboard/portfolio-summary` | max-age=5 (거래 시) / 60 (비거래 시) | 동적 |
| `/api/v1/dashboard/market-context` | max-age=1800 | 30분 캐시 |
| `/api/v1/dashboard/execution-logs` | max-age=10 | 10초 캐시 |

### 4.3 실시간 데이터 (선택사항, Phase 3+)

향후 WebSocket으로 업그레이드:
```
ws://localhost:8000/ws/dashboard?token=...
→ system-status, portfolio-summary 실시간 푸시
```

---

## 5. 기술 요구사항

### 5.1 백엔드 API

**신규 엔드포인트**:

| Method | Path | 설명 | 응답 시간 |
|--------|------|------|---------|
| GET | `/api/v1/dashboard/system-status` | 브릿지 상태 + 규칙/거래 카운트 | <100ms |
| GET | `/api/v1/dashboard/portfolio-summary` | 총 평가액, 손익, 수익률 | <150ms |
| GET | `/api/v1/dashboard/market-context` | LLM 시장 설명 | <500ms |
| GET | `/api/v1/dashboard/execution-logs` | 최근 로그 (limit 파라미터) | <200ms |

**기존 엔드포인트 활용**:
- `GET /api/v1/trading/accounts/{id}` — 계좌 정보 조회
- `GET /api/v1/trading/positions/{account_id}` — 포지션 조회
- `GET /api/v1/trading/scores` — 최신 스코어 (시장 컨텍스트 입력)

### 5.2 프론트엔드 기술

**라이브러리**:
- React Query: 폴링 + 캐싱 (`useQuery` with `refetchInterval`)
- Recharts: 자산 배분 파이 차트 (선택)
- HeroUI: 카드, 버튼, 아이콘
- Tailwind CSS: 레이아웃, 반응형

**컴포넌트**:
```typescript
// frontend/src/pages/Dashboard.tsx (신규)
export default function Dashboard() {
  const systemStatus = useQuery(...)      // 1분 갱신
  const portfolio = useQuery(...)         // 5초~1분 갱신
  const marketContext = useQuery(...)     // 30분 갱신
  const execLogs = useQuery(...)          // 10초 갱신

  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-1">
      <SystemStatusCard {...systemStatus.data} />
      <PortfolioSummary {...portfolio.data} />
      <MarketContext {...marketContext.data} />
      <ExecutionTimeline {...execLogs.data} />
      <QuickActions />
    </div>
  )
}
```

**컴포넌트 분리**:
- `SystemStatusCard.tsx` — [A] 시스템 상태
- `PortfolioSummary.tsx` — [B] 포트폴리오
- `MarketContext.tsx` — [C] 시장 컨텍스트
- `ExecutionTimeline.tsx` — [D] 로그 타임라인
- `QuickActions.tsx` — [E] 버튼 행

### 5.3 데이터베이스

**신규 모델**: 없음 (기존 모델 활용)

**기존 모델**:
- `VirtualAccount` — 계좌 조회
- `VirtualPosition` — 포지션 조회
- `VirtualTrade` — 거래 내역
- `AutoTradingRule` — 규칙 상태
- `ExecutionLog` (또는 App Log) — 이벤트 로그

### 5.4 LLM 통합 (마켓 컨텍스트)

**모델**: OpenAI GPT-4 (또는 로컬 LLM)

**입력 데이터** (1일 1회 또는 30분마다):
```json
{
  "kospi_price": 2850.45,
  "kospi_change_pct": 3.21,
  "kosdaq_price": 945.32,
  "kosdaq_change_pct": 2.15,
  "sector_performance": {
    "IT": 5.2,
    "Financials": -0.5,
    "Materials": 4.8,
    ...
  },
  "date": "2026-03-04",
  "time": "10:30"
}
```

**캐싱**: 동일 일자에 재생성 하지 않음 (Redis key: `market_context:{date}`)

---

## 6. 미결 사항

### 6.1 설계 결정 대기

| # | 항목 | 옵션 | 상태 |
|---|------|------|------|
| 1 | 로컬 브릿지 상태 API | Polling vs WebSocket | ⏳ 결정 대기 |
| 2 | 시장 컨텍스트 LLM | OpenAI vs 로컬 모델 (Llama) | ⏳ 비용 검토 필요 |
| 3 | 포트폴리오 새로고침 주기 | 5초 (배터리 부담) vs 30초 (지연) | ⏳ UX 검증 필요 |
| 4 | 자산 배분 차트 | 파이 차트 vs 도넛 차트 | ⏳ 디자인 검토 |
| 5 | 모바일 레이아웃 | 탭 vs 아코디언 vs 수평 스크롤 | ⏳ 프로토타입 필요 |

### 6.2 종속성

- **Phase 2 완료 필수**: VirtualAccount, VirtualTrade, ExecutionLog 모델 및 API
- **로컬 브릿지 상태 API**: `GET /api/v1/bridge/status` 구현 필요
- **LLM 서비스**: 기존 `AIAnalysis` 서비스 활용 또는 신규 LLM 통합

### 6.3 테스트 전략

**단위 테스트**:
- API 응답 형식 검증
- 계산 로직 (수익률, 손익)
- LLM 프롬프트 생성

**통합 테스트**:
- 실시간 데이터 폴링 동작
- 캐시 갱신 타이밍
- 에러 복구 (API 실패 시 재시도)

**E2E 테스트**:
- 로그인 → 대시보드 진입 → 모든 위젯 로드 → 상호작용

---

## 7. 참고: 기존 코드 경로

| 영역 | 경로 | 타입 |
|------|------|------|
| 가상 계좌 모델 | `backend/app/models/virtual_trading.py:VirtualAccount` | DB |
| 거래 내역 모델 | `backend/app/models/virtual_trading.py:VirtualTrade` | DB |
| 자동매매 규칙 모델 | `backend/app/models/auto_trading.py:AutoTradingRule` | DB |
| Trading API | `backend/app/api/trading.py` | Router |
| AI 분석 서비스 | `backend/app/services/ai_analysis.py` | Service |
| 로그 API | `backend/app/api/logs.py` | Router |
| 대시보드 페이지 | `frontend/src/pages/Dashboard.tsx` | Component (기존) |
| API 클라이언트 | `frontend/src/services/api.ts` | HTTP Client |

---

## 부록 A: API 응답 샘플

### A.1 System Status

```json
{
  "success": true,
  "data": {
    "bridge_status": "connected",
    "bridge_last_check": "2026-03-04T10:32:15Z",
    "active_rules_count": 3,
    "today_trades_count": 12
  },
  "count": 1
}
```

### A.2 Portfolio Summary

```json
{
  "success": true,
  "data": {
    "total_valuation": 10234560.50,
    "daily_profit_loss": 123450.00,
    "daily_return_pct": 1.23,
    "ytd_return_pct": 2.34,
    "cash_balance": 2345000.00,
    "stock_valuation": 7889560.50,
    "asset_allocation": {
      "cash_pct": 22.91,
      "stocks_pct": 77.09
    }
  },
  "count": 1
}
```

### A.3 Market Context

```json
{
  "success": true,
  "data": {
    "market_summary": "오늘 코스피는 3% 상승했으며, 기술주와 소재주가 주도했습니다. 금리 인하 기대감이 작용했으며, 외국인 순매수가 지속되고 있습니다.",
    "generated_at": "2026-03-04T10:30:00Z",
    "data_sources": ["KOSPI", "KOSDAQ", "기술주지수"]
  },
  "count": 1
}
```

### A.4 Execution Logs

```json
{
  "success": true,
  "data": [
    {
      "id": 1001,
      "timestamp": "2026-03-04T10:32:00Z",
      "event_type": "RULE_EXECUTED",
      "summary": "규칙 #1 실행: RSI 매수 신호",
      "details": {
        "rule_id": 1,
        "rule_name": "RSI 전략",
        "action": "BUY",
        "symbol": "005930",
        "quantity": 10,
        "price": 50000.00
      },
      "status": "SUCCESS"
    },
    {
      "id": 1000,
      "timestamp": "2026-03-04T10:15:00Z",
      "event_type": "SELL_ORDER",
      "summary": "매도 주문 완료: 5주 @ ₩51,000",
      "details": {
        "symbol": "005930",
        "quantity": 5,
        "price": 51000.00,
        "realized_pnl": 5000.00
      },
      "status": "SUCCESS"
    }
  ],
  "count": 5
}
```

---

**최종 수정일**: 2026-03-04
**작성자**: Claude Code (AI Assistant)
**리뷰 상태**: ⏳ 대기 (사용자 검토 후 확정)
