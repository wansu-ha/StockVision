# 프론트엔드 품질 — ErrorBoundary · staleTime · 프로필 수정

> 작성일: 2026-03-15 | 상태: 부분 구현 | F1 ✅ F2 ⚠️40% F3 ❌

## 1. 배경

프론트엔드의 안정성, 성능, 기능 완성도를 높이는 3건의 개선 사항을 묶어 처리한다.

## 2. 범위

### 2.1 포함

| # | 항목 | 분류 |
|---|------|------|
| F1 | ErrorBoundary 컴포넌트 추가 | 안정성 |
| F2 | React Query staleTime 설정 | 성능 |
| F3 | 사용자 프로필 수정 기능 | 기능 |

### 2.2 제외

- 다크/라이트 테마 전환 (현재 다크 모드 단일)
- 국제화 (i18n)
- PWA 오프라인 캐싱

## 3. 요구사항

### F1: ErrorBoundary

**문제**: React 컴포넌트에서 런타임 에러 발생 시 전체 앱이 흰 화면으로 크래시된다.
사용자에게 아무 피드백 없이 앱이 중단된다.

**현재 상태**: `main.tsx`에 `<StrictMode>` 적용됨, ErrorBoundary는 없음.

**요구사항**:
- `ErrorBoundary` class 컴포넌트 생성 (React는 class 컴포넌트만 지원)
- `App.tsx`의 라우트를 ErrorBoundary로 래핑
- 에러 발생 시 폴백 UI 표시:
  - "오류가 발생했습니다" 메시지
  - 에러 메시지 (개발 모드에서만 상세 표시)
  - "새로고침" 버튼
- `console.error`로 에러 정보 기록
- 라우트 전환 시 에러 상태 자동 리셋 (location 변경 감지)

### F2: React Query staleTime 설정

**문제**: 대부분의 `useQuery` 호출에 `staleTime`이 설정되지 않아
컴포넌트 마운트마다 불필요한 refetch가 발생한다.

**현재 설정된 곳** (2/23+):
- `BriefingCard.tsx`: `staleTime: 30 * 60 * 1000` (30분)
- `useStockData.ts` stockNames: `staleTime: 5 * 60_000` (5분)

**요구사항**:
- 데이터 특성에 따른 staleTime 가이드라인 수립 및 적용:

| 데이터 유형 | staleTime | 근거 |
|------------|-----------|------|
| 시세/잔고/미체결 | 설정 안 함 (refetchInterval에 의존) | 실시간 데이터, interval이 제어 |
| 규칙 목록 | 2분 | 사용자가 수정하지 않으면 변하지 않음 |
| 종목명/마스터 | 5분 | 장중 불변 |
| AI 브리핑 | 30분 | 비용이 큰 호출 |
| Admin 통계 | 30초 | 모니터링 목적 |

- `QueryClient` 글로벌 기본값은 설정하지 않음 (데이터별 개별 설정)
- 기존 `refetchInterval`이 있는 쿼리는 staleTime을 interval 이하로 설정

### F3: 프로필 수정

**문제**: Settings 페이지에서 이메일만 읽기전용으로 표시된다.
닉네임 변경 기능이 없고, 서버에 PATCH 엔드포인트도 없다.

**현재 상태**:
- `cloudClient.ts:83-87`: `updateProfile()` 스텁 존재 (console.warn만 출력)
- `cloud_server/api/auth.py`: 프로필 수정 엔드포인트 없음
- User 모델: `email`, `nickname`, `role` 필드 존재

**요구사항**:

백엔드:
- `PATCH /api/v1/auth/profile` 엔드포인트 추가
- 수정 가능 필드: `nickname` (2~20자, 공백 trim)
- JWT 인증 필수
- 성공 시 `{ success: true, data: { nickname } }` 반환

프론트엔드:
- Settings 계정 섹션에 닉네임 편집 필드 추가
- 인라인 편집: 표시 → 클릭 → 입력 → 저장
- 저장 성공 시 토스트 알림
- `cloudClient.updateProfile()` 스텁을 실제 API 호출로 교체

## 4. 변경 파일 (예상)

| 파일 | 변경 |
|------|------|
| `frontend/src/components/ErrorBoundary.tsx` | F1: **신규** |
| `frontend/src/App.tsx` | F1: ErrorBoundary 래핑 |
| `frontend/src/hooks/useStockData.ts` | F2: staleTime 조정 |
| `frontend/src/hooks/useMarketContext.ts` | F2: staleTime 추가 |
| `frontend/src/pages/MainDashboard.tsx` | F2: staleTime 추가 |
| `frontend/src/pages/StrategyList.tsx` | F2: staleTime 추가 |
| `frontend/src/pages/StrategyBuilder.tsx` | F2: staleTime 추가 |
| `frontend/src/pages/Admin/*.tsx` | F2: staleTime 추가 |
| `cloud_server/api/auth.py` | F3: PATCH /profile 엔드포인트 |
| `frontend/src/services/cloudClient.ts` | F3: updateProfile 구현 |
| `frontend/src/pages/Settings.tsx` | F3: 닉네임 편집 UI |

## 5. 수용 기준

- [ ] 컴포넌트 런타임 에러 시 폴백 UI가 표시된다 (흰 화면 아님)
- [ ] 에러 후 라우트 전환 시 정상 복구된다
- [ ] 종목명 쿼리가 5분 이내 재마운트 시 네트워크 요청 없이 캐시를 사용한다
- [ ] 규칙 목록이 2분 이내 재마운트 시 캐시를 사용한다
- [ ] 닉네임을 변경하고 저장하면 서버에 반영된다
- [ ] 닉네임 2자 미만 입력 시 유효성 검증 에러가 표시된다

## 6. 참고

- React Query: `frontend/src/App.tsx` (QueryClient)
- Auth API: `cloud_server/api/auth.py`
- Cloud Client: `frontend/src/services/cloudClient.ts`
- Settings: `frontend/src/pages/Settings.tsx`
