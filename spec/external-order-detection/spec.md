# 외부 주문 감지 + 경고 (External Order Detection)

> 작성일: 2026-03-12 | 상태: 초안 | Phase C

## 1. 배경

사용자가 증권사 앱(MTS)이나 HTS에서 직접 주문을 넣으면, StockVision의 System Trader가 모르는 포지션 변동이 발생한다.
이로 인해 포트폴리오 스냅샷이 실제와 불일치하고, 중복 주문이나 잘못된 손절이 발생할 수 있다.

System Trader spec §13 Phase 3에 "external order 감지 훅 연결"이 명시되어 있다.

## 2. 목표

StockVision이 관리하지 않는 외부 주문을 감지하고, 사용자에게 경고하여 포트폴리오 정합성을 유지한다.

## 3. 범위

### 3.1 포함

- 브로커 계좌의 체결/미체결 주문을 주기적으로 조회하여 외부 주문 식별
- 외부 주문 감지 시 사용자 경고 (알림 + 대시보드 표시)
- System Trader에 외부 주문 감지 상태 전달 (PortfolioSnapshot.external_order_detected)
- 정책에 따른 자동 대응: 경고만 / 신규 주문 일시 중지 / 엔진 정지

### 3.2 제외

- 외부 주문의 자동 취소나 수정
- 외부 주문을 System Trader 전략에 자동 편입
- 다른 계좌의 주문 감지

## 4. 의존성

| 의존 대상 | 상태 | 비고 |
|-----------|------|------|
| System Trader Phase 1-2 | 완료 | CandidateSignal, ExecutionResult 존재 |
| KIS Reconciler | **완료** | `local_server/broker/kis/reconciler.py` — GHOST 감지 (서버에만 있는 주문) |
| 브로커 API (미체결 조회) | 완료 | `adapter.get_open_orders()` 존재 (KIS, 키움 모두) |

### 기존 Reconciler 현황 (2026-03-15 점검)

`local_server/broker/kis/reconciler.py`에 기본 대사 모듈이 이미 존재한다:
- 30초 주기로 브로커 미체결 주문과 로컬 상태 비교
- GHOST 감지: 서버에만 있는 주문 → 현재는 **조용히 로컬에 흡수**
- ORPHAN 감지: 로컬에만 있는 주문 → 체결 완료로 동기화
- MISMATCH 감지: 상태 불일치 → 서버 기준 동기화

**GHOST가 외부 주문 감지의 기반이지만 다음이 부족:**

| 부족한 점 | 설명 |
|-----------|------|
| 경고/정책 없음 | GHOST 감지 시 조용히 흡수만 함. 사용자 알림·정책 적용 없음 |
| 최초 기동 오탐 | `_local_orders`가 메모리 전용이라 재시작 시 빈 상태. 기존 주문 전부 GHOST 처리됨 |
| 영속화 없음 | `_local_orders` dict가 메모리만. 재시작 시 소멸 |
| KIS 전용 | 키움 어댑터에 Reconciler 없음 |
| IntentStore 없음 | `intent_id`는 단순 문자열. 주문-인텐트 매핑 저장소 없음 |

**따라서 선행 작업은 해소됨 — 기존 GHOST 이벤트에 정책/알림을 연결하면 구현 가능.**

## 5. 감지 메커니즘

### 5.1 식별 기준

"외부 주문"의 정의:
- 브로커 계좌에 존재하는 미체결/체결 주문 중
- StockVision의 IntentStore에 대응하는 OrderIntent가 없는 것
- 구체적으로: `broker_order_id`가 Reconciler의 `_local_orders`에 등록되지 않은 주문 (GHOST)

### 5.2 최초 기동 처리

StockVision 기동 시 이미 존재하는 브로커 주문(기동 전 주문)을 외부 주문으로 오탐지하지 않도록:
- 기동 시 최초 reconciliation에서 발견된 주문은 "기존 주문"으로 등록 (외부 경고 안 함)
- 이후 감지 주기에서 새로 나타나는 미등록 주문만 외부 주문으로 판정

### 5.3 감지 주기

- Reconciler가 평가 주기마다 브로커의 open orders + 당일 체결을 조회
- 조회 결과에서 IntentStore에 없고 "기존 주문" 목록에도 없는 주문을 필터링
- 외부 주문이 발견되면 이벤트 발행

### 5.3 감지 결과 모델

```python
@dataclass
class ExternalOrderEvent:
    detected_at: datetime
    broker_order_id: str
    symbol: str
    side: Literal["BUY", "SELL"]
    qty: int
    price: Decimal
    status: str           # 미체결 / 체결
    source: str           # "UNKNOWN" (추후 MTS/HTS 식별 가능하면 확장)
```

## 6. 대응 정책

### 6.1 정책 옵션

사용자가 설정에서 선택 가능:

| 정책 | 동작 | 기본값 |
|------|------|--------|
| `WARN_ONLY` | 경고만 표시, 엔진 계속 실행 | ✓ |
| `PAUSE_NEW` | 경고 + 신규 주문 일시 중지 (기존 포지션 유지) | |
| `HALT_ENGINE` | 경고 + 엔진 정지 (ArmSession 해제) | |

### 6.2 정책 적용 흐름

1. Reconciler가 외부 주문 감지
2. ExternalOrderEvent 로그 기록
3. PortfolioSnapshot.external_order_detected = True
4. 정책에 따라:
   - WARN_ONLY: 로그만, System Trader는 계속 (단, 스냅샷에 경고 플래그)
   - PAUSE_NEW: System Trader가 신규 BUY 차단 (REDUCING 유사)
   - HALT_ENGINE: 엔진 정지 + ArmSession 해제

### 6.3 해제 조건

외부 주문 경고 해제:
- 사용자가 "확인" 버튼으로 명시적 해제
- 해제 시 현재 포트폴리오 스냅샷으로 재동기화

## 7. 프론트엔드 표시

### 7.1 경고 배너

운영 패널에 경고 배너:
```
⚠️ 외부 주문 감지: 005930 매수 100주 (MTS에서 주문?)
   [확인하고 계속] [엔진 정지]
```

### 7.2 알림

NotificationCenter에 외부 주문 감지 알림 추가.
원격 모드에서도 조회 가능 (Spec 2 연동).

### 7.3 로그 연동

ExecutionLog에 외부 주문 이벤트 별도 표시 (log_type: EXTERNAL).

## 8. 수용 기준

- [ ] MTS/HTS에서 넣은 주문이 StockVision 대시보드에 경고로 표시된다
- [ ] 경고 정책 (WARN_ONLY/PAUSE_NEW/HALT_ENGINE)을 설정에서 선택할 수 있다
- [ ] 외부 주문 감지 시 PortfolioSnapshot.external_order_detected가 true가 된다
- [ ] 사용자가 확인 후 경고를 해제하고 정상 운영을 재개할 수 있다
- [ ] StockVision이 낸 주문은 외부 주문으로 오탐지되지 않는다
- [ ] 기동 시 이미 존재하는 주문은 외부 주문으로 오탐지되지 않는다
