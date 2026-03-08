# 클라우드 서버 구현 계획서 (cloud-server)

> 작성일: 2026-03-05 | 상태: **진행 중** | 범위: Phase 3 Unit 4

---

## 0. 현황

### 기존 백엔드 (`backend/app/`) 상태

**Phase 1-2에서 구축된 기존 코드:**

| 항목 | 상태 | 파일 |
|------|------|------|
| FastAPI 앱 | 운영 중 | `backend/app/main.py` |
| 인증 (JWT) | 구현됨 | `backend/app/api/auth.py`, `backend/app/core/jwt_utils.py` |
| 주식 데이터 | yfinance 기반 | `backend/app/services/data_ingestion.py` |
| 기술적 지표 | 계산 구현 | `backend/app/services/technical_indicators.py` |
| 가상 거래 | 시뮬레이션 | `backend/app/api/trading.py`, `backend/app/models/auto_trading.py` |
| SQLAlchemy 모델 | 기본 구현 | `backend/app/models/` (User, Stock, Bar 등) |
| 이메일 | SMTP 연동 | `backend/app/core/email.py` |
| 암호화 | AES-256 | `backend/app/core/encryption.py` |
| 비밀번호 | Argon2id | `backend/app/core/password.py` |
| 데이터베이스 | SQLite(개발) | `backend/app/core/database.py` |
| 로깅 | 구현됨 | `backend/app/core/api_logging.py` |

**미포함 항목:**
- Refresh Token Rotation
- 규칙 CRUD (TradingRule 모델)
- 서비스 키움 WS 시세 수집기
- APScheduler 기반 수집 스케줄러
- 어드민 API (권한 기반)
- AI 컨텍스트 API (Claude 연동)
- 하트비트 수신 API
- 버전 체크 API

### 아키텍처 변경사항

**이전 (Phase 1-2):**
- 단일 FastAPI 서버 (`backend/app/`)
- 모의 거래 중심 (리스크 없는 검증)
- yfinance만 사용

**변화 (Phase 3):**
- **명칭 변경**: `backend/app/` → `cloud_server/` (모듈 구조 정리)
- **통합**: api-server + data-server 병합 (단일 프로세스)
- **신규**: 로컬 서버 통신 API (하트비트, 규칙 sync, 컨텍스트)
- **신규**: 시예 수집기 (서비스 키움 WS + REST)
- **신규**: APScheduler 스케줄러 (장시간 동작)
- **신규**: 어드민 대시보드

---

## 1. 구현 단계

### Step 1 — 프로젝트 구조 + FastAPI 앱 + DB 설정

**목표**: `cloud_server/` 디렉토리 구조 정립 및 개발 환경 구성

**파일:**
- `cloud_server/` (신규 디렉토리, `backend/app/` 이전)
- `cloud_server/main.py` (기존 `backend/app/main.py` 기반)
- `cloud_server/core/database.py` (PostgreSQL 멀티 환경 지원)
- `cloud_server/requirements.txt` (신규 의존성 추가)

**구현 내용:**
```
1. cloud_server/ 디렉토리 구조 생성
   - api/, services/, collector/, models/, core/ 서브디렉토리

2. FastAPI 앱 설정 (main.py)
   - CORS 설정 (localhost:5173, 클라이언트 호스트)
   - 미들웨어 등록 (로깅, 성능 모니터링)
   - health check 엔드포인트

3. 데이터베이스 설정 (core/database.py)
   - SQLAlchemy SessionLocal
   - PostgreSQL (운영) / SQLite (개발) 전환 설정
   - Alembic 마이그레이션 준비

4. 환경 설정 (core/config.py)
   - DATABASE_URL, SECRET_KEY, ANTHROPIC_API_KEY 등
   - 로깅 레벨, 캐시 TTL 설정

5. requirements.txt
   - 신규: argon2-cffi, anthropic, APScheduler
   - 유지: fastapi, sqlalchemy, pydantic 등
```

**검증:**
- [ ] `python -m uvicorn cloud_server.main:app --reload` 실행 → 8000 포트 응답
- [ ] `GET /health` → 200 OK
- [ ] DB 초기화 완료 (Alembic 마이그레이션 수행 또는 init_db)

---

### Step 2 — 인증 시스템 (User, JWT, Refresh Token, 비밀번호)

**목표**: 완전한 인증 플로우 구현 (가입 → 이메일 인증 → 로그인 → Refresh Token Rotation)

**파일:**
- `cloud_server/models/user.py` (User, RefreshToken, EmailVerification 모델)
- `cloud_server/api/auth.py` (인증 엔드포인트)
- `cloud_server/services/auth_service.py` (인증 비즈니스 로직)
- `cloud_server/core/security.py` (JWT, Argon2id, 암호화)

**구현 내용:**
```python
# 1. User 모델 확장
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    email_verified = Column(Boolean, default=False)
    password_hash = Column(String(255), nullable=False)
    nickname = Column(String(50))
    role = Column(String(20), default="user")  # user | admin
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime)

# 2. RefreshToken, EmailVerification, PasswordReset 모델
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String(255), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    rotated_at = Column(DateTime)  # Rotation 추적

class EmailVerification(Base):
    __tablename__ = "email_verifications"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(255), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    verified_at = Column(DateTime)

class PasswordReset(Base):
    __tablename__ = "password_resets"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(255), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime)

# 3. 인증 엔드포인트
POST /api/v1/auth/register       → 회원가입 + 이메일 인증 발송
GET  /api/v1/auth/verify-email?token=xxx → 이메일 인증 완료
POST /api/v1/auth/login          → JWT + Refresh Token 발급
POST /api/v1/auth/refresh        → JWT 갱신 (Token Rotation)
POST /api/v1/auth/logout         → Refresh Token 무효화
POST /api/v1/auth/forgot-password → 재설정 이메일 발송
POST /api/v1/auth/reset-password  → 새 비밀번호 설정

# 4. 보안 함수 (core/security.py)
def hash_password(password: str) -> str:
    # Argon2id (time=3, memory=64MB, parallelism=4)
    return PasswordHasher().hash(password)

def verify_password(password: str, hash: str) -> bool:
    try:
        PasswordHasher().verify(hash, password)
        return True
    except VerifyMismatchError:
        return False

def create_jwt(user_id: int, expires_in: int = 3600) -> str:
    # HS256, 1시간 만료
    payload = {"sub": str(user_id), "exp": datetime.utcnow() + timedelta(seconds=expires_in)}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

def create_refresh_token(user_id: int, expires_in_days: int = 7) -> str:
    # 7일 만료, DB에 해시 저장
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    # DB에 token_hash 저장
    return token

# 5. 이메일 인증 토큰 생성
def create_verification_token(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    # DB에 저장, 10분 TTL
    return token

# 6. Rate Limiting
- 로그인: 10회/시간/IP
- 가입: 5회/시간/IP
- 비밀번호 재설정: 3회/시간/IP
```

**검증:**
- [ ] `POST /api/v1/auth/register` → 이메일 인증 링크 수신
- [ ] `GET /api/v1/auth/verify-email?token=xxx` → 이메일 인증 완료
- [ ] `POST /api/v1/auth/login` → JWT + Refresh Token 반환
- [ ] `POST /api/v1/auth/refresh` → 새 JWT 발급 + Refresh Token Rotation
- [ ] JWT 1시간 만료 후 refresh로 갱신 가능
- [ ] 잘못된 비밀번호 → 400 Unauthorized
- [ ] Rate Limiting 동작 확인

---

### Step 3 — 전략 규칙 CRUD (TradingRule 모델, API, JSON 검증)

**목표**: 사용자 정의 규칙 저장/조회/수정/삭제 및 조건 JSON 검증

**파일:**
- `cloud_server/models/rule.py` (TradingRule 모델)
- `cloud_server/api/rules.py` (규칙 CRUD 엔드포인트)
- `cloud_server/services/rule_service.py` (비즈니스 로직)
- `cloud_server/core/validators.py` (조건 JSON 검증)

**구현 내용:**

> 상세 스키마: `spec/rule-model/spec.md` §4 참조

```python
# 1. TradingRule 모델
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
    version = Column(Integer, default=1)  # 클라이언트 동기화용
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "name"),
        Index("idx_user_rules", "user_id"),
    )

# NOTE: max_position_count, budget_ratio는 사용자 전역 설정으로 이동 (spec/rule-model/spec.md §7)

# 2. 조건 JSON 스키마 검증
def validate_conditions(conditions: dict) -> bool:
    """
    {
      "operator": "AND" | "OR",
      "conditions": [
        {
          "type": "indicator" | "context" | "price",
          "field": "rsi_14" | "market_kospi_rsi" | "current_price",
          "operator": "<=" | ">=" | "==" | "!=" | "<" | ">",
          "value": number
        }
      ]
    }
    """
    valid_operators = ["AND", "OR"]
    valid_types = ["indicator", "context", "price", "volume"]
    valid_field_operators = ["<", ">", "<=", ">=", "==", "!=", "cross_above", "cross_below"]

    if conditions.get("operator") not in valid_operators:
        raise ValueError(f"Invalid operator: {conditions.get('operator')}")

    for cond in conditions.get("conditions", []):
        if cond.get("type") not in valid_types:
            raise ValueError(f"Invalid type: {cond.get('type')}")
        if cond.get("operator") not in valid_field_operators:
            raise ValueError(f"Invalid field operator: {cond.get('operator')}")
        if not isinstance(cond.get("value"), (int, float)):
            raise ValueError(f"Invalid value: {cond.get('value')}")

    return True

# 3. 규칙 CRUD 엔드포인트
GET    /api/v1/rules         → 내 규칙 목록
POST   /api/v1/rules         → 규칙 생성 (version=1)
GET    /api/v1/rules/:id     → 규칙 상세
PUT    /api/v1/rules/:id     → 규칙 수정 (version++)
DELETE /api/v1/rules/:id     → 규칙 삭제

# 4. 응답 형식
{
  "success": true,
  "data": {
    "id": 1,
    "user_id": 10,
    "name": "RSI 역매매",
    "symbol": "005930",
    "buy_conditions": { "operator": "AND", "conditions": [...] },
    "sell_conditions": { "operator": "AND", "conditions": [...] },
    "execution": { "order_type": "market", "qty_type": "FIXED", "qty_value": 10 },
    "trigger_policy": { "frequency": "ONCE_PER_DAY" },
    "priority": 0,
    "is_active": true,
    "version": 2,
    "created_at": "2026-03-01T10:00:00",
    "updated_at": "2026-03-05T15:30:00"
  }
}
```

**검증:**
- [ ] `POST /api/v1/rules` → 조건 JSON이 유효 → 200 OK
- [ ] `POST /api/v1/rules` → 조건 JSON이 무효 → 400 Bad Request
- [ ] `GET /api/v1/rules` → 사용자 본인 규칙만 조회
- [ ] `PUT /api/v1/rules/:id` → version 증가 확인
- [ ] `DELETE /api/v1/rules/:id` → 물리 삭제 또는 soft delete
- [ ] 다른 사용자의 규칙 접근 → 403 Forbidden

---

### Step 4 — 하트비트 수신 + 버전 체크 API

**목표**: 로컬 서버의 주기적 상태 보고 및 버전 관리

**파일:**
- `cloud_server/models/heartbeat.py` (Heartbeat 모델)
- `cloud_server/api/heartbeat.py` (하트비트 엔드포인트)
- `cloud_server/api/version.py` (버전 체크 엔드포인트)
- `cloud_server/services/heartbeat_service.py` (비즈니스 로직)

**구현 내용:**
```python
# 1. Heartbeat 모델
class Heartbeat(Base):
    __tablename__ = "heartbeats"
    id = Column(Integer, primary_key=True)
    uuid = Column(String(50), nullable=False, index=True)  # 로컬 설치 고유 ID
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    version = Column(String(20))      # 로컬 서버 버전
    os = Column(String(20))           # windows | mac | linux
    kiwoom_connected = Column(Boolean)
    engine_running = Column(Boolean)
    active_rules_count = Column(Integer)  # 활성 규칙 수
    timestamp = Column(DateTime, nullable=False)  # 로컬 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_heartbeat_uuid_user", "uuid", "user_id"),
    )

# 2. 하트비트 엔드포인트 (로컬 서버 JWT 인증)
POST /api/v1/heartbeat
Body: {
  "uuid": "local-uuid-abc123",
  "version": "1.0.0",
  "os": "windows",
  "kiwoom_connected": true,
  "engine_running": true,
  "active_rules_count": 3,
  "timestamp": "2026-03-05T10:35:00+09:00"
}

Response: {
  "success": true,
  "data": {
    "rules_version": 5,            # 현재 규칙 버전 (로컬이 캐시한 버전과 비교)
    "context_version": 3,          # 현재 컨텍스트 버전
    "stock_master_version": "2026-03-05T08:00:00Z",  # 종목 마스터 최종 갱신 시각
    "watchlist_version": 2,        # 관심종목 변경 버전
    "timestamp": "2026-03-05T10:35:00Z"
  }
}

# 3. 버전 체크 엔드포인트 (공개, 인증 불필요)
GET /api/v1/version
Response: {
  "success": true,
  "data": {
    "latest": "1.0.0",
    "min_supported": "0.9.0",
    "download_url": "https://github.com/stockvision/releases/latest",
    "changelog": "..."
  }
}

# 4. 비즈니스 로직
def post_heartbeat(user_id: int, payload: dict) -> dict:
    """
    1. Heartbeat 레코드 생성/업데이트
    2. 현재 rules_version, context_version 계산
    3. 응답에 포함하여 반환
    """
    hb = Heartbeat(
        user_id=user_id,
        uuid=payload["uuid"],
        version=payload["version"],
        os=payload["os"],
        kiwoom_connected=payload["kiwoom_connected"],
        engine_running=payload.get("engine_running"),
        active_rules_count=payload.get("active_rules_count"),
        timestamp=payload["timestamp"]
    )
    db.add(hb)
    db.commit()

    # 규칙/컨텍스트 버전 계산
    rules_version = db.query(func.max(TradingRule.version)).filter(
        TradingRule.user_id == user_id
    ).scalar() or 0

    context_version = ... # 컨텍스트 마지막 갱신 시간 기반

    # 종목 마스터 최종 갱신 시각
    stock_master_version = db.query(func.max(StockMaster.updated_at)).scalar()

    # 관심종목 변경 버전 (최신 created_at 기반)
    watchlist_version = db.query(func.count(Watchlist.id)).filter(
        Watchlist.user_id == user_id
    ).scalar() or 0

    return {
        "rules_version": rules_version,
        "context_version": context_version,
        "stock_master_version": stock_master_version,
        "watchlist_version": watchlist_version,
        "timestamp": datetime.utcnow()
    }
```

**검증:**
- [ ] `POST /api/v1/heartbeat` (JWT 인증) → 200 OK, rules_version/context_version/stock_master_version/watchlist_version 반환
- [ ] rules_version 변경 시 → 응답값 변화 확인
- [ ] stock_master_version, watchlist_version 정상 반환 확인
- [ ] `GET /api/v1/version` → 200 OK, latest/min_supported 반환
- [ ] 하트비트 로그 DB 저장 확인

---

### Step 5 — 시세 수집 — 서비스 키움 BrokerAdapter (sv_core 사용)

**목표**: 서비스 키로 실시간 시세 수신 (키움 WS, REST)

**파일:**
- `cloud_server/collector/kis_collector.py` (키움 WS 수신기)
- `cloud_server/core/broker_factory.py` (BrokerAdapter 팩토리)
- `cloud_server/models/kiwoom_service_key.py` (서비스 키 설정)

**구현 내용:**
```python
# 1. sv_core.BrokerAdapter 사용
from sv_core.broker.base import BrokerAdapter
from sv_core.broker.kiwoom import KiwoomAdapter

# 2. 서비스 키 설정 모델
class KiwoomServiceKey(Base):
    __tablename__ = "kiwoom_service_keys"
    id = Column(Integer, primary_key=True)
    api_key = Column(String(255), nullable=False)
    api_secret = Column(String(255), nullable=False)  # 암호화
    is_active = Column(Boolean, default=True)
    app_name = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime)

# 3. BrokerAdapter 팩토리
class BrokerFactory:
    @staticmethod
    def create(broker_type: str = "kiwoom", service_key: dict = None) -> BrokerAdapter:
        if broker_type == "kiwoom":
            return KiwoomAdapter(
                api_key=service_key["api_key"],
                api_secret=service_key["api_secret"],
                use_sandbox=False  # 운영
            )
        raise ValueError(f"Unknown broker: {broker_type}")

# 4. 키움 시세 수집기
class KISCollector:
    def __init__(self, broker: BrokerAdapter):
        self.broker = broker
        self.subscribed_symbols = set()

    async def subscribe(self, symbols: list[str], data_type: str = "quote"):
        """시세 구독"""
        await self.broker.subscribe(symbols, data_type)
        self.subscribed_symbols.update(symbols)

    async def listen(self):
        """비동기 이벤트 스트림 수신"""
        async for event in self.broker.listen():
            # event = QuoteEvent(symbol, price, volume, timestamp, ...)
            # DB에 저장 (Step 6 참조)
            yield event

# 5. 시작: BrokerAdapter 인증 후 구독
async def start_kis_collector():
    service_key = db.query(KiwoomServiceKey).filter_by(is_active=True).first()
    broker = BrokerFactory.create("kiwoom", {
        "api_key": service_key.api_key,
        "api_secret": decrypt(service_key.api_secret)
    })

    await broker.authenticate()

    collector = KISCollector(broker)

    # 코스피/코스닥 주요 200종목 구독
    symbols = get_major_symbols()
    await collector.subscribe(symbols)

    async for event in collector.listen():
        # 분봉 저장 + 캐시 업데이트
        await save_minute_bar(event)
```

**검증:**
- [ ] KiwoomAdapter 인증 성공
- [ ] 시세 구독 성공 (실시간 데이터 수신)
- [ ] QuoteEvent 파싱 및 캐시 업데이트

---

### Step 6 — 시세 저장 (DailyBar, MinuteBar, StockMaster 모델 + Repository)

**목표**: 실시간 시세를 DB에 효율적으로 저장

**파일:**
- `cloud_server/models/market.py` (StockMaster, DailyBar, MinuteBar 모델)
- `cloud_server/services/market_repository.py` (DB 접근 레이어)

**구현 내용:**
```python
# 1. 시장 데이터 모델
class StockMaster(Base):
    __tablename__ = "stock_master"
    symbol = Column(String(10), primary_key=True)
    name = Column(String(100), nullable=False)
    market = Column(String(10))     # KOSPI | KOSDAQ | OVERSEAS
    sector = Column(String(50))
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_market", "market"),
    )

class DailyBar(Base):
    __tablename__ = "daily_bars"
    id = Column(Integer, primary_key=True)
    symbol = Column(String(10), ForeignKey("stock_master.symbol"), nullable=False)
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
    symbol = Column(String(10), ForeignKey("stock_master.symbol"), nullable=False)
    timestamp = Column(DateTime, nullable=False)  # KST
    open = Column(Integer)
    high = Column(Integer)
    low = Column(Integer)
    close = Column(Integer)
    volume = Column(BigInteger)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("symbol", "timestamp"),
        Index("idx_minute_symbol_ts", "symbol", "timestamp"),
    )

# 2. MarketRepository
class MarketRepository:
    def __init__(self, db: Session):
        self.db = db

    async def save_minute_bar(self, symbol: str, event: QuoteEvent) -> MinuteBar:
        """분봉 저장 (1분 단위)"""
        # timestamp를 1분 단위로 그룹핑
        minute_timestamp = event.timestamp.replace(second=0, microsecond=0)

        bar = MinuteBar(
            symbol=symbol,
            timestamp=minute_timestamp,
            open=event.price,
            high=event.price,
            low=event.price,
            close=event.price,
            volume=event.volume
        )

        # 기존 바가 있으면 high/low 업데이트
        existing = self.db.query(MinuteBar).filter_by(
            symbol=symbol, timestamp=minute_timestamp
        ).first()

        if existing:
            existing.high = max(existing.high, event.price)
            existing.low = min(existing.low, event.price)
            existing.close = event.price
            existing.volume += event.volume
            self.db.commit()
            return existing

        self.db.add(bar)
        self.db.commit()
        return bar

    async def save_daily_bar(self, symbol: str, date: date, ohlcv: dict) -> DailyBar:
        """일봉 저장 (장 마감 후)"""
        bar = DailyBar(
            symbol=symbol,
            date=date,
            open=ohlcv["open"],
            high=ohlcv["high"],
            low=ohlcv["low"],
            close=ohlcv["close"],
            volume=ohlcv["volume"],
            change_pct=ohlcv.get("change_pct")
        )

        self.db.merge(bar)  # upsert
        self.db.commit()
        return bar

    async def get_latest_price(self, symbol: str) -> int:
        """최신 시세 조회"""
        bar = self.db.query(MinuteBar).filter_by(symbol=symbol).order_by(
            MinuteBar.timestamp.desc()
        ).first()
        return bar.close if bar else None

    async def get_daily_bars(self, symbol: str, start_date: date, end_date: date) -> list[DailyBar]:
        """일봉 범위 조회"""
        return self.db.query(DailyBar).filter(
            DailyBar.symbol == symbol,
            DailyBar.date >= start_date,
            DailyBar.date <= end_date
        ).order_by(DailyBar.date).all()
```

**검증:**
- [ ] 실시간 시세 수신 → MinuteBar 저장 확인
- [ ] 1분 단위 OHLC 캡슐화 확인
- [ ] 일봉 저장 (장 마감 후) 확인
- [ ] DB 인덱스로 빠른 조회 확인

---

### Step 6-A — 종목 검색 API (StockMaster 검색 + 종목 상세)

**목표**: 사용자가 종목명/코드로 종목을 검색하고 메타데이터를 조회

**파일:**
- `cloud_server/api/stocks.py` (신규)
- `cloud_server/models/market.py` (기존 StockMaster 활용)
- `cloud_server/services/stock_service.py` (신규)

**구현 내용:**
```python
# 1. 종목 검색 엔드포인트
GET /api/v1/stocks/search?q=삼성    → StockMaster에서 name/symbol LIKE 매칭 (상위 20건)
GET /api/v1/stocks/:symbol          → 종목 상세 메타데이터 (시세 미포함)
GET /api/v1/stocks/master-version   → 마스터 버전 (로컬 캐시 동기화용)

# 2. StockService
class StockService:
    def search(self, db: Session, query: str, limit: int = 20) -> list[dict]:
        """종목명/코드 검색"""
        results = db.query(StockMaster).filter(
            or_(
                StockMaster.name.ilike(f"%{query}%"),
                StockMaster.symbol.ilike(f"%{query}%")
            ),
            StockMaster.is_active == True
        ).limit(limit).all()

        return [
            {"symbol": r.symbol, "name": r.name, "market": r.market, "sector": r.sector}
            for r in results
        ]

    def get_detail(self, db: Session, symbol: str) -> dict:
        """종목 상세 메타데이터"""
        master = db.query(StockMaster).filter_by(symbol=symbol).first()
        if not master:
            raise HTTPException(status_code=404, detail="Symbol not found")
        return {
            "symbol": master.symbol,
            "name": master.name,
            "market": master.market,
            "sector": master.sector,
            "is_active": master.is_active,
            "updated_at": master.updated_at
        }

    def get_master_version(self, db: Session) -> dict:
        """마스터 테이블 최신 갱신 시각"""
        latest = db.query(func.max(StockMaster.updated_at)).scalar()
        return {"version": latest.isoformat() if latest else None}

# 3. 응답 형식
{
  "success": true,
  "data": [
    {"symbol": "005930", "name": "삼성전자", "market": "KOSPI", "sector": "반도체"},
    {"symbol": "005935", "name": "삼성전자우", "market": "KOSPI", "sector": "반도체"}
  ],
  "count": 2
}
```

**검증:**
- [ ] `GET /api/v1/stocks/search?q=삼성` → 삼성 포함 종목 목록 반환
- [ ] `GET /api/v1/stocks/005930` → 삼성전자 메타데이터 반환 (시세 없음)
- [ ] `GET /api/v1/stocks/master-version` → 최신 갱신 시각 반환
- [ ] 존재하지 않는 종목 → 404

---

### Step 6-B — 관심종목 CRUD

**목표**: 사용자별 관심종목 등록/조회/삭제

**파일:**
- `cloud_server/api/watchlist.py` (신규)
- `cloud_server/models/watchlist.py` (신규)
- `cloud_server/services/watchlist_service.py` (신규)

**구현 내용:**
```python
# 1. Watchlist 모델
class Watchlist(Base):
    __tablename__ = "watchlist"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String(10), nullable=False)
    memo = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "symbol"),
        Index("idx_watchlist_user", "user_id"),
    )

# 2. 관심종목 엔드포인트 (JWT 인증)
GET    /api/v1/watchlist          → 내 관심종목 목록
POST   /api/v1/watchlist          → 관심종목 추가
DELETE /api/v1/watchlist/:id      → 관심종목 삭제

# 3. WatchlistService
class WatchlistService:
    def list(self, db: Session, user_id: int) -> list[dict]:
        """관심종목 목록 (StockMaster JOIN)"""
        items = db.query(Watchlist, StockMaster).join(
            StockMaster, Watchlist.symbol == StockMaster.symbol
        ).filter(
            Watchlist.user_id == user_id
        ).order_by(Watchlist.created_at.desc()).all()

        return [
            {
                "id": w.id,
                "symbol": w.symbol,
                "name": m.name,
                "market": m.market,
                "memo": w.memo,
                "created_at": w.created_at
            }
            for w, m in items
        ]

    def add(self, db: Session, user_id: int, symbol: str, memo: str = None) -> dict:
        """관심종목 추가"""
        # StockMaster에 존재하는 종목인지 확인
        master = db.query(StockMaster).filter_by(symbol=symbol, is_active=True).first()
        if not master:
            raise HTTPException(status_code=404, detail="Symbol not found")

        item = Watchlist(user_id=user_id, symbol=symbol, memo=memo)
        db.add(item)
        db.commit()
        return {"id": item.id, "symbol": item.symbol, "name": master.name}

    def remove(self, db: Session, user_id: int, item_id: int):
        """관심종목 삭제"""
        item = db.query(Watchlist).filter_by(id=item_id, user_id=user_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Watchlist item not found")
        db.delete(item)
        db.commit()

# 4. 응답 형식
{
  "success": true,
  "data": [
    {"id": 1, "symbol": "005930", "name": "삼성전자", "market": "KOSPI", "memo": null, "created_at": "..."},
    {"id": 2, "symbol": "000660", "name": "SK하이닉스", "market": "KOSPI", "memo": "반도체", "created_at": "..."}
  ],
  "count": 2
}
```

**검증:**
- [ ] `GET /api/v1/watchlist` → 본인 관심종목만 조회
- [ ] `POST /api/v1/watchlist` → 관심종목 추가 (StockMaster에 없는 종목 → 404)
- [ ] `POST /api/v1/watchlist` → 중복 추가 → 409 Conflict
- [ ] `DELETE /api/v1/watchlist/:id` → 삭제 확인
- [ ] 다른 사용자의 관심종목 삭제 → 404

---

### Step 7 — 수집 스케줄러 (APScheduler: WS, 일봉, 종목마스터, yfinance)

**목표**: 정기적인 데이터 수집 자동화

**파일:**
- `cloud_server/collector/scheduler.py` (APScheduler 스케줄 관리)
- `cloud_server/services/yfinance_service.py` (yfinance 보조 수집)

**구현 내용:**
```python
# 1. 스케줄러 설정
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

class CollectorScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.kis_collector = None
        self.broker = None

    def start(self):
        """스케줄러 시작"""
        # 실시간 WS (장시간)
        self.scheduler.add_job(
            self.start_kiwoom_ws,
            trigger=CronTrigger(hour=9, minute=0),  # 09:00
            id="kiwoom_ws_start"
        )

        # 일봉 저장 (장 마감 후)
        self.scheduler.add_job(
            self.save_daily_bars,
            trigger=CronTrigger(hour=16, minute=0),  # 16:00
            id="daily_bars"
        )

        # 종목 마스터 갱신 (매일 08:00)
        self.scheduler.add_job(
            self.update_stock_master,
            trigger=CronTrigger(hour=8, minute=0),
            id="stock_master"
        )

        # yfinance 보조 수집 (매일 17:00)
        self.scheduler.add_job(
            self.collect_yfinance,
            trigger=CronTrigger(hour=17, minute=0),
            id="yfinance"
        )

        # 데이터 정합성 체크 (매일 18:00)
        self.scheduler.add_job(
            self.check_data_integrity,
            trigger=CronTrigger(hour=18, minute=0),
            id="integrity_check"
        )

        self.scheduler.start()

    async def start_kiwoom_ws(self):
        """키움 WS 시작"""
        self.broker = BrokerFactory.create("kiwoom", service_key=...)
        await self.broker.authenticate()

        self.kis_collector = KISCollector(self.broker)
        symbols = get_major_symbols()
        await self.kis_collector.subscribe(symbols)

        # 비동기 리스닝 시작 (배경 태스크)
        asyncio.create_task(self.listen_quotes())

    async def listen_quotes(self):
        """실시간 시세 수신 및 저장"""
        repo = MarketRepository(get_db())
        async for event in self.kis_collector.listen():
            await repo.save_minute_bar(event.symbol, event)

    async def save_daily_bars(self):
        """일봉 저장 (키움 REST API 호출)"""
        repo = MarketRepository(get_db())

        for symbol in get_major_symbols():
            daily_data = await self.broker.get_daily_bars(symbol, days=1)
            if daily_data:
                ohlcv = daily_data[0]  # 어제 데이터
                await repo.save_daily_bar(symbol, ohlcv["date"], ohlcv)

    async def update_stock_master(self):
        """종목 마스터 갱신 (공공데이터포털 — 금융위원회_KRX상장종목정보)"""
        import httpx

        repo = MarketRepository(get_db())

        # 공공데이터포털 API 호출 (키움 API 대신)
        url = "https://apis.data.go.kr/1160100/service/GetKrxListedInfoService/getItemInfo"
        params = {
            "serviceKey": settings.PUBLIC_DATA_API_KEY,
            "resultType": "json",
            "numOfRows": 3000,
            "pageNo": 1,
        }

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, params=params)
            data = resp.json()

        items = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])

        for item in items:
            master = StockMaster(
                symbol=item["srtnCd"],       # 단축코드
                name=item["itmsNm"],         # 종목명
                market=item["mrktCtg"],      # KOSPI | KOSDAQ
                sector=item.get("idxIndNm"), # 업종
                is_active=True,
            )
            repo.db.merge(master)

        repo.db.commit()
        logging.info(f"Stock master updated: {len(items)} items")

    async def collect_yfinance(self):
        """yfinance 보조 수집 (해외 지수, 환율 등)"""
        yf_service = YFinanceService()

        # 코스피/코스닥 지수
        data = await yf_service.fetch(["^KS11", "^KQ11"])

        # DB에 저장
        repo = MarketRepository(get_db())
        for symbol, ohlcv in data.items():
            await repo.save_daily_bar(symbol, ohlcv["date"], ohlcv)

    async def check_data_integrity(self):
        """결측 데이터 감지 및 재수집"""
        repo = MarketRepository(get_db())

        # 어제 거래일이 있는지 확인
        yesterday = datetime.now().date() - timedelta(days=1)

        for symbol in get_major_symbols():
            bar = repo.db.query(DailyBar).filter_by(
                symbol=symbol, date=yesterday
            ).first()

            if not bar:
                logging.warning(f"Missing daily bar for {symbol} on {yesterday}")
                # 재수집 로직
                daily_data = await self.broker.get_daily_bars(symbol, days=1)
                if daily_data:
                    await repo.save_daily_bar(symbol, yesterday, daily_data[0])

# 2. main.py에서 시작
@app.on_event("startup")
async def startup():
    scheduler = CollectorScheduler()
    scheduler.start()
```

**검증:**
- [ ] 09:00 — 키움 WS 시작, 실시간 시세 수신
- [ ] 16:00 — 일봉 저장 완료
- [ ] 08:00 — 종목마스터 갱신 (공공데이터포털 API)
- [ ] 17:00 — yfinance 수집
- [ ] 18:00 — 결측 거래일 감지 및 경고 로그

---

### Step 8 — 어드민 API (유저, 통계, 서비스 키, 템플릿)

**목표**: 관리자 대시보드 백엔드

**파일:**
- `cloud_server/api/admin.py` (어드민 엔드포인트)
- `cloud_server/services/admin_service.py` (비즈니스 로직)
- `cloud_server/models/template.py` (StrategyTemplate 모델)

**구현 내용:**
```python
# 1. StrategyTemplate 모델
class StrategyTemplate(Base):
    __tablename__ = "strategy_templates"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    buy_conditions = Column(JSON)
    sell_conditions = Column(JSON)
    default_params = Column(JSON)   # qty, budget_ratio 등
    category = Column(String(50))   # "기술적 지표", "모멘텀" 등
    is_public = Column(Boolean, default=False)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

# 2. 어드민 엔드포인트 (role == "admin" 필수)
# 유저 관리
GET    /api/v1/admin/users           → 유저 목록
PATCH  /api/v1/admin/users/:id       → 유저 상태 변경 (활성/비활성)

# 통계
GET    /api/v1/admin/stats           → {user_count, active_users, rules_count, heartbeat_count}

# 서비스 키 관리
GET    /api/v1/admin/service-keys    → 키 목록 (secret은 마스킹)
POST   /api/v1/admin/service-keys    → 키 등록
DELETE /api/v1/admin/service-keys/:id → 키 삭제

# 전략 템플릿
GET    /api/v1/admin/templates       → 템플릿 목록
POST   /api/v1/admin/templates       → 템플릿 생성
PUT    /api/v1/admin/templates/:id   → 템플릿 수정
DELETE /api/v1/admin/templates/:id   → 템플릿 삭제

# 데이터 수집 상태
GET    /api/v1/admin/collector-status → {status, last_quote_time, error_count, quote_count}

# 3. AdminService
class AdminService:
    def get_stats(self, db: Session) -> dict:
        user_count = db.query(User).count()
        active_users = db.query(User).filter_by(is_active=True).count()
        rules_count = db.query(TradingRule).count()

        # 최근 하트비트 (30분 내)
        thirty_mins_ago = datetime.utcnow() - timedelta(minutes=30)
        active_heartbeats = db.query(Heartbeat).filter(
            Heartbeat.created_at >= thirty_mins_ago
        ).count()

        return {
            "user_count": user_count,
            "active_users": active_users,
            "rules_count": rules_count,
            "active_clients": active_heartbeats,
            "timestamp": datetime.utcnow()
        }

    def get_collector_status(self, db: Session) -> dict:
        # 최근 시세 수신 시간
        last_quote = db.query(MinuteBar).order_by(
            MinuteBar.created_at.desc()
        ).first()

        # 에러 로그 수집
        errors = get_recent_errors(limit=10)

        return {
            "status": "running",  # running | stopped | error
            "last_quote_time": last_quote.created_at if last_quote else None,
            "error_count": len(errors),
            "total_quotes": db.query(MinuteBar).count(),
            "timestamp": datetime.utcnow()
        }

# 4. 권한 검증 (의존성)
async def get_current_admin(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    user = get_current_user(token, db)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
```

**검증:**
- [ ] admin 유저로 어드민 API 접근 → 200 OK
- [ ] 일반 유저로 어드민 API 접근 → 403 Forbidden
- [ ] `GET /api/v1/admin/stats` → 사용자/규칙/하트비트 수 반환
- [ ] `GET /api/v1/admin/collector-status` → 시세 수집 상태 반환
- [ ] 템플릿 CRUD 동작 확인

---

### Step 9 — AI 컨텍스트 API + Claude API 연동 (v2 스텁)

**목표**: AI 컨텍스트 계산 및 Claude API 호출 기반 구조

**파일:**
- `cloud_server/api/context.py` (컨텍스트 API)
- `cloud_server/services/context_service.py` (컨텍스트 계산)
- `cloud_server/services/ai_service.py` (Claude API 호출)

**구현 내용:**
```python
# 1. 컨텍스트 API (v1에서는 지표만, v2에서 Claude 추가)
GET /api/v1/context                → 최신 컨텍스트 스냅샷
GET /api/v1/context/variables      → 사용 가능한 변수 목록
GET /api/v1/context/history?days=30 → 컨텍스트 변화 히스토리

# 2. ContextService — 시장 지표 계산
class ContextService:
    def __init__(self, db: Session):
        self.db = db

    async def get_current_context(self) -> dict:
        """최신 시장 컨텍스트 계산"""
        # KOSPI/KOSDAQ 일봉 조회
        kospi_bars = self.db.query(DailyBar).filter_by(symbol="^KS11").order_by(
            DailyBar.date.desc()
        ).limit(30).all()

        kosdaq_bars = self.db.query(DailyBar).filter_by(symbol="^KQ11").order_by(
            DailyBar.date.desc()
        ).limit(30).all()

        # 기술적 지표 계산
        kospi_rsi = calculate_rsi([b.close for b in kospi_bars], 14)
        kosdaq_rsi = calculate_rsi([b.close for b in kosdaq_bars], 14)
        kospi_ema = calculate_ema([b.close for b in kospi_bars], 20)
        market_volatility = calculate_volatility([b.close for b in kospi_bars])

        return {
            "market": {
                "kospi_rsi": kospi_rsi,
                "kosdaq_rsi": kosdaq_rsi,
                "kospi_ema": kospi_ema,
                "volatility": market_volatility
            },
            "timestamp": datetime.utcnow(),
            "version": 1  # 클라이언트 동기화용
        }

    async def get_available_variables(self) -> list[str]:
        """사용 가능한 변수 목록"""
        return [
            "market_kospi_rsi",
            "market_kosdaq_rsi",
            "market_kospi_ema",
            "market_volatility",
            "rsi_14", "rsi_21",
            "macd", "macd_signal",
            "bollinger_upper", "bollinger_lower",
            "current_price"
        ]

# 3. AIService — Claude API (v2 범위)
class AIService:
    def __init__(self, db: Session):
        self.db = db
        self.anthropic_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def get_sentiment(self, symbol: str, ttl_seconds: int = 3600) -> dict:
        """감성 분석 (v2 구현, v1에서는 스텁)"""

        # v1: 캐시에서 더미값 반환 (실제 Claude 호출은 v2)
        cache_key = f"sentiment:{symbol}"
        cached = await self.cache.get(cache_key)
        if cached:
            return cached

        # v2에서 구현
        """
        prompt = f"분석 대상 종목: {symbol}. 최근 시장 감정은 어떠한가?"
        response = await self.anthropic_client.messages.create(
            model=settings.CLAUDE_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )

        sentiment = parse_sentiment_from_response(response)
        await self.cache.set(cache_key, sentiment, ttl=ttl_seconds)
        return sentiment
        """

        return {
            "symbol": symbol,
            "score": 0.5,  # -1 ~ 1, 0.5 = 중립
            "source": "claude_v2",
            "cached": False
        }

# 4. v1 스텁 응답 (Claude 호출 없음, 지표만)
@app.get("/api/v1/context")
async def get_context(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = ContextService(db)
    context = await service.get_current_context()

    return {
        "success": true,
        "data": context
    }
```

**검증:**
- [ ] `GET /api/v1/context` → 시장 지표 반환 (RSI, EMA, 변동성)
- [ ] `GET /api/v1/context/variables` → 사용 가능한 변수 목록
- [ ] v1 범위에서는 Claude 호출 없음 (스텁만)
- [ ] v2 계획: Claude API 호출 추가

---

### Step 10 — 로컬 서버 통신 API (규칙 fetch, sync, 컨텍스트)

**목표**: 로컬 서버의 데이터 동기화 API

**파일:**
- `cloud_server/api/sync.py` (동기화 엔드포인트)
- `cloud_server/services/sync_service.py` (동기화 로직)

**구현 내용:**
```python
# 1. 로컬 서버 API (JWT 인증)
GET  /api/v1/rules              규칙 fetch (버전 변경 시)
PUT  /api/v1/rules/:id          규칙 sync (로컬에서 변경 시)
GET  /api/v1/context            AI 컨텍스트 fetch (버전 변경 시)
GET  /api/v1/templates          전략 템플릿 목록 fetch
GET  /api/v1/watchlist          관심종목 fetch (watchlist_version 변경 시)
GET  /api/v1/stocks/master-version  종목 메타 버전 확인
POST /api/v1/auth/refresh       JWT 자동 갱신

# 2. 규칙 fetch (하트비트에서 version 차이 감지 후)
GET /api/v1/rules?version=2
Response: {
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "RSI 역매매",
      "symbol": "005930",
      "buy_conditions": {...},
      "sell_conditions": {...},
      "version": 3,
      ...
    }
  ],
  "version": 3
}

# 3. 규칙 sync (로컬 변경 시 업로드)
PUT /api/v1/rules/1
Body: {
  "name": "RSI 역매매 (수정)",
  "buy_conditions": {...},
  "version": 3  # 클라이언트 버전
}
Response: {
  "success": true,
  "data": {
    "id": 1,
    "version": 4,  # 서버에서 증가
    "updated_at": "2026-03-05T15:35:00Z"
  }
}

# 4. SyncService
class SyncService:
    def get_user_rules(self, user_id: int, db: Session, since_version: int = 0) -> tuple[list[dict], int]:
        """사용자 규칙 조회"""
        rules = db.query(TradingRule).filter(
            TradingRule.user_id == user_id
        ).all()

        # 최신 버전 계산
        current_version = db.query(func.max(TradingRule.version)).filter(
            TradingRule.user_id == user_id
        ).scalar() or 1

        result = [
            {
                "id": r.id,
                "name": r.name,
                "symbol": r.symbol,
                "buy_conditions": r.buy_conditions,
                "sell_conditions": r.sell_conditions,
                "execution": r.execution,
                "trigger_policy": r.trigger_policy,
                "priority": r.priority,
                "version": r.version,
                "is_active": r.is_active
            }
            for r in rules
        ]

        return result, current_version

    def get_user_watchlist(self, user_id: int, db: Session) -> list[dict]:
        """관심종목 조회 (로컬 sync용)"""
        items = db.query(Watchlist, StockMaster).join(
            StockMaster, Watchlist.symbol == StockMaster.symbol
        ).filter(Watchlist.user_id == user_id).all()

        return [
            {"symbol": w.symbol, "name": m.name, "market": m.market, "memo": w.memo}
            for w, m in items
        ]

    def sync_rule(self, user_id: int, rule_id: int, payload: dict, db: Session) -> dict:
        """규칙 동기화 (로컬 업로드)"""
        rule = db.query(TradingRule).filter(
            TradingRule.id == rule_id,
            TradingRule.user_id == user_id
        ).first()

        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")

        # 클라이언트 버전 확인 (충돌 감지)
        if payload.get("version") != rule.version:
            raise HTTPException(status_code=409, detail="Version conflict")

        # 규칙 업데이트
        rule.name = payload.get("name", rule.name)
        rule.buy_conditions = payload.get("buy_conditions", rule.buy_conditions)
        rule.sell_conditions = payload.get("sell_conditions", rule.sell_conditions)
        rule.version += 1  # 버전 증가
        rule.updated_at = datetime.utcnow()

        db.commit()

        return {
            "id": rule.id,
            "version": rule.version,
            "updated_at": rule.updated_at
        }
```

**검증:**
- [ ] `GET /api/v1/rules?version=2` → 규칙 목록 + 최신 버전 반환
- [ ] `PUT /api/v1/rules/1` → 버전 증가 확인
- [ ] 버전 충돌 시 → 409 Conflict
- [ ] 로컬 서버가 규칙 fetch → 캐시 업데이트 확인
- [ ] `GET /api/v1/watchlist` → 관심종목 sync 확인
- [ ] `GET /api/v1/stocks/master-version` → 종목 마스터 버전 반환

---

### Step 11 — 기존 backend/ → cloud_server/ 마이그레이션

**목표**: Phase 1-2 코드를 cloud_server 구조로 통합

**파일:**
- 기존 `backend/app/` 코드 → `cloud_server/` 이전
- `backend/` 디렉토리 정리 (legacy 표시)

**구현 내용:**
```
1. 파일 이전
   backend/app/models/stock.py → cloud_server/models/stock.py
   backend/app/services/data_ingestion.py → cloud_server/services/data_ingestion.py
   ... (나머지 파일들)

2. import 수정
   from app.models → from cloud_server.models
   from app.services → from cloud_server.services

3. 기존 엔드포인트 유지
   /api/v1/stocks → 유지
   /api/v1/ai-analysis → 유지
   /api/v1/trading → 유지
   ... (새 엔드포인트 추가)

4. 데이터베이스 마이그레이션
   기존 SQLite → PostgreSQL 전환 (운영)
   Alembic 마이그레이션 스크립트 생성

   기존 테이블:
   - stocks
   - stock_prices
   - technical_indicators
   - auto_trade_snapshots
   - portfolio_history
   ...

   새 테이블 (Unit 4):
   - users (확장)
   - refresh_tokens
   - email_verifications
   - trading_rules
   - daily_bars
   - minute_bars
   - stock_master
   - heartbeats
   - strategy_templates
   - kiwoom_service_keys

5. 테스트 확인
   기존 테스트 수정 → cloud_server 임포트 경로 변경
```

**검증:**
- [ ] 기존 API 엔드포인트 동작 확인 (`/api/v1/stocks/*`)
- [ ] 새 API 엔드포인트 동작 확인 (`/api/v1/auth/*`, `/api/v1/rules/*`)
- [ ] DB 마이그레이션 완료 (schema 검증)
- [ ] 테스트 전체 통과

---

## 2. 파일 목록 및 변경 범위

### 신규 파일 (Step별)

| Step | 파일 | 용도 |
|------|------|------|
| 1 | `cloud_server/main.py` | FastAPI 앱 진입점 |
| 1 | `cloud_server/core/database.py` | DB 연결 설정 |
| 1 | `cloud_server/core/config.py` | 환경 변수 |
| 1 | `cloud_server/requirements.txt` | 의존성 |
| 2 | `cloud_server/models/user.py` | User, RefreshToken, EmailVerification |
| 2 | `cloud_server/api/auth.py` | 인증 API |
| 2 | `cloud_server/services/auth_service.py` | 인증 로직 |
| 2 | `cloud_server/core/security.py` | JWT, Argon2id |
| 3 | `cloud_server/models/rule.py` | TradingRule |
| 3 | `cloud_server/api/rules.py` | 규칙 CRUD API |
| 3 | `cloud_server/services/rule_service.py` | 규칙 로직 |
| 3 | `cloud_server/core/validators.py` | 조건 JSON 검증 |
| 4 | `cloud_server/models/heartbeat.py` | Heartbeat |
| 4 | `cloud_server/api/heartbeat.py` | 하트비트 API |
| 4 | `cloud_server/api/version.py` | 버전 체크 API |
| 5 | `cloud_server/collector/kis_collector.py` | 키움 WS 수신 |
| 5 | `cloud_server/core/broker_factory.py` | BrokerAdapter 팩토리 |
| 6 | `cloud_server/models/market.py` | StockMaster, DailyBar, MinuteBar |
| 6 | `cloud_server/services/market_repository.py` | 시장 데이터 레이어 |
| 6-A | `cloud_server/api/stocks.py` | 종목 검색/상세 API |
| 6-A | `cloud_server/services/stock_service.py` | 종목 메타데이터 로직 |
| 6-B | `cloud_server/api/watchlist.py` | 관심종목 CRUD API |
| 6-B | `cloud_server/models/watchlist.py` | Watchlist 모델 |
| 6-B | `cloud_server/services/watchlist_service.py` | 관심종목 로직 |
| 7 | `cloud_server/collector/scheduler.py` | APScheduler 스케줄 |
| 7 | `cloud_server/services/yfinance_service.py` | yfinance 수집 |
| 8 | `cloud_server/api/admin.py` | 어드민 API |
| 8 | `cloud_server/services/admin_service.py` | 어드민 로직 |
| 8 | `cloud_server/models/template.py` | StrategyTemplate |
| 9 | `cloud_server/api/context.py` | 컨텍스트 API |
| 9 | `cloud_server/services/context_service.py` | 컨텍스트 계산 |
| 9 | `cloud_server/services/ai_service.py` | Claude API (v2 스텁) |
| 10 | `cloud_server/api/sync.py` | 동기화 API |
| 10 | `cloud_server/services/sync_service.py` | 동기화 로직 |
| 11 | (기존 파일 이전) | `backend/app/` → `cloud_server/` |

### 기존 파일 수정

| 파일 | 변경 사항 |
|------|----------|
| `cloud_server/main.py` | 새 라우터 등록 (auth, rules, heartbeat, admin, sync, context, stocks, watchlist) |
| `cloud_server/core/database.py` | PostgreSQL 멀티 환경 지원 추가 |
| `cloud_server/requirements.txt` | 신규 의존성 추가 (argon2-cffi, anthropic, APScheduler 등) |

---

## 3. 의존성

### sv_core 공유 패키지

**필수:**
- `sv_core.broker.base.BrokerAdapter` (ABC)
- `sv_core.broker.kiwoom.KiwoomAdapter` (구현)
- `sv_core.models.*` (OrderResult, QuoteEvent 등)

**상태:** Unit 1에서 구현 완료 → pip install -e ../sv_core

---

## 4. 미결 사항 처리

| 미결 사항 | 처리 방법 |
|---------|---------|
| 규칙 조건 JSON 검증 스키마 확정 | Step 3에서 구현 (spec §5.3 참조) |
| Rate Limiting 구체 구현 | Step 2에서 in-memory 구현 (Redis는 v2+) |
| 분봉 데이터 보관 정책 | 1년 기본값 (Step 6, 배치 정리는 v2) |
| 서비스 키 IP 화이트리스트 | Step 5에서 선택적 구현 (클라우드 IP 등록) |
| 기존 yfinance 코드 재사용 | Step 7에서 통합 (data_ingestion.py) |
| Claude API 호출 비용 최적화 | Step 9 v2에서 캐시 TTL 조정 |

---

## 5. 커밋 계획

### 단계별 커밋 목록

| 순번 | Step | 커밋 메시지 |
|------|------|-----------|
| 1 | 1 | `feat: cloud-server 프로젝트 구조 + FastAPI 앱 + DB 설정` |
| 2 | 2 | `feat: cloud-server 인증 시스템 (가입, 로그인, JWT, Refresh Rotation, 비밀번호 재설정)` |
| 3 | 3 | `feat: cloud-server 규칙 CRUD + 조건 JSON 검증` |
| 4 | 4 | `feat: cloud-server 하트비트 수신 + 버전 체크 API` |
| 5 | 5 | `feat: cloud-server 시세 수집기 (서비스 키움 WS/REST, sv_core 사용)` |
| 6 | 6 | `feat: cloud-server 시세 저장 (DailyBar, MinuteBar, StockMaster)` |
| 7 | 6-A | `feat: cloud-server 종목 검색 API (StockMaster 검색 + 상세)` |
| 8 | 6-B | `feat: cloud-server 관심종목 CRUD` |
| 9 | 7 | `feat: cloud-server 수집 스케줄러 (APScheduler: WS, 일봉, 종목마스터, yfinance)` |
| 10 | 8 | `feat: cloud-server 어드민 API (유저, 통계, 서비스 키, 템플릿, 수집 상태)` |
| 11 | 9 | `feat: cloud-server AI 컨텍스트 API + Claude 연동 (v1 스텁, v2 추진)` |
| 12 | 10 | `feat: cloud-server 로컬 서버 통신 API (규칙/컨텍스트/관심종목 동기화)` |
| 13 | 11 | `feat: backend/app → cloud_server 마이그레이션 완료` |

---

## 6. 성공 기준

### 통합 검증 (전체 Step 완료 후)

#### 인증 흐름
- [ ] 회원가입 → 이메일 인증 → 로그인 → JWT 발급
- [ ] Refresh Token으로 JWT 자동 갱신 (Rotation)
- [ ] 비밀번호 재설정 완료
- [ ] Rate Limiting 동작

#### 규칙 관리
- [ ] 규칙 CRUD 정상 동작
- [ ] 조건 JSON 검증 (유효/무효)
- [ ] 사용자 격리 (다른 유저 규칙 접근 불가)
- [ ] 규칙 버전 변경 감지

#### 시세 수집
- [ ] 서비스 키로 키움 WS 연결
- [ ] 실시간 시세 수신 → MinuteBar 저장
- [ ] 장 마감 후 일봉 저장
- [ ] 결측 거래일 감지 + 재수집

#### 종목/관심종목
- [ ] 종목 검색 → 이름/코드 매칭 결과 반환 (시세 미포함)
- [ ] 종목 상세 → 메타데이터 반환
- [ ] 관심종목 등록/조회/삭제 정상 동작
- [ ] 중복 관심종목 추가 → 409 Conflict
- [ ] 공공데이터포털 수집 → StockMaster 갱신 확인

#### 로컬 서버 통신
- [ ] `POST /api/v1/heartbeat` (JWT 인증) → rules_version, context_version, stock_master_version, watchlist_version 반환
- [ ] rules_version 변경 시 규칙 fetch
- [ ] 규칙 sync → version 증가
- [ ] 관심종목 sync 정상 동작
- [ ] JWT 자동 갱신

#### 어드민
- [ ] admin 유저로 어드민 API 접근 가능
- [ ] 일반 유저로 어드민 API 접근 → 403
- [ ] 통계, 키 관리, 수집 상태 조회

#### 컨텍스트
- [ ] `GET /api/v1/context` → 시장 지표 반환
- [ ] v1에서는 Claude 호출 없음 (스텁)

---

## 7. 개발 순서 권장

**병렬 가능 항목** (독립적):
- Step 2 (인증) 과 Step 3 (규칙) 동시 진행
- Step 8 (어드민) 과 Step 4 (하트비트) 동시 진행
- Step 6-A (종목 검색) 과 Step 6-B (관심종목) 동시 진행 (Step 6 완료 후)

**의존 순서**:
```
Step 1 (DB) → Step 2 (인증) → Step 3 (규칙)
           → Step 4 (하트비트) → Step 10 (동기화)
           → Step 5 (수집기) → Step 6 (저장) → Step 6-A (종목 검색)
                                             → Step 6-B (관심종목)
                                             → Step 7 (스케줄)
                             → Step 9 (컨텍스트)
           → Step 8 (어드민)
           → Step 11 (마이그레이션)
```

---

**마지막 갱신**: 2026-03-06
