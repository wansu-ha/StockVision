# 클라우드 서버 명세서 (cloud-server)

> 작성일: 2026-03-05 | 상태: **진행 중** | Unit 4 (Phase 3)
>
> **병합**: `spec/api-server/` + `spec/data-server/` → 본 spec으로 통합.
> 기존 `spec/auth/`, `spec/context-cloud/` 내용도 포함.

---

## 1. 목표

클라우드에서 운영되는 **단일 서버**를 구현한다.
인증, 전략 규칙, 시세 수집/저장, AI 분석, 어드민 기능을 하나의 프로세스로 제공.

**핵심 원칙:**
- 개인 금융정보 미보유 (체결, 잔고, 수익률 = 로컬에만)
- 매매 판단/명령 미수행 (시스템매매 도구, 투자일임 아님)
- 수집된 시세는 **내부 분석용** (유저 재배포 아님)
- LLM은 "데이터 제공" 역할만 (감성 점수, 요약 등)
- 종목 메타데이터 관리 (공공데이터포털 수집)
- 관심종목 관리

---

## 2. 요구사항

### 2.1 기능적 요구사항

| ID | 요구사항 | 모듈 | 우선순위 |
|----|---------|------|---------|
| F1 | 회원가입 (이메일 + 비밀번호 + 닉네임) | auth | P0 |
| F2 | 이메일 인증 (인증 링크) | auth | P0 |
| F3 | 로그인 → JWT (1h) + Refresh Token (7~30d) | auth | P0 |
| F4 | 토큰 갱신 (Refresh Token Rotation) | auth | P0 |
| F5 | 비밀번호 재설정 (이메일 링크, 10분 TTL) | auth | P0 |
| F6 | 전략 규칙 CRUD (생성, 조회, 수정, 삭제) | rules | P0 |
| F7 | 서비스 키움 키로 실시간 시세 수신 (WebSocket) | market_data | P0 |
| F8 | 시세 데이터를 DB에 저장 (일봉, 분봉) | market_data | P0 |
| F9 | AI 컨텍스트 조회 API (시세 기반 지표 계산) | ai_analysis | P2 (v2) |
| F10 | AI 분석 (Claude API → 감성 점수, 뉴스 요약) | ai_analysis | P2 (v2) |
| F11 | 하트비트 수신 (익명 통계) | heartbeat | P1 |
| F12 | 버전 체크 API | version | P1 |
| F13 | 어드민: 유저 목록/관리 | admin | P1 |
| F14 | 어드민: 시스템 통계 (접속, 규칙 수) | admin | P1 |
| F15 | 히스토리컬 데이터 축적 (과거 데이터 보관) | market_data | P1 |
| F16 | 서비스 키움 토큰 자동 갱신 | market_data | P1 |
| F17 | 어드민: 서비스 키움 키 관리 | admin | P2 |
| F18 | 어드민: 전략 템플릿 CRUD | admin | P2 |
| F19 | yfinance 보조 수집 (한국 외 시장) | market_data | P2 |
| F20 | 데이터 수집 상태 모니터링 | admin | P2 |
| F21 | 시세 조회 API는 어드민 전용 (일반 유저 호출 금지, §5③ 준수) | market_data | P0 |
| F22 | 종목 메타데이터 관리 (StockMaster — 공공데이터포털 수집, 일 1회 갱신) | stocks | P0 |
| F23 | 종목 검색 API (메타데이터만, 시세 미포함) | stocks | P0 |
| F24 | 관심종목 CRUD | watchlist | P0 |

### 2.2 비기능적 요구사항

| 항목 | 목표 |
|------|------|
| API P95 응답 | < 200ms |
| 동시 접속 | 1000+ (Phase 1 목표: 100) |
| 가동률 | > 99.5% |
| 비밀번호 해싱 | Argon2id (OWASP 2023) |
| 설정 암호화 | AES-256-GCM (서버사이드) |
| 외부 모델/서비스명 | config에서 로드 (하드코딩 금지) |
| 시세 수신 지연 | < 500ms (키움 WS) |
| 일봉 데이터 저장 | 장 마감 후 30분 이내 |
| 데이터 보관 기간 | 5년+ (일봉), 1년 (분봉) |
| 동시 구독 종목 | 코스피/코스닥 주요 200종목 |

---

## 3. 아키텍처

### 3.1 모듈 구조

```
cloud_server/
├── main.py                    # FastAPI 앱
├── api/
│   ├── auth.py                # 인증 (가입, 로그인, 토큰, 비밀번호)
│   ├── rules.py               # 전략 규칙 CRUD
│   ├── context.py             # AI 컨텍스트 조회
│   ├── quotes.py              # 시세 데이터 조회
│   ├── heartbeat.py           # 하트비트 수신
│   ├── version.py             # 버전 체크
│   ├── admin.py               # 어드민 API
│   ├── stocks.py              # 종목 메타데이터 검색/관리
│   └── watchlist.py           # 관심종목 CRUD
├── services/
│   ├── auth_service.py        # 인증 비즈니스 로직
│   ├── rule_service.py        # 규칙 비즈니스 로직
│   ├── context_service.py     # 컨텍스트 계산 (시세 DB → 지표)
│   ├── ai_service.py          # Claude API 호출 (감성 분석 등)
│   ├── admin_service.py       # 어드민 비즈니스 로직
│   ├── stock_service.py       # 종목 메타데이터 비즈니스 로직
│   └── watchlist_service.py   # 관심종목 비즈니스 로직
├── collector/
│   ├── kis_collector.py       # KIS WS 시세 수신 (서비스 키)
│   └── scheduler.py           # 수집 스케줄 관리
├── models/
│   ├── user.py                # User, RefreshToken, EmailVerification
│   ├── rule.py                # TradingRule (전략 규칙)
│   ├── market.py              # StockMaster, DailyBar, MinuteBar
│   ├── heartbeat.py           # Heartbeat 로그
│   └── template.py            # StrategyTemplate (어드민)
├── core/
│   ├── security.py            # JWT 발급/검증, Argon2id
│   ├── encryption.py          # AES-256-GCM (설정 blob)
│   ├── database.py            # DB 연결
│   └── config.py              # 환경 변수
└── requirements.txt
```

### 3.2 BrokerAdapter 사용

시세 수집에 `BrokerAdapter` (서비스 키)를 사용.
Unit 1의 키움 클라이언트를 `sv_core` 공유 패키지로 재사용.

```
sv_core/                       # 공유 패키지 (pip install -e)
├── broker/
│   ├── base.py                # BrokerAdapter ABC
│   ├── kis/                   # KIS(한국투자증권) 구현
│   └── kiwoom/                # 키움증권 구현
├── parsing/                   # DSL 파서 (lexer, parser, evaluator)
└── models/                    # OrderResult, QuoteEvent 등
```

---

## 4. 인증 시스템

### 4.1 엔드포인트

```
POST /api/v1/auth/register       → 가입 + 이메일 인증 발송
GET  /api/v1/auth/verify-email?token=xxx → 이메일 인증
POST /api/v1/auth/login          → JWT + Refresh Token
POST /api/v1/auth/refresh        → 토큰 갱신 (Rotation)
POST /api/v1/auth/logout         → Refresh Token 무효화
POST /api/v1/auth/forgot-password → 재설정 이메일
POST /api/v1/auth/reset-password  → 새 비밀번호
```

### 4.2 보안

| 항목 | 내용 |
|------|------|
| 비밀번호 | Argon2id (time=3, memory=64MB, parallelism=4) |
| JWT | 1시간, HS256 |
| Refresh Token | 7~30일, SHA-256 해시 저장, Rotation |
| Rate Limiting | 로그인 10회/시간/IP, 가입 5회/시간 |

---

## 5. 전략 규칙 API

### 5.1 엔드포인트

```
GET    /api/v1/rules         → 내 규칙 목록
POST   /api/v1/rules         → 규칙 생성
GET    /api/v1/rules/:id     → 규칙 상세
PUT    /api/v1/rules/:id     → 규칙 수정
DELETE /api/v1/rules/:id     → 규칙 삭제
```

### 5.2 규칙 데이터 모델

> 상세 스키마: `spec/rule-model/spec.md` §4 참조

```python
class TradingRule(Base):
    __tablename__ = "trading_rules"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    symbol = Column(String(10), nullable=False)

    # 조건 (JSON)
    buy_conditions = Column(JSON)     # { operator: "AND", conditions: [...] }
    sell_conditions = Column(JSON)    # 선택 (매도 조건)

    # 주문 설정 (JSON)
    execution = Column(JSON, nullable=False)  # { order_type, qty_type, qty_value, limit_price }

    # 트리거 정책 (JSON)
    trigger_policy = Column(JSON, nullable=False, default={"frequency": "ONCE_PER_DAY"})

    # 메타
    priority = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
```

> `max_position_count`, `budget_ratio`는 사용자 전역 설정으로 이동 (`spec/rule-model/spec.md` §7)

### 5.3 조건 JSON 스키마

```json
{
  "operator": "AND",
  "conditions": [
    {
      "type": "indicator",
      "field": "rsi_14",
      "operator": "<=",
      "value": 30
    },
    {
      "type": "context",
      "field": "market_kospi_rsi",
      "operator": ">=",
      "value": 40
    },
    {
      "type": "price",
      "field": "current_price",
      "operator": "<=",
      "value": 50000
    }
  ]
}
```

### 5.5 종목 검색 API

```
GET /api/v1/stocks/search?q=삼성  → StockMaster에서 name/symbol 매칭 (상위 20건)
GET /api/v1/stocks/:symbol        → 종목 상세 메타데이터
```

메타데이터만 반환 (시세 미포함). 제5조③ 시세 중계와 무관.

### 5.6 관심종목 API

```
GET    /api/v1/watchlist          → 내 관심종목 목록
POST   /api/v1/watchlist          → 관심종목 등록 { symbol }
DELETE /api/v1/watchlist/:symbol  → 관심종목 해제
```

### 5.7 관심종목/종목 데이터 모델

```python
class Watchlist(Base):
    __tablename__ = "watchlist"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String(10), nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("user_id", "symbol"),)
```

---

## 6. AI 컨텍스트 API (v2 범위)

### 6.1 엔드포인트

```
GET /api/v1/context                → 최신 컨텍스트 스냅샷
GET /api/v1/context/variables      → 사용 가능한 변수 목록
GET /api/v1/context/history?days=30 → 컨텍스트 변화 히스토리
```

### 6.2 동작

- 동일 프로세스 내 시세 DB에서 직접 조회 (내부 API 불필요)
- 기술적 지표 계산 (RSI, MACD, 볼린저 등)
- Claude API 호출 → 감성 점수, 뉴스 요약 (캐싱)
- 결과를 JSON으로 응답

### 6.3 Claude API 연동

```python
# ai_service.py 개략
async def get_sentiment(symbol: str) -> SentimentResult:
    # 1. 캐시 확인 (TTL 1시간)
    cached = await cache.get(f"sentiment:{symbol}")
    if cached:
        return cached

    # 2. Claude API 호출 (모델명은 config에서 로드)
    response = await anthropic_client.messages.create(
        model=settings.CLAUDE_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )

    # 3. 캐시 저장 + 반환
    result = parse_sentiment(response)
    await cache.set(f"sentiment:{symbol}", result, ttl=3600)
    return result
```

**주의**: LLM은 "데이터 제공" 역할만.
"매수하세요" 같은 직접 조언 → 투자자문업 → 금지.

> **v2 범위**: AI 분석은 v1에서 구현하지 않음. 시세 수집 + 인증 + 규칙 안정화 후 v2에서 추가.

---

## 7. 시세 수집 (Market Data)

### 7.1 수집 구조

```
[클라우드 서버] → BrokerAdapter (서비스 키)
     ├── 키움 WS → 실시간 체결가 수신
     ├── 키움 REST → 일봉/분봉 조회
     └── yfinance → 해외 지수, 환율 등
           ↓
     [PostgreSQL] (시세 데이터)
```

### 7.2 시세 데이터 모델

```python
# 종목 메타데이터: 공공데이터포털에서 일 1회 수집. 시세(가격)와 명확히 분리.
# 메타데이터는 유저에게 검색 API로 제공 (공개 정보).
# 시세 데이터(DailyBar, MinuteBar)는 서비스 키로 수집, 내부 분석용만.
class StockMaster(Base):
    __tablename__ = "stock_master"
    symbol = Column(String(10), primary_key=True)
    name = Column(String(100), nullable=False)
    market = Column(String(10))     # KOSPI | KOSDAQ
    sector = Column(String(50))
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime)

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
    change_pct = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("symbol", "date"),
        Index("idx_daily_symbol_date", "symbol", "date"),
    )

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

### 7.3 수집 스케줄

| 작업 | 주기 | 시간 | 비고 |
|------|------|------|------|
| 실시간 체결가 WS 수신 | 장 시간 | 09:00~15:30 | 서비스 키 |
| 일봉 저장 | 매일 1회 | 16:00 (장 마감 후) | 당일 종가 확정 후 |
| 종목 마스터 갱신 | 매일 1회 | 08:00 (장 시작 전) | 공공데이터포털(금융위원회_KRX상장종목정보) 수집 → StockMaster 갱신 |
| yfinance 보조 수집 | 매일 1회 | 17:00 | 한국 외 지수, 환율 등 |
| 데이터 정합성 체크 | 매일 1회 | 18:00 | 누락 데이터 감지 + 재수집 |

### 7.4 시세 조회 API (내부/어드민 전용)

```
# 시세 조회 — 어드민 + 내부 모듈 전용 (일반 유저 호출 금지)
# 제5조③ 시세 중계 금지 준수: 수집 시세는 내부 분석용만
GET /api/v1/admin/quotes/:symbol/daily?start=2025-01-01&end=2026-03-05
    → 일봉 데이터 배열

GET /api/v1/admin/quotes/:symbol/latest
    → 최신 시세

GET /api/v1/admin/quotes/market-summary
    → 코스피/코스닥 지수, 전체 시장 요약

# 기술적 지표 — 내부 모듈(ai_analysis)이 직접 DB 조회하므로 API 불필요할 수 있음
GET /api/v1/admin/quotes/:symbol/indicators
    → RSI, MACD, 볼린저 등
```

> **접근 제한**: 어드민 권한(`role=admin`) 필수. 일반 유저 토큰으로 호출 불가.
> 내부 모듈(ai_analysis, context)은 동일 프로세스이므로 DB 직접 조회.
> 유저에게 원시 시세를 제공하지 않음 (유저 시세는 로컬에서 직접 수신).

### 7.5 키움 제5조③ 준수

```
키움증권 제5조③: 시세 중계 금지
→ 서비스 키로 수집한 시세를 유저에게 직접 제공하지 않음

우리 설계:
- 서비스 키 시세 → DB 저장 → 내부 분석 (컨텍스트 계산, 백테스팅)
- 유저에게 보여주는 시세 → 유저 본인의 키움 키로 로컬에서 직접 수신
- 클라우드 서버가 컨텍스트(가공된 지표)만 제공 → 원시 시세 미제공
```

---

## 8. 하트비트/버전

### 8.1 하트비트

```
POST /api/v1/heartbeat
Body: {
  "uuid": "anon-local-uuid-abc123",
  "version": "1.0.0",
  "os": "windows",
  "kiwoom_connected": true,
  "timestamp": "2026-03-04T10:35:00+09:00"
}
```

**응답**:
```json
{
  "rules_version": 5,
  "context_version": 3,
  "watchlist_version": 2,
  "stock_master_version": "2026-03-06T08:00:00Z",
  "latest_version": "1.2.0",
  "min_version": "1.0.0",
  "timestamp": "2026-03-06T10:35:00Z"
}
```

- UUID는 로컬 설치 시 1회 생성 (개인정보 아님)
- 로컬 서버가 JWT 인증으로 직접 전송
- 로컬은 응답의 버전을 로컬 캐시 버전과 비교 → 다르면 해당 리소스 fetch

### 8.2 버전 체크

```
GET /api/v1/version
Response: {
  "latest": "1.2.0",
  "min_supported": "1.0.0",
  "download_url": "https://..."
}
```

---

## 9. 어드민 API

### 9.1 엔드포인트

```
# 유저 관리
GET    /api/v1/admin/users           → 유저 목록
PATCH  /api/v1/admin/users/:id       → 유저 상태 변경

# 통계
GET    /api/v1/admin/stats           → 시스템 통계 (유저 수, 접속 수, 규칙 수)

# 서비스 키 관리
GET    /api/v1/admin/service-keys    → 서비스 키움 키 목록
POST   /api/v1/admin/service-keys    → 키 등록
DELETE /api/v1/admin/service-keys/:id → 키 삭제

# 전략 템플릿
GET    /api/v1/admin/templates       → 템플릿 목록
POST   /api/v1/admin/templates       → 템플릿 생성
PUT    /api/v1/admin/templates/:id   → 템플릿 수정
DELETE /api/v1/admin/templates/:id   → 템플릿 삭제

# 데이터 수집 상태
GET    /api/v1/admin/collector-status → 수집 상태, 마지막 수신 시각, 에러 수
```

### 9.2 권한

- `role` 필드로 관리: `"user"` | `"admin"`
- 어드민 API는 `role == "admin"` 필수

### 9.3 볼 수 있는 것 vs 없는 것

| 볼 수 있음 | 볼 수 없음 |
|------------|-----------|
| 유저 이메일/닉네임 | 키움 API Key (유저 키) |
| 접속 상태 (하트비트) | 체결 내역, 잔고 |
| 저장된 규칙 내용 | 수익률, 거래량 |
| 시세 데이터 | — |
| AI 분석 로그 | — |

---

## 10. 로컬 서버 통신

로컬 서버가 JWT 인증으로 클라우드 서버에 직접 접속.

### 10.1 로컬 서버가 사용하는 API

```
POST /api/v1/heartbeat          하트비트 (30초~1분 주기)
                                → 응답: { rules_version, context_version }
                                → 버전 다르면 아래 fetch
GET  /api/v1/rules              규칙 fetch (버전 변경 시)
PUT  /api/v1/rules/:id          규칙 sync (로컬에서 변경 시 업로드)
GET  /api/v1/context            AI 컨텍스트 fetch (버전 변경 시)
GET  /api/v1/templates          전략 템플릿 목록 fetch
POST /api/v1/auth/refresh       JWT 자동 갱신 (Refresh Token)
GET  /api/v1/stocks/master-version  종목 메타 버전 (하트비트 응답에 포함 가능)
```

> WS 없음 — 하트비트 응답의 버전 비교로 변경 감지.
> 실시간 필요 없는 구간이므로 HTTP 폴링으로 충분.

---

## 11. 데이터 모델 (인증/규칙)

### 11.1 User

```python
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    email_verified = Column(Boolean, default=False)
    password_hash = Column(String(255), nullable=False)
    nickname = Column(String(50))
    role = Column(String(20), default="user")  # user | admin
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime)
```

### 11.2 Heartbeat

```python
class Heartbeat(Base):
    __tablename__ = "heartbeats"
    id = Column(Integer, primary_key=True)
    uuid = Column(String(50), nullable=False, index=True)
    version = Column(String(20))
    os = Column(String(20))
    kiwoom_connected = Column(Boolean)
    timestamp = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### 11.3 StrategyTemplate

```python
class StrategyTemplate(Base):
    __tablename__ = "strategy_templates"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    buy_conditions = Column(JSON)
    sell_conditions = Column(JSON)
    default_params = Column(JSON)   # qty, budget_ratio 등
    category = Column(String(50))   # "기술적 지표", "모멘텀" 등
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
```

---

## 12. 수용 기준

### 12.1 인증

- [ ] 회원가입 → 인증 이메일 수신 → 이메일 인증 완료
- [ ] 로그인 → JWT + Refresh Token 발급
- [ ] Refresh Token으로 JWT 자동 갱신
- [ ] 비밀번호 재설정 완료

### 12.2 규칙

- [ ] 규칙 생성 → DB 저장 → 조회 확인
- [ ] 규칙 수정/삭제 정상 동작
- [ ] 조건 JSON 검증 (잘못된 형식 → 400 에러)

### 12.3 시세 수집

- [ ] 서비스 키로 키움 WS 연결 → 실시간 체결가 수신
- [ ] 수신된 시세가 DB에 저장됨
- [ ] 장 마감 후 일봉 데이터 정상 저장
- [ ] 결측 거래일 감지 + 재수집

### 12.4 AI 컨텍스트

- [ ] `GET /api/v1/context` → 시장 지표 JSON 응답
- [ ] Claude API 호출 → 감성 점수 반환
- [ ] 캐싱 동작 확인 (동일 요청 재호출 방지)

### 12.5 어드민

- [ ] admin 유저로 유저 목록 조회
- [ ] 일반 유저로 어드민 API 접근 → 403
- [ ] 서비스 키 등록 → 토큰 발급 → 시세 수신 성공

### 12.6 로컬 서버 통신

- [ ] 로컬 서버가 JWT로 하트비트 전송 → 응답에 rules_version, context_version 포함
- [ ] rules_version 변경 시 규칙 fetch 성공
- [ ] 로컬 서버가 규칙 sync (업로드) → DB 반영 + version 증가
- [ ] Refresh Token 갱신 정상 동작

### 12.7 종목/관심종목

- [ ] 종목 검색 → 이름/코드 매칭 결과 반환
- [ ] 관심종목 등록/해제 정상 동작
- [ ] 공공데이터포털 수집 → StockMaster 갱신 확인

---

## 13. 범위

### 포함

- 인증 시스템 전체 (가입~비밀번호 재설정)
- 전략 규칙 CRUD
- 시세 수집/저장 (서비스 키, 일봉, 분봉, 종목 마스터)
- AI 컨텍스트 조회 + Claude API 연동
- 하트비트 수신, 버전 체크
- 어드민 API (유저, 통계, 키, 템플릿, 수집 상태)
- 하트비트 응답에 버전 정보 포함 (규칙/컨텍스트 변경 감지)
- yfinance 보조 수집
- 수집 스케줄러

### 미포함

- 프론트엔드 (별도 spec)
- 로컬 서버 (별도 spec)
- 커뮤니티 전략 공유 (v2)
- 백테스팅 엔진 (v2)
- 코스콤 정식 연동 (v3+)

---

## 14. 기존 spec과의 관계

| 기존 | 상태 |
|------|------|
| `spec/api-server/` | **SUPERSEDED** — 본 spec에 병합 |
| `spec/data-server/` | **SUPERSEDED** — 본 spec에 병합 |
| `spec/auth/` | **병합** — 인증 부분 본 spec §4에 통합 |
| `spec/context-cloud/` | **병합** — 컨텍스트 API 부분 본 spec §6에 통합 |
| `spec/data-source/` | **참고** — 데이터 소스 전략은 여전히 유효 |

---

## 15. 기술 요구사항

| 항목 | 선택 |
|------|------|
| Python | 3.13 |
| 프레임워크 | FastAPI |
| DB | PostgreSQL (운영), SQLite (개발) |
| ORM | SQLAlchemy + Alembic |
| 비밀번호 | argon2-cffi |
| JWT | python-jose |
| 암호화 | cryptography (AES-256-GCM) |
| 이메일 | SMTP (Gmail / SendGrid) |
| 스케줄러 | APScheduler |
| WS 클라이언트 | websockets (BrokerAdapter 경유) |
| AI | anthropic (Claude API SDK) |
| 공유 패키지 | sv_core (BrokerAdapter + 공통 모델) |

---

## 16. 미결 사항

- [ ] 커뮤니티 전략 공유 API 설계 (v2 시점)
- [ ] 규칙 조건 JSON 검증 스키마 확정
- [ ] 어드민 페이지 RBAC 세분화 필요 여부
- [ ] Rate Limiting 구체 구현 (Redis vs in-memory)
- [ ] 분봉 데이터 보관 정책 (1년? 디스크 사용량 추정)
- [ ] 서비스 키 IP 화이트리스트 관리 (클라우드 IP)
- [ ] 기존 yfinance 코드(`backend/app/services/data_collector.py`) 재사용 범위
- [ ] Claude API 호출 비용 최적화 (캐시 TTL, 호출 빈도)

---

## 참고

- `spec/kiwoom-rest/spec.md` (키움 REST API 연동)
- `spec/data-source/spec.md` (데이터 소스 전략)
- `docs/architecture.md` §4.2, §4.3, §4.5, §8
- `docs/development-plan-v2.md` Unit 4

---

**마지막 갱신**: 2026-03-09
