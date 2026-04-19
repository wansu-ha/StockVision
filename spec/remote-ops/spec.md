# 원격 제어 (Remote Operations)

> 작성일: 2026-03-12 | 상태: 구현 완료 | Phase C (C6-c)
>
> 대체: `spec/remote-control/spec.md` 기능 부분을 대체 (인프라는 C6-a, 인증은 C6-b)

## 1. 배경

릴레이 인프라(C6-a)와 인증 체계(C6-b)가 구축되면, 그 위에서 실제 원격 기능을 구현한다. 핵심은 세 가지:

1. 밖에서 폰으로 시스템 상태를 본다
2. 위험하면 즉시 정지한다
3. 안전하면 다시 켠다 (더 어렵게)

권한 모델 원칙: **조회는 넓게, 실행은 좁게, 정지는 쉽게, 재개는 어렵게.**

## 2. 목표

원격 디바이스에서 실시간 상태를 확인하고, 긴급 정지/재개를 수행하며, 중요 이벤트를 푸시 알림으로 받는다.

## 3. 범위

### 3.1 포함

**A. 원격 상태 조회**
- 엔진 상태 (running/stopped/halted/armed)
- 브로커 연결 상태
- Kill Switch / 손실 락 상태
- 계좌 요약 (잔고, 평가, 당일 손익) — E2E 암호화 전송
- 오늘 통계 (신호 수, 체결 수, 오류 수)
- 최근 실행 로그 (10건)
- 로컬 서버 온라인/오프라인 표시 + "마지막 동기화: X분 전"

**B. 긴급 정지 (킬스위치)**
- WS로 즉시 전달 (로컬 연결 시)
- 로컬 오프라인 시 클라우드 pending 큐에 저장 (C6-a 메시지 큐 활용)
- 정지 모드: `stop_new` (신규 차단) / `stop_all` (신규 차단 + 미체결 취소)
- 1탭 + 1회 확인 ("엔진을 정지합니다")

**C. 원격 엔진 재개/무장 (arm)**
- 비밀번호 재입력으로 본인 확인 (2단계 확인 코드 대신)
- 재개 가능 조건: 로컬 온라인 + 브로커 연결 + 비정상 상태 없음
- 조건 미충족 시 구체적 사유 표시
- 로컬 오프라인 시 재개 금지

**D. FCM 웹 푸시**
- Firebase Cloud Messaging (HTTP v1 API)
- 푸시 토큰 등록 (JWT와 별도)
- 앱 백그라운드에서도 OS 알림 수신
- 이벤트별 알림 (체결, 오류, 킬스위치, 브로커 연결 해제)

**E. PWA**
- manifest.json + Service Worker
- 홈화면 추가 → standalone 모드 실행
- Android Chrome + iOS Safari (16.4+) 지원

**F. 원격 모드 UI**
- 로컬/원격 모드 자동 감지
- 원격 모드 배지 표시
- 설정/실행 버튼 비활성화 (읽기 전용)
- 킬스위치 버튼 항상 활성
- 모바일 반응형 (OpsPanel 래핑, 킬스위치 FAB)

### 3.2 제외

- 원격 수동 실주문 (초기 금지 정책)
- 원격 설정 변경 (민감 설정)
- 메신저 봇 (텔레그램) → Phase D
- 외부 주문 감지 (C8) → 기존 `spec/remote-control/spec.md` §12 유지
- 종목별 가격 알림 → Phase E

## 4. 의존성

| 의존 대상 | 상태 | 비고 |
|-----------|------|------|
| 릴레이 인프라 (C6-a) | 미구현 | WS, E2E, 메시지 프로토콜 |
| 인증 확장 (C6-b) | 미구현 | 디바이스 등록, OAuth2 |
| 엔진 start/stop (`local_server/routers/trading.py`) | 구현됨 | |
| Safeguard (`local_server/engine/safeguard.py`) | 구현됨 | kill_switch, loss_lock |
| 상태 API (`local_server/routers/status.py`) | 구현됨 | |
| Firebase 프로젝트 | 미설정 | Service Account Key 필요 |

## 5. 설계

### 5.1 원격 상태 조회

**실시간 릴레이 방식** (30초 주기 push 대신):

```
로컬 서버
  → 상태 변경 시 즉시 WS로 state 메시지 전송
  → 30초마다 heartbeat에도 상태 포함 (변경 없어도)
  → 금융 데이터는 E2E 암호화 (디바이스별 키)

클라우드
  → 평문 필드(엔진 상태 등)만 DB에 저장 (오프라인 뷰용)
  → 암호문은 저장하지 않음, 릴레이만
  → 원격 디바이스 WS로 즉시 전달

원격 디바이스
  → WS로 실시간 수신
  → E2E 복호화 후 표시
  → 디바이스 로컬 저장 (IndexedDB)
  → 오프라인 시 마지막 저장된 데이터 표시
```

**상태 스냅샷 구조**:

```json
{
  "type": "state",
  "payload": {
    "engine_state": "running",
    "armed": true,
    "broker_connected": true,
    "broker_mode": "live",
    "kill_switch": "OFF",
    "loss_lock": false,
    "today_stats": { "signals": 3, "fills": 2, "errors": 0 },
    "recent_logs": [...],
    "encrypted_for": {
      "device-A": { "iv": "...", "ciphertext": "...", "tag": "..." }
    }
  }
}
```

`encrypted_for` 내부 (복호화 후):
```json
{
  "total_balance": 100000000,
  "total_eval": 102500000,
  "daily_pnl": 2500000,
  "daily_pnl_pct": 2.5,
  "positions": [...],
  "open_orders": [...]
}
```

### 5.2 킬스위치

**정지 흐름**:

```
원격 디바이스
  → 킬스위치 버튼 탭
  → 확인 다이얼로그 ("엔진을 정지합니다. 계속하시겠습니까?")
  → 확인 → WS로 command 메시지 전송

  { type: "command", payload: { action: "kill", mode: "stop_new" | "stop_all" } }

클라우드
  → 로컬 WS 연결됨 → 즉시 전달
  → 로컬 WS 끊김 → pending_commands에 저장

로컬 서버
  → 수신 → safeguard.activate_kill_switch(level)
  → ArmSession 해제
  → command_ack 전송 { success: true }

원격 디바이스
  → ACK 수신 → "정지 완료" 피드백 표시
```

**오프라인 킬스위치**:

```
원격 디바이스 → 클라우드 (로컬 오프라인)
  → "정지 명령 전송됨 — 로컬 서버 복귀 시 즉시 적용됩니다" 표시
  → 클라우드 DB pending_commands에 저장

로컬 서버 재연결 시
  → 클라우드가 pending 큐 flush
  → 로컬 즉시 실행 → ACK
```

### 5.3 원격 재개/무장 (arm)

**재개 흐름**:

```
원격 디바이스
  → "재개" 버튼 탭
  → 재개 조건 체크 (프론트에서 1차, 서버에서 2차)
    - 로컬 온라인? 브로커 연결? 비정상 상태?
  → 조건 미충족 → 구체적 사유 표시, 버튼 비활성
  → 조건 충족 → 비밀번호 재입력 다이얼로그

  → 비밀번호 입력 → 클라우드에 검증 요청
    POST /api/v1/auth/verify-password { password }
    → 200 OK → 클라우드가 WS로 arm 명령 전달
    → 401 → "비밀번호가 틀립니다"

  → OAuth2 전용 사용자 (비밀번호 없음)
    → C6-b의 OAuth2 재인증 플로우 사용
    → GET /api/v1/auth/oauth/{provider}/login으로 재로그인
    → 새 access_token 수신 → 클라우드가 본인 확인 완료로 판단 → arm 명령 전달

로컬 서버
  → arm 명령 수신 → engine.arm()
  → command_ack { success: true }

원격 디바이스
  → "재개 완료" 피드백
```

**재개 불가 사유 표시 예시**:
- "브로커 미연결 — 로컬 PC에서 연결하세요"
- "로컬 서버 오프라인 — 서버를 시작하세요"
- "미해결 경고 있음 — 경고를 확인하세요"

**비밀번호 검증 API**:

```
POST /api/v1/auth/verify-password
Body: { password: string }
Response: { success: true } or 401
```

기존 로그인과 별도. 비밀번호만 검증, 새 토큰 발급하지 않음. brute-force 방지: 5회 실패 시 10분 잠금.

### 5.4 FCM 웹 푸시

**아키텍처**:

```
로컬 서버 (이벤트 발생)
  → WS로 클라우드에 alert 메시지 전송
클라우드 서버
  → FCM HTTP v1 API로 푸시 전송
Firebase Cloud Messaging
  → Service Worker가 수신 → OS 알림
```

**푸시 토큰 관리**:

```
POST /api/v1/push/register
Body: { push_token: string, platform: 'web' | 'android' | 'ios', device_id: string }
```

- 로그인 후 브라우저가 FCM 토큰 발급
- JWT 만료와 무관 — 푸시 토큰은 별도 수명
- 토큰 갱신 시 자동 업데이트

**알림 유형**:

| 이벤트 | 제목 | 본문 예시 | 우선순위 |
|--------|------|-----------|---------|
| 체결 | 체결 완료 | "삼성전자 10주 매수 — 72,400원" | normal |
| 주문 실패 | 주문 실패 | "SK하이닉스 매수 실패 — 예산 초과" | high |
| Kill Switch | 엔진 정지 | "Kill Switch 발동 — 신규 주문 차단" | high |
| Loss Lock | 손실 한도 | "일일 손실 한도 도달 — 자동 정지" | high |
| 엔진 중단 | 엔진 응답 없음 | "3분째 응답 없음 — 확인 필요" | high |
| 브로커 끊김 | 브로커 연결 해제 | "키움증권 연결 해제" | high |

**푸시 토큰 모델**:

```python
class PushToken(Base):
    __tablename__ = "push_tokens"
    id         = Column(Integer, primary_key=True)
    user_id    = Column(UUID, ForeignKey("users.id"), nullable=False)
    device_id  = Column(String(50))
    token      = Column(Text, nullable=False)
    platform   = Column(String(10))   # 'web' | 'android' | 'ios'
    is_active  = Column(Boolean, default=True)
    updated_at = Column(DateTime, default=now, onupdate=now)
```

### 5.5 PWA 설정

**추가 파일**:
- `frontend/public/manifest.json` — 앱 이름, 아이콘, display: standalone
- `frontend/public/sw.js` — Service Worker (캐시 전략 + 푸시 수신)
- `frontend/public/firebase-messaging-sw.js` — FCM 백그라운드 메시지

**수정 파일**:
- `frontend/index.html` — manifest 링크, 메타 태그
- `frontend/src/App.tsx` — SW 등록, 푸시 권한 요청

### 5.6 원격 모드 감지

```typescript
function useRemoteMode() {
  // 1. 로컬 서버 직접 연결 시도 (localhost:4020/health)
  // 2. 성공 → 로컬 모드 (기존 동작)
  // 3. 실패 + 클라우드 인증 있음 → 원격 모드
  // 4. 실패 + 인증 없음 → 로그인 화면
  return { isRemote, localOnline }
}
```

**원격 모드 UI 차이**:

| 요소 | 로컬 모드 | 원격 모드 |
|------|----------|----------|
| 헤더 배지 | 없음 | "원격 모드" |
| 설정 | 전체 | 읽기 전용 |
| 엔진 start/stop | 활성 | 비활성 (킬스위치만 가능) |
| 킬스위치 | 활성 | 활성 |
| arm 재개 | 활성 | 조건부 활성 (비밀번호 필요) |
| 규칙 편집 | 활성 | 비활성 |
| 계좌 정보 | 직접 API | E2E 릴레이 |

### 5.7 모바일 반응형

- OpsPanel: 2줄 래핑 (`flex-wrap`)
- ListView: 카드형 전환 (세로 스택)
- 킬스위치: 하단 고정 FAB (모바일에서만)
- DetailView: 탭 기반 세로 배치

### 5.8 Firebase 키 관리

어드민이 Firebase Service Account Key를 등록:

```
POST /api/v1/admin/firebase-key
Body: { service_account_json: object }
```

키는 서버 파일시스템 또는 환경변수에 저장. DB 저장 금지.

## 6. 수용 기준

### 원격 상태 조회
- [ ] 원격에서 엔진/브로커/킬스위치 상태를 실시간으로 확인할 수 있다
- [ ] 계좌 요약이 E2E 암호화되어 전달·표시된다
- [ ] 오늘의 신호/체결/오류 수가 표시된다
- [ ] 최근 실행 로그 10건이 표시된다
- [ ] 로컬 오프라인 시 "마지막 동기화: X분 전" 표시

### 킬스위치
- [ ] 원격에서 1탭 + 1회 확인으로 엔진을 정지할 수 있다
- [ ] WS 연결 시 즉시 전달, 오프라인 시 pending 저장
- [ ] 정지 후 "정지 완료" 피드백이 표시된다
- [ ] 로컬 복귀 시 pending 킬 명령이 즉시 실행된다

### 원격 재개/무장
- [ ] 비밀번호 재입력으로 원격 arm이 가능하다
- [ ] OAuth2 전용 사용자는 OAuth2 재인증으로 arm이 가능하다
- [ ] 조건 미충족 시 구체적 사유가 표시된다
- [ ] 로컬 오프라인 시 재개가 금지된다
- [ ] 비밀번호 5회 틀리면 10분 잠금

### FCM 웹 푸시
- [ ] 로그인 후 푸시 권한 요청이 표시된다
- [ ] 푸시 토큰이 클라우드에 등록된다
- [ ] 체결/오류/킬스위치 이벤트 시 OS 알림이 수신된다
- [ ] 앱 백그라운드에서도 알림이 수신된다 (Service Worker)
- [ ] 알림 클릭 시 앱이 열린다

### PWA
- [ ] Android Chrome에서 "앱 설치" 배너가 표시된다
- [ ] iOS Safari에서 홈화면 추가 후 standalone 모드로 실행된다
- [ ] manifest.json + Service Worker 정상 등록

### 원격 모드 UI
- [ ] 로컬/원격 모드가 자동 감지된다
- [ ] 원격 모드에서 "원격 모드" 배지가 표시된다
- [ ] 원격 모드에서 설정/규칙 편집이 비활성화된다
- [ ] 모바일에서 킬스위치 FAB이 표시된다
- [ ] 모바일에서 텍스트 잘림 없이 표시된다

## 7. 참고

- 릴레이 인프라: `spec/relay-infra/spec.md` (C6-a)
- 인증 확장: `spec/auth-extension/spec.md` (C6-b)
- 권한 모델: `docs/product/remote-permission-model.md`
- 기존 원격 제어 spec (대체됨): `spec/remote-control/spec.md`
- 기존 상태 API: `local_server/routers/status.py`
- FCM 결정: `docs/roadmap.md` §채널 결정
