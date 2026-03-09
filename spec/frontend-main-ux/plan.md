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

ProtoC를 컴포넌트로 분해하고 mock → 실제 API로 교체.
`/proto-c` → `/` (인증 필수 메인 화면)로 전환.

```
pages/
  MainDashboard.tsx          ← ProtoC를 리네임, 상태/데이터 관리
  Login.tsx                  ← 다크 테마 리스타일
  Register.tsx               ← 다크 테마 리스타일

components/main/
  Header.tsx                 ← 로고 + 신호등 + 검색 + 알림 + 톱니바퀴
  SearchOverlay.tsx          ← cloudStocks.search() 연동
  NotificationDropdown.tsx   ← useNotifStore 연동
  GearDropdown.tsx           ← 엔진/연결/사용자
  AccountSummary.tsx         ← localStatus → 계좌 정보
  StockList.tsx              ← 탭 + 아코디언 종목 행
  StockRow.tsx               ← 단일 종목 행 + 확장 영역
  PendingOrders.tsx          ← 미체결 주문 테이블
  ExecutionHistory.tsx       ← 체결 내역 테이블
  DetailView.tsx             ← 상세 뷰 (차트, 지표, 규칙, 체결)
  PriceChart.tsx             ← Lightweight Charts 래퍼
  RuleCard.tsx               ← 규칙 카드 (토글 + 편집)

hooks/
  useAccountStatus.ts        ← localStatus 폴링 (5s)
  useStockData.ts            ← cloudRules + watchlist 병합
  useMarketContext.ts        ← cloudContext 폴링
```

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
  └─ cloudStocks.search() → 검색 오버레이 (on-demand)
```

---

## 2. 수정 파일 목록

### 신규 생성

| 파일 | 내용 |
|------|------|
| `components/main/Header.tsx` | 헤더 (로고, 검색, 알림, 톱니바퀴) |
| `components/main/SearchOverlay.tsx` | 검색 오버레이 (cloudStocks.search) |
| `components/main/NotificationDropdown.tsx` | 알림 드롭다운 (useNotifStore) |
| `components/main/GearDropdown.tsx` | 톱니바퀴 드롭다운 |
| `components/main/AccountSummary.tsx` | 계좌 요약 카드 |
| `components/main/StockList.tsx` | 탭 + 종목 리스트 |
| `components/main/StockRow.tsx` | 종목 행 (아코디언) |
| `components/main/PendingOrders.tsx` | 미체결 주문 |
| `components/main/ExecutionHistory.tsx` | 체결 내역 |
| `components/main/DetailView.tsx` | 상세 뷰 |
| `components/main/PriceChart.tsx` | 가격 차트 |
| `components/main/RuleCard.tsx` | 규칙 카드 |
| `hooks/useAccountStatus.ts` | 계좌 상태 폴링 훅 |
| `hooks/useStockData.ts` | 종목+규칙 데이터 훅 |
| `hooks/useMarketContext.ts` | 시장 컨텍스트 훅 |
| `pages/MainDashboard.tsx` | 메인 대시보드 (ProtoC 리네임) |

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

### Step 1: 컴포넌트 분해 (mock 유지)

ProtoC.tsx의 inline JSX를 `components/main/` 파일들로 추출.
동작은 동일하되 파일만 분리. mock 데이터는 그대로 props로 전달.

**작업:**
- `components/main/` 디렉토리 생성
- Header, AccountSummary, StockList, StockRow, PendingOrders, ExecutionHistory, DetailView, PriceChart, RuleCard 추출
- SearchOverlay, NotificationDropdown, GearDropdown 추출
- MainDashboard.tsx 생성 (ProtoC 구조 유지, 컴포넌트 조합)

**verify:** `npm run dev` → `/proto-c`와 동일한 화면 렌더링. `npx tsc --noEmit` 통과.

### Step 2: 커스텀 훅 + API 연동

mock 데이터를 실제 API 호출로 교체.

**작업:**
- `useAccountStatus` 훅: `localStatus.get()` 5초 폴링, 계좌/보유/엔진/연결 상태
- `useStockData` 훅: `cloudRules.list()` → 규칙이 걸린 종목 추출 (내 종목), `cloudWatchlist.list()` (관심 종목)
- `useMarketContext` 훅: `cloudContext.get()` 30초 폴링
- 알림: 기존 `useNotifStore` (useLocalBridgeWS) 연결
- MainDashboard에서 mock 상수 제거, 훅으로 교체

**verify:** 브라우저 Network 탭에서 API 호출 확인. 빈 데이터 시 빈 상태 UI 표시. `npx tsc --noEmit` 통과.

### Step 3: 검색 오버레이

헤더 검색바를 실제 `cloudStocks.search()` 연동.

**작업:**
- SearchOverlay: 300ms 디바운스, 드롭다운 결과 (최대 10건)
- 기존 `StockSearch.tsx`의 `doSearch` 로직 참조 (재사용)
- 종목 선택 → 상세 뷰로 전환 (페이지 이동 없음, `setView('detail')`)
- ESC / 외부 클릭으로 닫기
- 다크 테마 스타일

**verify:** 검색어 입력 → 300ms 후 API 호출 → 결과 드롭다운 → 선택 시 상세 뷰. `npx tsc --noEmit` 통과.

### Step 4: 규칙 토글 + 인라인 편집 API 연동

**작업:**
- 토글 클릭 → `cloudRules.update(id, { is_active: !current })` → 낙관적 업데이트
- 인라인 편집 저장 → `cloudRules.update(id, payload)`
- 규칙 추가 → `cloudRules.create(payload)`
- 규칙 삭제 → `cloudRules.remove(id)` (확인 모달)

**verify:** 토글 ON↔OFF → API 호출 확인 → 새로고침 후 상태 유지. `npx tsc --noEmit` 통과.

### Step 5: 라우팅 전환 + 인증 연결

**작업:**
- App.tsx: `/` 라우트 → MainDashboard (ProtectedRoute 내부)
- `/proto-c` 라우트 유지 (개발용 비교)
- MainDashboard에서 AuthContext의 jwt/email 활용
- GearDropdown: `useAuth().logout()` 연결
- 미인증 시 `/login`으로 리다이렉트 (기존 ProtectedRoute 동작)

**verify:** 로그아웃 → `/login` 이동. 로그인 → `/` 메인 대시보드 표시. `npx tsc --noEmit` 통과.

### Step 6: 로그인/회원가입 다크 테마

**작업:**
- Login.tsx, Register.tsx, ForgotPassword.tsx, ResetPassword.tsx 스타일 변경
- 배경: `bg-gray-950`, 카드: `bg-gray-900 border-gray-800`, 텍스트: `text-gray-100`
- 버튼: `bg-blue-600 hover:bg-blue-500`
- 입력: `bg-gray-800 border-gray-700`
- 기능 로직 변경 없음 (스타일만)

**verify:** `/login`, `/register` 페이지 → Proto C와 통일된 다크 테마. `npx tsc --noEmit` 통과.

### Step 7: 툴팁 (용어 설명)

**작업:**
- 금융 용어 데이터 정의 (RSI, MACD, 볼린저, 거래량배수 등)
- 점선 밑줄 스타일 적용 (Tailwind: `decoration-dotted underline cursor-help`)
- 호버/클릭 시 설명 표시 (CSS tooltip 또는 Headless UI Popover)
- 최초 방문 시 힌트 (localStorage 플래그)

**verify:** 지표 라벨 호버 → 설명 팝오버 표시. `npx tsc --noEmit` 통과.

---

## 4. 검증 방법

| 단계 | 검증 |
|------|------|
| 모든 단계 | `npx tsc --noEmit` 통과 |
| 모든 단계 | `npm run build` 성공 (ProtoC 외 기존 에러 제외) |
| Step 1 | `/proto-c`와 시각적으로 동일 |
| Step 2 | Network 탭에서 API 호출 확인, 빈 데이터 시 빈 상태 표시 |
| Step 3 | 검색 → 결과 → 선택 → 상세 뷰 전환 |
| Step 4 | 토글/저장 → API → 새로고침 후 상태 유지 |
| Step 5 | 인증 흐름: 로그인 → 메인 → 로그아웃 → 로그인 |
| Step 6 | 로그인/가입 페이지 스크린샷 비교 |
| Step 7 | 용어 호버 → 팝오버 표시 |

---

## 5. 의존성 및 리스크

| 항목 | 설명 | 대응 |
|------|------|------|
| Unit 2 (로컬 서버) API | 계좌, 엔진 상태 | mock fallback 유지, API 가용 시 교체 |
| Unit 4 (클라우드 서버) API | 규칙, 검색, 컨텍스트 | 클라우드 서버 구현 완료 상태, 통합 테스트 필요 |
| WebSocket 연결 | 실시간 알림 | 기존 useLocalBridgeWS 훅 사용, 연결 실패 시 폴링 fallback |
| 반응형 (§3.6) | 태블릿/모바일 대응 | Step 1~7 완료 후 별도 이터레이션 |

---

**마지막 갱신**: 2026-03-09
