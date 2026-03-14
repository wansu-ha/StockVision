# Auth Security — 인증/보안 취약점 수정

> 작성일: 2026-03-13 | 상태: 구현 완료

---

## 목표

인증 누락 엔드포인트 보호, 시크릿 노출 차단, IP 스푸핑 방지를 통해 **보안 수준**을 확보한다.

근거 자료: `docs/research/review-local-server.md`, `docs/research/review-cloud-server.md`, `docs/research/review-frontend.md`

---

## 범위

### 포함 (6건)

로컬 서버 인증 누락, WS 인증 방식, 클라우드 rate limiter, 프론트엔드 인증 헤더.

### 미포함

- 거래 안전 → `spec/trading-safety/`
- 안정성 (OAuth 동시성, 재연결) → `spec/stability/`
- HTTPS/TLS — 로컬 서버는 `127.0.0.1` 전용이므로 대상 외

---

## AS-1: WS 인증 방식 변경 (LS-C5)

**현상**: `ws.py:101` `local_secret`이 `ws://...?sec=...` URL query param으로 전달. 브라우저 히스토리/동일 PC 프로세스가 URL을 탈취 가능.
**맥락**: 브라우저 WS API는 핸드셰이크 시 커스텀 헤더를 지원하지 않으므로 query param이 사실상 유일한 방법. 하지만 로그/히스토리 노출은 방지해야 함.
**수정**:
- WS 핸드셰이크 후 첫 프레임에서 `{"type": "auth", "secret": "..."}` 전송
- 서버가 5초 내 auth 프레임 미수신 시 연결 종료
- URL에서 `sec` 파라미터 제거
**파일**: `local_server/routers/ws.py`, `frontend/src/hooks/useLocalBridgeWS.ts`
**검증**: URL에 secret 미포함 + 인증 없이 WS 연결 시 5초 후 자동 종료

## AS-2: /api/auth/token + /api/auth/restore 보호 (LS-H1)

**현상**: `auth.py:47` `/api/auth/token`은 임의 JWT POST로 `local_secret` 획득 가능. `auth.py:104` `/api/auth/restore`는 **body 없이도** keyring 토큰이 있으면 `local_secret` 반환 — 더 심각.
**수정 방안** (택 1):
- (a) 최초 등록 시에만 허용, 이후 `require_local_secret` 적용
- (b) 일회성 nonce 생성 → 프론트가 nonce 포함해서 호출
**파일**: `local_server/routers/auth.py`
**검증**: 임의 JWT POST → 403 또는 nonce 미포함 시 거부. restore도 동일.

## AS-3: /api/auth/status 정보 노출 (신규)

**현상**: `auth.py:160` `GET /api/auth/status`가 인증 없이 이메일, 토큰 보유 여부를 반환.
**수정**: `require_local_secret` 추가, 또는 민감 필드(email) 제거.
**파일**: `local_server/routers/auth.py`
**검증**: 인증 없이 호출 → 403 또는 이메일 미포함

## AS-4: Rate limiter 스푸핑 방지 (CS-H3)

**현상**: `rate_limit.py:40` `X-Forwarded-For` 무조건 신뢰. 클라이언트가 임의 IP 설정으로 rate limit 우회 가능.
**수정**: Render 프록시의 rightmost IP 사용, 또는 `request.client.host` 폴백.
**파일**: `cloud_server/core/rate_limit.py`
**검증**: 위조된 `X-Forwarded-For` 헤더로 rate limit 우회 불가

## AS-5: alertsClient → localClient 교체 (FE-C2)

**현상**: `alertsClient.ts:28` bare axios 사용, `X-Local-Secret` 미첨부. 서버 측(`alerts.py`)도 인증 미적용이라 현재는 우연히 동작하지만, TS-2에서 서버 인증 추가 시 완전히 깨짐.
**수정**: `alertsClient.ts`에서 `axios` → `localClient` 교체.
**파일**: `frontend/src/services/alertsClient.ts`
**검증**: 경고 설정 로드/저장 정상 동작 (TS-2 서버 인증 추가 후에도)

## AS-6: DeviceManager + devices.py 페어링 인증 추가 (FE-C4)

**현상**:
- 프론트: `DeviceManager.tsx:25` `handlePairInit/handlePairComplete`에서 raw `fetch()` 사용, `X-Local-Secret` 없음
- 서버: `devices.py:24` `pair_init`, `pair_complete`에 `require_local_secret` 없음. 인증 없이 E2E 키 생성 및 QR 데이터 탈취 가능
**수정**:
- 프론트: `fetch()` → `localClient` 교체
- 서버: `pair_init`, `pair_complete`에 `Depends(require_local_secret)` 추가
**파일**: `frontend/src/components/DeviceManager.tsx`, `local_server/routers/devices.py`
**검증**: 페어링 API 인증 없이 호출 → 403. localClient 사용 시 정상 동작.
**참고**: 디바이스 목록/해제(`cloudDevices.list/deactivate`)는 cloudClient JWT 인증으로 정상.

---

## 수용 기준

- [x] WS URL에 secret 미포함
- [x] /api/auth/token, /api/auth/restore 무단 호출 차단
- [x] /api/auth/status 이메일 노출 차단
- [x] Rate limiter IP 스푸핑 불가
- [x] 경고 설정 로드/저장 정상 (localClient 사용)
- [x] 디바이스 페어링 인증 적용 (프론트 + 서버)

---

## WS 프로토콜 변경

- 로컬 WS (`/ws`): URL query `sec` 제거 → 첫 프레임 auth 방식
- 프론트: WS 연결 후 `{"type":"auth","secret":"..."}` 전송

---

## 참고 파일

- `local_server/routers/ws.py` — WS 인증 (AS-1)
- `local_server/routers/auth.py` — 토큰 등록/복원/상태 (AS-2, AS-3)
- `cloud_server/core/rate_limit.py` — IP 스푸핑 (AS-4)
- `frontend/src/services/alertsClient.ts` — 인증 (AS-5)
- `frontend/src/components/DeviceManager.tsx` — 인증 (AS-6)
- `local_server/routers/devices.py` — pair 인증 (AS-6)
- `docs/research/review-local-server.md` — 근거 자료
- `docs/research/review-cloud-server.md` — 근거 자료
- `docs/research/review-frontend.md` — 근거 자료
