# KIS 어댑터 보완 — 매도 TR ID 검증 + WebSocket Approval Key

> 작성일: 2026-03-15 | 상태: 초안

## 1. 배경

KIS(한국투자증권) 어댑터가 기본 기능은 동작하나, 두 가지 구현 미비가 있다:

1. **매도 TR ID**: 매수/매도 모두 동일 TR ID(`TTTC0801U`)를 사용 중. KIS API 문서 대조 필요
2. **Approval Key**: WebSocket 접속 시 별도 approval_key 대신 access_token을 직접 사용 중

## 2. 범위

### 2.1 포함

| # | 항목 |
|---|------|
| K1 | 매도 주문 TR ID 정확성 검증 + 수정 |
| K2 | WebSocket approval_key 별도 발급 구현 |

### 2.2 제외

- 키움 어댑터 변경 (별도 spec)
- KIS 실API 통합 테스트 (테스트 계정 미보유)

## 3. 요구사항

### K1: 매도 TR ID 검증

**현재 코드** (`local_server/broker/kis/order.py:25-30`):
```python
_ORDER_TR_ID: dict[tuple[OrderSide, OrderType], str] = {
    (OrderSide.BUY, OrderType.MARKET): "TTTC0802U",   # 매수 시장가
    (OrderSide.BUY, OrderType.LIMIT): "TTTC0801U",    # 매수 지정가
    (OrderSide.SELL, OrderType.MARKET): "TTTC0801U",   # 매도 시장가
    (OrderSide.SELL, OrderType.LIMIT): "TTTC0801U",    # 매도 지정가
}
```

**문제**: 매도 주문이 매수 지정가와 동일한 `TTTC0801U`를 사용한다.
주석에 "동일 tr_id, ord_dvsn으로 구분"이라고 되어 있고, `SLL_TYPE`(`"01"` 매수, `"02"` 매도)으로
매수/매도를 구분하는 구조이지만, KIS API 문서 기준 정확한 TR ID를 확인해야 한다.

**요구사항**:
- KIS OpenAPI 공식 문서에서 주식 매도 TR ID 확인
- 실전/모의 TR ID 테이블 업데이트
- 모의 TR ID (`_MOCK_ORDER_TR_ID`)도 동일하게 검증

**KIS API 참고**: `https://apiportal.koreainvestment.com`의 국내주식주문 > 매도 항목

### K2: WebSocket Approval Key

**현재 코드** (`local_server/broker/kis/ws.py:148-154`):
```python
async def _get_approval_key(self) -> str:
    """KIS WebSocket은 별도 approval_key가 필요하다.
    현재는 access_token을 그대로 사용 (실제 API에서는 별도 endpoint 필요).
    """
    return await self._auth.get_access_token()
```

**문제**: KIS WebSocket API는 OAuth access_token이 아닌 별도 approval_key를 요구한다.
현재는 access_token을 그대로 전달하는 임시 구현이다.

**요구사항**:
- KIS `/oauth2/Approval` 엔드포인트 호출하여 approval_key 발급
- 발급된 key 캐싱 (유효 기간 동안 재사용)
- `KisAuth` 클래스에 `get_approval_key()` 메서드 추가
- `KisWebSocket._get_approval_key()`에서 새 메서드 호출

## 4. 변경 파일 (예상)

| 파일 | 변경 |
|------|------|
| `local_server/broker/kis/order.py` | K1: `_ORDER_TR_ID`, `_MOCK_ORDER_TR_ID` 수정 (필요 시) |
| `local_server/broker/kis/auth.py` | K2: `get_approval_key()` 메서드 추가 |
| `local_server/broker/kis/ws.py` | K2: `_get_approval_key()` → auth 메서드 호출로 변경 |

## 5. 수용 기준

- [ ] 매도 TR ID가 KIS API 공식 문서와 일치한다
- [ ] 실전/모의 TR ID가 각각 올바른 값을 사용한다
- [ ] WebSocket 접속 시 별도 approval_key를 발급받아 사용한다
- [ ] approval_key가 캐싱되어 불필요한 재발급이 발생하지 않는다
- [ ] KIS 계정 없이도 mock 어댑터로 단위 테스트가 통과한다

## 6. 선행 조건

- KIS OpenAPI 포털 접속하여 TR ID 및 approval_key 엔드포인트 문서 확인 필요
- KIS 테스트 계정 미보유 — 모의서버 기준으로 검증

## 7. 참고

- KIS 어댑터: `local_server/broker/kis/`
- KIS auth: `local_server/broker/kis/auth.py`
- 키움 어댑터 (참고): `local_server/broker/kiwoom/`
