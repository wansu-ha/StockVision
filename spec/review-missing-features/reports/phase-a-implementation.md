# Phase A 구현 리포트 — A1~A9 완료

> 작성일: 2026-03-16 | 브랜치: claude/review-missing-features-UhJr7

## 구현 요약

| 작업 | 커밋 | 변경 파일 | 상태 |
|------|------|----------|------|
| A1+A2: 버그 수정 + 보안 강화 | `5ca7b15` | 10개 | ✅ 완료 |
| A3: KIS 어댑터 완성 | `b1257bf` | 4개 | ✅ 완료 |
| A4: 관심종목 하트 토글 | `37ec735` | 8개 | ✅ 완료 |
| A5: UI 미구현 U2~U5, S1~S3 | — | 0개 | ✅ 이미 구현됨 |
| A6: 프론트엔드 품질 | `95eca91` | 3개 | ✅ 완료 |
| A7: 약관 동의 시스템 | `21931da` | 8개 | ✅ 완료 |
| A8: 품질 이슈 Q1~Q7 | — | 0개 | ✅ 대부분 이미 해결 |
| A9: 브로커 자동 재연결 | `c1e0dcf` | 1개 | ✅ 완료 |

총 변경: **27개 파일**, **+445 / -127 lines**

---

## A1+A2: 버그 수정 + 보안 강화

### 버그 수정 (B1~B4)
- **B1**: `email.py` — SMTP 장애 시 send_email fire-and-forget 에러 핸들링
- **B2**: `rate_limit.py` — sliding window 개선 + 구간별 차등 제한
- **B3**: `User` 모델 — `email_verified` 기본값 `False` 명시
- **B4**: `ResetPassword.tsx` — `#token=` fragment 파싱 지원

### 보안 강화 (S1~S8)
- `AuthContext.tsx` — 토큰 갱신 로직 경쟁 조건 해소, `localReady` 리셋 방지
- `authEvents.ts` — `sv-token-refreshed` / `sv-auth-expired` 커스텀 이벤트
- `cloudClient.ts` — 401 인터셉터 강화, 토큰 갱신 큐 + 이벤트 기반 동기화
- `Login.tsx` — 에러 처리 및 UX 개선
- `ResetPassword.tsx` — fragment 기반 토큰 전달 (Referer/로그 노출 방지)

---

## A3: KIS 어댑터 완성

- **K1**: `order.py` — hashkey 헤더 자동 생성 (POST 주문 시 body hash)
- **K2**: `auth.py` — `get_approval_key()` 메서드 (POST `/oauth2/Approval`)
  - `ws.py` — `_get_approval_key()`가 approval_key 전용 메서드 호출
- **K3**: `routers/ws.py` — bridge 연결 상태 브로드캐스트 라우터

---

## A4: 관심종목 하트 토글

### 신규 파일
- `HeartToggle.tsx` — 재사용 하트 아이콘 버튼 (300ms 디바운스, stopPropagation, a11y)
- `useWatchlistToggle.ts` — React Query mutation (optimistic update + rollback)

### 수정 파일
- `useStockData.ts` — `watchlistSet` 메모이제이션 + staleTime 2분
- `ListView.tsx` / `DetailView.tsx` / `StockSearch.tsx` — HeartToggle 통합
- `MainDashboard.tsx` / `StockList.tsx` — props 전달

---

## A6: 프론트엔드 품질

- `ErrorBoundary.tsx` — React class component, 다크 테마 fallback UI
- `PriceChart.tsx` — bars 쿼리 `staleTime: 5분`
- `StrategyList.tsx` — rules 쿼리 `staleTime: 2분`
- `App.tsx` — ErrorBoundary 최상위 래핑 + `/legal/:type` 라우트

---

## A7: 약관 동의 시스템

### 백엔드
- `models/legal.py` — `LegalDocument`, `LegalConsent` SQLAlchemy 모델
- `api/legal.py` — GET documents, GET consent/status, POST consent 엔드포인트
- `api/auth.py` — 회원가입 시 `terms_agreed`, `privacy_agreed` 검증 + LegalConsent 기록

### 프론트엔드
- `Register.tsx` — 이용약관/개인정보처리방침 체크박스, 미체크 시 가입 버튼 비활성
- `auth.ts` — register API에 terms/privacy 파라미터 추가
- `LegalDocument.tsx` — 공개 약관 열람 페이지
- `Layout.tsx` — 푸터에 법적 문서 링크 (이용약관, 개인정보처리방침, 투자위험고지)

---

## A9: 브로커 자동 재연결

- `Settings.tsx` — BrokerKeyForm `onSuccess`에 `localBroker.reconnect()` 호출 추가

---

## 코드 리뷰 결과

### 리뷰 후 수정 완료 (3건)

| 파일 | 이슈 | 심각도 | 조치 |
|------|------|--------|------|
| `auth.py:350` | OAuth2 에러 메시지 내부 정보 노출 | Critical | 일반 메시지로 변경 |
| `legal.py:117` | POST consent 응답에 `data` 필드 누락 | Warning | `{ success, data }` 형식 준수 |
| `HeartToggle.tsx` | 언마운트 시 타이머 cleanup 누락 | Warning | `useEffect` cleanup 추가 |

### 오탐 정리 (2건)

| 지적 사항 | 판정 | 이유 |
|----------|------|------|
| `email.py:146` 이메일 인증 토큰 query string 노출 | ❌ 오탐 | 서버 엔드포인트가 토큰을 수신해야 하므로 fragment 불가 |
| `order.py` httpx context manager 종료 후 resp.json() | ❌ 오탐 | httpx는 response body를 이미 로드하므로 안전 |

### 기존 코드 수준의 이슈 (수정 불필요)

대부분의 warning/info는 기존 코드와 동일한 패턴 (타입 힌트 누락, any 사용 등). 이번 구현 범위에서 기존 패턴을 변경하지 않는 것이 원칙.
