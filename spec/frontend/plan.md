# 프론트엔드 구현 계획서 (frontend)

> 작성일: 2026-03-05 | 상태: 초안 | Unit 5 (Phase 3-B)
> 갱신: 2026-03-09 — 싱글 페이지 확정, Trading/Portfolio 삭제, 구현 단계 재정리

---

## 0. 현황

### 0.1 기존 코드 (Phase 1-2)

**위치**: `frontend/src/`

**기존 기술**: React 19, TypeScript, Vite, Tailwind CSS, HeroUI, React Router, React Query, Zustand, Axios

**기존 라우팅** (App.tsx):
- `/login`, `/register`, `/forgot-password`, `/reset-password` (인증)
- `/onboarding` (온보딩)
- `/` (Dashboard), `/stocks`, `/stocks/:symbol`, `/trading`, `/logs`, `/strategies`, `/portfolio`, `/templates`, `/admin`

**구현 상태**:
- ✅ 인증 (Login, Register, ForgotPassword, ResetPassword, AuthContext)
- ✅ 온보딩 (6단계)
- ✅ Layout (상단 navbar + 6개 메뉴)
- ✅ TrafficLightStatus, StockSearch, ConditionEditor, ExecutionFeed, RuleCard
- ✅ Settings (API Key 등록)
- ✅ ExecutionLog (체결 로그 뷰어)
- ✅ AdminDashboard (통계+유저+템플릿 단일 페이지)
- ⚠️ localClient.ts (기본 구조만)
- ⚠️ useLocalBridgeWS.ts (스켈레톤)
- ❌ 싱글 페이지 대시보드 (현재 Hero+퀵액션)
- ❌ 종목 상세 패널 (현재 별도 페이지)
- ❌ 규칙 편집 모달 (현재 별도 페이지)
- ❌ 엔진 제어 (시작/중지/Kill Switch)
- ❌ 관심종목 실시간 테이블

**주요 변경:**
- ❌ Trading.tsx, Portfolio.tsx → **삭제** (Spec 범위 외)
- ❌ StockList.tsx, StockDetail.tsx → **통합/전환** (싱글 페이지)
- ❌ StrategyBuilder.tsx → **모달로 전환**
- ❌ navbar 6개 메뉴 → **상단바만** (검색+알림+유저메뉴)

---

## 1. 구현 단계

### Step 1 — 정리: 불필요 파일 삭제 + 라우팅 변경

**목표**: Phase 2 레거시 제거, Spec 라우팅으로 단순화

**삭제 파일**:
```
pages/Trading.tsx
pages/Portfolio.tsx
pages/StockList.tsx
pages/StockDetail.tsx
pages/StrategyBuilder.tsx
pages/Templates.tsx
pages/AdminDashboard.tsx
services/portfolio.ts
services/dashboard.ts
services/templates.ts
types/dashboard.ts
types/trading.ts
components/VolumeChart.tsx
components/StockChart.tsx
components/PriceTable.tsx
components/MarketContext.tsx
components/AIStockAnalysis.tsx
components/BridgeInstaller.tsx
components/RiskDisclosure.tsx
```

**수정 파일**:
- `App.tsx` — 라우팅 단순화:
  ```
  /              → Dashboard (싱글 페이지)
  /login         → Login
  /register      → Register
  /forgot-password → ForgotPassword
  /reset-password  → ResetPassword
  /onboarding    → Onboarding
  /settings      → Settings
  /logs          → ExecutionLog
  /admin/*       → Admin (Unit 6)
  ```
- `Layout.tsx` — navbar 메뉴 제거, 상단바만:
  - 좌측: 로고 + 신호등
  - 중앙: 검색바
  - 우측: 알림 벨 + 유저 메뉴
- `UserMenu.tsx` — 드롭다운에 "실행 로그", "설정" 링크 추가

**검증**:
- [ ] 삭제한 파일 import 참조 없음 (빌드 통과)
- [ ] 라우팅 정상 동작
- [ ] 상단바 레이아웃 확인

---

### Step 2 — API 클라이언트 정비

**목표**: 클라우드/로컬 서버 API 클라이언트 보강 + 타입 정리

**파일**:
- `services/cloudClient.ts` (수정) — 누락 API 추가:
  - 규칙 CRUD (getRules, createRule, updateRule, deleteRule)
  - 관심종목 CRUD (getWatchlist, addWatchlist, deleteWatchlist)
  - 종목 검색 (searchStocks)
  - 종목 지표 (getIndicators)
- `services/localClient.ts` (수정) — 엔진 제어 API 추가:
  - 엔진 시작/중지/Kill Switch (startEngine, stopEngine, killSwitch, unlockEngine)
  - 상태 조회 (getStatus)
  - 로그 조회 (getLogs)
  - JWT 전달 (setAuthToken)
  - 규칙 sync (syncRules)
  - API Key 등록 (setKisKeys)
- `types/` — 불필요 타입 삭제, 백엔드 스키마 기준으로 정리

**검증**:
- [ ] cloudClient.getRules() 호출 → 규칙 목록 반환
- [ ] localClient.getStatus() 호출 → 상태 반환
- [ ] localClient.startEngine() / stopEngine() 동작
- [ ] TypeScript strict 모드 통과

---

### Step 3 — 메인 싱글 페이지 (`/`)

**목표**: 대시보드를 엔진 상태 + 관심종목 테이블 + 최근 체결 피드로 재작성

**파일**:
- `pages/Dashboard.tsx` — 전면 재작성

**새 컴포넌트**:
- `components/EngineControl.tsx` — 엔진 상태 바
  - 실행 상태 표시 (🟢 실행 중 / ⏸ 중지됨 / 🔒 Kill Switch)
  - [시작] / [중지] 버튼
  - [Kill Switch] 버튼 (확인 다이얼로그)
  - 오늘 체결 수 표시
  - API: localClient.startEngine(), stopEngine(), killSwitch(), unlockEngine()

- `components/WatchlistTable.tsx` — 관심종목 실시간 테이블
  - 컬럼: 종목명, 현재가, 변동률, 활성 규칙 수, 최근 체결
  - 행 클릭 → StockDetailPanel 열기
  - [+ 종목 추가] → StockSearch 오버레이
  - 실시간 가격: WS에서 수신
  - API: cloudClient.getWatchlist(), cloudClient.getRules()

**기존 컴포넌트 배치**:
- `ExecutionFeed` — 대시보드 하단에 배치 (최근 체결 5-10건)

**검증**:
- [ ] 대시보드 로드 → 엔진 상태 바 + 관심종목 테이블 + 체결 피드 표시
- [ ] 엔진 시작/중지 버튼 동작
- [ ] 관심종목 테이블 행 클릭 → 종목 상세 패널 열림
- [ ] [종목 추가] → 검색 → 관심종목 등록

---

### Step 4 — 종목 상세 패널 (슬라이드)

**목표**: 관심종목 클릭 시 우측 슬라이드 패널로 종목 상세 + 규칙 목록 표시

**파일**:
- `components/StockDetailPanel.tsx` — NEW
  - 종목명 + 현재가 + 등락률
  - 현재 지표 섹션 (RSI, MACD, 거래량배수 등)
  - 이 종목의 규칙 목록 (RuleCard 재사용)
    - 규칙 ON/OFF 토글
    - [수정] → RuleEditModal
    - [삭제] → 확인 다이얼로그
  - [+ 규칙 추가] → RuleEditModal
  - [관심 종목 해제] 버튼
  - 닫기 버튼 + 외부 클릭 닫기
  - API: cloudClient.getIndicators(symbol), cloudClient.getRules(symbol)

**검증**:
- [ ] 관심종목 클릭 → 우측에서 슬라이드 인
- [ ] 지표 값 표시
- [ ] 규칙 목록 표시 + ON/OFF 토글
- [ ] [규칙 추가] → 모달 열림
- [ ] [관심 종목 해제] → 목록에서 제거 + 패널 닫기
- [ ] [× 닫기] / 외부 클릭 → 패널 닫기

---

### Step 5 — 규칙 편집 모달

**목표**: 종목 상세에서 규칙 생성/수정 모달

**파일**:
- `components/RuleEditModal.tsx` — NEW
  - 종목 자동 바인딩 (StockDetailPanel에서 열릴 때)
  - 조건 섹션: ConditionEditor 재사용 (매수/매도 조건)
  - 실행 섹션: 방향(매수/매도), 수량, 유형(시장가/지정가)
  - 버튼: [저장], [저장 + 활성화], [취소]

**저장 흐름**:
```typescript
async function saveRule(rule: Rule) {
  // 1. 클라우드에 저장
  await cloudClient.saveRule(rule);
  // 2. localhost에 즉시 sync
  try {
    await localClient.syncRules();
  } catch {
    toast.warn("로컬 서버 미연결 — 규칙은 서버에 저장되었습니다");
  }
  // 3. 모달 닫기 + 패널/대시보드 갱신
  closeModal();
  queryClient.invalidateQueries(['rules']);
}
```

**검증**:
- [ ] 조건 추가/삭제/수정 동작
- [ ] AND/OR 토글 동작
- [ ] 저장 → cloudClient + localClient sync
- [ ] localhost 미연결 시 → 경고 Toast (저장은 성공)
- [ ] 기존 규칙 수정 → 기존 값 로드

---

### Step 6 — WS 실시간 연동

**목표**: localhost WebSocket으로 실시간 시세 + 체결 스트리밍

**파일**:
- `hooks/useLocalBridgeWS.ts` — 완성/강화
  - 메시지 타입 분류:
    - `quote` → 시세 업데이트 → WatchlistTable 반영
    - `fill` → 체결 알림 → ExecutionFeed + Toast
    - `status_change` → 엔진/KIS 상태 → EngineControl 반영
  - 자동 재연결 (exponential backoff: 1s → 5s → 30s)
  - 연결 상태 표시 (connected / reconnecting / disconnected)

**컴포넌트 통합**:
- WatchlistTable: `quote` 이벤트로 가격 갱신 (< 200ms)
- ExecutionFeed: `fill` 이벤트로 체결 추가
- EngineControl: `status_change` 이벤트로 상태 반영
- ToastContainer: `fill` 이벤트로 체결 알림

**검증**:
- [ ] WS 연결 성공 → isConnected = true
- [ ] 시세 메시지 → WatchlistTable 가격 갱신 (< 200ms)
- [ ] 체결 메시지 → ExecutionFeed 추가 + Toast 알림
- [ ] 연결 끊김 → 자동 재연결
- [ ] localhost 미실행 → 재연결 시도 + 상태 표시

---

### Step 7 — 오프라인 대응

**목표**: 클라우드 서버 미연결 시 UX 처리

**구현**:
- 에러 배너: "서버 점검 중 — 자동 매매는 정상 작동합니다"
- 종목 검색: localClient.searchStocks() fallback
- 규칙 저장: localClient에 저장 → sync_queue → 복구 후 flush
- 관심종목: localClient.getWatchlist() 캐시 사용
- JWT 만료: 갱신 불가 경고

**검증**:
- [ ] 클라우드 미연결 → 에러 배너 표시
- [ ] 종목 검색 → 로컬 캐시 fallback
- [ ] 클라우드 복구 → 배너 사라짐 + sync

---

### Step 8 — 설정 + 온보딩 + 로그 검수

**목표**: 기존 페이지 동작 확인 + 미비점 보완

**검수 대상**:
- `Settings.tsx` — KIS API Key 등록 → localClient.setKisKeys() 동작 확인
  - 모의투자/실거래 모드 전환
  - "API Key는 이 PC에만 저장됩니다" 안내
- `Onboarding.tsx` — 6단계 흐름 확인
- `ExecutionLog.tsx` — localClient.getLogs() 연동 확인
  - 필터 (날짜, 종목, 상태)
  - localhost 미연결 시 오류 메시지

**검증**:
- [ ] API Key 등록 → localhost 저장 (서버 미전송)
- [ ] 온보딩 완료 → 대시보드 이동
- [ ] 실행 로그 조회 + 필터

---

## 2. 파일 구조 (최종)

```
frontend/src/
├── components/
│   ├── Layout.tsx               # 수정: navbar 제거, 상단바만
│   ├── TrafficLightStatus.tsx   # 유지
│   ├── StockSearch.tsx          # 유지
│   ├── ConditionEditor.tsx      # 유지
│   ├── ConditionRow.tsx         # 유지
│   ├── ExecutionFeed.tsx        # 유지
│   ├── RuleCard.tsx             # 유지
│   ├── NotificationCenter.tsx   # 유지
│   ├── UserMenu.tsx             # 수정: 로그/설정 링크 추가
│   ├── AdminGuard.tsx           # 유지
│   ├── AlertContainer.tsx       # 유지
│   ├── ToastContainer.tsx       # 유지
│   ├── EngineControl.tsx        # NEW
│   ├── WatchlistTable.tsx       # NEW
│   ├── StockDetailPanel.tsx     # NEW
│   └── RuleEditModal.tsx        # NEW
├── pages/
│   ├── Dashboard.tsx            # 전면 재작성 (싱글 페이지)
│   ├── Login.tsx                # 유지
│   ├── Register.tsx             # 유지
│   ├── ForgotPassword.tsx       # 유지
│   ├── ResetPassword.tsx        # 유지
│   ├── Onboarding.tsx           # 유지
│   ├── Settings.tsx             # 유지
│   ├── ExecutionLog.tsx         # 유지
│   └── Admin/                   # Unit 6에서 구현
├── services/
│   ├── api.ts                   # 기존 유지 (하위 호환)
│   ├── cloudClient.ts           # 수정: 규칙/관심종목 API 보강
│   ├── localClient.ts           # 수정: 엔진 제어 API 추가
│   ├── auth.ts                  # 유지
│   ├── admin.ts                 # 유지 (Unit 6에서 확장)
│   ├── rules.ts                 # 유지
│   ├── logs.ts                  # 유지
│   └── onboarding.ts            # 유지
├── hooks/
│   └── useLocalBridgeWS.ts      # 수정: 이벤트 타입 분류 강화
├── context/
│   └── AuthContext.tsx           # 유지
├── stores/
│   ├── alertStore.ts            # 유지
│   └── toastStore.ts            # 유지
├── types/
│   ├── index.ts                 # 유지
│   ├── stock.ts                 # 유지
│   ├── strategy.ts              # 유지
│   ├── auth.ts                  # 유지
│   ├── log.ts                   # 유지
│   ├── settings.ts              # 유지
│   └── ui.ts                    # 유지
└── App.tsx                      # 수정: 라우팅 단순화
```

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
| `GET /api/watchlist` | 관심종목 캐시 |
| `GET /api/stocks/search` | 종목 검색 (오프라인 fallback) |
| `POST /api/strategy/start` | 엔진 시작 |
| `POST /api/strategy/stop` | 엔진 중지 |
| `POST /api/strategy/kill` | Kill Switch |
| `POST /api/strategy/unlock` | Kill Switch 해제 |
| `WS /ws` | 실시간 시세 + 체결 |

### Unit 4 (클라우드 서버)

| API | 목적 |
|-----|------|
| `POST /api/v1/auth/register, login, refresh` | 인증 |
| `GET/POST/PUT/DELETE /api/v1/rules` | 규칙 CRUD |
| `GET/POST/DELETE /api/v1/watchlist` | 관심종목 CRUD |
| `GET /api/v1/stocks/search` | 종목 검색 |
| `GET /api/v1/stocks/:symbol/indicators` | 종목 지표 |

---

## 4. 커밋 계획

| Step | 커밋 메시지 |
|------|-----------|
| 1 | `refactor: 레거시 페이지 삭제 + 싱글 페이지 라우팅 전환` |
| 2 | `feat: cloudClient/localClient API 보강 + 타입 정리` |
| 3 | `feat: 싱글 페이지 대시보드 (EngineControl + WatchlistTable + ExecutionFeed)` |
| 4 | `feat: 종목 상세 슬라이드 패널 (StockDetailPanel)` |
| 5 | `feat: 규칙 편집 모달 (RuleEditModal + 클라우드/로컬 sync)` |
| 6 | `feat: localhost WS 실시간 연동 (시세 + 체결 + 상태)` |
| 7 | `feat: 오프라인 대응 (에러 배너 + fallback + sync_queue)` |
| 8 | `fix: 설정/온보딩/실행 로그 검수` |

---

## 5. 검증 체크리스트

### 인증
- [ ] 회원가입 → 이메일 확인 → 로그인
- [ ] JWT 저장 + localClient.setAuthToken() 호출
- [ ] 로그아웃 → localStorage 삭제

### 대시보드
- [ ] 엔진 시작/중지/Kill Switch 동작
- [ ] 관심종목 테이블 실시간 가격 표시 (WS)
- [ ] 체결 이벤트 수신 → 피드 갱신 + Toast
- [ ] 신호등 1개 (통합) 5초마다 갱신

### 종목 상세 + 규칙
- [ ] 관심종목 클릭 → 슬라이드 패널
- [ ] 규칙 생성 → 클라우드 + localhost sync
- [ ] 규칙 수정/삭제/ON/OFF
- [ ] localhost 미연결 시 경고

### 설정
- [ ] API Key 등록 → localhost 저장 (서버 미전송)
- [ ] 모드 전환 (모의 ↔ 실거래)

### 빌드
- [ ] `npm run lint` 통과
- [ ] `npm run build` 성공

---

**마지막 갱신**: 2026-03-09
