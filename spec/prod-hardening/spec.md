# 프로덕션 하드닝 v2 명세서

> 작성일: 2026-03-24 | 상태: 초안 | 선행: `spec/pre-deploy-hardening/` (완료)

---

## 1. 배경

`pre-deploy-hardening` (M1~M5) 완료 후 T1/T2 구현으로 새로 생긴 갭:

| 항목 | 현황 | 위험도 |
|------|------|--------|
| Alembic 미생성 테이블 4개 | create_all()로만 생성, Alembic 히스토리 없음 | 🔴 높음 |
| 로그 레벨 환경변수 없음 | 운영 로그 레벨 조정 불가 | 🟡 중간 |
| 로그 포맷 미통일 | 운영 로그 분석 어려움 | 🟡 중간 |
| 백업 정책 미문서화 | 장애 시 복구 절차 불명확 | 🟡 중간 |

---

## 2. H1 — Alembic 마이그레이션 (신규 테이블 4개)

### 문제

T2 구현으로 추가된 테이블 4개가 Alembic 히스토리에 없음:

| 테이블 | 모델 | 추가 시점 |
|--------|------|----------|
| `pending_commands` | `PendingCommand` | T2 relay-infra |
| `audit_logs` | `AuditLog` | T2 relay-infra |
| `oauth_accounts` | `OAuthAccount` | T2 auth-extension (v2 미활성) |
| `devices` | `Device` | T2 auth-extension (v2 미활성) |

**현재 동작**: `init_db()`의 `create_all()`이 서버 시작 시 테이블을 자동 생성 → 운영 DB에도 존재.

**문제**: `alembic upgrade head` 기반 배포로 전환하거나, 이후 `alembic revision --autogenerate` 실행 시 스키마 불일치.

### 해결

`alembic revision --autogenerate`로 현재 상태를 캡처하여 히스토리 동기화.

#### Step 1: autogenerate 실행

```bash
# 프로젝트 루트에서
source .venv/Scripts/activate
alembic revision --autogenerate -m "add_t2_relay_and_auth_extension_tables"
```

#### Step 2: 생성된 마이그레이션 스크립트 검토

```
cloud_server/alembic/versions/{hash}_add_t2_relay_and_auth_extension_tables.py
```

- `upgrade()`: CREATE TABLE 4개 포함 확인
- `downgrade()`: DROP TABLE 4개 포함 확인
- 기존 테이블 수정 없음 확인

#### Step 3: 개발 환경 검증

```bash
# SQLite로 마이그레이션 적용 테스트
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

#### Step 4: 운영 DB 적용

```bash
# Render PostgreSQL에 적용 (DATABASE_URL 필요)
DATABASE_URL=<render_db_url> alembic upgrade head
```

### 수용 기준

- [ ] `alembic upgrade head` → 4개 테이블 생성 (기존 미존재 시)
- [ ] `alembic downgrade -1` → 4개 테이블 삭제
- [ ] 기존 운영 DB에서 `alembic current` → 최신 revision

---

## 3. H2 — 로그 레벨 환경변수

### 문제

`cloud_server/main.py`에 `logging.basicConfig()` 없음.
uvicorn의 기본 로깅에 의존 → 운영 로그 레벨을 환경변수로 조정 불가.

### 해결

`main.py` 상단에 로그 레벨 설정 추가:

```python
# main.py 상단 (FastAPI app 생성 전)
import logging
import os

_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, _LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
```

**변경 파일**: `cloud_server/main.py`

**Render env var 추가**:
```
LOG_LEVEL=INFO
```

### 수용 기준

- [ ] `LOG_LEVEL=DEBUG` 설정 시 DEBUG 로그 출력
- [ ] `LOG_LEVEL` 미설정 시 INFO 기본값 동작
- [ ] Render 로그에 타임스탬프 포함 출력

---

## 4. H3 — 백업 정책 확인 및 문서화

### Render PostgreSQL 백업 현황

- **Starter 플랜**: 자동 백업 없음 (수동만)
- **Standard 이상**: 일일 자동 백업, 7일 보관

현재 플랜 확인 후:
- Starter → Standard 업그레이드 검토 (또는 수동 백업 스크립트)
- Standard → 일일 자동 백업으로 충분

### 수동 백업 절차 (Alembic 실행 전 필수)

```bash
# Render DB 백업 생성
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql
```

또는 Render 대시보드: PostgreSQL → Backups → Create Backup

### 수용 기준

- [ ] 현재 Render 플랜 + 백업 정책 확인
- [ ] Alembic 마이그레이션 전 수동 백업 1회 실행

---

## 5. 작업 순서

```
H1 (Alembic) — 최우선
  1. autogenerate 로컬 실행 → 스크립트 검토
  2. 개발 SQLite로 검증
  3. 운영 DB 적용 전 수동 백업 (H3)
  4. 운영 DB에 upgrade head

H2 (로그) — H1 이후 묶어서
  5. main.py basicConfig 추가
  6. Render env var LOG_LEVEL=INFO 추가
  7. 배포 후 로그 포맷 확인

H3 (백업) — H1 전제
  8. Render 플랜 확인
  9. H1 운영 적용 전 백업
```

---

## 6. 범위 외

| 항목 | 사유 |
|------|------|
| Sentry / 외부 모니터링 | v2 이후 (비용/복잡도) |
| 커넥션 풀 튜닝 | 단일 프로세스, Render 기본으로 충분 |
| Redis 백업 | AI 캐시 + Rate limit용 — 휘발성 데이터, 백업 불필요 |
| HTTPS 강제 미들웨어 | Render 프록시가 SSL 처리, FastAPI에 추가 불필요 |
