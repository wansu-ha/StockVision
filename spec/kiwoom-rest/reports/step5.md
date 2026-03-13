# Step 5 리포트: RateLimiter

## 생성/수정된 파일
- `local_server/broker/kiwoom/rate_limiter.py`

## 주요 구현 내용

### RateLimiter
- 슬라이딩 윈도우(1초) 방식으로 초당 호출 수 제한
- `_call_times: list[float]`에 monotonic 시각 기록
- `acquire()`: 1초 내 호출 수 < 한도면 즉시 반환, 초과 시 대기
- asyncio.Lock으로 동시 acquire 경합 방지
- `total_calls` property로 누적 통계 조회

### MultiEndpointRateLimiter
- 엔드포인트별 독립 RateLimiter 관리
- `set_limit(endpoint, cps)`: 특정 엔드포인트 한도 설정
- `acquire(endpoint)`: 해당 엔드포인트 토큰 획득

### 상수
- `DEFAULT_CALLS_PER_SECOND = 20` (키움 기본)
- `DEFAULT_CALLS_PER_DAY = 100_000`

## 리뷰에서 발견한 이슈 및 수정 사항
- asyncio.Semaphore는 단순 카운터라 슬라이딩 윈도우 구현이 어려움 → `_call_times` 리스트로 대체
- `asyncio.Lock` 으로 동시 접근 시 경쟁 상태 방지

## 테스트 결과
- 단위 테스트: Step 13 test_broker_unit.py에서 RateLimiter 시나리오 검증

## 다음 Step과의 연결점
- Step 6 KiwoomWS는 별도 제한 없음 (WebSocket은 연결 수로 제한)
- Step 11 KiwoomAdapter에서 MultiEndpointRateLimiter 인스턴스 생성 및 주입
