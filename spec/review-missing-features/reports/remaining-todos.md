# Phase A 잔여 TODO — 추후 작업 목록

> 작성일: 2026-03-16 | 상태: 추적 중

---

## 🔴 즉시 필요 — 배포/테스트 전 필수

### 1. Alembic 마이그레이션

| 테이블 | 관련 Spec | 비고 |
|--------|----------|------|
| `legal_documents` | legal L3 | CREATE TABLE |
| `legal_consents` | legal L3 | CREATE TABLE |
| `User.deleted_at` | security-phase2 S4 | ALTER TABLE (S4 구현 시) |

```bash
# 로컬 환경에서 실행
alembic revision --autogenerate -m "add legal_documents and legal_consents"
alembic upgrade head
```

### 2. 법적 문서 시드 데이터

`legal_documents` 테이블에 초기 데이터 입력 필요:

| doc_type | version | 내용 소스 |
|----------|---------|----------|
| `terms` | `1.1` | `docs/legal/terms-of-service.md` |
| `privacy` | `1.1` | `docs/legal/privacy-policy.md` |
| `disclaimer` | `1.1` | `docs/legal/investment-disclaimer.md` |

시드 스크립트 또는 Alembic data migration으로 처리.

### 3. 브라우저 테스트

| 테스트 항목 | 확인 사항 |
|------------|----------|
| 회원가입 | 약관 체크박스 2개 → 미체크 시 버튼 비활성, 체크 후 가입 성공 |
| 약관 열람 | `/legal/terms`, `/legal/privacy` 페이지 정상 로드 |
| 하트 토글 | ListView/DetailView/StockSearch에서 토글 → 즉시 UI 반영 → 새로고침 후 유지 |
| 비밀번호 재설정 | `#token=` fragment 정상 파싱 |
| Settings 키 등록 | 등록 후 브로커 자동 연결 시도 확인 |
| ErrorBoundary | 의도적 에러 발생 시 fallback UI 표시 |
| 푸터 링크 | Layout 하단 법적 링크 3개 정상 작동 |

---

## 🟡 운영 전 필수 — Phase A 졸업 잔여

### 4. 보안 미해결

| 항목 | 심각도 | 상세 |
|------|--------|------|
| 이메일/비밀번호 리셋 토큰 평문 저장 | 🔴 P1 | `EmailVerificationToken.token`, `PasswordResetToken.token`에 `hash_token()` 미적용. `RefreshToken`은 적용됨 |
| 비밀번호 강도 검증 | 🟡 | 현재 빈 문자열 허용 |
| WS Origin 헤더 검증 | 🟡 | localhost 외부 접근 가능 |

### 5. UI 미구현 잔여

| 항목 | 상세 |
|------|------|
| 미체결 "취소" 버튼 | `ListView.tsx` onClick 미연결, `PendingOrder.orderId` 타입 누락 |
| 키 미등록 온보딩 CTA | 브로커 미연결 시 설정 안내 배너 |
| 장 상태 공휴일 | `useMarketContext()` 서버 데이터 미사용 |

### 6. Legal 추가 기능

| 항목 | 상세 |
|------|------|
| react-markdown 의존성 | 약관 마크다운 렌더링 (현재 plain text) |
| Settings 약관 섹션 | "약관 및 고지" 메뉴 |
| 기존 사용자 재동의 | 약관 버전 업데이트 시 `requires_consent` → 재동의 모달 |
| 면책 고지 시점 | 전략 활성화 시 disclaimer 동의 (Q4) |

---

## 🟢 기술 부채 — Phase B 이후

| 항목 | 상세 |
|------|------|
| Register.tsx 라이트 테마 | 다크 테마 통일 (이번 구현에서 약관 체크박스는 다크 테마로 추가됨) |
| `auth.ts` 중복 구현 | `cloudAuth`와 별도 `auth.ts` 공존 |
| AdminGuard 리다이렉트 | 어드민 로그인 페이지 대신 메인으로 이동 |
| localClient 에러 처리 불일치 | `setBrokerKeys`만 throw, 나머지는 null 반환 |
| ListView pendingOrders key | 인덱스 → orderId 사용 |
| Phase 1/2 문서 SUPERSEDED 헤더 | 5건 미표기 |
| 6개 spec 상태 헤더 불일치 | "초안/진행 중"이나 실제 "구현 완료" |
