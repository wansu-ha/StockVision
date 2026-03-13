# StockVision 전체 프로젝트 리뷰 종합

> 작성일: 2026-03-13 | 리뷰어: Claude Code

---

## 1. 전체 현황

| 영역 | Critical | High | Medium | Low | 미완성 |
|------|----------|------|--------|-----|--------|
| 로컬 서버 | 5 | 9 | 7 | — | 5 |
| 클라우드 서버 | 3 | 6 | 8 | 6 | 6 |
| 프론트엔드 | 4 | 10 | 6 | — | 5 |
| 문서 | 2 | — | 5 | — | — |
| **합계** | **14** | **25** | **26** | **6** | **16** |

---

## 2. Critical 이슈 전체 목록

### 로컬 서버

| ID | 내용 | 파일 |
|----|------|------|
| LS-C1 | **트레이 Kill Switch가 엔진에 실제 명령을 전달하지 않음** — `set_engine_running(False)`는 하트비트 플래그만 수정, 실제 주문 계속 나감 | tray/tray_app.py:135 |
| LS-C2 | **PUT /api/settings/alerts 인증 없음** — `require_local_secret` 누락, 경고 임계값 무단 변경 가능 | routers/alerts.py:31 |
| LS-C3 | **재연결 후 WS 시세 재구독 없음** — 엔진이 빈 시세로 동작, 주문 0건 | broker/kis/reconnect.py:85 |
| LS-C4 | **LogDB.write() asyncio 블로킹** — 동기 SQLite 연결이 이벤트 루프 차단 | storage/log_db.py:66 |
| LS-C5 | **WS `sec` query param이 URL/로그에 노출** — local_secret 평문 기록 | routers/ws.py:101 |

### 클라우드 서버

| ID | 내용 | 파일 |
|----|------|------|
| CS-C1 | **`broker.authenticate()` → AttributeError** — ABC에 없는 메서드, KIS WS 데이터 수집 불가 | collector/scheduler.py:157 |
| CS-C2 | **OAuth 동시 로그인 → IntegrityError (500)** — unique constraint 위반 미처리 | services/oauth_service.py:139 |
| CS-C3 | **password_hash nullable 설계 미비** — OAuth 등록 시 `""` 저장, `nullable=True`로 변경 필요 | models/user.py:29 |

### 프론트엔드

| ID | 내용 | 파일 |
|----|------|------|
| FE-C1 | **OAuth 콜백 → AuthContext 미갱신** — 토큰 저장하지만 `login()` 미호출, 로그인 항상 실패 | pages/OAuthCallback.tsx:31 |
| FE-C2 | **alertsClient 인증 헤더 없음** — bare axios 사용, 모든 경고 설정 API 실패 | services/alertsClient.ts:29 |
| FE-C3 | **Settings handleLaunch setInterval 누수** — 언마운트 시 미정리 | pages/Settings.tsx:63 |
| FE-C4 | **DeviceManager 페어링 X-Local-Secret 없음** — raw fetch, 디바이스 페어링 비작동 | components/DeviceManager.tsx:28 |

### 문서

| ID | 내용 |
|----|------|
| DOC-C1 | **CLAUDE.md 서버 기동 명령어 2개 모두 오류** — `cd` 후 실행 시 ModuleNotFoundError |
| DOC-C2 | **roadmap.md C6 "미착수" 표시** — 실제 구현 완료 (16/16 PASS) |

---

## 3. High 이슈 주요 항목 (발췌)

### 안전/보안 (거래 직결)

- **LS-H4**: LimitChecker 일일 예산 — 재시작 시 0 리셋, 중복 실행 가능
- **LS-H9**: FILL 로그가 제출 즉시 기록 (실체결 아님) → 손익 계산 부정확
- **LS-H3**: KIS 매도 시장가 TR ID 오류 가능 → 실거래 주문 거부 위험
- **LS-H7**: Watchdog에 엔진 참조 미주입 → 엔진 하트비트 체크 항상 스킵

### 인증/보안

- **LS-H1**: POST /api/auth/token 인증 없이 local_secret 획득 가능
- **CS-H3**: Rate limiter X-Forwarded-For 스푸핑 가능

### 프론트엔드 UX

- **FE-I5**: StrategyBuilder 편집 모드 → 조건이 기본값으로 리셋 (데이터 손실)
- **FE-I8**: Layout.tsx 라이트 테마 ↔ 나머지 다크 테마 불일치
- **FE-I1**: WS 3회 실패 후 영구 중단, 재연결 불가

---

## 4. 미완성 기능 전체 목록

### 로컬 서버

| ID | 기능 | 차단 요인 |
|----|------|----------|
| LS-I1 | KIS WS approval_key 발급 | 미구현 (실거래 WS 불가) |
| LS-I2 | KIS 모의/실전 자동 감지 | 미구현 (항상 모의) |
| LS-I3 | WS heartbeat_ack 버전 처리 | 미구현 (규칙 자동 갱신 안 됨) |
| LS-I4 | 오프라인 내성 (6AC) | 부분 구현 |
| LS-I5 | 하트비트 WS ↔ HTTP 통합 | 미구현 |

### 클라우드 서버

| ID | 기능 | 차단 요인 |
|----|------|----------|
| CS-I1 | 실시간 MinuteBar 수집 | CS-C1 (authenticate → connect) |
| CS-I2 | DART 배당 데이터 | get_dividends() stub |
| CS-I3 | WS 원격 제어 (C7/C8) | 미착수 |
| CS-I4 | Redis rate limiting | 인메모리만 구현 |
| CS-I5 | MinuteBar 데이터 | CS-C1 의존 |
| CS-I6 | context_version | 하드코딩 `1` |

### 프론트엔드

| ID | 기능 |
|----|------|
| FE-S1 | cloudAuth.updateProfile 미구현 |
| FE-S2 | StrategyBuilder DSL 역파싱 |
| FE-S3 | ProtoA/B/C 목업 데이터만 |
| FE-S4 | 원격 제어 (C6-C8) Firebase/FCM |
| FE-S5 | MinuteBar 데이터 수집 |

---

## 5. 문서 정비 필요 항목

| 우선순위 | 내용 |
|----------|------|
| 1 | CLAUDE.md 기동 명령어 수정 |
| 2 | roadmap.md C6 → "구현 완료" |
| 3 | 6개 spec 상태 헤더 갱신 (초안/진행 중 → 구현 완료) |
| 4 | docs/README.md 깨진 링크 2개 수정 |
| 5 | Phase 1/2 문서 5개에 SUPERSEDED 헤더 추가 |
| 6 | architecture.md C6 기능 추가 (E2E, WS relay, OAuth2, 디바이스) |
| 7 | CLAUDE.md 프로젝트 구조 갱신 |

---

## 6. 권장 수정 순서

### Phase 1: 즉시 수정 (안전 Critical)

1. LS-C1: Kill Switch → 실제 엔진 중지 API 호출로 변경
2. LS-C2: alerts 라우터에 `require_local_secret` 추가
3. LS-H9: FILL 로그를 주문 제출이 아닌 체결 확인 후 기록
4. LS-H4: LimitChecker 일일 금액 → 로그DB에서 당일 체결 합산으로 복원

### Phase 2: 보안/인증

5. LS-C5: WS 인증을 첫 프레임 토큰 방식으로 변경
6. LS-H1: /api/auth/token에 일회성 nonce 검증 추가
7. CS-H3: Rate limiter — trusted proxy만 X-Forwarded-For 허용
8. FE-C2: alertsClient → localClient 인스턴스 교체

### Phase 3: 안정성

9. LS-C3: 재연결 후 subscribe_quotes() 재호출
10. LS-C4: LogDB를 aiosqlite 또는 asyncio.to_thread() 래핑
11. CS-C1: `broker.authenticate()` → `broker.connect()` 수정
12. FE-C1: OAuth 콜백 → loginWithTokens() 메서드 추가

### Phase 4: UX/문서

13. FE-I5: StrategyBuilder 편집 버튼 비활성화 (DSL 역파싱 전까지)
14. FE-I8: Layout.tsx 다크 테마 통일
15. 문서 정비 (위 7개 항목)

---

## 7. 테스트 커버리지 갭

### 클라우드 서버 (테스트 없는 영역)
- WebSocket relay / session manager
- Market data API (/bars, /quote, /financials, /dividends)
- OAuth flow
- Device management
- Context service (RSI/MACD/Bollinger)
- Admin service key management
- Scheduler cron 작업
- Data providers (DART, yfinance)

### 로컬 서버
- 기존 41/41 통과하지만 재연결 시나리오, 동시성 테스트 없음

### 프론트엔드
- E2E 테스트 없음, 컴포넌트 단위 테스트 없음

---

## 8. 세부 리뷰 파일

- [로컬 서버 리뷰](review-local-server.md)
- [클라우드 서버 리뷰](review-cloud-server.md)
- [프론트엔드 리뷰](review-frontend.md)
- [문서 정합성 리뷰](review-documentation.md)
