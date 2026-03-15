# 관심종목 하트 토글

> 작성일: 2026-03-15 | 상태: 초안

## 목표

대시보드 종목 행과 종목 검색 결과에 **하트 아이콘**으로 관심종목 추가/제거를 지원한다.
현재 관심종목 해제는 DetailView에서만 가능하고, 추가는 검색 후 별도 동작이 필요하다.

---

## 1. 현황

| 항목 | 현재 상태 |
|------|----------|
| 관심종목 추가 | StockSearch에서 검색 → 종목 선택 → 암묵적 추가 (명시적 UI 없음) |
| 관심종목 해제 | DetailView 진입 후 "관심 해제" 버튼 |
| ListView | "내 종목" / "관심 종목" 탭 전환, 하트 아이콘 없음 |
| API | `POST/DELETE /api/v1/watchlist` 완비 |

### 관련 코드

- `frontend/src/components/main/ListView.tsx` — 종목 리스트 (행 렌더링)
- `frontend/src/components/main/DetailView.tsx` — 종목 상세 (관심 해제 버튼)
- `frontend/src/components/StockSearch.tsx` — 검색 드롭다운
- `frontend/src/services/cloudClient.ts` — `cloudWatchlist.add/remove/list`
- `cloud_server/api/watchlist.py` — CRUD 엔드포인트

---

## 2. 요구사항

### 기능적 요구사항

1. **ListView 종목 행**: 각 행 우측에 하트 아이콘 표시
   - 관심종목이면 채워진 하트 (filled, 빨간색)
   - 아니면 빈 하트 (outline, 회색)
   - 클릭 시 토글 (추가/제거)

2. **StockSearch 검색 결과**: 각 결과 행에 하트 아이콘 표시
   - 동일한 토글 동작
   - 검색 결과에서 바로 관심종목 추가 가능

3. **DetailView**: 기존 "관심 해제" 버튼을 하트 아이콘으로 교체
   - 일관된 UX

4. **낙관적 업데이트**: 클릭 즉시 UI 반영, API 실패 시 롤백

### 비기능적 요구사항

- 하트 클릭이 행 클릭(상세 이동)과 충돌하지 않을 것 (`e.stopPropagation()`)
- 토글 반응 시간 < 100ms (낙관적 업데이트)
- 연속 빠른 클릭 디바운스 (300ms)

---

## 3. UI 설계

### 3.1 ListView 종목 행

```
┌──────────────────────────────────────────────┐
│ ▌ 삼성전자  005930    55,000  +1.2%    ♥  ▸ │
│ ▌ SK하이닉스 000660  180,000  -0.5%    ♡  ▸ │
└──────────────────────────────────────────────┘
                                          ↑  ↑
                                       하트  상세
```

- 하트: 상세 chevron(▸) 왼쪽에 배치
- 크기: 20×20px, 클릭 영역 32×32px (모바일 터치 대응)

### 3.2 StockSearch 검색 결과

```
┌─────────────────────────────────┐
│ 🔍 삼성                         │
├─────────────────────────────────┤
│ 삼성전자  005930  KOSPI    ♥    │
│ 삼성SDI   006400  KOSPI    ♡    │
│ 삼성물산  028260  KOSPI    ♡    │
└─────────────────────────────────┘
```

- 하트: 행 우측 끝
- 행 클릭 → 종목 선택 (기존 동작 유지)
- 하트 클릭 → 관심종목 토글 (이벤트 전파 차단)

### 3.3 색상

| 상태 | 색상 | Tailwind |
|------|------|----------|
| 관심종목 (채워진 하트) | 빨간색 | `text-red-500 fill-current` |
| 비관심 (빈 하트) | 회색 | `text-gray-500` |
| 호버 | 핑크 | `hover:text-red-400` |
| 토글 애니메이션 | scale bounce | `transition-transform duration-150` |

---

## 4. 구현 방향

### 4.1 HeartToggle 컴포넌트

```tsx
// frontend/src/components/HeartToggle.tsx
interface HeartToggleProps {
  symbol: string
  isWatchlisted: boolean
  onToggle: (symbol: string, newState: boolean) => void
  size?: number  // default 20
}
```

- heroicons `HeartIcon` (outline/solid) 사용
- `onClick` 에서 `e.stopPropagation()` 필수

### 4.2 관심종목 상태 관리

현재 `useStockData` 훅이 watchlist를 React Query로 관리 중.

```
watchlistQuery = useQuery('watchlist', cloudWatchlist.list)
```

토글 시:
1. `useMutation`으로 add/remove 호출
2. `onMutate`: 낙관적 업데이트 (queryClient.setQueryData)
3. `onError`: 롤백
4. `onSettled`: invalidate('watchlist')

### 4.3 변경 파일

| 파일 | 변경 |
|------|------|
| `components/HeartToggle.tsx` | 신규 — 하트 토글 컴포넌트 |
| `components/main/ListView.tsx` | 종목 행에 HeartToggle 추가 |
| `components/StockSearch.tsx` | 검색 결과에 HeartToggle 추가 |
| `components/main/DetailView.tsx` | "관심 해제" 버튼 → HeartToggle 교체 |

### 4.4 API 변경

없음. 기존 `POST/DELETE /api/v1/watchlist` 그대로 사용.

---

## 5. 수용 기준

- [ ] ListView: 각 종목 행에 하트 아이콘 표시
- [ ] ListView: 하트 클릭으로 관심종목 추가/제거 토글
- [ ] ListView: 하트 클릭이 행 클릭(상세 이동)과 충돌하지 않음
- [ ] StockSearch: 검색 결과에 하트 아이콘 표시 및 토글
- [ ] DetailView: 기존 "관심 해제" 버튼이 하트 아이콘으로 교체
- [ ] 낙관적 업데이트: 클릭 즉시 UI 반영, 실패 시 롤백
- [ ] 연속 클릭 디바운스 (300ms)
- [ ] 채워진 하트(빨강) / 빈 하트(회색) 시각 구분

---

## 6. 범위

### 포함
- HeartToggle 컴포넌트
- ListView, StockSearch, DetailView에 적용
- 낙관적 업데이트 + 롤백

### 미포함
- 관심종목 순서 변경 (드래그 정렬)
- 관심종목 그룹/폴더
- 관심종목 알림 설정
