# 프론트엔드 레이아웃 통일 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 대시보드와 나머지 페이지의 헤더/네비/레이아웃을 통합 UnifiedLayout으로 통일하고, 하단 상태 바를 추가한다.

**Architecture:** Outlet 기반 `UnifiedLayout`을 만들어 모든 보호 라우트를 감싼다. 기존 `Layout.tsx`와 `Header.tsx`를 대체. 컴포넌트는 `components/layout/` 디렉터리에 모은다. 상태 데이터는 기존 `useAccountStatus`, `useMarketContext`, `useNotifStore` 훅을 재사용한다.

**Tech Stack:** React 19, TypeScript, Tailwind CSS, React Router, Zustand

**Spec:** `spec/frontend-layout-consistency/spec.md`

**Prototype:** `.superpowers/brainstorm/984-1774886349/content/full-prototype-v2.html`

---

## 현재 구조 → 목표 구조

```
현재:
  /              → ProtectedRoute → MainDashboard (자체 Header.tsx)
  /settings      → ProtectedRoute → Settings (자체 헤더)
  /strategies/*  → ProtectedRoute → Layout.tsx → {children}
  /backtest      → ProtectedRoute → Layout.tsx → {children}
  ...

목표:
  /admin/*       → AdminGuard → 기존 유지 (이번 범위 밖)
  /              → ProtectedRoute → UnifiedLayout (Outlet) → MainDashboard
  /settings      → ProtectedRoute → UnifiedLayout (Outlet) → Settings
  /strategies/*  → ProtectedRoute → UnifiedLayout (Outlet) → ...
  /backtest      → ProtectedRoute → UnifiedLayout (Outlet) → ...
```

## 파일 구조

| 구분 | 파일 | 역할 |
|------|------|------|
| 신규 | `src/components/layout/UnifiedLayout.tsx` | Outlet 기반 통합 레이아웃 |
| 신규 | `src/components/layout/UnifiedHeader.tsx` | 헤더 (로고 + 검색 + 알림 + 아바타) |
| 신규 | `src/components/layout/NavTabs.tsx` | 네비 탭 |
| 신규 | `src/components/layout/AccountDropdown.tsx` | 계정 드롭다운 |
| 신규 | `src/components/layout/StatusBar.tsx` | 하단 상태 바 |
| 신규 | `src/components/layout/MobileMenu.tsx` | 모바일 풀스크린 메뉴 |
| 수정 | `src/App.tsx` | 라우트 구조 변경 |
| 수정 | `src/pages/MainDashboard.tsx` | Header import 제거 |
| 수정 | `tailwind.config.js` | 시맨틱 색상 토큰 (선택) |

---

### Task 1: layout 디렉토리 + StatusBar 컴포넌트

**Files:**
- Create: `src/components/layout/StatusBar.tsx`

상태 바는 독립적이고 다른 컴포넌트에 의존하지 않으므로 먼저 만든다.

- [ ] **Step 1: StatusBar.tsx 작성**

```tsx
import { useAccountStatus } from '../../hooks/useAccountStatus'

interface StatusItem {
  label: string
  ok: boolean
}

export default function StatusBar() {
  const { engineRunning, brokerConnected } = useAccountStatus()

  // 로컬은 useAccountStatus가 응답하면 연결된 것
  const items: StatusItem[] = [
    { label: '로컬', ok: true },
    { label: '브로커', ok: brokerConnected },
    { label: '클라우드', ok: true }, // TODO: cloudStatus 추가 시 교체
    { label: '엔진', ok: engineRunning },
  ]

  return (
    <div className="sticky bottom-0 z-40 bg-[#16162a] border-t border-[#2d2d4a] px-8 py-1 flex justify-between text-[11px]">
      <div className="flex gap-3.5">
        {items.map((item) => (
          <span key={item.label} className="flex items-center gap-1">
            <span className={`w-2 h-2 rounded-full ${item.ok ? 'bg-green-500' : 'bg-gray-500'}`} />
            {item.label}
          </span>
        ))}
      </div>
      <span className="text-gray-500">장전</span>
    </div>
  )
}
```

- [ ] **Step 2: import 확인**

```bash
cd frontend && npx tsc --noEmit 2>&1 | head -20
```

- [ ] **Step 3: 커밋**

```bash
git add src/components/layout/StatusBar.tsx
git commit -m "feat: StatusBar 컴포넌트 (하단 고정 상태 바)"
```

---

### Task 2: NavTabs 컴포넌트

**Files:**
- Create: `src/components/layout/NavTabs.tsx`

- [ ] **Step 1: NavTabs.tsx 작성**

```tsx
import { Link, useLocation } from 'react-router-dom'

const tabs = [
  { label: '대시보드', path: '/' },
  { label: '전략', path: '/strategies' },
  { label: '백테스트', path: '/backtest' },
  { label: '관심종목', path: '/stocks' },
  { label: '실행 로그', path: '/logs' },
]

export default function NavTabs() {
  const { pathname } = useLocation()

  const isActive = (path: string) => {
    if (path === '/') return pathname === '/'
    return pathname.startsWith(path) || (path === '/strategies' && pathname.startsWith('/strategy'))
  }

  return (
    <div className="bg-transparent">
      <div className="max-w-[1100px] mx-auto flex gap-1 px-8">
        {tabs.map((tab) => (
          <Link
            key={tab.path}
            to={tab.path}
            className={`px-2 py-2 text-[13px] border-b-2 transition-colors ${
              isActive(tab.path)
                ? 'text-white font-semibold border-indigo-500'
                : 'text-gray-500 border-transparent hover:text-gray-300'
            }`}
          >
            {tab.label}
          </Link>
        ))}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: 커밋**

```bash
git add src/components/layout/NavTabs.tsx
git commit -m "feat: NavTabs 컴포넌트 (투명 배경, 활성 탭 인디고 라인)"
```

---

### Task 3: AccountDropdown 컴포넌트

**Files:**
- Create: `src/components/layout/AccountDropdown.tsx`

- [ ] **Step 1: AccountDropdown.tsx 작성**

```tsx
import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

export default function AccountDropdown() {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const { email, logout } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    if (open) document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        className={`w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center font-semibold text-[13px] border-2 transition-colors ${
          open ? 'border-indigo-500' : 'border-transparent hover:border-indigo-500'
        }`}
      >
        {(email?.[0] ?? 'U').toUpperCase()}
      </button>

      {open && (
        <div className="absolute top-10 right-0 w-[250px] bg-gray-800 border border-gray-700 rounded-xl shadow-2xl overflow-hidden z-70">
          <div className="p-4 border-b border-gray-700 flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gray-700 flex items-center justify-center font-bold text-base border border-gray-600 shrink-0">
              {(email?.[0] ?? 'U').toUpperCase()}
            </div>
            <div className="min-w-0">
              <div className="text-[13px] font-semibold truncate">{email ?? '사용자'}</div>
              <div className="text-[11px] text-gray-500 mt-0.5">Free Plan</div>
            </div>
          </div>
          <div className="py-1">
            <button onClick={() => { navigate('/settings'); setOpen(false) }} className="w-full text-left px-4 py-2.5 text-[13px] text-gray-300 hover:bg-gray-700">설정</button>
          </div>
          <div className="border-t border-gray-700">
            <button onClick={() => { logout(); setOpen(false) }} className="w-full text-left px-4 py-2.5 text-[13px] text-red-400 hover:bg-gray-700">로그아웃</button>
          </div>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: 커밋**

```bash
git add src/components/layout/AccountDropdown.tsx
git commit -m "feat: AccountDropdown 컴포넌트 (카드형 드롭다운)"
```

---

### Task 4: MobileMenu 컴포넌트

**Files:**
- Create: `src/components/layout/MobileMenu.tsx`

- [ ] **Step 1: MobileMenu.tsx 작성**

```tsx
import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

interface Props {
  open: boolean
  onClose: () => void
}

const menuItems = [
  { label: '대시보드', path: '/' },
  { label: '전략', path: '/strategies' },
  { label: '백테스트', path: '/backtest' },
  { label: '관심종목', path: '/stocks' },
  { label: '실행 로그', path: '/logs' },
  { label: '설정', path: '/settings' },
]

export default function MobileMenu({ open, onClose }: Props) {
  const { pathname } = useLocation()
  const { email, logout } = useAuth()

  const isActive = (path: string) => {
    if (path === '/') return pathname === '/'
    return pathname.startsWith(path)
  }

  return (
    <div
      className={`fixed inset-0 bg-[#0a0a1a] z-[100] flex flex-col transition-transform duration-250 will-change-transform ${
        open ? 'translate-x-0' : 'translate-x-full'
      }`}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-800">
        <span className="font-bold text-indigo-500 text-[15px]">StockVision</span>
        <button onClick={onClose} className="text-white text-lg">✕</button>
      </div>

      {/* Account card */}
      <div className="mx-4 mt-4 mb-2 bg-gray-800 border border-gray-700 rounded-xl p-3.5 flex items-center gap-3">
        <div className="w-9 h-9 rounded-full bg-gray-700 flex items-center justify-center font-bold text-sm border border-gray-600 shrink-0">
          {(email?.[0] ?? 'U').toUpperCase()}
        </div>
        <div className="min-w-0">
          <div className="text-[13px] font-semibold truncate">{email ?? '사용자'}</div>
          <div className="text-[11px] text-gray-500 mt-0.5">Free Plan</div>
        </div>
      </div>

      {/* Menu items */}
      <div className="flex-1 flex flex-col justify-center px-6">
        {menuItems.map((item) => (
          <Link
            key={item.path}
            to={item.path}
            onClick={onClose}
            className={`py-3.5 text-xl border-b border-gray-800 ${
              isActive(item.path) ? 'text-white font-semibold' : 'text-gray-400'
            }`}
          >
            {item.label}
          </Link>
        ))}
      </div>

      {/* Logout */}
      <div className="px-6 py-4 border-t border-gray-800">
        <button onClick={() => { logout(); onClose() }} className="text-red-400 text-sm">로그아웃</button>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: 커밋**

```bash
git add src/components/layout/MobileMenu.tsx
git commit -m "feat: MobileMenu 컴포넌트 (풀스크린 오버레이)"
```

---

### Task 5: UnifiedHeader 컴포넌트

**Files:**
- Create: `src/components/layout/UnifiedHeader.tsx`

기존 `Header.tsx`의 검색/알림 기능을 재사용하되, 상태/액션 로직은 훅(`useAccountStatus`, `useNotifStore`)에서 직접 읽는다. props 전달 없음.

- [ ] **Step 1: UnifiedHeader.tsx 작성**

기존 `Header.tsx`에서 검색 로직(StockSearch/debounce)과 알림 표시를 가져오되, 엔진 stop/kill 등의 액션은 포함하지 않는다. 검색 결과 클릭 시 `navigate('/')` 후 인라인 뷰로 이동 (기존 동작 유지를 위해 `onStockSelect` 대신 네비게이트).

핵심 구조:

```tsx
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useNotifStore } from '../../hooks/useLocalBridgeWS'
import AccountDropdown from './AccountDropdown'

interface Props {
  onMenuOpen: () => void
}

export default function UnifiedHeader({ onMenuOpen }: Props) {
  const unreadCount = useNotifStore(s => s.unread)
  const [query, setQuery] = useState('')
  // TODO: 기존 Header.tsx의 검색 debounce 로직 이식

  return (
    <header className="sticky top-0 z-50 bg-gray-900 border-b border-gray-800">
      <div className="max-w-[1100px] mx-auto flex items-center justify-between px-8 py-3 gap-4">
        <Link to="/" className="font-bold text-indigo-500 text-[17px] shrink-0">StockVision</Link>

        {/* 검색바 — 모바일에서 숨김 */}
        <input
          type="text"
          placeholder="종목 검색..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="hidden md:block flex-1 max-w-[400px] bg-gray-800 border border-gray-700 rounded-lg px-3.5 py-1.5 text-[13px] text-gray-200 placeholder:text-gray-500 outline-none focus:border-indigo-500"
        />

        <div className="flex items-center gap-3.5">
          {/* 알림 */}
          <button className="relative text-gray-400 hover:text-gray-200">
            🔔
            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-1.5 bg-red-500 text-white text-[8px] w-[15px] h-[15px] rounded-full flex items-center justify-center">
                {unreadCount}
              </span>
            )}
          </button>

          {/* 계정 — 데스크탑 */}
          <div className="hidden md:block">
            <AccountDropdown />
          </div>

          {/* 햄버거 — 모바일 */}
          <button onClick={onMenuOpen} className="md:hidden text-gray-400 hover:text-gray-200 text-xl">
            ☰
          </button>
        </div>
      </div>
    </header>
  )
}
```

실제 구현 시 기존 `Header.tsx`의 검색 debounce, `cloudStocks.search()`, 검색 결과 드롭다운 렌더링을 이식한다. 핵심은 검색 결과 클릭 시 `navigate('/', { state: { selectedStock } })`로 대시보드 인라인 뷰를 여는 것.

- [ ] **Step 2: 커밋**

```bash
git add src/components/layout/UnifiedHeader.tsx
git commit -m "feat: UnifiedHeader 컴포넌트 (검색 + 알림 + 계정)"
```

---

### Task 6: UnifiedLayout 컴포넌트

**Files:**
- Create: `src/components/layout/UnifiedLayout.tsx`

모든 조각을 합치고, `useLocalBridgeWS()` 호출을 여기서 한다.

- [ ] **Step 1: UnifiedLayout.tsx 작성**

```tsx
import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { useLocalBridgeWS } from '../../hooks/useLocalBridgeWS'
import UnifiedHeader from './UnifiedHeader'
import NavTabs from './NavTabs'
import StatusBar from './StatusBar'
import MobileMenu from './MobileMenu'

export default function UnifiedLayout() {
  // WS 연결 (알림/실행 결과 수신)
  useLocalBridgeWS()

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  return (
    <div className="min-h-screen bg-[#0a0a1a] text-gray-200 flex flex-col">
      <UnifiedHeader onMenuOpen={() => setMobileMenuOpen(true)} />
      <NavTabs />

      <main className="flex-1 w-full max-w-[1100px] mx-auto px-8 py-6 md:px-8 px-4">
        <Outlet />
      </main>

      <StatusBar />
      <MobileMenu open={mobileMenuOpen} onClose={() => setMobileMenuOpen(false)} />
    </div>
  )
}
```

- [ ] **Step 2: 커밋**

```bash
git add src/components/layout/UnifiedLayout.tsx
git commit -m "feat: UnifiedLayout 컴포넌트 (Outlet 기반 통합 레이아웃)"
```

---

### Task 7: App.tsx 라우트 구조 변경

**Files:**
- Modify: `src/App.tsx`

현재 구조를 Outlet 기반 `UnifiedLayout`으로 변경. Admin은 기존 유지.

- [ ] **Step 1: App.tsx 수정**

핵심 변경:

```tsx
// 기존: MainDashboard, Settings가 Layout 밖
// 기존: 나머지가 Layout({children}) 안

// 변경: 모든 보호 라우트가 UnifiedLayout 안
<Route element={<ProtectedRoute><UnifiedLayout /></ProtectedRoute>}>
  <Route path="/" element={<MainDashboard />} />
  <Route path="/settings" element={<Settings />} />
  <Route path="/strategies" element={<StrategyList />} />
  <Route path="/strategies/new" element={<StrategyBuilder />} />
  <Route path="/strategies/:id/edit" element={<StrategyBuilder />} />
  <Route path="/strategy" element={<StrategyBuilder />} />
  <Route path="/backtest" element={<Backtest />} />
  <Route path="/stocks" element={<StockList />} />
  <Route path="/logs" element={<LogViewer />} />
</Route>

// Admin은 기존 유지 (별도 레이아웃)
<Route path="/admin/*" element={...기존 유지...} />
```

`ProtectedRoute`를 Outlet-wrapping layout의 부모로 두어, 인증 체크 → ConsentGate → UnifiedLayout → Outlet 순서가 되도록 한다.

- [ ] **Step 2: 기존 Layout import 제거**

`App.tsx`에서 `import Layout from './components/Layout'` 제거. `UnifiedLayout` import 추가.

- [ ] **Step 3: 빌드 확인**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 4: 커밋**

```bash
git add src/App.tsx
git commit -m "refactor(App): 모든 보호 라우트를 UnifiedLayout으로 통합"
```

---

### Task 8: MainDashboard에서 Header 제거

**Files:**
- Modify: `src/pages/MainDashboard.tsx`

- [ ] **Step 1: Header import 및 사용 제거**

`MainDashboard.tsx`에서:
- `import Header from '../components/main/Header'` 제거
- `<Header ... />` JSX 제거
- 컴포넌트의 최상위 `<div className="min-h-screen bg-gray-950">` → 콘텐츠만 남김 (UnifiedLayout이 이미 감싸므로)

기존:
```tsx
return (
  <div className="min-h-screen bg-gray-950">
    <Header onStockSelect={...} engineRunning={...} brokerConnected={...} />
    <main>
      {/* 대시보드 콘텐츠 */}
    </main>
  </div>
)
```

변경:
```tsx
return (
  <>
    {/* 대시보드 콘텐츠 (UnifiedLayout이 헤더/네비/상태바 제공) */}
    {/* 기존 main 안의 콘텐츠만 유지 */}
  </>
)
```

`onStockSelect`는 UnifiedHeader의 검색에서 `navigate('/', { state: { selectedStock } })`로 대체. MainDashboard에서 `useLocation().state`로 읽어서 인라인 뷰를 연다.

- [ ] **Step 2: 동일하게 Settings 페이지도 자체 헤더 제거**

`Settings.tsx`에서 자체 헤더/네비가 있다면 제거. UnifiedLayout이 제공하므로 콘텐츠만 렌더링.

- [ ] **Step 3: 브라우저 확인**

```bash
cd frontend && npm run dev
```

localhost:5173에서 대시보드, 전략, 설정 페이지를 각각 확인. 헤더/네비/상태바가 동일하게 표시되는지 확인.

- [ ] **Step 4: 커밋**

```bash
git add src/pages/MainDashboard.tsx src/pages/Settings.tsx
git commit -m "refactor: MainDashboard/Settings에서 자체 헤더 제거 (UnifiedLayout 사용)"
```

---

### Task 9: 페이지 셸 정리

**Files:**
- Modify: 각 페이지 파일에서 중복 `min-h-screen`/`max-w-*` 제거

- [ ] **Step 1: 각 페이지에서 중복 wrapper 정리**

UnifiedLayout이 이미 `min-h-screen`, `max-w-[1100px]`, 패딩을 제공하므로, 각 페이지의 자체 wrapper를 제거하거나 조정.

대상 파일 확인:
```bash
cd frontend && grep -rn "min-h-screen\|max-w-" src/pages/ --include="*.tsx" | grep -v node_modules
```

각 파일에서 `min-h-screen bg-gray-950` 같은 wrapper를 제거하고 콘텐츠만 남긴다.

- [ ] **Step 2: 빌드 확인**

```bash
cd frontend && npx tsc --noEmit && npm run build
```

- [ ] **Step 3: 커밋**

```bash
git add src/pages/
git commit -m "refactor: 페이지 셸 정리 (UnifiedLayout과 중복 wrapper 제거)"
```

---

### Task 10: E2E 테스트 업데이트

**Files:**
- Modify: `e2e/strategy-v2.spec.ts`, `e2e/strategy-builder.spec.ts`, 기타

헤더/네비 구조가 바뀌었으므로 E2E 셀렉터 확인.

- [ ] **Step 1: E2E 테스트 실행**

```bash
cd frontend && npx playwright test
```

실패하는 테스트가 있으면 셀렉터 수정. 주로:
- `getByText('전략 빌더')` — 페이지 제목은 유지되므로 문제 없을 가능성 높음
- 네비게이션 관련 셀렉터 — `Layout.tsx`의 네비 구조가 바뀌었으므로 확인
- `mock-auth.ts`의 `setupAllMocks`에서 `localhost:4020` 차단 패턴 확인

- [ ] **Step 2: 필요 시 셀렉터 수정**

실패 내용에 따라 수정. 공통 패턴:
- 네비 링크: `getByRole('link', { name: '전략' })` 등은 NavTabs에서도 동일하게 렌더되므로 대부분 호환
- 페이지 제목: 변경 없음

- [ ] **Step 3: 전체 테스트 PASS 확인**

```bash
cd frontend && npx playwright test
```

Expected: 24 passed

- [ ] **Step 4: 커밋**

```bash
git add e2e/
git commit -m "test(e2e): UnifiedLayout 구조 변경에 맞춰 셀렉터 업데이트"
```

---

### Task 11: 최종 검증

- [ ] **Step 1: 빌드 확인**

```bash
cd frontend && npm run build
```

- [ ] **Step 2: 브라우저 수동 확인**

- 모든 페이지에서 동일한 헤더 + 네비 탭 표시
- 하단 상태 바 모든 페이지에 표시
- 아바타 클릭 → 계정 드롭다운
- 브라우저 768px 이하 → 햄버거 + 풀스크린 메뉴
- 전략 탭 → /strategies (목록)

- [ ] **Step 3: E2E 최종**

```bash
cd frontend && npx playwright test
```

- [ ] **Step 4: 최종 커밋**

```bash
git add -A
git commit -m "feat: 프론트엔드 레이아웃 통일 완료"
```
