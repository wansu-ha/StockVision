> 작성일: 2026-03-15 | 상태: 초안 | 미개발 사항 리뷰

# StockVision 미개발 Spec & Plan 상세 분석

## 요약

| # | Spec | 상태 | Plan 유무 | 공수 | 미충족 기준 | 의존성 |
|---|------|------|-----------|------|------------|--------|
| 1 | frontend-quality | 초안 | ✅ 있음 | 7-10h | 6개 | 없음 |
| 2 | security-phase2 | 초안 | ✅ 있음 | 6-10h | 7개 | S1→S2 순차 |
| 3 | legal (UI 연동) | 확정 | ✅ 있음 (plan-v2) | 8-10h | 3개 | 없음 |
| 4 | kis-adapter-completion | 초안 | ✅ 있음 | 3-5h | 5개 | 없음 (KIS 문서 필요) |
| 5 | engine-live-execution | 초안 | ✅ 있음 | 2-3일 | 4개 | S2→S3 순차 |
| 6 | dsl-client-parser | 초안 | ✅ 있음 | 3-4일 | 6개 | D1→D2→D3→D4 순차 |
| 7 | chart-timeframe | 초안 | ❌ 없음 | 5-7일 | 12개 | 3 스테이지 |
| 8 | local-server-resilience | 초안 | ✅ 있음 | 2-3일 | 7개 | R1/R2/R4 병렬→R3 |
| 9 | watchlist-heart | 초안 | ❌ 없음 | 1-2일 | 8개 | 없음 |
| 10 | relay-infra | 초안 | ✅ 있음 | 2-3주 | 16개 | 8단계 순차 |
| 11 | remote-ops | 초안 | ✅ 있음 | 2-3주 | 23개 | relay-infra 선행 |
| — | remote-control | 확정 | ✅ 있음 | 3-4주 | 20개 | relay-infra 선행 |

---

## 1. frontend-quality (프론트엔드 품질) — P0

> Plan: ✅ 있음 (2026-03-16) | 공수: 7-10h | 변경 파일: 10개

### 구현 항목

| ID | 항목 | 카테고리 | 상세 |
|----|------|---------|------|
| F1 | ErrorBoundary | 안정성 | 런타임 에러 → 폴백 UI (흰 화면 방지) |
| F2 | React Query staleTime | 성능 | 데이터 유형별 캐시 TTL 설정 (22+ 쿼리) |
| F3 | 프로필 수정 | 기능 | 닉네임 편집 + `PATCH /auth/profile` 백엔드 |

### 수용 기준
- [ ] 런타임 에러 시 폴백 UI 표시 (흰 화면 아님)
- [ ] 에러 후 라우트 전환 시 정상 복구
- [ ] 종목명 5분 이내 재마운트 → 네트워크 요청 없음 (캐시)
- [ ] 규칙 목록 2분 이내 재마운트 → 캐시 사용
- [ ] 닉네임 변경 저장 시 서버 반영
- [ ] 닉네임 2자 미만 → 유효성 검증 에러

### Plan 의존 구조
```
F1 (ErrorBoundary) ─── 독립
F2 (staleTime)     ─── 독립
F3 (Profile)       ─── 독립
→ 3개 모두 병렬 가능
```

### 변경 파일
- `frontend/src/components/ErrorBoundary.tsx` — **신규**
- `frontend/src/App.tsx` — ErrorBoundary 래핑
- `frontend/src/hooks/useStockData.ts`, `useMarketContext.ts` — staleTime
- `frontend/src/pages/*.tsx` (6개) — staleTime
- `cloud_server/api/auth.py` — PATCH /profile 추가
- `frontend/src/services/cloudClient.ts` — updateProfile 연결

### 평가
- **Plan 완성도**: 높음 — 파일별 변경 사항 명확
- **리스크**: 낮음 — 모두 독립 작업, API 추가만 포함
- **부족한 점**: F2의 22+ 쿼리 목록이 plan에 구체적으로 열거되어 있는지 확인 필요

---

## 2. security-phase2 (보안 2차) — P0

> Plan: ✅ 있음 (2026-03-16) | 공수: 6-10h | 변경 파일: 6개

### 구현 항목

| ID | 항목 | 감사 ID | 상세 |
|----|------|---------|------|
| S1 | Rate Limiter IP Trust | H4 | rightmost-N X-Forwarded-For IP 추출 |
| S2 | Redis Rate Limiter | H7 | 인메모리 → Redis ZSET 슬라이딩 윈도우 |
| S3 | RT 보안 강화 | C4 | localStorage → sessionStorage + "로그인 유지" |
| S4 | Soft-Delete | 신규 | `deleted_at` 필드, 비활성 사용자 로그인 차단 |

### 수용 기준
- [ ] X-Forwarded-For 헤더 조작으로 rate limit 우회 불가
- [ ] Redis 가용 → ZSET에 카운터 저장
- [ ] Redis 불가 → 인메모리 폴백 동작
- [ ] 기본 로그인 → RT가 sessionStorage에 저장
- [ ] "로그인 유지" 체크 시에만 localStorage
- [ ] 사용자 삭제 → deleted_at 설정, DB row 유지
- [ ] 비활성 사용자 로그인 불가

### Plan 의존 구조
```
S1 (IP 추출) → S2 (Redis ZSET)  ← 같은 파일, 순차
S3 (RT 보안) ─── 독립
S4 (Soft-Delete) ─── 독립
→ S3, S4는 S1과 병렬 가능
```

### 변경 파일
- `cloud_server/core/rate_limit.py` — S1 + S2
- `cloud_server/models/user.py` — S4 (deleted_at 필드)
- `frontend/src/context/AuthContext.tsx` — S3 (sessionStorage)
- `frontend/src/pages/Login.tsx` — S3 ("로그인 유지" 체크박스)

### 평가
- **Plan 완성도**: 높음 — 보안 감사 ID와 매핑 명확
- **리스크**: 중간 — RT 저장소 변경은 기존 사용자 세션 영향
- **부족한 점**: S4 마이그레이션 스크립트(Alembic) 언급 필요

---

## 3. legal (법무 UI 연동) — P0

> Plan: ✅ 있음 (plan-v2) | 공수: 8-10h | 문서 작성 완료, UI 연동만 잔여

### 현황
- 문서 4종 **완료**: 이용약관, 개인정보처리방침, 면책 고지, 증권사 약관 준수
- UI 연동 **미시작**: 동의 체크, 팝업, 설정 열람

### 수용 기준 (UI 관련)
- [ ] 회원가입 시 이용약관 + 개인정보처리방침 동의 체크
- [ ] 투자 면책 고지 팝업 (전략 활성화 시)
- [ ] 설정 페이지에서 약관 열람 가능

### 평가
- **Plan 완성도**: 중간 — plan-v2에 UI 구현 상세가 있으나 확인 필요
- **리스크**: 낮음 — 프론트엔드 UI + 간단한 백엔드 API
- **부족한 점**: 약관 버전 관리 + 재동의 정책 미정, 외부 법률 검수 미완

---

## 4. kis-adapter-completion (KIS 어댑터 완성) — P1

> Plan: ✅ 있음 (2026-03-16) | 공수: 3-5h | 변경 파일: 3개

### 구현 항목

| ID | 항목 | 상세 |
|----|------|------|
| K1 | 매도 TR ID 검증 | 현재 매수와 동일 TR ID 사용 → 실전/모의 분리 필요 |
| K2 | WS approval_key | access_token 대신 `/oauth2/Approval`에서 별도 키 발급 |

### 수용 기준
- [ ] 매도 TR ID가 KIS 공식 문서와 일치
- [ ] 실전/모의 TR ID 각각 올바른 값
- [ ] WebSocket 접속 시 별도 approval_key 사용
- [ ] approval_key 캐싱, 불필요한 재발급 없음
- [ ] KIS 계정 없이 mock 단위 테스트 통과

### Plan 의존 구조
```
K1 (매도 TR ID) ─── 독립
K2 (approval_key) ─── 독립
→ 병렬 가능
```

### 변경 파일
- `local_server/broker/kis/order.py` — K1
- `local_server/broker/kis/auth.py` — K2 (get_approval_key 메서드)
- `local_server/broker/kis/ws.py` — K2 (approval_key 사용)

### 평가
- **Plan 완성도**: 높음 — 변경 범위 명확
- **리스크**: 중간 — KIS API 포탈 접근 필요 (TR ID 테이블 확인)
- **블로커**: KIS 테스트 계정 미확보 → mock 검증만 가능

---

## 5. engine-live-execution (전략 엔진 E2E) — P1

> Plan: ✅ 있음 (2026-03-10) | 공수: 2-3일 | 브랜치: feat/engine-live-execution

### 핵심 문제 4가지

| ID | 문제 | 상태 |
|----|------|------|
| P1 | WS 실시간 시세 파싱 | ✅ 해결 |
| P2 | 지표 계산 누락 | ❌ IndicatorProvider 필요 |
| P3 | 규칙 동기화 타입 불일치 | ⚠️ rules_version int/str |
| P4 | E2E 실행 미검증 | ❌ 통합 테스트 필요 |

### 필요 지표 (일봉 기반)

| 키 | 설명 | 필요 데이터 |
|----|------|------------|
| `rsi_{N}` | RSI | N+1 종가 |
| `ma_{N}` | SMA | N 종가 |
| `ema_{N}` | EMA | N×2 종가 |
| `bb_upper/lower_{N}` | 볼린저 밴드 | N 종가 |
| `macd`, `macd_signal` | MACD(12,26,9) | 35 종가 |
| `avg_volume_{N}` | 평균 거래량 | N 거래량 |

### 설계 결정
- **데이터 소스**: yfinance 60일 일봉 → 로컬 직접 계산
- **캐시**: 하루 1회 갱신 (일봉은 장중 불변)
- **sv_core 미추출**: 클라우드/로컬 니즈 다름 → 각 서버에서 독립 계산

### Plan 의존 구조
```
S1 (WS 파서) ✅ ──┐
                   ├→ S3 (엔진 주입) → S5 (E2E 검증)
S2 (IndicatorProvider) ─┘
S4 (Heartbeat 타입 수정) ─────────────────┘
```

### 평가
- **Plan 완성도**: 높음 — P1 해결, 나머지 3개 명확
- **리스크**: 중간 — yfinance 의존 (장 시간 외 API 제한)
- **부족한 점**: IndicatorProvider 단위 테스트 명세 부족

---

## 6. dsl-client-parser (DSL 클라이언트 파서) — P1

> Plan: ✅ 있음 (2026-03-16) | 공수: 3-4일 | 변경 파일: 5개

### 구현 항목

| ID | 항목 | 타입 | 상세 |
|----|------|------|------|
| D1 | TypeScript DSL parser | 신규 | Python `sv_core/parsing/` 포팅 (lexer + parser) |
| D2 | DSL ↔ 폼 변환 | 신규 | `dslToConditions()` + round-trip 보장 |
| D3 | ConditionEditor 모드 토글 | 개선 | 폼 ↔ 스크립트 전환, 데이터 유지 |
| D4 | 에러 인라인 표시 | 개선 | 300ms 디바운스, 한국어 메시지, 줄/열 위치 |

### DSL 문법 (지원 범위)
```
rule      := "매수:" condition_expr "\n" "매도:" condition_expr
condition := field operator value (("AND" | "OR") field operator value)*
field     := identifier ("." identifier)*   # rsi_14, macd.signal
operator  := >, >=, <, <=, ==, !=
value     := number | string
```

### 수용 기준
- [ ] `parseDsl()` 올바른 구조 반환
- [ ] `dslToConditions()` → `conditionsToDsl()` round-trip 일치
- [ ] 서버 저장된 기존 규칙 → 폼 모드로 편집 가능
- [ ] 문법 에러 → 위치 + 한국어 메시지 표시
- [ ] 폼 ↔ 스크립트 모드 전환 시 데이터 유지
- [ ] 변환 불가능한 복잡 DSL → 스크립트 전용 모드

### Plan 의존 구조
```
D1 (TS parser) → D2 (conversion) → D3 (mode toggle) → D4 (error display)
→ 완전 순차 (각 단계가 이전 단계에 의존)
```

### 변경 파일
- `frontend/src/utils/dslParser.ts` — **신규** (lexer + parser)
- `frontend/src/utils/dslConverter.ts` — **신규** (변환 로직)
- `frontend/src/services/rules.ts` — conditionsToDsl 리팩터링
- `frontend/src/components/DslEditor.tsx` — **신규** (스크립트 편집기)
- `frontend/src/components/ConditionEditor.tsx` — 모드 토글 추가

### 평가
- **Plan 완성도**: 높음 — 문법 정의, 단계별 파일 명확
- **리스크**: 높음 — TS 파서 구현량 많음, Python 파서와 호환성 유지 필요
- **부족한 점**: 테스트 케이스 명세 부족, Python 파서와의 동작 일관성 검증 방법 미정

---

## 7. chart-timeframe (차트 타임프레임) — P1

> Plan: ❌ 없음 | 공수: 5-7일 | 스테이지 3개

### 현재 상태
- 일봉만 지원 (클라우드 yfinance → DB 캐시)
- 기간: 1W, 1M(기본), 3M, 6M, 1Y
- MinuteBar 모델 존재하나 데이터 수집/API 미구현
- BarBuilder WS 틱→1분봉 변환 코드 존재하나 API 미노출

### 해상도별 데이터 소스

| 해상도 | 소스 | 최대 기간 |
|--------|------|----------|
| 1m, 5m, 15m, 1h | 로컬 서버 (KIS REST, 30일) | ~30일 |
| 1D, 1W, 1M | 클라우드 (yfinance → DB 집계) | 연 단위 |

### API 변경

**클라우드** (기존 확장):
```
GET /api/v1/stocks/{symbol}/bars
  ?resolution=1d|1w|1mo  # 신규 파라미터
```

**로컬 서버** (신규):
```
GET /api/v1/bars/{symbol}
  ?resolution=1m|5m|15m|1h
  &start=...&end=...
```

### 수용 기준 (12개)
- [ ] 해상도 버튼(1m, 5m, 15m, 1h, D, W, M) 표시 및 전환
- [ ] 해상도별 기간 버튼 세트 동적 전환
- [ ] 일봉/주봉/월봉: 클라우드에서 정상 로드
- [ ] 분봉/시봉: 로컬 서버 연결 시 정상 로드
- [ ] 로컬 미연결 → 장중 해상도 버튼 비활성 + 툴팁
- [ ] 좌측 스크롤 → lazy load (디바운스 200~300ms)
- [ ] 이미 로드된 구간 재요청 방지
- [ ] 줌 인/아웃이 해상도를 변경하지 않음
- [ ] 로컬: `GET /api/v1/bars/{symbol}` 엔드포인트
- [ ] 로컬: KIS REST 분봉 조회 + DB 캐시
- [ ] 5분/15분/시봉은 1분봉 집계로 생성

### 구현 스테이지 (spec에서 제안)
```
Stage 1: 로컬 서버 분봉 API + KIS 연동 + 캐시
Stage 2: 클라우드 주봉/월봉 집계
Stage 3: 프론트엔드 해상도/기간 UI + lazy load + 소스 분기
```

### 평가
- **Plan 완성도**: ❌ Plan 미작성 — spec만 존재
- **리스크**: 높음 — 3계층(클라우드/로컬/프론트) 모두 변경, KIS REST API 연동
- **부족한 점**: Plan 작성 필요, 데이터 정합성 검증 방법 미정, 분봉 보존 기간 정책 미확정

---

## 8. local-server-resilience (로컬 서버 견고성) — P1

> Plan: ✅ 있음 (2026-03-16) | 공수: 2-3일 | 변경 파일: 7개

### 구현 항목

| ID | 항목 | 상세 |
|----|------|------|
| R1 | Config Atomic Write | tempfile + os.replace() 원자적 저장 |
| R2 | Mock/실전 자동 감지 | 계좌번호 패턴 + URL 기반 자동 판별 |
| R3 | SyncQueue 활성화 | 기존 구현 있으나 미사용 → 라우터/하트비트에 연결 |
| R4 | Heartbeat WS Ack 버전 | WS ack에서 버전 필드 파싱, HTTP와 동일 동작 |

### Plan 의존 구조
```
R1 (Config) ─── 독립
R2 (Mock)   ─── 독립     → 병렬 가능
R4 (Heartbeat) ─── 독립
      └→ R3 (SyncQueue) ─ R4의 재연결 감지로 flush 트리거
```

### 수용 기준
- [ ] Config 동시 저장 시 파일 손상 안 됨
- [ ] 모의 계좌 접속 → is_mock=true 자동 설정
- [ ] 수동/자동 불일치 → 경고 로그
- [ ] 클라우드 연결 끊김 → SyncQueue에 규칙 변경 저장
- [ ] 클라우드 재연결 → 큐 자동 플러시
- [ ] WS 모드에서 규칙 버전 변경 감지 → 자동 fetch
- [ ] HTTP/WS 동일 버전 변경 감지

### 평가
- **Plan 완성도**: 높음 — SyncQueue 기존 코드 활용, 변경 범위 명확
- **리스크**: 낮음 — 기존 구현 활성화 + 소규모 수정
- **특이사항**: R3은 이미 구현된 코드가 있어 연결만 하면 됨

---

## 9. watchlist-heart (관심종목 하트) — P2

> Plan: ❌ 없음 | 공수: 1-2일 | 변경 파일: 4개

### 수용 기준 (8개)
- [ ] ListView 각 종목 행에 하트 아이콘 표시
- [ ] 하트 클릭으로 토글 (행 클릭과 충돌 없음)
- [ ] StockSearch 검색 결과에 하트 표시 + 토글
- [ ] DetailView "관심 해제" 버튼 → 하트로 교체
- [ ] 낙관적 업데이트 (클릭 즉시 UI, 실패 시 롤백)
- [ ] 연속 클릭 디바운스 (300ms)
- [ ] 채워진 하트(빨강) / 빈 하트(회색)

### 핵심 설계
- `HeartToggle.tsx` 신규 컴포넌트 (heroicons)
- React Query useMutation + 낙관적 업데이트
- **API 변경 없음** — 기존 watchlist 엔드포인트 활용

### 평가
- **Plan 완성도**: ❌ Plan 미작성
- **리스크**: 낮음 — 프론트엔드 전용, API 변경 없음
- **부족한 점**: Plan 작성 필요하나 규모가 작아 spec만으로 구현 가능

---

## 10. relay-infra (릴레이 인프라) — P2 (원격 제어 기반)

> Plan: ✅ 있음 (초안) | 공수: 2-3주 | 8단계 순차 | 변경 파일: 클라우드 7, 로컬 5, 프론트 1

### 인프라 구성

```
[로컬 서버] ──WS──→ [클라우드 /ws/relay] ←──WS── [원격 디바이스 /ws/remote]
                         │
                    RelayManager
                    SessionManager
                    PendingCommand DB
                    AuditLog
```

### 8단계 Plan

| 단계 | 내용 | 주요 산출물 |
|------|------|-----------|
| 1 | 클라우드 WS `/ws/relay` | RelayManager 서비스 |
| 2 | 로컬 WS 클라이언트 | WsRelayClient (exponential backoff) |
| 3 | Heartbeat WS 전환 | HTTP 폴링 → WS heartbeat |
| 4 | 메시지 프로토콜 + 라우팅 | state/command/alert 메시지 |
| 5 | 클라우드 WS `/ws/remote` | SessionManager (디바이스 5대 제한) |
| 6 | E2E 암호화 모듈 | Python + TypeScript AES-256-GCM |
| 7 | 오프라인 명령 큐 | pending_commands 테이블 |
| 8 | 감사 로그 + Rate Limit | audit_log 테이블, 429 응답 |

### 수용 기준 (16개, 모두 미충족)
- WS 자동 연결/재연결, E2E 암호화, 메시지 envelope, 오프라인 큐, 세션 관리, 감사 로그 등

### 평가
- **Plan 완성도**: 중간 — 8단계 정의되었으나 각 단계 상세 구현 명세 부족
- **리스크**: 매우 높음 — 가장 큰 미구현 영역, 3계층 모두 변경
- **의존 관계**: remote-ops, remote-control 모두 이 인프라에 의존
- **부족한 점**: 부하 테스트 기준 미정, WS 세션 복구 시나리오 미상세

---

## 11. remote-ops (원격 운영) — P2

> Plan: ✅ 있음 (초안) | 공수: 2-3주 | 9단계 | relay-infra 선행

### 9단계 Plan

| 단계 | 내용 |
|------|------|
| 1 | 원격 상태 수신 (useRemoteControl 훅, E2E 복호화) |
| 2 | 원격 모드 감지 + UI 분기 (useRemoteMode, OpsPanel) |
| 3 | 킬스위치 (KillSwitchFAB, 확인 다이얼로그) |
| 4 | 원격 arm (ArmDialog, 비밀번호 재입력, brute-force 방지) |
| 5 | FCM 백엔드 (PushToken 모델, FirebaseService) |
| 6 | FCM 프론트 (usePushNotification, SW 백그라운드) |
| 7 | PWA (manifest.json, SW, 아이콘, 메타 태그) |
| 8 | 모바일 반응형 (flex-wrap, 카드 레이아웃, FAB) |
| 9 | 통합 테스트 |

### 수용 기준 (23개, 모두 미충족)
- 원격 상태 조회, 킬스위치, arm/재개, FCM 푸시, PWA, 모바일 UI

### 평가
- **Plan 완성도**: 높음 — 9단계 상세, 컴포넌트/훅 명확
- **리스크**: 높음 — relay-infra 완료 전 착수 불가, Firebase 프로젝트 설정 필요
- **부족한 점**: Firebase Service Account Key 확보 절차 미정

---

## 12. remote-control (원격 제어 — 상위 spec) — 참고

> 상태: 확정 | Plan: ✅ 있음 (12단계) | relay-infra + remote-ops의 상위 개념

- `relay-infra` (C6-a)와 `remote-ops` (C6-c)가 이 spec을 구체화한 하위 spec
- 외부 주문 감지 (reconciliation)는 remote-ops에 미포함 → 별도 구현 필요
- 2단계 확인 코드(30초 TTL) 방식은 remote-ops에서 비밀번호 방식으로 변경

---

## 종합 분석

### Plan 미작성 항목 — 2건
| Spec | 규모 | Plan 필요성 |
|------|------|-----------|
| chart-timeframe | 5-7일 | ⚠️ **필수** — 3계층 변경, 스테이지 정의만 있음 |
| watchlist-heart | 1-2일 | 낮음 — spec만으로 구현 가능한 규모 |

### 의존 체인 (구현 순서 제약)

```
[독립 그룹 — 병렬 가능]
├── frontend-quality (F1, F2, F3)
├── security-phase2 (S1→S2, S3, S4)
├── legal UI
├── kis-adapter-completion (K1, K2)
├── watchlist-heart
├── local-server-resilience (R1, R2, R4→R3)
└── dsl-client-parser (D1→D2→D3→D4)

[순차 그룹]
engine-live-execution (S2→S3→S5)
    ↑ IndicatorProvider가 chart-timeframe 분봉 데이터 활용 가능

[원격 제어 체인]
relay-infra (8단계) → remote-ops (9단계)
```

### 총 공수 추정

| 그룹 | 공수 |
|------|------|
| P0 (운영 필수) | 2-3주 |
| P1 (핵심 기능) | 3-4주 |
| P2 (확장 기능) | 5-7주 |
| **합계** | **10-14주** |
