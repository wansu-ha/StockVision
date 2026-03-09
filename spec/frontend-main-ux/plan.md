# 프론트엔드 메인 화면 UX 구현 계획서

> 작성일: 2026-03-09 | 상태: 초안 | Unit 5
>
> **spec**: `spec/frontend-main-ux/spec.md`
> **기반 프로토타입**: `frontend/src/pages/ProtoC.tsx` (모든 UI 완성, 100% mock 데이터)

---

## 1. 아키텍처

### 1.1 현재 상태

ProtoC.tsx (701줄)가 단일 파일에 모든 UI를 포함:
- 헤더 (검색, 알림, 톱니바퀴) — inline JSX
- ListView (계좌 요약, 탭, 종목 리스트, 미체결, 체결) — 함수 컴포넌트
- DetailView (차트, 지표, 규칙, 체결) — 함수 컴포넌트
- PriceChart (Lightweight Charts) — 함수 컴포넌트
- 7개 MOCK_* 상수 + generateCandles()

라우팅: `/proto-c` (public, 비인증)

### 1.2 목표 구조

ProtoC를 적절한 단위로 분해하고 mock → 실제 API로 교체.
`/proto-c` → `/` (인증 필수 메인 화면)로 전환.

ProtoC.tsx는 701줄 — 과잉 분해를 피하고 자연스러운 경계로 나눈다.

```
pages/
  MainDashboard.tsx          ← 상태 관리 + 뷰 전환 (~60줄)
  Login.tsx                  ← 다크 테마 리스타일
  Register.tsx               ← 다크 테마 리스타일

components/main/
  Header.tsx                 ← 로고 + 신호등 + 검색 + 알림 + 톱니바퀴 (드롭다운 포함, ~150줄)
  ListView.tsx               ← 계좌 요약 + 탭 + 종목 행 + 미체결 + 체결 (~250줄)
  DetailView.tsx             ← 차트 + 지표 + 컨텍스트 + 규칙 + 체결 (~200줄)
  PriceChart.tsx             ← Lightweight Charts (독립, 복잡도 높아 분리 필수, ~170줄)

hooks/
  useAccountStatus.ts        ← localStatus 폴링 (5s)
  useStockData.ts            ← cloudRules + watchlist + quote 병합
  useMarketContext.ts        ← cloudContext 폴링
```

> **분해 기준**: Header/ListView/DetailView/PriceChart는 각각 독립적 책임 + 100줄 이상.
> 드롭다운(검색/알림/톱니바퀴)은 Header 내부에 유지 (Header에서만 사용).

### 1.3 데이터 흐름

```
AuthContext (jwt/email)
  ↓
MainDashboard
  ├─ useAccountStatus()  → localStatus.get() (5s 폴링)
  │   └─ 계좌잔고, 보유종목, 브로커연결, 엔진상태, 장상태
  ├─ useStockData()      → cloudRules.list() + cloudWatchlist.list()
  │   └─ 내 종목 (규칙 있는 종목), 관심 종목
  ├─ useMarketContext()  → cloudContext.get() (30s 폴링)
  │   └─ KOSPI RSI, KOSDAQ RSI, 시장 추세, 변동성
  ├─ useNotifStore       → WebSocket /ws (useLocalBridgeWS)
  │   └─ 실시간 알림 (체결, 트리거, 연결 변경)
  ├─ cloudStocks.search() → 검색 오버레이 (on-demand)
  └─ cloudBars.get()      → OHLCV 차트 데이터 (on-demand, 상세 진입 시)
```

### 1.4 시세 데이터 소스

백엔드에 시세 API가 이미 구현되어 있다:

| API | 엔드포인트 | 데이터 |
|-----|----------|--------|
| 일봉 OHLCV | `GET /api/v1/stocks/{symbol}/bars?start=&end=` | DailyBar 테이블 캐시 + yfinance fallback |
| 현재가 | `GET /api/v1/stocks/{symbol}/quote` | 지연 시세 (REST) |

프론트엔드 `cloudClient.ts`에 메서드만 추가하면 mock 대체 가능.
yfinance는 무료, 토큰 불필요.

---

## 2. 수정 파일 목록

### 신규 생성

| 파일 | 내용 | 예상 줄수 |
|------|------|----------|
| `pages/MainDashboard.tsx` | 상태 관리 + 뷰 전환 오케스트레이터 | ~60 |
| `components/main/Header.tsx` | 로고 + 신호등 + 검색 오버레이 + 알림 + 톱니바퀴 (드롭다운 포함) | ~150 |
| `components/main/ListView.tsx` | 계좌 요약 + 탭 + 종목 행(아코디언) + 미체결 + 체결 | ~250 |
| `components/main/DetailView.tsx` | 상세 뷰 (지표, 컨텍스트, 규칙 토글+편집, 체결) | ~200 |
| `components/main/PriceChart.tsx` | Lightweight Charts 래퍼 (기간선택, 드래그확대) | ~170 |
| `hooks/useAccountStatus.ts` | localStatus 폴링 (5s) | ~40 |
| `hooks/useStockData.ts` | cloudRules + watchlist + quote 병합 | ~60 |
| `hooks/useMarketContext.ts` | cloudContext 폴링 (30s) | ~30 |

### 수정

| 파일 | 변경 |
|------|------|
| `pages/Login.tsx` | 다크 테마 리스타일 |
| `pages/Register.tsx` | 다크 테마 리스타일 |
| `pages/ForgotPassword.tsx` | 다크 테마 리스타일 |
| `pages/ResetPassword.tsx` | 다크 테마 리스타일 |
| `App.tsx` | `/` → MainDashboard, `/proto-c` 유지(개발용) |
| `services/cloudClient.ts` | 필요시 타입 보강 (StockMasterItem 등) |

### 삭제 없음

ProtoC.tsx는 삭제하지 않고 유지 (비교 참조용).

---

## 3. 구현 순서

### Step 1: 컴포넌트 분해 + 라우팅 (mock 유지)

ProtoC.tsx를 4개 컴포넌트로 분해 + 인증 라우팅 설정.
API 연동 전에 인증 프레임을 먼저 갖춘다 (Step 2에서 API 호출에 JWT 필요).

**작업:**
- `components/main/` 디렉토리 생성
- Header.tsx 추출 (검색/알림/톱니바퀴 드롭다운 포함)
- ListView.tsx 추출 (계좌 요약, 탭, 종목 행, 미체결, 체결)
- DetailView.tsx 추출 (지표, 컨텍스트, 규칙, 체결)
- PriceChart.tsx 추출 (Lightweight Charts 래퍼)
- MainDashboard.tsx 생성 (상태 관리 + 4개 컴포넌트 조합)
- App.tsx: `/` → MainDashboard (ProtectedRoute), `/proto-c` 유지
- GearDropdown 내 로그아웃 → `useAuth().logout()` 연결

**verify:** `npm run dev` → 로그인 후 `/`에서 ProtoC와 동일한 화면. `npx tsc --noEmit` 통과.

### Step 2: 커스텀 훅 + API 연동

mock 데이터를 실제 API 호출로 교체. cloudClient에 시세 메서드 추가.

**작업:**
- `cloudClient.ts`에 `cloudBars.get(symbol, start?, end?)` 추가 (→ `/api/v1/stocks/{symbol}/bars`)
- `cloudClient.ts`에 `cloudQuote.get(symbol)` 추가 (→ `/api/v1/stocks/{symbol}/quote`)
- `useAccountStatus` 훅: `localStatus.get()` 5초 폴링
- `useStockData` 훅: `cloudRules.list()` + `cloudWatchlist.list()` + `cloudQuote.get()`
- `useMarketContext` 훅: `cloudContext.get()` 30초 폴링
- PriceChart: `cloudBars.get()` 연동 (기간 변경 시 API 재호출)
- 알림: 기존 `useNotifStore` (useLocalBridgeWS) 연결
- MainDashboard에서 MOCK_* 상수 제거, 훅으로 교체

**verify:** Network 탭에서 API 호출 확인. 빈 데이터 시 빈 상태 UI. `npx tsc --noEmit` 통과.

### Step 3: 검색 오버레이

헤더 검색바를 실제 `cloudStocks.search()` 연동.

**작업:**
- Header 내 검색 입력 → 300ms 디바운스 → `cloudStocks.search(q, 10)`
- 드롭다운 결과 표시 (다크 테마)
- 종목 선택 → 상세 뷰로 전환 (페이지 이동 없음)
- ESC / 외부 클릭으로 닫기
- 기존 `StockSearch.tsx`의 `doSearch` 로직 참조

**verify:** 검색 → 300ms → API 호출 → 결과 → 선택 → 상세 뷰. `npx tsc --noEmit` 통과.

### Step 4: 규칙 토글 + 인라인 편집 API 연동

**작업:**
- 토글 클릭 → `cloudRules.update(id, { is_active: !current })` → 낙관적 업데이트
- 인라인 편집 저장 → `cloudRules.update(id, payload)`
- 규칙 추가 → `cloudRules.create(payload)`
- 규칙 삭제 → `cloudRules.remove(id)` (확인 모달)

**verify:** 토글 ON↔OFF → API → 새로고침 후 상태 유지. `npx tsc --noEmit` 통과.

### Step 5: 로그인/회원가입 다크 테마

**작업:**
- Login.tsx, Register.tsx, ForgotPassword.tsx, ResetPassword.tsx 스타일 변경
- 배경: `bg-gray-950`, 카드: `bg-gray-900 border-gray-800`, 텍스트: `text-gray-100`
- 버튼: `bg-blue-600 hover:bg-blue-500`, 입력: `bg-gray-800 border-gray-700`
- 기능 로직 변경 없음 (스타일만)

**verify:** `/login`, `/register` → Proto C 다크 테마 통일. `npx tsc --noEmit` 통과.

### Step 6: 툴팁 (용어 설명)

**작업:**
- 금융 용어 데이터 정의 (RSI, MACD, 볼린저, 거래량배수 등)
- 점선 밑줄 스타일 (Tailwind: `decoration-dotted underline cursor-help`)
- 호버/클릭 시 설명 표시 (CSS tooltip 또는 Headless UI Popover)
- 최초 방문 시 힌트 (localStorage 플래그)

**verify:** 지표 라벨 호버 → 설명 팝오버 표시. `npx tsc --noEmit` 통과.

---

## 4. 검증 방법

| 단계 | 검증 |
|------|------|
| 모든 단계 | `npx tsc --noEmit` 통과 |
| 모든 단계 | `npm run build` 성공 (ProtoC 외 기존 에러 제외) |
| Step 1 | 로그인 → `/`에서 ProtoC와 동일한 화면, 로그아웃 → `/login` |
| Step 2 | Network: API 호출, 차트에 실제 OHLCV 표시, 빈 데이터 시 빈 상태 |
| Step 3 | 검색 → 결과 → 선택 → 상세 뷰 전환 |
| Step 4 | 토글/저장 → API → 새로고침 후 상태 유지 |
| Step 5 | 로그인/가입 페이지 Proto C 다크 테마 통일 |
| Step 6 | 용어 호버 → 팝오버 표시 |

---

## 5. 의존성 및 리스크

| 항목 | 설명 | 대응 |
|------|------|------|
| Unit 2 (로컬 서버) API | 계좌, 엔진 상태 | mock fallback 유지, API 가용 시 교체 |
| Unit 4 (클라우드 서버) API | 규칙, 검색, 컨텍스트 | 클라우드 서버 구현 완료, 통합 테스트 필요 |
| 시세 API | `/api/v1/stocks/{symbol}/bars`, `/quote` | 구현 완료 (yfinance, 토큰 불필요). cloudClient 메서드만 추가 |
| WebSocket 연결 | 실시간 알림 | 기존 useLocalBridgeWS 훅 사용, 연결 실패 시 폴링 fallback |
| 반응형 (§3.6) | 태블릿/모바일 대응 | Step 1~6 완료 후 별도 이터레이션 |

---

**마지막 갱신**: 2026-03-09
