# P0 보안 수정 보고서 — Unit 1 (broker/kiwoom)

날짜: 2026-03-05

## SEC-C1: App Secret이 모든 API 요청 헤더에 포함되는 문제

### 문제

`KiwoomAuth.build_headers()`가 `appsecret`을 반환 딕셔너리에 포함시켰다.
`quote.py`와 `order.py`의 모든 API 호출(시세 조회, 잔고 조회, 주문 실행/취소/미체결 조회)이
이 메서드를 사용하여 appsecret을 불필요하게 전송하고 있었다.

키움 REST API 스펙상 appsecret은 토큰 발급 요청(`POST /oauth2/token`)의 **요청 본문(JSON body)**에만 필요하다.
그 외 모든 엔드포인트는 `Authorization: Bearer {token}` + `appkey`만 요구한다.

### 영향 범위

`build_headers()`를 호출하는 위치 (모두 일반 API 요청):

| 파일 | 라인 | 호출 목적 |
|------|------|-----------|
| `quote.py` | 55 | 현재가 조회 |
| `quote.py` | 90 | 잔고 조회 |
| `order.py` | 102 | 주문 실행 |
| `order.py` | 156 | 주문 취소 |
| `order.py` | 200 | 미체결 조회 |

### 수정 내용

**파일**: `local_server/broker/kiwoom/auth.py` (worktree: `agent-a574e260`)

#### 변경 전

```python
async def build_headers(self) -> dict[str, str]:
    """API 요청에 필요한 인증 헤더를 구성한다."""
    token = await self.get_access_token()
    return {
        "Authorization": f"Bearer {token}",
        "appkey": self._app_key,
        "appsecret": self._app_secret,   # 모든 요청에 포함 — 잘못됨
        "Content-Type": "application/json; charset=utf-8",
    }
```

#### 변경 후

```python
async def build_headers(self) -> dict[str, str]:
    """일반 API 요청용 헤더. appsecret 미포함."""
    token = await self.get_access_token()
    return {
        "Authorization": f"Bearer {token}",
        "appkey": self._app_key,
        # appsecret 제거
        "Content-Type": "application/json; charset=utf-8",
    }

def build_auth_headers(self) -> dict[str, str]:
    """토큰 발급 전용 헤더. POST /oauth2/token에만 사용."""
    return {
        "appkey": self._app_key,
        "appsecret": self._app_secret,
        "Content-Type": "application/json; charset=utf-8",
    }
```

### 추가 확인 사항

- **`_fetch_token()`**: appsecret을 HTTP 헤더가 아닌 JSON body에 담아 전송 — 키움 OAuth 스펙에 맞는 올바른 방식. 수정 불필요.
- **`ws.py`**: `get_access_token()`을 직접 호출, `build_headers()` 미사용. 수정 불필요.
- **로깅**: `_fetch_token()`은 토큰 만료 시각만 로깅하며 토큰값/시크릿을 출력하지 않음. 마스킹 불필요.
- **`quote.py`, `order.py`**: `build_headers()` 호출 코드 그대로 유지 — 메서드 시그니처 변경 없이 수정 완료.

### `build_auth_headers()` 사용 지침

현재 `_fetch_token()`은 appsecret을 JSON body로 전송하므로 `build_auth_headers()`를 별도로 호출하지 않는다.
향후 키움 API가 헤더 방식 인증을 요구할 경우 `_fetch_token()` 내에서 `build_auth_headers()`를 사용하면 된다.
