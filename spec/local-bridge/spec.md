# 로컬 서버 명세서 (local-bridge)

> 작성일: 2026-03-04 | 상태: 업데이트 (아키텍처 전환) | 담당: Backend/DevOps

> **변경 이력**: 초안은 "클라우드 서버 → 로컬 브릿지" 구조였으나,
> 2026-03-04 아키텍처 결정으로 **로컬 FastAPI 서버가 메인 실행 코어**로 전환됨.

---

## 1. 개요

**로컬 서버(Local Server)**는 사용자 PC에 설치되는 **FastAPI 기반 백엔드**로,
StockVision의 실질적인 실행 코어다. "로컬 브릿지"는 이 서버를 지칭하는 이름이다.

| 구분 | 역할 |
|------|------|
| 클라우드 (stockvision.app) | React 앱 정적 호스팅 + 컨텍스트/템플릿/버전/하트비트 API |
| **로컬 서버 (이 문서)** | 키움 실행, 전략 평가, 설정 저장, WS 서버 |

**핵심 역할:**
1. **WebSocket 서버**: React 앱(클라우드)과 실시간 양방향 통신 (React → 로컬)
2. **키움 COM API 연동**: Windows에서 주문/체결/잔고 조회
3. **전략 규칙 평가**: 사용자 정의 조건 → 충족 시 직접 키움 주문 실행
4. **설정 자동 저장**: config.json에 debounce 저장 (사용자 액션 없음)
5. **클라우드 통신**: 컨텍스트 데이터 fetch + 익명 하트비트 전송 (outbound only)

**키움 약관 준수:** G5 제5조② — ID/PW/인증서는 영웅문 HTS가 관리. 우리 앱은 자격증명 미보관.

---

## 2. 성공 기준

| 항목 | 목표 |
|------|------|
| 설치 시간 | < 5분 (.exe 실행 → 서버 시작) |
| 브라우저 연결 시간 | < 3초 (WS 자동 연결) |
| 신호 → 주문 지연 | < 100ms |
| 서버 가동률 | > 99% |
| 메모리 사용 | < 200MB |

---

## 3. 아키텍처

### 3.1 전체 흐름

```
Cloud (stockvision.app)                  Local PC (Windows)
┌──────────────────────────────┐         ┌──────────────────────────────────┐
│  React 앱 (정적)             │◀──WS────│  FastAPI 서버 (localhost:8765)   │
│  ├── 전략 빌더 UI            │         │  ├── /ws  WebSocket 엔드포인트   │
│  ├── 대시보드                │──HTTP──▶│  ├── /api/* REST 엔드포인트      │
│  └── 설정 페이지             │         │  │                               │
│                              │         │  ├── kiwoom/ (COM API 레이어)    │
│  컨텍스트 API                │◀──HTTP──│  ├── engine/ (전략 평가 엔진)    │
│  템플릿 API                  │         │  ├── cloud/ (컨텍스트 fetch)     │
│  버전 API                    │         │  ├── config.json (자동 저장)     │
│  하트비트 수신               │◀──ping──│  └── logs.db (체결·오류 기록)    │
└──────────────────────────────┘         └──────────────────────────────────┘
                                                    ↓
                                         키움증권 COM API (Windows 전용)
                                         ├── 주문 실행
                                         ├── 체결 조회
                                         └── 잔고 조회
```

**통신 방향 명확화:**
- `React → local WS`: 설정 변경, 전략 ON/OFF, UI 명령
- `local → React WS`: 체결 결과, 잔고 업데이트, 키움 연결 상태, 알림
- `local → cloud HTTP`: 컨텍스트 fetch (장 마감 후), 하트비트 (5분마다)
- **cloud → local 방향 없음** (클라우드는 요청 수신만)

### 3.2 모듈 구조

```
local_server/
├── main.py                       # FastAPI 앱 진입점 (localhost:8765)
├── routers/
│   ├── ws.py                     # WebSocket 엔드포인트 (/ws)
│   ├── config.py                 # 설정 조회/수정 REST API
│   ├── kiwoom.py                 # 키움 상태/계좌 REST API
│   └── trading.py                # 전략 실행/중지 REST API
├── kiwoom/
│   ├── com_client.py             # COM 객체 래퍼 (pywin32)
│   ├── session.py                # 세션 관리 (connect/disconnect/switch)
│   ├── order.py                  # 주문 실행 (send_order)
│   └── account.py                # 잔고/포지션 조회
├── engine/
│   ├── scheduler.py              # 규칙 평가 스케줄러 (1분 주기)
│   ├── evaluator.py              # 조건 평가 로직
│   └── signal.py                 # 신호 생성 → kiwoom.order 호출
├── cloud/
│   ├── context.py                # 클라우드 컨텍스트 fetch + 로컬 캐시
│   └── heartbeat.py              # 익명 하트비트 전송 (5분 주기)
├── storage/
│   ├── config_manager.py         # config.json 자동저장 (500ms debounce)
│   └── log_db.py                 # logs.db SQLite 관리
└── requirements.txt
```

---

## 4. 배포 방식

**결정: 단일 PyInstaller .exe**

| 항목 | 내용 |
|------|------|
| 배포 형태 | 단일 `.exe` (PyInstaller 번들) |
| 포함 요소 | FastAPI + uvicorn + 의존성 + 기본 config 템플릿 |
| 제외 요소 | React 앱 (cloud 호스팅, exe에 포함 안 함) |
| 실행 후 | 시스템 트레이 아이콘 + 백그라운드 서버 시작 |
| 업데이트 | cloud `/api/version` 폴링 → 신버전 시 다운로드 안내 |
| 자동 시작 | Windows 시작프로그램 등록 (선택) |

---

## 5. 설치 및 초기 설정

### 5.1 설치 플로우

```
[사용자] stockvision_setup.exe 다운로드 + 실행
    ↓
[exe] localhost:8765 FastAPI 서버 시작 (백그라운드)
    ↓
[exe] 브라우저 자동 열기: https://stockvision.app
    ↓
[브라우저] React 앱 로딩
    ↓
[React] ws://localhost:8765/ws 자동 연결 시도
    ↓ (브라우저 localhost 예외: HTTPS → ws://localhost 허용)
[연결 성공] 대시보드 활성화 → 온보딩 화면
    ↓
[사용자] 설정 페이지 → "키움 연결" 클릭 → 영웅문 HTS 기동 안내
    ↓
[키움 HTS] 사용자가 직접 로그인 (ID/PW + 공동인증서)
    ↓
[로컬 서버] 이미 로그인된 COM 세션에 연결
    ↓
✓ 연결 완료, 모의투자 또는 실거래 모드 선택
```

**우리 앱이 요구하는 것:**
- 키움증권 계좌 (개설 필요)
- 영웅문 HTS 설치 + 자동로그인 설정 (1회)

**우리 앱이 저장하지 않는 것:**
- 키움 ID/PW (영웅문 HTS 위임)
- 공동인증서 (사용자 PC에 원래 있음)

### 5.2 설정 자동 저장

```
[사용자] 전략 수정 또는 설정 변경
    ↓
[React] HTTP PATCH /api/config { key: value }
    ↓
[로컬 서버] 500ms debounce
    ↓
[로컬 서버] cloud_config.json 덮어쓰기
    ↓
(완료, 사용자에게 별도 표시 없음)
```

---

## 6. 데이터 저장 구조

```
%APPDATA%\StockVision\
├── cloud_config.json     # 동기화 가능: 전략, UI 설정, 키움 모드
├── local_secrets.json    # 절대 업로드 금지: 계좌번호만
└── logs.db               # SQLite: 체결 로그, 오류, 전략 이력
```

**cloud_config.json:**
```json
{
  "kiwoom": { "mode": "demo" },
  "strategies": [],
  "ui_preferences": {}
}
```

**local_secrets.json:**
```json
{
  "account_no": "1234567890"
}
```

> ID/PW/인증서는 영웅문 HTS가 관리 → 우리 파일에 없음

**PC2 이전 시:**
1. `cloud_config.json` → 클라우드 동기화로 자동 복원
2. `local_secrets.json` → 계좌번호 수동 입력 (1회)
3. 영웅문 HTS + 공동인증서 → PC2에서 직접 설치

---

## 7. React ↔ 로컬 서버 통신 프로토콜

### 7.1 WebSocket 메시지

**React → 로컬 서버 (명령)**

```json
{ "type": "strategy_toggle", "data": { "rule_id": 1, "is_active": true } }
```
```json
{ "type": "config_update", "data": { "kiwoom.mode": "demo" } }
```

**로컬 서버 → React (이벤트)**

```json
{
  "type": "execution_result",
  "data": {
    "rule_id": 1,
    "symbol": "005930",
    "side": "BUY",
    "filled_qty": 10,
    "filled_price": 70000,
    "timestamp": "2026-03-04T10:30:15+09:00"
  }
}
```
```json
{
  "type": "kiwoom_status",
  "data": { "connected": true, "mode": "demo", "balance": 10000000 }
}
```

### 7.2 REST API (로컬 서버)

```
GET  /api/health            → 서버 상태
GET  /api/kiwoom/status     → 키움 연결 상태
GET  /api/account           → 잔고/포지션
PATCH /api/config           → 설정 업데이트 (자동 저장)
POST /api/strategy/start    → 전략 실행
POST /api/strategy/stop     → 전략 중지
GET  /api/logs?limit=100    → 체결/오류 로그
```

---

## 8. 클라우드 통신 (아웃바운드만)

로컬 서버가 클라우드로 **outbound HTTP 요청만** 수행. 클라우드가 로컬로 연결 시도 없음.

| 목적 | 엔드포인트 | 주기 |
|------|-----------|------|
| 시장 컨텍스트 fetch | `GET /api/context` | 장 마감 후 1회 (16:30) |
| 전략 템플릿 fetch | `GET /api/templates` | 앱 시작 시 |
| 버전 체크 | `GET /api/version` | 앱 시작 시 |
| 익명 하트비트 | `POST /api/heartbeat` | 5분마다 |

**하트비트 페이로드 (개인정보 없음):**
```json
{
  "uuid": "anon-local-uuid-abc123",
  "version": "1.0.0",
  "os": "windows",
  "kiwoom_connected": true,
  "timestamp": "2026-03-04T10:35:00+09:00"
}
```

> UUID는 설치 시 1회 생성, 이후 고정. 개인정보보호법상 개인정보 해당 없음.

---

## 9. 키움 API 호출 제한 관리

| 기능 | 제한 | 대응 |
|------|------|------|
| 조회 API | 초당 5건 | 조회 큐 + 200ms 간격 |
| 주문 API | 초당 5건 | 주문 큐 + FIFO |
| 실시간 등록 | 최대 200개 | 보유 종목 기준 자동 관리 |

---

## 10. 에러 처리 및 복구

| 상황 | 처리 방식 |
|------|---------|
| 클라우드 연결 끊김 | 로컬 서버 정상 작동 유지, 컨텍스트는 캐시 사용 |
| 키움 세션 만료 | 자동 재연결 시도 3회 → 실패 시 WS로 React에 알림 |
| 전략 평가 오류 | 해당 규칙만 비활성화 + logs.db 기록 |
| exe 재시작 | config.json 자동 로딩, 이전 전략 상태 복원 |
| WS 연결 끊김 | React가 자동 재연결 (1s → 5s → 30s 백오프) |

---

## 11. 계정 전환 (재시작 없이)

```
[사용자] UI에서 "계정 전환" 클릭
    ↓
[로컬 서버] 실행 중인 전략 일시 중지
    ↓
[로컬 서버] KiwoomSession.logout()
    ↓
[영웅문 HTS] 사용자가 다른 계정으로 재로그인
    ↓
[로컬 서버] KiwoomSession.connect() → 새 세션 획득
    ↓
[로컬 서버] 새 계좌번호로 local_secrets.json 업데이트
    ↓
✓ 전략 재시작 (서버 재시작 불필요)
```

---

## 12. 기술 요구사항

| 항목 | 선택 | 비고 |
|------|------|------|
| 언어 | Python 3.13 | Windows COM → Python 필수 |
| 프레임워크 | FastAPI + uvicorn | localhost:8765 |
| 키움 래퍼 | pywin32 (COM) | 공식 키움 가이드 기반 |
| 패키징 | PyInstaller | 단일 .exe |
| 로컬 DB | SQLite (logs.db) | 체결·오류 기록 |
| 설정 저장 | JSON 파일 | cloud_config + local_secrets |

---

## 13. 미결 사항

- [ ] 상태 동기화 전략 (클라우드 config vs 로컬 config 불일치 시)
- [ ] exe 자동 업데이트 메커니즘
- [ ] Windows 시작프로그램 자동 등록 여부
- [ ] 계정 전환 시 체결 중인 주문 처리

---

**마지막 갱신**: 2026-03-04 (아키텍처 전환: 클라우드 신호 수신 → 로컬 서버 통합)
**상태**: 업데이트 완료
