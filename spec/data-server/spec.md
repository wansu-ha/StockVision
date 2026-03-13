# 데이터 서버 명세서 (data-server)

> **⚠️ SUPERSEDED** — `spec/cloud-server/spec.md`에 병합됨 (2026-03-05).
> API 서버 + 데이터 서버 → 클라우드 서버로 통합.
>
> 작성일: 2026-03-04 | 상태: ~~초안~~ SUPERSEDED | Unit 5 (Phase 3-B)
>
> **참고**: `spec/data-source/` (데이터 소스 전략) 참조.
> **의존**: Unit 1의 키움 REST 클라이언트 재사용.

---

## 1. 목표

클라우드에서 운영되는 시세 수집/저장 서비스를 구현한다.
**서비스 키움 키**로 시세를 수신하여 내부 DB에 저장하고,
API 서버가 접근하여 컨텍스트 계산 등에 활용한다.

**핵심 원칙:**
- 외부 직접 접근 차단 (API 서버 뒤에 위치)
- 수집된 시세는 **내부 분석용** (유저 재배포 아님)
- 유저 시세는 각자 키움 키로 로컬에서 직접 수신
- 키움 제5조③ 시세 중계 금지 준수

---

## 2. 요구사항

### 2.1 기능적 요구사항

| ID | 요구사항 | 우선순위 |
|----|---------|---------|
| F1 | 서비스 키움 키로 실시간 시세 수신 (WebSocket) | P0 |
| F2 | 시세 데이터를 DB에 저장 (일봉, 분봉) | P0 |
| F3 | API 서버에서 접근 가능한 내부 API 제공 | P0 |
| F4 | 외부 직접 접근 차단 | P0 |
| F5 | 히스토리컬 데이터 축적 (과거 데이터 보관) | P1 |
| F6 | 서비스 키움 토큰 자동 갱신 | P1 |
| F7 | 기존 yfinance 데이터 소스 병행 (한국 외 시장) | P2 |
| F8 | 데이터 수집 상태 모니터링 API | P2 |

### 2.2 비기능적 요구사항

| 항목 | 목표 |
|------|------|
| 시세 수신 지연 | < 500ms (키움 WS) |
| 일봉 데이터 저장 | 장 마감 후 30분 이내 |
| 데이터 보관 기간 | 5년+ (일봉), 1년 (분봉) |
| 가동률 | > 99% (장 시간) |
| 동시 구독 종목 | 코스피/코스닥 주요 200종목 |

---

## 3. 아키텍처

### 3.1 위치

```
[외부] → ✗ (직접 접근 불가)

[API 서버] → HTTP → [데이터 서버] → WS → [키움 openapi]
                                     ↓
                              [PostgreSQL]
                              (시세 데이터)
```

### 3.2 모듈 구조

```
data_server/
├── main.py                    # FastAPI 앱 (내부 전용)
├── collector/
│   ├── kiwoom_collector.py    # 키움 WS 시세 수신 (서비스 키)
│   ├── yfinance_collector.py  # yfinance 보조 수집
│   └── scheduler.py           # 수집 스케줄 관리
├── storage/
│   ├── models.py              # DB 모델 (일봉, 분봉, 종목 마스터)
│   ├── repository.py          # DB CRUD
│   └── migrations/            # Alembic 마이그레이션
├── api/
│   ├── quotes.py              # 시세 조회 API (내부용)
│   ├── status.py              # 수집 상태 API
│   └── admin.py               # 서비스 키 관리 API
├── core/
│   ├── config.py              # 환경 변수
│   └── database.py            # DB 연결
└── requirements.txt
```

### 3.3 키움 클라이언트 재사용

Unit 1(`local_server/kiwoom/`)의 REST/WS 클라이언트를 **패키지로 분리**하거나
**코드 복사**하여 데이터 서버에서 사용.

```
# 옵션 A: 공유 패키지
stockvision-kiwoom/
├── auth.py
├── websocket.py
├── quote.py
└── rate_limiter.py

# 옵션 B: 데이터 서버에 복사
data_server/kiwoom/
├── auth.py
├── websocket.py
└── ...
```

---

## 4. 데이터 모델

### 4.1 종목 마스터

```python
class StockMaster(Base):
    __tablename__ = "stock_master"
    symbol = Column(String(10), primary_key=True)  # 종목코드
    name = Column(String(100), nullable=False)
    market = Column(String(10))     # KOSPI | KOSDAQ
    sector = Column(String(50))
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime)
```

### 4.2 일봉 데이터

```python
class DailyBar(Base):
    __tablename__ = "daily_bars"
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False, index=True)
    date = Column(Date, nullable=False)
    open = Column(Integer)
    high = Column(Integer)
    low = Column(Integer)
    close = Column(Integer)
    volume = Column(BigInteger)
    change_pct = Column(Float)       # 전일 대비 변동률
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("symbol", "date"),
        Index("idx_daily_symbol_date", "symbol", "date"),
    )
```

### 4.3 분봉 데이터

```python
class MinuteBar(Base):
    __tablename__ = "minute_bars"
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False)
    open = Column(Integer)
    high = Column(Integer)
    low = Column(Integer)
    close = Column(Integer)
    volume = Column(BigInteger)

    __table_args__ = (
        UniqueConstraint("symbol", "timestamp"),
        Index("idx_minute_symbol_ts", "symbol", "timestamp"),
    )
```

---

## 5. 내부 API

```
# 시세 조회 (API 서버만 접근)
GET /internal/quotes/:symbol/daily?start=2025-01-01&end=2026-03-04
    → 일봉 데이터 배열

GET /internal/quotes/:symbol/latest
    → 최신 시세

GET /internal/quotes/market-summary
    → 코스피/코스닥 지수, 전체 시장 요약

# 컨텍스트 계산용
GET /internal/context/indicators?symbols=005930,000660
    → RSI, MACD, 볼린저 등 기술적 지표

# 상태
GET /internal/status
    → 수집 상태, 마지막 수신 시각, 에러 수

# 서비스 키 관리 (어드민 경유)
POST /internal/admin/service-key
    → 서비스 키움 키 등록
```

> `internal` 프리픽스: API 서버의 내부 네트워크에서만 접근 가능.
> 외부에서 데이터 서버 포트에 직접 접근 불가 (방화벽/네트워크 정책).

---

## 6. 수집 스케줄

| 작업 | 주기 | 시간 | 비고 |
|------|------|------|------|
| 실시간 체결가 WS 수신 | 장 시간 | 09:00~15:30 | 서비스 키 |
| 일봉 저장 | 매일 1회 | 16:00 (장 마감 후) | 당일 종가 확정 후 |
| 종목 마스터 갱신 | 매일 1회 | 08:00 (장 시작 전) | 상장/폐지 반영 |
| yfinance 보조 수집 | 매일 1회 | 17:00 | 한국 외 지수, 환율 등 |
| 데이터 정합성 체크 | 매일 1회 | 18:00 | 누락 데이터 감지 + 재수집 |

---

## 7. 키움 제5조③ 준수

```
키움증권 제5조③: 시세 중계 금지
→ 서비스 키로 수집한 시세를 유저에게 직접 제공하지 않음

우리 설계:
- 서비스 키 시세 → DB 저장 → 내부 분석 (컨텍스트 계산, 백테스팅)
- 유저에게 보여주는 시세 → 유저 본인의 키움 키로 로컬에서 직접 수신
- API 서버가 컨텍스트(가공된 지표)만 제공 → 원시 시세 미제공
```

---

## 8. 수용 기준

### 8.1 시세 수집

- [ ] 서비스 키로 키움 WS 연결 → 실시간 체결가 수신
- [ ] 수신된 시세가 DB에 저장됨
- [ ] 장 마감 후 일봉 데이터 정상 저장

### 8.2 내부 API

- [ ] API 서버에서 `/internal/quotes/005930/daily` 호출 → 일봉 배열 반환
- [ ] 외부에서 직접 접근 시 → 차단 (connection refused)

### 8.3 데이터 품질

- [ ] 결측 거래일 감지 + 재수집
- [ ] 5년 일봉 데이터 보관 확인

### 8.4 서비스 키 관리

- [ ] 어드민 경유 키 등록 → 토큰 발급 → WS 연결 성공

---

## 9. 범위

### 포함

- 키움 WS 시세 수집 (서비스 키)
- DB 저장 (일봉, 분봉, 종목 마스터)
- 내부 API (시세 조회, 상태, 지표)
- yfinance 보조 수집
- 수집 스케줄러

### 미포함

- 유저에게 시세 직접 제공 (유저는 로컬에서 자체 수신)
- LLM 분석 (v3+ LLM 서버)
- 백테스팅 엔진 (v2)
- 코스콤 정식 연동 (v3+)

---

## 10. 기존 spec과의 관계

| 기존 | 상태 |
|------|------|
| `spec/data-source/` | **참고** — 데이터 소스 전략은 여전히 유효, 본 spec이 구현 |

---

## 11. 기술 요구사항

| 항목 | 선택 |
|------|------|
| Python | 3.13 |
| 프레임워크 | FastAPI |
| DB | PostgreSQL |
| ORM | SQLAlchemy + Alembic |
| 스케줄러 | APScheduler |
| WS 클라이언트 | websockets (Unit 1 재사용) |

---

## 12. 미결 사항

- [ ] Unit 1 키움 클라이언트 공유 방식 (패키지 분리 vs 복사)
- [ ] 분봉 데이터 보관 정책 (1년? 디스크 사용량 추정)
- [ ] 데이터 서버 → API 서버 통신 방식 (REST vs gRPC)
- [ ] 서비스 키 IP 화이트리스트 관리 (클라우드 IP)
- [ ] 기존 yfinance 코드(`backend/app/services/data_collector.py`) 재사용 범위

---

## 참고

- `spec/data-source/spec.md` (데이터 소스 전략)
- `docs/architecture.md` §4.3 (데이터 서버), §5.2 (키 분리)
- `docs/development-plan-v2.md` Unit 5

---

**마지막 갱신**: 2026-03-04
