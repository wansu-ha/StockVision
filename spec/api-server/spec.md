# API 서버 명세서 (api-server)

> **⚠️ SUPERSEDED** — `spec/cloud-server/spec.md`에 병합됨 (2026-03-05).
> API 서버 + 데이터 서버 → 클라우드 서버로 통합.
>
> 작성일: 2026-03-04 | 상태: ~~초안~~ SUPERSEDED | Unit 4 (Phase 3-A)
>
> **병합 대상**: `spec/auth/`, `spec/context-cloud/` → 본 spec에 통합.
> 기존 Phase 1-2 `backend/` 코드를 정리/확장.

---

## 1. 목표

클라우드에서 운영되는 **얇은 웹 서버**를 구현한다.
사용자 인증, 전략 규칙 저장, AI 컨텍스트 중계, 어드민 기능을 제공.

**핵심 원칙:**
- 개인 금융정보 미보유 (체결, 잔고, 수익률 = 로컬에만)
- 매매 판단/명령 미수행 (시스템매매 도구, 투자일임 아님)

---

## 2. 요구사항

### 2.1 기능적 요구사항

| ID | 요구사항 | 우선순위 |
|----|---------|---------|
| F1 | 회원가입 (이메일 + 비밀번호 + 닉네임) | P0 |
| F2 | 이메일 인증 (인증 링크) | P0 |
| F3 | 로그인 → JWT (1h) + Refresh Token (7~30d) | P0 |
| F4 | 토큰 갱신 (Refresh Token Rotation) | P0 |
| F5 | 비밀번호 재설정 (이메일 링크, 10분 TTL) | P0 |
| F6 | 전략 규칙 CRUD (생성, 조회, 수정, 삭제) | P0 |
| F7 | AI 컨텍스트 조회 API (데이터 서버에서 fetch) | P1 |
| F8 | 하트비트 수신 (익명 통계) | P1 |
| F9 | 버전 체크 API | P1 |
| F10 | 어드민: 유저 목록/관리 | P1 |
| F11 | 어드민: 시스템 통계 (접속, 규칙 수) | P1 |
| F12 | 어드민: 서비스 키움 키 관리 | P2 |
| F13 | 어드민: 전략 템플릿 CRUD | P2 |

### 2.2 비기능적 요구사항

| 항목 | 목표 |
|------|------|
| API P95 응답 | < 200ms |
| 동시 접속 | 1000+ (Phase 1 목표: 100) |
| 가동률 | > 99.5% |
| 비밀번호 해싱 | Argon2id (OWASP 2023) |
| 설정 암호화 | AES-256-GCM (서버사이드) |

---

## 3. 아키텍처

### 3.1 모듈 구조

```
backend/app/
├── api/
│   ├── auth.py           # 인증 (가입, 로그인, 토큰, 비밀번호)
│   ├── rules.py          # 전략 규칙 CRUD
│   ├── context.py        # AI 컨텍스트 조회
│   ├── heartbeat.py      # 하트비트 수신
│   ├── version.py        # 버전 체크
│   └── admin.py          # 어드민 API
├── core/
│   ├── security.py       # JWT 발급/검증, Argon2id
│   ├── encryption.py     # AES-256-GCM (설정 blob)
│   ├── database.py       # DB 연결
│   └── config.py         # 환경 변수
├── models/
│   ├── user.py           # User, RefreshToken, EmailVerification
│   ├── rule.py           # TradingRule (전략 규칙)
│   ├── heartbeat.py      # Heartbeat 로그
│   └── template.py       # StrategyTemplate (어드민)
├── services/
│   ├── auth_service.py   # 인증 비즈니스 로직
│   ├── rule_service.py   # 규칙 비즈니스 로직
│   ├── context_service.py # 컨텍스트 조회 (데이터 서버 연동)
│   └── admin_service.py  # 어드민 비즈니스 로직
└── main.py               # FastAPI 앱
```

---

## 4. 인증 시스템

> 상세는 `spec/auth/spec.md` 참조. 핵심만 요약.

### 4.1 가입/로그인

```
POST /api/v1/auth/register   → 가입 + 이메일 인증 발송
GET  /api/v1/auth/verify-email?token=xxx → 이메일 인증
POST /api/v1/auth/login      → JWT + Refresh Token
POST /api/v1/auth/refresh    → 토큰 갱신 (Rotation)
POST /api/v1/auth/logout     → Refresh Token 무효화
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

```python
class TradingRule(Base):
    __tablename__ = "trading_rules"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    symbol = Column(String(10), nullable=False)

    # 조건 (JSON)
    buy_conditions = Column(JSON)     # { operator: "AND", conditions: [...] }
    sell_conditions = Column(JSON)

    # 설정
    order_type = Column(String(10), default="market")  # market | limit
    qty = Column(Integer, nullable=False)
    max_position_count = Column(Integer, default=5)
    budget_ratio = Column(Float, default=0.2)

    # 상태
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
```

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

---

## 6. AI 컨텍스트 API

### 6.1 엔드포인트

```
GET /api/v1/context                → 최신 컨텍스트 스냅샷
GET /api/v1/context/variables      → 사용 가능한 변수 목록
GET /api/v1/context/history?days=30 → 컨텍스트 변화 히스토리
```

### 6.2 동작

- API 서버가 데이터 서버에서 시세 데이터 조회
- 컨텍스트 변수 계산 (RSI, 모멘텀, 강도 등)
- 결과를 JSON으로 응답

> 상세 변수 목록은 `spec/context-cloud/spec.md` §3 참조.

---

## 7. 하트비트/버전

### 7.1 하트비트

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

- UUID는 로컬 설치 시 1회 생성 (개인정보 아님)
- 로컬 서버가 JWT 인증으로 직접 전송 (프론트엔드 경유 불필요)

### 7.2 버전 체크

```
GET /api/v1/version
Response: {
  "latest": "1.2.0",
  "min_supported": "1.0.0",
  "download_url": "https://..."
}
```

---

## 8. 어드민 API

### 8.1 엔드포인트

```
# 유저 관리
GET    /api/v1/admin/users           → 유저 목록 (이메일, 닉네임, 가입일)
PATCH  /api/v1/admin/users/:id       → 유저 상태 변경 (비활성화 등)

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
```

### 8.2 권한

- `role` 필드로 관리: `"user"` | `"admin"`
- 어드민 API는 `role == "admin"` 필수

### 8.3 볼 수 있는 것 vs 없는 것

| 볼 수 있음 | 볼 수 없음 |
|------------|-----------|
| 유저 이메일/닉네임 | 키움 API Key |
| 접속 상태 (하트비트) | 체결 내역, 잔고 |
| 저장된 규칙 내용 | 수익률, 거래량 |
| 시세 데이터 (데이터 서버) | — |

---

## 9. 데이터 모델

### 9.1 User

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

### 9.2 Heartbeat

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

### 9.3 StrategyTemplate

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

## 10. 로컬 서버 직접 통신

로컬 서버가 JWT 인증으로 API 서버에 직접 접속한다 (프론트엔드 경유 불필요).

### 10.1 로컬 서버가 사용하는 API

```
GET  /api/v1/context            AI 컨텍스트 fetch (스케줄 폴링)
POST /api/v1/heartbeat          하트비트 전송 (주기적)
GET  /api/v1/templates          전략 템플릿 목록 fetch
POST /api/v1/auth/refresh       JWT 자동 갱신 (Refresh Token)
GET  /api/v1/rules              규칙 re-fetch (WS push 수신 후)
```

### 10.2 WebSocket (로컬 서버용)

```
WS /ws (JWT 인증)

서버 → 로컬 서버 push 이벤트:
  { "type": "rules_changed" }        → 규칙 변경됨 → re-fetch 트리거
  { "type": "context_updated" }      → 새 컨텍스트 준비됨 → fetch 트리거
  { "type": "system_notice", ... }   → 점검 예정, 긴급 공지
```

> 프론트엔드 WS와 로컬 서버 WS는 같은 엔드포인트 사용 가능.
> 클라이언트 유형(browser/local)은 연결 시 구분.

---

## 11. 수용 기준

### 11.1 인증

- [ ] 회원가입 → 인증 이메일 수신 → 이메일 인증 완료
- [ ] 로그인 → JWT + Refresh Token 발급
- [ ] Refresh Token으로 JWT 자동 갱신
- [ ] 비밀번호 재설정 완료

### 11.2 규칙

- [ ] 규칙 생성 → DB 저장 → 조회 확인
- [ ] 규칙 수정/삭제 정상 동작
- [ ] 조건 JSON 검증 (잘못된 형식 → 400 에러)

### 11.3 컨텍스트

- [ ] `GET /api/v1/context` → 시장 지표 JSON 응답
- [ ] `GET /api/v1/context/variables` → 변수 목록

### 11.4 어드민

- [ ] admin 유저로 유저 목록 조회
- [ ] 일반 유저로 어드민 API 접근 → 403

---

### 11.5 로컬 서버 통신

- [ ] 로컬 서버가 JWT로 컨텍스트 fetch 성공
- [ ] 로컬 서버가 JWT로 하트비트 전송 성공
- [ ] WS 연결 → 규칙 변경 push 수신 확인
- [ ] Refresh Token 갱신 정상 동작

---

## 12. 범위

### 포함

- 인증 시스템 전체 (가입~비밀번호 재설정)
- 전략 규칙 CRUD
- AI 컨텍스트 조회 API
- 하트비트 수신
- 버전 체크 API
- 어드민 API (유저, 통계, 키, 템플릿)
- WebSocket (프론트엔드 + 로컬 서버 공용: 규칙 변경/컨텍스트 갱신 push)

### 미포함

- 프론트엔드 (Unit 6)
- 데이터 서버 시세 수집 (Unit 5)
- 로컬 서버 (Unit 2)
- 커뮤니티 전략 공유 (v2)
- LLM 서버 연동 (v3+)

---

## 13. 기존 spec과의 관계

| 기존 | 상태 |
|------|------|
| `spec/auth/` | **병합** — 인증 부분 본 spec §4에 통합 |
| `spec/context-cloud/` | **병합** — 컨텍스트 API 부분 본 spec §6에 통합 |

---

## 14. 기술 요구사항

| 항목 | 선택 |
|------|------|
| Python | 3.13 |
| 프레임워크 | FastAPI |
| DB | PostgreSQL (운영), SQLite (개발) |
| ORM | SQLAlchemy |
| 비밀번호 | argon2-cffi |
| JWT | python-jose |
| 암호화 | cryptography (AES-256-GCM) |
| 이메일 | SMTP (Gmail / SendGrid) |

---

## 15. 미결 사항

- [ ] 커뮤니티 전략 공유 API 설계 (v2 시점)
- [ ] 규칙 조건 JSON 검증 스키마 확정
- [ ] 데이터 서버 내부 API 통신 방식 (HTTP / gRPC)
- [ ] 어드민 페이지 RBAC 세분화 필요 여부
- [ ] Rate Limiting 구체 구현 (Redis vs in-memory)

---

## 참고

- `spec/auth/spec.md` (상세 인증 흐름)
- `spec/context-cloud/spec.md` (상세 변수 목록)
- `docs/architecture.md` §4.2, §8
- `docs/development-plan-v2.md` Unit 4

---

**마지막 갱신**: 2026-03-04
