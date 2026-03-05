# 프론트엔드 구현 계획서 (frontend)

> 작성일: 2026-03-05 | 상태: 초안 | Unit 6 (Phase 3)

---

## 0. 현황

### 0.1 기존 코드 (Phase 1-2)

**위치**: `frontend/src/`

**구조**:
```
src/
├── pages/          # 페이지 (Dashboard, StockList, Trading, ExecutionLog, etc.)
├── components/     # 재사용 컴포넌트
├── services/       # API 클라이언트
│   ├── api.ts            # stockApi (클라우드 서버, localhost 미지원)
│   ├── auth.ts           # 인증 (구현 부재, AuthContext에서만 일부)
│   ├── rules.ts          # 규칙 (API 없음)
│   ├── dashboard.ts      # 대시보드 (기본만)
│   ├── portfolio.ts      # 포트폴리오
│   ├── logs.ts           # 로그 (백엔드 미지원)
│   ├── templates.ts      # 템플릿
│   ├── admin.ts          # 어드민
│   └── onboarding.ts     # 온보딩
├── hooks/          # React 훅
│   └── useLocalBridgeWS.ts   # localhost WS (미완성)
├── types/          # TypeScript 타입
│   ├── index.ts         # 주식, AI 분석 타입
│   ├── stock.ts         # Stock, StockPrice (중복?)
│   └── trading.ts       # 거래 타입
├── stores/         # Zustand (토스트만)
├── context/        # React Context (AuthContext만)
├── App.tsx         # 라우팅 (기본 구조 완성)
└── main.tsx        # 진입점
```

**기존 라우팅** (App.tsx):
- `/login`, `/register`, `/forgot-password`, `/reset-password` (인증)
- `/onboarding` (온보딩)
- `/ (Dashboard), /stocks, /stocks/:symbol, /trading, /logs, /strategy, /portfolio, /templates, /admin`

**기존 기술**:
- React 19, TypeScript, Vite, Tailwind CSS, HeroUI
- React Router, React Query, Zustand (토스트)
- Axios (HTTP), 네이티브 WebSocket (미완성)

**현황 문제점**:
1. **localhost 클라이언트 부재** — `api.ts`는 클라우드 서버만 (http://localhost:8000/api/v1)
2. **JWT 전달 로직 부재** — 로그인 후 localhost에 JWT 전달 구현 없음
3. **규칙 sync 로직 부재** — 규칙 저장 후 localhost에 sync 구현 없음
4. **WS 재연결 로직 미완성** — `useLocalBridgeWS.ts` 스켈레톤만
5. **신호등 상태 관리 부재** — 클라우드/키움/API 상태 조회 및 갱신 로직 없음
6. **API Key 저장 로직 부재** — localhost로 API Key 전달 구현 없음
7. **타입 정의 불완전** — Rule, Strategy, ExecutionLog 등 Phase 3 타입 미정의

**기존 서비스 API 호출**:
- `api.ts` (클라우드 서버): stockApi, aiAnalysisApi, tradingApi, healthApi
- `/api/v1/stocks`, `/api/v1/ai-analysis`, `/api/v1/trading`

---

## 1. 구현 단계

### Step 1 — API 클라이언트 2개 (cloudClient + localClient) 생성

**목표**: 클라우드 서버와 localhost를 분리하여 관리하는 HTTP 클라이언트 두 개 구성

**파일**:
- `services/cloudClient.ts` (신규) — 클라우드 서버 (HTTPS/HTTP, JWT 인증)
  - 인증 (register, login, refresh)
  - 규칙 CRUD (getRules, saveRule, deleteRule)
  - 컨텍스트 조회
  - 어드민
- `services/localClient.ts` (신규) — localhost (HTTP)
  - JWT 전달
  - 규칙 sync
  - API Key 등록
  - 상태 조회 (health check)
  - 설정 조회/변경
  - 로그 조회
  - 전략 시작/중지

**기존 파일 정리**:
- `services/api.ts` (기존) — 하위 호환성을 위해 유지하되, cloudClient로 점진 대체

**기술**:
- Axios 인터셉터로 JWT 자동 첨부 (cloudClient)
- 에러 처리: 401 시 Refresh Token 자동 갱신 (cloudClient만)
- localhost 미연결 경고 (localClient)

**검증**:
- [ ] cloudClient.register/login/refresh 동작
- [ ] localClient.setAuthToken() → JWT 저장
- [ ] localClient.syncRules() → 규칙 전달
- [ ] localClient.getStatus() → 상태 반환
- [ ] 401 에러 시 자동 갱신 테스트

---

### Step 2 — 인증 페이지 (로그인, 회원가입, 이메일 인증, 비밀번호 재설정)

**목표**: 사용자 인증 흐름 구현 (cloudClient 기반)

**파일**:
- `pages/Login.tsx` (기존 개선) — 이메일 + 비밀번호 로그인
  - cloudClient.login() 호출
  - JWT + Refresh Token 저장
  - localStorage + localClient.setAuthToken() 호출 ← **new**
  - 대시보드로 리다이렉트
- `pages/Register.tsx` (기존 개선) — 회원가입 + 이메일 확인
  - cloudClient.register() 호출
  - 이메일 확인 대기 UI
  - 확인 코드 입력 (cloudClient.verifyEmail())
  - 로그인 페이지로 리다이렉트
- `pages/ForgotPassword.tsx` (기존 유지) — 비밀번호 재설정 요청
- `pages/ResetPassword.tsx` (기존 유지) — 비밀번호 변경

**AuthContext 개선**:
- `context/AuthContext.tsx` (기존 개선)
  - user (이메일, 역할)
  - JWT + Refresh Token 저장 (localStorage)
  - logout() → localStorage 삭제 + localClient에 전달
  - isAuthenticated 플래그

**타입 정의**:
- `types/auth.ts` (신규)
  - User (email, role, created_at)
  - AuthResponse (user, access_token, refresh_token)
  - LoginRequest, RegisterRequest, VerifyEmailRequest

**localhost 브릿지**:
- Login/Register 성공 후 → localClient.setAuthToken(jwt, refreshToken) ← **new**

**검증**:
- [ ] 회원가입 → 이메일 인증 → 로그인 흐름 전체
- [ ] JWT 저장/로드 동작
- [ ] localClient.setAuthToken() 호출 확인
- [ ] 토큰 만료 시 자동 갱신 (cloudClient 인터셉터)
- [ ] 로그아웃 → JWT 삭제 + localStorage 초기화

---

### Step 3 — 레이아웃 + 라우팅 (사이드바, 신호등 헤더, 보호된 라우트)

**목표**: 인증된 사용자만 접근 가능한 레이아웃 및 네비게이션 완성

**파일**:
- `components/Layout.tsx` (기존 개선)
  - 헤더 (로고, 신호등 3개, 유저메뉴)
  - 사이드바 (메뉴: 대시보드, 전략, 로그, 설정, 어드민)
  - 푸터 (선택)
  - 반응형 디자인 (태블릿/PC)
- `components/TrafficLightStatus.tsx` (신규)
  - 3개 신호등: 클라우드 서버, 로컬 서버, 키움 API
  - 5초마다 갱신 (cloudClient.healthCheck + localClient.getStatus)
  - 색상: green(정상), red(오류), yellow(준비 중)
  - 호버 시 상태 텍스트 표시
- `components/UserMenu.tsx` (신규)
  - 드롭다운: 프로필, 설정, 로그아웃
- `hooks/useAuth.ts` (신규)
  - AuthContext를 래핑하여 isAuthenticated 확인
- `App.tsx` (기존 개선)
  - ProtectedRoute 컴포넌트 추가
  - 미인증 시 /login으로 리다이렉트

**라우팅 구조**:
```
/                       → Dashboard (인증 필요)
/login, /register, ...  → 인증 페이지 (인증 불필요)
/strategies             → 전략 목록
/strategies/new         → 전략 빌더 (새 규칙)
/strategies/:id/edit    → 전략 빌더 (수정)
/logs                   → 실행 로그
/settings               → 설정
/admin/*                → 어드민 (role=admin만)
```

**타입**:
- `types/ui.ts` (신규)
  - TrafficLightColor ('green' | 'red' | 'yellow')
  - ServerStatus (cloud, local, kiwoom)

**검증**:
- [ ] 미인증 시 /login 리다이렉트
- [ ] 인증 후 모든 페이지 접근 가능
- [ ] 신호등 5초 갱신 + 색상 변화 확인
- [ ] 사이드바 메뉴 렌더링 + 클릭 네비게이션
- [ ] 로그아웃 → /login 리다이렉트

---

### Step 4 — 대시보드 (실시간 시세, 체결 피드, 시장 컨텍스트, 신호등)

**목표**: 메인 대시보드 구성 — 실시간 시세 테이블, 체결 알림, 신호등, 시장 컨텍스트

**파일**:
- `pages/Dashboard.tsx` (기존 개선)
  - 상단: 시스템 상태 (신호등 3개) + 요약 (활성 전략, 오늘 체결)
  - 중앙-상: 실시간 시세 테이블 (종목명, 현재가, 변동률, 거래량)
  - 중앙-하: 최근 체결 피드 (시간, 종목, 매수/매도, 수량, 체결가, 상태)
  - 하단: 시장 컨텍스트 (KOSPI RSI, 변동성, 추세)
- `components/PriceTable.tsx` (신규)
  - React Table 또는 Recharts 기반 실시간 테이블
  - localhost WS에서 시세 수신 (useLocalBridgeWS)
  - 종목별 색상 (상승 red, 하락 blue)
  - 정렬/필터 기능
- `components/ExecutionFeed.tsx` (신규)
  - 최근 체결 5-10건 표시 (localhost WS)
  - 시간, 종목, 방향, 수량, 체결가, 상태 표시
  - 스크롤하여 더보기
- `components/MarketContext.tsx` (기존 유지/개선)
  - KOSPI/KOSDAQ 지수 + RSI + 변동성
  - cloudClient.getContext() 호출
  - 5초마다 갱신

**타입**:
- `types/dashboard.ts` (신규)
  - PriceQuote (symbol, name, price, changePercent, volume)
  - ExecutionEvent (timestamp, symbol, side, qty, price, status)
  - MarketContext (kospi_rsi, volatility, trend)

**localhost WS 통합**:
- `hooks/useLocalBridgeWS.ts` (기존 개선/완성)
  - WebSocket 연결: ws://localhost:8765/ws
  - 자동 재연결 (1s → 5s → 30s 백오프)
  - 시세 + 체결 이벤트 수신
  - 타입 안전 메시지 파싱

**API 호출**:
- cloudClient.getContext() — 시장 컨텍스트
- cloudClient.healthCheck() — 신호등 (클라우드)
- localClient.getStatus() — 신호등 (로컬 + 키움)

**검증**:
- [ ] 대시보드 로드 시 시세 테이블 표시
- [ ] localhost WS 연결 → 시세 업데이트 실시간 반영
- [ ] 체결 이벤트 수신 → ExecutionFeed 반영
- [ ] 신호등 5초 갱신
- [ ] 시장 컨텍스트 데이터 표시
- [ ] localhost 미연결 시 경고 UI

---

### Step 5 — localhost WS 연결 (시세 + 체결 실시간)

**목표**: WebSocket을 통한 실시간 시세 + 체결 데이터 스트리밍

**파일**:
- `hooks/useLocalBridgeWS.ts` (신규 완성)
  - WebSocket 클래스 기반 (자동 재연결)
  - 메시지 타입:
    - `price_update` — 시세 갱신 (symbol, price, changePercent, volume)
    - `execution` — 체결 알림 (timestamp, symbol, side, qty, price, status)
    - `status_change` — 상태 변경 (server, kiwoom_connected)
  - 훅 인터페이스: (url, handlers) → { connect, disconnect, isConnected }
  - 에러 처리: 재연결 + 사용자 알림
- `utils/ws.ts` (신규)
  - WebSocketManager 클래스
  - 자동 재연결 로직 (exponential backoff)
  - 메시지 큐 (연결 중 메시지 버퍼링)
  - 하트비트 (연결 유지)

**메시지 형식** (JSON):
```typescript
// 시세 업데이트
{
  "type": "price_update",
  "symbol": "005930",
  "name": "삼성전자",
  "price": 71000,
  "changePercent": 1.2,
  "volume": 123000
}

// 체결 알림
{
  "type": "execution",
  "timestamp": "2026-03-05T10:30:15",
  "symbol": "005930",
  "side": "buy",  // "buy" | "sell"
  "qty": 10,
  "price": 71000,
  "status": "filled"  // "pending" | "filled" | "cancelled" | "failed"
}

// 상태 변경
{
  "type": "status_change",
  "server": "running",  // "running" | "stopped"
  "kiwoom_connected": true
}
```

**컴포넌트 통합**:
- Dashboard, PriceTable, ExecutionFeed에서 useLocalBridgeWS 사용

**검증**:
- [ ] WS 연결 성공 → useLocalBridgeWS.isConnected = true
- [ ] 시세 메시지 수신 → PriceTable 업데이트 (< 200ms)
- [ ] 체결 메시지 수신 → ExecutionFeed 추가
- [ ] 연결 끊김 → 자동 재연결 (로그 확인)
- [ ] localhost 미연결 시 → 재연결 시도 + 경고

---

### Step 6 — 전략 빌더 (조건 UI, AND/OR, 저장 + sync)

**목표**: 시각적 규칙 편집기 — 매수/매도 조건을 드래그-드롭 또는 폼으로 구성

**파일**:
- `pages/StrategyBuilder.tsx` (기존 개선)
  - 상단: 전략 이름 + 대상 종목 입력
  - 중단: 매수 조건 + 매도 조건 각각 구성기
  - 하단: 주문 설정 (주문 유형, 수량, 예산 비율, 최대 포지션)
  - 버튼: 저장, 저장+활성화, 취소
- `components/ConditionEditor.tsx` (기존 개선)
  - 조건 행 반복 (지표, 연산자, 값)
  - AND/OR 드롭다운
  - 조건 추가/삭제 버튼
- `components/ConditionRow.tsx` (기존 유지/개선)
  - 지표 선택 (드롭다운): RSI, EMA, MACD, 거래량배수, 등
  - 연산자 선택: <, <=, >, >=, ==, !=
  - 값 입력 (숫자 또는 참조)
  - 삭제 버튼

**타입**:
- `types/strategy.ts` (신규)
  - Condition (indicator, operator, value, logic: 'AND' | 'OR')
  - Rule (id, name, symbol, buy_conditions, sell_conditions, order_settings, enabled, created_at, updated_at)
  - OrderSettings (order_type: 'market' | 'limit', qty, budget_ratio, max_positions)
  - Indicator (key, name, params?)

**API 호출**:
- cloudClient.createRule() / updateRule() — 규칙 저장
- localClient.syncRules() — localhost에 즉시 전달 ← **new**

**저장 흐름**:
```typescript
// 1. 클라우드에 저장
const savedRule = await cloudClient.saveRule(rule);

// 2. localhost에 즉시 sync
await localClient.syncRules([savedRule]);

// 3. 전략 목록으로 이동
navigate('/strategies');
```

**미보존된 변경 경고**:
- 페이지 이탈 시 "저장하지 않은 변경이 있습니다" 알림

**검증**:
- [ ] 조건 추가/삭제 동작
- [ ] AND/OR 토글 동작
- [ ] 저장 → cloudClient.saveRule() 호출
- [ ] 저장 직후 → localClient.syncRules() 호출
- [ ] 저장 + 활성화 → enabled = true로 저장
- [ ] 기존 규칙 수정 화면 로드 (URL 파라미터)
- [ ] localhost 미연결 경고 (규칙은 API에 저장됨)

---

### Step 7 — 전략 목록 관리 (CRUD, ON/OFF 토글)

**목표**: 저장된 규칙 목록 조회, 활성화/비활성화, 수정, 삭제

**파일**:
- `pages/StrategyList.tsx` (신규) 또는 라우트 통합
  - 테이블: 규칙명, 대상 종목, 조건 요약, 활성 여부, 생성일, 작업 버튼
  - 검색/필터 (종목, 활성 여부)
  - 규칙 하나 클릭 → 상세 뷰 또는 수정 페이지
  - 토글 버튼: 규칙 ON/OFF (즉시 api 호출)
  - 삭제 버튼 (확인 다이얼로그)
- `components/RuleCard.tsx` (신규)
  - 규칙 하나를 카드로 표시 (모바일)
  - 이름, 종목, 조건 요약, ON/OFF 토글

**API 호출**:
- cloudClient.getRules() — 규칙 목록 조회
- cloudClient.updateRule(id, { enabled: boolean }) — ON/OFF 토글
- cloudClient.deleteRule(id) — 삭제
- localClient.syncRules() — localhost에 전달 (토글/삭제 직후)

**React Query 통합**:
- `useQuery(['rules'], cloudClient.getRules, { refetchInterval: 10000 })` — 10초마다 갱신

**검증**:
- [ ] 규칙 목록 로드 + 표시
- [ ] 규칙 ON/OFF 토글 → api 호출 + UI 반영
- [ ] 규칙 삭제 → 확인 → api 호출 + 목록 갱신
- [ ] localhost 미연결 시 → 경고 표시 (api는 성공)
- [ ] 수정 클릭 → /strategies/:id/edit로 이동

---

### Step 8 — 실행 로그 뷰어 (체결 내역, 필터, 상세 조회)

**목표**: localhost에서 저장된 체결 로그, 오류 로그를 조회하고 분석

**파일**:
- `pages/ExecutionLog.tsx` (기존 개선)
  - 상단: 필터 (날짜, 종목, 상태)
  - 테이블: 시간, 종목, 방향, 수량, 체결가, 상태, 수익률
  - 행 클릭 → 상세 정보 (팝업 또는 사이드 패널)
- `components/LogDetailPanel.tsx` (신규)
  - 상세 로그: 규칙 ID, 이유, 오류 메시지, 원본 명령, 응답
  - 공유 버튼 (향후)

**타입**:
- `types/log.ts` (신규)
  - ExecutionLog (id, timestamp, symbol, side, qty, price, status, rule_id, reason)
  - ErrorLog (id, timestamp, message, context)

**API 호출**:
- localClient.getLogs(filters) — 로그 조회
  - query: { date_from, date_to, symbol, status }
  - 페이지네이션: offset, limit

**검증**:
- [ ] 로그 조회 + 테이블 렌더링
- [ ] 필터 적용 → api 재호출
- [ ] 행 클릭 → 상세 패널 열기
- [ ] 페이지네이션 (더보기 또는 페이지 네비)
- [ ] localhost 미연결 시 → 오류 메시지

---

### Step 9 — 설정 페이지 (API Key 등록, 모드 전환, 프로필)

**목표**: 사용자 설정 — 키움 API Key, 모의/실거래 모드, 프로필 정보

**파일**:
- `pages/Settings.tsx` (신규)
  - 섹션 1: 키움 API 설정
    - App Key 입력 (마스크 처리)
    - App Secret 입력 (마스크 처리)
    - 등록 버튼
    - 현재 상태 표시 (🟢 등록됨 / 🔴 미등록)
    - 모드 전환 (모의투자 ↔ 실거래)
  - 섹션 2: 프로필 정보
    - 이메일 (읽기 전용)
    - 닉네임 (수정 가능)
    - 저장 버튼
  - 섹션 3: 알림 설정 (향후)

**API 호출**:
- localClient.setKiwoomKeys(appKey, appSecret) — API Key 등록
- localClient.setMode(mode: 'paper' | 'live') — 모드 전환
- cloudClient.updateProfile(nickname) — 프로필 업데이트
- localClient.getConfig() — 현재 설정 조회

**보안 주의**:
- API Key는 localStorage에 저장하지 않음
- localClient를 통해서만 localhost로 전달
- 화면에 "API Key는 이 PC에만 저장됩니다" 안내 표시

**타입**:
- `types/settings.ts` (신규)
  - KiwoomConfig (appKey, appSecret, mode: 'paper' | 'live', status: 'ok' | 'error')
  - UserProfile (email, nickname, role, created_at)

**검증**:
- [ ] API Key 입력 + 등록 → localhost api 호출
- [ ] 모드 전환 → localhost api 호출 + UI 반영
- [ ] 프로필 수정 → cloudClient 호출
- [ ] 현재 설정 로드 후 UI에 표시
- [ ] localhost 미연결 시 → API Key 등록 불가 경고

---

### Step 10 — 신호등 + 상태 모니터링 (헤더, 토스트 알림)

**목표**: 신호등 시스템 완성 — 실시간 상태 모니터링 + 변화 시 알림

**파일**:
- `components/TrafficLightStatus.tsx` (기존 Step 3에서 확장)
  - 매 5초 갱신
  - 상태 변화 감지 → 토스트 알림 (예: "키움 API 연결 끊김")
  - 호버 시 상세 정보 (마지막 갱신 시간, 상태 메시지)

**토스트 알림**:
- `stores/alertStore.ts` (Zustand)
  - info, warn, error, success 메서드
  - 자동 닫기 (5초)
- `components/AlertContainer.tsx` (신규)
  - 우상단에 토스트 표시

**상태 변화 감지**:
```typescript
// 이전 상태와 비교하여 변화 시에만 알림
if (prevStatus.kiwoom !== currentStatus.kiwoom) {
  addAlert({
    type: currentStatus.kiwoom ? 'success' : 'error',
    message: currentStatus.kiwoom ? '키움 API 연결됨' : '키움 API 연결 끊김'
  })
}
```

**API 호출** (5초 주기):
- cloudClient.healthCheck() — 클라우드 서버
- localClient.getStatus() — 로컬 서버 + 키움 상태

**검증**:
- [ ] 신호등 색상 변화 (green → red → yellow)
- [ ] 상태 변화 시 토스트 알림 표시
- [ ] 매 5초 갱신 (네트워크 요청)
- [ ] 호버 시 상세 정보 표시
- [ ] localhost 연결 불가 → 빨강 + 알림

---

## 2. 파일 목록

### 신규 파일

| 파일 | 용도 |
|------|------|
| `services/cloudClient.ts` | 클라우드 서버 HTTP 클라이언트 |
| `services/localClient.ts` | localhost HTTP 클라이언트 |
| `utils/ws.ts` | WebSocket 관리자 |
| `hooks/useLocalBridgeWS.ts` (완성) | WS 훅 |
| `hooks/useAuth.ts` | 인증 상태 훅 |
| `components/TrafficLightStatus.tsx` | 신호등 |
| `components/UserMenu.tsx` | 사용자 메뉴 |
| `components/PriceTable.tsx` | 실시간 시세 테이블 |
| `components/ExecutionFeed.tsx` | 체결 피드 |
| `components/ConditionEditor.tsx` | 조건 편집기 |
| `components/ConditionRow.tsx` (개선) | 조건 행 |
| `components/LogDetailPanel.tsx` | 로그 상세 |
| `components/AlertContainer.tsx` | 토스트 알림 |
| `components/RuleCard.tsx` | 규칙 카드 |
| `pages/Dashboard.tsx` (개선) | 대시보드 |
| `pages/StrategyBuilder.tsx` (개선) | 전략 빌더 |
| `pages/StrategyList.tsx` | 전략 목록 |
| `pages/ExecutionLog.tsx` (개선) | 실행 로그 |
| `pages/Settings.tsx` | 설정 |
| `types/auth.ts` | 인증 타입 |
| `types/dashboard.ts` | 대시보드 타입 |
| `types/strategy.ts` | 전략 타입 |
| `types/log.ts` | 로그 타입 |
| `types/settings.ts` | 설정 타입 |
| `types/ui.ts` | UI 타입 |
| `stores/alertStore.ts` | 알림 상태 관리 |
| `context/AuthContext.tsx` (개선) | 인증 컨텍스트 |

### 기존 파일 (개선)

| 파일 | 변경 |
|------|------|
| `components/Layout.tsx` | 신호등, 사이드바, 헤더 개선 |
| `pages/Login.tsx` | localClient.setAuthToken() 호출 추가 |
| `pages/Register.tsx` | 이메일 인증 흐름 추가 |
| `pages/Dashboard.tsx` | 시세, 체결, 시장 컨텍스트 추가 |
| `pages/StrategyBuilder.tsx` | localClient.syncRules() 호출 추가 |
| `pages/ExecutionLog.tsx` | 필터, 상세 조회 추가 |
| `App.tsx` | ProtectedRoute, 라우팅 조정 |
| `services/api.ts` | cloudClient로 점진 대체 (하위 호환성 유지) |

---

## 3. 의존성

### Unit 2 (로컬 서버)

| API | 목적 |
|-----|------|
| `POST /api/auth/token` | JWT + Refresh Token 전달 |
| `POST /api/config/kiwoom` | API Key 등록 |
| `GET /api/config` | 설정 조회 |
| `PATCH /api/config` | 설정 변경 (모드 전환) |
| `POST /api/rules/sync` | 규칙 동기화 |
| `GET /api/status` | 서버 상태 |
| `GET /api/logs` | 로그 조회 |
| `POST /api/strategy/start` | 전략 시작 |
| `POST /api/strategy/stop` | 전략 중지 |
| `WS /ws` | 실시간 시세 + 체결 |

**상태**: Unit 2의 로컬 서버 구현 완료 필요

### Unit 4 (클라우드 서버)

| API | 목적 |
|-----|------|
| `POST /api/v1/auth/register` | 회원가입 |
| `POST /api/v1/auth/login` | 로그인 |
| `POST /api/v1/auth/refresh` | 토큰 갱신 |
| `GET /api/v1/rules` | 규칙 조회 |
| `POST /api/v1/rules` | 규칙 생성 |
| `PUT /api/v1/rules/:id` | 규칙 수정 |
| `DEL /api/v1/rules/:id` | 규칙 삭제 |
| `GET /api/v1/context` | 시장 컨텍스트 |
| `GET /api/v1/admin/*` | 어드민 |
| `GET /health` | 헬스 체크 |

**상태**: Unit 4 (API 서버) 구현 병렬 진행

---

## 4. 미결 사항 처리

### 4.1 전략 빌더 조건 타입 확장

**미결**: custom_formula 지원 여부?

**결정**: **Step 6에서는 UI 드롭다운만**
- 지표: RSI, EMA, MACD, 거래량배수, 등 (사전정의 목록)
- 향후 v2에서 custom_formula 추가 검토

### 4.2 localhost 미연결 시 UX

**미결**: 기능 제한 범위?

**결정**:
- **대시보드**: 시세 + 체결 부분만 오류 (나머지 표시 가능)
- **전략 빌더**: 저장 가능 (클라우드), but sync 불가 경고
- **설정**: API Key 등록 불가 (경고 표시)
- **실행 로그**: 조회 불가 (로컬 데이터)

### 4.3 모바일 반응형 필요 여부

**미결**: m.stockvision.app 필요?

**결정**: **Step 1-10에서는 PC 기준** (태블릿 포함)
- Tailwind breakpoints: md (768px) 이상 지원
- 모바일 전용 UI는 v2에서 검토

### 4.4 다크 모드 지원 범위

**미결**: theme switching?

**결정**: **Step 1-10에서는 라이트 모드만**
- HeroUI 컴포넌트는 다크 모드 호환
- next-themes 설치 후 v2에서 추가

### 4.5 브릿지 sync 실패 시 재시도 정책

**미결**: 재시도 횟수, 백오프?

**결정**:
- **Step 6**: localClient.syncRules() 실패 → 토스트 경고 (자동 재시도 없음)
- 로그인 직후 JWT 전달 실패 → 재시도 3회 (1s 백오프)
- 향후 queue 기반 재시도 (v2)

---

## 5. 커밋 계획

| Step | 커밋 메시지 |
|------|-----------|
| 1 | `feat: Step 1 — cloudClient + localClient 구성` |
| 2 | `feat: Step 2 — 인증 UI (로그인, 회원가입, 비밀번호 재설정)` |
| 3 | `feat: Step 3 — 레이아웃 + 라우팅 (사이드바, 신호등, ProtectedRoute)` |
| 4 | `feat: Step 4 — 대시보드 (시세, 체결, 시장 컨텍스트, 신호등)` |
| 5 | `feat: Step 5 — localhost WS 연결 (실시간 시세 + 체결)` |
| 6 | `feat: Step 6 — 전략 빌더 (조건 UI, AND/OR, 저장 + sync)` |
| 7 | `feat: Step 7 — 전략 목록 관리 (CRUD, ON/OFF 토글)` |
| 8 | `feat: Step 8 — 실행 로그 뷰어 (필터, 상세)` |
| 9 | `feat: Step 9 — 설정 페이지 (API Key, 모드, 프로필)` |
| 10 | `feat: Step 10 — 신호등 + 상태 모니터링 (헤더, 토스트)` |

---

## 6. 검증 체크리스트

### 인증
- [ ] 회원가입 → 이메일 확인 → 로그인
- [ ] JWT 저장 + localClient.setAuthToken() 호출
- [ ] 로그아웃 → localStorage 삭제

### 대시보드
- [ ] localhost WS 연결 → 시세 실시간 표시
- [ ] 체결 이벤트 수신 → 피드 갱신
- [ ] 신호등 3개 5초마다 갱신
- [ ] 시장 컨텍스트 표시

### 전략 관리
- [ ] 규칙 생성 → 클라우드 + localhost sync
- [ ] 규칙 수정 → 클라우드 + localhost sync
- [ ] 규칙 삭제 → 클라우드 + localhost sync
- [ ] 규칙 ON/OFF 토글

### 설정
- [ ] API Key 등록 → localhost 저장 (서버 미전송)
- [ ] 모드 전환 (모의 ↔ 실거래)

### 오류 처리
- [ ] localhost 미연결 시 경고 + 기능 제한
- [ ] JWT 만료 → 자동 갱신
- [ ] API 에러 → 토스트 알림

---

## 7. 개발 환경

**프론트엔드 실행**:
```bash
cd frontend
npm install
npm run dev       # http://localhost:5173
```

**API 서버** (병렬):
- 클라우드: `http://localhost:8000/api/v1`
- 로컬: `http://localhost:8765` (WS: `ws://localhost:8765/ws`)

**테스트**:
- 로컬 서버 모의 API 제공 스크립트 (향후)
- Storybook 컴포넌트 테스트 (향후)

---

**마지막 갱신**: 2026-03-05
