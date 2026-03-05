# Step 10 리포트: IdempotencyGuard + ErrorClassifier

## 생성/수정된 파일
- `local_server/broker/kiwoom/idempotency.py`
- `local_server/broker/kiwoom/error_classifier.py`

## 주요 구현 내용

### IdempotencyGuard
- `check(client_order_id)`: 기존 기록 조회, 있으면 반환 (중복 방지)
- `register(result)`: 주문 성공 후 결과 등록
- TTL 기반 자동 만료: 24시간 후 기록 삭제
- asyncio.Lock으로 동시 접근 안전 처리
- `DuplicateOrderError`: 호출자가 구분 사용 가능한 예외 (현재 미사용, 참고용)

### ErrorClassifier
- `classify_http_error(exc)`: HTTP 상태 코드 → ErrorCategory
- `classify_api_response(json)`: rt_cd + msg_cd → ErrorCategory
- `classify_exception(exc)`: 일반 예외 분류
- `is_retryable(category)`: TRANSIENT/RATE_LIMIT → True
- `needs_reauth(category)`: AUTH → True

### 주요 코드 매핑
- HTTP 401 → AUTH, 429 → RATE_LIMIT, 500/502/503 → TRANSIENT
- msg_cd EGW00123/121 → AUTH, EGW00201/202 → RATE_LIMIT

## 리뷰에서 발견한 이슈 및 수정 사항
- classify_api_response에서 rt_cd="0" (정상)도 TRANSIENT 반환 — 호출자가 rt_cd 확인 후 무시 필요
- msg_cd 매핑은 키움 API 문서 기반으로 확장 가능

## 테스트 결과
- 구문 오류 없음

## 다음 Step과의 연결점
- Step 11 KiwoomAdapter.place_order()에서:
  1. IdempotencyGuard.check() → 중복이면 기존 결과 반환
  2. 주문 실행 후 IdempotencyGuard.register()
  3. 예외 발생 시 ErrorClassifier.classify_exception() → 재시도/재인증 판단
