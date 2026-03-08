# Step 11 보고서: 마이그레이션 (backend/app → cloud_server)

> 완료일: 2026-03-05

## 마이그레이션 전략

### 접근 방법

`cloud_server/`를 신규 코드베이스로 생성하고, `backend/app/`은 레거시로 유지.
점진적 전환 방식으로 기존 API를 깨뜨리지 않음.

### 코드 재사용 현황

| 기존 | 신규 | 상태 |
|------|------|------|
| `backend/app/api/auth.py` | `cloud_server/api/auth.py` | 재설계 (v1/auth → v1/auth, JWT 1h, Rotation 개선) |
| `backend/app/core/password.py` | `cloud_server/core/security.py` | 통합 (password + jwt + token) |
| `backend/app/core/encryption.py` | `cloud_server/core/encryption.py` | str 기반으로 개선 |
| `backend/app/core/email.py` | `cloud_server/core/email.py` | settings 기반으로 개선 |
| `backend/app/core/database.py` | `cloud_server/core/database.py` | pool_pre_ping 추가 |
| `backend/app/api/admin.py` | `cloud_server/api/admin.py` | 확장 (서비스 키, 수집 상태 추가) |
| `backend/app/models/auth.py` | `cloud_server/models/user.py` | is_active, last_login_at 추가 |
| `backend/app/services/market_context.py` | `cloud_server/services/context_service.py` | DB 기반 + yfinance 폴백 |

### 신규 기능 (Phase 3)

| 기능 | 파일 |
|------|------|
| TradingRule CRUD | `cloud_server/api/rules.py` |
| 하트비트 API | `cloud_server/api/heartbeat.py` |
| 버전 체크 API | `cloud_server/api/version.py` |
| 시세 수집기 | `cloud_server/collector/kis_collector.py` |
| 시장 데이터 저장 | `cloud_server/services/market_repository.py` |
| APScheduler | `cloud_server/collector/scheduler.py` |
| sv_core stub | `sv_core/broker/base.py` |

### DB 스키마 변경

기존 `backend/app/` 테이블:
- stocks, stock_prices, technical_indicators, auto_trade_snapshots 등

신규 `cloud_server/` 테이블:
- users (확장: is_active, last_login_at)
- refresh_tokens, email_verification_tokens, password_reset_tokens
- trading_rules
- heartbeats
- stock_master, daily_bars, minute_bars
- strategy_templates
- kiwoom_service_keys

### 실행 명령

```bash
# cloud_server 실행 (포트 8001)
python -m uvicorn cloud_server.main:app --reload --port 8001

# DB 초기화 (첫 실행 시 자동, 수동 실행도 가능)
python -m cloud_server.core.init_db
```

### 미완료 항목

- [ ] `backend/app/`의 yfinance 기반 stocks API 이전 (Phase 3 범위 외)
- [ ] Alembic 마이그레이션 스크립트 (현재 create_all 방식)
- [ ] PostgreSQL 전환 테스트 (DATABASE_URL 환경변수로 제어)
