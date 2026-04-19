# Stability — 구현 계획

> 작성일: 2026-03-13 | 상태: 구현 완료

---

## 아키텍처

```
[브로커 재연결 흐름]
KisWS._recv_loop()
  → ConnectionClosed 예외
    → _on_disconnect 콜백           ← ST-2: StateMachine → ERROR 전환
      → ReconnectManager.on_state_change()
        → _do_connect()
          → subscribe(saved_symbols) ← ST-1: 재구독

[LogDB 흐름]
엔진 async 컨텍스트
  → asyncio.to_thread(log_db.write)  ← ST-3: 비동기 래핑

[클라우드 OAuth 흐름]
OAuth 콜백
  → oauth_service.login_or_register()
    → email 빈 문자열 체크           ← ST-7: 빈 이메일 차단
    → User INSERT
      → try/except IntegrityError    ← ST-5: 재조회
    → password_hash=None             ← ST-6: nullable

[프론트 OAuth 흐름]
OAuthCallback
  → 토큰 저장
  → loginWithTokens()                ← ST-8: AuthContext 갱신
  → navigate('/')
```

---

## 수정 파일 목록

| 파일 | 변경 내용 |
|------|----------|
| `local_server/broker/kis/ws.py` | `_recv_loop()`에 disconnect 콜백 호출 추가 |
| `local_server/broker/kis/adapter.py` | `_subscribed_symbols` 보관, `_do_connect()` 후 재구독, ws에 disconnect 콜백 전달 |
| `local_server/storage/log_db.py` | `async_write()` 래퍼 추가 |
| `local_server/engine/executor.py` | `log_db.write()` → `await log_db.async_write()` 변경 (ST-3 호출부) |
| `local_server/routers/trading.py` | `log_db.write()` → `await log_db.async_write()` 변경 (ST-3 호출부) |
| `cloud_server/collector/scheduler.py` | `authenticate()` → `connect()` |
| `cloud_server/services/oauth_service.py` | IntegrityError 처리, 빈 이메일 검증 |
| `cloud_server/models/user.py` | `password_hash` nullable=True |
| `cloud_server/alembic/versions/` | 마이그레이션 파일 추가 |
| `frontend/src/context/AuthContext.tsx` | `loginWithTokens()` 메서드 추가 |
| `frontend/src/pages/OAuthCallback.tsx` | `loginWithTokens()` 호출 |

---

## 구현 순서

### Step 1: collector authenticate → connect (ST-4)

`scheduler.py:157` 한 줄 변경:

```python
# Before: await broker.authenticate()
await broker.connect()
```

**verify**: 클라우드 서버 시작 시 AttributeError 없음

### Step 2: password_hash nullable (ST-6)

`user.py:29` 변경:

```python
password_hash = Column(String(255), nullable=True)
```

Alembic 마이그레이션 생성:

```bash
alembic revision --autogenerate -m "password_hash nullable"
```

마이그레이션에 데이터 수정 추가:

```python
op.execute("UPDATE users SET password_hash = NULL WHERE password_hash = ''")
```

`oauth_service.py:145` 변경: `password_hash=""` → `password_hash=None`

**verify**: OAuth 가입 → `password_hash IS NULL`

### Step 3: OAuth 동시 로그인 보호 (ST-5)

`oauth_service.py` `login_or_register()` 수정:

```python
try:
    db.flush()
except IntegrityError:
    db.rollback()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise  # 진짜 에러
```

**verify**: 동시 OAuth 요청 시뮬레이션 → 500 없음

### Step 4: Kakao 빈 이메일 차단 (ST-7)

`oauth_service.py` Kakao 프로필 파싱 후:

```python
if not email:
    raise HTTPException(400, "이메일 동의가 필요합니다. Kakao 설정에서 이메일 제공을 허용해주세요.")
```

**verify**: 빈 이메일로 OAuth 요청 → 400 + 안내 메시지

### Step 5: LogDB 비동기 래핑 (ST-3)

`log_db.py`에 async 래퍼 추가:

```python
async def async_write(self, *args, **kwargs) -> int:
    return await asyncio.to_thread(self.write, *args, **kwargs)
```

호출부에서 `log_db.write()` → `await log_db.async_write()` 변경.
호출부: `engine/executor.py`, `routers/trading.py:197,233,289` (async 핸들러에서 동기 호출).
동기 컨텍스트 호출부는 기존 `write()` 유지.

**verify**: 엔진 평가 중 이벤트 루프 블로킹 없음

### Step 6: OAuth 콜백 AuthContext 갱신 (ST-8)

`AuthContext.tsx`에 추가:

```typescript
const loginWithTokens = useCallback(async (jwt: string, rt: string) => {
    sessionStorage.setItem('sv_jwt', jwt);
    localStorage.setItem('sv_rt', rt);
    await localAuth.setAuthToken(jwt, rt);  // async + 인자 2개
    setState(prev => ({ ...prev, jwt, refreshToken: rt, isAuthenticated: true, localReady: true }));
}, []);
```

context value에 `loginWithTokens` 포함. `AuthContextValue` 인터페이스에도 `loginWithTokens: (jwt: string, rt: string) => Promise<void>` 추가.

`OAuthCallback.tsx` 수정:

```typescript
const { loginWithTokens } = useAuth();
// 토큰 교환 성공 후:
await loginWithTokens(tokens.access_token, tokens.refresh_token);
navigate('/', { replace: true });
```

**verify**: OAuth 로그인 → 메인 대시보드 정상 진입 (로그인 페이지로 튕기지 않음)

### Step 7: KisWS StateMachine 전환 (ST-2)

`ws.py`에 disconnect 콜백 추가:

```python
def __init__(self, ..., on_disconnect: Callable | None = None):
    self._on_disconnect = on_disconnect
```

`_recv_loop()` 예외 핸들러에서:

```python
except ConnectionClosed:
    self._connected = False
    if self._on_disconnect:
        self._on_disconnect()  # 동기 콜백 — _recv_loop는 asyncio Task 내부이므로 running loop 있음
```

`adapter.py:67`에서 ws 생성 시 콜백 전달:

```python
self._ws = KisWS(self._auth, on_disconnect=self._on_ws_disconnect)

def _on_ws_disconnect(self):
    # _recv_loop가 asyncio Task 안에서 실행되므로 create_task 사용 가능
    asyncio.create_task(self._state.transition(ConnectionState.ERROR))
```

**verify**: WS 연결 끊김 → StateMachine ERROR 전환 → 로그 확인

### Step 8: 재연결 후 시세 재구독 (ST-1)

`adapter.py`에 `_subscribed_symbols` 관리:

```python
async def subscribe_quotes(self, symbols, callback):
    self._subscribed_symbols.update(symbols)  # 별도 보관
    ...

async def _do_connect(self):
    ... # 기존 연결 로직
    # 재구독
    if self._subscribed_symbols:
        await self._ws.subscribe(list(self._subscribed_symbols))
```

**verify**: 브로커 연결 끊김 → 자동 재연결 → 시세 수신 재개

---

## 검증 방법

1. **빌드**: 로컬/클라우드 서버 import 에러 없음, 프론트 `npm run build` 성공
2. **로컬 서버 테스트**: `pytest local_server/tests/ -q` — 통과
3. **클라우드 서버 테스트**: `pytest cloud_server/tests/ -q` — 통과
4. **수동 확인**:
   - 클라우드 서버 시작 → collector 에러 없음
   - OAuth 로그인 → 메인 대시보드 진입
   - password_hash nullable 마이그레이션 성공
