# 계약 테스트 명세서

> 작성일: 2026-03-09 | 상태: 구현 완료 | 갱신일: 2026-03-15

## 목적

`contract-alignment` spec(구현 완료)에 정의된 API 계약이 drift 없이 유지되는지
자동 테스트로 검증한다. 기존 통합 테스트(145개)는 **동작 검증**에 집중하므로,
본 테스트는 **응답 shape·필드·타입 검증**에 집중한다.

## 전제: 환경 게이트

### mock vs 실제 경계

| 경로 | 어댑터 | 외부 의존 | pytest marker |
|------|--------|-----------|---------------|
| 계약 테스트 + E2E | MockAdapter | 없음 | (기본, 마커 없음) |
| 키움 REST 외부 검증 | KiwoomAdapter | keyring 자격증명 + 키움 모의서버 | `@pytest.mark.live` |

- **계약 테스트와 E2E는 외부 의존 0으로 동작해야 한다.** CI에서도 돌아야 하므로.
- 키움 WS 모의서버 미지원 → 실시간 시세 E2E는 MockAdapter로만.
- `tests/test_kiwoom_live.py`는 live 마커로 격리, 기본 pytest 실행에서 제외.

### pytest 설정

프로젝트 루트(`d:\Projects\StockVision\`)에 `pytest.ini` 생성:

```ini
[pytest]
markers =
    live: 외부 브로커 API 필요 (keyring 자격증명)
addopts = -m "not live"
```

## 범위

`contract-alignment` spec의 C1~C4 + `security-hardening` 계약을 테스트로 고정.

**제외**: 프론트엔드 컴포넌트 테스트, 브로커 실제 API, DB 마이그레이션.

## 알려진 계약-구현 불일치

리뷰 과정에서 contract-alignment spec과 실제 코드 사이의 gap을 발견.
계약 테스트 구현 시 **코드를 수정**하여 계약에 맞추거나, 계약을 조정해야 한다.

| 계약 | spec 정의 | 실제 코드 | 결정 |
|------|----------|----------|------|
| C3-1 `broker.has_credentials` | `data.broker.has_credentials: bool` | `status.py`에 해당 필드 없음 (`broker.connected`만 존재) | **코드 수정** — `has_credential()` 함수가 이미 존재하므로 status 응답에 추가 |
| C2 register 응답 | contract-alignment에 shape 미정의 | 실제: `{"success": true, "message": "..."}`  (최상위 message, data 래퍼 없음) | **계약 추가** — 현재 코드를 정본으로 shape 고정 |

## 테스트 대상

### CT-1. 인증 응답 shape (cloud_server)

진실의 원천: `contract-alignment` C2, `cloud_server/api/auth.py`

| ID | 검증 항목 | 기존 커버 | 새 테스트 필요 |
|----|----------|----------|--------------|
| CT-1a | login 응답: `data.access_token` (str), `data.refresh_token` (str), `data.expires_in` (int) | 대부분 (`expires_in == 3600`으로 값+타입 확인) | 타입 명시 assertion 추가 |
| CT-1b | refresh 응답: login과 동일 shape (`data.expires_in` 포함) | 부분 (`expires_in` 미확인) | `expires_in` 타입+존재 검증 |
| CT-1c | `data.jwt` 키 부재 확인 (금지 키) | 없음 | **필요** |
| CT-1d | verify-email: GET 메서드 정합 | 있음 (`test_verify_email`) | 불필요 |
| CT-1e | register 응답: `success` (bool), `message` (str) — data 래퍼 없음 | 부분 (`success`만) | `message` 필드 존재+타입 |

### CT-2. 규칙(Rule) 응답 shape (cloud_server)

진실의 원천: `contract-alignment` C1, `cloud_server/api/rules.py`

| ID | 검증 항목 | 기존 커버 | 새 테스트 필요 |
|----|----------|----------|--------------|
| CT-2a | Rule 객체 필수 필드 17개 전체 존재: id, name, symbol, is_active, priority, version, created_at, updated_at, script, execution, trigger_policy, buy_conditions, sell_conditions, order_type, qty, max_position_count, budget_ratio | 없음 (3개만) | **필요** — 전체 필드 검증 |
| CT-2b | 목록 응답 shape: `success` (bool), `data` (list), `version` (int), `count` (int) | 부분 (count, version만) | success + data 타입 추가 |
| CT-2c | PUT `/api/v1/rules/{id}` 성공 + PATCH 동일 경로 → 405 | 없음 | **필요** — FastAPI는 미등록 메서드에 405 반환 |
| CT-2d | Rule 응답에 금지 필드 부재: conditions, operator, side | 없음 | **필요** |

### CT-3. 상태 모델 shape (local_server)

진실의 원천: `contract-alignment` C3, `local_server/routers/status.py`

| ID | 검증 항목 | 기존 커버 | 새 테스트 필요 |
|----|----------|----------|--------------|
| CT-3a | GET /api/status: `data.broker.connected` (bool), `data.broker.has_credentials` (bool), `data.strategy_engine.running` (bool) | 부분 (키 존재만) | **필요** — 중첩 구조 + 타입 검증. ⚠️ `has_credentials` 필드는 현재 미구현, 계약 테스트 전에 `status.py`에 추가 필요 |
| CT-3b | GET /health: `status` (str), `version` (str) | 부분 (status만) | `version` 필드 존재 검증 |

### CT-4. 로컬 인증 (local_server)

진실의 원천: `security-hardening`, `local_server/core/local_auth.py`

| ID | 검증 항목 | 기존 커버 | 새 테스트 필요 |
|----|----------|----------|--------------|
| CT-4a | POST /api/auth/token 응답에 `data.local_secret` (str) + `data.message` (str) 포함 | 없음 | **필요** |
| CT-4b | 보호 엔드포인트 6개: X-Local-Secret 없이 호출 → 401/403. 대상: POST /logout, GET/PATCH /config, POST /strategy/start·stop, POST /trading/order, POST /rules/sync, GET /rules, GET /logs | 없음 | **필요** — 대표 3개 엔드포인트로 검증 |
| CT-4c | 면제 엔드포인트 4개: GET /health, GET /api/status, GET /api/auth/status, POST /api/auth/token → secret 없이 200 | 없음 | **필요** |
| CT-4d | WS /ws: sec param 없이 연결 → close code 4003 | 없음 | **필요** — `TestClient.websocket_connect()` 사용 |
| CT-4e | WS /ws: 올바른 sec → 연결 유지 | 없음 | **필요** |

### CT-5. 하트비트 shape (cloud_server)

진실의 원천: `contract-alignment` C3-3, `cloud_server/api/heartbeat.py`

| ID | 검증 항목 | 기존 커버 | 새 테스트 필요 |
|----|----------|----------|--------------|
| CT-5a | rules_version (int), context_version (int) | 있음 (`test_heartbeat.py:31~33`) | 불필요 |
| CT-5b | latest_version, min_version, download_url | 있음 (`test_heartbeat.py:69~71`) | 불필요 |
| CT-5c | 응답 전체 shape 불변 (추가 필드 drift 감지) | 있음 (`test_cloud_client.py:162~176` — 8개 필드 전체 검증) | 불필요 |

> CT-5 전체가 기존 테스트로 충분히 커버됨. 수용 기준에서 제외.

### CT-6. 규칙 sync + 폐기 API (local_server)

진실의 원천: `contract-alignment` C1-3, C1-4

| ID | 검증 항목 | 기존 커버 | 새 테스트 필요 |
|----|----------|----------|--------------|
| CT-6a | POST /api/rules/sync 응답: `data.synced_count` (int) | 있음 | 불필요 |
| CT-6b | GET /api/rules 응답: `data` (list), `count` (int) | 있음 | 불필요 |
| CT-6c | GET /api/variables → 404 | 없음 | **필요** |

### CT-7. 레거시 제거 검증

진실의 원천: `contract-alignment` C4

| ID | 검증 항목 | 기존 커버 | 새 테스트 필요 |
|----|----------|----------|--------------|
| CT-7a | 프론트엔드 소스(`frontend/src/`)에 `localhost:8000` 참조 0건 | 없음 | **필요** — grep 기반 테스트 |

## 구현 방식

### 파일 구조

```
cloud_server/tests/test_contract.py    — CT-1, CT-2
local_server/tests/conftest.py         — 기존 test_routers.py에서 픽스처 추출
local_server/tests/test_contract.py    — CT-3, CT-4, CT-6c
tests/test_legacy_removal.py           — CT-7
pytest.ini                             — 프로젝트 루트, live 마커 설정
```

기존 테스트 파일의 **테스트 코드는 수정하지 않는다.**
local_server `test_routers.py`에서 픽스처(`tmp_config`, `client`, `sh`)만 `conftest.py`로 추출.

### 코드 수정 (계약-구현 gap 해소)

| 파일 | 변경 | 이유 |
|------|------|------|
| `local_server/routers/status.py` | `broker` 객체에 `has_credentials` 필드 추가 | C3-1 계약 준수. `has_credential(KEY_CLOUD_ACCESS_TOKEN)` 호출로 구현 |

### 테스트 패턴

```python
def assert_shape(data: dict, required: set[str], forbidden: set[str] = frozenset()):
    """필수 키 존재 + 금지 키 부재"""
    missing = required - data.keys()
    assert not missing, f"필수 키 누락: {missing}"
    present = forbidden & data.keys()
    assert not present, f"금지 키 존재: {present}"
```

### 기존 픽스처 재사용

- cloud: `conftest.py`의 `client`, `db`, `_make_user`, `_auth_header` 그대로 사용
- local: `conftest.py`로 추출된 `tmp_config`, `client`, `sh` 사용

## 새로 작성할 테스트 요약

| 파일 | 테스트 수 | 대상 |
|------|----------|------|
| `cloud_server/tests/test_contract.py` | ~8개 | CT-1a/b/c/e, CT-2a/b/c/d |
| `local_server/tests/test_contract.py` | ~12개 | CT-3a/b, CT-4a/b/c/d/e, CT-6c |
| `tests/test_legacy_removal.py` | 1개 | CT-7a |

총 **~21개** 신규 테스트.

## 수용 기준

- [ ] CT-1a/b/c/e: 인증 응답 shape 검증 통과
- [ ] CT-2a~d: 규칙 응답 shape 검증 통과
- [ ] CT-3a~b: 상태 모델 shape 검증 통과 (has_credentials 포함)
- [ ] CT-4a~e: 로컬 인증 계약 검증 통과
- [ ] CT-6c: /api/variables → 404 검증 통과
- [ ] CT-7a: 레거시 참조 0건 검증 통과
- [ ] `status.py`에 `broker.has_credentials` 필드 추가 (계약-구현 gap 해소)
- [ ] local_server 픽스처 conftest.py 추출 완료
- [ ] `pytest.ini`에 live 마커 설정 완료
- [ ] 기존 테스트 145개 전부 통과 유지 (regression 없음)
