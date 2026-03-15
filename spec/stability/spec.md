# Stability — 안정성 개선

> 작성일: 2026-03-13 | 상태: 구현 완료

---

## 목표

재연결 실패, asyncio 블로킹, OAuth 경합 조건 등 **런타임 안정성** 이슈를 수정한다.

근거 자료: `docs/research/review-local-server.md`, `docs/research/review-cloud-server.md`, `docs/research/review-frontend.md`

---

## 범위

### 포함 (8건)

브로커 재연결/재구독, asyncio 블로킹, 클라우드 서버 런타임 에러, 프론트엔드 상태 관리.

### 미포함

- 거래 안전 → `spec/trading-safety/`
- 인증/보안 → `spec/auth-security/`
- UX/문서 → `spec/ux-polish/`, `spec/docs-cleanup/`

---

## ST-1: 재연결 후 시세 재구독 (LS-C3)

**현상**: `KisAdapter._do_connect()`는 인증 + WS 연결만 수행. `ws.disconnect()`에서 `_subscribed.clear()`로 구독 목록이 지워져 재연결 후 시세 수신 불가.
**수정**:
- `KisAdapter`에 `_subscribed_symbols: set[str]` 별도 보관
- `_do_connect()` 성공 후 `_ws.subscribe(list(_subscribed_symbols))` 호출
- KIS, 키움 어댑터 모두 적용
**파일**: `local_server/broker/kis/adapter.py:94-107`, `local_server/broker/kis/ws.py:75-91`, `local_server/broker/kis/reconnect.py`
**검증**: 브로커 연결 끊김 → 자동 재연결 → 시세 수신 재개

## ST-2: KisWS 연결 끊김 시 StateMachine 미전환 (신규)

**현상**: `ws.py:190` `_recv_loop`에서 `ConnectionClosed` 예외 시 `_connected = False`만 설정. `StateMachine` 상태를 `ERROR`로 전환하지 않아 `ReconnectManager.on_state_change()`가 트리거되지 않음.
**수정**: `_recv_loop` 예외 핸들러에서 adapter의 `StateMachine` 상태를 `ERROR`로 전환하는 콜백 호출.
**파일**: `local_server/broker/kis/ws.py:183-195`, `local_server/broker/kis/adapter.py:69-79`
**검증**: WS 연결 끊김 → StateMachine ERROR → ReconnectManager 자동 재연결 트리거
**참고**: ST-1과 연관 — 재연결 트리거가 없으면 재구독도 무의미.

## ST-3: LogDB 동기 호출 이벤트 루프 블로킹 (LS-C4)

**현상**: `log_db.py:47` "동기 버전" 명시. `write()`(89-94행)가 순수 동기 SQLite 호출이라 async 컨텍스트에서 직접 호출 시 이벤트 루프 블로킹.
**수정**: `asyncio.to_thread(log_db.write, ...)` 래핑, 또는 aiosqlite 교체.
**파일**: `local_server/storage/log_db.py`
**검증**: 엔진 평가 중 WS/하트비트 지연 없음

## ST-4: collector authenticate → connect (CS-C1)

**현상**: `scheduler.py:157` `await broker.authenticate()` 호출 → `AttributeError`. `BrokerAdapter` ABC에 `authenticate()` 메서드 없음. `connect()`만 존재.
**수정**: `await broker.authenticate()` → `await broker.connect()`.
**파일**: `cloud_server/collector/scheduler.py:157`
**검증**: 서버 시작 시 KIS WS 수집 에러 로그 없음

## ST-5: OAuth 동시 로그인 보호 (CS-C2)

**현상**: `oauth_service.py:130-158` 동시 OAuth 요청 시 동일 이메일 `User` INSERT race condition → `IntegrityError` → 500.
**수정**: `db.flush()` 주변에 `try/except IntegrityError` → 기존 계정 재조회 반환.
**파일**: `cloud_server/services/oauth_service.py:130-158`
**검증**: 동시 OAuth 요청 → 500 없이 정상 응답

## ST-6: password_hash 빈 문자열 처리 (CS-C3)

**현상**: `user.py:29` `nullable=False`인데 OAuth 등록 시 `password_hash=""`(빈 문자열)로 우회. DB 스키마와 코드 의도 불명확.
**수정** (택 1):
- (a) `nullable=True`로 변경 + Alembic 마이그레이션 + 기존 `""` → `None`
- (b) 현행 유지 + `password_hash == ""`를 OAuth 마커로 문서화
**파일**: `cloud_server/models/user.py:29`, `cloud_server/services/oauth_service.py:145`
**검증**: OAuth 신규 가입 → password_hash 의미 명확

## ST-7: Kakao 빈 이메일 충돌 (신규)

**현상**: `oauth_service.py:113-116` Kakao 이메일 미동의 시 `email=""`. `User.email == ""`로 조회하면 다른 미동의 사용자와 충돌 → 잘못된 계정 매칭.
**수정**: 빈 이메일 시 에러 반환 ("이메일 동의 필요"), 또는 `email` nullable + Kakao ID 기반 매칭.
**파일**: `cloud_server/services/oauth_service.py:113-116, 140`
**검증**: Kakao 이메일 미동의 → 적절한 에러 메시지 또는 정상 가입

## ST-8: OAuth 콜백 AuthContext 갱신 (FE-C1)

**현상**: `OAuthCallback.tsx:31-34` 토큰을 스토리지에 저장하지만 `AuthContext`의 `setState`를 호출하지 않음. 메인 페이지 리다이렉트 후 `isAuthenticated=false`로 로그인 페이지로 튕겨남.
**수정**:
- `AuthContext`에 `loginWithTokens(accessToken, refreshToken)` 메서드 추가
- `OAuthCallback`에서 `navigate` 전 `loginWithTokens()` 호출
**파일**: `frontend/src/context/AuthContext.tsx:26-82`, `frontend/src/pages/OAuthCallback.tsx:31-34`
**검증**: Google/Kakao OAuth 로그인 → 메인 대시보드 정상 진입

---

## 수용 기준

- [x] 브로커 재연결 후 시세 수신 재개
- [x] WS 연결 끊김 → StateMachine ERROR → 자동 재연결 트리거
- [x] LogDB 비동기 래핑 완료
- [x] KIS WS 수집 시작 성공 (AttributeError 해소)
- [x] OAuth 동시 로그인 안전
- [x] password_hash 의미 명확화
- [x] Kakao 빈 이메일 충돌 방지
- [x] OAuth 콜백 → 로그인 성공

---

## DB 스키마 변경 (ST-6 선택 시)

- `cloud_server/models/user.py`: `password_hash = Column(String(255), nullable=True)`
- Alembic 마이그레이션: `ALTER COLUMN password_hash DROP NOT NULL` + `UPDATE SET NULL WHERE password_hash = ''`

---

## 참고 파일

- `local_server/broker/kis/adapter.py` — 재연결 (ST-1, ST-2)
- `local_server/broker/kis/ws.py` — WS recv loop (ST-2)
- `local_server/broker/kis/reconnect.py` — ReconnectManager (ST-1)
- `local_server/storage/log_db.py` — asyncio (ST-3)
- `cloud_server/collector/scheduler.py` — authenticate (ST-4)
- `cloud_server/services/oauth_service.py` — OAuth (ST-5, ST-6, ST-7)
- `cloud_server/models/user.py` — password_hash (ST-6)
- `frontend/src/context/AuthContext.tsx` — OAuth 콜백 (ST-8)
- `frontend/src/pages/OAuthCallback.tsx` — OAuth 콜백 (ST-8)
