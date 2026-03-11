# StockVision 1단계 실제 이동 체크리스트

이 문서는 StockVision 모노레포를 여러 저장소로 분리할 때,
가장 먼저 실행할 1단계 작업을 실제 행동 기준으로 정리한 체크리스트입니다.

이 단계의 목표는 두 가지입니다.

1. 내부 문서와 공개 후보 코드를 섞어 두지 않게 경계를 세운다.
2. `sv_core`를 첫 번째 독립 저장소로 분리할 준비를 끝낸다.

## 1단계의 완료 기준

이 단계가 끝났다고 볼 수 있는 조건은 아래와 같습니다.

- GitHub Organization과 기본 저장소가 준비되어 있다.
- 내부 문서의 최종 귀속이 정리되어 있다.
- `sv_core`가 독립 패키지로 나갈 수 있는 구조인지 점검이 끝나 있다.
- `local_server`와 `cloud_server`가 `sv_core`를 공유 코어로만 사용한다는 규칙이 확정되어 있다.
- `frontend`는 아직 이동하지 않되, 혼합 파일 목록이 고정되어 있다.

## 1단계에서 실제로 움직일 대상

이번 단계에서 실제 이동 대상으로 보는 것은 아래 2개입니다.

- `stockvision-internal-docs`
- `stockvision-core`

이번 단계에서 아직 이동하지 않는 것은 아래입니다.

- `local_server/`
- `cloud_server/`
- `frontend/`
- admin 프런트 전체

이유는 간단합니다.
`sv_core`는 가장 작고 공유성이 높아서 먼저 분리하기 좋고,
내부 문서는 먼저 격리할수록 공개 사고를 줄일 수 있기 때문입니다.

## 체크리스트

### A. GitHub Organization 준비

- [ ] GitHub Organization을 하나 만든다.
- [ ] Organization 이름은 `stockvision` 계열로 정한다.
- [ ] 아래 5개 저장소를 비어 있는 상태로 생성한다.
  - `stockvision-core`
  - `stockvision-local`
  - `stockvision-cloud`
  - `stockvision-admin`
  - `stockvision-internal-docs`
- [ ] `stockvision-core`, `stockvision-local`은 공개로 둔다.
- [ ] `stockvision-cloud`, `stockvision-admin`, `stockvision-internal-docs`는 비공개로 둔다.
- [ ] 기본 브랜치를 모두 `main`으로 통일한다.

### B. 모노레포 동결 규칙 선언

- [ ] `sv_core` 밖의 공유 코드를 새로 만들지 않는다.
- [ ] `local_server`에서 `cloud_server`를 직접 import하지 않는다.
- [ ] `cloud_server`에서 `local_server`를 직접 import하지 않는다.
- [ ] `frontend`의 혼합 파일에는 분리 목적이 아닌 신규 결합 로직을 추가하지 않는다.
- [ ] 내부 의사결정 문서를 공개 후보 폴더에 새로 만들지 않는다.

### C. 내부 문서 먼저 격리

아래 경로는 우선 `stockvision-internal-docs`로 갈 대상으로 확정합니다.

- [ ] `docs/product/`
- [ ] `docs/positioning/`
- [ ] `docs/research/`
- [ ] `spec/`
- [ ] `docs/legal.md`
- [ ] `docs/legal/broker-compliance.md`
- [ ] `docs/open-source/repo-split-plan.md`
- [ ] `docs/open-source/oss-license-strategy.md`
- [ ] `docs/open-source/solo-maintainer-rules.md`

이 단계에서 할 일:

- [ ] 각 문서가 공개 대상인지 내부 대상인지 1회 재확인한다.
- [ ] 내부 문서는 새 저장소로 옮길 목록을 확정한다.
- [ ] 공개 저장소 루트에 둘 문서와 내부 저장소에 둘 문서를 분리 메모로 남긴다.

## D. `sv_core` 분리 준비

아래 항목은 `stockvision-core`로 옮기기 전에 꼭 확인합니다.

- [ ] `sv_core`가 `local_server`, `cloud_server`, `frontend`를 참조하지 않는지 확인한다.
- [ ] `sv_core` 내부에서 로컬/클라우드 전용 코드가 섞여 있지 않은지 확인한다.
- [ ] `sv_core` 테스트가 독립 실행 가능한지 확인한다.
- [ ] `sv_core`용 최소 패키징 파일 목록을 정한다.
  - `pyproject.toml`
  - `README.md`
  - `LICENSE`
- [ ] 패키지 이름과 버전 규칙을 정한다.
- [ ] `stockvision-core`의 첫 릴리스 태그를 `v0.1.0` 같은 초기 버전으로 정한다.

### `sv_core` 이동 대상 최소셋

- [ ] `sv_core/`
- [ ] `sv_core` 관련 테스트
- [ ] 패키징 메타 파일
- [ ] 코어 전용 README
- [ ] 코어 전용 LICENSE

## E. 의존성 연결 방식 결정

`stockvision-core`를 분리한 뒤 나머지 저장소가 어떻게 참조할지 먼저 정해야 합니다.

- [ ] 개발 중에는 git dependency 또는 editable install 중 하나로 통일한다.
- [ ] `local_server`가 `stockvision-core`를 참조하는 방식 초안을 정한다.
- [ ] `cloud_server`가 `stockvision-core`를 참조하는 방식 초안을 정한다.
- [ ] 최소 호환 버전 정책을 메모한다.
  - 예: `stockvision-local >= core 0.1.x`
  - 예: `stockvision-cloud >= core 0.1.x`

## F. `frontend`는 건드리지 않고 경계만 고정

이번 단계에서는 `frontend`를 옮기지 않습니다.
대신 아래 파일을 `혼합 파일`로 고정해두고, 이후 단계 분리 대상으로 표시합니다.

- [ ] `frontend/src/context/AuthContext.tsx`
- [ ] `frontend/src/pages/StrategyBuilder.tsx`
- [ ] `frontend/src/pages/StrategyList.tsx`
- [ ] `frontend/src/components/TrafficLightStatus.tsx`
- [ ] `frontend/src/components/main/Header.tsx`
- [ ] `frontend/src/App.tsx`

이번 단계에서 할 일:

- [ ] 위 파일에 새 결합 로직을 넣지 않는다.
- [ ] 새 화면을 만들 때는 local/admin/web 중 어디 소속인지 먼저 정한다.

## G. 이동 전에 치워야 하는 로컬 전용 자산

아래는 어떤 저장소에도 올리면 안 되는 항목으로 분류합니다.

- [ ] `.env`
- [ ] `.venv/`
- [ ] `.pytest_cache/`
- [ ] `.tmp/`
- [ ] `.playwright-mcp/`
- [ ] `cloud_server.db`

## H. 1단계 종료 점검

아래 질문에 모두 `예`라고 답할 수 있으면 1단계를 끝내도 됩니다.

- [ ] 공개 저장소에 들어가면 안 되는 내부 문서 목록이 확정되었는가?
- [ ] `sv_core`가 독립 저장소가 되어도 되는 구조인지 확인했는가?
- [ ] `frontend`는 아직 안 옮긴다는 원칙이 팀 내에서 명확한가?
- [ ] 다음 단계에서 `stockvision-core`를 실제 생성하고 연결할 준비가 되었는가?

## 1단계 다음 추천 순서

1. `stockvision-internal-docs`에 내부 문서 이관
2. `stockvision-core` 실제 추출
3. 모노레포에서 `stockvision-core`를 외부 의존성으로 참조하도록 연결
4. 그 다음 `stockvision-local`
5. 그 다음 `stockvision-cloud`
6. 마지막에 `stockvision-admin`, `stockvision-web`

## 한 줄 결론

1단계는 `코드를 많이 옮기는 단계`가 아니라,
`내부 문서를 먼저 숨기고, sv_core를 첫 번째 분리 대상으로 고정하는 단계`로 보는 것이 가장 안전합니다.
