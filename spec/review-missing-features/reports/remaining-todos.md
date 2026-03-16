# Phase A 잔여 TODO — 추후 작업 목록

> 작성일: 2026-03-16 | 갱신: 2026-03-16 | 상태: 추적 중

---

## 🔴 즉시 필요 — 배포/테스트 전 필수

### 1. Alembic 마이그레이션 — ⏳ 사용자 로컬 실행 대기

| 테이블 | 관련 Spec | 비고 |
|--------|----------|------|
| `legal_documents` | legal L3 | CREATE TABLE |
| `legal_consents` | legal L3 | CREATE TABLE |
| `User.deleted_at` | security-phase2 S4 | ALTER TABLE (S4 구현 시) |

마이그레이션 스크립트 및 시드는 이전 커밋(`a590ef8`)에서 생성 완료.

```bash
# 로컬 환경에서 실행
alembic upgrade head
python -m cloud_server.scripts.seed_legal
```

### 2. 브라우저 테스트 — ⏳ 미실행

| 테스트 항목 | 확인 사항 |
|------------|----------|
| 회원가입 | 약관 체크박스 2개 → 미체크 시 버튼 비활성, 체크 후 가입 성공 |
| 약관 열람 | `/legal/terms`, `/legal/privacy` 페이지 정상 로드 (react-markdown 렌더링) |
| 하트 토글 | ListView/DetailView/StockSearch에서 토글 → 즉시 UI 반영 → 새로고침 후 유지 |
| 비밀번호 재설정 | `#token=` fragment 정상 파싱 |
| Settings 키 등록 | 등록 후 브로커 자동 연결 시도 확인 |
| ErrorBoundary | 의도적 에러 발생 시 fallback UI 표시 |
| 푸터 링크 | Layout 하단 법적 링크 3개 정상 작동 |
| **미체결 취소** | 미체결 탭 → 취소 버튼 클릭 → 주문 취소 확인 |
| **Settings 약관** | Settings → "약관 및 고지" 섹션 링크 정상 작동 |
| **키 등록 CTA** | 브로커 미연결 시 "키 등록하기 →" 버튼 → Settings 이동 |

---

## 🟡 운영 전 필수 — Phase A 졸업 잔여

### 3. 보안 — ✅ 전부 해결 확인 (2026-03-16)

재검증 결과 모두 이미 구현됨:
- ✅ S5 토큰 해싱 — `token_hash` 컬럼 (SHA-256)
- ✅ S7 비밀번호 강도 — `_validate_password_strength()`, 최소 8자
- ✅ S6 WS Origin 검증 — `ws.py:114`
- ✅ S8 reset-password fragment — `#token=`

### 4. UI — ✅ P2~P4 구현 완료 (2026-03-16)

| 항목 | 상태 | 커밋 |
|------|------|------|
| 미체결 "취소" 버튼 | ✅ 엔드포인트 + 프론트 연결 완료 | `a515a4e` |
| 키 미등록 온보딩 CTA | ✅ "키 등록하기 →" 버튼 (Settings 이동) | `a515a4e` |
| 장 상태 공휴일 | ⏳ 미구현 — `useMarketContext()` 서버 데이터 미사용 |

### 5. Legal — ✅ P3+P5 구현 완료 / 2건 잔여 (2026-03-16)

| 항목 | 상태 | 커밋 |
|------|------|------|
| react-markdown 의존성 | ✅ 설치 + LegalDocument 렌더링 적용 | `a515a4e` |
| Settings 약관 섹션 | ✅ "약관 및 고지" 3개 링크 추가 | `a515a4e` |
| 기존 사용자 재동의 | ⏳ 약관 버전 업데이트 시 `requires_consent` → 재동의 모달 |
| 면책 고지 시점 | ⏳ 전략 활성화 시 disclaimer 동의 (Q4) |

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
