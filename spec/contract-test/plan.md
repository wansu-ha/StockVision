# 계약 테스트 구현 계획

> 작성일: 2026-03-09 | 상태: 초안

## Step 1: 인프라 설정

**대상 파일:**
- `pytest.ini` (신규) — live 마커, addopts
- `local_server/tests/conftest.py` (신규) — test_routers.py에서 픽스처 추출
- `local_server/tests/test_routers.py` (수정) — 픽스처 코드 제거, import/테스트 유지

**검증:** `python -m pytest local_server/tests/test_routers.py -v` — 기존 테스트 전체 통과

## Step 2: status.py 코드 수정

**대상 파일:**
- `local_server/routers/status.py` — `broker.has_credentials` 필드 추가

**변경:** `has_credential(KEY_CLOUD_ACCESS_TOKEN)` 호출 결과를 broker 객체에 추가

**검증:** `python -m pytest local_server/tests/test_routers.py::TestStatusRouter -v` 통과

## Step 3: cloud_server 계약 테스트

**대상 파일:**
- `cloud_server/tests/test_contract.py` (신규) — CT-1a/b/c/e, CT-2a/b/c/d (~8개)

**픽스처:** 기존 conftest.py의 client, db, _make_user, _auth_header 재사용

**검증:** `python -m pytest cloud_server/tests/test_contract.py -v` 전체 통과

## Step 4: local_server 계약 테스트

**대상 파일:**
- `local_server/tests/test_contract.py` (신규) — CT-3a/b, CT-4a/b/c/d/e, CT-6c (~12개)

**픽스처:** conftest.py에서 추출한 tmp_config, client, sh 재사용

**검증:** `python -m pytest local_server/tests/test_contract.py -v` 전체 통과

## Step 5: 레거시 제거 검증 테스트

**대상 파일:**
- `tests/test_legacy_removal.py` (신규) — CT-7a

**검증:** `python -m pytest tests/test_legacy_removal.py -v` 통과

## Step 6: 전체 검증

- `python -m pytest cloud_server/tests/ -v` — 전체 통과
- `python -m pytest local_server/tests/ -v` — 전체 통과
- `python -m pytest tests/test_legacy_removal.py -v` — 통과

## 결과

| Step | 통과/실패 | 비고 |
|------|----------|------|
| 1 | 19/19 통과 | 픽스처 추출 후 기존 test_routers.py 전체 통과 |
| 2 | 19/19 통과 | has_credentials 필드 추가, 기존 테스트 영향 없음 |
| 3 | 8/8 통과 | rate limiter 누적 이슈 해결 (login_limiter._store.clear()) |
| 4 | 9/9 통과 | WS close code 4003 검증: WebSocketDisconnect 예외 캐치 |
| 5 | 1/1 통과 | 주석 내 localhost:8000 허용, URL 패턴만 검사 |
| 6 | 전체 통과 | cloud 46개, local 116개, legacy 1개 — regression 없음 |
