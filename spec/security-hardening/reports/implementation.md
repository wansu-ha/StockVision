# security-hardening 구현 보고서

> 작성일: 2026-03-08

## 요약

보안 감사 보고서(`docs/research/security-audit-report.md`) 즉시 수정 대상 3건 구현 완료.

## Step 1: Shared Secret 인증 (C1+C2)

### 신규 파일
- `local_server/core/__init__.py` — 패키지 초기화
- `local_server/core/local_auth.py` — `generate_secret()`, `require_local_secret()` Depends

### 수정 파일
| 파일 | 변경 내용 |
|------|----------|
| `local_server/main.py` | lifespan에서 `generate_secret()` → `app.state.local_secret` 저장 |
| `local_server/routers/auth.py` | `/token` 응답에 `local_secret` 포함, `/logout`에 `require_local_secret` 적용, `token_preview` 제거 (M2) |
| `local_server/routers/config.py` | 3개 엔드포인트 모두 `require_local_secret` 적용 |
| `local_server/routers/trading.py` | 5개 엔드포인트 모두 `require_local_secret` 적용 |
| `local_server/routers/rules.py` | 2개 엔드포인트 모두 `require_local_secret` 적용 |
| `local_server/routers/logs.py` | `query_logs`에 `require_local_secret` 적용 |
| `local_server/routers/ws.py` | WebSocket handshake `sec` query param 검증 (실패 시 code 4003) |
| `frontend/src/services/localClient.ts` | `setAuthToken` 응답에서 `local_secret` 추출/저장, request interceptor로 `X-Local-Secret` 헤더 자동 첨부 |

### 보호 분류
- **보호**: 모든 mutation (POST/PATCH), GET /config, GET /logs, GET /rules, WS /ws
- **면제**: GET /health, GET /api/status, GET /api/auth/status, POST /api/auth/token (secret 발급)

## Step 2: token.dat → Keyring 마이그레이션 (H1)

### 변경
- `local_server/main.py` — `_migrate_token_dat()` 함수 추가 (lifespan 시작 시 1회 실행)
- `local_server/cloud/auth_client.py`는 이미 contract-alignment에서 삭제됨 → plan §2.2와 차이. 마이그레이션 로직만 main.py에 구현

### 동작
1. `%APPDATA%\StockVision\token.dat` 존재 확인
2. 내용 읽기 → `save_credential(KEY_CLOUD_REFRESH_TOKEN, token)`
3. 파일 삭제

## Step 3: 비밀번호 최소 길이 검증 (H5)

### 변경
- `cloud_server/api/auth.py` — `field_validator` import 추가, `MIN_PASSWORD_LENGTH = 8` 상수, `RegisterBody.password`와 `ResetPasswordBody.new_password`에 검증 추가

### 검증 결과
- 8자 이상 비밀번호 → 통과
- 7자 이하 비밀번호 → `ValidationError` (422)

## 빌드 검증

- Python import: OK
- 비밀번호 validator 단위 테스트: 통과/거부 정상
- TypeScript `tsc -b`: 기존 에러 12개 (우리 변경과 무관, pre-existing)

## plan과의 차이

| plan | 실제 | 이유 |
|------|------|------|
| Step 2에서 `auth_client.py` 수정 | `main.py`에 마이그레이션 함수만 추가 | `auth_client.py`가 contract-alignment에서 이미 삭제됨 |
