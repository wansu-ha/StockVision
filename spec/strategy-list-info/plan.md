> 작성일: 2026-03-11 | 상태: 구현 완료 | spec: strategy-list-info

# 전략 목록 정보 표시 구현 계획

## 현재 상태 요약

### 파악된 사실
- `cloudStocks.get(symbol)` 이미 존재 (`cloudClient.ts`) — 종목명 단건 조회 가능
- `useStockData` 훅에 `namesQuery` 이미 구현 — `queryKey: ['stockNames', ...]`로 종목명 캐싱됨
- `StrategyList.tsx`는 `useStockData` 미사용, `cloudRules.list`만 단독 호출
- `RuleCard`: `rule.symbol`만 표시, 종목명/방향/실행 상태 없음
- `RuleList`: 동일 — 방향/실행 상태 없음
- `useAccountStatus` 훅이 `engineRunning: boolean` 노출 — `StrategyList.tsx`에서 미사용
- `localStatus.get()` 응답에 규칙별 실행 상태는 없음
  - 엔진 실행 중 + `rule.is_active === true` → "실행 중"으로 프론트에서 판단

### 방향 파싱 로직
- `rule.script`에서 `/^매수:/m`, `/^매도:/m` 정규식 테스트
- script 없으면 `buy_conditions` / `sell_conditions` null 여부로 판단
- 결과: `"매수"` / `"매도"` / `"양방향"` / `"없음"`

### 종목명 매핑 전략
- `StrategyList.tsx`에서 unique symbols에 대해 `cloudStocks.get()` 병렬 호출 → `Map<string, string>`
- `queryKey: ['stockNames', ...]` — MainDashboard와 캐시 공유

## 구현 단계

### Step 1: 방향 파싱 유틸리티 추가
- 변경 파일: `frontend/src/types/strategy.ts`
- 변경 내용: `parseDirection(rule: Rule): '매수' | '매도' | '양방향' | '없음'` 함수 추가
- 검증: 콘솔에서 파싱 결과 확인

### Step 2: StrategyList.tsx — 종목명 + 엔진 상태 주입
- 변경 파일: `frontend/src/pages/StrategyList.tsx`
- 변경 내용:
  - `useAccountStatus` 임포트 → `engineRunning` 추출
  - 종목명 쿼리 추가 — unique symbols에 대해 `cloudStocks.get()` 병렬 호출
  - `RuleCard`에 `symbolName`, `engineRunning` props 전달
- 검증: 렌더 후 종목명 쿼리 1회 발생, 이후 캐시

### Step 3: RuleCard.tsx — 종목명 + 방향 + 실행 상태 표시
- 변경 파일: `frontend/src/components/RuleCard.tsx`
- 변경 내용:
  - Props에 `symbolName?: string`, `engineRunning?: boolean` 추가
  - `parseDirection` 사용하여 방향 배지 추가
  - 실행 상태: `engineRunning && rule.is_active` → "실행 중" / "OFF"
  - 종목명: `{symbolName ? `${symbolName} ${rule.symbol}` : rule.symbol}`
- 검증: 카드에 종목명, 방향 배지, 실행 상태 표시

### Step 4: RuleList.tsx — 동일 정보 추가
- 변경 파일: `frontend/src/components/RuleList.tsx`
- 변경 내용:
  - Props에 `namesMap?: Map<string, string>`, `engineRunning?: boolean` 추가
  - 종목명 + 방향 + 실행 상태를 `·` 구분자로 한 줄 표시
- 검증: 리스트 뷰에서 한 줄 정보 표시

## 변경 파일 목록

| 파일 | 변경 유형 | 내용 |
|------|-----------|------|
| `frontend/src/types/strategy.ts` | 추가 | `parseDirection()` 유틸 함수 |
| `frontend/src/pages/StrategyList.tsx` | 수정 | 종목명 쿼리 + engineRunning 주입 |
| `frontend/src/components/RuleCard.tsx` | 수정 | symbolName/engineRunning props + 배지 |
| `frontend/src/components/RuleList.tsx` | 수정 | namesMap/engineRunning props + 배지 |

## 주의사항

- **종목명 N+1 호출 문제**: `cloudStocks.get(symbol)`은 단건 API. 종목 10개면 10회 호출.
  - `Promise.allSettled`로 병렬 처리 + `staleTime: 5분`으로 캐싱하여 완화
  - React Query가 동일 queryKey 캐시를 공유하므로 MainDashboard와 중복 호출은 없음
  - 종목 수가 많아지면 배치 API(`GET /api/v1/stocks?symbols=...`) 추가 검토 필요
- `cloudStocks.get()` 실패 시 → fallback으로 `rule.symbol` 코드만 표시
- 로컬 서버 미실행 시 → `engineRunning` 기본값 `false` → 모든 규칙 "OFF"
- **RuleList 사용처**: 현재 `StrategyBuilder.tsx`에서만 사용. `StrategyBuilder`에서도 `namesMap`과 `engineRunning`을 전달해야 하지만, StrategyBuilder는 Phase A 직접 대상이 아님. RuleList props를 optional로 두어 backward compatible 유지. StrategyBuilder 연동은 추후
