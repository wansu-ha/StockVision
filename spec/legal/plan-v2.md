# 법무 UI/API 구현 계획서 (L1/L2/L3)

> 작성일: 2026-03-09 | 상태: 초안 | 범위: Step 5-6 구체화 (회원가입 동의, 약관 열람, 버전 관리)

---

## 0. 배경

법무 문서 4개 (이용약관, 개인정보처리방침, 투자 면책 고지, 증권사 준수 확인서)는 v1.1로 작성 완료.
그러나 **서비스에서 사용자에게 보여주고 동의를 받는 부분**이 미구현:

| ID | 이슈 | 법적 근거 | 현재 |
|----|------|----------|------|
| L1 | 회원가입 시 약관 동의 체크박스 없음 | 개인정보보호법 제15조 (수집 전 별도 동의) | `Register.tsx`에 체크박스 없음 |
| L2 | 약관 열람 경로 없음 | 전자상거래법 (약관 게시 의무) | 서비스 내 열람 불가 |
| L3 | 약관 버전 관리 없음 | 약관규제법 (변경 시 재동의) | DB 모델/API 없음 |

**코드베이스 현황:**
- 회원가입: `cloud_server/api/auth.py` `RegisterBody(email, password, nickname)` — 동의 필드 없음
- 라우트: `/legal/*` 없음, Settings에 법무 섹션 없음, Layout에 Footer 없음
- DB: `cloud_server/models/user.py` User 모델에 동의 필드 없음
- 참고 패턴: `backend/app/models/auth.py` OnboardingState.risk_accepted — 동의 기록 패턴 존재

---

## 1. L1 — 회원가입 약관 동의 체크박스

### 1.1 프론트엔드

**파일: `frontend/src/pages/Register.tsx`**

현재 폼 구조 (email, password, nickname → submit) 아래에 동의 영역 추가:

```
[이메일 입력]
[비밀번호 입력]
[닉네임 입력 (선택)]
─────────────────────────
☐ [이용약관] 에 동의합니다 (필수)          ← 추가
☐ [개인정보처리방침] 에 동의합니다 (필수)    ← 추가
─────────────────────────
[회원가입] (두 체크박스 모두 체크 시에만 활성)
```

변경 사항:
- `useState` 2개 추가: `termsAgreed`, `privacyAgreed`
- 각 체크박스 옆에 약관 전문 보기 링크 → 클릭 시 새 탭 `/legal/terms`, `/legal/privacy`
- submit 조건: `termsAgreed && privacyAgreed`가 true일 때만 버튼 활성
- API 호출 시 `terms_agreed: true`, `privacy_agreed: true` 추가 전송

**파일: `frontend/src/services/auth.ts`**

```typescript
// 현재
register: (email: string, password: string, nickname?: string) =>
  axios.post(`${BASE}/register`, { email, password, nickname }),

// 변경
register: (email: string, password: string, nickname?: string,
           termsAgreed?: boolean, privacyAgreed?: boolean) =>
  axios.post(`${BASE}/register`, {
    email, password, nickname,
    terms_agreed: termsAgreed,
    privacy_agreed: privacyAgreed,
  }),
```

**파일: `frontend/src/types/auth.ts`**

```typescript
// 현재
export interface RegisterRequest {
  email: string
  password: string
  nickname?: string
}

// 변경
export interface RegisterRequest {
  email: string
  password: string
  nickname?: string
  terms_agreed: boolean
  privacy_agreed: boolean
}
```

### 1.2 백엔드

**파일: `cloud_server/api/auth.py`**

RegisterBody 확장:
```python
class RegisterBody(BaseModel):
    email: EmailStr
    password: str
    nickname: str | None = None
    terms_agreed: bool = False      # 추가
    privacy_agreed: bool = False    # 추가
```

register 엔드포인트 검증 추가:
```python
@router.post("/register", status_code=200)
def register(body: RegisterBody, request: Request, db: Session = Depends(get_db)):
    # 약관 동의 검증 (서버단 필수)
    if not body.terms_agreed or not body.privacy_agreed:
        raise HTTPException(400, "이용약관과 개인정보처리방침에 동의해야 합니다.")

    # ... 기존 유저 생성 로직 ...

    # 동의 기록 저장 (L3 LegalConsent 모델 사용)
    _record_consent(db, user.id, "terms", CURRENT_TERMS_VERSION, request)
    _record_consent(db, user.id, "privacy", CURRENT_PRIVACY_VERSION, request)

    db.commit()
    return {"success": True, "message": "인증 메일을 확인하세요."}
```

### 1.3 검증

- [ ] 체크박스 2개 모두 체크하지 않으면 가입 버튼 비활성
- [ ] 서버에서도 `terms_agreed=false` 시 400 반환
- [ ] 가입 성공 시 `legal_consents` 테이블에 2건 (terms, privacy) 기록
- [ ] 약관 링크 클릭 → 새 탭에서 약관 전문 열람 가능

---

## 2. L2 — 약관 열람

### 2.1 법적 문서 열람 페이지

**파일: `frontend/src/pages/LegalDocument.tsx` (신규)**

공개 라우트 (로그인 불필요)로 법적 문서를 렌더링하는 범용 페이지.

```
URL 패턴: /legal/:type
  - /legal/terms     → 이용약관
  - /legal/privacy   → 개인정보처리방침
  - /legal/disclaimer → 투자 면책 고지
```

동작:
- URL의 `:type` 파라미터로 문서 종류 결정
- `GET /api/v1/legal/documents/:type` API로 최신 버전 문서 조회
- 마크다운 → HTML 렌더링 (react-markdown 또는 간단한 렌더러)
- 헤더에 버전, 효력 발생일, 최종 갱신일 표시

**파일: `frontend/src/App.tsx` — 라우트 추가**

```tsx
// 공개 라우트 섹션에 추가
<Route path="/legal/:type" element={<LegalDocument />} />
```

### 2.2 Settings 약관 섹션

**파일: `frontend/src/pages/Settings.tsx`**

기존 섹션 (증권사 API, 모드 전환, 프로필) 아래에 "약관 및 고지" 섹션 추가:

```
┌─ 약관 및 고지 ─────────────────────────┐
│                                        │
│  📄 이용약관 (v1.1)          [열람 →]   │
│  📄 개인정보처리방침 (v1.1)   [열람 →]   │
│  📄 투자 위험 고지 (v1.1)    [열람 →]   │
│                                        │
│  내 동의 현황:                          │
│  ✅ 이용약관 v1.1 동의 (2026-03-09)     │
│  ✅ 개인정보처리방침 v1.1 동의           │
│  ✅ 투자 위험고지 수락 (온보딩)          │
│                                        │
└────────────────────────────────────────┘
```

변경 사항:
- `GET /api/v1/legal/consent/status` API 호출 → 동의 현황 표시
- 각 "열람" 버튼 → `/legal/:type` 라우트로 이동 (새 탭)

### 2.3 Footer 법적 링크

**파일: `frontend/src/components/Layout.tsx`**

현재 Footer 없음. 인증 영역(Layout) 하단에 간결한 Footer 추가:

```
─────────────────────────────────────────────
이용약관 · 개인정보처리방침 · 투자 위험 고지
© 2026 StockVision. All rights reserved.
─────────────────────────────────────────────
```

변경 사항:
- Layout 컴포넌트의 `<main>` 아래에 `<footer>` 추가
- 3개 링크 → `/legal/terms`, `/legal/privacy`, `/legal/disclaimer`
- 작은 글씨, 회색 톤 — 기존 UI 스타일에 맞춤

### 2.4 검증

- [ ] `/legal/terms` 접속 시 이용약관 전문 표시 (로그인 없이)
- [ ] `/legal/privacy` 접속 시 개인정보처리방침 전문 표시
- [ ] `/legal/disclaimer` 접속 시 투자 면책 고지 전문 표시
- [ ] Settings 페이지에서 "약관 및 고지" 섹션 표시 + 동의 현황
- [ ] Footer에 3개 링크 표시, 클릭 시 해당 페이지 이동

---

## 3. L3 — 약관 버전 관리 API

### 3.1 DB 모델

**파일: `cloud_server/models/legal.py` (신규)**

```python
class LegalDocument(Base):
    """약관/고지 문서 원문 + 버전"""
    __tablename__ = "legal_documents"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    doc_type       = Column(String(30), nullable=False)   # "terms" | "privacy" | "disclaimer"
    version        = Column(String(10), nullable=False)    # "1.0", "1.1", ...
    title          = Column(String(200), nullable=False)   # "StockVision 이용약관"
    content_md     = Column(Text, nullable=False)          # 마크다운 원문
    effective_date = Column(Date, nullable=True)           # 효력 발생일 (null = 미발효)
    created_at     = Column(DateTime, default=_utcnow)

    __table_args__ = (
        UniqueConstraint("doc_type", "version", name="uq_doc_type_version"),
    )


class LegalConsent(Base):
    """사용자별 약관 동의 기록"""
    __tablename__ = "legal_consents"

    id           = Column(Integer, primary_key=True, autoincrement=True)
    user_id      = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    doc_type     = Column(String(30), nullable=False)   # "terms" | "privacy" | "disclaimer"
    doc_version  = Column(String(10), nullable=False)   # 동의한 버전
    agreed_at    = Column(DateTime, default=_utcnow, nullable=False)
    ip_address   = Column(String(45), nullable=True)    # 감사 추적용

    user = relationship("User", backref="legal_consents")

    __table_args__ = (
        Index("ix_consent_user_type", "user_id", "doc_type"),
    )
```

**Alembic 마이그레이션**: `legal_documents`, `legal_consents` 테이블 생성

### 3.2 설정값

**파일: `cloud_server/core/config.py`**

```python
# 현재 유효한 약관 버전 (코드에 하드코딩 — 변경 시 배포 필요)
CURRENT_TERMS_VERSION = "1.1"
CURRENT_PRIVACY_VERSION = "1.1"
CURRENT_DISCLAIMER_VERSION = "1.1"
```

> 왜 DB가 아닌 코드에? — 약관 변경은 드물고 (연 1-2회), 변경 시 문서 내용 자체가 바뀌므로 배포가 동반됨.
> DB의 LegalDocument는 약관 원문 저장/조회용이지, "현재 버전이 뭔지" 결정하는 용도가 아님.

### 3.3 API 엔드포인트

**파일: `cloud_server/api/legal.py` (신규)**

```
GET  /api/v1/legal/documents/{doc_type}
     → 해당 타입의 최신 버전 문서 반환 (content_md, version, effective_date)
     → 인증 불필요 (공개)

GET  /api/v1/legal/documents/{doc_type}/{version}
     → 특정 버전 문서 반환
     → 인증 불필요 (공개)

GET  /api/v1/legal/consent/status
     → 현재 사용자의 동의 현황 반환
     → 인증 필요
     → 응답 예시:
     {
       "success": true,
       "data": {
         "terms": { "agreed_version": "1.1", "agreed_at": "...", "latest_version": "1.1", "up_to_date": true },
         "privacy": { "agreed_version": "1.0", "agreed_at": "...", "latest_version": "1.1", "up_to_date": false },
         "disclaimer": { "agreed_version": null, "agreed_at": null, "latest_version": "1.1", "up_to_date": false }
       }
     }

POST /api/v1/legal/consent
     → 동의 기록 저장
     → 인증 필요
     → body: { "doc_type": "terms", "doc_version": "1.1" }
     → 응답: { "success": true }
```

### 3.4 로그인 시 약관 확인 플로우

**파일: `cloud_server/api/auth.py` — login 엔드포인트 수정**

현재 login 응답:
```python
return {
    "success": True,
    "data": {
        "access_token": jwt_token,
        "refresh_token": raw_rt,
        "expires_in": 3600,
    },
}
```

변경 — `requires_consent` 필드 추가:
```python
# 로그인 성공 후, 최신 약관 동의 여부 체크
outdated = _check_outdated_consents(db, user.id)

return {
    "success": True,
    "data": {
        "access_token": jwt_token,
        "refresh_token": raw_rt,
        "expires_in": 3600,
        "requires_consent": outdated,  # [] 이면 최신, ["terms", "privacy"] 등이면 재동의 필요
    },
}
```

`_check_outdated_consents` 로직:
1. 사용자의 각 doc_type별 최신 동의 버전 조회
2. `CURRENT_*_VERSION`과 비교
3. 미동의 또는 구버전이면 해당 doc_type 반환

### 3.5 프론트엔드 재동의 플로우

**파일: `frontend/src/services/auth.ts`**

login 응답의 `requires_consent` 확인:
```typescript
// 로그인 성공 후
if (data.requires_consent?.length > 0) {
  // zustand store에 재동의 필요 상태 저장
  useAuthStore.getState().setRequiresConsent(data.requires_consent)
}
```

**파일: `frontend/src/components/ConsentModal.tsx` (신규)**

로그인 후 `requires_consent`가 비어있지 않으면 모달 표시:

```
┌─ 약관 변경 안내 ──────────────────────────┐
│                                           │
│  서비스 이용약관이 변경되었습니다.            │
│  계속 이용하시려면 변경된 약관에              │
│  동의해 주세요.                             │
│                                           │
│  📄 이용약관 (v1.0 → v1.1)    [변경 확인]   │
│  📄 개인정보처리방침 (v1.0 → v1.1) [변경 확인]│
│                                           │
│  ☐ 변경된 약관에 동의합니다                  │
│                                           │
│  [동의하고 계속]  [로그아웃]                  │
└───────────────────────────────────────────┘
```

동작:
- "변경 확인" → `/legal/:type` 새 탭으로 열기
- "동의하고 계속" → `POST /api/v1/legal/consent` 호출 (각 doc_type별)
- "로그아웃" → 세션 종료
- 모달은 dismissable하지 않음 (배경 클릭으로 닫기 불가)

**파일: `frontend/src/App.tsx` 또는 `ProtectedRoute` 컴포넌트**

인증 영역 진입 시 `requires_consent` 체크 → 비어있지 않으면 ConsentModal 표시.

### 3.6 검증

- [ ] `legal_documents` 테이블에 약관 원문 3건 (terms, privacy, disclaimer) 시딩
- [ ] `GET /api/v1/legal/documents/terms` → 최신 약관 반환
- [ ] 회원가입 시 `legal_consents`에 동의 2건 기록 (terms, privacy)
- [ ] `GET /api/v1/legal/consent/status` → 사용자 동의 현황 정확히 반환
- [ ] 약관 버전 올린 후 로그인 → `requires_consent: ["terms"]` 반환
- [ ] 재동의 모달 표시 → 동의 → `legal_consents`에 새 버전 기록
- [ ] 재동의 없이 서비스 이용 시도 → 모달 우회 불가

---

## 4. 파일 변경 목록

### 신규 파일

| 파일 | 용도 |
|------|------|
| `cloud_server/models/legal.py` | LegalDocument, LegalConsent 모델 |
| `cloud_server/api/legal.py` | 약관 조회/동의 API 라우터 |
| `frontend/src/pages/LegalDocument.tsx` | 약관 전문 열람 페이지 |
| `frontend/src/components/ConsentModal.tsx` | 약관 재동의 모달 |

### 수정 파일

| 파일 | 변경 내용 |
|------|----------|
| `cloud_server/api/auth.py` | RegisterBody에 동의 필드 추가, login에 requires_consent 추가 |
| `cloud_server/core/config.py` | CURRENT_*_VERSION 상수 추가 |
| `cloud_server/main.py` | legal 라우터 등록 |
| `frontend/src/pages/Register.tsx` | 약관 동의 체크박스 2개 + 링크 추가 |
| `frontend/src/pages/Settings.tsx` | "약관 및 고지" 섹션 추가 |
| `frontend/src/components/Layout.tsx` | Footer 추가 (법적 링크 3개) |
| `frontend/src/App.tsx` | `/legal/:type` 공개 라우트 추가 |
| `frontend/src/services/auth.ts` | register 인터페이스 확장, login 응답 처리 |
| `frontend/src/types/auth.ts` | RegisterRequest 타입 확장 |

### 마이그레이션

| 파일 | 내용 |
|------|------|
| `cloud_server/alembic/versions/xxx_add_legal_tables.py` | legal_documents, legal_consents 테이블 생성 |

### 시드 데이터

| 내용 | 소스 |
|------|------|
| terms v1.1 | `docs/legal/terms-of-service.md` 원문 |
| privacy v1.1 | `docs/legal/privacy-policy.md` 원문 |
| disclaimer v1.1 | `docs/legal/disclaimer.md` 원문 |

> 시드는 Alembic data migration 또는 별도 스크립트로. 약관 원문은 마크다운 그대로 DB에 저장.

---

## 5. 구현 순서

| 단계 | 작업 | 의존 |
|------|------|------|
| A | DB 모델 (`legal.py`) + Alembic 마이그레이션 | 없음 |
| B | API 엔드포인트 (`legal.py` 라우터) + 시드 데이터 | A |
| C | Register.tsx 체크박스 + auth.py 검증 | B |
| D | LegalDocument.tsx 열람 페이지 + 라우트 | B |
| E | Settings.tsx 법무 섹션 + Layout Footer | B, D |
| F | login 응답 수정 + ConsentModal 재동의 | B |

```
A → B → C (L1 완료)
       → D → E (L2 완료)
       → F (L3 완료)
```

C, D, F는 B 이후 병렬 가능.

---

## 6. 커밋 계획

| # | 메시지 | 파일 | 비고 |
|---|--------|------|------|
| 1 | `feat(legal): LegalDocument/LegalConsent 모델 + 마이그레이션` | cloud_server/models/legal.py, alembic/ | 단계 A |
| 2 | `feat(legal): 약관 조회/동의 API + 시드 데이터` | cloud_server/api/legal.py, config.py, main.py | 단계 B |
| 3 | `feat(legal): 회원가입 약관 동의 체크박스 (L1)` | Register.tsx, auth.ts, auth.py | 단계 C |
| 4 | `feat(legal): 약관 열람 페이지 + Settings 섹션 + Footer (L2)` | LegalDocument.tsx, Settings.tsx, Layout.tsx, App.tsx | 단계 D+E |
| 5 | `feat(legal): 로그인 시 약관 재동의 플로우 (L3)` | auth.py login, ConsentModal.tsx | 단계 F |

---

## 7. 미결 사항

| # | 항목 | 결정 필요 | 제안 |
|---|------|----------|------|
| Q1 | 마크다운 렌더링 라이브러리 | react-markdown vs 직접 렌더링 | react-markdown (이미 package.json 의존성 확인 필요) |
| Q2 | 약관 원문 저장 방식 | DB에 마크다운 저장 vs 파일 참조 | DB 저장 (버전별 원문 보존, API 서빙 간편) |
| Q3 | 기존 사용자 처리 | 이미 가입한 사용자는 어떻게? | 다음 로그인 시 `requires_consent` → 재동의 모달 |
| Q4 | 투자 면책 고지 동의 시점 | 가입 시 vs 전략 활성화 시 | 가입 시에는 terms/privacy만, disclaimer는 전략 활성화 시 (기존 RiskDisclosure 패턴 유지) |
| Q5 | react-markdown 의존성 | 추가 설치 필요 여부 | `npm install react-markdown` 필요 시 추가 |

---

**마지막 갱신**: 2026-03-09
