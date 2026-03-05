# Step 3 보고서: REST 라우터

## 생성/수정된 파일

- `local_server/routers/__init__.py` — 패키지 초기화
- `local_server/routers/auth.py` — POST /api/auth/token, POST /api/auth/logout, GET /api/auth/status
- `local_server/routers/config.py` — GET/PATCH /api/config
- `local_server/routers/status.py` — GET /api/status
- `local_server/routers/trading.py` — POST /api/strategy/start, stop, POST /api/trading/order
- `local_server/routers/rules.py` — POST /api/rules/sync, GET /api/rules
- `local_server/routers/logs.py` — GET /api/logs

## 구현 내용 요약

### auth.py
- POST /api/auth/token: app_key/app_secret → keyring 저장 → stub 토큰 반환
- POST /api/auth/logout: clear_all_credentials()
- GET /api/auth/status: 자격증명/토큰 존재 여부 확인

### config.py
- GET /api/config: read_config() (민감정보 마스킹)
- PATCH /api/config: update_config() (부분 업데이트)

### status.py
- GET /api/status: 서버 running, 브로커 has_credentials, 전략 엔진 running 상태
- set_strategy_running() / is_strategy_running() — 인메모리 상태 관리

### trading.py
- POST /api/strategy/start: 자격증명 확인 → 엔진 시작, 로그 기록
- POST /api/strategy/stop: 엔진 중지, 로그 기록
- POST /api/trading/order: OrderRequest 유효성 검사 → 주문 로그 기록 (stub)

### rules.py
- POST /api/rules/sync: body.rules 있으면 직접 동기화, 없으면 클라우드 fetch
- GET /api/rules: 캐시된 규칙 목록 반환

### logs.py
- GET /api/logs: log_type/symbol 필터, limit/offset 페이지네이션

## 리뷰 발견 사항

- 모든 응답이 { success, data, count } 형식 준수
- trading.py: LIMIT 주문 시 limit_price 없으면 422 반환
- trading.py: 자격증명 없으면 400 반환 (401이 아닌 이유: keyring 기반 로컬 인증)
- auth.py: GET /api/auth/status 추가 (spec에 명시는 안 됐지만 프론트엔드 필요)
- rules.py: GET /api/rules 추가 (동기화 후 확인용)

## 테스트 결과

- 문법 검증: 정상
- 기능 테스트는 Step 12 (test_routers.py)에서 수행
