# cloud_server 코드 리뷰

> 작성일: 2026-03-13 | 대상: cloud_server/ 전체

---

## 요약

| 분류 | 건수 |
|------|------|
| Critical | 3 |
| High | 6 |
| Medium | 8 |
| Low | 6 |
| 미완성 기능 | 6 |

핵심 문제: (1) collector scheduler가 `broker.authenticate()` 호출 → `AttributeError` (ABC에 없는 메서드), KIS WS 데이터 수집 불가, (2) OAuth 동시 로그인 시 IntegrityError, (3) `password_hash` nullable 설계 미비.

---

## Critical

### C-1: broker.authenticate() → AttributeError, KIS WS 시작 불가

**파일**: `cloud_server/collector/scheduler.py` L157
**신뢰도**: 100%

`BrokerAdapter` ABC에 `authenticate()` 메서드가 없음. `connect()`로 교체 필요.

### C-2: OAuth 동시 로그인 → IntegrityError (500)

**파일**: `cloud_server/services/oauth_service.py` L139-157
**신뢰도**: 95%

동시 요청 시 `(provider, provider_user_id)` unique constraint 위반. try/except IntegrityError 필요.

### C-3: User.password_hash nullable 설계 미비

**파일**: `cloud_server/models/user.py` L29, `oauth_service.py` L145
**신뢰도**: 90%

OAuth 등록 시 `password_hash=""` 저장. `nullable=True`로 변경하고 `is None` 체크가 적절.

---

## High

### H-1: Device 중복 체크에 user_id 필터 없음

**파일**: `cloud_server/api/devices.py` L67
**신뢰도**: 92%

다른 사용자가 같은 device_id를 등록하면 409 에러. Cross-user DoS 가능.

### H-2: AIService.__new__() 안티패턴

**파일**: `cloud_server/api/ai.py` L57
**신뢰도**: 85%

`__init__` 우회로 `self.db` 미설정. `get_status()`가 `self.db` 사용하면 AttributeError.

### H-3: Rate limiter X-Forwarded-For 스푸핑 가능

**파일**: `cloud_server/core/rate_limit.py` L41-45
**신뢰도**: 85%

클라이언트가 임의 IP로 헤더 설정하면 rate limit 우회 가능.

### H-4: /stocks/master 페이지네이션 없음

**파일**: `cloud_server/api/stocks.py` L31-46
**신뢰도**: 83%

KRX 전체 ~2,500종목을 한 번에 반환. 부하 위험.

### H-5: 해외 지수 OHLC 정수 절삭

**파일**: `cloud_server/api/market_data.py` L72-79
**신뢰도**: 82%

`int()` 변환으로 소수점 이하 손실. 한국 주식은 문제없으나 해외 지수 데이터 부정확.

### H-6: WS heartbeat마다 새 DB 세션 생성

**파일**: `cloud_server/services/relay_manager.py` L174, 225, 246
**신뢰도**: 80%

---

## Medium

### M-1: auth.py 함수 내부 중복 import (dead code)
`cloud_server/api/auth.py` L354.

### M-2: AI daily counter — 프로세스 로컬, 재시작 시 리셋
`cloud_server/services/ai_service.py` L22-23. Redis에 저장 필요.

### M-3: 배당 데이터 — DB 저장 후 재조회 안 함
`cloud_server/api/market_data.py` L215-226.

### M-4: OAuth URL 쿼리스트링 URL 인코딩 안 됨
`cloud_server/services/oauth_service.py` L39-48. `urlencode()` 사용 필요.

### M-5: Watchlist 버전 = item count — 단조 증가 아님
`cloud_server/services/watchlist_service.py` L56-60. 추가+삭제 시 변경 감지 실패.

### M-6: Alembic 마이그레이션 초기 스키마 불일치
`cloud_server/alembic/versions/5fc19af729fc_initial_schema.py`. 신규 DB에서 `alembic upgrade head` 실패.

### M-7: MAX_DEVICES 상수 두 곳에 독립 정의
`cloud_server/api/devices.py` L17 vs `services/session_manager.py` L14.

### M-8: stock search — SQL LIKE 와일드카드 미이스케이프
`cloud_server/services/stock_service.py` L33. `%`, `_` 문자가 와일드카드로 동작.

---

## Low

| ID | 내용 |
|----|------|
| L-1 | `DartProvider.get_dividends()` 항상 `[]` 반환 — dead code |
| L-2 | Email/PasswordReset 토큰 평문 저장 (RefreshToken은 해시) |
| L-3 | `_KisStub`에도 `authenticate()` 없음 — C-1과 동일 |
| L-4 | MinuteBar 수집 비기능 (C-1 의존) |
| L-5 | stock search LIKE 와일드카드 미이스케이프 |
| L-6 | 일봉 캐시 partial hit 시 불완전 범위 반환 |

---

## 테스트 커버리지 갭

테스트 없는 영역:
- WebSocket relay / session manager / relay manager
- Market data API (/bars, /quote, /financials, /dividends)
- OAuth flow
- Device management
- Context service (RSI/MACD/Bollinger 계산)
- Admin service key management
- Scheduler (모든 cron 작업)
- Data providers (DART, yfinance)
- conftest.py에 MarketBriefing, StockBriefing, PendingCommand, AuditLog, OAuthAccount, Device 모델 누락

---

## 미완성 기능

| ID | 내용 | 차단 요인 |
|----|------|----------|
| I-1 | 실시간 MinuteBar 수집 | C-1 (authenticate → connect) |
| I-2 | DART 배당 데이터 | L-1 (get_dividends stub) |
| I-3 | WS 원격 제어 (Phase C6-C8) | 구현됨, 미테스트 |
| I-4 | Redis rate limiting | 인메모리만 구현 |
| I-5 | MinuteBar 데이터 | C-1 의존 |
| I-6 | context_version | 하드코딩 `1`, "v2에서 확장" 주석 |
