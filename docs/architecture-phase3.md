# StockVision Phase 3 아키텍처

> 작성일: 2026-03-04 | 상태: 확정 | 담당: 전체

---

## 1. 개요

Phase 3는 **로컬 브릿지 + 시스템매매** 단계다.
사용자가 로컬 PC에 설치파일(.exe) 하나를 실행하면, 클라우드 웹 UI에서 설정한 전략이 키움증권 API를 통해 자동 체결되는 시스템.

**핵심 설계 원칙:**
- 실행 코어는 로컬 PC에 — 클라우드는 UI + 공개 API만
- 전략/설정은 서버사이드 AES-256-GCM 암호화 (개인정보보호법 제29조 초과 조치)
- 키움 자격증명은 영웅문 HTS에 위임 — 우리 앱에 저장 안 함
- 법적 포지션: 시스템매매 (투자일임·자문 아님) — 사용자가 규칙 정의, 시스템이 실행

---

## 2. 전체 시스템 다이어그램

```
사용자 브라우저                 클라우드 (stockvision.app)
┌──────────────┐               ┌──────────────────────────────────────┐
│ React 앱     │ ◀── 정적 ──── │ CDN / 정적 호스팅                    │
│ (SPA)        │               │                                      │
│              │               │ Auth API:                            │
│              │ ──로그인──▶   │   POST /api/auth/login               │
│              │ ◀─JWT+RT──    │   POST /api/auth/refresh             │
│              │               │                                      │
│              │               │ 공개 API:                            │
│              │ ◀── HTTP ──   │   GET  /api/context   (시장 변수)    │
│              │ ◀── HTTP ──   │   GET  /api/templates (전략 템플릿)  │
│              │ ◀── HTTP ──   │   GET  /api/version   (버전 체크)   │
│              │ ──ping──▶     │   POST /api/heartbeat (익명 통계)    │
│              │               │                                      │
│              │               │ 설정 동기화 API:                      │
│              │ ──upload──▶   │   PUT  /api/v1/config   (서버사이드 암호화)|
│              │ ◀── download──│   GET  /api/v1/config                │
└──────┬───────┘               └──────────────────────────────────────┘
       │
       │  ws://localhost:8765/ws  (브라우저 localhost 예외 허용)
       │  http://localhost:8765/api/*
       │
┌──────▼──────────────────────────────────────────────────────────────┐
│  로컬 서버 (FastAPI, localhost:8765)         Windows 전용           │
│                                                                     │
│  routers/                                                           │
│  ├── ws.py          WebSocket 엔드포인트 (/ws)                      │
│  ├── config.py      설정 조회/수정 REST API                          │
│  ├── kiwoom.py      키움 상태/계좌 REST API                          │
│  └── trading.py     전략 실행/중지 REST API                          │
│                                                                     │
│  engine/                                                            │
│  ├── scheduler.py   규칙 평가 스케줄러 (1분 주기)                    │
│  ├── evaluator.py   조건 평가 로직                                   │
│  └── signal.py      신호 생성 → kiwoom.order 호출                   │
│                                                                     │
│  kiwoom/                                                            │
│  ├── com_client.py  COM 객체 래퍼 (pywin32)                         │
│  ├── session.py     세션 관리 (connect/switch/disconnect)            │
│  ├── order.py       주문 실행 (send_order)                           │
│  └── account.py     잔고/포지션 조회                                 │
│                                                                     │
│  storage/                                                           │
│  ├── config_manager.py  config blob 동기화 관리 (암호화는 서버사이드)  │
│  └── log_db.py          logs.db SQLite 관리                         │
│                                                                     │
│  cloud/                                                             │
│  ├── context.py     컨텍스트 fetch (장 마감 후 1회)                  │
│  └── heartbeat.py   익명 하트비트 (5분마다)                          │
└──────────────────────────┬──────────────────────────────────────────┘
                           │  COM API (Windows 전용)
                           ▼
               ┌───────────────────────┐
               │  영웅문 HTS            │
               │  (사용자가 직접 로그인) │
               │  ├── 주문 실행         │
               │  ├── 체결 조회         │
               │  └── 잔고 조회         │
               └───────────────────────┘
```

---

## 3. 역할 분리

| 구분 | 역할 | 저장 데이터 |
|------|------|-----------|
| **클라우드** | React 정적 호스팅, Auth API, 공개 시장 API, 설정 blob 동기화 | users(이메일+password_hash), config_blobs(서버사이드 AES-256-GCM), refresh_tokens, heartbeat |
| **로컬 서버** | 키움 COM API 실행, 규칙 평가, 설정 저장, WS 서버 | config.blob.enc (메모리), local_secrets.json, logs.db, token.dat |
| **키움 HTS** | 사용자 인증, 주문 중계, 시세 제공 | ID/PW/공동인증서 (우리 앱 미보관) |

**통신 방향:**
```
React ──WS/HTTP──▶ 로컬 서버        (설정 변경, 전략 ON/OFF)
로컬 서버 ──WS──▶ React            (체결 결과, 잔고 업데이트, 알림)
로컬 서버 ──HTTP──▶ 클라우드        (컨텍스트 fetch, heartbeat, config-blob 업로드)
클라우드 ──HTTP──▶ 로컬 서버        ❌ 없음 (클라우드에서 로컬로 연결 불가)
```

---

## 4. 인증 & 서버사이드 암호화

### 4.1 인증 구조

| 구분 | 여부 | 이유 |
|------|:----:|------|
| 클라우드 Auth (이메일 + 비밀번호) | ✅ | 프로파일 식별, JWT 발급, 설정 접근 |
| 로컬 서버 Auth | ❌ | localhost-only 수신, 외부 접근 불가 |

### 4.2 로그인 흐름

```
[사용자]
  이메일 + 비밀번호 입력 → POST /api/auth/login
       ↓
[클라우드]
  Argon2id(password) 검증 → JWT (24h) + Refresh Token (30d) 반환
       ↓
[로컬 클라이언트]
  token.dat에 Refresh Token 저장
       ↓
  GET /api/v1/config (JWT 포함)
       ↓
[서버]
  config_blobs.blob → AES-256-GCM.decrypt(blob, SERVER_KEY) → JSON 응답
       ↓
[클라이언트]
  설정 메모리 로드 → 전략 엔진 시작
```

### 4.3 자동 재시작 흐름 (부팅 시)

```
exe 시작
    ↓
token.dat → Refresh Token 읽기
    ↓
POST /api/auth/refresh
  → 성공: 새 JWT + 새 Refresh Token (Rotation)
  → 실패: 트레이 알림 "재로그인 필요"
    ↓
GET /api/v1/config (새 JWT)
  → 서버가 복호화 → JSON 응답
    ↓
전략 엔진 시작 ← 사용자 개입 없음
```

### 4.4 서버사이드 암호화 설계

```
PUT /api/v1/config ← 클라이언트 평문 JSON
                           ↓
                   [서버 API 레이어]
                   AES-256-GCM.encrypt(json, SERVER_KEY)
                           ↓
                   config_blobs 테이블 저장

GET /api/v1/config → 클라이언트 평문 JSON
                           ↑
                   [서버 API 레이어]
                   AES-256-GCM.decrypt(blob, SERVER_KEY)
                           ↑
                   config_blobs 테이블 조회
```

**법적 근거:**
- [개인정보보호법 제29조](https://www.law.go.kr/법령/개인정보보호법) 안전조치의무
- [개인정보의 안전성 확보조치 기준](https://www.law.go.kr/행정규칙/개인정보의안전성확보조치기준) §10 암호화

**보안 특성:**

| 위협 시나리오 | 결과 |
|-------------|------|
| DB 직접 접근 | 암호화 blob — SERVER_KEY 없으면 복호화 불가 |
| JWT 탈취 | 설정 조회 가능 (API 경유), 24h TTL |
| 비밀번호 분실 | 서버가 재설정 → 설정 데이터 영향 없음 ✅ |
| SERVER_KEY 유출 | 전체 설정 데이터 노출 (AWS KMS 사용 시 위험 최소화) |

---

## 5. 데이터 저장 모델

### 5.1 로컬 PC (`%APPDATA%\StockVision\`)

| 파일 | 내용 | 보호 방식 | 클라우드 동기화 |
|------|------|:--------:|:--------------:|
| `token.dat` | Refresh Token | OS 파일 권한 | ❌ |
| `local_secrets.json` | 계좌번호 (평문) | — | ❌ 절대 금지 |
| `logs.db` | 체결 로그, 오류, 전략 이력 | — | ❌ |

```json
// local_secrets.json (절대 업로드 금지)
{ "account_no": "1234567890" }
```

### 5.2 클라우드 DB

| 테이블 | 주요 컬럼 | 비고 |
|--------|------|------|
| `users` | id, email, email_verified, password_hash, nickname | Argon2id 해싱 |
| `refresh_tokens` | user_id, token_hash, expires_at | SHA-256(token) 저장, 30d TTL |
| `email_verification_tokens` | user_id, token, expires_at, used | 이메일 인증 1회용 |
| `password_reset_tokens` | user_id, token, expires_at, used | 비밀번호 재설정 1회용, 10분 |
| `config_blobs` | user_id, blob, updated_at | 서버사이드 AES-256-GCM 암호화 |
| `heartbeat` | uuid, version, os, kiwoom_connected, ts | 개인정보 없음 |

---

## 6. 핵심 데이터 흐름

### 6.1 설치 후 첫 실행

```
[사용자]
  stockvision_setup.exe 실행
       ↓
[exe]
  localhost:8765 FastAPI 서버 시작 (백그라운드)
  브라우저 자동 열기: https://stockvision.app
       ↓
[React]
  ws://localhost:8765/ws 자동 연결 시도
  연결 성공 → 로그인 화면 표시
       ↓
[사용자]
  이메일 + 비밀번호 입력 → 로그인
       ↓
[React]
  JWT + Refresh Token 수신
  token.dat에 Refresh Token 저장
       ↓
  GET /api/v1/config → 서버 복호화 → 전략 로드 → 대시보드
       ↓
[사용자]
  설정 → "키움 연결" → 영웅문 HTS 기동 안내
       ↓
[영웅문 HTS]
  사용자가 직접 로그인 (ID/PW + 공동인증서)
       ↓
[로컬 서버]
  이미 로그인된 COM 세션에 연결 → 잔고 조회 → 대시보드 표시
```

### 6.2 전략 자동 실행 (1분 주기)

```
[Scheduler] 매 1분마다
       ↓
[Evaluator] cloud_config.enc(복호화된 메모리 캐시)에서 활성 규칙 로딩
       ↓
[Context Cache] 로컬 캐시된 시장 변수 (RSI, 모멘텀 등) 조회
       ↓
[Evaluator] 조건 평가: rule.condition → True/False
       ↓ (True인 경우)
[Signal] 중복 실행 체크 (state machine: NEW → SENT → FILLED)
       ↓
[Kiwoom Order] COM API send_order() 호출
       ↓
[logs.db] 주문/체결 결과 기록
       ↓
[WS Push] React에 execution_result 이벤트 전송
```

### 6.3 PC2 이전 (설정 동기화)

```
[PC1 로컬 서버]
  설정 변경 감지 → 500ms debounce
  PUT /api/v1/config (평문 JSON) → 서버 AES-256-GCM 암호화 → 저장
       ↓
[PC2 설치 후 첫 실행]
  이메일 + 비밀번호 로그인 → JWT + Refresh Token 수신
  token.dat에 Refresh Token 저장
  GET /api/v1/config → 서버 복호화 → 전략/설정 완전 복원
  local_secrets.json → 계좌번호 수동 입력 (1회)
```

### 6.4 계정 전환 (서버 재시작 없이)

```
[사용자] UI에서 "계정 전환" 클릭
       ↓
[로컬 서버] 실행 중인 전략 일시 중지
[로컬 서버] KiwoomSession.logout()
       ↓
[영웅문 HTS] 사용자가 다른 계정으로 재로그인
       ↓
[로컬 서버] KiwoomSession.connect() → 새 세션 획득
[로컬 서버] local_secrets.json 계좌번호 업데이트
       ↓
✓ 전략 재시작 (서버 재시작 불필요)
```

---

## 7. WebSocket 메시지 프로토콜

### React → 로컬 서버 (명령)

```json
{ "type": "strategy_toggle", "data": { "rule_id": 1, "is_active": true } }
{ "type": "config_update",   "data": { "kiwoom.mode": "demo" } }
{ "type": "jwt_unlock",      "data": { "jwt": "eyJhbGc..." } }
```

### 로컬 서버 → React (이벤트)

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
```json
{
  "type": "alert",
  "data": { "level": "warn", "message": "규칙 #1 평가 오류: 데이터 없음" }
}
```

---

## 8. REST API (로컬 서버)

```
GET    /api/health              서버 상태
GET    /api/kiwoom/status       키움 연결 상태 + 모드
GET    /api/account             잔고/포지션
PATCH  /api/config              설정 업데이트 (500ms debounce 자동 저장)
POST   /api/config/unlock       React → 로컬 서버에 JWT 전달 (token.dat 없을 때)
POST   /api/strategy/start      전략 전체 시작
POST   /api/strategy/stop       전략 전체 중지
GET    /api/logs?limit=100      체결/오류 로그
```

---

## 9. 배포 모델

| 항목 | 내용 |
|------|------|
| 배포 형태 | 단일 `.exe` (PyInstaller 번들) |
| 포함 | FastAPI + uvicorn + pywin32 + 의존성 |
| 미포함 | React 앱 (cloud 호스팅) |
| 실행 후 | 시스템 트레이 아이콘 + 백그라운드 서버 시작 |
| 업데이트 | `GET /api/version` 폴링 → 신버전 시 다운로드 안내 |
| 자동 시작 | Windows 시작프로그램 등록 (선택 옵션) |
| 언어/런타임 | Python 3.13, Windows 전용 (COM API 의존) |

---

## 10. 키움 API 호출 제한 관리

| 기능 | 제한 | 대응 |
|------|------|------|
| 조회 API | 초당 5건 | 조회 큐 + 200ms 간격 |
| 주문 API | 초당 5건 | 주문 큐 + FIFO |
| 실시간 등록 | 최대 200개 종목 | 보유 종목 기준 자동 관리 |

---

## 11. 에러 처리 및 복구

| 상황 | 처리 |
|------|------|
| 클라우드 연결 끊김 | 로컬 서버 정상 작동 유지, 컨텍스트는 캐시 사용 |
| 키움 세션 만료 | 자동 재연결 3회 → 실패 시 WS로 React에 알림 |
| 전략 평가 오류 | 해당 규칙만 비활성화 + logs.db 기록 |
| exe 재시작 | token.dat → Refresh Token → 새 JWT → GET /api/v1/config 자동 재로드 |
| WS 연결 끊김 | React 자동 재연결 (1s → 5s → 30s 백오프) |
| JWT 만료 (24h) | Refresh Token으로 자동 갱신 → 실패 시 트레이 알림 후 재로그인 |
| Refresh Token 만료 (30d) | 트레이 알림 → 브라우저 로그인 → 새 JWT 발급 → 자동 재개 |

---

## 12. 보안 원칙

| 원칙 | 구현 |
|------|------|
| 키움 자격증명 미보관 | 영웅문 HTS에 위임, 우리 파일에 없음 |
| 서버사이드 암호화 | AES-256-GCM (개인정보보호법 제29조 준수, 법적 최소 초과) |
| 비밀번호 해싱 | Argon2id (개인정보 안전성확보조치기준 §8) |
| 계좌번호 분리 | local_secrets.json — 서버 미보관, 클라우드 업로드 절대 금지 |
| localhost 격리 | 로컬 서버는 0.0.0.0 bind 금지 → 127.0.0.1만 수신 |
| 하트비트 익명 | UUID + 버전만, 개인정보 없음 |
| Rate limit | 로그인 실패 IP당 10회/시간, CORS stockvision.app만 허용 |
| Refresh Token 보안 | SHA-256(token) 서버 저장, Rotation, 30일 TTL |

---

## 13. 미결 항목

| 항목 | 우선순위 |
|------|---------|
| CONFIG_ENCRYPTION_KEY 운영 환경 키 rotation 정책 (AWS KMS) | 높음 |
| 멀티 디바이스 Refresh Token 목록 관리 UI | 중간 |
| exe 자동 업데이트 메커니즘 | 중간 |
| Windows 시작프로그램 자동 등록 기본값 | 낮음 |
| 계정 전환 중 체결 진행 중 주문 처리 | 중간 |
| 개인정보 수집 법적 검토 (PIPA 준수 확인) | 높음 (배포 전 필수) |

---

## 14. 연관 문서

| 문서 | 경로 |
|------|------|
| 로컬 서버 명세 | `spec/local-bridge/spec.md` |
| 인증 명세 | `spec/auth/spec.md` |
| 키움 연동 명세 | `spec/kiwoom-integration/spec.md` |
| 실행 엔진 명세 | `spec/execution-engine/spec.md` |
| 컨텍스트 클라우드 명세 | `spec/context-cloud/spec.md` |
| Phase 1/2 아키텍처 | `docs/architecture.md` |

---

**마지막 갱신**: 2026-03-04 (인증 모델 확정: 이메일+비밀번호, 서버사이드 AES-256-GCM, Refresh Token)
**상태**: 확정 (Phase 3 구현 기준 문서)
