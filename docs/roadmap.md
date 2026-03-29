# StockVision 로드맵

> 최종 갱신: 2026-03-29 (AI 코어 서비스 구현 완료, 테스트 174+)
> 역할: 개발 우선순위와 Phase 간 의존성을 요약하는 최상위 방향 문서.
> 상세 제품 방향: `docs/product/product-direction-log.md`

## 제품 정체성

> 자동매매 툴이 아니라 **사용자 특화 주식 비서 + 로컬 실행 엔진**.

- 핵심 가치: 종목 추천 < **개인화**, 완전 자동화 < **안전한 실행**, 일회성 챗봇 < **지속적 비서**
- 수익 모델: 무료 오픈소스 로컬 엔진 + 유료 클라우드 비서/동기화/운영

## 과거 이력

### Phase 1 — 기반 구축 (완료, 2024-12)

- 데이터 수집 (yfinance), 기술적 지표, RF 예측 모델
- 프론트엔드 기본 페이지, 캐싱/로깅 인프라

### Phase 2 — 가상 자동매매 (완료, 2025)

- 가상 거래 엔진, 스코어링 엔진, 백테스팅, 자동매매 스케줄러
- 키움증권 COM API 연동 (모의투자)

### Phase 3 — 3프로세스 아키텍처 전환 (2026-03)

- 아키텍처 전환 완료: 프론트엔드 + 클라우드 서버 + 로컬 서버
- 7 Unit 기본 구현 완료, 레거시(backend/, COM) 전체 삭제
- 세부 개선(UX, System Trader 등)은 Phase A 이후 사용자 가치 단위로 진행
- 당시 구현 계획: `docs/development-plan-v2.md` (Phase 3 시점 기준 참고용)

## 현재 방향

각 Phase는 **사용자가 체감하는 가치 단위**로 끊는다. 기술 레이어가 아니라 "이걸 끝내면 사용자가 뭘 느끼는가"가 기준.

```
A (쓸 수 있다) → B (보인다) → C (안심된다) → D (찾아온다) → E (나를 안다)
```

### Phase A — "켜면 바로 쓸 수 있다" (완료)

**목표**: 앱 켜면 계좌가 보이고, 상태가 읽히고, 뭘 할 수 있는지 안다.

| 항목 | spec | 상태 |
|------|------|------|
| broker-auto-connect (서버 시작 시 자동 연결) | `spec/broker-auto-connect/spec.md` | 구현 완료 |
| 프론트 UX v2 (신호등 이동, 전략 실행 버튼, 장 상태) | `spec/frontend-ux-v2/spec.md` | 구현 완료 |
| 전략 목록 정보 표시 (종목명, 방향, 실행 상태) | `spec/strategy-list-info/spec.md` | 구현 완료 |
| UI 버그 수정 (AuthContext 경쟁조건, useStockData 클로저 등) | `spec/phase-a-review.md` | 구현 완료 |

> `전략 목록 정보 표시`는 `frontend-ux-v2` 범위 밖 (spec §범위에 "전략 목록 UI 개선 (추후)" 명시). 별도 spec으로 분리.

**끝나면**: 서버 켜면 바로 잔고 보이고, 대시보드에서 전략 실행/중지 가능.

### Phase B — "돌아가는 게 보인다" (완료)

**목표**: 전략이 실행되고, 뭐가 체결되고, 왜 그런지 한 화면에서 읽힌다.

| 항목 | spec | 상태 |
|------|------|------|
| System Trader Phase 1 (candidate → 선택/차단 → intent) | `spec/system-trader/spec.md` | 구현 완료 |
| submitted/filled 분리 (주문 상태 정확화) | system-trader에 포함 | 구현 완료 |
| 규칙 카드 구조화 (조건/실행/리스크/결과 4블록) | `spec/rule-card-structured/spec.md` | 구현 완료 |
| 차트 타입 전환 (캔들/속빈/하이킨/OHLC/라인) | `spec/chart-type-switcher/spec.md` | 구현 완료 |
| 차트 이벤트 마커 (매수/매도/실패 표시) | `spec/chart-event-markers/spec.md` | 구현 완료 |

**끝나면**: 규칙 카드에서 조건/실행/결과가 읽히고, 차트에 매수/매도 마커가 표시된다. ✓

> `실행 로그 타임라인`(UX PRD 중요도 P2 · 출시 Phase 3)은 Phase B 범위 밖. Phase C에서 착수한다.

### Phase C — "안심이 된다"

**목표**: 안 보고 있어도 시스템이 안전하게 돌아간다는 확신.

**선행 조건**: 원격 권한 모델 확정 (`docs/product/remote-permission-model.md`)
- 채널별 권한 범위 (로컬 / 원격 앱 / 메신저 / 오프라인)
- 재개/무장(arm) 확인 규칙
- 원격 수동 실주문 초기 정책

#### 구현 항목

| # | 항목 | spec | 의존 | 상태 |
|---|------|------|------|------|
| C1 | 일일 P&L API + OpsPanel 표시 | `spec/ops-panel-v2/spec.md` | 없음 | 구현 완료 |
| C2 | 운영 패널 확장 (드롭다운, 상세 상태) | `spec/ops-panel-v2/spec.md` | C1 | 구현 완료 |
| C3 | 실행 로그 타임라인 (trigger→submit→fill/fail) | `spec/execution-log-timeline/spec.md` | System Trader (완료) | 구현 완료 |
| C4 | exe 패키징 (PyInstaller + 딥링크) | `spec/local-exe-deeplink/spec.md` | 없음 | 구현 완료 |
| C5 | 온보딩 신뢰 강화 (설치 피드백) | `spec/onboarding-v2/spec.md` | C4 | 구현 완료 |
| C6 | 원격 상태 조회 + 긴급 정지 (PWA + FCM) | `spec/remote-control/spec.md` | 권한 모델 | 미착수 |
| C7 | 엔진 재개/무장 (재개는 어렵게) | `spec/remote-control/spec.md` | C6 | 미착수 |
| C8 | 외부 주문 감지 + 경고 | `spec/remote-control/spec.md` | System Trader | 미착수 |

#### 구현 순서

```
Step 1 (독립, 병렬 가능)
  ├─ C1  일일 P&L API           ← Quick Win
  ├─ C3  실행 로그 타임라인      ← System Trader 완료됨
  └─ C4  exe 빌드 검증           ← spec/코드 완료, 빌드 테스트만

Step 2 (Step 1 결과 위에)
  ├─ C2  운영 패널 확장          ← C1 위에
  └─ C5  온보딩 신뢰 강화        ← C4 위에

Step 3 (권한 모델 기반, PWA + FCM)
  ├─ C6  원격 조회 + 긴급 정지   ← PWA + FCM 푸시
  └─ C7  엔진 재개/무장          ← C6 위에

Step 4
  └─ C8  외부 주문 감지          ← 독립
```

#### 채널 결정 (2026-03-12)

- **주 채널**: PWA (기존 React SPA + 반응형 + Service Worker)
- **알림**: 웹 푸시 (FCM) — Android 완벽, iOS 16.4+ 지원
- **메신저 (텔레그램)**: 당장은 안 함. iOS 푸시 불만 시 보조 채널로 검토
- **네이티브 앱**: 과도. 사용자 규모 커지면 검토

> 원칙: `조회는 넓게 / 실행은 좁게`, `정지는 쉽게 / 재개는 어렵게`, `원격 수동 실주문은 초기 금지`.
> 상세 권한 표: `docs/product/remote-permission-model.md` §5.
> 벤치마크: `docs/research/phase-c-dashboard-benchmark.md` §7.

**끝나면**: 밖에서 폰으로 상태 확인 + 긴급 정지 가능. 재개는 추가 확인을 거쳐야만 가능.

### 테스트 및 안정성 현황 (2026-03-29)

| 레이어 | 테스트 수 | 비고 |
|--------|----------|------|
| cloud_server | 79 | WS relay 8, scheduler 3, backtest 9 포함 |
| local_server | 213 | 브로커 + 엔진 + 라우터 + 분봉 지표 + **엔진 v2 30 + PositionState 11 + 링버퍼 4 + Tracker 6 + 시간 2** |
| sv_core (DSL + indicators) | 174 | 파서/평가기/렉서 + 지표 + **v2 파서 44 + v2 평가기 21 + 신규 함수/다이버전스 16 + 스키마 6** |
| frontend Vitest | 53 | dslParser 26 + dslConverter 8 + e2eCrypto 8 + **dslParserV2 11** |
| frontend Playwright | 24 | auth 4, admin 2, onboarding 1, strategy 2, backtest 2, Builder E2E 5, **v2 E2E 8** |
| **합계** | **521** | (2개 flaky backtest 간헐 실패 — 기존 이슈) |

**risk-mitigation 완료 (2026-03-26)**: `spec/risk-mitigation/`
- WS relay kill-switch 경로 테스트, APScheduler catch-up, Playwright E2E 기반 구축

**Phase E 구현 (2026-03-28)**: `spec/` 하위 6개 spec
- 분봉 수집 파이프라인 (키움 배치 + 로컬→클라우드 sync)
- 백테스트 엔진 + API + UI (멀티 타임프레임, 수수료/세금/슬리피지)
- DSL 타임프레임 확장 `RSI(14, "5m")`
- 라이브 엔진 분봉 IndicatorProvider
- 전략 수명주기 (Builder→백테스트→결과 DB→RuleCard 요약)
- e2eCrypto 유닛 + StrategyBuilder E2E

### Phase D — "먼저 찾아온다"

**목표**: 내가 안 열어도 비서가 먼저 챙긴다.

| # | 항목 | spec | 의존 | LLM | 상태 |
|---|------|------|------|-----|------|
| D1 | 장중 실시간 경고 (9종 규칙 기반) | `spec/realtime-alerts/spec.md` | 엔진 | 불필요 | 구현 완료 |
| D2 | 시장 브리핑 (1회/일, 시황 요약) | `spec/market-briefing/spec.md` | 클라우드 AI | 운영자 (캐싱) | 구현 완료 |
| D3 | 종목별 분석 (1회/일, 기술적 지표 요약) | `spec/stock-analysis/spec.md` | 클라우드 AI | 운영자 (캐싱) | 구현 완료 |
| D4 | 텔레그램 알림 연동 | 미작성 | 권한 모델 | - | 미착수 |

> D1은 LLM 불필요 (룰 기반). D2/D3는 운영자 Claude API + 캐싱. 개인화 분석(포트폴리오 기반 브리핑, 장마감 복기)은 Phase E(사용자 BYO LLM).

**끝나면**: 장중에 손실/급변동/미체결 경고가 실시간으로 오고, 매일 아침 시장 브리핑이 온다.

### Phase E — "나를 안다" ← 현재

**목표**: 투자 성향, 원칙, 과거 기록을 바탕으로 개인화.

| 항목 | 의존 | 상태 |
|------|------|------|
| 분봉 수집 파이프라인 | 키움 REST API | 구현 완료 (수집은 수동) |
| 백테스트 엔진 (멀티 TF, 비용 시뮬) | 분봉/일봉 데이터 | 구현 완료 |
| DSL 타임프레임 확장 | sv_core 파서 | 구현 완료 |
| 전략 수명주기 (Builder→백테스트→결과→RuleCard) | 백테스트 | 구현 완료 |
| 라이브 분봉 IndicatorProvider | 분봉 수집 | 구현 완료 |
| 전략 엔진 v2 (DSL+엔진+상태API+카드UI+프리셋) | - | 구현 완료 (2026-03-29) |
| DSL 함수 ���장 + 프리셋 8개 + 전략 상태 요약 | - | 구현 완료 (2026-03-29) |
| DSL 스키마 API + 자동��성 + dsl_meta + validators v2 | - | 구현 완료 (2026-03-29) |
| AI 코어 서비스 (코파일럿+비서+크레딧+대화패널+버전) | Claude API | 구현 완료 (2026-03-29) |
| DSL 에디터 구문 하이라이팅 (CodeMirror 6) | - | 미착수 (별도 이슈) |
| 사용자 프로필/메모리 ��델 | - | 미착수 |
| 기본 복구/최근 이력 | 무��� 범위 | 미착수 |
| 장기 보관/다기기 연속성 | Pro 과금 핵심 | 미착수 |

> 무료: 로컬 메모리, 최근 30일 이력/롤백, 기기 교체 복구 기본, 전략 import/export.
> Pro: 장기 이력·장기 메모리·장기 복구, 다기기 연속성, 원격 비서 맥락 이어짐.
> Pro의 가치는 `단순 저장`이 아니라 `연속성`, `운영 편의`, `장기 보관`에 있다.
> 상세: `docs/product/free-pro-boundary.md`

**끝나면**: "이 사용자는 보수적, -1.5% 손절, 반도체 선호" 맥락으로 비서가 움직인다.

## 레포 분리 + 오픈소스 공개

Phase A~E는 **기능** 마일스톤이고, 레포 분리는 **인프라** 마일스톤이다. 둘은 병렬로 진행 가능하지만, 의존성이 있다.

```
현재 (모노레포)
  │
  ├─ Phase C 기능 개발 (계속)
  │
  ├─ M1: 프론트엔드 경계 리팩터링 ← Phase C와 병렬
  │     ├─ AuthContext → cloud auth / local bridge sync 분리
  │     ├─ App.tsx → local / web / admin 앱 쉘 분리
  │     ├─ StrategyBuilder → cloud 저장 / local 배포 분리
  │     └─ TrafficLightStatus → local / cloud 위젯 분리
  │
  ├─ M2: sv_core 독립 패키지화
  │     ├─ pyproject.toml + 패키지 메타
  │     ├─ 인터페이스 동결 (BrokerAdapter, DSL, Indicator)
  │     └─ local_server/cloud_server가 sv_core를 의존성으로 import
  │
  ├─ M3: 레포 분리 실행
  │     ├─ stockvision-core (공개) ← sv_core/
  │     ├─ stockvision-local (공개) ← local_server/ + 로컬 프론트
  │     ├─ stockvision-cloud (비공개) ← cloud_server/
  │     └─ stockvision-internal-docs (비공개) ← docs/research, spec, docs/product
  │
  ├─ M4: 오픈소스 공개 준비
  │     ├─ 공개 repo에 비밀정보 없음 확인
  │     ├─ 제3자 라이선스 점검 (OSS 의존성)
  │     ├─ MPL-2.0 소스 고지 반영
  │     ├─ README, LICENSE, CONTRIBUTING, SECURITY 배치
  │     ├─ 코드 서명 (SignPath.io)
  │     └─ 인스톨러 (MSI/NSIS) + 자동 업데이트
  │
  └─ M5: 공개 릴리스 (v1.0)
        ├─ stockvision-core + stockvision-local GitHub 공개
        ├─ 인스톨러 배포 (GitHub Releases)
        └─ 랜딩 페이지 / 문서 사이트
```

### 의존성 정리

| 마일스톤 | 선행 조건 | Phase 연관 |
|---------|----------|-----------|
| M1 (프론트 리팩터링) | 없음 — 지금 시작 가능 | Phase C와 병렬 |
| M2 (sv_core 독립) | sv_core 인터페이스 안정화 | Phase C 기능 추가가 끝나야 안정 |
| M3 (레포 분리) | M1 + M2 | Phase D 이전 권장 |
| M4 (공개 준비) | M3 | Phase D 이전 |
| M5 (공개 릴리스) | M4 + Phase C 완료 | Phase D부터는 분리된 레포에서 개발 |

### 현실적 순서

**지금 (Phase C 진행 중):**
- Phase C 기능 개발 (원격 권한, 운영 패널, 실행 로그)
- M1 병렬 착수 (프론트 경계 리팩터링) — 기능 개발하면서 분리 가능한 것부터

**Phase C 후반:**
- M2 (sv_core 독립) — Phase C 기능 추가로 인터페이스 변동이 줄었을 때
- PyInstaller exe 빌드 검증

**Phase C 완료 후 ~ Phase D 진입 전:**
- M3 (레포 분리 실행)
- M4 (오픈소스 공개 준비)
- M5 (공개 릴리스) → **Phase D부터는 분리된 레포에서 개발**

### 프론트엔드 분리 상세 (M1)

현재 `frontend/`는 local/cloud/admin이 한 앱에 섞여 있다. 레포 분리 전에 논리적 경계를 만들어야 한다.

| 혼합 파일 | 조치 |
|----------|------|
| `App.tsx` | local/web/admin 라우트를 앱 쉘로 분리 |
| `AuthContext.tsx` | cloud auth + local bridge sync 분리 |
| `StrategyBuilder.tsx` | cloud CRUD + local deploy 분리 |
| `StrategyList.tsx` | cloud list + local sync 분리 |
| `TrafficLightStatus.tsx` | local/cloud/broker 상태 위젯 분리 |
| `Header.tsx` | local 제어 + cloud 검색 분리 |

목표: 파일 이동 없이도 "이 파일은 local, 이 파일은 cloud" 구분 가능한 상태.

### 관련 문서

| 문서 | 역할 |
|------|------|
| `docs/open-source/repo-split-plan.md` | 레포 분리 전략 상세 |
| `docs/open-source/repo-mapping-table.md` | 파일별 대상 레포 매핑 |
| `docs/open-source/OPEN_SOURCE_SCOPE.md` | 공개/비공개 범위 정의 |
| `docs/open-source/oss-license-strategy.md` | 라이선스 전략 (MPL-2.0) |
| `spec/phase-b-backlog.md` | 인스톨러, 클라우드 릴레이 등 미결 항목 |

## 참고 문서

| 문서 | 역할 |
|------|------|
| `docs/architecture.md` | 현재 시스템 구조 |
| `docs/development-plan-v2.md` | Phase 3 시점 구현 계획 (7 Unit, 참고용) |
| `docs/development-plan-v3.md` | 기술 구현 백로그 (T1/T2/T3 — 이 로드맵의 Phase와 별도 축) |
| `docs/product/product-direction-log.md` | 제품 방향 의사결정 로그 |
| `docs/product/frontend-ux-priority-prd-2026-03-10.md` | 프론트 UX 개편 우선순위 (P1/P2=중요도, Phase 1/2/3=출시순서) |
| `docs/product/remote-permission-model.md` | 원격 권한 모델 (채널별 권한 표) |
| `spec/system-trader/spec.md` | System Trader 설계 명세 |
| `spec/broker-auto-connect/spec.md` | 브로커 자동 연결 명세 |
| `spec/frontend-ux-v2/spec.md` | 프론트 UX 개선 v2 명세 |
