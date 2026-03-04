# admin-dashboard 구현 보고서

> 작성일: 2026-03-04 | 커밋 대기

## 생성/수정 파일 목록

| 파일 | 내용 |
|------|------|
| `backend/app/models/auth.py` | `User.role` 필드 추가 (`"user" \| "admin"`, default="user") |
| `backend/app/core/jwt_utils.py` | `create_jwt(role=)` 파라미터 추가 |
| `backend/app/api/auth.py` | 로그인/리프레시에서 `user.role` JWT에 포함 |
| `backend/app/api/dependencies.py` | `require_admin` dependency 추가 |
| `backend/app/api/admin.py` | `GET /api/admin/stats`, `GET /api/admin/users`, 템플릿 CRUD |
| `backend/app/main.py` | `admin_router` 등록 |
| `frontend/src/services/admin.ts` | API 클라이언트 |
| `frontend/src/pages/AdminDashboard.tsx` | 관리자 대시보드 UI |
| `frontend/src/App.tsx` | `/admin` 라우트 추가 |

## 주요 기능

### 권한 체계
- `User.role`: "user" (기본) | "admin"
- JWT payload에 `role` 클레임 포함 (로그인/리프레시 시 발급)
- `require_admin`: JWT role != "admin" → 403 반환

### 관리자 API
- `GET /api/admin/stats` — 총 사용자 수, 7일 신규, 온보딩 완료 수, 활성 템플릿 수
- `GET /api/admin/users?page=&limit=` — 사용자 목록 (이메일, 역할, 가입일)
- `GET /api/admin/templates` — 전체 템플릿 (비활성 포함)
- `POST /api/admin/templates` — 새 템플릿 생성
- `PUT /api/admin/templates/{id}` — 수정
- `DELETE /api/admin/templates/{id}` — soft delete (is_active=False)

### 프론트엔드
- 통계 카드 4개 (총 사용자, 신규 7일, 온보딩 완료, 활성 템플릿)
- 사용자 목록 테이블 (최근 20명)
- 템플릿 관리 테이블 (비활성화 버튼)
- 403/401 에러 → "관리자 권한 없음" 메시지 + 홈 버튼

## 비고
- admin role 설정: DB에서 직접 `UPDATE users SET role='admin' WHERE email='...'`
- 에러 로그 API (`GET /api/admin/errors`)는 추후 구현 (로그 파일 접근 방식 결정 필요)
