# StockVision 개발 계획서 v2

> 작성일: 2026-03-05 | 아키텍처: `docs/architecture.md` 기준 (3프로세스)
>
> Phase 1-2 (가상 거래, ML 예측)는 완료. 이 문서는 Phase 3 이후 계획.

---

## 개발 단위 (Spec 단위)

아키텍처 문서의 3 프로세스를 기준으로 개발 단위를 나눈다.
각 단위마다 `spec/{name}/spec.md` 생성 후 구현.

---

### Unit 1: 키움 REST API 연동

**범위**: 키움 REST API 클라이언트 (로컬 서버 내부 모듈)

- OAuth 토큰 발급/갱신 (App Key/Secret → Bearer Token 24h)
- 주문 실행 (시장가/지정가)
- 현재가 조회 (가격 검증용)
- 실시간 시세 수신 (WebSocket)
- API 호출 제한 관리 (초당 5건, 큐)
- 모의투자/실거래 모드 전환

**의존**: 없음 (독립 모듈)
**산출**: `local_server/kiwoom/` 전체 재작성 (COM → REST)
**spec**: `spec/kiwoom-rest/spec.md`

---

### Unit 2: 로컬 서버 코어

**범위**: 로컬 서버 기반 구조

- FastAPI 서버 (localhost:8765)
- 시스템 트레이 아이콘 (pystray, 더블클릭 → 대시보드, 우클릭 → 메뉴)
- 트레이 아이콘 색상 (🟢🟡🔴 전체 상태)
- API Key + Refresh Token 저장 (Windows Credential Manager / keyring)
- 전략 규칙 캐시 (평문 JSON 파일)
- 설정 파일 (config.json)
- 체결 로그 DB (SQLite, logs.db)
- 클라우드 서버 직접 통신 (컨텍스트/하트비트/템플릿/WS 알림)
- 자동 로그인 (Refresh Token으로 PC 재부팅 후 복구)
- PyInstaller .exe 번들

**의존**: 없음
**산출**: `local_server/` 기반 구조
**spec**: `spec/local-server-core/spec.md`

---

### Unit 3: 전략 엔진

**범위**: 규칙 평가 → 신호 생성 → 주문 요청

- 스케줄러 (장 시간 1분 주기)
- 규칙 평가 (조건 + 컨텍스트 + 시세 → True/False)
- 신호 관리 (NEW → SENT → FILLED, 중복 방지)
- 주문 전 가격 검증 (키움 REST 직접 조회 vs 수신 시세 비교)
- 컨텍스트 캐시 (로컬 서버가 클라우드 서버에서 직접 fetch)
- 규칙 캐시 (프론트 sync 또는 WS push, JSON 파일에서 로드)

**의존**: Unit 1 (키움 REST), Unit 2 (로컬 서버 코어)
**산출**: `local_server/engine/` 재작성
**spec**: `spec/strategy-engine/spec.md`

---

### Unit 4: 클라우드 서버

**범위**: 인증 + 규칙 + 시세 수집 + AI 분석 + 어드민 (단일 서버)

- 사용자 인증 (회원가입, 이메일 인증, 로그인, JWT + Refresh Token)
- 전략 규칙 CRUD (DB 저장, 조회, 수정, 삭제)
- 서비스 키움 키로 시세 수집/저장 (WS, 히스토리컬)
- AI 컨텍스트 계산 (시세 기반 지표)
- AI 분석 (Claude API → 감성 점수, 뉴스 요약)
- 하트비트 수신 (익명 통계)
- 버전 체크 API
- 어드민 API (유저, 통계, 키, 템플릿, 수집 상태)

**의존**: Unit 1의 키움 REST 클라이언트 (sv_core 패키지로 재사용)
**산출**: `cloud_server/` (기존 `backend/` 코드 리팩토링)
**spec**: `spec/cloud-server/spec.md`

> 기존 `spec/api-server/` + `spec/data-server/` 병합.
> Phase 1-2의 auth, stocks, ai_analysis 코드를 정리/확장.

---

### Unit 5: 프론트엔드

**범위**: React SPA 전체

- 인증 (로그인/회원가입)
- 대시보드 (실시간 시세, 체결 알림, 신호등)
- 전략 빌더 (규칙 생성/수정/삭제)
- 실행 로그 뷰어
- 설정 (키움 API Key 등록 → localhost)
- localhost WS (실시간 시세 + 체결)
- JWT 전달 (로그인 후 → localhost) + 규칙 sync (저장 후 → localhost)

**의존**: Unit 2 (localhost API), Unit 4 (클라우드 서버)
**산출**: `frontend/src/` 업데이트
**spec**: `spec/frontend/spec.md`

> 기존 spec (strategy-builder, user-dashboard, notification, onboarding 등)과 병합.

---

### Unit 6: 어드민 페이지

**범위**: 관리자 UI

- 유저 목록/관리
- 접속 통계 (하트비트 기반)
- 시세 데이터 모니터링 (수집 상태)
- 서비스 키움 키 관리
- 전략 템플릿 관리 (디폴트 양식)

**의존**: Unit 4 (클라우드 서버)
**산출**: `frontend/src/pages/admin/` 업데이트
**spec**: `spec/admin/spec.md`

---

### Unit 7: 약관/법무

**범위**: 서비스 약관 작성

- 이용약관 (시스템매매 도구, 투자 면책, 커뮤니티 데이터 활용)
- 개인정보처리방침 (최소 수집, 로컬 데이터 비수집 명시)
- 키움 약관 준수 확인서 (내부 문서)

**의존**: 아키텍처 확정 후
**산출**: `docs/legal/` 또는 프론트엔드 페이지
**spec**: `spec/legal/spec.md`

---

## 개발 순서

### Phase 3-A: 기반 (병렬 가능)

```
Unit 1: 키움 REST API ──┐
Unit 2: 로컬 서버 코어 ──┼──→ Unit 3: 전략 엔진
Unit 4: 클라우드 서버 ───┘
```

- Unit 1, 2는 독립적 → 병렬 개발 가능
- Unit 4는 Unit 1의 sv_core 패키지 재사용 (시세 수집) → Unit 1 이후 또는 병렬
- Unit 3은 1+2 완료 후

### Phase 3-B: 연결

```
Unit 5: 프론트엔드 (Unit 2 + Unit 4 필요)
Unit 7: 약관
```

- Unit 5는 localhost + 클라우드 서버 둘 다 필요

### Phase 3-C: 마무리

```
Unit 6: 어드민 (Unit 4 필요)
통합 테스트
모의투자 E2E 테스트
```

---

## 의존성 다이어그램

```
Unit 1 (키움 REST) ─────────┐
                             ├──→ Unit 3 (전략 엔진)
Unit 2 (로컬 서버 코어) ─────┤
                             └──→ Unit 5 (프론트엔드)
Unit 4 (클라우드 서버) ─────────→ Unit 5 (프론트엔드)
                             └──→ Unit 6 (어드민)

Unit 7 (약관) ── 독립 (아키텍처 확정 후 언제든)
```

---

## 기존 spec 매핑

| 기존 spec | → 새 Unit | 처리 |
|-----------|----------|------|
| `spec/kiwoom-integration/` | Unit 1 | v3 재작성 (REST API) |
| `spec/local-bridge/` | Unit 2 | 업데이트 |
| `spec/execution-engine/` | Unit 3 | 업데이트 |
| `spec/api-server/` | Unit 4 (클라우드 서버) | **SUPERSEDED** — cloud-server에 병합 |
| `spec/data-server/` | Unit 4 (클라우드 서버) | **SUPERSEDED** — cloud-server에 병합 |
| `spec/auth/` | Unit 4에 포함 | 병합 |
| `spec/context-cloud/` | Unit 4에 포함 | 병합 |
| `spec/data-source/` | Unit 4 참고 | 참고 |
| `spec/strategy-builder/` | Unit 5에 포함 | 병합 |
| `spec/user-dashboard/` | Unit 5에 포함 | 병합 |
| `spec/notification/` | Unit 5에 포함 | 병합 |
| `spec/onboarding/` | Unit 5에 포함 | 병합 |
| `spec/portfolio/` | Unit 5에 포함 | 병합 |
| `spec/execution-log/` | Unit 5에 포함 | 병합 |
| `spec/strategy-template/` | Unit 6에 포함 | 병합 |
| `spec/admin-dashboard/` | Unit 6에 포함 | 병합 |
| `spec/koscom-integration/` | 미래 (v3+) | 보류 유지 |

---

## 미래 Unit (v2+)

| Unit | 버전 | 내용 |
|------|------|------|
| 자동 업데이트 | v2 | 로컬 서버 .exe 자동 업데이트 |
| 백테스팅 | v2 | 클라우드 서버 히스토리 활용 |
| 커뮤니티 | v2-3 | 전략 공유, 수익 인증, 포크 |
| 코스콤 연동 | v3+ | 정식 시세 라이선스 |
| 크로스 플랫폼 | v3+ | Mac/Linux 지원 |

> LLM 서버는 별도 Unit 불필요 — Claude API(HTTP 호출)로 클라우드 서버 내 ai_analysis 모듈에서 처리.
