# 관리자 대시보드 구현 계획서 (admin-dashboard)

> 작성일: 2026-03-04 | 상태: **→ Unit 6 (admin) plan에 통합**

---

## 0. 전제 조건

- 인증 시스템 완료 (`spec/auth/plan.md`)
- 클라우드 서버 배포 완료
- 관리자 권한: `users.role = "admin"` 필드 또는 별도 `admins` 테이블

---

## 1. 관리자 권한 설계

파일: `backend/app/models/auth.py` 확장

```python
class User(Base):
    ...
    role = Column(String, default="user")  # "user" | "admin"
```

```python
# FastAPI dependency
def require_admin(user = Depends(current_user)):
    if user.role != "admin":
        raise HTTPException(403, "관리자 권한 필요")
    return user
```

**검증:**
- [ ] 일반 사용자 → 관리자 API 403
- [ ] admin role 설정 → 접근 허용

---

## 2. 구현 단계

### Step 1 — 서버 상태 + 사용자 통계 API

파일: `backend/app/api/admin.py`

```
GET /api/admin/stats
  → {
      "users": { "total": 42, "active_30d": 28, "new_7d": 5 },
      "heartbeats": { "active_bridges": 15, "kiwoom_connected": 12 },
      "templates": { "total": 8, "active": 6 }
    }

GET /api/admin/users?page=1&limit=20
  → 사용자 목록 (이메일, 가입일, 마지막 접속, role)
  ※ 거래 내역, 전략 내용 표시 안 함 (개인정보 최소화)

GET /api/admin/heartbeat-stats
  → 버전별, OS별 브릿지 통계 (개인정보 없음)

GET /api/admin/errors?limit=50
  → 서버 에러 로그 최근 50건
```

**검증:**
- [ ] admin API 응답 정상
- [ ] 거래 내역/전략 내용 미포함 확인

### Step 2 — 전략 템플릿 관리

**목표**: 관리자가 UI에서 템플릿 추가/수정/삭제

```
GET  /api/admin/templates        → 모든 템플릿 (비활성 포함)
POST /api/admin/templates        → 새 템플릿 생성
PUT  /api/admin/templates/{id}   → 수정
DELETE /api/admin/templates/{id} → 삭제 (soft delete)
```

**검증:**
- [ ] 새 템플릿 생성 → 사용자 `GET /api/templates`에 반영
- [ ] 비활성화 → 사용자 목록에서 제거

### Step 3 — React 관리자 UI

파일: `frontend/src/pages/AdminDashboard.tsx`

```
┌──────────────────────────────────────────────────────────┐
│ 관리자 대시보드                                             │
├─────────────┬────────────────────────────────────────────┤
│ 통계         │ 최근 에러 로그                               │
│ 사용자: 42   │ [ERROR] 2026-03-04 10:30 ...              │
│ 활성 브릿지: 15│                                           │
├─────────────┼────────────────────────────────────────────┤
│ 사용자 목록  │ 전략 템플릿 관리                              │
│ [테이블]     │ [추가] [수정] [비활성화]                     │
└─────────────┴────────────────────────────────────────────┘
```

접근 제한: React 라우트에서 admin role 체크 → 미충족 시 404 또는 로그인 페이지

**검증:**
- [ ] 일반 사용자 → 관리자 페이지 접근 불가
- [ ] 통계 카드 렌더링
- [ ] 템플릿 CRUD UI 동작

---

## 3. 파일 목록

| 파일 | 내용 |
|------|------|
| `backend/app/api/admin.py` | 관리자 API 전체 |
| `backend/app/core/auth.py` | `require_admin` dependency |
| `frontend/src/pages/AdminDashboard.tsx` | 관리자 대시보드 |
| `frontend/src/services/admin.ts` | API 클라이언트 |

---

## 4. 커밋 계획

| 커밋 | 메시지 |
|------|--------|
| 1 | `feat: Step 1 — 관리자 권한 + 통계 API` |
| 2 | `feat: Step 2 — 템플릿 관리 API (관리자)` |
| 3 | `feat: Step 3 — React 관리자 대시보드 UI` |
