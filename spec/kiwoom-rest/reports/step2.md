# Step 2 리포트: KiwoomAuth

## 생성/수정된 파일
- `local_server/__init__.py`
- `local_server/broker/__init__.py`
- `local_server/broker/kiwoom/__init__.py`
- `local_server/broker/kiwoom/auth.py`

## 주요 구현 내용

### KiwoomAuth
- `TokenInfo` dataclass: access_token, token_type, expires_at 보관
- `get_access_token()`: asyncio.Lock으로 동시 갱신 방지, 만료 5분 전 자동 갱신
- `_needs_refresh()`: 토큰 없거나 만료 임박 시 True
- `_fetch_token()`: POST /oauth2/token, grant_type=client_credentials
- `invalidate()`: 인증 오류 발생 시 캐시 초기화
- `build_headers()`: Authorization Bearer + appkey + appsecret 헤더 반환

### 상수
- `KIWOOM_BASE_URL`: https://openapi.koreainvestment.com:9443
- `TOKEN_REFRESH_MARGIN_SECONDS`: 300 (5분 여유)

## 리뷰에서 발견한 이슈 및 수정 사항
- 초안에 `resp = client.post(...)` 동기 호출 오타 발견 → `await client.post(...)` 수정
- asyncio.Lock 추가로 동시 요청 시 중복 발급 방지

## 테스트 결과
- 구문 오류 없음 (정적 검토)
- 실제 API 호출은 Step 13 통합 테스트에서 MockAdapter로 대체

## 다음 Step과의 연결점
- KiwoomQuote, KiwoomOrder는 `auth.build_headers()` 호출로 인증 헤더 획득
