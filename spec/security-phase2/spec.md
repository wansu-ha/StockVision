# 보안 2차 — Rate Limiter · Redis · Refresh Token · Soft-Delete

> 작성일: 2026-03-15 | 상태: 구현 완료
> 선행: `spec/security-hardening/` (구현 완료 — local_secret, keyring, 비밀번호 검증)

## 1. 배경

보안 감사 (`docs/research/security-audit-report.md`) 비범위로 남겨둔 항목 중
프로덕션 배포 전 반드시 해결해야 하는 4건을 묶어 처리한다.

## 2. 범위

### 2.1 포함

| # | 항목 | 원래 감사 ID |
|---|------|-------------|
| S1 | Rate Limiter X-Forwarded-For 신뢰 정책 | H4 |
| S2 | Rate Limiter → Redis 슬라이딩 윈도우 마이그레이션 | H7 관련 |
| S3 | Refresh Token localStorage → 보안 강화 | C4 |
| S4 | 사용자 삭제 시 soft-delete 보장 | 신규 |

| S5 | 이메일/리셋 토큰 해싱 | C3 |
| S6 | WebSocket Origin 헤더 검증 | H3 |
| S7 | 비밀번호 강도 검증 | H5 |
| S8 | 비밀번호 리셋 토큰 URL 노출 방지 | H6 |

### 2.2 제외

- rules injection 차단 (H2 — DSL 파서 강화와 묶음)
- 프로덕션 하드닝 M1~M6 (배포 직전 체크리스트)

## 3. 요구사항

### S1: Rate Limiter 신뢰 정책

**문제**: `cloud_server/core/rate_limit.py`의 `_get_ip()`가 `X-Forwarded-For` 헤더를 무조건 신뢰한다.
공격자가 헤더를 조작하면 IP 기반 rate limit를 우회할 수 있다.

**현재 코드** (`rate_limit.py:40-50`):
```python
def _get_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
```

**요구사항**:
- Render 프록시 환경에서만 `X-Forwarded-For`를 신뢰한다
- `TRUSTED_PROXY_DEPTH` 환경변수로 프록시 홉 수를 설정한다 (기본값: 1)
- rightmost-N 방식으로 신뢰할 수 있는 클라이언트 IP를 추출한다
- 프록시 없는 로컬 개발 환경에서는 `request.client.host`를 사용한다

### S2: Redis Rate Limiter

**문제**: `RateLimiter`가 인메모리 `defaultdict(list)`를 사용한다.
서버 재시작 시 카운터가 초기화되고, 다중 워커 환경에서 공유되지 않는다.

**현재 코드** (`rate_limit.py:2-4`):
```
프로덕션에서는 Redis로 교체 예정. 현재는 메모리 딕셔너리로 IP별 요청 횟수 추적
```

**요구사항**:
- Redis 사용 가능 시: `ZSET` 기반 슬라이딩 윈도우 (timestamp score)
- Redis 불가 시: 기존 인메모리 폴백 유지
- `cloud_server/core/redis.py`의 기존 `get_redis()` 활용
- 기존 3개 리미터 (`login_limiter`, `register_limiter`, `forgot_pw_limiter`) 인터페이스 유지

### S3: Refresh Token 보안 강화

**문제**: `frontend/src/context/AuthContext.tsx`에서 refresh token을 `localStorage`에 저장한다.
XSS 공격 시 RT가 탈취되어 장기 세션 하이재킹이 가능하다.

**현재 저장 방식**:
- JWT (access): `sessionStorage` (안전)
- RT (refresh): `localStorage` (위험)
- email: `localStorage`

**요구사항**:
- RT를 `sessionStorage`으로 이동 (탭 종료 시 소멸)
- "로그인 유지" 체크박스 → 체크 시에만 `localStorage` 사용
- 기존 `localStorage`에 RT가 있으면 `sessionStorage`으로 마이그레이션 후 삭제
- 로컬 서버 `restore_session` 흐름과의 호환성 유지

### S4: Soft-Delete

**문제**: `cloud_server/models/user.py`에 `is_active` 필드가 존재하나,
실제 삭제 API가 있다면 hard-delete(`DELETE FROM`)를 수행할 수 있다.

**현재 상태**: 삭제 API 엔드포인트 자체가 없음 (admin에서도 미구현).

**요구사항**:
- User 모델에 `deleted_at: DateTime | None` 필드 추가
- 삭제 시 `is_active = False`, `deleted_at = now()` 설정 (hard-delete 금지)
- 로그인 시 `is_active` 체크 (이미 존재)
- 관련 데이터(rules, tokens)는 cascade 삭제하지 않음
- Admin에서 비활성 사용자 조회 가능

### S5: 이메일/리셋 토큰 해싱

**문제**: `EmailVerificationToken.token`, `PasswordResetToken.token`이 DB에 평문 저장된다.
`RefreshToken`은 `hash_token()`으로 해싱하지만, 이 두 모델은 누락되어 있다.
DB 유출 시 임의 계정의 비밀번호 리셋이 가능하다.

**요구사항**:
- `RefreshToken`과 동일한 `hash_token()` 패턴을 적용
- 토큰 생성 시 해시값만 DB에 저장, 원문은 사용자에게만 전달
- 검증 시 입력 토큰을 해싱하여 DB와 비교

### S6: WebSocket Origin 검증

**문제**: `local_server/routers/ws.py`의 WebSocket이 Origin 헤더를 검증하지 않는다.
악성 웹페이지가 `ws://localhost:4020/ws`에 접속하여 포지션 데이터를 수신할 수 있다.

**요구사항**:
- WS 연결 시 Origin 헤더 확인
- `localhost`, `127.0.0.1` 외 Origin은 거부
- Origin 없는 요청은 허용 (로컬 앱)

### S7: 비밀번호 강도 검증

**문제**: 회원가입 시 빈 문자열 `""` 비밀번호가 허용된다.

**요구사항**:
- 최소 8자, 영문+숫자 포함 필수
- Pydantic `field_validator`로 서버 측 검증
- 프론트엔드에서도 동일 규칙 표시

### S8: 비밀번호 리셋 토큰 URL 노출 방지

**문제**: `/reset-password?token=xxx` 형태로 토큰이 URL에 노출된다.
브라우저 히스토리, Referer 헤더, 서버 로그에 토큰이 기록된다.

**요구사항**:
- URL fragment (`#token=xxx`) 또는 POST body로 토큰 전달
- 프론트에서 fragment에서 토큰 추출 후 API에 POST로 전송

## 4. 변경 파일 (예상)

| 파일 | 변경 |
|------|------|
| `cloud_server/core/rate_limit.py` | S1: `_get_ip()` rightmost-N 방식, S2: Redis ZSET 백엔드 |
| `cloud_server/core/redis.py` | S2: `rate_limit_check()` 헬퍼 추가 |
| `cloud_server/models/user.py` | S4: `deleted_at` 필드 추가 |
| `cloud_server/api/auth.py` | S4: 삭제 로직 soft-delete 보장 |
| `frontend/src/context/AuthContext.tsx` | S3: RT 저장 위치 변경, "로그인 유지" 로직 |
| `frontend/src/pages/Login.tsx` | S3: "로그인 유지" 체크박스 UI |
| `cloud_server/models/user.py` | S5: 토큰 모델 해싱 적용 |
| `cloud_server/api/auth.py` | S5: 토큰 생성/검증 로직 수정, S7: 비밀번호 검증, S8: 리셋 URL |
| `local_server/routers/ws.py` | S6: Origin 검증 |
| `frontend/src/pages/Register.tsx` | S7: 비밀번호 강도 표시 |
| `frontend/src/pages/ResetPassword.tsx` | S8: fragment 토큰 추출 |

## 5. 수용 기준

- [ ] `X-Forwarded-For` 헤더 조작으로 rate limit를 우회할 수 없다
- [ ] Redis 가용 시 rate limit 카운터가 Redis에 저장된다
- [ ] Redis 불가 시 인메모리 폴백이 동작한다
- [ ] 기본 로그인 시 RT가 `sessionStorage`에 저장된다
- [ ] "로그인 유지" 체크 시에만 RT가 `localStorage`에 저장된다
- [ ] 사용자 삭제 시 `deleted_at`이 설정되고 DB row는 유지된다
- [ ] 비활성 사용자는 로그인할 수 없다
- [ ] 이메일 인증 토큰이 DB에 해싱되어 저장된다
- [ ] 비밀번호 리셋 토큰이 DB에 해싱되어 저장된다
- [ ] WebSocket 연결 시 localhost 외 Origin이 거부된다
- [ ] 8자 미만 또는 영문/숫자 미포함 비밀번호가 거부된다
- [ ] 비밀번호 리셋 토큰이 URL 쿼리스트링에 노출되지 않는다

## 6. 참고

- 1차 보안 강화: `spec/security-hardening/plan.md` (구현 완료)
- 보안 감사: `docs/research/security-audit-report.md`
- Redis 클라이언트: `cloud_server/core/redis.py`
- 인증 컨텍스트: `frontend/src/context/AuthContext.tsx`
