# 관심종목 하트 토글 — 구현 계획

> 작성일: 2026-03-15 | 상태: 초안 | spec: `spec/watchlist-heart/spec.md`

## 의존관계

```
Step 1 (HeartToggle 컴포넌트) ─── 독립 (기반 컴포넌트)
     │
     ├→ Step 2 (ListView 적용)   ─── Step 1 후
     ├→ Step 3 (StockSearch 적용) ─── Step 1 후
     └→ Step 4 (DetailView 적용)  ─── Step 1 후

→ Step 1 선행 → Step 2, 3, 4 병렬 가능
```

## Step 1: HeartToggle 컴포넌트

**파일**: `frontend/src/components/HeartToggle.tsx` (신규)

### 1.1 컴포넌트

```tsx
import { HeartIcon as HeartOutline } from '@heroicons/react/24/outline'
import { HeartIcon as HeartSolid } from '@heroicons/react/24/solid'
import { useRef, useCallback } from 'react'

interface HeartToggleProps {
  symbol: string
  isWatchlisted: boolean
  onToggle: (symbol: string, newState: boolean) => void
  size?: number
}

export default function HeartToggle({
  symbol, isWatchlisted, onToggle, size = 20,
}: HeartToggleProps) {
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const handleClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation()  // 행 클릭 전파 차단
    e.preventDefault()

    // 300ms 디바운스: 연속 클릭 무시
    if (timerRef.current) return
    timerRef.current = setTimeout(() => { timerRef.current = null }, 300)

    onToggle(symbol, !isWatchlisted)
  }, [symbol, isWatchlisted, onToggle])

  const Icon = isWatchlisted ? HeartSolid : HeartOutline

  return (
    <button
      onClick={handleClick}
      className="p-1.5 rounded-full transition-transform duration-150
                 hover:scale-110 active:scale-95"
      aria-label={isWatchlisted ? '관심종목 해제' : '관심종목 추가'}
    >
      <Icon
        className={`transition-colors ${
          isWatchlisted ? 'text-red-500' : 'text-gray-500 hover:text-red-400'
        }`}
        style={{ width: size, height: size }}
      />
    </button>
  )
}
```

### 1.2 낙관적 업데이트 훅

**파일**: `frontend/src/hooks/useWatchlistToggle.ts` (신규)

```tsx
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { cloudWatchlist } from '../services/cloudClient'

export function useWatchlistToggle() {
  const qc = useQueryClient()

  return useMutation({
    mutationFn: async ({ symbol, add }: { symbol: string; add: boolean }) => {
      if (add) {
        return cloudWatchlist.add(symbol)
      } else {
        return cloudWatchlist.remove(symbol)
      }
    },
    onMutate: async ({ symbol, add }) => {
      // 진행 중인 쿼리 취소
      await qc.cancelQueries({ queryKey: ['watchlist'] })

      // 현재 값 백업
      const prev = qc.getQueryData<WatchlistItem[]>(['watchlist'])

      // 낙관적 업데이트
      qc.setQueryData<WatchlistItem[]>(['watchlist'], old => {
        if (!old) return old
        if (add) {
          return [...old, { id: Date.now(), symbol, added_at: new Date().toISOString() }]
        } else {
          return old.filter(item => item.symbol !== symbol)
        }
      })

      return { prev }
    },
    onError: (_err, _vars, context) => {
      // 실패 시 롤백
      if (context?.prev) {
        qc.setQueryData(['watchlist'], context.prev)
      }
    },
    onSettled: () => {
      // 서버 데이터로 동기화
      qc.invalidateQueries({ queryKey: ['watchlist'] })
    },
  })
}
```

**검증**:
- [ ] 하트 클릭 → 즉시 UI 반영 (낙관적)
- [ ] API 실패 → 원래 상태 롤백
- [ ] 300ms 이내 재클릭 → 무시
- [ ] `e.stopPropagation()` 동작

---

## Step 2: ListView 적용

**파일**: `frontend/src/components/main/ListView.tsx` (수정)

### 2.1 하트 추가 위치

종목 행 우측, 상세 화살표(▸) 왼쪽에 배치.

```tsx
import HeartToggle from '../HeartToggle'
import { useWatchlistToggle } from '../../hooks/useWatchlistToggle'

// 컴포넌트 내부
const { mutate: toggleWatchlist } = useWatchlistToggle()

// watchlist 심볼 Set (빠른 lookup)
const watchlistSet = useMemo(
  () => new Set(watchStocks.map(s => s.symbol)),
  [watchStocks]
)

// 행 렌더링 내부 (가격/변동률 오른쪽, chevron 왼쪽)
<HeartToggle
  symbol={stock.symbol}
  isWatchlisted={watchlistSet.has(stock.symbol)}
  onToggle={(sym, add) => toggleWatchlist({ symbol: sym, add })}
  size={18}
/>
```

현재 ListView의 행 구조:
```
[주가색 바] [종목명 + 코드] [가격 + 변동] [♥] [▸]
```

**검증**:
- [ ] "내 종목" 탭: 각 행에 하트 표시
- [ ] "관심 종목" 탭: 각 행에 채워진 하트 표시
- [ ] 하트 클릭이 행 확장/축소(accordion)를 트리거하지 않음

---

## Step 3: StockSearch 적용

**파일**: `frontend/src/components/StockSearch.tsx` (수정)

### 3.1 검색 결과 행에 하트 추가

```tsx
// 검색 결과 렌더 내부
// 현재: [아바타] [종목명 + 코드] [마켓칩] [→]
// 변경: [아바타] [종목명 + 코드] [마켓칩] [♥] [→]

<HeartToggle
  symbol={item.symbol}
  isWatchlisted={watchlistSet.has(item.symbol)}
  onToggle={(sym, add) => toggleWatchlist({ symbol: sym, add })}
  size={16}
/>
```

검색 결과 드롭다운에서 하트 클릭 시:
- 이벤트 전파 차단 → 종목 선택(내비게이션) 발생하지 않음
- 하트만 토글

**검증**:
- [ ] 검색 결과에 하트 표시
- [ ] 하트 클릭 ≠ 종목 선택 (이벤트 분리)
- [ ] 관심종목 상태가 검색 결과에 즉시 반영

---

## Step 4: DetailView 적용

**파일**: `frontend/src/components/main/DetailView.tsx` (수정)

### 4.1 기존 "관심 해제" 버튼 → HeartToggle 교체

현재 코드 (line 215-218):
```tsx
<button onClick={handleRemoveWatchlist} className="text-sm text-red-400 ...">
  관심 종목 해제
</button>
```

변경:
```tsx
<HeartToggle
  symbol={stock.symbol}
  isWatchlisted={isWatchlisted}
  onToggle={(sym, add) => toggleWatchlist({ symbol: sym, add })}
  size={22}
/>
```

- `handleRemoveWatchlist` 함수 삭제 (useWatchlistToggle이 대체)
- 관심종목이 아닌 종목도 DetailView에서 추가 가능

**검증**:
- [ ] 관심종목 → 채워진 하트, 클릭 시 해제
- [ ] 비관심 종목 → 빈 하트, 클릭 시 추가
- [ ] 토글 후 `onBack()` 호출하지 않음 (기존은 해제 후 뒤로가기)

---

## 변경 파일 요약

| 파일 | Step | 변경 |
|------|------|------|
| `frontend/src/components/HeartToggle.tsx` | 1 | **신규** — 하트 토글 컴포넌트 |
| `frontend/src/hooks/useWatchlistToggle.ts` | 1 | **신규** — 낙관적 업데이트 훅 |
| `frontend/src/components/main/ListView.tsx` | 2 | 행에 HeartToggle 추가 |
| `frontend/src/components/StockSearch.tsx` | 3 | 검색 결과에 HeartToggle 추가 |
| `frontend/src/components/main/DetailView.tsx` | 4 | "관심 해제" 버튼 → HeartToggle 교체 |

**총 5개 파일** (신규 2, 수정 3)

---

## 블로커 & 리스크

| 항목 | 상세 | 대응 |
|------|------|------|
| heroicons 패키지 | `@heroicons/react` 설치 필요할 수 있음 | `npm ls @heroicons/react`로 확인 |
| watchlist 쿼리 키 | `useStockData.ts`에서 `['watchlist']` 키 사용 중 — 동일 키 사용 필수 | `useWatchlistToggle`에서 같은 키 사용 |
| StockSearch 드롭다운 z-index | 하트 클릭 시 드롭다운이 닫힐 수 있음 | `onMouseDown` + `preventDefault`로 포커스 유지 |
