> 작성일: 2026-03-15 | 상태: 초안 | 미개발 사항 리뷰

# StockVision 미개발 사항 및 부족한 점 리뷰

## 1. 미구현 Spec (초안 상태) — 11건

### 1.1 relay-infra (릴레이 인프라) — 미충족 기준 25개 ⚠️ 최우선
- 클라우드 `/ws/relay`, `/ws/remote` 엔드포인트 미구현
- RelayManager, SessionManager 서비스 없음
- E2E 암호화 메시지 프로토콜 미구현
- 오프라인 명령 큐, 세션 관리, 감사 로그 미구현
- **영향**: remote-ops, remote-control의 기반 인프라 → 이것 없이 원격 제어 불가

### 1.2 remote-ops (원격 운영) — 미충족 기준 15개
- 원격 엔진/브로커/킬스위치 상태 실시간 확인 불가
- 원격 arm/stop 기능 미구현
- FCM 푸시 알림 미구현 (FirebaseService)
- PWA (manifest.json, Service Worker) 미구현
- **의존**: relay-infra 선행 필요

### 1.3 dsl-client-parser (DSL 클라이언트 파서) — 미충족 기준 6개
- TypeScript DSL lexer + parser 미구현
- dslConverter 모듈 (DSL ↔ 폼 데이터 변환) 없음
- ConditionEditor 모드 토글 (폼 ↔ 스크립트) 미구현
- DslEditor 컴포넌트 신규 생성 필요
- **영향**: 서버에 저장된 기존 규칙을 프론트에서 폼 모드로 편집 불가

### 1.4 chart-timeframe (차트 타임프레임) — 미충족 기준 12개
- 해상도 버튼(1m, 5m, 15m, 1h, D, W, M) 전환 UI 미구현
- 분봉/시봉 로컬 서버 API (`GET /api/v1/bars/{symbol}`) 미구현
- KIS REST 분봉 조회 + 로컬 DB 캐시 없음
- 5분/15분/시봉 1분봉 집계 로직 미구현
- 좌측 스크롤 lazy load 미구현

### 1.5 engine-live-execution (전략 엔진 E2E) — 미충족 기준 4개
- IndicatorProvider 미구현 (RSI, MACD, 볼린저 등 지표 계산)
- Heartbeat 버전 비교 타입 불일치
- E2E 수동 검증 시나리오 미완
- **영향**: 실제 지표 기반 전략 실행 불가

### 1.6 security-phase2 (보안 2차) — 미충족 기준 7개
- Rate Limiter: X-Forwarded-For 헤더 조작 방지 (rightmost-N IP 추출) 미구현
- Redis ZSET 슬라이딩 윈도우 rate limit 미구현
- Refresh Token: localStorage → sessionStorage 이동 미완
- "로그인 유지" 체크박스 UI 없음
- User.deleted_at 소프트 삭제 필드 없음

### 1.7 frontend-quality (프론트엔드 품질) — 미충족 기준 6개
- ErrorBoundary 컴포넌트 없음 (런타임 에러 시 흰 화면)
- React Query staleTime 미설정 (22+ 쿼리에 추가 필요)
- 프로필 수정 기능 미구현 (`PATCH /auth/profile` + UI)

### 1.8 local-server-resilience (로컬 서버 견고성) — 미충족 기준 7개
- Config atomic write 미구현 (동시 저장 시 파일 손상 가능)
- 모의/실전 자동 감지 로직 없음
- SyncQueue 비활성 상태 (클라우드 끊김 시 규칙 변경 유실 가능)
- Heartbeat WS Ack 버전 파싱 미구현

### 1.9 kis-adapter-completion (KIS 어댑터 완성) — 미충족 기준 5개
- KIS 매도 TR ID 검증 미완 (실전/모의 분리)
- WebSocket approval_key 발급 미구현
- `KisAuth.get_approval_key()` 메서드 없음

### 1.10 watchlist-heart (관심종목 하트) — 미충족 기준 8개
- HeartToggle 컴포넌트 미구현
- ListView, StockSearch, DetailView에 하트 아이콘 적용 안 됨
- 낙관적 업데이트 (useMutation) 미구현
- 연속 클릭 디바운스 없음

### 1.11 legal (법무 UI 연동) — 미충족 기준 3개 (확정 상태)
- 회원가입 시 약관 동의 체크박스 UI 없음
- 투자 면책 고지 팝업 (전략 활성화 시) 없음
- 설정 페이지에서 약관 열람 불가

---

## 2. 코드 수준 부족한 점

### 2.1 백엔드-프론트엔드 불일치 ⚠️
| 문제 | 위치 |
|------|------|
| `POST /api/v1/auth/profile` 엔드포인트 미구현 | `cloud_server/api/auth.py`에 없음 |
| 프론트엔드 `cloudAuth.updateProfile()`이 항상 실패 반환 | `frontend/src/services/cloudClient.ts:83-87` |

### 2.2 TODO 항목 — 3건
| 파일 | 내용 |
|------|------|
| `frontend/src/pages/StrategyBuilder.tsx:114` | script → 폼 역파싱 미구현 |
| `frontend/src/services/cloudClient.ts:84` | auth/profile 엔드포인트 없음 |
| `local_server/routers/config.py:98` | KIS 모의/실전 감지 로직 미구현 |

### 2.3 에러 처리 부족
- `frontend/src/pages/StrategyBuilder.tsx:65,76,83` — 로컬 서버 규칙 동기화 시 `.catch(() => {})` (사용자 피드백 없음)
- `frontend/src/context/AuthContext.tsx:61` — 인증 복원 실패 시 `.catch(() => {})` (무시)
- ErrorBoundary 컴포넌트 부재 → 런타임 에러 시 전체 화면 깨짐 가능

### 2.4 Stub/Fallback 구현 (의도적이지만 운영 시 주의)
- AI 서비스: API 키 없을 때 stub 분석 결과 반환 (`source: "stub"`)
- 브로커: `sv_core.broker.kis` 미설치 시 stub KisAdapter 사용
- Redis: 불가 시 인메모리 폴백 (`except Exception: pass`)

---

## 3. 우선순위 제안

### P0 — 운영 전 필수
1. **frontend-quality** (ErrorBoundary, staleTime) — 사용자 경험 직결
2. **security-phase2** (RT 보안, rate limit IP, soft-delete) — 보안 필수
3. **auth/profile 엔드포인트** — 프론트와 백엔드 불일치 해소
4. **legal UI 연동** — 법적 요구사항

### P1 — 핵심 기능 완성
5. **kis-adapter-completion** — 실매매 연동 필수
6. **engine-live-execution** (IndicatorProvider) — 지표 기반 전략 실행
7. **dsl-client-parser** — 규칙 편집 UX 핵심
8. **chart-timeframe** — 차트 기능 완성
9. **local-server-resilience** — 안정성

### P2 — 확장 기능
10. **watchlist-heart** — UX 개선
11. **relay-infra** → **remote-ops** — 원격 제어 (의존 체인)

---

## 4. 통계 요약

| 항목 | 수치 |
|------|------|
| 초안 상태 Spec | 11개 |
| 미충족 수용 기준 합계 | ~100개 |
| 코드 TODO 항목 | 3건 |
| 백엔드/프론트엔드 불일치 | 1건 |
| Silent catch 블록 | 10+ 건 |
| Stub 구현 | 5건 |
