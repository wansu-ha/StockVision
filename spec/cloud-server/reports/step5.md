# Step 5 보고서: 시세 수집기 (KISCollector, sv_core)

> 완료일: 2026-03-05

## 구현 내용

### 생성된 파일

| 파일 | 설명 |
|------|------|
| `sv_core/__init__.py` | sv_core 공유 패키지 stub |
| `sv_core/broker/base.py` | BrokerAdapter ABC |
| `sv_core/models/quote.py` | QuoteEvent 데이터 클래스 |
| `cloud_server/core/broker_factory.py` | BrokerAdapter 팩토리 + KiwoomStub |
| `cloud_server/collector/kis_collector.py` | 키움 시세 수집기 |
| `cloud_server/models/template.py` (KiwoomServiceKey) | 서비스 키 모델 |

### sv_core 구조 (stub)

```
sv_core/
├── broker/
│   └── base.py    # BrokerAdapter ABC
└── models/
    └── quote.py   # QuoteEvent
```

Unit 1 완성 후 `sv_core.broker.kiwoom.KiwoomAdapter` 로 교체.

### BrokerFactory

- `BrokerFactory.create("kiwoom", service_key)` → KiwoomAdapter 또는 KiwoomStub (미설치 시)
- 서비스 키 DB에서 조회 → api_secret 복호화 후 주입

### KISCollector

```python
collector = KISCollector(broker)
await collector.subscribe(symbols, "quote")
async for event in collector.listen():
    # event: QuoteEvent(symbol, price, volume, timestamp)
    await repo.save_minute_bar(event)
```

## 검증 결과

- [x] BrokerAdapter ABC 정의 (stub)
- [x] KiwoomStub 구현 (빈 이터레이터)
- [x] KISCollector (subscribe, listen, stop)
- [x] 서비스 키 암호화 저장 (AES-256-GCM)
- [ ] 실제 키움 WS 연결 (Unit 1 KiwoomAdapter 완성 후)
