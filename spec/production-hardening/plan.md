# 프로덕션 보안 하드닝 구현 계획

> 작성일: 2026-03-17 | 상태: 구현 완료

---

## 선행 조건

- `spec/pre-deploy-hardening/` (CRITICAL/WARNING) 구현 완료
- `docs/research/security-audit-report.md` 감사 결과 확인
- Redis 인프라 가용 (M3용)

---

## Step 1: M1 — Config PATCH SSRF 차단

**파일**: `local_server/routers/config.py`

**변경 내용**:
1. `MUTABLE_CONFIG_KEYS` 상수 정의 (허용 키만 열거)
2. `PATCH /api/config` 핸들러에서 키 검증 로직 추가
3. allowlist 외 키 → 403 Forbidden 반환

```python
MUTABLE_CONFIG_KEYS = {
    "broker.app_key", "broker.app_secret", "broker.account_no",
    "broker.account_type", "broker.is_mock",
    "engine.enabled", "engine.kill_switch",
}
# cloud.url, cloud.token, cloud.user_id 등은 제외
```

**검증**: allowlist 외 키(`cloud.url`) PATCH 시 403 확인

---

## Step 2: M2 — 토큰 미리보기 제거

**파일**: `local_server/routers/auth.py`

**변경 내용**:
1. `/api/auth/status` 응답에서 `token_preview` 필드 제거
2. `has_cloud_token: bool` 필드로 대체

**검증**: 응답 JSON에 토큰 문자열 미포함 확인

---

## Step 3: M3 — Redis Rate Limiter

**파일**: `cloud_server/core/rate_limit.py`

**변경 내용**:
1. Redis INCR + EXPIRE 패턴으로 rate limiter 재구현
2. fallback: Redis 미접속 시 in-memory 유지 + 경고 로그

```python
async def check_rate_limit(key: str, limit: int, window: int) -> bool:
    try:
        count = await redis.incr(f"ratelimit:{key}")
        if count == 1:
            await redis.expire(f"ratelimit:{key}", window)
        return count <= limit
    except RedisError:
        logger.warning("Redis unavailable, falling back to in-memory rate limiter")
        return self._in_memory_check(key, limit, window)
```

**의존**: Redis 인프라 가용
**검증**: multi-worker 환경에서 rate limit 카운트 공유 확인

---

## Step 4: M4 — 환경변수 필수 검증

**파일**: `cloud_server/core/config.py`

**변경 내용**:
1. `Settings` 클래스의 `@validator` 또는 startup 이벤트에서 `CONFIG_ENCRYPTION_KEY` 검증
2. 프로덕션(`ENV=production`): 미설정 시 시작 실패 + 에러 메시지
3. 개발(`ENV=development`): 미설정 시 경고 로그만

```python
@app.on_event("startup")
async def validate_required_env():
    if settings.ENV == "production" and not settings.CONFIG_ENCRYPTION_KEY:
        raise RuntimeError("CONFIG_ENCRYPTION_KEY is required in production")
    elif not settings.CONFIG_ENCRYPTION_KEY:
        logger.warning("CONFIG_ENCRYPTION_KEY not set — encryption disabled in dev mode")
```

**검증**: `ENV=production` + 키 미설정 시 서버 시작 실패 확인

---

## Step 5: M5 — 토큰 로그 마스킹

**파일**: `cloud_server/services/email_service.py`

**변경 내용**:
1. 이메일 본문 로그 출력 시 토큰을 마스킹
2. 앞 8자 + `***` 형태로만 출력
3. dev 모드 로그에서도 전체 토큰 노출 방지

```python
def _mask_token(token: str) -> str:
    return token[:8] + "***" if len(token) > 8 else "***"
```

**검증**: dev 모드 로그에 토큰 전문 미출력 확인

---

## Step 6: H1 — HTTPS 강제 (인프라)

**파일**: `docker-compose.yml` 또는 nginx/Caddy 설정

**변경 내용**:
1. 리버스 프록시 설정에 TLS 종료 추가
2. HSTS 헤더: `Strict-Transport-Security: max-age=31536000; includeSubDomains`
3. HTTP 80 → HTTPS 443 리다이렉트 (301)

**참고**: 실제 TLS 인증서는 배포 환경에 따라 Let's Encrypt 또는 managed cert 사용.

**검증**: HTTP 접근 시 301 리다이렉트 + HSTS 헤더 확인

---

## Step 7: H2 — CSP 헤더

**파일**: 클라우드 서버 미들웨어 또는 리버스 프록시 설정

**변경 내용**:
1. `Content-Security-Policy` 응답 헤더 추가
2. 정책:
   - `default-src 'self'`
   - `script-src 'self'`
   - `style-src 'self' 'unsafe-inline'` (Tailwind 인라인 스타일 허용)
   - `connect-src 'self' wss: https:`
   - `img-src 'self' data:`
3. FastAPI 미들웨어로 구현 또는 nginx `add_header`

**검증**: 브라우저 콘솔에서 CSP 위반 없는지 확인

---

## Step 8: H3 — Dependency Audit CI

**파일**: `.github/workflows/audit.yml` (신규)

**변경 내용**:
1. GitHub Actions 워크플로우 추가
2. `npm audit --audit-level=high` + `pip-audit --severity high`
3. HIGH 이상 취약점 시 빌드 실패

```yaml
- name: Frontend audit
  run: cd frontend && npm audit --audit-level=high
- name: Backend audit
  run: pip-audit --requirement requirements.txt --severity high
```

**검증**: 의도적 취약 패키지 추가 시 CI 실패 확인

---

## 의존성 그래프

```
Step 1 (M1) ──┐
Step 2 (M2) ──┤
Step 4 (M4) ──┼→ 모두 독립, 병렬 가능
Step 5 (M5) ──┤
              │
Step 3 (M3) ──┘ ← Redis 가용 필요

Step 6 (H1) ──┐
Step 7 (H2) ──┼→ 인프라 설정, 병렬 가능
Step 8 (H3) ──┘
```

**코드 수정** (Step 1~5)과 **인프라 설정** (Step 6~8)은 독립 트랙으로 병렬 진행.

---

## 수정 파일 종합

| # | 파일 | Step | 작업 |
|---|------|------|------|
| 1 | `local_server/routers/config.py` | 1 | MUTABLE_CONFIG_KEYS allowlist |
| 2 | `local_server/routers/auth.py` | 2 | token_preview → has_cloud_token |
| 3 | `cloud_server/core/rate_limit.py` | 3 | Redis rate limiter |
| 4 | `cloud_server/core/config.py` | 4 | 환경변수 필수 검증 |
| 5 | `cloud_server/services/email_service.py` | 5 | 토큰 마스킹 |
| 6 | nginx/Caddy 설정 | 6 | TLS + HSTS |
| 7 | 미들웨어 또는 프록시 설정 | 7 | CSP 헤더 |
| 8 | `.github/workflows/audit.yml` | 8 | CI 파이프라인 (신규) |

**예상 공수**: Step 1~5: 1~2일, Step 6~8: 1일
