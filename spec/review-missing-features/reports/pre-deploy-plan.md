# 운영 전 작업 계획서

> 작성일: 2026-03-16 | 상태: 구현 완료 (P1~P6 전항목 커밋 완료)

## 현황 요약

A1~A9 구현 + 코드 리뷰 + Alembic 마이그레이션 + 시드 스크립트 완료.

report.md에서 "보안 미해결"로 표기된 항목들 재검증 결과 **모두 이미 구현됨**:
- ✅ S5 토큰 해싱 — `EmailVerificationToken.token_hash`, `PasswordResetToken.token_hash`
- ✅ S7 비밀번호 강도 — `_validate_password_strength()`, 최소 8자 + 대소문자+숫자+특수문자
- ✅ S6 WS Origin 검증 — `ws.py:114` Origin 파싱 + 허용 목록
- ✅ S8 reset-password URL — fragment 기반 (`#token=`) A1+A2에서 구현

---

## Phase A 잔여 — 운영 전 작업 (우선순위 순)

### P1. Alembic 마이그레이션 적용 (즉시)

```bash
# 로컬 개발 DB
alembic upgrade head

# 시드 데이터
python -m cloud_server.scripts.seed_legal_documents
```

파일: `cloud_server/alembic/versions/b7c8d9e0f1a2_add_legal_tables.py`

---

### P2. 미체결 취소 버튼 연결 (1시간)

| 파일 | 변경 |
|------|------|
| `frontend/src/types/` | `PendingOrder`에 `orderId: string` 추가 |
| `MainDashboard.tsx` | `orderId: o.order_id` 매핑 (이미 있을 수 있음, 타입만 누락) |
| `ListView.tsx` | "취소" 버튼 `onClick` → `localBroker.cancelOrder(orderId)` |
| `services/localClient.ts` | `cancelOrder(orderId: string)` 함수 추가 (있으면 확인) |

**수용 기준**: 미체결 목록에서 "취소" 클릭 → 주문 취소 API 호출 → 목록에서 제거

---

### P3. Settings 약관 섹션 (30분)

| 파일 | 변경 |
|------|------|
| `Settings.tsx` | "약관 및 고지" 탭/섹션 추가 |
| | 이용약관, 개인정보처리방침, 투자위험고지 링크 |
| | 현재 동의 상태 표시 (GET `/api/v1/legal/consent/status`) |

---

### P4. 키 미등록 온보딩 CTA (30분)

| 파일 | 변경 |
|------|------|
| `ListView.tsx` | 브로커 미연결 시 계좌 카드 영역에 안내 배너 |
| | "설정에서 증권사 API 키를 등록하세요 →" + Settings 링크 |

**조건**: `localStatus.broker.status === 'disconnected'` && keys 미등록

---

### P5. react-markdown 의존성 + 약관 렌더링 (1시간)

```bash
cd frontend && npm install react-markdown
```

| 파일 | 변경 |
|------|------|
| `LegalDocument.tsx` | `<ReactMarkdown>{content}</ReactMarkdown>` 렌더링 |
| | 현재 plain text → 마크다운 렌더링으로 전환 |

---

### P6. 약관 재동의 모달 (2시간)

약관 버전 업데이트 시 기존 사용자에게 재동의 요청.

| 파일 | 변경 |
|------|------|
| `api/legal.py` | 동의 상태 응답에 `requires_consent: bool` 추가 |
| | 현재 버전 > 마지막 동의 버전 → `true` |
| `App.tsx` 또는 `Layout.tsx` | 로그인 후 consent 상태 체크 |
| | `requires_consent=true` → 재동의 모달 표시 |
| `ConsentModal.tsx` (신규) | 약관 재동의 모달 컴포넌트 |

---

### P7. 기술 부채 (Phase B로 이월 가능)

| 항목 | 예상 시간 | 긴급도 |
|------|----------|--------|
| Register.tsx 다크 테마 통일 | 30분 | 🟢 |
| auth.ts 중복 제거 (cloudAuth 통합) | 1시간 | 🟢 |
| ListView pendingOrders key → orderId | 5분 | 🟢 (P2에서 같이) |
| 장 상태 공휴일 처리 | 1시간 | 🟢 |
| localClient 에러 처리 통일 | 1시간 | 🟢 |

---

## 작업 순서 제안

```
즉시:   P1 (마이그레이션) → 브라우저 테스트
1일차:  P2 (취소 버튼) + P4 (온보딩 CTA) ← 병렬
2일차:  P3 (Settings 약관) + P5 (react-markdown) ← 병렬
3일차:  P6 (재동의 모달)
이후:   P7 (기술 부채) — Phase B 진입 시 함께 처리
```

**P1~P5 완료 시 Phase A 졸업 조건 충족.**
P6은 약관 업데이트가 예정된 시점에 맞춰 구현해도 됨.
