# UX Polish — 구현 계획

> 작성일: 2026-03-13 | 상태: 초안

---

## 아키텍처

```
App.tsx
  → ProtectedRoute 또는 DEV 가드      ← UX-4: proto 라우트

Layout.tsx
  → bg-gray-950, border-gray-800      ← UX-2: 다크 테마 통일

StrategyBuilder.tsx
  → startEdit() 조건 읽기 전용         ← UX-1: 데이터 손실 방지

useLocalBridgeWS.ts
  → 지수 백오프 + 무한 재시도          ← UX-3: WS 재연결
```

---

## 수정 파일 목록

| 파일 | 변경 내용 |
|------|----------|
| `frontend/src/App.tsx` | proto 라우트에 `import.meta.env.DEV` 가드 |
| `frontend/src/components/Layout.tsx` | 배경/네비게이션 다크 테마 클래스 |
| `frontend/src/pages/StrategyBuilder.tsx` | `startEdit()`에서 조건 섹션 읽기 전용 처리 |
| `frontend/src/hooks/useLocalBridgeWS.ts` | 재연결 로직 — 지수 백오프, 무한 재시도 |

---

## 구현 순서

### Step 1: proto 라우트 보호 (UX-4)

`App.tsx` proto 라우트를 `import.meta.env.DEV` 가드로 감싸기.
추가로 `ProtoA/B/C`의 정적 import(App.tsx:22-24)를 `React.lazy()` + dynamic import로 변경해야 프로덕션 번들에서 코드가 제거됨.

```tsx
// 정적 import 제거, lazy import로 교체
const ProtoA = lazy(() => import('./pages/ProtoA'));
const ProtoB = lazy(() => import('./pages/ProtoB'));
const ProtoC = lazy(() => import('./pages/ProtoC'));

// 라우트에 DEV 가드
{import.meta.env.DEV && (
    <>
        <Route path="/proto-a" element={<Suspense fallback={null}><ProtoA /></Suspense>} />
        <Route path="/proto-b" element={<Suspense fallback={null}><ProtoB /></Suspense>} />
        <Route path="/proto-c" element={<Suspense fallback={null}><ProtoC /></Suspense>} />
    </>
)}
```

**verify**: `npm run build` 후 `/proto-a` 접근 → 404. 번들에 ProtoA/B/C 코드 미포함.

### Step 2: Layout 다크 테마 (UX-2)

`Layout.tsx` 클래스 변경:

```tsx
// Before
<div className="min-h-screen bg-gray-50">
<nav className="bg-white shadow-lg border-b border-gray-100">

// After
<div className="min-h-screen bg-gray-950">
<nav className="bg-gray-900 shadow-lg border-b border-gray-800">
```

네비게이션 링크, 텍스트 색상도 다크 테마에 맞게 조정 (text-gray-300, hover:text-white 등).

**참고**: `MainDashboard`, `OnboardingWizard`, `Settings`는 `<Layout>` 없이 자체 헤더 사용 — Layout 변경 영향 없음. Layout을 사용하는 페이지(stocks, logs, strategies 등)만 테마 변경됨.

**verify**: Layout 사용 페이지 이동 시 테마 일관성 (브라우저 확인)

### Step 3: StrategyBuilder 편집 보호 (UX-1)

`readOnlyScript` 상태 추가 + `startEdit()` 수정:

```tsx
// 상태 선언 추가
const [readOnlyScript, setReadOnlyScript] = useState<string | null>(null);

const startEdit = (rule: RuleCard) => {
    setEditId(rule.id);
    setForm({
        name: rule.name,
        symbol: rule.symbol,
        qty: rule.qty,
        buyConditions: EMPTY_FORM.buyConditions,
        sellConditions: EMPTY_FORM.sellConditions,
    });
    setReadOnlyScript(rule.script);  // 기존 DSL 표시용
    setShowForm(true);
};
```

편집 모드에서 조건 섹션 대신 기존 script를 읽기 전용으로 표시:

```tsx
{editId && readOnlyScript ? (
    <div>
        <p className="text-sm text-gray-400">기존 전략 (읽기 전용)</p>
        <pre className="bg-gray-800 p-3 rounded text-sm">{readOnlyScript}</pre>
    </div>
) : (
    // 기존 조건 입력 폼
)}
```

폼 닫기/취소 시 `setReadOnlyScript(null)` 초기화 필요 (상태 누수 방지).

**verify**: 기존 전략 편집 → 기존 script 표시, 조건 데이터 리셋 없음. 취소 후 새 전략 생성 시 readOnlyScript 미표시.

### Step 4: WS 재연결 지수 백오프 (UX-3)

**Cross-spec 주의**: `auth-security` AS-1도 동일 파일(`useLocalBridgeWS.ts`)의 `onopen`에서 auth 프레임 전송을 추가함. 두 변경이 함께 적용되어야 함 — AS-1이 먼저 구현되면 이 step에서 auth 로직을 유지하면서 재연결만 수정.

`useLocalBridgeWS.ts` 재연결 로직 수정.
현재: `retries.current < 3` + 고정 3초 지연 (line 80-83). `timeout` 변수를 closure로 사용 (line 66,82).

```typescript
// ref 추가 (기존 timeout closure 대체)
const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

const getBackoff = (retry: number) =>
    Math.min(1000 * Math.pow(2, retry), 30000);  // 1s → 2s → 4s → ... → 30s max

ws.onclose = () => {
    setConnected(false);
    const delay = getBackoff(retries.current);
    retries.current += 1;
    reconnectTimer.current = setTimeout(connect, delay);
};

ws.onopen = () => {
    retries.current = 0;
    setConnected(true);
};
```

`retries.current < 3` 제한 제거 (무한 재시도). cleanup에서 `clearTimeout(reconnectTimer.current)`.

**verify**: 브릿지 중단 → 1s, 2s, 4s, ... 간격으로 재시도 → 브릿지 재시작 후 자동 연결

---

## 검증 방법

1. **빌드**: `npm run build` — 에러 없음
2. **브라우저 확인**:
   - proto 라우트 프로덕션 접근 불가
   - 모든 페이지 다크 테마 일관
   - 전략 편집 시 데이터 유지
   - WS 끊김 → 자동 재연결
