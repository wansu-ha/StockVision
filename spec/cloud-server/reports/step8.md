# Step 8 보고서: 어드민 API

> 완료일: 2026-03-05

## 구현 내용

### 생성된 파일

| 파일 | 설명 |
|------|------|
| `cloud_server/models/template.py` | StrategyTemplate, KiwoomServiceKey |
| `cloud_server/services/admin_service.py` | 어드민 비즈니스 로직 |
| `cloud_server/api/admin.py` | 어드민 API 라우터 |

### API 엔드포인트 (/api/v1/admin/)

| 경로 | 메서드 | 설명 |
|------|--------|------|
| `/stats` | GET | 시스템 통계 |
| `/users` | GET | 유저 목록 |
| `/users/{id}` | PATCH | 유저 활성/비활성 전환 |
| `/service-keys` | GET | 서비스 키 목록 (secret 마스킹) |
| `/service-keys` | POST | 서비스 키 등록 |
| `/service-keys/{id}` | DELETE | 서비스 키 삭제 |
| `/templates` | GET/POST | 전략 템플릿 목록/생성 |
| `/templates/{id}` | PUT/DELETE | 전략 템플릿 수정/삭제 |
| `/collector-status` | GET | 수집기 상태 |
| `/quotes/{symbol}/daily` | GET | 일봉 조회 (어드민 전용) |
| `/quotes/{symbol}/latest` | GET | 최신 시세 (어드민 전용) |

### 보안

- `require_admin` 의존성: JWT role == "admin" 필수, 아니면 403
- 시세 조회 API: 어드민 전용 (제5조③ 시세 중계 금지 준수)

### 서비스 키 보안

- api_secret: AES-256-GCM 암호화 후 hex로 저장
- 목록 조회 시 api_secret은 "***"로 마스킹

## 검증 결과

- [x] role=admin 권한 검증 (403 응답)
- [x] 통계 API (유저 수, 규칙 수, 활성 클라이언트)
- [x] 서비스 키 암호화 저장
- [x] 수집기 상태 조회
- [x] 어드민 전용 시세 API (일반 유저 접근 불가)
