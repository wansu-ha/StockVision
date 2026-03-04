# auth 구현 보고서

> 작성일: 2026-03-04 | 브랜치: main (커밋 대기)

## 생성/수정 파일 목록

### 신규 생성 (백엔드)
| 파일 | 내용 |
|------|------|
| `backend/app/models/auth.py` | User, RefreshToken, EmailVerificationToken, PasswordResetToken, ConfigBlob |
| `backend/app/core/encryption.py` | AES-256-GCM encrypt_blob / decrypt_blob |
| `backend/app/core/password.py` | Argon2id hash_password / verify_password |
| `backend/app/core/jwt_utils.py` | create_jwt / verify_jwt (python-jose) |
| `backend/app/core/email.py` | SMTP 발송 (SMTP_ENABLED=false 시 로그 출력) |
| `backend/app/api/dependencies.py` | current_user FastAPI Depends |
| `backend/app/api/auth.py` | register, verify-email, login, refresh, logout, forgot-password, reset-password |
| `backend/app/api/config.py` | GET/PUT /api/v1/config (서버사이드 암호화) |

### 신규 생성 (로컬 서버)
| 파일 | 내용 |
|------|------|
| `local_server/__init__.py` | 패키지 초기화 |
| `local_server/cloud/__init__.py` | 패키지 초기화 |
| `local_server/cloud/auth_client.py` | token.dat 관리 + refresh_jwt + get_config |

### 신규 생성 (프론트엔드)
| 파일 | 내용 |
|------|------|
| `frontend/src/services/auth.ts` | Auth API 클라이언트 (axios) |
| `frontend/src/context/AuthContext.tsx` | JWT/RT 상태 관리, 자동 갱신 |
| `frontend/src/pages/Login.tsx` | 로그인 페이지 |
| `frontend/src/pages/Register.tsx` | 회원가입 페이지 |
| `frontend/src/pages/ForgotPassword.tsx` | 비밀번호 찾기 |
| `frontend/src/pages/ResetPassword.tsx` | 비밀번호 재설정 |

### 수정 (기존)
| 파일 | 변경 |
|------|------|
| `backend/requirements.txt` | argon2-cffi, cryptography, python-jose, slowapi 추가 |
| `backend/app/core/init_db.py` | auth 모델 import 추가 |
| `backend/app/main.py` | auth_router, config_router 등록 |
| `frontend/src/App.tsx` | AuthProvider 추가, 4개 auth 라우트 추가 |

## 주요 설계 결정

- **UUID**: SQLite 호환을 위해 `String(36)` 사용 (PostgreSQL 운영 시 그대로 호환)
- **Refresh Token**: DB에 SHA-256 해시만 저장, 평문은 클라이언트에만
- **Rotation**: refresh 호출마다 기존 토큰 삭제 + 새 토큰 발급
- **SMTP dev mode**: `SMTP_ENABLED=false`(기본) → 토큰을 로그로 출력
- **이메일 열거 방지**: forgot-password는 이메일 존재 여부 무관 200 반환

## 미설치 패키지
```
pip install argon2-cffi cryptography python-jose[cryptography] slowapi
```
(또는 `pip install -r requirements.txt`)

## 필수 환경변수 (backend/.env)
```env
CONFIG_ENCRYPTION_KEY=<openssl rand -hex 32>
JWT_SECRET=<openssl rand -hex 32>
JWT_EXPIRE_HOURS=24
REFRESH_TOKEN_EXPIRE_DAYS=30
SMTP_ENABLED=false
CLOUD_URL=http://localhost:8000
```
