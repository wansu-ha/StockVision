# Step 1: _active_user 영속화 + token_utils + CloudClient 토큰 동적 관리

## 변경 파일

| 파일 | 변경 |
|------|------|
| `local_server/storage/credential.py` | `set_active_user()` — config.json에 `auth.last_user` 저장 추가. `_restore_active_user()` 신규 (메모리만, config 미저장) |
| `local_server/cloud/token_utils.py` | **신규** — `_refresh_lock` (asyncio.Lock), `is_jwt_expired()` (60초 leeway) |
| `local_server/cloud/client.py` | `CloudClientError.status_code` 추가, `self._api_token` 인스턴스 변수화, `set_token()`, `clear_token()`, `refresh_access_token()` 추가, `_get()`/`_post()` HTTPStatusError에서 status_code 보존 |

## 검증 결과

- token_utils: Lock 타입, 만료/유효/leeway/잘못된 토큰 5개 케이스 통과
- CloudClient: status_code 전파, set_token/clear_token 상태 변경, 생성자 토큰 전달 통과
- credential: set_active_user→config 저장, _restore_active_user→메모리만 변경 통과
- 기존 테스트: 34 중 33 통과 (1 실패는 기존 키움 balance 파싱 버그, Step 1 무관)
- 프론트엔드 빌드: 정상
