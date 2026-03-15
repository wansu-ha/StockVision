# Auth Security — 구현 계획

> 작성일: 2026-03-13 | 상태: 초안

---

## 아키텍처

```
[로컬 인증 흐름]
프론트엔드
  → localClient (X-Local-Secret 인터셉터)  ← AS-5: alertsClient 교체
  → localClient (fetch → localClient)       ← AS-6: DeviceManager 교체
  → WS 첫 프레임 auth                      ← AS-1: query param 제거
    ↓
로컬 서버
  → require_local_secret (Depends)          ← AS-3: auth/status 추가
  → devices.py pair 인증                    ← AS-6: Depends 추가
  → auth.py 토큰 등록 보호                  ← AS-2: nonce 또는 1회 게이트
  → ws.py 첫 프레임 검증                    ← AS-1: 5초 타임아웃

[클라우드 인증 흐름]
클라이언트
  → X-Forwarded-For
    ↓
Render 프록시
  → cloud_server rate_limit.py              ← AS-4: rightmost IP
```

---

## 수정 파일 목록

| 파일 | 변경 내용 |
|------|----------|
| `local_server/routers/auth.py` | `/api/auth/status`에 `Depends` 추가. `/api/auth/token`, `/api/auth/restore`에 1회 게이트 또는 nonce |
| `local_server/routers/devices.py` | `pair_init`, `pair_complete`에 `Depends(require_local_secret)` 추가 |
| `local_server/routers/ws.py` | `sec` query param 제거, 첫 프레임 auth 로직 추가 |
| `cloud_server/core/rate_limit.py` | `_get_ip()` — rightmost IP 또는 `request.client.host` 폴백 |
| `frontend/src/services/alertsClient.ts` | bare axios → localClient 교체 |
| `frontend/src/components/DeviceManager.tsx` | raw fetch → localClient 교체 |
| `frontend/src/services/localClient.ts` | `getLocalSecret()` getter 함수 export 추가 |
| `frontend/src/hooks/useLocalBridgeWS.ts` | WS URL에서 `sec` 제거, 연결 후 첫 프레임 auth 전송 |

---

## 구현 순서

### Step 1: /api/auth/status 인증 추가 (AS-3)

`auth.py` `auth_status()` 시그니처에 `Depends(require_local_secret)` 추가.

**verify**: 인증 없이 GET /api/auth/status → 403

### Step 2: alertsClient 교체 (AS-5)

`alertsClient.ts`에서 `import axios from 'axios'` → `import client from './localClient'` 교체 (default export).
모든 `axios.get/put` → `client.get/put`. `localClient`의 `baseURL`이 `${LOCAL_URL}/api`이므로 경로를 `/settings/alerts`로 단축.

**의존성**: `trading-safety` Step 1 (TS-2: alerts 서버 인증)이 선행 완료되어야 정상 동작. 서버 인증 없이도 교체 자체는 가능하나, verify는 TS-2 이후 수행.

**verify**: 경고 설정 페이지 로드/저장 정상 (TS-2 서버 인증 추가 후)

### Step 3: DeviceManager + devices.py 인증 (AS-6)

**서버**: `devices.py` `pair_init()`, `pair_complete()` 시그니처에 `Depends(require_local_secret)` 추가.

**프론트**: `DeviceManager.tsx`의 `fetch()` 호출을 `localClient` 사용으로 교체.

```tsx
// Before: fetch(`http://localhost:4020/api/devices/pair/init`, { method: 'POST' })
// After: client.post('/devices/pair/init')
// 주의: localClient의 baseURL이 `${LOCAL_URL}/api`이므로 경로에서 /api 제거
```

**verify**: 인증 없이 POST /api/devices/pair/init → 403. 프론트에서 정상 페어링 시작.

### Step 4: Rate limiter 수정 (AS-4)

`rate_limit.py` `_get_ip()` 수정:

**주의**: Render 프록시의 X-Forwarded-For 동작을 먼저 확인해야 함.

**구현 전 확인 작업**: Render 배포 환경에서 `request.client.host`와 `X-Forwarded-For` 값을 로깅하여 실제 동작 파악. Render는 로드밸런서가 `X-Forwarded-For`를 설정하므로 `request.client.host`는 프록시 IP일 가능성 높음 → 프록시 IP만 반환하면 모든 사용자가 동일 rate limit 공유.

확인 후 적용할 코드 (일반적 패턴):

```python
def _get_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Render 프록시가 설정한 X-Forwarded-For의 첫 번째 IP = 실제 클라이언트
        # 클라이언트 위조 방지: Render가 기존 XFF를 덮어쓰는지 추가하는지 확인 필요
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
```

현재 코드와 동일 구조이므로, **Render가 클라이언트의 XFF를 덮어쓰는 경우** 위조 방지됨. 추가만 하는 경우 위조 가능 → 이 경우만 rightmost 적용.

**verify**: Render 환경에서 `X-Forwarded-For` 위조 테스트 + 정상 IP rate limit 확인

### Step 5: /api/auth/token + /api/auth/restore 보호 (AS-2)

**방안 선택**: (a) 최초 등록 게이트

```python
# auth.py — 이미 local_secret이 발급된 상태면 require_local_secret 적용
async def register_token(body, request):
    if _secret_already_issued():
        # 이미 등록됨 → 인증 필요
        require_local_secret(request)
    ...
```

`local_auth.py`에 `is_registered() -> bool` 메서드 추가 — `_secret`이 이미 생성되어 있으면 True.
`/api/auth/restore`도 동일 게이트 적용 (restore도 `local_secret` 반환하므로).

**주의**: 앱 초기화 흐름에서 `GET /api/auth/status` 호출 시점과 secret 획득 시점의 순서를 확인해야 함. `localClient`가 secret 없이 status를 조회하면 403이 됨 — 초기화 흐름 설계 시 이 의존성 고려.

**verify**: 첫 호출 → 정상 (local_secret 반환). 이후 호출 → 인증 없이 403. restore도 동일.

### Step 6: WS 인증 프로토콜 변경 (AS-1)

**서버** (`ws.py`):

```python
async def websocket_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    # 5초 내 auth 프레임 대기
    try:
        auth_msg = await asyncio.wait_for(ws.receive_json(), timeout=5.0)
        if auth_msg.get("type") != "auth" or not _verify_secret(auth_msg.get("secret", "")):
            await ws.close(1008, "Unauthorized")
            return
    except asyncio.TimeoutError:
        await ws.close(1008, "Auth timeout")
        return
    # 인증 성공 → 기존 로직
    ...
```

**프론트** (`useLocalBridgeWS.ts`):

**사전 작업**: `localClient.ts`에 `getLocalSecret()` getter export 추가 (현재 `localSecret`은 모듈 내부 변수).

```typescript
// localClient.ts에 추가
export function getLocalSecret(): string { return localSecret; }

// useLocalBridgeWS.ts
import { getLocalSecret } from '../services/localClient';

ws.onopen = () => {
    ws.send(JSON.stringify({ type: 'auth', secret: getLocalSecret() }));
    retries.current = 0;
};
```

**verify**: URL에 secret 미포함. 인증 없이 WS 연결 → 5초 후 종료. 인증 후 정상 메시지 수신.

---

## 검증 방법

1. **빌드**: 로컬 서버 import 에러 없음, 프론트 `npm run build` 성공
2. **기존 테스트**: `pytest local_server/tests/ -q` — 통과
3. **수동 확인**:
   - 각 엔드포인트 인증 없이 호출 → 403
   - WS 연결 → 첫 프레임 auth → 정상 동작
   - Rate limiter 위조 IP 차단
