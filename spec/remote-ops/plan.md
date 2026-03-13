# 원격 제어 구현 계획

> 작성일: 2026-03-12 | 상태: 초안 | Phase C (C6-c)

## 아키텍처

```
원격 디바이스 (PWA)                 클라우드 서버                   로컬 서버
┌──────────────────┐            ┌─────────────────┐           ┌──────────────┐
│ useRemoteMode    │            │                  │           │              │
│ useRemoteControl │── WS ─────►│ RelayManager     │◄── WS ───│ 상태 변경 시  │
│ usePushNotif     │            │ (C6-a)           │           │ state 메시지  │
│                  │            │                  │           │              │
│ RemoteStatus     │            │ FirebaseService  │           │ command 수신  │
│ KillSwitchFAB    │            │   → FCM 발송     │           │ → safeguard  │
│ ArmDialog        │            │                  │           │ → engine     │
│                  │            │ verify-password  │           │ → ACK        │
│ E2ECrypto        │            │   → arm 권한     │           │              │
│ (decrypt)        │            │                  │           │              │
│                  │            │ PushToken 모델   │           │              │
│ ServiceWorker    │◄── FCM ───│                  │           │              │
│ (백그라운드 수신) │            │                  │           │              │
└──────────────────┘            └─────────────────┘           └──────────────┘
```

## 수정 파일 목록

### 클라우드 서버 (신규 3, 수정 3)

| 파일 | 변경 | 내용 |
|------|------|------|
| `cloud_server/models/push_token.py` | 신규 | `PushToken` 모델 |
| `cloud_server/services/firebase_service.py` | 신규 | FCM HTTP v1 API 알림 전송 |
| `cloud_server/api/push.py` | 신규 | 푸시 토큰 등록/해제 API |
| `cloud_server/api/auth.py` | 수정 | `POST /verify-password` 추가 |
| `cloud_server/services/relay_manager.py` | 수정 | alert 수신 시 FCM 트리거 |
| `cloud_server/main.py` | 수정 | Firebase Admin SDK 초기화, push 라우터 등록 |

### 로컬 서버 (수정 2)

| 파일 | 변경 | 내용 |
|------|------|------|
| `local_server/cloud/ws_relay_client.py` | 수정 | command 핸들러 (kill, arm) |
| `local_server/engine/engine.py` 또는 `safeguard.py` | 수정 | 원격 kill/arm 처리 메서드 |

### 프론트엔드 (신규 10, 수정 5)

| 파일 | 변경 | 내용 |
|------|------|------|
| `frontend/public/manifest.json` | 신규 | PWA 설정 |
| `frontend/public/sw.js` | 신규 | Service Worker |
| `frontend/public/firebase-messaging-sw.js` | 신규 | FCM 백그라운드 수신 |
| `frontend/public/icon-192x192.png` | 신규 | PWA 아이콘 |
| `frontend/public/icon-512x512.png` | 신규 | PWA 아이콘 |
| `frontend/src/hooks/useRemoteMode.ts` | 신규 | 로컬/원격 모드 감지 |
| `frontend/src/hooks/useRemoteControl.ts` | 신규 | 원격 WS 연결, 상태 수신, 명령 전송 |
| `frontend/src/hooks/usePushNotification.ts` | 신규 | FCM 토큰 등록, 권한 요청 |
| `frontend/src/components/KillSwitchFAB.tsx` | 신규 | 킬스위치 버튼 + 확인 다이얼로그 |
| `frontend/src/components/ArmDialog.tsx` | 신규 | 재개 조건 표시 + 비밀번호 입력 |
| `frontend/index.html` | 수정 | manifest 링크, 메타 태그 |
| `frontend/src/App.tsx` | 수정 | SW 등록, FCM 초기화, RemoteMode 컨텍스트 |
| `frontend/src/components/main/OpsPanel.tsx` | 수정 | 원격 모드 배지, 반응형 래핑 |
| `frontend/src/services/cloudClient.ts` | 수정 | verify-password, push/register API |
| `frontend/src/types/index.ts` | 수정 | RemoteState 타입 |

## 구현 순서

### Step 1: 원격 상태 수신 (프론트엔드 WS)

원격 디바이스가 클라우드 `/ws/remote`에 연결하여 상태를 수신.

**파일**:
1. `frontend/src/hooks/useRemoteControl.ts`
   - 클라우드 WS 연결 (`/ws/remote`)
   - auth 메시지 전송 (JWT + device_id)
   - `state` 메시지 수신 → 상태 업데이트
   - E2E 복호화 (IndexedDB에서 키 로드 → `e2eCrypto.decrypt()`)
   - 상태를 React state로 관리
   - `last_received_ts` 관리 + 재연결 시 sync_request

2. `frontend/src/types/index.ts` 수정
   - `RemoteState` 타입 정의

**verify**: 클라우드+로컬 실행 → 원격 프론트 WS 연결 → 로컬에서 상태 변경 → 원격에서 수신 확인

---

### Step 2: 원격 모드 감지 + UI 분기

**파일**:
1. `frontend/src/hooks/useRemoteMode.ts`
   - `localhost:4020/health` 시도
   - 성공 → `isRemote: false` (기존 동작)
   - 실패 + 클라우드 JWT 있음 → `isRemote: true`
   - 실패 + JWT 없음 → 로그인 화면

2. `frontend/src/App.tsx` 수정
   - `RemoteModeContext` 제공
   - 원격 모드 시 `useRemoteControl()` 활성화

3. `frontend/src/components/main/OpsPanel.tsx` 수정
   - `isRemote` 시 "원격 모드" 배지 표시
   - 설정/엔진 start 버튼 비활성화
   - 원격 상태 데이터 소스 전환
   - `flex-wrap` 추가 (모바일 래핑)

**verify**: 로컬 서버 미실행 + 클라우드 로그인 → "원격 모드" 배지 → 설정 비활성 확인

---

### Step 3: 킬스위치

**파일**:
1. `frontend/src/components/KillSwitchFAB.tsx`
   - FAB 버튼 (모바일 하단 고정, PC는 OpsPanel 내)
   - 클릭 → 확인 다이얼로그 ("엔진을 정지합니다")
   - mode 선택: `stop_new` / `stop_all`
   - WS로 `{ type: "command", payload: { action: "kill", mode } }` 전송
   - ACK 대기 → "정지 완료" 또는 "명령 저장됨 (오프라인)"

2. `local_server/cloud/ws_relay_client.py` 수정
   - `_handle_command(msg)` 추가
   - `action: "kill"` → `safeguard.activate_kill_switch()` + disarm
   - `command_ack` 전송

**verify**: 원격에서 킬스위치 → 로컬 엔진 정지 확인 → ACK 수신 확인

---

### Step 4: 원격 arm (비밀번호 재입력)

**파일**:
1. `cloud_server/api/auth.py` 수정
   - `POST /api/v1/auth/verify-password`
   - `{ password }` → bcrypt 검증 → `{ success: true }` or 401
   - brute-force: Redis 카운터 (5회 실패 → 10분 잠금)

2. `frontend/src/components/ArmDialog.tsx`
   - 재개 조건 체크 (로컬 온라인, 브로커 연결, 비정상 상태 없음)
   - 조건 미충족 → 사유 목록 표시, 버튼 비활성
   - 조건 충족 → 비밀번호 입력 필드
   - 제출 → `POST /verify-password` → 성공 시 WS command `{ action: "arm" }`
   - OAuth2 전용 사용자 → OAuth2 재인증 버튼

3. `local_server/cloud/ws_relay_client.py` 수정
   - `action: "arm"` → `engine.arm()` + safeguard 리셋
   - `command_ack` 전송

**verify**: 원격에서 "재개" → 비밀번호 입력 → 로컬 arm 확인 → 잘못된 비밀번호 5회 → 잠금 확인

---

### Step 5: FCM 푸시 — 백엔드

**파일**:
1. `cloud_server/models/push_token.py` — PushToken 모델

2. `cloud_server/services/firebase_service.py`
   - `FirebaseService` 클래스
   - `init(credentials_path)` — Firebase Admin SDK 초기화
   - `send(user_id, title, body, data, priority, db)` — 사용자의 활성 토큰 조회 → FCM 전송
   - `register_token(user_id, device_id, token, platform, db)`
   - `deactivate_token(token, db)` — 토큰 만료/오류 시

3. `cloud_server/api/push.py`
   - `POST /api/v1/push/register` — 토큰 등록
   - `DELETE /api/v1/push/unregister` — 토큰 해제

4. `cloud_server/services/relay_manager.py` 수정
   - `handle_local_message()` — `type: "alert"` 수신 시:
     - 디바이스 WS로 릴레이 + `FirebaseService.send()` 호출

5. `cloud_server/main.py` 수정
   - Firebase Admin SDK 초기화 (환경변수 `FIREBASE_CREDENTIALS_PATH`)
   - push 라우터 등록

**verify**: curl로 토큰 등록 → 로컬에서 alert 발생 → FCM 푸시 수신 확인

---

### Step 6: FCM 푸시 — 프론트엔드

**파일**:
1. `frontend/src/hooks/usePushNotification.ts`
   - Firebase JS SDK 초기화
   - `Notification.requestPermission()`
   - `getToken()` → `POST /api/v1/push/register`
   - `onMessage()` → 포그라운드 토스트 표시
   - 토큰 갱신 시 자동 재등록

2. `frontend/public/firebase-messaging-sw.js`
   - `messaging.onBackgroundMessage()` → 알림 표시
   - 클릭 시 `clients.openWindow(data.route || '/')`

3. `frontend/src/App.tsx` 수정
   - 로그인 후 `usePushNotification()` 호출

4. `frontend/.env.example` 수정
   - `VITE_FIREBASE_CONFIG`

**verify**: 앱 열린 상태 → 알림 토스트. 앱 닫은 상태 → OS 알림. 알림 클릭 → 앱 열림.

---

### Step 7: PWA

**파일**:
1. `frontend/public/manifest.json`
   ```json
   {
     "name": "StockVision",
     "short_name": "SV",
     "start_url": "/",
     "display": "standalone",
     "background_color": "#111827",
     "theme_color": "#111827",
     "icons": [
       { "src": "/icon-192x192.png", "sizes": "192x192", "type": "image/png" },
       { "src": "/icon-512x512.png", "sizes": "512x512", "type": "image/png" }
     ]
   }
   ```

2. `frontend/public/sw.js` — 기본 Service Worker (네트워크 퍼스트 캐시)

3. `frontend/index.html` 수정
   - `<link rel="manifest" href="/manifest.json">`
   - `<meta name="theme-color" content="#111827">`
   - apple-mobile-web-app 메타 태그

4. `frontend/public/icon-192x192.png`, `icon-512x512.png` — 아이콘 생성

**verify**: Android Chrome → "앱 설치" 배너. iOS Safari → "홈 화면에 추가" → standalone 실행.

---

### Step 8: 모바일 반응형

**파일**:
1. `frontend/src/components/main/OpsPanel.tsx` 수정
   - `flex-wrap` + breakpoint 처리

2. `frontend/src/components/main/ListView.tsx` 수정 (필요 시)
   - 모바일에서 카드 레이아웃 전환

3. `frontend/src/components/KillSwitchFAB.tsx` 수정
   - 모바일: 하단 고정 `fixed bottom-4 right-4`
   - PC: OpsPanel 내 inline

**verify**: Chrome DevTools 모바일 뷰포트 → 텍스트 잘림 없음 → FAB 위치 확인

---

### Step 9: 통합 테스트

**시나리오**:
1. 로컬+클라우드 시작 → 로컬 WS 연결 확인
2. 원격 디바이스 WS 연결 → 실시간 상태 수신 확인
3. 계좌 정보 E2E 암호화 전달 확인
4. 킬스위치 → 로컬 정지 → ACK → 원격 UI 갱신
5. arm → 비밀번호 검증 → 로컬 재개 → ACK
6. 로컬 오프라인 → 킬스위치 → pending 저장 → 로컬 복귀 → 자동 정지
7. FCM 토큰 등록 → alert 발생 → 푸시 수신
8. PWA 설치 → standalone 실행 → 원격 모드 동작

**verify**: 전체 시나리오 수동 테스트 + 스크린샷 보고서

## 의존성 그래프

```
C6-a (릴레이 인프라) + C6-b (인증 확장) 완료 전제

Step 1 (원격 상태 수신)
  └→ Step 2 (원격 모드 감지 + UI)
       └→ Step 3 (킬스위치)
       └→ Step 4 (원격 arm)

Step 5 (FCM 백엔드) — 독립
  └→ Step 6 (FCM 프론트) — Step 5 의존

Step 7 (PWA) — 독립

Step 8 (모바일 반응형) — Step 2 이후

Step 9 (통합 테스트) — 전체 완료 후
```

## 검증 방법

- 빌드: `npm run build` 통과
- Playwright: 원격 모드 UI, 킬스위치 다이얼로그, arm 다이얼로그 스크린샷
- 실제 디바이스: Android Chrome PWA 설치 + FCM 수신
- E2E: 로컬 encrypt → 원격 decrypt → 화면 표시
- 보안: 비밀번호 brute-force 잠금 확인, rate limit 확인
