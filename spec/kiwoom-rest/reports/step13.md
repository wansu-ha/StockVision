# Step 13 리포트: AdapterFactory + 테스트

## 생성/수정된 파일
- `local_server/broker/factory.py` — AdapterFactory + create_adapter 편의 함수
- `local_server/tests/__init__.py`
- `local_server/tests/test_broker_unit.py` — 유닛 테스트 9개 그룹
- `local_server/tests/test_broker_integration.py` — 통합 테스트 5개 시나리오

## 주요 구현 내용

### AdapterFactory
- `create(broker_type, **kwargs)`: 환경변수 또는 명시적 파라미터로 어댑터 선택
- `_create_kiwoom(**kwargs)`: KIWOOM_APP_KEY, KIWOOM_APP_SECRET, KIWOOM_ACCOUNT_NO 확인 후 생성
- `_create_mock(**kwargs)`: initial_cash 선택 인자로 MockAdapter 생성
- `create_adapter(broker_type)`: 모듈 수준 편의 함수

### 유닛 테스트 (test_broker_unit.py)
1. sv_core.broker.models — Enum 값, dataclass 기본값
2. BrokerAdapter ABC — 인스턴스화 불가, 추상 메서드 10개 존재
3. RateLimiter — 초기화, 제한 내 호출, MultiEndpointRateLimiter
4. StateMachine — 상태 전환, 잘못된 전환 거부, 콜백, reset
5. IdempotencyGuard — 미등록 None, 등록 후 기존 결과 반환
6. ErrorClassifier — API 응답/HTTP 분류, is_retryable, needs_reauth
7. MockAdapter — 연결, 잔고, 시세, 매수/매도, 잔고 부족, reset
8. AdapterFactory — mock 생성, kiwoom 환경변수 누락 오류, 미지원 타입 오류
9. Reconciler — ORPHAN 감지, FILLED 갱신, 이벤트 콜백

### 통합 테스트 (test_broker_integration.py)
- IT-1: 전체 매매 플로우 (연결→잔고→시세→매수→포지션→매도→해제)
- IT-2: 멱등성 보장 (동일 ID 중복 요청 → 기존 결과 반환)
- IT-3: 실시간 시세 구독 + 이벤트 처리
- IT-4: 에러 처리 (잔고 부족, 보유 수량 부족, 미연결)
- IT-5: ReconnectManager + StateMachine 연동

## 리뷰에서 발견한 이슈 및 수정 사항
- adapter.py _do_connect: CONNECTING → AUTHENTICATED 직접 전환 불가 → CONNECTED 경유 수정
- state_machine.py: ERROR → CONNECTED 전환 허용 추가 (ReconnectManager 재연결 경로)
- 모든 구문 오류 및 타입 힌트 정적 검토 완료

## 테스트 실행 방법
```bash
# 유닛 테스트
python local_server/tests/test_broker_unit.py

# 통합 테스트
python local_server/tests/test_broker_integration.py
```

## 다음 Step과의 연결점
- Unit 2 로컬 서버 코어에서 KiwoomAdapter 또는 MockAdapter를 AdapterFactory로 생성
- AdapterFactory는 환경변수로 제어하므로 배포 환경 분리 가능
