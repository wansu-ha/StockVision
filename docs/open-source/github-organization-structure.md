# StockVision GitHub Organization 구조 제안

이 문서는 StockVision을 여러 저장소로 나눠 운영할 때 권장하는 GitHub Organization 구조를 정리한 초안입니다.
전제는 아래와 같습니다.

- `backend/`는 이미 제거되었고 더 이상 저장소 대상이 아니다.
- 1인 개발자가 감당 가능한 수준으로 단순하게 운영한다.
- 오픈소스 공개 범위는 로컬 엔진과 공유 코어에 한정한다.
- 클라우드 운영 코드, 관리자 기능, 내부 문서는 비공개로 유지한다.

## 한 줄 추천

`Organization`은 하나만 만들고, 그 안에 공개 레포와 비공개 레포를 함께 두는 구성이 가장 현실적입니다.

추천 이름:

- 1순위: `stockvision`
- 2순위: `stockvision-dev`
- 3순위: `stockvisionhq`

1인 운영 기준에서는 `public org`와 `private org`를 따로 나누는 것보다,
하나의 Organization 안에서 repo visibility만 다르게 가져가는 편이 훨씬 덜 번거롭습니다.

## 권장 Organization 구조

### 최상위 원칙

- Organization은 하나만 사용한다.
- 공개/비공개는 repo 단위로 나눈다.
- 내부 의사결정 문서는 코드 저장소와 분리한다.
- `frontend`는 바로 repo를 만들지 않고, 먼저 local/web/admin 경계를 코드상에서 나눈다.

## 권장 저장소 목록

| 저장소 | 공개 여부 | 현재 소스 | 역할 |
|---|---|---|---|
| `stockvision-core` | 공개 | `sv_core/` | 공유 코어, DSL, 공통 모델, 브로커 인터페이스 |
| `stockvision-local` | 공개 | `local_server/` + 로컬 UI 일부 | 오픈소스 로컬 엔진 본체 |
| `stockvision-cloud` | 비공개 | `cloud_server/` | 인증, 동기화, AI, 운영, admin API |
| `stockvision-admin` | 비공개 | `frontend/src/pages/Admin/*` 등 | 관리자 프런트엔드 |
| `stockvision-internal-docs` | 비공개 | `docs/product`, `docs/research`, `spec` 등 | 내부 전략, 리서치, 보안, 법무, 분리 계획 |
| `stockvision-web` | 비공개 후보 | `frontend` 일부 | 일반 사용자용 클라우드 웹앱, 나중에 분리 |
| `stockvision-labs` | 비공개 후보 | `prototypes/` | 실험용 저장소, 필요할 때만 생성 |

## 지금 당장 만들 저장소

바로 만드는 것을 권장하는 저장소는 아래 5개입니다.

1. `stockvision-core`
2. `stockvision-local`
3. `stockvision-cloud`
4. `stockvision-admin`
5. `stockvision-internal-docs`

`stockvision-web`은 아직 만들지 않아도 됩니다.
현재 `frontend`는 local/cloud/admin이 섞여 있으므로, 코드 경계가 정리된 뒤에 만드는 편이 낫습니다.

## 공개/비공개 기준

### 공개 저장소

- `stockvision-core`
- `stockvision-local`

공개 이유:

- 로컬 엔진과 코어는 오픈소스 가치가 크다.
- 사용자가 로컬 동작을 검증할 수 있다.
- 외부 기여를 받을 수 있다.

### 비공개 저장소

- `stockvision-cloud`
- `stockvision-admin`
- `stockvision-internal-docs`
- `stockvision-web` (분리 시점에도 우선 비공개 권장)

비공개 이유:

- 운영 코드와 계정 시스템은 공격면이 넓다.
- 관리자 기능은 공개 가치보다 위험이 크다.
- 제품 방향, 가격, 리서치, 보안 감사는 내부 정보다.

## Team 구성 권장안

1인 개발자 기준에서는 팀을 많이 만들 필요가 없습니다.
그래도 나중을 대비해 최소 구조만 정해두면 좋습니다.

### 최소 권장 Team

- `owners`
  - 용도: Organization 설정, repo 생성/삭제, billing, secrets
  - 현재는 본인만 포함
- `public-maintainers`
  - 용도: 공개 저장소 관리
  - 권한: `stockvision-core`, `stockvision-local`에 write/maintain
- `private-maintainers`
  - 용도: 비공개 제품 코드 관리
  - 권한: `stockvision-cloud`, `stockvision-admin`, `stockvision-internal-docs`에 write/maintain

### 지금은 없어도 되는 Team

- `contractors`
- `security-reviewers`
- `advisors`

혼자 운영 중이라면 팀을 실제로 만들지 않아도 되지만,
이 이름을 미리 기준으로 잡아두면 나중에 사람을 초대할 때 덜 흔들립니다.

## 저장소별 기본 설정

모든 저장소에 공통으로 권장하는 설정은 아래와 같습니다.

- 기본 브랜치: `main`
- 브랜치 보호: `main` 직접 force push 금지
- 태그 규칙: `v0.1.0`, `v0.2.0` 같은 semver 사용
- 기본 이슈 템플릿: bug, feature, security
- 공개 저장소에는 `SECURITY.md`, `SUPPORT.md`, `CONTRIBUTING.md` 배치
- 비공개 저장소에는 운영자용 `README`와 배포/복구 메모만 최소 배치

## 저장소 네이밍 규칙

권장 규칙은 `stockvision-*` 접두사 고정입니다.

좋은 예:

- `stockvision-core`
- `stockvision-local`
- `stockvision-cloud`
- `stockvision-admin`
- `stockvision-internal-docs`

피해야 할 예:

- `core`
- `server2`
- `stockvision-new-backend`
- `frontend-next`

이름만 보고 역할과 공개 여부를 짐작할 수 있어야 유지보수가 쉽습니다.

## 추천 pinned repositories

Organization 메인 화면에서 고정해둘 저장소는 아래가 적당합니다.

- `stockvision-local`
- `stockvision-core`
- `stockvision-cloud`
- `stockvision-admin`

`stockvision-internal-docs`는 비공개라 외부 노출 가치가 없으니 pinned 대상이 아니어도 됩니다.

## 릴리스 운영 권장안

### 공개 저장소

- `stockvision-core`: 태그 릴리스 중심
- `stockvision-local`: 릴리스 노트 + 설치 가이드 중심

### 비공개 저장소

- `stockvision-cloud`: 운영 배포 태그 또는 내부 배포 로그
- `stockvision-admin`: cloud와 버전 호환 기준만 맞추기
- `stockvision-internal-docs`: 릴리스 개념 없음

## 하지 않는 것을 먼저 정하기

아래는 지금 단계에서 하지 않는 것을 권장합니다.

- Organization을 두 개 이상 만들기
- `cloud_server` 내부를 auth/collector/admin/ai 별도 repo로 더 찢기
- `frontend`를 지금 바로 `stockvision-web`으로 독립시키기
- 내부 문서를 공개 docs repo로 통째로 올리기

## 실행 순서 요약

1. `stockvision` Organization 생성
2. 위 5개 저장소 생성
3. 공개/비공개 visibility 설정
4. `stockvision-internal-docs`로 내부 문서부터 격리
5. `stockvision-core` 분리
6. `stockvision-local`, `stockvision-cloud` 분리
7. 마지막에 admin/web 프런트 분리

## 한 줄 결론

StockVision은 `하나의 GitHub Organization + 공개 2개 + 비공개 3개` 구조로 시작하는 것이 가장 단순하고, 지금 프로젝트 상태에도 잘 맞습니다.
