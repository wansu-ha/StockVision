# StockVision 저장소 매핑 표 초안

이 문서는 현재 워크스페이스를 기준으로 각 폴더와 파일을 어느 저장소로 보낼지 정리한 초안입니다.
전제는 다음과 같습니다.

- `backend/`는 이미 제거되었고 더 이상 대상이 아니다.
- 공개 저장소는 최소한으로 유지한다.
- 내부 의사결정, 리서치, 운영 자료는 공개하지 않는다.
- `frontend`는 바로 이동하지 않고 일부는 먼저 분리 리팩터링이 필요하다.

## 대상 저장소 정의

- `stockvision-core` — 공개, 공유 코어
- `stockvision-local` — 공개, 로컬 엔진 + 로컬 UI
- `stockvision-cloud` — 비공개, 클라우드 백엔드 + 운영 코드
- `stockvision-admin` — 비공개, 관리자 프런트엔드
- `stockvision-web` — 비공개 후보, 일반 사용자용 클라우드 웹앱
- `stockvision-internal-docs` — 비공개, 내부 문서/리서치/spec/기획
- `local-only` — 어떤 저장소에도 올리지 않음
- `refactor-first` — 먼저 코드 경계 정리 후 이동

## 최상위 매핑

| 현재 경로 | 대상 | 공개 여부 | 메모 |
|---|---|---:|---|
| `sv_core/` | `stockvision-core` | 공개 | 가장 먼저 분리할 공유 코어 |
| `local_server/` | `stockvision-local` | 공개 | 오픈소스 엔진 본체 |
| `cloud_server/` | `stockvision-cloud` | 비공개 | 인증, 동기화, AI, 수집, admin API 포함 |
| `frontend/` | `refactor-first` | 혼합 | local/cloud/admin이 섞여 있어 바로 이동 금지 |
| `docs/product/` | `stockvision-internal-docs` | 비공개 | 제품 방향, 가격, 권한 모델, 내부 정의 |
| `docs/positioning/` | `stockvision-internal-docs` | 비공개 | 포지셔닝 문서 |
| `docs/research/` | `stockvision-internal-docs` | 비공개 | 리서치, 보안 감사, 리뷰 문서 |
| `spec/` | `stockvision-internal-docs` | 비공개 | 내부 spec/plan/reports |
| `docs/legal/` | 분리 필요 | 혼합 | 사용자 공개용과 내부 준수 문서가 섞여 있음 |
| `docs/open-source/` | 분산 이관 | 혼합 | 최종적으로 각 공개 저장소 루트 문서로 이동 |
| `scripts/` | `stockvision-cloud` 또는 `stockvision-internal-docs` | 비공개 | 현재는 일회성 마이그레이션 성격 |
| `tests/` | 검토 후 분리 | 혼합 | 일부는 공개 가능, 일부는 브로커/실환경 의존 |
| `prototypes/` | `stockvision-internal-docs` 또는 별도 `labs` | 비공개 | 실험 산출물 |
| `changeLog/` | `stockvision-internal-docs` | 비공개 | 내부 작업 로그 성격 |
| `.env` | `local-only` | 비공개 | 절대 커밋 금지 |
| `.venv/` | `local-only` | 비공개 | 로컬 환경 |
| `.pytest_cache/`, `.tmp/`, `.playwright-mcp/` | `local-only` | 비공개 | 임시/캐시 |
| `cloud_server.db` | `local-only` | 비공개 | 개발 DB, 커밋 금지 |
| `docker-compose.yml` | `stockvision-cloud` | 비공개 | 운영/개발 compose |
| `alembic.ini` | `stockvision-cloud` | 비공개 | 클라우드 DB 마이그레이션 |
| `README.md` | 추후 분리 | 혼합 | 현재 monorepo 기준이라 각 저장소용으로 재작성 필요 |
| `CLAUDE.md` | `local-only` | 비공개 | 작업 보조 문서 |

## frontend 세부 매핑

### 바로 `stockvision-admin`으로 이동 가능한 것

| 현재 경로 | 대상 | 메모 |
|---|---|---|
| `frontend/src/pages/Admin/*` | `stockvision-admin` | admin 전용 화면 |
| `frontend/src/services/admin.ts` | `stockvision-admin` | admin API 클라이언트 |
| `frontend/src/components/AdminGuard.tsx` | `stockvision-admin` | admin 권한 가드 |
| `admin-dashboard.png` | `stockvision-admin` 또는 internal docs | admin 스크린샷 자산 |
| `admin-dashboard-live.png` | `stockvision-admin` 또는 internal docs | admin 스크린샷 자산 |
| `admin-users-live.png` | `stockvision-admin` 또는 internal docs | admin 스크린샷 자산 |

### `stockvision-local` 후보

| 현재 경로 | 대상 | 메모 |
|---|---|---|
| `frontend/src/services/localClient.ts` | `stockvision-local` | 로컬 API 클라이언트 |
| `frontend/src/hooks/useLocalBridgeWS.ts` | `stockvision-local` | localhost WS 의존 |
| `frontend/src/hooks/useAccountStatus.ts` | `stockvision-local` | 로컬 상태 조회 |
| `frontend/src/hooks/useAccountBalance.ts` | `stockvision-local` | 로컬 계좌 정보 조회 |
| `frontend/src/pages/MainDashboard.tsx` | `stockvision-local` 후보 | 로컬 대시보드 성격 강함 |
| `frontend/src/pages/Settings.tsx` | `stockvision-local` 후보 | 로컬 설정/엔진 제어 성격 강함 |
| `frontend/src/pages/ExecutionLog.tsx` | `stockvision-local` 후보 | 로컬 실행 로그 중심 |
| `frontend/src/components/BridgeInstaller.tsx` | `stockvision-local` | 로컬 브리지 설치 가이드 |

### `stockvision-web` 후보

| 현재 경로 | 대상 | 메모 |
|---|---|---|
| `frontend/src/services/cloudClient.ts` | `stockvision-web` | 사용자용 클라우드 API 클라이언트 |
| `frontend/src/pages/Login.tsx` | `stockvision-web` | 클라우드 인증 |
| `frontend/src/pages/Register.tsx` | `stockvision-web` | 클라우드 인증 |
| `frontend/src/pages/ForgotPassword.tsx` | `stockvision-web` | 클라우드 인증 |
| `frontend/src/pages/ResetPassword.tsx` | `stockvision-web` | 클라우드 인증 |
| `frontend/src/pages/StockList.tsx` | `stockvision-web` | 종목/관심종목 중심 |
| `frontend/src/components/StockSearch.tsx` | `stockvision-web` 후보 | 클라우드 종목 검색 |
| `frontend/src/components/MarketContext.tsx` | `stockvision-web` | 클라우드 컨텍스트 |

### 먼저 리팩터링해야 하는 혼합 파일

| 현재 경로 | 현재 문제 | 권장 조치 |
|---|---|---|
| `frontend/src/context/AuthContext.tsx` | cloud login + local token sync를 한 컨텍스트에서 처리 | cloud auth와 local bridge sync 분리 |
| `frontend/src/pages/StrategyBuilder.tsx` | cloud CRUD 후 local sync 수행 | `cloud strategy editor`와 `local deploy` 분리 |
| `frontend/src/pages/StrategyList.tsx` | cloud list + local sync가 같은 화면에 있음 | 저장/배포 단계를 분리 |
| `frontend/src/components/TrafficLightStatus.tsx` | cloud/local/broker 상태를 한 컴포넌트에서 폴링 | local status widget과 cloud health widget 분리 |
| `frontend/src/components/main/Header.tsx` | local engine 제어 + cloud stock search 동시 포함 | local header와 web header 역할 분리 |
| `frontend/src/App.tsx` | 사용자 앱과 admin, local/cloud 라우트가 한 앱에 섞여 있음 | app shell을 local/web/admin으로 나누기 |

## docs 세부 매핑

### 내부 docs로 가야 하는 것

| 현재 경로 | 대상 | 메모 |
|---|---|---|
| `docs/product/*` | `stockvision-internal-docs` | 제품 전략, 가격, 내부 정의 |
| `docs/positioning/*` | `stockvision-internal-docs` | 시장 포지셔닝 |
| `docs/research/*` | `stockvision-internal-docs` | 리서치, 벤치마크, 보안 감사 |
| `spec/*` | `stockvision-internal-docs` | 구현 spec, plan, report |
| `docs/architecture.md` | `stockvision-internal-docs` 초안 | 외부 공개용으로 재작성 전까지 비공개 |
| `docs/development-plan*.md` | `stockvision-internal-docs` | 내부 개발 계획 |
| `docs/roadmap.md` | `stockvision-internal-docs` | 내부 우선순위 |
| `docs/project-blueprint.md` | `stockvision-internal-docs` | 내부 청사진 |

### 사용자 공개용으로 살릴 수 있는 것

| 현재 경로 | 대상 | 메모 |
|---|---|---|
| `docs/legal/terms-of-service.md` | `stockvision-cloud` | 사용자 공개 법률 문서 |
| `docs/legal/privacy-policy.md` | `stockvision-cloud` | 사용자 공개 법률 문서 |
| `docs/legal/disclaimer.md` | `stockvision-cloud` | 사용자 공개 면책 문서 |

### 내부에 남겨야 하는 legal 문서

| 현재 경로 | 대상 | 메모 |
|---|---|---|
| `docs/legal/broker-compliance.md` | `stockvision-internal-docs` | 내부 준수 문서 |
| `docs/legal/README.md` | `stockvision-internal-docs` 또는 cloud repo 보조 문서 | 내용 검토 후 결정 |
| `docs/legal.md` | `stockvision-internal-docs` | 엔지니어링 법적 검토 메모 |

### open-source 문서의 최종 귀속

| 현재 경로 | 최종 대상 | 메모 |
|---|---|---|
| `docs/open-source/LICENSE` | 각 공개 저장소 루트 `LICENSE` | 공개 저장소마다 맞게 배치 |
| `docs/open-source/README-license-section.md` | 각 공개 저장소 `README.md` | 저장소별 문구로 재작성 |
| `docs/open-source/OPEN_SOURCE_SCOPE.md` | `stockvision-local` 또는 공개 루트 | 공개 범위 문서 |
| `docs/open-source/TRADEMARKS.md` | 공개 저장소 루트 또는 공식 웹 | 상표 정책 |
| `docs/open-source/SECURITY.md` | 공개 저장소 루트 | 보안 정책 |
| `docs/open-source/SUPPORT.md` | 공개 저장소 루트 | 지원 정책 |
| `docs/open-source/CONTRIBUTING.md` | 공개 저장소 루트 | 기여 가이드 |
| `docs/open-source/solo-maintainer-rules.md` | `stockvision-internal-docs` 또는 maintainer docs | 운영 원칙 내부 참고 |
| `docs/open-source/repo-split-plan.md` | `stockvision-internal-docs` | 내부 분리 계획 |
| `docs/open-source/oss-license-strategy.md` | `stockvision-internal-docs` | 내부 라이선스 전략 메모 |

## tests 세부 매핑

| 현재 경로 | 대상 | 메모 |
|---|---|---|
| `local_server/tests/` | `stockvision-local` | 공개 가능 테스트 위주 |
| `cloud_server/tests/` | `stockvision-cloud` | 비공개 서비스 테스트 |
| `tests/test_legacy_removal.py` | `stockvision-internal-docs` 또는 archive | 과도기성 테스트 |
| `tests/test_kiwoom_live.py` | private integration tests | 실브로커/실환경 의존 가능성 높음 |
| `tests/test_kiwoom_broker.py` | `stockvision-local` 검토 후 이동 | 민감정보/실환경 의존 여부 확인 필요 |

## 분리 순서 제안

1. `sv_core/` -> `stockvision-core`
2. `local_server/` + local UI 최소셋 -> `stockvision-local`
3. `cloud_server/` -> `stockvision-cloud`
4. `docs/product`, `docs/positioning`, `docs/research`, `spec` -> `stockvision-internal-docs`
5. `frontend/src/pages/Admin/*` 등 admin 프런트 -> `stockvision-admin`
6. `frontend` 나머지는 local/web 경계 재설계 후 분리

## 한 줄 결론

가장 먼저 움직일 것은 `sv_core`, `local_server`, `cloud_server`, `internal docs`이고,
가장 마지막에 움직일 것은 혼합도가 높은 `frontend` 본체입니다.
