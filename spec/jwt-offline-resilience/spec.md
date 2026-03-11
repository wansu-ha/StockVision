# JWT 자동갱신 + 프론트엔드 자동 로그인

> 작성일: 2026-03-11 | 상태: 구현 완료 | Unit 2 (로컬 서버 코어) 잔여분

---

## 1. 개요

**원칙: 로컬 서버와 프론트엔드의 인증 상태는 항상 동기화되어야 한다.**

로컬 서버 keyring에 유효한 토큰이 남아있다면:
- 로컬 서버는 클라우드와 인증된 통신을 유지한다 (하트비트, 규칙 fetch 등)
- 프론트엔드는 별도 로그인 없이 세션을 복원한다
- PC 재부팅 후에도 동일하게 동작한다

현재 상태:
- `_active_user`가 메모리 변수 → 재부팅 시 `"default"`로 리셋 → keyring 네임스페이스 불일치
- 하트비트가 **토큰 없이** 요청 → 클라우드 서버 인증 필수(`Depends(current_user)`)이므로 **모든 하트비트가 401로 실패 중**
- 401 시 refresh 로직 없음
- 프론트엔드가 로컬 서버의 토큰 유무를 확인하지 않음 (자기 localStorage만 봄)
- `SyncQueue` 구현됨, 호출부 없음 (오프라인 내성 불필요 — §2 제외 참조)

## 2. 범위

### A 파트: JWT 자동갱신 + 인증 동기화

| ID | 기능 | 우선순위 |
|----|------|---------|
| A1 | `_active_user` 영속화 — config.json에 저장, 재부팅 시 복원 | P0 |
| A2 | 하트비트에 JWT Authorization 헤더 포함 | P0 |
| A3 | 401 응답 시 refresh_token으로 자동 갱신 + 재시도 | P0 |
| A4 | 갱신된 토큰 쌍을 keyring에 저장 (Token Rotation) | P0 |
| A5 | 서버 시작 시 refresh_token으로 자동 로그인 | P0 |
| A6 | refresh_token 만료/무효 → "재로그인 필요" 상태 전환 | P0 |
| A7 | 런타임 로그인 시 heartbeat CloudClient에도 토큰 반영 | P0 |
| A8 | `POST /api/auth/restore` — 세션 복원 엔드포인트 (토큰 + local_secret 반환) | P0 |
| A9 | 프론트엔드: 로컬 서버 우선 refresh + 세션 복원 | P0 |

### 제외
- PyInstaller 빌드 (별도 spec)
- 오프라인 내성 — 프론트엔드가 클라우드에 정적 호스팅되므로 클라우드 다운 시 SPA 자체 로딩 불가. 전략 엔진은 캐시된 규칙으로 독립 동작. 오프라인 UI가 불필요하므로 SyncQueue flush도 불필요.

## 3. 보안 모델

### 3.1 기존 local_secret 체계

로컬 서버는 시작 시 `local_secret`(32바이트 hex)을 1회 생성, 메모리에만 보관.
- `POST /api/auth/token` — 인증 없이 호출 가능 (bootstrap). 응답에 `local_secret` 포함.
- 이후 mutation API — `X-Local-Secret` 헤더 필수 (`require_local_secret`).
- `GET /api/auth/status` — 인증 없이 호출 가능 (읽기 전용).

### 3.2 토큰 노출 방지

**원칙**: raw 토큰(access_token, refresh_token)은 GET 엔드포인트로 노출하지 않는다.

`GET /api/auth/status`는 인증 없이 접근 가능하므로, 여기에 토큰을 넣으면
같은 PC의 다른 프로세스가 `curl http://127.0.0.1:4020/api/auth/status`로 탈취 가능.
(CORS는 브라우저 정책 — 비브라우저 프로세스는 우회)

**해결**: 토큰 반환은 `POST /api/auth/restore` 별도 엔드포인트로 분리.
`local_secret`을 함께 반환하여 기존 `POST /api/auth/token`과 동일한 보안 수준 유지.

```
GET  /api/auth/status  → { has_cloud_token, has_refresh_token, email } (토큰 미포함)
POST /api/auth/restore → { access_token, refresh_token, email, local_secret } (bootstrap 동등)
```

`/auth/restore`도 인증 없이 호출 가능하며, 인증 요구사항은 `/auth/token`과 동일하다.
단, 위협 성격은 다르다:
- `/auth/token`은 **등록** — 호출자가 이미 토큰을 가지고 있어야 함. 공격자에게 도움 안 됨.
- `/auth/restore`는 **열람** — keyring에서 토큰을 꺼내 반환. 같은 PC의 악성 프로세스가 호출하면 refresh_token 탈취 가능.

이 위험은 127.0.0.1 바인딩 + Windows DPAPI(keyring — 동일 Windows 사용자 세션 내에서만 복호화)로 완화된다.
같은 OS 사용자로 실행 중인 프로세스는 어차피 keyring에 직접 접근 가능하므로, `/auth/restore`가 추가 공격 표면을 만들지 않는다.

### 3.3 Refresh Token Rotation 경쟁 조건

**문제**: 클라우드 서버는 Token Rotation 사용 (`auth.py:188` — refresh 시 기존 토큰 삭제).
프론트엔드와 로컬 서버가 **같은 refresh_token으로 동시에 refresh**하면:
1. 먼저 도착한 쪽이 성공 → 기존 refresh_token 삭제, 새 토큰 발급
2. 나중에 도착한 쪽이 실패 → 삭제된 토큰으로 요청 → 401
3. 한쪽 인증 끊김

**정책: 로컬 서버가 refresh 단일 주체. 프론트엔드는 로컬 서버 경유.**

```
프론트엔드 401 발생 시:
  1단계: POST /api/auth/restore → 로컬 서버에서 최신 토큰 요청
         (로컬이 이미 refresh했으면 새 토큰이 반환됨)
  2단계: 로컬 서버 다운 or 토큰 없음 → 클라우드 직접 refresh (폴백)
         성공 시 → localAuth.setAuthToken()으로 로컬에도 전달
```

이렇게 하면:
- 정상 경로: 로컬 서버만 refresh → 경쟁 없음
- 폴백 경로: 로컬 서버 다운 시에만 프론트엔드가 직접 refresh → 경쟁 불가능 (한쪽이 없으므로)

### 3.4 만료된 access_token 잔존

keyring에 저장된 access_token은 1시간 후 만료. 만료된 토큰이 남아있으면
`has_cloud_token: true`이지만 실제로는 무효.

**해결**: `POST /api/auth/restore`에서 access_token의 `exp` 클레임 확인.
만료 60초 전부터 만료로 간주 (네트워크 레이턴시 고려). 만료됐으면 refresh_token으로 갱신 후 새 토큰을 반환한다.

최종 구현은 §5.6 참조. 아래는 핵심 흐름만 요약:
```
1. load_cloud_tokens() → access_token, refresh_token
2. refresh_token 없으면 → 404
3. access_token 만료 (60초 leeway) → _refresh_lock 하에 refresh
4. 응답: { success, data: { access_token, refresh_token, email, local_secret } }
```

### 3.6 refresh 경쟁 조건 직렬화

**문제 1 — 브라우저 탭 간 경쟁**: 두 브라우저 탭이 동시에 `POST /api/auth/restore`를 호출하고,
둘 다 access_token 만료를 감지하여 refresh를 시도하면 Token Rotation 경쟁 발생.

**문제 2 — 하트비트 × restore 교차 경쟁**: 하트비트 루프가 401을 받아 `_try_refresh()`를 실행하는
동시에 브라우저가 `POST /api/auth/restore`를 호출하면, 같은 refresh_token으로 동시 요청 발생.

**해결**: 모듈 레벨 `_refresh_lock = asyncio.Lock()`을 **restore와 하트비트가 공유**.
Lock 획득 후 `load_cloud_tokens()`를 다시 확인 — 선행 요청이 이미 refresh했으면 새 토큰을 사용.

```python
# cloud/token_utils.py — 순환 import 방지를 위해 별도 모듈
_refresh_lock = asyncio.Lock()

# routers/auth.py restore_session 내부:
from local_server.cloud.token_utils import _refresh_lock
async with _refresh_lock:
    access_token, refresh_token = load_cloud_tokens()  # 다시 확인
    ...

# cloud/heartbeat.py _try_refresh 내부:
from local_server.cloud.token_utils import _refresh_lock
async with _refresh_lock:
    access_token, refresh_token = load_cloud_tokens()  # 다시 확인
    ...
```

### 3.7 HTTP 평문 전송

로컬 서버는 `http://127.0.0.1:4020`. 127.0.0.1 루프백은 OS 커널 내부 처리 — 네트워크를 거치지 않아 패킷 스니핑 불가. **허용 가능.**

## 4. 현재 코드 분석

### 4.1 `_active_user` 영속화 문제

`credential.py`에서 `_active_user`는 모듈 레벨 변수:
```python
_active_user: str = _DEFAULT_USER  # "default"
```

`set_active_user(email)`은 `auth.py:60`에서만 호출 (프론트엔드가 `POST /api/auth/token` 시).
재부팅하면 `"default"`로 돌아가므로, `stockvision:{email}` 네임스페이스에 저장된 토큰을 찾을 수 없다.

### 4.2 CloudClient — 토큰 고정

`client.py:27-43`: 생성자에서 `api_token`을 한 번 헤더에 설정. 이후 변경 불가.

### 4.3 heartbeat.py — 토큰 미전달

`heartbeat.py:73`: `CloudClient(base_url=cloud_url)` — `api_token` 없음.
클라우드 하트비트 엔드포인트는 `Depends(current_user)` → **모든 요청 401**.

### 4.4 auth.py — 런타임 로그인 시 heartbeat 미갱신

`auth.py:64`: `save_cloud_tokens()` 후 끝. heartbeat의 `CloudClient`에 새 토큰을 전달하는 경로 없음.

### 4.5 프론트엔드 — 로컬 서버 토큰 미확인

`AuthContext.tsx:35-65`: 마운트 시 `sessionStorage`/`localStorage`만 확인. 로컬 서버의 인증 상태를 확인하지 않음.

### 4.6 프론트엔드 — 401 시 클라우드 직접 refresh

`cloudClient.ts:27-54`: 401 인터셉터에서 클라우드에 직접 refresh.
로컬 서버도 refresh하면 Token Rotation 경쟁 발생 (§3.3).

## 5. 설계

### 5.1 `_active_user` 영속화 (A1)

```python
# credential.py
def set_active_user(user_id: str) -> None:
    global _active_user
    _active_user = user_id
    from local_server.config import get_config
    cfg = get_config()
    cfg.set("auth.last_user", user_id)
    cfg.save()

def _restore_active_user(user_id: str) -> None:
    """서버 시작 시 config에서 복원 — config 재저장 안 함."""
    global _active_user
    _active_user = user_id
```

**하위 호환성**: config.json에 `auth.last_user`가 없으면 (A1 이전 버전, 첫 실행):
- `_active_user`는 `"default"` 유지
- `load_cloud_tokens()`는 `stockvision:default` 네임스페이스 조회
- 이전에 `stockvision:{email}`에 저장된 토큰은 찾을 수 없음 → 로그 경고 + 수동 로그인 필요
- 수동 로그인하면 `set_active_user(email)`이 config에 저장 → 이후 재부팅부터 정상 동작

### 5.2 CloudClient 토큰 동적 관리 (A2)

```python
class CloudClientError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code

class CloudClient:
    def set_token(self, token: str) -> None:
        self._api_token = token
        self._headers["Authorization"] = f"Bearer {token}"

    def clear_token(self) -> None:
        self._api_token = None
        self._headers.pop("Authorization", None)

    async def refresh_access_token(self, refresh_token: str) -> dict:
        """POST /api/v1/auth/refresh → { access_token, refresh_token }"""
        result = await self._post("/api/v1/auth/refresh", {"refresh_token": refresh_token})
        return result.get("data", result)
```

`_get()`, `_post()`에서 `HTTPStatusError` 잡을 때 `status_code` 보존:
```python
except httpx.HTTPStatusError as e:
    raise CloudClientError(..., status_code=e.response.status_code) from e
```

### 5.3 하트비트 JWT + 401 자동갱신 (A2~A4)

```python
# heartbeat.py
_client: CloudClient | None = None

def get_cloud_client() -> CloudClient | None:
    return _client

async def start_heartbeat() -> None:
    global _client
    access_token, _ = load_cloud_tokens()
    _client = CloudClient(base_url=cloud_url, api_token=access_token)
    ...
    while True:
        try:
            resp = await _client.send_heartbeat(payload)
            ...
        except CloudClientError as e:
            if e.status_code == 401:
                refreshed = await _try_refresh(_client)
                if refreshed:
                    continue  # 갱신 후 즉시 재시도
            ...

async def _try_refresh(client: CloudClient) -> bool:
    """restore_session과 같은 _refresh_lock을 공유하여 교차 경쟁 방지."""
    from local_server.cloud.token_utils import _refresh_lock, is_jwt_expired
    async with _refresh_lock:
        # Lock 내부에서 토큰 다시 로드 — 선행 요청이 이미 refresh했을 수 있음
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

### 5.4 런타임 로그인 → heartbeat 반영 (A7)

```python
# routers/auth.py register_cloud_token()
save_cloud_tokens(body.access_token, body.refresh_token)
from local_server.cloud.heartbeat import get_cloud_client
cc = get_cloud_client()
if cc:
    cc.set_token(body.access_token)
```

### 5.5 서버 시작 시 자동 로그인 (A5~A6)

main.py lifespan에서 하트비트 시작 전:

```
1. config.json에서 auth.last_user 읽기 → _restore_active_user() (메모리만)
2. load_cloud_tokens() → (access_token, refresh_token)
3. access_token 없고 refresh_token 있으면 → refresh 시도
   - 성공: save_cloud_tokens() + access_token 확보
   - 실패: 로그 경고, 하트비트는 토큰 없이 시작
4. 둘 다 없으면 → 정상 (첫 실행)
```

### 5.6 `POST /api/auth/restore` (A8)

새 엔드포인트. `POST /api/auth/token`과 동일 보안 수준 (인증 없이 호출 가능, local_secret 반환).

`_refresh_lock`과 `is_jwt_expired`는 `cloud/token_utils.py`에 정의 — restore와 하트비트 모두 이 모듈에서 import (§3.6 참조).

```python
from local_server.cloud.token_utils import _refresh_lock, is_jwt_expired

@router.post("/restore", summary="저장된 토큰으로 세션 복원")
async def restore_session(request: Request) -> dict:
    access_token, refresh_token = load_cloud_tokens()
    if not refresh_token:
        raise HTTPException(status_code=404, detail="저장된 토큰 없음")

    # access_token 만료 확인 → 만료 시 refresh
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
                    # heartbeat에도 반영
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

    # is_jwt_expired()는 cloud/token_utils.py에 정의 (§3.6 참조)
```

### 5.7 `GET /api/auth/status` (A8 보조)

기존 엔드포인트 확장. **토큰은 반환하지 않음** — 유무와 이메일만.

```python
@router.get("/status")
async def auth_status() -> dict:
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

### 5.8 프론트엔드: 로컬 서버 우선 refresh + 세션 복원 (A9)

#### 5.8a AuthContext 마운트 — 세션 복원

`localAuth.restore()`는 내부적으로 `localSecret`도 저장한다 (§5.8c 참조).

```typescript
useEffect(() => {
  const jwt = sessionStorage.getItem(STORAGE_KEY_JWT)
  const rt = localStorage.getItem(STORAGE_KEY_RT)

  if (jwt && rt) {
    // 기존: JWT 있음 → 로컬 서버에 전달
    localAuth.setAuthToken(jwt, rt).then(...)
  } else if (rt) {
    // 기존: RT만 있음 → 클라우드 refresh
    // ... (기존 코드 유지)
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
        // 로컬 서버 다운 or 토큰 없음 → 미인증 상태 확정, localReady는 true로 설정하여 블로킹 해제
        setState(prev => ({ ...prev, localReady: true }))
      }
    })
  }
}, [])
```

#### 5.8b cloudClient 401 인터셉터 — 로컬 서버 우선 refresh

기존: 클라우드에 직접 refresh.
변경: **로컬 서버 우선 → 폴백으로 클라우드 직접.**

**주의**: `cloudClient.ts`에서 `localAuth`를 import해야 한다:
```typescript
import { localAuth } from './localClient'
```

```typescript
// cloudClient.ts 401 인터셉터
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

#### 5.8c localClient — `localAuth.restore()` 추가

```typescript
// localClient.ts
export const localAuth = {
  // ... 기존 ...
  restore: async () => {
    try {
      const res = await client.post('/auth/restore')
      // local_secret을 모듈 변수에 저장 — 이후 mutation API 호출에 필요
      localSecret = res.data?.data?.local_secret ?? null
      return res.data
    } catch {
      return null
    }
  },
}
```

**핵심**: `localSecret = res.data?.data?.local_secret`을 반드시 저장해야 한다.
이 값이 없으면 이후 `X-Local-Secret` 헤더가 누락되어 모든 mutation API가 403을 반환한다.

## 6. 수용 기준

### 인증 동기화
- [ ] `_active_user`가 config.json에 영속화, 재부팅 후 복원
- [ ] 하트비트가 JWT Authorization 헤더를 포함하여 전송
- [ ] 401 응답 시 refresh_token으로 자동 갱신 후 재시도
- [ ] 갱신된 토큰 쌍이 keyring에 저장됨 (Token Rotation)
- [ ] 서버 시작 시 refresh_token이 있으면 자동 로그인
- [ ] refresh_token 만료 시 트레이 🔴 + "재로그인 필요" 상태
- [ ] 런타임 로그인 시 heartbeat CloudClient에도 새 토큰 반영
- [ ] `POST /api/auth/restore` — 만료 확인 후 토큰+local_secret 반환
- [ ] `GET /api/auth/status` — 토큰 미노출, 유무+이메일만
- [ ] 프론트엔드 마운트 시 로컬 서버에서 세션 복원
- [ ] 프론트엔드 401 시 로컬 서버 우선 refresh, 실패 시 클라우드 폴백

## 7. 수정 대상 파일

| 파일 | 변경 내용 |
|------|----------|
| `local_server/cloud/token_utils.py` | **신규** — `_refresh_lock`, `is_jwt_expired()`. 순환 import 방지용 공유 모듈 |
| `local_server/storage/credential.py` | `set_active_user()` config 영속화, `_restore_active_user()` 추가 |
| `local_server/cloud/client.py` | `set_token()`, `clear_token()`, `refresh_access_token()`. `CloudClientError.status_code` |
| `local_server/cloud/heartbeat.py` | 토큰 로드→전달, 401→refresh, `get_cloud_client()` 싱글턴 |
| `local_server/main.py` | `_restore_active_user()` + 자동 로그인 단계 |
| `local_server/routers/auth.py` | `POST /restore` 신규, `GET /status` 확장, `register_cloud_token`에서 heartbeat 반영 |
| `frontend/src/context/AuthContext.tsx` | 마운트 시 로컬 서버 restore 시도 |
| `frontend/src/services/cloudClient.ts` | 401 인터셉터: 로컬 서버 우선 → 클라우드 폴백 |
| `frontend/src/services/localClient.ts` | `localAuth.restore()` 추가 |

## 8. 참조

- 클라우드 refresh: `cloud_server/api/auth.py:175` (`POST /api/v1/auth/refresh`, Token Rotation)
- 클라우드 하트비트 인증: `cloud_server/api/heartbeat.py:33` (`Depends(current_user)`)
- 로컬 보안: `local_server/core/local_auth.py` (local_secret 생성/검증)
- 토큰 저장소: `local_server/storage/credential.py`
- 프론트엔드 인증: `frontend/src/context/AuthContext.tsx`
- 프론트엔드 클라우드 클라이언트: `frontend/src/services/cloudClient.ts` (401 인터셉터)
- 프론트엔드 로컬 클라이언트: `frontend/src/services/localClient.ts`
