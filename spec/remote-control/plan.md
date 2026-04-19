# 원격 제어 구현 계획

> 작성일: 2026-03-12 | 상태: 구현 완료 (SUPERSEDED by `spec/remote-ops/`) | Phase C (C6 + C7 + C8)

## 개요

원격 모드에서 상태 조회, 킬스위치, 엔진 재개/무장, PWA+FCM 알림, 외부 주문 감지를 구현한다.

핵심 흐름:
```
[로컬 서버]
    ↓ 30초마다 상태 push
[클라우드 서버]
    ↓ 저장 + WebSocket relay 유지
[원격 앱/웹 (PWA)]
    ↓ FCM 토큰 등록
[Firebase Admin SDK (FCM)]
    ↓ 푸시 알림
[사용자 브라우저/모바일]
```

## 아키텍처

### 통신 경로

**상태 조회 (Pull/Push)**:
- 로컬 → 클라우드: 30초 주기 push (RemoteStatusSnapshot)
- 클라우드는 최신 스냅샷을 메모리/DB에 저장
- 원격 웹/앱: `GET /api/v1/remote/status` → 클라우드의 최신 스냅샷 반환

**명령 전달 (Push)**:
- 원격 웹/앱: `POST /api/v1/remote/kill` 또는 `POST /api/v1/remote/arm`
- 클라우드: 로컬이 온라인이면 즉시 전달, 오프라인이면 pending 저장
- 로컬: 명령 수신 → 즉시 실행

**알림 전달**:
- 로컬 이벤트 발생 (체결, 오류, 킬스위치 등)
- 로컬 → 클라우드: 상태 push 또는 별도 이벤트 API
- 클라우드: FCM HTTP v1 API로 푸시 토큰 대상으로 알림 전송
- 사용자 브라우저/PWA: Service Worker가 백그라운드에서 수신 → 알림 표시

### WebSocket Relay (선택)

현재 기본은 **30초 주기 Pull/Push**로 설계하되, 나중에 필요시 WebSocket Relay로 전환 가능:
- 로컬 → 클라우드: WS 연결 유지, heartbeat 15초, ping/pong
- 클라우드 → 원격: 같은 WS 또는 별도 relay 채널
- 실시간성 향상 필요 시에만 적용

## 수정 파일 목록

### 클라우드 서버 (`cloud_server/`)

| 파일 | 변경 | 추가 |
|------|------|------|
| `models/remote.py` | 신규 | `RemoteSnapshot` (user_id, snapshot_json, updated_at) |
| `api/remote.py` | 신규 | `/api/v1/remote/status`, `/api/v1/remote/kill`, `/api/v1/remote/arm`, `/api/v1/push/register` |
| `services/remote_service.py` | 신규 | 상태 저장, 명령 관리, 권한 검증 |
| `services/firebase_service.py` | 신규 | FCM 알림 전송 로직 |
| `models/push_token.py` | 신규 | `PushToken` (user_id, token, platform, updated_at) |
| `main.py` | 수정 | Firebase Admin SDK 초기화 |

### 로컬 서버 (`local_server/`)

| 파일 | 변경 | 추가 |
|------|------|------|
| `sync/cloud_sync.py` | 신규 | 30초 주기 상태 push, 로컬→클라우드 HTTPS 호출 |
| `routers/remote.py` | 신규 | 클라우드 릴레이 명령 수신 (킬스위치, arm) |
| `main.py` | 수정 | cloud_sync 태스크 시작 (engine 시작 후) |
| `config.json` | 수정 | `cloud_server_url` 추가 (default: http://localhost:4010) |
| `models.py` 또는 `engine/models.py` | 수정 | `external_order_detected` 필드 추가 |

### 프론트엔드 (`frontend/`)

| 파일 | 변경 | 추가 |
|------|------|------|
| `public/manifest.json` | 신규 | PWA 설정 (app name, icons, theme color, display: standalone) |
| `public/sw.js` | 신규 | Service Worker (캐시 전략 + 푸시 수신) |
| `public/firebase-messaging-sw.js` | 신규 | FCM 백그라운드 메시지 처리 |
| `index.html` | 수정 | manifest 링크, 메타 태그 (theme-color, apple-mobile-web-app-capable) |
| `src/App.tsx` | 수정 | Service Worker 등록, FCM 초기화, 푸시 권한 요청 |
| `src/hooks/useRemoteMode.ts` | 신규 | 원격/로컬 모드 감지 |
| `src/hooks/useRemoteControl.ts` | 신규 | 상태 조회, 킬스위치, arm 명령 |
| `src/hooks/usePushNotification.ts` | 신규 | FCM 토큰 등록, 푸시 권한 관리 |
| `src/components/RemoteStatus.tsx` | 신규 | 원격 상태 조회 UI |
| `src/components/KillSwitchButton.tsx` | 신규 | 킬스위치 버튼 + 다이얼로그 |
| `src/components/ArmDialog.tsx` | 신규 | 2단계 재개/무장 UI |
| `src/components/OpsPanel.tsx` | 수정 | "원격 모드" 배지, 외부 주문 감지 배너 |
| `src/components/MobileNav.tsx` | 신규 | 모바일 하단 고정 네비 (킬스위치 FAB) |
| `src/types/index.ts` | 수정 | `RemoteStatusSnapshot` 타입 추가 |
| `src/services/cloudClient.ts` | 수정 | 원격 API 호출 (status, kill, arm, push register) |
| `.env.example` | 수정 | `VITE_FIREBASE_CONFIG` 추가 |

## 구현 순서

### Step 1: 클라우드 원격 API 기초 (C6 기초)

**목표**: 로컬 상태를 클라우드가 저장하고, 원격 클라이언트가 조회 가능하게

**파일 변경**:
1. `cloud_server/models/remote.py` 작성
   - `RemoteSnapshot` (user_id, snapshot_json, synced_at, local_online, pending_kill)
2. `cloud_server/services/remote_service.py` 작성
   - `save_snapshot(user_id, snapshot_dict)`
   - `get_snapshot(user_id)` → RemoteStatusSnapshot
   - `set_pending_kill(user_id, mode)`
   - `clear_pending_kill(user_id)`
3. `cloud_server/api/remote.py` 작성 (POST /api/v1/remote/sync)
   - 로컬이 POST하는 상태 동기화 API
   - 인증: 로컬 서버 API key (또는 모든 요청에서 body에 user_id 포함)

**검증**:
- [ ] 클라우드 DB에 `remote_snapshots` 테이블 생성 (migration)
- [ ] 로컬 POSTing 없이 수동 curl로 테스트: `curl -X POST http://localhost:4010/api/v1/remote/sync -d '{...}'`

---

### Step 2: 로컬 상태 동기화 (로컬 서버)

**목표**: 로컬 서버가 30초마다 상태를 클라우드에 push

**파일 변경**:
1. `local_server/sync/cloud_sync.py` 작성
   - `RemoteStatusSnapshot` 모델 (로컬 타입, serializable)
   - `CloudSync` 클래스:
     - `__init__(local_url, cloud_url, user_id, interval=30)`
     - `async start()` — 백그라운드 태스크
     - `async stop()`
     - `_build_snapshot()` — 엔진, 브로커, 계좌 상태 수집
     - `async _push_snapshot()` — HTTP POST to cloud
2. `local_server/main.py` 수정
   - 앱 시작 시 `cloud_sync.start()` 호출 (engine 시작 후)
   - 앱 종료 시 `cloud_sync.stop()` 호출
3. `local_server/config.json` 수정
   - `"cloud_server_url": "http://localhost:4010"` 기본값

**검증**:
- [ ] 로컬 서버 시작 후 클라우드 DB 확인 — `remote_snapshots` 테이블에 매 30초 신 레코드 삽입
- [ ] 로컬 오프라인 시 — 클라우드 DB에 마지막 `synced_at` 유지, UI에서 "마지막 동기화: 3분 전" 표시

---

### Step 3: 원격 상태 조회 API (C6-1 조회)

**목표**: 원격 웹에서 `/api/v1/remote/status` 호출 → 최신 스냅샷 반환

**파일 변경**:
1. `cloud_server/api/remote.py` 추가
   ```python
   @router.get("/api/v1/remote/status")
   async def get_remote_status(user=Depends(require_auth)) -> dict:
       """
       권한 확인 후 최신 스냅샷 반환.
       로컬 온라인: 실시간 상태
       로컬 오프라인: 마지막 동기화 정보 + "마지막 동기화: X분 전" 경고
       """
       service = remote_service.get_snapshot(user["user_id"])
       return {
           "success": True,
           "data": service,
       }
   ```

**검증**:
- [ ] 원격 웹에서 API 호출: 계좌 요약, 신호/체결/오류 수 확인
- [ ] 오프라인 시 마지막 동기화 시각 확인

---

### Step 4: 킬스위치 API (C6-2 정지)

**목표**: 원격에서 1탭 + 1회 확인으로 엔진 정지

**파일 변경**:
1. `cloud_server/api/remote.py` 추가
   ```python
   @router.post("/api/v1/remote/kill")
   async def kill_remote_engine(
       body: KillBody,  # { mode: 'stop_new' | 'stop_all' }
       user=Depends(require_auth)
   ) -> dict:
       """
       1. 로컬 온라인 → 즉시 명령 전달
       2. 로컬 오프라인 → pending_kill 저장 → 복귀 시 적용
       """
   ```
2. `local_server/routers/remote.py` 신규 작성
   ```python
   @router.post("/remote/kill")
   async def receive_kill_command(body: KillBody):
       """클라우드에서 받은 정지 명령 즉시 실행"""
       engine.stop(mode=body.mode)
       engine.safeguard.disarm()
   ```
3. `local_server/sync/cloud_sync.py` 수정
   - `_pull_pending_commands()` — 시작 시 pending_kill 확인
   - 있으면 즉시 실행

**검증**:
- [ ] 원격 웹에서 킬스위치 탭 → 로컬 콘솔에 "Engine stopped" 로그
- [ ] 오프라인 중 킬스위치 탭 → "명령 저장됨" 메시지
- [ ] 로컬 복귀 후 자동 정지 확인

---

### Step 5: 엔진 재개/무장 API (C7 2단계 확인)

**목표**: 원격에서 2단계 확인을 거쳐 엔진 재개

**파일 변경**:
1. `cloud_server/models/confirm_code.py` 신규
   - `ConfirmCode` (user_id, code, action, expires_at, used)
   - TTL 30초
2. `cloud_server/services/remote_service.py` 추가
   ```python
   def initiate_arm() -> str:
       """확인 코드 생성 후 반환"""
       code = generate_random_code()  # 6자리
       db에 저장 (expires_at=now+30s, used=False)
       return code

   def confirm_arm(user_id: str, code: str) -> bool:
       """코드 검증 후 arm 실행"""
       확인_성공이면: 로컬에 arm 명령 전달
   ```
3. `cloud_server/api/remote.py` 추가
   ```python
   @router.post("/api/v1/remote/arm/initiate")
   async def initiate_arm(user=Depends(require_auth)):
       """첫 번째 단계: 확인 코드 생성"""
       code = remote_service.initiate_arm(user["user_id"])
       return { "success": True, "data": { "code": code } }

   @router.post("/api/v1/remote/arm/confirm")
   async def confirm_arm(body, user=Depends(require_auth)):
       """두 번째 단계: 확인 코드 제출"""
       ok = remote_service.confirm_arm(user["user_id"], body.code)
       if ok:
           전송_arm_명령_to_로컬()
       return { "success": ok }
   ```
4. `local_server/routers/remote.py` 추가
   ```python
   @router.post("/remote/arm")
   async def receive_arm_command():
       """클라우드에서 받은 재개 명령"""
       engine.arm()
       engine.safeguard.reset_halted()
   ```

**검증**:
- [ ] 원격 웹: "재개" 버튼 → 확인 코드 요청 → 입력 다이얼로그 → 로컬 콘솔 "Engine armed"
- [ ] 확인 코드 30초 만료 후 실패 메시지
- [ ] 조건 미충족 시 ("브로커 미연결") 명확한 오류 메시지

---

### Step 6: 원격 모드 감지 및 UI (프론트엔드)

**목표**: 로컬/원격 모드를 자동 감지 → UI 차이 적용

**파일 변경**:
1. `frontend/src/hooks/useRemoteMode.ts` 신규
   ```typescript
   export function useRemoteMode() {
     // 로컬 서버 직접 연결 시도
     // 실패 → 원격 모드
     // 성공 → 로컬 모드
     return { isRemote: boolean, remoteStatusSnapshot }
   }
   ```
2. `frontend/src/components/OpsPanel.tsx` 수정
   - 원격 모드 시 "원격 모드" 배지 추가
   - 실행/설정 버튼 비활성화
   - 킬스위치 + arm 버튼은 활성 유지
3. `frontend/src/components/KillSwitchButton.tsx` 신규
   - FAB (Floating Action Button) 또는 헤더 버튼
   - 클릭 → 확인 다이얼로그 → `POST /api/v1/remote/kill`
4. `frontend/src/components/ArmDialog.tsx` 신규
   - Step 1: "재개" 버튼 → `POST /api/v1/remote/arm/initiate` → 확인 코드 표시
   - Step 2: 사용자가 코드 입력 → `POST /api/v1/remote/arm/confirm`

**검증**:
- [ ] 로컬 서버 연결 가능 → "로컬 모드"
- [ ] 로컬 서버 연결 불가 + 클라우드 인증 → "원격 모드" 배지 표시
- [ ] 원격 모드에서 설정 버튼 비활성화
- [ ] 킬스위치/arm 버튼 활성 유지

---

### Step 7: PWA 설정 (C11 채널)

**목표**: 앱 설치 가능 + 홈화면 추가

**파일 변경**:
1. `frontend/public/manifest.json` 신규
   ```json
   {
     "name": "StockVision",
     "short_name": "SV",
     "description": "AI 기반 주식 시스템매매",
     "start_url": "/",
     "display": "standalone",
     "scope": "/",
     "background_color": "#ffffff",
     "theme_color": "#1f2937",
     "icons": [
       {
         "src": "/icon-192x192.png",
         "sizes": "192x192",
         "type": "image/png",
         "purpose": "any"
       },
       {
         "src": "/icon-512x512.png",
         "sizes": "512x512",
         "type": "image/png",
         "purpose": "any"
       }
     ]
   }
   ```
2. `frontend/index.html` 수정
   ```html
   <link rel="manifest" href="/manifest.json" />
   <meta name="theme-color" content="#1f2937" />
   <meta name="apple-mobile-web-app-capable" content="yes" />
   <meta name="apple-mobile-web-app-status-bar-style" content="default" />
   <meta name="apple-mobile-web-app-title" content="StockVision" />
   <link rel="apple-touch-icon" href="/icon-192x192.png" />
   ```
3. 아이콘 추가: `frontend/public/icon-192x192.png`, `icon-512x512.png` (192x192, 512x512)

**검증**:
- [ ] Android Chrome: "앱 설치" 배너 표시
- [ ] iOS Safari: "공유" → "홈 화면에 추가" 가능
- [ ] 설치 후 standalone mode로 실행 (주소바 없음)

---

### Step 8: FCM 푸시 알림 (C11 알림)

**목표**: 체결, 오류, 킬스위치 등 이벤트 발생 시 푸시 알림

**파일 변경**:
1. `cloud_server/models/push_token.py` 신규
   - `PushToken` (user_id, token, platform, updated_at, is_active)
2. `cloud_server/services/firebase_service.py` 신규
   ```python
   class FirebaseService:
       def __init__(self, credentials_path):
           # Firebase Admin SDK 초기화
           self.app = firebase_admin.initialize_app(
               options={"serviceName": "stockvision"}
           )

       async def send_notification(self, user_id, title, body, data=None):
           """FCM HTTP v1 API로 푸시 알림"""
           # user_id로 push_token 조회
           # FCM에 HTTP POST
   ```
3. `cloud_server/main.py` 수정
   - Firebase Admin SDK 초기화 (ServiceAccountKey JSON)
4. `cloud_server/api/remote.py` 추가
   ```python
   @router.post("/api/v1/push/register")
   async def register_push_token(
       body: { push_token: str, platform: str },
       user=Depends(require_auth)
   ):
       """클라이언트가 FCM 토큰 등록"""
       remote_service.register_push_token(user["user_id"], body.push_token, body.platform)
       return { "success": True }
   ```
5. `frontend/src/hooks/usePushNotification.ts` 신규
   ```typescript
   export function usePushNotification() {
       // Firebase Messaging 초기화
       // notification 권한 요청
       // 토큰 등록: POST /api/v1/push/register
       // onMessage/onBackgroundMessage 리스너
   }
   ```
6. `frontend/src/App.tsx` 수정
   - 로그인 후 `usePushNotification()` 호출
7. `frontend/.env.example` 수정
   - `VITE_FIREBASE_CONFIG="{ \"apiKey\": \"...\", ... }"`

**검증**:
- [ ] 앱 로그인 후 "알림 허용" 권한 요청 표시
- [ ] 푸시 토큰이 클라우드에 저장됨
- [ ] 로컬 이벤트 발생 → 클라우드 알림 전송 → 푸시 수신 확인

---

### Step 9: Firebase 어드민 키 관리 UI (프론트엔드)

**목표**: 어드민이 Firebase Service Account Key를 안전하게 등록

**파일 변경**:
1. `frontend/src/pages/Admin/AdminServiceKeys.tsx` 수정 (또는 신규)
   - 기존 "서비스 키" 페이지에 Firebase 섹션 추가
   - 텍스트 영역에 JSON 붙여 넣기
   - "Firebase 키 업로드" 버튼 → `POST /api/v1/admin/firebase-key`
   - 성공 후 "Firebase 초기화됨" 상태 표시
2. `cloud_server/api/admin.py` 추가
   ```python
   @router.post("/api/v1/admin/firebase-key")
   async def upload_firebase_key(body, admin=Depends(require_admin)):
       """Firebase ServiceAccountKey 업로드"""
       # JSON 파싱
       # 파일 시스템 또는 환경 변수로 저장
       # Firebase Admin SDK 재초기화
   ```

**검증**:
- [ ] 어드민 페이지에서 Firebase 키 업로드 가능
- [ ] 업로드 후 FCM 알림 전송 정상 작동

---

### Step 10: 모바일 반응형 UI (C11 모바일)

**목표**: PC 레이아웃을 모바일에서도 사용 가능

**파일 변경**:
1. `frontend/src/components/MobileNav.tsx` 신규
   - 모바일 하단 고정 네비게이션 (브레드크럼 또는 탭)
2. `frontend/src/components/OpsPanel.tsx` 수정
   - 반응형: PC는 가로 배치, 모바일은 2줄 래핑
3. `frontend/src/components/ListView.tsx` 수정
   - 카드형 레이아웃 전환 (모바일)
4. `frontend/src/components/KillSwitchButton.tsx` 수정
   - 모바일에서 FAB (하단 고정)로 표시

**검증**:
- [ ] 모바일 화면 너비에서 텍스트 잘림 없음
- [ ] 킬스위치 FAB이 모든 화면에서 클릭 가능
- [ ] 스크롤 가능 범위 확인

---

### Step 11: 외부 주문 감지 (C8 reconciliation)

**목표**: 엔진이 알지 못하는 포지션 변동 감지

**파일 변경**:
1. `local_server/engine/models.py` 또는 engine 타입 정의 수정
   - `external_order_detected: bool = False`
2. `local_server/engine/trader.py` 또는 reconciliation 로직 추가
   ```python
   async def reconcile_portfolio():
       """엔진의 포지션 vs 브로커 잔고 비교"""
       broker_positions = await broker.get_holdings()
       engine_positions = engine.portfolio.snapshot()

       if 불일치:
           external_order_detected = True
           # WS 이벤트로 클라우드/프론트에 알림
   ```
3. `local_server/routers/status.py` 수정
   ```python
   data["strategy_engine"]["external_order_detected"] = engine.external_order_detected
   ```
4. `cloud_server/services/remote_service.py` 수정
   - 동기화 받은 snapshot에서 `external_order_detected` 필드 저장
5. `frontend/src/components/OpsPanel.tsx` 수정
   ```tsx
   {remoteStatus.strategy_engine.external_order_detected && (
       <Alert variant="warning">
           ⚠ 외부 주문 감지 — StockVision 외부에서 주문이 실행되었습니다.
       </Alert>
   )}
   ```

**검증**:
- [ ] 테스트: 모의 거래 중 직접 HTS에서 주문 넣기 → 감지 플래그 활성화
- [ ] 프론트에 경고 배너 표시
- [ ] 실행 로그에 "external order detected" 기록

---

### Step 12: 통합 테스트

**목표**: 전체 원격 제어 흐름 검증

**시나리오**:
1. 로컬 서버 시작 → 30초마다 상태 push
2. 원격 웹 로그인 → "원격 모드" 배지 확인
3. 상태 조회 → 계좌/신호/체결 수 확인
4. 킬스위치 탭 → 로컬 엔진 정지 확인
5. arm initiate → 확인 코드 수신 → confirm → 로컬 엔진 재개 확인
6. 로컬 오프라인 → 킬스위치 → "명령 저장" 메시지 → 로컬 복귀 → 자동 정지 확인
7. 푸시 등록 → 로컬 이벤트 발생 → FCM 알림 수신 확인
8. 외부 주문 감지 → 경고 배너 표시

**검증 체크리스트**:
- [ ] 클라우드 DB: `remote_snapshots`, `push_tokens`, `confirm_codes` 테이블 생성
- [ ] 로컬: 30초 주기 push 로그 확인
- [ ] 원격 웹: 모든 API 응답 200
- [ ] 모바일: PWA 설치 가능, 푸시 수신 가능
- [ ] 오프라인: 명령 저장 → 복귀 시 적용
- [ ] 권한: 원격에서 설정 버튼 비활성화, 킬스위치는 활성

## 변경 요약

### 신규 파일 (25개+)

**클라우드**:
- `cloud_server/models/remote.py`
- `cloud_server/models/push_token.py`
- `cloud_server/models/confirm_code.py`
- `cloud_server/api/remote.py`
- `cloud_server/services/remote_service.py`
- `cloud_server/services/firebase_service.py`

**로컬**:
- `local_server/sync/cloud_sync.py`
- `local_server/routers/remote.py`

**프론트엔드**:
- `frontend/public/manifest.json`
- `frontend/public/sw.js`
- `frontend/public/firebase-messaging-sw.js`
- `frontend/public/icon-192x192.png`
- `frontend/public/icon-512x512.png`
- `frontend/src/hooks/useRemoteMode.ts`
- `frontend/src/hooks/useRemoteControl.ts`
- `frontend/src/hooks/usePushNotification.ts`
- `frontend/src/components/RemoteStatus.tsx`
- `frontend/src/components/KillSwitchButton.tsx`
- `frontend/src/components/ArmDialog.tsx`
- `frontend/src/components/MobileNav.tsx`

### 수정 파일 (10개+)

**클라우드**:
- `cloud_server/main.py` (Firebase 초기화)
- `cloud_server/api/admin.py` (Firebase 키 관리)

**로컬**:
- `local_server/main.py` (cloud_sync 태스크 시작)
- `local_server/config.json` (cloud_server_url)
- `local_server/routers/status.py` (external_order_detected)
- `local_server/engine/models.py` 또는 trader.py (reconciliation)

**프론트엔드**:
- `frontend/index.html` (manifest, 메타 태그)
- `frontend/src/App.tsx` (Service Worker, FCM)
- `frontend/src/components/OpsPanel.tsx` (원격 배지, 외부 주문 배너)
- `frontend/src/services/cloudClient.ts` (원격 API)
- `frontend/src/types/index.ts` (타입)
- `frontend/.env.example`

## 수용 기준

### 원격 상태 조회 (C6-1)
- [ ] 원격 웹에서 로컬/브로커/엔진 상태를 실시간 조회할 수 있다
- [ ] 계좌 요약 (잔고, 평가, 손익)이 표시된다
- [ ] 오늘의 신호/체결/오류 수가 표시된다
- [ ] 로컬 서버 오프라인 시 "마지막 동기화: X분 전" 표시

### 킬스위치 (C6-2)
- [ ] 원격 웹에서 1탭 + 1회 확인으로 엔진을 정지할 수 있다
- [ ] 정지 후 "확인됨" 피드백이 표시된다
- [ ] 로컬 서버 오프라인 중 킬스위치 → "명령 저장됨" 메시지
- [ ] 로컬 복귀 후 자동 정지 확인

### 엔진 재개/무장 (C7)
- [ ] 원격 웹: 재개 버튼 → 확인 코드 요청 (initiate)
- [ ] 확인 코드 입력 다이얼로그 표시
- [ ] 코드 제출 → 로컬 arm 실행
- [ ] 조건 미충족 시 ("브로커 미연결") 명확한 사유 표시
- [ ] 30초 TTL 만료 후 재시도 필요

### PWA + FCM (C11)
- [ ] Android Chrome: "앱 설치" 배너 표시
- [ ] iOS Safari: "홈 화면에 추가" 가능
- [ ] 로그인 후 푸시 권한 요청 → 토큰 등록
- [ ] 체결/오류/킬스위치 이벤트 발생 시 FCM 푸시 알림 수신
- [ ] 백그라운드 상태에서도 알림 수신 (Service Worker)
- [ ] 알림 클릭 시 앱 열림

### 모바일 반응형 (C11)
- [ ] 모바일 화면에서 텍스트 잘림 없음
- [ ] 킬스위치 FAB이 모든 화면에서 클릭 가능
- [ ] OpsPanel 2줄 래핑 또는 가로 스크롤

### 외부 주문 감지 (C8)
- [ ] 엔진 외부에서 발생한 포지션 변동이 감지된다
- [ ] 감지 시 OpsPanel에 경고 배너 표시
- [ ] 실행 로그에 "external order detected" 기록
- [ ] 설정에 따라 자동 정지 가능 (선택적)

## 의존성

| 대상 | 상태 |
|------|------|
| 권한 모델 문서 | 초안 (Phase C 시작 시 확정 필요) |
| 로컬 상태 API (`status.py`) | 완료 ✓ |
| 엔진 start/stop | 완료 ✓ |
| 브로커 API (holdings, orders) | 완료 ✓ |
| Firebase Admin SDK | 초기 설정 필요 |
| WebSocket (선택사항) | 나중에 필요시 |

## 선행 작업

1. Firebase 프로젝트 생성 → Service Account Key JSON 발급
2. 권한 모델 문서 상태 초안→확정 전환
3. Cloud Sync retry/exponential backoff 정책 결정 (권장: 3회 재시도, 2초 간격)
4. 확인 코드 생성 알고리즘 (권장: 6자리 숫자)

## 참고 자료

- 권한 모델: `docs/product/remote-permission-model.md`
- 벤치마크: `docs/research/phase-c-dashboard-benchmark.md`
- System Trader: `spec/system-trader/spec.md`
- 기존 상태 API: `local_server/routers/status.py`
- 기존 Admin 패턴: `cloud_server/api/admin.py`
