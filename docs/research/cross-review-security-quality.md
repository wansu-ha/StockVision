# 보안 + 코드 품질 교차 리뷰

**검토 대상**: Unit 1 (키움 REST), Unit 2 (로컬 서버), Unit 4 (클라우드 서버)
**검토 일자**: 2026-03-05
**검토자**: Claude Code (claude-sonnet-4-6)

---

## 목차

1. [보안 이슈 목록](#보안-이슈-목록)
2. [코드 품질 이슈 목록](#코드-품질-이슈-목록)
3. [우선순위별 수정 필요 사항](#우선순위별-수정-필요-사항)

---

## 보안 이슈 목록

### Critical

#### [SEC-C1] Unit 1 — App Secret이 HTTP 헤더에 매번 포함됨
- **파일**: `agent-a574e260/local_server/broker/kiwoom/auth.py:108-113`
- **내용**: `build_headers()`가 `appkey`와 `appsecret`을 모든 요청 헤더에 포함한다. 키움 REST API 문서 기준으로 토큰 발급 요청에만 secret이 필요하고, 이후 요청에는 `Authorization: Bearer {token}`만 사용해야 한다.
- **위험**: 모든 API 요청 로그에 App Secret이 포함되면 로그 수집 시스템, 키움 서버 등에 secret이 노출된다.
- **코드**:
  ```python
  # auth.py:101-113 — 모든 요청에 appsecret 포함
  async def build_headers(self) -> dict[str, str]:
      token = await self.get_access_token()
      return {
          "Authorization": f"Bearer {token}",
          "appkey": self._app_key,
          "appsecret": self._app_secret,  # 위험: 매 요청마다 포함
          "Content-Type": "application/json; charset=utf-8",
      }
  ```
- **수정**: 시세 조회, 주문 등 일반 요청은 `Authorization` + `appkey`만 포함. `appsecret`은 토큰 발급(`_fetch_token`) 시에만 사용.

---

#### [SEC-C2] Unit 4 — 개발 기본값 `SECRET_KEY`가 취약
- **파일**: `cloud_server/core/config.py:29`
- **내용**: `SECRET_KEY`의 기본값이 `"dev-secret-key-change-in-production"` 이다. `lru_cache`로 싱글톤이 생성되므로 환경변수 미설정 시 운영 환경에서도 이 값이 사용될 수 있다.
- **위험**: 기본 Secret Key로 임의의 JWT를 서명할 수 있어 전체 인증 체계가 무력화된다.
- **코드**:
  ```python
  SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
  ```
- **수정**: 기본값 제거. 환경변수 미설정 시 `RuntimeError` 발생. 운영 환경에서 반드시 64자 이상 랜덤 값 설정 강제.

---

### High

#### [SEC-H1] Unit 2 — 로컬 서버 API 엔드포인트에 인증 없음
- **파일**: `agent-a643a319/local_server/routers/trading.py`, `routers/rules.py`, `routers/logs.py`, `routers/config.py`
- **내용**: `/api/trading/order`, `/api/strategy/start`, `/api/rules/sync`, `/api/config`, `/api/logs` 등 모든 엔드포인트에 인증(JWT/세션/토큰) 없이 접근 가능하다. 현재 CORS만으로 보호하고 있다.
- **위험**: 로컬 네트워크(같은 Wi-Fi)의 다른 장치, 또는 브라우저 CORS bypass 공격으로 임의 주문 발행, 설정 변경이 가능하다.
- **맥락**: 설계상 `127.0.0.1`만 바인딩하지만 (`main.py:153`), 이것은 OS 레벨 방어이고 앱 레벨 인증이 없다. CORS는 브라우저에만 적용된다.
- **수정**: 로컬 서버 전용 단순 토큰(환경변수 또는 keyring 저장)으로 Bearer 인증 추가. 최소한 `POST /api/trading/order`와 `POST /api/strategy/start`에는 필수.

---

#### [SEC-H2] Unit 4 — `EmailVerificationToken.token`이 평문 저장
- **파일**: `cloud_server/models/user.py:63`, `cloud_server/api/auth.py:100-101`
- **내용**: `RefreshToken`은 SHA-256 해시로 저장하는데, `EmailVerificationToken`과 `PasswordResetToken`의 `token` 컬럼은 평문 저장이다.
- **위험**: DB 유출 시 유효한 인증 링크를 공격자가 직접 사용 가능. 특히 비밀번호 재설정 토큰(10분 TTL)은 즉각적 계정 탈취로 이어진다.
- **코드**:
  ```python
  # models/user.py:63 — 평문 token 컬럼
  token = Column(String(64), nullable=False, index=True)

  # api/auth.py:100 — 평문으로 DB 조회
  ev = db.query(EmailVerificationToken).filter(
      EmailVerificationToken.token == token, ...
  )
  ```
- **수정**: `RefreshToken`과 동일하게 `token_hash` 컬럼(SHA-256)으로 교체. 발급 시 `hash_token()` 적용, 검증 시 쿼리 파라미터에도 `hash_token()` 적용.

---

#### [SEC-H3] Unit 4 — X-Forwarded-For 헤더 스푸핑으로 Rate Limiting 우회
- **파일**: `cloud_server/core/rate_limit.py:40-45`
- **내용**: `_get_ip()`가 `X-Forwarded-For` 헤더를 신뢰하여 Rate Limiting 키로 사용한다. 공격자가 임의의 IP를 `X-Forwarded-For`에 넣어 무제한 요청 가능.
- **코드**:
  ```python
  def _get_ip(request: Request) -> str:
      forwarded = request.headers.get("X-Forwarded-For")
      if forwarded:
          return forwarded.split(",")[0].strip()  # 클라이언트 조작 가능
      return request.client.host if request.client else "unknown"
  ```
- **수정**: 리버스 프록시(Nginx)를 신뢰하는 경우 `TRUSTED_PROXIES` 설정 추가. 아니면 `X-Forwarded-For` 무시하고 `request.client.host`만 사용. 또는 `slowapi` 라이브러리를 활용.

---

#### [SEC-H4] Unit 2 — `detail` 필드에 내부 예외 메시지 노출
- **파일**: `agent-a643a319/local_server/routers/auth.py:70-72`, `routers/rules.py:60-62`
- **내용**: `HTTPException`의 `detail`에 `str(e)`를 직접 포함하여 내부 예외 메시지(파일 경로, 키링 구조, 스택 정보 등)가 API 응답에 노출된다.
- **코드**:
  ```python
  # auth.py:70
  raise HTTPException(
      status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
      detail=f"토큰 발급 실패: {e}",  # 내부 오류 직접 노출
  )
  ```
- **수정**: 500 응답에는 일반적인 메시지만 반환. 상세 오류는 서버 로그에만 기록.

---

### Medium

#### [SEC-M1] Unit 4 — CORS `allow_origins`에 와일드카드 수준 설정
- **파일**: `cloud_server/core/config.py:59-62`, `cloud_server/main.py:70-76`
- **내용**: `CORS_ORIGINS`가 `["http://localhost:5173", "http://localhost:3000"]`으로 하드코딩되어 있고, 운영 환경의 실제 도메인이 없다. 또한 `allow_credentials=True`와 함께 사용 시 `allow_origins=["*"]`는 불가능하지만 도메인 검증이 느슨하다.
- **수정**: 환경변수 `CORS_ORIGINS`로 운영/개발 분리. 운영 시 정확한 도메인(예: `https://stockvision.com`)으로 제한.

---

#### [SEC-M2] Unit 1 — WebSocket 접속키로 Access Token을 그대로 사용
- **파일**: `agent-a574e260/local_server/broker/kiwoom/ws.py:151-152`
- **내용**: `_get_approval_key()`가 WebSocket 접속용 approval_key를 발급받지 않고 access_token을 그대로 반환한다. 주석에 "실제 API에서는 별도 endpoint 필요"라고 명시되어 있으나 미구현 상태.
- **위험**: WebSocket 메시지에 access_token이 평문으로 포함된다. approval_key와 access_token은 별도 발급이어야 한다.
- **코드**:
  ```python
  async def _get_approval_key(self) -> str:
      # 현재는 access_token을 그대로 사용 (실제 API에서는 별도 endpoint 필요)
      return await self._auth.get_access_token()
  ```
- **수정**: 키움 WebSocket approval_key 발급 endpoint(`/oauth2/Approval`) 호출로 교체.

---

#### [SEC-M3] Unit 2 — 하트비트에 인증 토큰 미사용
- **파일**: `agent-a643a319/local_server/cloud/heartbeat.py:41`, `cloud/client.py:28-43`
- **내용**: `CloudClient` 생성 시 `api_token=None`으로 기본값을 사용한다. 클라우드 서버의 `/api/v1/heartbeat`는 JWT 인증이 필요한데 (`dependencies.py:current_user`), 로컬 서버는 인증 없이 요청을 보낸다.
- **코드**:
  ```python
  # heartbeat.py:41
  client = CloudClient(base_url=cloud_url)  # api_token 미전달
  ```
- **수정**: 로컬 서버 인증 토큰을 keyring에서 로드하여 `CloudClient(api_token=token)` 전달.

---

#### [SEC-M4] Unit 4 — `PasswordResetToken` 사용 후 즉시 삭제 안 됨
- **파일**: `cloud_server/api/auth.py:250-254`
- **내용**: 비밀번호 재설정 완료 시 `prt.used = True`만 설정하고 DB에서 삭제하지 않는다. `used=True`인 토큰이 DB에 계속 쌓인다.
- **수정**: `db.delete(prt)` 추가. 또는 만료된 토큰 정리 배치 작업 추가.

---

#### [SEC-M5] Unit 4 — `refresh` 엔드포인트에 Rate Limiting 없음
- **파일**: `cloud_server/api/auth.py:159-195`
- **내용**: `/auth/login`, `/auth/register`, `/auth/forgot-password`는 Rate Limiting이 있지만, `/auth/refresh`는 없다. 유출된 Refresh Token으로 무제한 JWT 발급 시도 가능.
- **수정**: `check_login_rate(request)` 수준의 Rate Limiting 추가.

---

#### [SEC-M6] Unit 2 — `config.json`에 `kiwoom.app_key`, `kiwoom.app_secret` 항목 존재
- **파일**: `agent-a643a319/local_server/config.py:28-31`
- **내용**: `DEFAULT_CONFIG`에 `kiwoom.app_key`, `kiwoom.app_secret` 빈 문자열 필드가 있다. `config_store.py`에서 이 값이 오면 keyring으로 이동시키지만, 외부에서 `PATCH /api/config`로 보낸 json에 키가 포함되면 config.json에 일시적으로 저장될 수 있다.
- **맥락**: `update_config`에서 `pop()`으로 분리하므로 실제 저장은 방지된다. 하지만 필드가 config schema에 있어서 혼란 유발.
- **수정**: DEFAULT_CONFIG에서 `app_key`, `app_secret` 필드 제거. 명세를 통해 "키는 keyring에만 저장"임을 명확히.

---

### Low

#### [SEC-L1] Unit 1 — `datetime.now()` 사용 (timezone-naive)
- **파일**: `agent-a574e260/local_server/broker/kiwoom/auth.py:68,89`
- **내용**: `datetime.now()`는 로컬 타임존 기준이다. 시스템 시계 변경 또는 타임존 불일치 시 토큰 갱신 시점 계산이 틀릴 수 있다.
- **수정**: `datetime.now(timezone.utc)` 사용.

---

#### [SEC-L2] Unit 4 — `health` 엔드포인트가 환경 정보 노출
- **파일**: `cloud_server/main.py:119-123`
- **내용**: `/health` 응답에 `"env": settings.ENV`가 포함된다. 운영 환경(`production`/`development`)이 외부에 노출된다.
- **수정**: `env` 필드 제거 또는 내부망에서만 접근 가능하도록 제한.

---

#### [SEC-L3] Unit 1 — `KIWOOM_BASE_URL` 상수 중복 정의
- **파일**: `auth.py:14`, `order.py:22`, `quote.py:17`
- **내용**: 동일한 `KIWOOM_BASE_URL` 상수가 3개 모듈에 각각 정의되어 있다. 보안 관점에서 URL이 변경될 때 한 곳만 수정하면 나머지가 구버전으로 남을 수 있다.
- **수정**: `auth.py` 또는 별도 `constants.py`에 한 번만 정의하고 import.

---

## 코드 품질 이슈 목록

### 설계/아키텍처

#### [QUA-A1] Unit 1 — `adapter.py`에서 `_local_orders` private 속성 직접 접근
- **파일**: `agent-a574e260/local_server/broker/kiwoom/adapter.py:220`
- **내용**: `KiwoomAdapter.cancel_order()`가 `self._reconciler._local_orders`에 직접 접근한다. 캡슐화 위반.
- **코드**:
  ```python
  local = self._reconciler._local_orders.get(order_id)  # private 직접 접근
  ```
- **수정**: `Reconciler`에 `get_order(order_id: str) -> Optional[OrderResult]` 공개 메서드 추가.

---

#### [QUA-A2] Unit 2 — `LogDB.write()`가 async 컨텍스트에서 blocking I/O 실행
- **파일**: `agent-a643a319/local_server/storage/log_db.py:57-83`
- **내용**: `LogDB`는 동기 sqlite3를 사용한다. FastAPI async 핸들러(`trading.py`, `logs.py`)에서 직접 호출하면 이벤트 루프가 블로킹된다.
- **코드**:
  ```python
  # log_db.py:78 — 동기 sqlite3
  with sqlite3.connect(str(self._path)) as conn:
      cursor = conn.execute(...)

  # trading.py:111 — async 핸들러에서 직접 호출
  async def place_order(body: OrderRequest) -> dict[str, Any]:
      log_db.write(...)  # blocking!
  ```
- **수정**: `aiosqlite`로 교체하거나 `asyncio.get_event_loop().run_in_executor()`로 스레드풀에서 실행.

---

#### [QUA-A3] Unit 1 — `httpx.AsyncClient`를 매 요청마다 생성/소멸
- **파일**: `auth.py:80`, `order.py:121,174,216`, `quote.py:65,109`
- **내용**: 모든 HTTP 요청에서 `async with httpx.AsyncClient(...) as client:`를 사용하여 매번 클라이언트를 생성한다. 커넥션 풀이 재사용되지 않아 성능 저하와 소켓 낭비.
- **수정**: `KiwoomAuth`, `KiwoomOrder`, `KiwoomQuote` 클래스 레벨에서 `httpx.AsyncClient` 공유. `KiwoomAdapter`의 `connect()`/`disconnect()` 라이프사이클에서 관리.

---

#### [QUA-A4] Unit 2 — `RulesCache._save()`가 동기 파일 I/O (async 핸들러에서 호출)
- **파일**: `agent-a643a319/local_server/storage/rules_cache.py:41-46`, `routers/rules.py:64`
- **내용**: `cache.sync(rules)`가 `_save()`를 호출하고, 이는 async 라우터에서 블로킹 I/O를 발생시킨다.
- **수정**: `anyio.to_thread.run_sync()` 또는 `aiofiles`로 비동기화.

---

### 에러 핸들링

#### [QUA-E1] Unit 1 — `_do_connect()` 내부 예외 처리의 이중 전환 문제
- **파일**: `agent-a574e260/local_server/broker/kiwoom/adapter.py:94-118`
- **내용**: 연결 실패 시 `ConnectionState.ERROR`로 전환을 시도하는데, 이 전환이 실패할 경우 또 다른 예외가 발생한다 (내부 `try/except Exception: pass`로 무시). 연결 실패의 원인이 불명확해진다.
- **코드**:
  ```python
  except Exception as exc:
      try:
          await self._state.transition(ConnectionState.ERROR)
      except Exception:
          pass  # 무시 — 위험할 수 있음
      raise ConnectionError(f"키움 연결 실패: {exc}") from exc
  ```
- **수정**: `StateMachine.reset()`을 사용하거나, 전환 실패를 명시적으로 로깅.

---

#### [QUA-E2] Unit 2 — `RulesCache._save()` 예외 미처리
- **파일**: `agent-a643a319/local_server/storage/rules_cache.py:41-46`
- **내용**: 파일 쓰기 실패 시 예외가 그대로 전파되어 `/api/rules/sync` 호출이 500으로 실패한다. 파일 저장 실패는 경고로 처리하고 메모리 캐시는 유지하는 편이 낫다.
- **수정**:
  ```python
  def _save(self) -> None:
      try:
          self._path.parent.mkdir(parents=True, exist_ok=True)
          with self._path.open("w", encoding="utf-8") as f:
              json.dump(self._rules, f, ensure_ascii=False, indent=2)
      except OSError as e:
          logger.error("규칙 캐시 저장 실패: %s", e)
  ```

---

#### [QUA-E3] Unit 4 — `rule_service.py`의 DB 예외를 모두 409로 처리
- **파일**: `cloud_server/services/rule_service.py:77-82`
- **내용**: `db.commit()` 실패 시 모든 예외를 409("같은 이름의 규칙이 이미 존재합니다.")로 처리한다. 네트워크 오류, DB 연결 실패, 기타 무결성 오류가 모두 같은 메시지로 반환된다.
- **코드**:
  ```python
  try:
      db.commit()
  except Exception:
      db.rollback()
      raise HTTPException(status_code=409, detail="같은 이름의 규칙이 이미 존재합니다.")
  ```
- **수정**: `sqlalchemy.exc.IntegrityError`만 409로 처리. 나머지는 500 반환.

---

#### [QUA-E4] Unit 1 — `reconciler.py`에서 ORPHAN 처리 로직이 부정확
- **파일**: `agent-a574e260/local_server/broker/kiwoom/reconciler.py:167-168`
- **내용**: 서버 미체결 목록에 없는 로컬 주문을 무조건 `FILLED`로 처리한다. 실제로는 취소된 경우도 있고, 조회 실패로 빠진 경우도 있다.
- **코드**:
  ```python
  # 서버에서 사라진 주문 = 체결/취소된 것으로 가정
  self.update_order(order_id, OrderStatus.FILLED)
  ```
- **수정**: `ORPHAN` 이벤트 발생 후 상태를 `FILLED`로 직접 변경하지 말고, 상위 레이어에서 콜백을 통해 결정하도록 위임.

---

### 타입 힌트 / 네이밍

#### [QUA-T1] Unit 4 — `main.py` 미들웨어에서 타입 힌트 누락
- **파일**: `cloud_server/main.py:81`
- **내용**: `request_logging` 미들웨어의 `call_next` 파라미터에 타입 힌트가 없다.
- **코드**:
  ```python
  async def request_logging(request: Request, call_next):  # call_next 타입 없음
  ```
- **수정**: `from starlette.middleware.base import RequestResponseEndpoint` 또는 `Callable` 타입 추가.

---

#### [QUA-T2] Unit 4 — `lifespan` 제너레이터 반환 타입 힌트 누락
- **파일**: `cloud_server/main.py:36`
- **내용**: `async def lifespan(app: FastAPI):` — 반환 타입이 없다. 로컬 서버(`agent-a643a319/local_server/main.py:24`)는 `-> AsyncIterator[None]`으로 올바르게 선언.
- **수정**: `async def lifespan(app: FastAPI) -> AsyncIterator[None]:` + `from typing import AsyncIterator` 추가.

---

#### [QUA-T3] Unit 4 — `admin.py`에서 `get_daily_quotes` 파라미터 `start/end` 미검증
- **파일**: `cloud_server/api/admin.py:197-200`
- **내용**: `start`, `end` 파라미터를 `date.fromisoformat(start)`로 변환하는데, 형식이 맞지 않으면 `ValueError`가 500으로 반환된다. Pydantic으로 타입 강제하거나 try/except 필요.
- **코드**:
  ```python
  if start:
      query = query.filter(DailyBar.date >= date.fromisoformat(start))  # ValueError 미처리
  ```
- **수정**: `start: date | None = Query(None)`으로 Pydantic이 자동 파싱하도록 변경.

---

#### [QUA-T4] Unit 1 — `_build_subscribe_msg` 반환 타입이 `dict` (너무 광범위)
- **파일**: `agent-a574e260/local_server/broker/kiwoom/ws.py:154-156`
- **내용**: 반환 타입이 `dict`이고 내부 구조가 런타임에만 확인된다. `TypedDict`나 `dataclass`로 구조 명시 권장.
- **수정**: 마이너한 이슈. 필요 시 `TypedDict` 정의.

---

### 리소스 관리

#### [QUA-R1] Unit 4 — `get_db_session()` 세션 관리 책임 불명확
- **파일**: `cloud_server/core/database.py:38-40`
- **내용**: `get_db_session()`은 세션을 반환하지만 컨텍스트 매니저나 close 보장이 없다. 호출자가 `db.close()`를 잊으면 커넥션 누수.
- **코드**:
  ```python
  def get_db_session():
      return SessionLocal()  # close 책임이 호출자에게 있음, 불명확
  ```
- **수정**: 문서에 "반드시 close 필요"를 명시하거나 `@contextmanager`로 래핑.

---

#### [QUA-R2] Unit 1 — `KiwoomWS.subscribe()`가 approval_key를 매 구독마다 재발급
- **파일**: `agent-a574e260/local_server/broker/kiwoom/ws.py:101-122`
- **내용**: 종목 목록으로 subscribe 시 모든 종목에 대해 `await self._get_approval_key()`를 호출한다. 내부적으로는 `get_access_token()`이어서 캐시되지만, 향후 실제 approval_key endpoint로 교체 시 매 구독마다 HTTP 요청이 발생한다.
- **수정**: loop 밖에서 approval_key를 한 번만 획득한 후 재사용 (현재 코드의 line 114가 루프 밖이므로 실제로는 괜찮음. `unsubscribe()`의 line 133도 동일하게 루프 밖).

---

### async 정합성

#### [QUA-AS1] Unit 4 — FastAPI 라우터 함수가 `async def` 대신 `def` 사용
- **파일**: `cloud_server/api/auth.py:66,119,159,...`, `cloud_server/api/rules.py:65,...`
- **내용**: 대부분의 라우터 함수가 `def`(동기)로 선언되어 있다. DB I/O가 있는 함수이므로 `async def`로 선언하거나, 아니면 명시적으로 `def`를 선택한 이유를 주석으로 설명해야 한다.
- **맥락**: FastAPI는 `def` 함수를 자동으로 스레드풀에서 실행하므로 기술적으로 문제없다. 하지만 `async def`와 `def` 혼용은 일관성을 해친다.
- **수정**: 팀 컨벤션 결정 후 통일. DB I/O가 있는 라우터는 `def` (FastAPI threadpool) 또는 `async def` + `run_in_executor`로 통일.

---

#### [QUA-AS2] Unit 2 — `ws.py`의 WebSocket에 인증 없음
- **파일**: `agent-a643a319/local_server/routers/ws.py:84-127`
- **내용**: WebSocket 엔드포인트 `/ws`는 인증 없이 즉시 연결을 수락한다. 로컬 서버 전체가 localhost 바인딩이므로 낮은 위험이지만, 설계 원칙상 일관성 필요.

---

### 중복 코드

#### [QUA-D1] Unit 1 + Unit 4 — 유사한 RateLimiter 구현 중복
- **파일**: `agent-a574e260/local_server/broker/kiwoom/rate_limiter.py` vs `cloud_server/core/rate_limit.py`
- **내용**: 두 파일 모두 슬라이딩 윈도우 기반 Rate Limiter를 각각 구현했다. 전자는 asyncio Lock 기반, 후자는 threading Lock 기반이어서 완전 같지는 않지만, 로직의 핵심이 동일하다.
- **맥락**: 두 모듈이 다른 서버에 있고 의존성 분리가 필요하므로 중복이 완전히 나쁜 것은 아님. `sv_core`에 공통 Rate Limiter 추상화를 넣는 것을 검토.

---

## 우선순위별 수정 필요 사항

### P0 — 즉시 수정 (운영 전 반드시)

| ID | 유닛 | 내용 | 파일 |
|----|------|------|------|
| SEC-C2 | Unit 4 | `SECRET_KEY` 기본값 제거, 미설정 시 RuntimeError | `core/config.py:29` |
| SEC-C1 | Unit 1 | 일반 요청 헤더에서 `appsecret` 제거 | `broker/kiwoom/auth.py:108-113` |
| SEC-H2 | Unit 4 | 이메일/비밀번호 재설정 토큰 해시 저장으로 교체 | `models/user.py`, `api/auth.py` |

### P1 — 단기 수정 (이번 이터레이션)

| ID | 유닛 | 내용 | 파일 |
|----|------|------|------|
| SEC-H1 | Unit 2 | 로컬 서버 API 최소 토큰 인증 추가 | `routers/trading.py`, `routers/config.py` |
| SEC-H3 | Unit 4 | X-Forwarded-For 신뢰 제한 또는 slowapi 사용 | `core/rate_limit.py` |
| SEC-H4 | Unit 2 | 500 응답에 내부 예외 메시지 노출 제거 | `routers/auth.py:70-72` |
| SEC-M2 | Unit 1 | WebSocket approval_key 별도 endpoint 호출 구현 | `broker/kiwoom/ws.py:151-152` |
| SEC-M3 | Unit 2 | 하트비트 클라이언트에 JWT 토큰 전달 | `cloud/heartbeat.py:41` |
| QUA-A1 | Unit 1 | `Reconciler._local_orders` 직접 접근 캡슐화 | `broker/kiwoom/adapter.py:220` |
| QUA-A2 | Unit 2 | `LogDB.write()` async 컨텍스트 블로킹 해결 | `storage/log_db.py` |
| QUA-E2 | Unit 2 | `RulesCache._save()` 예외 처리 추가 | `storage/rules_cache.py:41-46` |
| QUA-E3 | Unit 4 | DB 예외 분류 세분화 | `services/rule_service.py:77-82` |

### P2 — 중기 수정 (다음 이터레이션)

| ID | 유닛 | 내용 | 파일 |
|----|------|------|------|
| SEC-M5 | Unit 4 | `/auth/refresh`에 Rate Limiting 추가 | `api/auth.py` |
| SEC-M4 | Unit 4 | `PasswordResetToken` 사용 후 삭제 | `api/auth.py:250-254` |
| SEC-L1 | Unit 1 | `datetime.now()` → `datetime.now(timezone.utc)` | `broker/kiwoom/auth.py` |
| QUA-A3 | Unit 1 | `httpx.AsyncClient` 재사용으로 커넥션 풀 활성화 | `broker/kiwoom/*.py` |
| QUA-T3 | Unit 4 | `start/end` 파라미터 타입 안전 파싱 | `api/admin.py:197-200` |
| QUA-T2 | Unit 4 | `lifespan` 반환 타입 힌트 추가 | `main.py:36` |
| QUA-AS1 | Unit 4 | 라우터 `def`/`async def` 컨벤션 통일 | `api/auth.py`, `api/rules.py` |
| QUA-E4 | Unit 1 | ORPHAN 주문 처리 로직 수정 | `broker/kiwoom/reconciler.py:167-168` |

### P3 — 개선 검토 (기술 부채)

| ID | 유닛 | 내용 | 파일 |
|----|------|------|------|
| SEC-M1 | Unit 4 | 운영 CORS Origins 환경변수화 | `core/config.py:59-62` |
| SEC-M6 | Unit 2 | config schema에서 `app_key`/`app_secret` 제거 | `config.py:28-31` |
| SEC-L2 | Unit 4 | `/health` 응답에서 `env` 필드 제거 | `main.py:119-123` |
| SEC-L3 | Unit 1 | `KIWOOM_BASE_URL` 상수 단일화 | `auth.py`, `order.py`, `quote.py` |
| QUA-R1 | Unit 4 | `get_db_session()` 컨텍스트 매니저 래핑 | `core/database.py:38-40` |
| QUA-T1 | Unit 4 | 미들웨어 `call_next` 타입 힌트 추가 | `main.py:81` |
| QUA-D1 | Unit 1+4 | RateLimiter 공통 추상화 `sv_core`로 이동 검토 | — |

---

## 종합 평가

### 잘 된 점
- **Unit 1**: 토큰 갱신 Lock, 멱등성 보장(IdempotencyGuard), 상태 머신, 지수 백오프 재연결 — 운영 안정성을 고려한 설계가 탁월함.
- **Unit 2**: Windows Keyring으로 자격증명 관리, localhost 바인딩, config에서 민감 정보 마스킹 — 로컬 서버 보안 원칙이 잘 지켜짐.
- **Unit 4**: Argon2id OWASP 권장 파라미터, Refresh Token Rotation, SHA-256 해시 DB 저장, AES-256-GCM 암호화 — 클라우드 인증 체계가 전반적으로 견고함.

### 주요 우려 사항
1. **Unit 1의 App Secret 헤더 노출**: 가장 시급. 금융 API Key가 모든 요청 로그에 노출됨.
2. **Unit 4의 기본 SECRET_KEY**: 운영 배포 시 이 값이 그대로 사용되면 JWT 전체 무력화.
3. **이메일/비밀번호 재설정 토큰 평문 저장**: Refresh Token과 일관성 없는 보안 처리.
4. **로컬 서버 API 인증 없음**: CORS는 브라우저 방어이고 앱 레벨 인증이 없어 로컬 네트워크 접근에 취약.
