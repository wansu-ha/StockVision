# JWT 자동갱신 + 프론트엔드 자동 로그인 구현 계획

> 작성일: 2026-03-11 | 상태: 구현 완료 | spec: `spec/jwt-offline-resilience/spec.md`

---

## Step 1: `_active_user` 영속화 + CloudClient 강화

**목표**: 재부팅 후에도 keyring 네임스페이스가 복원되고, CloudClient가 토큰을 동적 갱신할 수 있게 한다.

### 1a. `_active_user` 영속화

**파일**: `local_server/storage/credential.py`

**현재 코드** (line 24-28):
```python
def set_active_user(user_id: str) -> None:
    global _active_user
    _active_user = user_id
    logger.info("활성 사용자 설정: %s", user_id)
```

**변경**:
1. `set_active_user()` — config.json에 `auth.last_user` 저장 추가
2. `_restore_active_user(user_id)` 신규 — 서버 시작 시 config에서 복원 (config 재저장 안 함, 메모리만)

```python
def set_active_user(user_id: str) -> None:
    global _active_user
    _active_user = user_id
    from local_server.config import get_config
    cfg = get_config()
    cfg.set("auth.last_user", user_id)
    cfg.save()
    logger.info("활성 사용자 설정: %s", user_id)


def _restore_active_user(user_id: str) -> None:
    """서버 시작 시 config에서 복원 — config 재저장 안 함."""
    global _active_user
    _active_user = user_id
    logger.info("활성 사용자 복원: %s", user_id)
```

### 1b. `_refresh_lock` + `_is_jwt_expired` — 공유 유틸리티

**파일**: `local_server/cloud/token_utils.py` (**신규**)

auth.py와 heartbeat.py 양쪽에서 사용하므로, 순환 import를 피하기 위해 별도 모듈로 추출.

```python
"""토큰 갱신 공유 유틸리티.

_refresh_lock: restore_session과 heartbeat _try_refresh가 공유하여 Token Rotation 경쟁 방지.
_is_jwt_expired: JWT exp 클레임 확인 (60초 leeway).
"""
import asyncio
import base64
import json
import time

_refresh_lock = asyncio.Lock()


def is_jwt_expired(token: str, leeway: int = 60) -> bool:
    """JWT exp 클레임으로 만료 여부 확인. leeway초 여유를 둔다. 파싱 실패 시 만료로 간주."""
    try:
        payload_b64 = token.split(".")[1]
        payload_b64 += "=" * (4 - len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        return payload.get("exp", 0) < (time.time() + leeway)
    except Exception:
        return True
```

### 1c. CloudClient 토큰 관리

**파일**: `local_server/cloud/client.py`

**현재 코드 문제점**:
- `CloudClientError`에 `status_code` 필드 없음 → 401 분기 불가
- 생성자에서 토큰 1회 설정 → 이후 갱신 불가
- `_get()`, `_post()`에서 `HTTPStatusError` 시 status_code 유실

**변경**:

1. `CloudClientError.__init__`에 `status_code: int | None = None` 추가
```python
class CloudClientError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code
```

2. `_get()`, `_post()` — `HTTPStatusError` catch에서 `status_code` 보존
```python
except httpx.HTTPStatusError as e:
    raise CloudClientError(
        f"HTTP 오류 {e.response.status_code} ({url}): {e.response.text}",
        status_code=e.response.status_code,
    ) from e
```

3. `set_token(token)` — 런타임 토큰 교체
```python
def set_token(self, token: str) -> None:
    self._api_token = token
    self._headers["Authorization"] = f"Bearer {token}"
```
> 참고: 생성자에서 `_api_token`은 지역변수로만 사용되지만, `set_token()`이 추가되면
> 일관성을 위해 `__init__`에서도 `self._api_token = api_token`으로 인스턴스 변수화한다.

4. `clear_token()` — 인증 헤더 제거
```python
def clear_token(self) -> None:
    self._api_token = None
    self._headers.pop("Authorization", None)
```

5. `refresh_access_token(refresh_token)` — 클라우드 refresh 호출
```python
async def refresh_access_token(self, refresh_token: str) -> dict:
    result = await self._post("/api/v1/auth/refresh", {"refresh_token": refresh_token})
    return result.get("data", result)
```

**검증**:
- [ ] `set_active_user("test@example.com")` → config.json `auth.last_user` 확인
- [ ] 서버 재시작 후 `get_active_user()` == `"test@example.com"` (main.py에서 _restore 호출 전제)
- [ ] `CloudClientError.status_code == 401` 정확히 설정
- [ ] `set_token()` 후 다음 요청에 새 토큰 반영
- [ ] `refresh_access_token()` 정상 응답 반환

---

## Step 2: 서버 시작 시 자동 로그인 + 하트비트 JWT 통합

**목표**: PC 재부팅 후 자동으로 인증 상태를 복원하고, 하트비트가 인증된 상태로 동작한다.

### 2a. main.py 자동 로그인

**파일**: `local_server/main.py`

lifespan에서 하트비트 시작 전 (line 65 근처), `_migrate_token_dat()` 이후에 삽입:

```python
# 활성 사용자 복원 + 자동 로그인
from local_server.storage.credential import _restore_active_user, load_cloud_tokens, save_cloud_tokens
last_user = cfg.get("auth.last_user")
if last_user:
    _restore_active_user(last_user)
    logger.info("활성 사용자 복원: %s", last_user)

access_token, refresh_token = load_cloud_tokens()
if not access_token and refresh_token:
    # access_token 없고 refresh_token 있으면 → refresh 시도
    cloud_url = cfg.get("cloud.url", "")
    if cloud_url:
        try:
            from local_server.cloud.client import CloudClient
            temp = CloudClient(base_url=cloud_url)
            tokens = await temp.refresh_access_token(refresh_token)
            save_cloud_tokens(tokens["access_token"], tokens["refresh_token"])
            access_token = tokens["access_token"]
            logger.info("서버 시작 시 토큰 자동 갱신 완료")
        except Exception as e:
            logger.warning("서버 시작 시 토큰 자동 갱신 실패 (수동 로그인 필요): %s", e)
```

### 2b. 하트비트 JWT + 401 자동갱신

**파일**: `local_server/cloud/heartbeat.py`

**현재 코드 문제** (line 73):
```python
client = CloudClient(base_url=cloud_url)  # api_token 없음 → 모든 하트비트 401
```

**변경**:

1. 모듈 레벨 `_client` + `get_cloud_client()` 추가
```python
_client: CloudClient | None = None

def get_cloud_client() -> CloudClient | None:
    return _client
```

2. `start_heartbeat()` 시작 시 토큰 로드 + CloudClient에 전달
```python
async def start_heartbeat() -> None:
    global _client
    cfg = get_config()
    cloud_url = cfg.get("cloud.url", "")
    interval = cfg.get("cloud.heartbeat_interval", 30)
    if not cloud_url:
        logger.warning("cloud.url이 설정되지 않아 하트비트를 시작할 수 없습니다.")
        return

    from local_server.storage.credential import load_cloud_tokens
    access_token, _ = load_cloud_tokens()
    _client = CloudClient(base_url=cloud_url, api_token=access_token)
    # ... 나머지 루프 ...
```

3. 하트비트 루프에서 401 분기 + `_try_refresh()` — `_refresh_lock` 공유 (spec §3.6)
```python
except CloudClientError as e:
    if e.status_code == 401:
        refreshed = await _try_refresh(_client)
        if refreshed:
            consecutive_failures = 0
            continue  # 갱신 후 즉시 재시도
    consecutive_failures += 1
    # ... 기존 실패 처리 ...
```

4. `_try_refresh()` — `token_utils`에서 `_refresh_lock`, `is_jwt_expired` import (순환 import 방지)
```python
async def _try_refresh(client: CloudClient) -> bool:
    from local_server.cloud.token_utils import _refresh_lock, is_jwt_expired
    from local_server.storage.credential import load_cloud_tokens, save_cloud_tokens
    async with _refresh_lock:
        access_token, refresh_token = load_cloud_tokens()
        if access_token and not is_jwt_expired(access_token):
            client.set_token(access_token)
            return True
        if not refresh_token:
            return False
        try:
            tokens = await client.refresh_access_token(refresh_token)
            client.set_token(tokens["access_token"])
            save_cloud_tokens(tokens["access_token"], tokens["refresh_token"])
            return True
        except CloudClientError:
            _update_tray("error")
            _send_toast("StockVision", "재로그인이 필요합니다.")
            return False
```

**검증**:
- [ ] 서버 시작 → config에서 last_user 복원 → keyring에서 토큰 로드
- [ ] 하트비트 Authorization 헤더 포함
- [ ] 401 → `_refresh_lock` 하에 refresh → 새 토큰으로 재시도 성공
- [ ] refresh 실패 → 트레이 🔴
- [ ] 갱신된 토큰이 keyring에 저장됨

---

## Step 3: `POST /api/auth/restore` + 런타임 로그인 반영

**목표**: 프론트엔드가 로컬 서버에서 세션을 복원할 수 있고, 런타임 로그인이 heartbeat에 반영된다.

### 3a. `POST /api/auth/restore` 신규

**파일**: `local_server/routers/auth.py`

추가 import:
```python
from local_server.storage.credential import (
    # ... 기존 ...
    get_active_user,
    load_cloud_tokens,
)
from local_server.config import get_config
from local_server.cloud.heartbeat import get_cloud_client
from local_server.cloud.token_utils import _refresh_lock, is_jwt_expired
```

> `_refresh_lock`은 `token_utils.py`에 정의 (Step 1b). auth.py와 heartbeat.py 양쪽에서 import하여 공유.
> `is_jwt_expired`도 동일. auth.py에 별도 정의하지 않음.

```python
@router.post("/restore", summary="저장된 토큰으로 세션 복원")
async def restore_session(request: Request) -> dict[str, Any]:
    access_token, refresh_token = load_cloud_tokens()
    if not refresh_token:
        raise HTTPException(status_code=404, detail="저장된 토큰 없음")

    if access_token and is_jwt_expired(access_token):
        access_token = None

    if not access_token:
        async with _refresh_lock:
            # Lock 내부에서 다시 확인 — 선행 요청이 이미 refresh했을 수 있음
            access_token, refresh_token = load_cloud_tokens()
            if not refresh_token:
                raise HTTPException(status_code=404, detail="저장된 토큰 없음")
            if not access_token or is_jwt_expired(access_token):
                try:
                    from local_server.cloud.client import CloudClient
                    cloud_url = get_config().get("cloud.url")
                    temp = CloudClient(base_url=cloud_url)
                    tokens = await temp.refresh_access_token(refresh_token)
                    access_token = tokens["access_token"]
                    refresh_token = tokens["refresh_token"]
                    save_cloud_tokens(access_token, refresh_token)
                    cc = get_cloud_client()
                    if cc:
                        cc.set_token(access_token)
                except Exception:
                    raise HTTPException(status_code=401, detail="토큰 갱신 실패. 재로그인 필요.")

    email = get_active_user()
    return {
        "success": True,
        "data": {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "email": email if email != "default" else None,
            "local_secret": request.app.state.local_secret,
        },
    }
```

### 3b. `GET /api/auth/status` 확장

**현재 코드** (line 93-107): `has_cloud_token` bool 1개만 반환.

**변경**: `has_refresh_token` + `email` 추가.

```python
@router.get("/status", summary="인증 상태 확인")
async def auth_status() -> dict[str, Any]:
    access_token, refresh_token = load_cloud_tokens()
    email = get_active_user()
    return {
        "success": True,
        "data": {
            "has_cloud_token": bool(access_token),
            "has_refresh_token": bool(refresh_token),
            "email": email if email != "default" else None,
        },
    }
```

### 3c. `register_cloud_token` → heartbeat 반영

**현재 코드** (line 64): `save_cloud_tokens()` 후 끝.

**변경**: heartbeat의 CloudClient에도 새 토큰 반영.
```python
save_cloud_tokens(body.access_token, body.refresh_token)
# heartbeat에도 반영
cc = get_cloud_client()
if cc:
    cc.set_token(body.access_token)
```

**검증**:
- [ ] `POST /api/auth/restore` → 유효 토큰 + local_secret 반환
- [ ] 만료된 access_token → `_refresh_lock` 하에 refresh 후 새 토큰 반환
- [ ] 토큰 없을 때 → 404
- [ ] `GET /api/auth/status` → 토큰 미포함, 유무+이메일만
- [ ] 런타임 로그인 → heartbeat 다음 사이클 인증 성공

---

## Step 4: 프론트엔드 세션 복원 + 401 로컬 서버 우선

**목표**: 브라우저 토큰이 없어도 로컬 서버에서 세션 복원. 401 시 로컬 서버 우선 refresh.

### 4a. `localClient.ts` — `localAuth.restore()` 추가

**파일**: `frontend/src/services/localClient.ts`

`localAuth` 객체에 추가:
```typescript
restore: async () => {
  try {
    const res = await client.post('/auth/restore')
    // local_secret 필수 저장 — 이후 mutation API X-Local-Secret 헤더에 사용
    localSecret = res.data?.data?.local_secret ?? null
    return res.data
  } catch {
    return null
  }
},
```

### 4b. `AuthContext.tsx` — 마운트 시 로컬 서버 복원

**파일**: `frontend/src/context/AuthContext.tsx`

**현재 코드** (line 35-65): `jwt && rt` → 로컬 전달, `rt` → 클라우드 refresh, 그 외 → 아무것도 안 함.

**변경**: else 분기에 `localAuth.restore()` 추가. 실패 시에도 `localReady: true` 설정.

```typescript
useEffect(() => {
  const jwt = sessionStorage.getItem(STORAGE_KEY_JWT)
  const rt = localStorage.getItem(STORAGE_KEY_RT)

  if (jwt && rt) {
    localAuth.setAuthToken(jwt, rt).then(() => {
      setState(prev => ({ ...prev, localReady: true }))
    })
  } else if (rt) {
    // 기존 코드 유지 (클라우드 refresh)
    cloudAuth.refresh(rt)
      .then(async (res) => {
        const d = res.data
        sessionStorage.setItem(STORAGE_KEY_JWT, d.access_token)
        localStorage.setItem(STORAGE_KEY_RT, d.refresh_token)
        await localAuth.setAuthToken(d.access_token, d.refresh_token)
        setState({
          jwt: d.access_token, refreshToken: d.refresh_token,
          email: localStorage.getItem(STORAGE_KEY_EMAIL),
          isAuthenticated: true, localReady: true,
        })
      })
      .catch(() => {
        localStorage.removeItem(STORAGE_KEY_RT)
        localStorage.removeItem(STORAGE_KEY_EMAIL)
        // 실패해도 localReady 설정하여 블로킹 해제
        setState(prev => ({ ...prev, localReady: true }))
      })
  } else {
    // 신규: 브라우저에 토큰 없음 → 로컬 서버에서 복원
    localAuth.restore().then((res) => {
      const d = res?.data
      if (d?.access_token && d?.refresh_token) {
        sessionStorage.setItem(STORAGE_KEY_JWT, d.access_token)
        localStorage.setItem(STORAGE_KEY_RT, d.refresh_token)
        if (d.email) localStorage.setItem(STORAGE_KEY_EMAIL, d.email)
        setState({
          jwt: d.access_token, refreshToken: d.refresh_token,
          email: d.email ?? null, isAuthenticated: true, localReady: true,
        })
      } else {
        // 로컬 서버 다운 or 토큰 없음 → 미인증, localReady true로 블로킹 해제
        setState(prev => ({ ...prev, localReady: true }))
      }
    })
  }
}, [])
```

### 4c. `cloudClient.ts` — 401 인터셉터 변경

**파일**: `frontend/src/services/cloudClient.ts`

**추가 import**:
```typescript
import { localAuth } from './localClient'
```

**현재 401 인터셉터** (line 27-54): 클라우드 직접 refresh.

**변경**: 로컬 서버 우선 → 클라우드 폴백.

```typescript
client.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true

      // 1단계: 로컬 서버에서 최신 토큰 요청
      try {
        const restored = await localAuth.restore()
        if (restored?.data?.access_token) {
          sessionStorage.setItem(JWT_KEY, restored.data.access_token)
          localStorage.setItem(RT_KEY, restored.data.refresh_token)
          original.headers.Authorization = `Bearer ${restored.data.access_token}`
          return client(original)
        }
      } catch { /* 로컬 서버 다운 — 폴백 진행 */ }

      // 2단계: 폴백 — 클라우드 직접 refresh
      const rt = localStorage.getItem(RT_KEY)
      if (rt) {
        try {
          const { data } = await axios.post(`${CLOUD_URL}/api/v1/auth/refresh`, { refresh_token: rt })
          const newJwt = data.data?.access_token ?? data.access_token
          const newRt = data.data?.refresh_token ?? data.refresh_token
          if (!newJwt || !newRt) throw new Error('Invalid refresh response')
          sessionStorage.setItem(JWT_KEY, newJwt)
          localStorage.setItem(RT_KEY, newRt)
          // 로컬 서버에도 전달 (가능하면)
          localAuth.setAuthToken(newJwt, newRt).catch(() => {})
          original.headers.Authorization = `Bearer ${newJwt}`
          return client(original)
        } catch {
          sessionStorage.removeItem(JWT_KEY)
          localStorage.removeItem(RT_KEY)
          window.location.href = '/login'
        }
      }
    }
    return Promise.reject(error)
  },
)
```

**검증**:
- [ ] 브라우저 캐시 삭제 → 페이지 열기 → 로컬 서버에서 자동 로그인
- [ ] 로컬 서버 다운 + 브라우저 토큰 없음 → /login 리다이렉트
- [ ] 401 발생 → 로컬 서버 우선 → 성공 시 재시도
- [ ] 로컬 서버 다운 시 401 → 클라우드 직접 refresh 폴백
- [ ] 새 브라우저/시크릿 모드에서도 자동 로그인 (로컬 서버 실행 중이면)
- [ ] restore 실패 시 localReady: true 설정 → 대시보드 쿼리 블로킹 안 됨

---

## 의존성

```
Step 1 (credential + token_utils + CloudClient)
  ↓
Step 2 (main.py + heartbeat) ← Step 1 필요 (token_utils의 _refresh_lock, is_jwt_expired 포함)
  ↓
Step 3 (auth.py restore + heartbeat 반영) ← Step 1 필요 (token_utils에서 import)
  ↓
Step 4 (프론트엔드) ← Step 3 필요 (restore API)
```

> Step 2와 3은 모두 Step 1의 `token_utils.py`에 의존.
> `_refresh_lock`과 `is_jwt_expired`가 token_utils에 있으므로 순환 import 없음.
> Step 2, 3은 독립적이지만 순서대로 진행.

**실행 순서**: 1 → 2 → 3 → 4

---

## 수정 대상 파일

| 파일 | Step | 변경 |
|------|------|------|
| `local_server/cloud/token_utils.py` | 1 | **신규** — `_refresh_lock`, `is_jwt_expired` |
| `local_server/storage/credential.py` | 1 | `set_active_user` 영속화, `_restore_active_user` 추가 |
| `local_server/cloud/client.py` | 1 | `status_code`, `set_token`, `clear_token`, `refresh_access_token` |
| `local_server/main.py` | 2 | lifespan에 자동 로그인 단계 |
| `local_server/cloud/heartbeat.py` | 2 | 토큰 로드, `get_cloud_client`, 401→refresh |
| `local_server/routers/auth.py` | 3 | `POST /restore`, `GET /status` 확장, `register_cloud_token` heartbeat 반영 |
| `frontend/src/services/localClient.ts` | 4 | `localAuth.restore()` 추가 |
| `frontend/src/context/AuthContext.tsx` | 4 | 마운트 시 로컬 서버 restore |
| `frontend/src/services/cloudClient.ts` | 4 | 401 인터셉터 로컬 우선 + `localAuth` import |

---

## 커밋 계획

| Step | 커밋 메시지 |
|------|-----------|
| 1 | `feat: _active_user 영속화 + token_utils + CloudClient 토큰 동적 관리` |
| 2 | `feat: 서버 자동 로그인 + 하트비트 JWT 인증 + 401 자동갱신` |
| 3 | `feat: POST /auth/restore + 런타임 로그인 heartbeat 반영` |
| 4 | `feat: 프론트엔드 로컬 서버 세션 복원 + 401 로컬 우선 refresh` |
