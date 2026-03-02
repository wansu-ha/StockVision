# 프론트엔드 안정성 수정 — 구현 계획서

## 수정 파일

| 파일 | 변경 내용 |
|------|-----------|
| `frontend/src/pages/StockList.tsx` | null 안전 검색 필터, 섹터 목록 null 제거 |
| `frontend/src/pages/Trading.tsx` | 5개 mutation onError에서 백엔드 메시지 추출 |

## 단계별 구현

### Step 1: StockList.tsx — null 안전 처리

**변경 위치**: `StockList.tsx:35-51`

1. 섹터 목록 추출 시 null 필터링
```tsx
// 수정 전
const sectorSet = new Set(stocks.map(stock => stock.sector))

// 수정 후
const sectorSet = new Set(stocks.map(stock => stock.sector).filter(Boolean))
```

2. 검색 필터에서 optional chaining 적용
```tsx
// 수정 전
stock.sector.toLowerCase().includes(searchTerm.toLowerCase()) ||
stock.industry.toLowerCase().includes(searchTerm.toLowerCase())

// 수정 후
(stock.sector?.toLowerCase() ?? '').includes(searchTerm.toLowerCase()) ||
(stock.industry?.toLowerCase() ?? '').includes(searchTerm.toLowerCase())
```

3. 섹터 매칭 필터에서 null 처리
```tsx
// 수정 전
const matchesSector = selectedSector === 'all' || stock.sector === selectedSector

// 수정 후
const matchesSector = selectedSector === 'all' || (stock.sector ?? '') === selectedSector
```

### Step 2: Trading.tsx — onError 백엔드 메시지 추출

**변경 위치**: `Trading.tsx:104, 115, 129, 157, 167`

에러 메시지 추출 인라인 헬퍼:
```tsx
// axios AxiosError에서 detail 추출
(err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
```

각 mutation onError 패턴:
```tsx
// 수정 전
onError: () => showToast('계좌 생성에 실패했습니다.', 'error'),

// 수정 후
onError: (err) => {
  const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
  showToast(detail ?? '계좌 생성에 실패했습니다.', 'error')
},
```

적용 대상 5건:
- `createAccountMutation` onError
- `calculateScoresMutation` onError
- `runBacktestMutation` onError
- `placeOrderMutation` onError
- `createRuleMutation` onError

## 검증

- `npm run build` — 빌드 에러 없음
- `npm run lint` — lint 경고 없음
- StockList에서 sector null인 종목 존재 시 검색 정상 동작 확인
- Trading에서 잔고 부족 주문 시 백엔드 메시지 toast 표시 확인
