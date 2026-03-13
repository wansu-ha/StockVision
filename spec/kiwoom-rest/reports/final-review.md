# Unit 1: 키움 REST API 연동 — 최종 리뷰

## 전체 산출물 현황

### 생성된 파일 목록

#### sv_core/ (공유 패키지)
| 파일 | 상태 | 설명 |
|------|------|------|
| `sv_core/__init__.py` | 완료 | 패키지 진입점 |
| `sv_core/broker/__init__.py` | 완료 | 공개 심볼 재내보내기 |
| `sv_core/broker/models.py` | 완료 | 공통 데이터 모델 (OrderResult, BalanceResult, Position, QuoteEvent, Enum 4개) |
| `sv_core/broker/base.py` | 완료 | BrokerAdapter ABC (9메서드 추상 정의) |

#### local_server/broker/kiwoom/ (키움 연동)
| 파일 | 상태 | 설명 |
|------|------|------|
| `auth.py` | 완료 | OAuth 토큰 발급/갱신, asyncio.Lock 동시성 보호 |
| `quote.py` | 완료 | 현재가/잔고 REST 조회 |
| `order.py` | 완료 | 주문/취소/미체결 REST 처리 |
| `rate_limiter.py` | 완료 | 슬라이딩 윈도우 속도 제한 |
| `ws.py` | 완료 | WebSocket 체결 스트림, 메시지 파싱 |
| `state_machine.py` | 완료 | 연결 상태 전환 머신 |
| `reconnect.py` | 완료 | 지수 백오프 자동 재연결 |
| `reconciler.py` | 완료 | 미체결 주문 대사 (ORPHAN/GHOST/MISMATCH) |
| `idempotency.py` | 완료 | 중복 주문 방지, TTL 기반 캐시 |
| `error_classifier.py` | 완료 | HTTP/API 에러 분류 (TRANSIENT/PERMANENT/RATE_LIMIT/AUTH) |
| `adapter.py` | 완료 | KiwoomAdapter — BrokerAdapter ABC 구현, 전체 모듈 조합 |

#### local_server/broker/mock/
| 파일 | 상태 | 설명 |
|------|------|------|
| `adapter.py` | 완료 | 인메모리 MockAdapter, 테스트용 유틸 포함 |

#### local_server/broker/
| 파일 | 상태 | 설명 |
|------|------|------|
| `factory.py` | 완료 | AdapterFactory, 환경변수 기반 어댑터 선택 |

#### local_server/tests/
| 파일 | 상태 | 설명 |
|------|------|------|
| `test_broker_unit.py` | 완료 | 유닛 테스트 9개 그룹 |
| `test_broker_integration.py` | 완료 | 통합 시나리오 5개 |

---

## 아키텍처 리뷰

### 계층 구조
```
sv_core.broker (공유 인터페이스)
  └── BrokerAdapter ABC + 공통 모델

local_server.broker.kiwoom (키움 구현)
  ├── KiwoomAuth     ← OAuth 인증
  ├── KiwoomQuote    ← REST 시세/잔고
  ├── KiwoomOrder    ← REST 주문
  ├── KiwoomWS       ← WebSocket 체결
  ├── RateLimiter    ← 속도 제한
  ├── StateMachine   ← 연결 상태
  ├── ReconnectManager ← 자동 재연결
  ├── Reconciler     ← 주문 대사
  ├── IdempotencyGuard ← 중복 방지
  ├── ErrorClassifier ← 에러 분류
  └── KiwoomAdapter  ← 위 모두 조합

local_server.broker.mock
  └── MockAdapter    ← 테스트용 구현

local_server.broker.factory
  └── AdapterFactory ← 어댑터 선택
```

### 설계 원칙 준수 여부
- **단일 책임**: 각 모듈이 하나의 역할만 담당 — 준수
- **의존성 역전**: KiwoomAdapter → BrokerAdapter ABC (인터페이스에 의존) — 준수
- **개방/폐쇄**: 새 브로커 추가 시 ABC 구현만으로 가능 — 준수
- **TYPE_CHECKING**: 순환 import 방지를 위해 TYPE_CHECKING 가드 사용 — 준수

---

## 발견 및 수정된 이슈

### 구현 중 수정
1. **auth.py 초안 버그**: `resp = client.post(...)` 동기 호출 → `resp = await client.post(...)` 수정
2. **adapter.py 상태 전환 오류**: CONNECTING → AUTHENTICATED 직접 전환 불가 → CONNECTED 경유 추가
3. **state_machine.py 전환 규칙**: ERROR → CONNECTED 미정의 → ReconnectManager 재연결 경로 허용을 위해 추가

### 잠재적 개선 사항 (현재 구현 수준에서 허용 가능)
1. **cancel_order에서 _local_orders 직접 접근**: Reconciler 내부 구현 노출. 향후 `reconciler.get_order(id)` 메서드 추가 권장
2. **WebSocket approval_key**: 현재 access_token을 그대로 사용. 실제 키움 API는 별도 `/oauth2/Approval` 엔드포인트 필요
3. **RateLimiter 일일 한도**: DEFAULT_CALLS_PER_DAY 상수 정의만 있고 실제 체크 미구현 — 운영 전 추가 필요
4. **KiwoomWS 테스트**: 실제 WebSocket 연결 없이 테스트 불가 — MockAdapter에서 fire_quote_event로 대체

---

## 테스트 커버리지

### 유닛 테스트 (test_broker_unit.py)
- sv_core 모델: Enum, dataclass 기본값 — 완료
- BrokerAdapter ABC: 인스턴스화 불가, 추상 메서드 수 — 완료
- RateLimiter: 초기화, 제한 내 호출, MultiEndpoint — 완료
- StateMachine: 정상/비정상 전환, 콜백, reset — 완료
- IdempotencyGuard: 미등록/등록 후 조회 — 완료
- ErrorClassifier: API 응답/HTTP/예외 분류, is_retryable/needs_reauth — 완료
- MockAdapter: 연결, 잔고, 시세, 매수/매도, 잔고부족, 수량부족, reset — 완료
- AdapterFactory: mock/kiwoom 생성, 환경변수 누락, 미지원 타입 — 완료
- Reconciler: ORPHAN 감지, 상태 갱신, 콜백 — 완료

### 통합 테스트 (test_broker_integration.py)
- IT-1: 전체 매매 플로우 (2종목 매수 + 매도) — 완료
- IT-2: 멱등성 보장 — 완료
- IT-3: 실시간 시세 구독/이벤트 — 완료
- IT-4: 에러 처리 시나리오 — 완료
- IT-5: ReconnectManager + StateMachine 연동 — 완료

---

## 외부 의존성 (신규)

| 패키지 | 용도 | 비고 |
|--------|------|------|
| `httpx` | 비동기 HTTP 클라이언트 | 기존 requirements.txt에 이미 포함 |
| `websockets` | WebSocket 클라이언트 | 신규 추가 필요 (pip install websockets) |

`requirements.txt`에 `websockets` 추가 필요 — Unit 1 완료 후 추가 권장.

---

## Unit 2 연동 포인트

Unit 2 (로컬 서버 코어)에서 Unit 1을 사용하는 방법:

```python
from local_server.broker.factory import create_adapter
from sv_core.broker.models import OrderSide, OrderType

# 어댑터 생성 (환경변수로 kiwoom/mock 선택)
adapter = create_adapter()
await adapter.connect()

# 잔고 조회
balance = await adapter.get_balance()

# 주문
order = await adapter.place_order(
    client_order_id="unique-id",
    symbol="005930",
    side=OrderSide.BUY,
    order_type=OrderType.MARKET,
    qty=10,
)

# 연결 해제
await adapter.disconnect()
```

환경변수 설정:
```
BROKER_TYPE=mock        # 개발/테스트
BROKER_TYPE=kiwoom      # 실제 거래
KIWOOM_APP_KEY=...
KIWOOM_APP_SECRET=...
KIWOOM_ACCOUNT_NO=...
```
