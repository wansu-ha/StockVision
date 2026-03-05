# Step 4 보고서: 하트비트 수신 + 버전 체크 API

> 완료일: 2026-03-05

## 구현 내용

### 생성된 파일

| 파일 | 설명 |
|------|------|
| `cloud_server/models/heartbeat.py` | Heartbeat 모델 |
| `cloud_server/services/heartbeat_service.py` | 하트비트 비즈니스 로직 |
| `cloud_server/api/heartbeat.py` | 하트비트 API |
| `cloud_server/api/version.py` | 버전 체크 API |

### API 엔드포인트

**POST /api/v1/heartbeat** (JWT 인증):
```json
요청: {"uuid": "abc", "version": "1.0.0", "kiwoom_connected": true, "timestamp": "..."}
응답: {"success": true, "data": {"rules_version": 3, "context_version": 1, "timestamp": "..."}}
```

**GET /api/v1/version** (인증 불필요):
```json
응답: {"success": true, "data": {"latest": "1.0.0", "min_supported": "1.0.0", "download_url": "..."}}
```

### 로컬 서버 동기화 흐름

1. 로컬 서버 → POST /api/v1/heartbeat (30초~1분 주기)
2. 응답에서 rules_version 확인
3. 로컬 캐시 버전과 다르면 GET /api/v1/rules 호출
4. context_version 다르면 GET /api/v1/context 호출

## 검증 결과

- [x] Heartbeat 모델 (uuid, user_id, engine_running, active_rules_count)
- [x] rules_version: 사용자 TradingRule의 max(version) 계산
- [x] context_version: v1 고정 (Step 9 확장 예정)
- [x] 버전 체크 API (공개, 인증 불필요)
