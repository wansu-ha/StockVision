# Step 3: POST /auth/restore + 런타임 로그인 heartbeat 반영

## 변경 파일

| 파일 | 변경 |
|------|------|
| `local_server/routers/auth.py` | `POST /restore` 신규 (세션 복원, 만료 시 refresh, _refresh_lock 공유), `GET /status` 확장 (has_refresh_token, email 추가, 토큰 미노출), `register_cloud_token`에서 heartbeat CloudClient에 set_token 반영, import 추가 (get_active_user, load_cloud_tokens) |

## 검증 결과

- `POST /restore`: valid token → 200, no token → 404, expired+refresh → 200 (3케이스)
- `GET /status`: authenticated → has_cloud_token+email, unauthenticated → null (2케이스)
- 토큰 미노출 확인 (status 응답에 access_token/refresh_token 키 없음)
- register_cloud_token → heartbeat 반영 로직 추가
