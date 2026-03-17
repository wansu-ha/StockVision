# 프로덕션 보안 하드닝 명세서

> 작성일: 2026-03-17 | 상태: 초안

---

## 1. 목표

`docs/research/security-audit-report.md`에서 발견된 MEDIUM 등급 보안 이슈 M1~M6을 수정하고,
프로덕션 배포에 필요한 추가 보안 조치를 적용한다.

**참고**: `spec/pre-deploy-hardening/` (구현 완료)는 CRITICAL/WARNING 수정.
이 spec은 그 다음 단계인 MEDIUM 등급 + 인프라 보안.

---

## 2. 보안 이슈 목록 (M1~M6)

### M1 — Config PATCH SSRF 체인

**파일**: `local_server/routers/config.py`
**문제**: `PATCH /api/config`로 `cloud.url`을 임의 주소로 변경 가능 → SSRF + 자격증명 유출 체인.
**수정**: config key allowlist 적용. 변경 가능한 키를 명시적으로 제한.

```python
MUTABLE_CONFIG_KEYS = {"broker.app_key", "broker.app_secret", "broker.account_no", ...}
# cloud.url, cloud.token 등은 변경 불가
```

**수용 기준**:
- [ ] allowlist에 없는 키 PATCH 시 403 반환
- [ ] `cloud.url`, `cloud.token` 등 민감 키는 allowlist에서 제외

---

### M2 — 토큰 앞 12자 노출

**파일**: `local_server/routers/auth.py`
**문제**: `GET /api/auth/status`에서 클라우드 토큰 앞 12자를 응답에 포함.
**수정**: `token_preview` → `has_cloud_token: bool`로 변경.

**수용 기준**:
- [ ] 응답에 토큰 문자열이 포함되지 않음
- [ ] `has_cloud_token: true/false`로만 상태 표시

---

### M3 — Rate Limiter 분산 무력화

**파일**: `cloud_server/core/rate_limit.py`
**문제**: in-memory rate limiter가 multi-worker 환경에서 분산되어 보호 무력화.
**수정**: Redis 기반 rate limiter로 전환 (이미 TODO 존재).

```python
# Redis INCR + EXPIRE 패턴
key = f"ratelimit:{endpoint}:{client_ip}"
count = await redis.incr(key)
if count == 1:
    await redis.expire(key, window_seconds)
```

**수용 기준**:
- [ ] Redis 기반 rate limiter 동작
- [ ] multi-worker 환경에서 카운트 공유됨
- [ ] Redis 미접속 시 fallback (in-memory 또는 요청 허용 + 경고 로그)

---

### M4 — CONFIG_ENCRYPTION_KEY 미검증

**파일**: `cloud_server/core/config.py`
**문제**: `CONFIG_ENCRYPTION_KEY` 미설정 시 서버 시작은 되지만, 서비스키 암호화가 조용히 실패.
**수정**: `validate_settings()` 또는 startup 이벤트에서 필수 환경변수 검증.

**수용 기준**:
- [ ] `CONFIG_ENCRYPTION_KEY` 미설정 시 서버 시작 실패 + 명확한 에러 메시지
- [ ] 프로덕션 모드(`ENV=production`)에서만 강제, 개발 모드에서는 경고만

---

### M5 — Dev 모드 토큰 로그 노출

**파일**: `cloud_server/services/email_service.py`
**문제**: dev 모드에서 비밀번호 재설정 토큰이 포함된 이메일 본문을 INFO 로그에 출력.
**수정**: 토큰을 마스킹하거나, 전체 이메일 본문 대신 수신자/제목만 로그.

**수용 기준**:
- [ ] 로그에 토큰 전문이 출력되지 않음
- [ ] dev 모드에서도 토큰은 앞 8자 + `***` 형태로만 표시

---

### M6 — localStorage JWT 키 오류 — ✅ 이미 수정됨

**파일**: `frontend/src/hooks/useOnboarding.ts`
**문제**: `localStorage.getItem('jwt')` — 실제 키는 `sessionStorage.getItem('sv_jwt')`.
**현재**: `localStorage.getItem('jwt')` 호출이 프로젝트에 존재하지 않음. `useOnboarding.ts`는 `stockvision:onboarding_completed` 키 사용. 인증은 `AuthContext.tsx`에서 `sv_jwt`/`sv_rt` 키로 정상 관리.

**수용 기준**:
- [x] `localStorage.getItem('jwt')` 호출 제거 — 이미 없음
- [x] 인증 상태가 정확하게 반영됨 — AuthContext에서 올바른 키 사용

---

## 3. 추가 인프라 보안

### H1 — HTTPS 강제 (프로덕션)

- 클라우드 서버: 리버스 프록시(nginx/Caddy)에서 TLS 종료
- HSTS 헤더 추가: `Strict-Transport-Security: max-age=31536000`
- HTTP → HTTPS 301 리다이렉트

**수용 기준**:
- [ ] 프로덕션 환경에서 HTTP 접근 시 HTTPS로 리다이렉트
- [ ] HSTS 헤더 포함

### H2 — CSP 헤더

- `Content-Security-Policy` 헤더 추가
- `default-src 'self'`, `script-src 'self'`, `connect-src 'self' wss://` 등

**수용 기준**:
- [ ] CSP 헤더가 응답에 포함
- [ ] XSS 공격 벡터 차단

### H3 — Dependency Audit CI

- `npm audit` + `pip-audit` 를 CI 파이프라인에 추가
- HIGH/CRITICAL 취약점 발견 시 빌드 실패

**수용 기준**:
- [ ] CI에서 dependency audit 실행
- [ ] HIGH 이상 취약점 시 빌드 차단
