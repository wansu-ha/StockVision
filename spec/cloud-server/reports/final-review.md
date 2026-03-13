# 최종 리뷰 보고서: cloud_server Unit 4

> 완료일: 2026-03-05

## 개요

`cloud_server/`는 총 11 Step에 걸쳐 구현된 Phase 3 클라우드 서버.
본 보고서는 전체 구현을 일관성, 보안, API 규격, 모델 관계, 법적 준수 측면에서 검토한다.

---

## 1. 파일 구조 점검

```
cloud_server/
├── main.py                          # FastAPI 앱, 라이프사이클, 미들웨어
├── requirements.txt                 # 의존성
├── core/
│   ├── config.py                    # 환경변수 Settings
│   ├── database.py                  # SQLAlchemy engine, get_db, get_db_session
│   ├── security.py                  # JWT, Argon2id, SHA-256
│   ├── encryption.py                # AES-256-GCM
│   ├── rate_limit.py                # 슬라이딩 윈도우 Rate Limiter
│   ├── email.py                     # SMTP 이메일
│   ├── validators.py                # 조건 JSON 검증
│   ├── broker_factory.py            # BrokerFactory + _KiwoomStub
│   └── init_db.py                   # create_all
├── models/
│   ├── user.py                      # User, RefreshToken, 인증 토큰들
│   ├── rule.py                      # TradingRule
│   ├── heartbeat.py                 # Heartbeat
│   ├── market.py                    # StockMaster, DailyBar, MinuteBar
│   └── template.py                  # StrategyTemplate, KiwoomServiceKey
├── api/
│   ├── dependencies.py              # current_user, require_admin
│   ├── auth.py                      # 인증 7개 엔드포인트
│   ├── rules.py                     # 규칙 CRUD 5개 엔드포인트
│   ├── heartbeat.py                 # POST /api/v1/heartbeat
│   ├── version.py                   # GET /api/v1/version
│   ├── admin.py                     # 어드민 11개 엔드포인트
│   ├── context.py                   # GET /api/v1/context[/variables]
│   └── sync.py                      # GET /api/v1/templates (공개)
├── services/
│   ├── rule_service.py              # 규칙 CRUD 비즈니스 로직
│   ├── heartbeat_service.py         # 하트비트 저장 + 버전 계산
│   ├── market_repository.py         # 시세 upsert
│   ├── yfinance_service.py          # yfinance 수집
│   ├── context_service.py           # RSI, EMA, 변동성
│   ├── ai_service.py                # Claude API stub (v1)
│   └── admin_service.py             # 어드민 비즈니스 로직
└── collector/
    ├── kis_collector.py          # KiwoomCollector
    └── scheduler.py                 # APScheduler (5개 cron)

sv_core/   (Unit 1 stub — cloud_server 의존성 해소용)
├── broker/base.py                   # BrokerAdapter ABC
└── models/quote.py                  # QuoteEvent
```

**이상 없음.** 모든 모듈이 존재하고 init_db.py가 전체 모델을 import한다.

---

## 2. API 응답 형식 일관성

규칙: `{ "success": bool, "data": ..., "count": int }` 통일.

| 엔드포인트 | success | data | count | 비고 |
|-----------|---------|------|-------|------|
| POST /auth/register | O | X (message) | X | 적절 (생성 확인 메시지) |
| POST /auth/login | O | {jwt, refresh_token, expires_in} | X | 적절 |
| POST /auth/refresh | O | {jwt, refresh_token, expires_in} | X | 적절 |
| GET /rules | O | [...] | O | OK |
| POST /rules | O | {...} | X | OK (단일 객체) |
| POST /heartbeat | O | {rules_version, context_version, ...} | X | OK |
| GET /admin/stats | O | {...} | X | OK (단일 통계) |
| GET /admin/users | O (+ users, total, page, limit) | X | X | 허용 — 페이지네이션 구조 |
| GET /admin/service-keys | O | [...] | O | OK |
| GET /context | O | {...} | X | OK (단일 컨텍스트) |
| GET /templates (sync) | O | [...] | O | OK |

**이상 없음.** forgot-password 응답은 이메일 열거 방지로 항상 200 + message 반환 — 의도적 설계.

---

## 3. 인증 & 보안 점검

### 3.1 비밀번호

- `Argon2id` (time=3, memory=64MB, parallelism=4) — OWASP 2023 권장 수준
- `verify_password`에서 `InvalidHashError`, `VerifyMismatchError` 모두 catch → False 반환

### 3.2 JWT

- HS256, 1시간 만료, payload에 `sub`, `email`, `role`, `iat`, `exp`
- `current_user` 의존성이 `verify_jwt` 래핑 → JWTError 시 401 반환
- `require_admin` 의존성이 role == "admin" 검증 → 아니면 403 반환

### 3.3 Refresh Token Rotation

```
로그인: raw_token → hash_token(SHA-256) → DB 저장
갱신: hash_token(요청 토큰) → DB 조회 → 기존 삭제 → 새 토큰 발급
```

- `rotated_at` 필드로 교체 이력 추적 가능
- 비밀번호 재설정 시 전체 RefreshToken 삭제 → 기존 세션 무효화

### 3.4 Rate Limiting

| 엔드포인트 | 제한 | 윈도우 |
|-----------|------|--------|
| /auth/login | 10회/시간 | 슬라이딩 |
| /auth/register | 5회/시간 | 슬라이딩 |
| /auth/forgot-password | 3회/시간 | 슬라이딩 |

- IP별 `threading.Lock` 슬라이딩 윈도우 구현
- `X-Forwarded-For` 헤더 우선 (프록시/로드밸런서 환경 대응)
- 초과 시 HTTP 429 반환

### 3.5 서비스 키 암호화

- `api_secret`: AES-256-GCM 암호화 후 hex 저장
- 목록 조회 시 `"***"` 마스킹
- 복호화는 스케줄러에서 WS 시작 시에만 수행

**이상 없음.** 이메일 인증 필수, 계정 비활성 차단, 이메일 열거 방지 모두 구현.

---

## 4. DB 모델 & 관계 점검

### 4.1 User 중심 관계 그래프

```
User (1) ──< RefreshToken           cascade delete
     (1) ──< EmailVerificationToken cascade delete
     (1) ──< PasswordResetToken     cascade delete
     (1) ──< TradingRule            cascade delete
     (1) ──< Heartbeat              cascade delete
```

- 모든 FK에 `cascade="all, delete-orphan"` 설정 → 유저 삭제 시 관련 데이터 정리
- `StrategyTemplate.created_by`는 FK이지만 cascade 없음 — 의도적 (어드민 콘텐츠 보존)

### 4.2 인덱스

| 모델 | 인덱스 | 목적 |
|------|--------|------|
| User | email (unique) | 로그인 |
| RefreshToken | user_id, token_hash | Rotation 조회 |
| TradingRule | user_id + UniqueConstraint(user_id, name) | 사용자별 규칙 조회 |
| Heartbeat | (uuid, user_id) | 복합 조회 |
| DailyBar | (symbol, date) + UniqueConstraint | 시계열 조회 |
| MinuteBar | (symbol, timestamp) + UniqueConstraint | 실시간 시계열 |
| StockMaster | market | 시장별 필터 |

**이상 없음.** init_db.py가 모든 모델을 import하여 누락 없이 테이블 생성.

---

## 5. 수집기 & 스케줄러 점검

### 5.1 APScheduler 설정

- `AsyncIOScheduler(timezone="Asia/Seoul")` — KST 기준 cron
- 5개 Job: kiwoom_ws_start(09:00), daily_bars(16:00), stock_master(08:00), yfinance(17:00), integrity_check(18:00)
- `replace_existing=True` — 재시작 시 중복 Job 방지

### 5.2 상태 관리

`_collector_status` 전역 dict로 추적:
```python
{
    "status": "running | stopped | error",
    "last_quote_time": "ISO string",
    "error_count": 0,
    "total_quotes": 0,
    "last_error": None,
}
```

- 어드민 API `/admin/collector-status`에서 이 상태를 DB 최신 MinuteBar와 병합하여 반환

### 5.3 미완성 항목 (Unit 1 대기)

| 항목 | 현재 | 완성 조건 |
|------|------|-----------|
| 키움 WS 실제 연결 | BrokerFactory → _KiwoomStub fallback | Unit 1: sv_core.broker.kiwoom 구현 |
| 일봉 저장 (16:00) | yfinance 폴백으로 대체 | BrokerAdapter.get_daily_bars() |
| 종목 마스터 갱신 | stub (로그만) | BrokerAdapter.get_listed_symbols() |

**설계 의도에 부합.** stub 경로가 명확하게 문서화되어 있고, BrokerFactory 패턴으로 Unit 1 완성 시 코드 최소 변경으로 교체 가능.

---

## 6. 법적 준수 (키움 약관) 점검

| 약관 조항 | 위반 위험 | 구현 대응 |
|-----------|-----------|-----------|
| 제3자 위임 금지 | 클라우드가 주문 명령 | 클라우드는 규칙/컨텍스트만 제공, 주문은 로컬 서버에서만 |
| 제5조③ 시세 중계 금지 | 수집 시세를 외부 제공 | 어드민 API만 시세 접근 가능, 일반 유저 엔드포인트 없음 |
| API 키 보안 | 유저 키 클라우드 저장 | 서비스 키(수집용)만 클라우드 저장, 유저 키는 로컬에만 |

**이상 없음.** 시세 API가 `require_admin` 의존성으로 잠겨 있어 일반 유저 접근 불가.

---

## 7. 버전 동기화 흐름 점검

```
로컬 서버 → POST /api/v1/heartbeat
                 ↓
           { rules_version: N, context_version: M }
                 ↓
   로컬 캐시 버전 비교 → 차이 있으면 GET /api/v1/rules 호출
```

- `rules_version`: `MAX(TradingRule.version)` for user_id
- `context_version`: v1에서는 상수 1, v2에서 DB 또는 Redis 기반 캐시로 교체 예정
- TradingRule 수정 시 `version++` → 다음 하트비트에서 로컬이 감지하고 fetch

**이상 없음.** 버전 기반 폴링 설계가 일관되게 구현됨.

---

## 8. 발견된 버그 및 수정 이력

| 번호 | 파일 | 내용 | 조치 |
|------|------|------|------|
| 1 | `models/heartbeat.py` | `relationship` import가 클래스 바디 내에 위치 | 모듈 레벨로 이동 |
| 2 | `core/broker_factory.py` | `_KiwoomStub.listen()` 빈 async generator 관용구 불명확 | `if False: yield` 패턴으로 교체 |
| 3 | `services/admin_service.py` | `decrypt_value` import했으나 미사용 | import 제거 |

모든 버그는 구현 중 즉시 수정되었으며, 현재 코드에는 존재하지 않음.

---

## 9. 미구현 항목 (Phase 3 범위 외)

| 항목 | 이유 |
|------|------|
| Alembic 마이그레이션 | 현재 create_all, PostgreSQL 전환 시 필요 |
| Redis Rate Limiter | 현재 in-memory, 수평 확장 시 필요 |
| Claude API 실제 호출 | v2 계획, ai_service.py에 주석으로 확장 지점 표시 |
| 뉴스 감성 분석 | v2 계획 |
| PostgreSQL 통합 테스트 | DATABASE_URL 환경변수로 제어 가능, 테스트 미완 |
| backend/app/ stocks API 이전 | Phase 3 범위 외 |

---

## 10. 최종 체크리스트

- [x] 모든 라우터가 `main.py`에 등록됨
- [x] 모든 모델이 `init_db.py`에 import됨
- [x] API 응답 형식 `{ success, data, count }` 일관
- [x] 인증이 필요한 모든 엔드포인트에 `current_user` 의존성 적용
- [x] 어드민 전용 엔드포인트에 `require_admin` 적용
- [x] 비밀번호 Argon2id 해싱
- [x] Refresh Token Rotation (SHA-256 해시 저장)
- [x] AES-256-GCM 서비스 키 암호화
- [x] Rate Limiting (login/register/forgot-password)
- [x] APScheduler KST 타임존
- [x] 이메일 열거 방지 (forgot-password 항상 200)
- [x] 계정 비활성 차단 (login 403)
- [x] 이메일 인증 필수 (login 403)
- [x] 시세 API 어드민 전용 (키움 약관 제5조③)
- [x] 디버그 코드 없음
- [x] 모든 Step 보고서 작성 완료 (step1~step11)

---

## 실행 방법

```bash
# 의존성 설치
pip install -r cloud_server/requirements.txt

# 서버 실행 (포트 8001)
python -m uvicorn cloud_server.main:app --reload --port 8001

# DB 수동 초기화 (서버 시작 시 자동)
python -m cloud_server.core.init_db
```

환경변수 (`.env`):
```
DATABASE_URL=sqlite:///./cloud_server.db  # 개발
SECRET_KEY=<random-secret>
SMTP_ENABLED=false                         # 개발
```
