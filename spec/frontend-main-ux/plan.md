# 프론트엔드 메인 화면 UX 구현 계획서

> 작성일: 2026-03-09 | 상태: 구현 완료 | Unit 5
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

### 1.5 디자인 개선 사항

ProtoC 프로토타입에 대한 UX 리뷰 결과, 아래 개선 사항을 구현에 반영한다.

#### (A) 색상 충돌 해소 — UI 액센트를 indigo로 분리

하락 색(`blue-400`)과 UI 액센트(`blue-600`)가 동일 계열이라 혼란.

| 용도 | 현재 | 변경 |
|------|------|------|
| 하락 (금융) | `blue-400` | 유지 |
| UI 액센트 (탭, 버튼, 포커스, 링크) | `blue-600`/`blue-500`/`blue-400` | `indigo-600`/`indigo-500`/`indigo-400` |
| 액센트 바 | `blue-500` | `indigo-500` |

#### (B) 아코디언 확장 어포던스

행이 확장 가능하다는 시각적 단서가 부족.

| 플랫폼 | 어포던스 |
|--------|---------|
| 데스크톱 | 호버 시 하단 발광 (그라디언트 `via-indigo-500/30`) + 기존 왼쪽 액센트 바 |
| 터치/첫 방문 | 첫 번째 행 자동 확장 + 힌트 텍스트 "행을 탭하면 지표를 볼 수 있습니다" (1회, localStorage) |

#### (C) 계좌 요약 위계 강화

총 평가와 수익률을 1행에 강조, 보조 정보를 2행으로 분리.

```
15,650,000원          +1.2% ▲     ← text-2xl bold + 수익률 배지
주문가능 3,200,000 │ 보유 2종목 │ ● 장중    ← text-sm gray-400
```

#### (D) 빈 상태 UI

종목 0개, 체결 0건 등 데이터 없을 때 안내 카드 표시.
각 영역별 1~2줄 안내 텍스트 + 액션 버튼 1개.

#### (E) 뷰 전환 애니메이션

목록 ↔ 상세 전환 시 fade + translateY (200ms 이내).
아코디언 확장/축소 시 max-height transition (150ms).

#### (F) 접근성 최소 기준

| 요소 | 속성 |
|------|------|
| 토글 | `role="switch"` + `aria-checked` |
| 행 확장 | `aria-expanded` + `aria-controls` |
| 드롭다운 | `aria-haspopup` + `aria-expanded` + ESC 닫기 |
| 검색 | `role="combobox"` + `aria-autocomplete` |

#### (G) 규칙 편집 IF/THEN 구조화

조건(IF)과 액션(THEN)을 시각적으로 분리. 라벨 `text-[10px] uppercase tracking-wider`.

#### (H) 엔진 제어 확인

톱니바퀴 드롭다운에서 엔진 중지/Kill 클릭 시 인라인 확인 ("엔진을 중지합니까? [확인] [취소]").

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

### Step 1: 컴포넌트 분해 + 라우팅 + 디자인 개선 (mock 유지)

ProtoC.tsx를 4개 컴포넌트로 분해 + 인증 라우팅 설정 + 디자인 개선 동시 적용.
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
- **(A) 색상**: blue 액센트 → indigo 전체 교체 (탭, 버튼, 포커스, 링크, 액센트 바)
- **(B) 아코디언**: 호버 시 하단 발광 + 첫 방문 시 첫 행 자동 확장 + 힌트 (localStorage)
- **(C) 계좌 요약**: 총 평가(text-2xl) + 수익률 배지 1행, 보조 정보 2행 레이아웃
- **(E) 애니메이션**: 목록↔상세 fade+translateY (200ms), 아코디언 max-height transition (150ms)
- **(F) 접근성**: 각 컴포넌트에 aria 속성 적용 (토글, 확장, 드롭다운)
- **(H) 엔진 확인**: 톱니바퀴 중지/Kill 인라인 확인 UI

**verify:** `npm run dev` → 로그인 후 `/`에서 ProtoC와 동일한 화면 + 디자인 개선 확인. `npx tsc --noEmit` 통과.

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

- **(D) 빈 상태**: 각 영역(종목 리스트, 체결, 차트) 빈 데이터 시 안내 카드 표시

**verify:** Network 탭에서 API 호출 확인. 빈 데이터 시 빈 상태 UI 표시. `npx tsc --noEmit` 통과.

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
- **(G) IF/THEN 구조화**: 편집 UI를 조건(IF)/액션(THEN) 영역으로 시각 분리

**verify:** 토글 ON↔OFF → API → 새로고침 후 상태 유지. `npx tsc --noEmit` 통과.

### Step 5: 로그인/회원가입 다크 테마

**작업:**
- Login.tsx, Register.tsx, ForgotPassword.tsx, ResetPassword.tsx 스타일 변경
- 배경: `bg-gray-950`, 카드: `bg-gray-900 border-gray-800`, 텍스트: `text-gray-100`
- 버튼: `bg-indigo-600 hover:bg-indigo-500`, 입력: `bg-gray-800 border-gray-700`
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
| Step 1 | indigo 액센트 적용 확인 (탭, 버튼, 링크에 blue 없음) |
| Step 1 | 종목 행 호버 시 하단 발광, 첫 방문 시 첫 행 자동 확장 |
| Step 1 | 계좌 요약 2행 레이아웃, 목록↔상세 전환 애니메이션 |
| Step 2 | Network: API 호출, 차트에 실제 OHLCV 표시 |
| Step 2 | 빈 데이터 시 각 영역별 빈 상태 안내 카드 표시 |
| Step 3 | 검색 → 결과 → 선택 → 상세 뷰 전환 |
| Step 4 | 토글/저장 → API → 새로고침 후 상태 유지 |
| Step 4 | 규칙 편집 IF/THEN 영역 분리 확인 |
| Step 5 | 로그인/가입 페이지 Proto C 다크 테마 통일 (indigo 버튼) |
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

**마지막 갱신**: 2026-03-09 (디자인 리뷰 반영, 상태 확정)
