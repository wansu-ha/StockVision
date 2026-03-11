# Step 2: 서버 자동 로그인 + 하트비트 JWT 인증 + 401 자동갱신

## 변경 파일

| 파일 | 변경 |
|------|------|
| `local_server/main.py` | lifespan에 `_restore_active_user` + 자동 refresh 단계 삽입 (하트비트 시작 전) |
| `local_server/cloud/heartbeat.py` | `_client` 싱글턴 + `get_cloud_client()`, 시작 시 토큰 로드→CloudClient 전달, 401→`_try_refresh()` 분기, `_try_refresh()` 신규 함수 (`_refresh_lock` 공유) |

## 검증 결과

- `_try_refresh` 4케이스 통과: success, already_fresh, no_rt, fail
- main.py import 정상
- heartbeat.py 구조 검증 (get_cloud_client, _try_refresh 코루틴)
- 기존 테스트 영향 없음 (키움 기존 실패 4건은 Step 2 무관)
