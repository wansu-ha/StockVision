# KIS 어댑터 보완 — 구현 계획

> 작성일: 2026-03-16 | 상태: 초안 | spec: `spec/kis-adapter-completion/spec.md`

## 선행 조건

- KIS OpenAPI 포털에서 매도 TR ID 및 Approval Key 발급 문서 확인 필요
- KIS 테스트 계정 미보유 → 모의서버 기준 검증

## 의존관계

```
K1 (매도 TR ID)     ─── 독립
K2 (Approval Key)   ─── 독립
K3 (App Secret)     ─── K2 완료 후 (같은 auth.py 수정)

→ K1, K2 병렬. K3은 K2 후.
```

## Step 1: 매도 TR ID 검증

**파일**: `local_server/broker/kis/order.py` (수정)

### 1.1 현재 매핑 (lines 25-38)

```python
# 실전
_ORDER_TR_ID = {
    (BUY, MARKET): "TTTC0802U",   # 매수 시장가
    (BUY, LIMIT):  "TTTC0801U",   # 매수 지정가
    (SELL, MARKET): "TTTC0801U",  # 매도 — 매수와 동일?
    (SELL, LIMIT):  "TTTC0801U",  # 매도 — 매수와 동일?
}
# 모의
_MOCK_ORDER_TR_ID = {
    (BUY, MARKET): "VTTC0802U",
    (BUY, LIMIT):  "VTTC0801U",
    (SELL, MARKET): "VTTC0801U",
    (SELL, LIMIT):  "VTTC0801U",
}
```

### 1.2 KIS API 확인 필요사항

KIS 국내주식주문 API 기준:
- 매수: `TTTC0802U` (시장가), `TTTC0801U` (지정가)
- 매도: **동일 TR ID 사용 가능** — `SLL_TYPE` 필드(`"01"` 매수, `"02"` 매도)로 구분

**확인 방법**: KIS API 문서의 TR ID 테이블 대조

### 1.3 변경 (확인 결과에 따라)

경우 1: 현재 매핑이 맞음 → 주석만 보강
```python
# KIS API는 매수/매도 동일 TR ID, SLL_TYPE으로 구분
```

경우 2: 매도 전용 TR ID 존재 → 매핑 수정
```python
(SELL, MARKET): "TTTC0812U",  # 예시
(SELL, LIMIT):  "TTTC0811U",
```

**검증**:
- [ ] KIS API 문서 TR ID 테이블과 코드 일치
- [ ] 모의서버 TR ID도 동일 검증
- [ ] 기존 단위 테스트 통과

## Step 2: WebSocket Approval Key

**파일**: `local_server/broker/kis/auth.py` (수정), `local_server/broker/kis/ws.py` (수정)

### 2.1 KisAuth에 approval_key 발급 추가

```python
# auth.py
class KisAuth:
    _approval_key: str | None = None
    _approval_key_expires: datetime | None = None

    async def get_approval_key(self) -> str:
        """WebSocket 접속용 approval_key 발급 (캐싱)."""
        if self._approval_key and self._approval_key_expires and datetime.now() < self._approval_key_expires:
            return self._approval_key

        url = f"{self._base_url}/oauth2/Approval"
        body = {
            "grant_type": "client_credentials",
            "appkey": self._app_key,
            "secretkey": self._app_secret,
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=body)
            resp.raise_for_status()
            data = resp.json()

        self._approval_key = data["approval_key"]
        # KIS approval_key 유효기간: 24시간 (안전 마진 23시간)
        self._approval_key_expires = datetime.now() + timedelta(hours=23)
        return self._approval_key
```

### 2.2 KisWebSocket에서 호출

```python
# ws.py
async def _get_approval_key(self) -> str:
    return await self._auth.get_approval_key()
```

**검증**:
- [ ] approval_key가 access_token과 다른 값
- [ ] 캐싱되어 24시간 내 재요청 없음
- [ ] WS 구독 메시지에 올바른 key 포함
- [ ] 모의서버 approval_key 엔드포인트 동작 확인

## Step 3: App Secret 불필요 전송 제거 (K3)

**파일**: `local_server/broker/kis/auth.py` (수정)

### 3.1 헤더 분리

현재 `_get_common_headers()` (또는 동등 함수)가 모든 요청에 `appsecret`을 포함한다.
OAuth 전용 헤더와 일반 API 헤더를 분리.

```python
# auth.py
def get_auth_headers(self) -> dict:
    """일반 API 요청용 헤더 (appsecret 미포함)."""
    return {
        "authorization": f"Bearer {self._access_token}",
        "appkey": self._app_key,
        "content-type": "application/json; charset=utf-8",
    }

def _get_oauth_headers(self) -> dict:
    """OAuth 토큰 발급용 헤더 (appsecret 포함)."""
    return {
        "appkey": self._app_key,
        "appsecret": self._app_secret,
        "content-type": "application/json; charset=utf-8",
    }
```

### 3.2 기존 호출 지점 수정

- `get_access_token()` → `_get_oauth_headers()` 사용
- `get_approval_key()` → `_get_oauth_headers()` 사용
- 주문/시세 등 일반 REST → `get_auth_headers()` 사용

**검증**:
- [ ] `/oauth2/token` 요청에 `appsecret` 포함
- [ ] `/oauth2/Approval` 요청에 `appsecret` 포함
- [ ] 일반 REST (주문, 시세) 요청에 `appsecret` 미포함
- [ ] 기존 단위 테스트 통과

## 변경 파일 요약

| 파일 | Step | 변경 |
|------|------|------|
| `local_server/broker/kis/order.py` | K1 | TR ID 검증 + 수정/주석 보강 |
| `local_server/broker/kis/auth.py` | K2, K3 | `get_approval_key()` 추가 + 헤더 분리 |
| `local_server/broker/kis/ws.py` | K2 | `_get_approval_key()` → auth 호출 |
