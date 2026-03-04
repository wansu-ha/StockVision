# StockVision 아키텍처 다이어그램

> 최종 갱신: 2026-03-05 (v3: DEGRADED 정책/reconcile/용어 통일) | `docs/architecture.md` 기반

---

## 1. 전체 시스템 구조

```mermaid
graph TB
    UI[프론트엔드<br/>React SPA]

    subgraph Cloud["클라우드"]
        API["API 서버<br/>auth · rules · admin"]
        Data["데이터 서버<br/>market_data · ai"]
        CloudDB[(PostgreSQL)]
    end

    subgraph Local["로컬 · 127.0.0.1"]
        Engine["전략 엔진 + 안전장치"]
        Broker[BrokerAdapter]
        Tray["트레이 🟢🟡🔴"]
        Store["SQLite + 규칙 캐시"]
    end

    Kiwoom[키움 REST API]
    Claude[Claude API]

    UI -->|HTTPS| API
    UI -->|localhost| Engine
    Engine -->|HTTP 폴링| API
    Broker -->|유저 키| Kiwoom
    Data -->|서비스 키| Kiwoom
    Data -->|HTTP| Claude
```

---

## 2. 주문 흐름

```mermaid
sequenceDiagram
    participant E as 전략 엔진
    participant S as 안전장치
    participant K as 키움

    Note over E: 매 1분 (장 시간)

    E->>S: Kill Switch?
    alt ON
        S-->>E: 차단 → 로그
    else OFF
        E->>S: 상태 READY?
        alt DEGRADED
            S-->>E: Trading 차단 (STOP_NEW)
        else READY
            E->>E: 분봉 확인 + 규칙 평가
            E->>S: 중복/한도/손실/속도?

            alt 통과
                E->>K: 현재가 재조회
                K-->>E: 현재가

                alt 가격 일치
                    E->>K: 주문 (ORDER_SENT)
                    K-->>E: 접수 (ACCEPTED)
                    Note over E: 로그 + WS 알림
                    Note over E: 10초 내 체결 미수신 → reconcile()
                else 불일치
                    Note over E: 거부 로그
                end
            else 손실 초과
                S->>K: 미체결 전량 취소
                Note over S: Trading 차단 + 락
            end
        end
    end
```

---

## 3. 규칙 동기화

```mermaid
sequenceDiagram
    participant P as 폰
    participant C as 클라우드
    participant PC as PC

    P->>C: 규칙 저장
    C->>C: DB + version++

    Note over PC: 하트비트 (30초~1분)
    PC->>C: heartbeat
    C-->>PC: version 변경
    PC->>C: fetch 규칙
    C-->>PC: 규칙 데이터
    PC->>PC: 캐시 갱신
```

---

## 4. 인증 흐름

```mermaid
sequenceDiagram
    participant W as 브라우저
    participant C as 클라우드
    participant L as 로컬

    W->>C: 로그인
    C-->>W: JWT + exchange code
    W->>L: exchange code 전달 (1회)
    L->>C: code → Refresh 교환
    C-->>L: Refresh Token
    L->>L: Refresh → Credential Manager
    Note over L: JWT 메모리만, Refresh CM만

    Note over L: 이후 자립 동작
    L->>C: JWT로 API 호출

    Note over L: JWT 만료 시
    L->>C: Refresh → 갱신
    C-->>L: 새 JWT
```

---

## 5. 데이터 위치

```mermaid
graph TB
    subgraph Cloud["클라우드 — 돈 모름"]
        A1[이메일·닉네임]
        A2[규칙 원본]
        A3[시세·분석]
    end

    subgraph Local["로컬 — 돈 다룸"]
        B1[키움 Key]
        B2[Refresh Token]
        B3[체결 로그]
    end
```

---

## 6. 키 분리

```mermaid
graph TB
    SK["서비스 키 (우리)"]
    UK["유저 키 (사용자)"]
    KA[키움 API]

    SK -->|시세 수집| KA
    UK -->|시세 + 주문| KA

    SK -.- C[클라우드]
    UK -.- L[로컬]
```

---

## 7. BrokerAdapter

```mermaid
classDiagram
    class BrokerAdapter {
        <<ABC>>
        +authenticate()
        +send_order()
        +cancel_order()
        +get_current_price()
        +get_balance()
        +subscribe()
        +listen()
    }
    class KiwoomAdapter {
        R1 RateLimiter
        R2 StateMachine
        R3 reconnect_resubscribe()
        R4 reconcile()
        R5 idempotency
        R6 ErrorClassifier
    }
    class MockAdapter {
        가상 거래 · 테스트
    }

    BrokerAdapter <|.. KiwoomAdapter
    BrokerAdapter <|.. MockAdapter
```

---

## 8. KiwoomAdapter 상태 머신

```mermaid
stateDiagram-v2
    [*] --> DISCONNECTED

    DISCONNECTED --> CONNECTING: 시작
    CONNECTING --> AUTHED: 토큰 성공
    CONNECTING --> DISCONNECTED: 실패

    AUTHED --> SYNCING: WS 구독
    SYNCING --> READY: 완료

    READY --> DEGRADED: 끊김/오류 (STOP_NEW)
    DEGRADED --> CONNECTING: 재연결
    DEGRADED --> READY: 복구 (WS+구독+reconcile)

    READY --> DISCONNECTED: 종료
    DEGRADED --> DISCONNECTED: 종료
```

**READY 복귀 조건**: WS 연결 정상 + 구독 성공 + reconcile 1회 성공 (미체결/잔고/체결 정합)

**reconcile 원칙**: 키움 계좌 상태 = source of truth. 엔진 내부 상태(미체결/잔고)를 계좌 기준으로 보정.
