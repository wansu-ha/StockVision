# Step 1 보고서: 프로젝트 구조 + FastAPI 앱 + DB 설정

> 완료일: 2026-03-05

## 구현 내용

### 생성된 파일

| 파일 | 설명 |
|------|------|
| `cloud_server/__init__.py` | 패키지 초기화 |
| `cloud_server/main.py` | FastAPI 앱 진입점 (lifespan, CORS, 라우터) |
| `cloud_server/core/config.py` | 환경 변수 설정 (Settings 클래스) |
| `cloud_server/core/database.py` | SQLAlchemy 세션 설정 (SQLite/PostgreSQL 멀티 환경) |
| `cloud_server/core/init_db.py` | 테이블 생성 (Base.metadata.create_all) |
| `cloud_server/core/security.py` | JWT, Argon2id, 토큰 유틸 |
| `cloud_server/core/encryption.py` | AES-256-GCM 암호화 |
| `cloud_server/core/email.py` | SMTP 이메일 발송 |
| `cloud_server/core/rate_limit.py` | in-memory Rate Limiter |
| `cloud_server/core/validators.py` | 조건 JSON 검증 |
| `cloud_server/core/broker_factory.py` | BrokerAdapter 팩토리 |
| `cloud_server/requirements.txt` | 의존성 목록 |
| 각 서브패키지 `__init__.py` | api/, services/, collector/, models/, core/ |

### 설계 결정

1. **lifespan 방식**: `@app.on_event("startup")` deprecated → `asynccontextmanager` lifespan 사용
2. **DB 전환**: SQLite(개발)↔PostgreSQL(운영)을 `DATABASE_URL` 환경변수로 제어
3. **CORS**: 환경변수로 오리진 관리 (settings.CORS_ORIGINS)
4. **미들웨어**: 요청 로깅 미들웨어 (trace_id 포함), 헬스체크/버전 경로 제외

## 검증 결과

- [x] 디렉토리 구조 생성 완료
- [x] FastAPI 앱 설정 완료
- [x] DB 설정 완료 (SQLite/PostgreSQL 멀티 환경)
- [x] `GET /health` 엔드포인트 구현
- [x] 스케줄러 lifespan 통합
