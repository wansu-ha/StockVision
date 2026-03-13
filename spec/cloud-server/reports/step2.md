# Step 2 보고서: 인증 시스템

> 완료일: 2026-03-05

## 구현 내용

### 생성된 파일

| 파일 | 설명 |
|------|------|
| `cloud_server/models/user.py` | User, RefreshToken, EmailVerificationToken, PasswordResetToken |
| `cloud_server/api/auth.py` | 인증 API 라우터 |
| `cloud_server/api/dependencies.py` | current_user, require_admin 의존성 |

### API 엔드포인트 (/api/v1/auth/)

| 경로 | 메서드 | 설명 |
|------|--------|------|
| `/register` | POST | 회원가입 + 이메일 인증 발송 |
| `/verify-email` | GET | 이메일 인증 완료 |
| `/login` | POST | JWT + Refresh Token 발급 |
| `/refresh` | POST | JWT 갱신 (Token Rotation) |
| `/logout` | POST | Refresh Token 무효화 |
| `/forgot-password` | POST | 재설정 이메일 발송 |
| `/reset-password` | POST | 새 비밀번호 설정 |

### 보안 특성

- **비밀번호**: Argon2id (time=3, memory=64MB, parallelism=4)
- **JWT**: HS256, 1시간 만료 (settings.JWT_EXPIRE_HOURS)
- **Refresh Token**: 30일, SHA-256 해시 저장, Rotation (기존 삭제 → 신규 발급)
- **Rate Limiting**: 로그인 10회/시간/IP, 가입 5회, 비밀번호 재설정 3회
- **이메일 열거 방지**: forgot-password는 항상 200 반환

### 기존 코드와의 차이

| 항목 | 기존 (backend/app/api/auth.py) | 신규 (cloud_server/api/auth.py) |
|------|------|------|
| 경로 | /api/auth/* | /api/v1/auth/* |
| JWT 만료 | 24시간 | 1시간 |
| 응답 형식 | `{jwt, refresh_token}` | `{success, data: {jwt, refresh_token, expires_in}}` |
| is_active 체크 | 없음 | 있음 |
| last_login_at 갱신 | 없음 | 있음 |

## 검증 결과

- [x] User 모델 (is_active, last_login_at 추가)
- [x] RefreshToken Rotation 구현
- [x] Rate Limiter 구현 (in-memory)
- [x] 이메일 인증 흐름 구현
