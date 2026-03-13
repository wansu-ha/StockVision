# 프론트엔드 안정성 수정 — 기능 명세서

> 상태: 구현 완료 (Phase 2) | 구현: `e372b79`

## 목표

StockList 페이지의 null 필드 런타임 에러와 Trading 페이지의 에러 메시지 미전달 문제를 수정한다.

## 문제

### C-4: StockList.tsx — null 필드 접근 런타임 에러

DB에서 `sector`, `industry`가 null인 종목이 존재한다.
현재 코드에서 `stock.sector.toLowerCase()`를 호출하면 `TypeError: Cannot read properties of null`이 발생한다.

영향 범위:
- 검색어 입력 시 null 종목이 있으면 전체 목록이 사라짐
- 섹터 필터 드롭다운 목록에 `null` 항목이 포함됨

```tsx
// 현재 (에러 발생)
stock.sector.toLowerCase().includes(searchTerm.toLowerCase())
stock.industry.toLowerCase().includes(searchTerm.toLowerCase())

// 섹터 목록에도 null 포함
const sectorSet = new Set(stocks.map(stock => stock.sector))
```

### W-4: Trading.tsx — onError에서 백엔드 오류 메시지 무시

mutation `onError` 콜백이 고정 문자열만 표시하고 백엔드가 반환하는 구체적인 오류 내용을 버린다.

```tsx
// 현재 (백엔드 오류 무시)
onError: () => showToast('주문 실행에 실패했습니다.', 'error'),

// 백엔드가 실제로 반환하는 에러
// { detail: "잔고 부족 (필요: 500,000원, 잔고: 100,000원)" }
```

영향 범위:
- `createAccountMutation`, `calculateScoresMutation`, `runBacktestMutation`, `placeOrderMutation`, `createRuleMutation`
- 사용자가 실패 원인을 알 수 없어 UX 저하

## 요구사항

### FR-1: null 안전 검색 필터

- FR-1.1: `sector`/`industry`가 null이면 검색 매칭에서 빈 문자열로 처리
- FR-1.2: `selectedSector` 필터에서 null sector 종목은 'all'일 때만 포함
- FR-1.3: 섹터 드롭다운 목록에서 null 제거

### FR-2: 백엔드 에러 메시지 전달

- FR-2.1: axios 에러에서 `error.response?.data?.detail` 추출
- FR-2.2: `detail`이 있으면 해당 메시지 표시, 없으면 기존 고정 문자열 폴백
- FR-2.3: 적용 대상: 5개 mutation onError 콜백 전부

## 수용 기준

- [ ] null sector/industry 종목이 있어도 StockList 검색 시 TypeError 미발생
- [ ] 섹터 드롭다운에 null 항목 미포함
- [ ] 잔고 부족 주문 시 백엔드 오류 메시지가 toast에 표시됨
- [ ] `npm run build` 경고 없이 통과
