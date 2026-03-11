# StockVision 저장소 분리 계획 초안

이 문서는 현재 StockVision 모노레포를 여러 저장소로 분리할 때의 권장 구조를 정리한 초안입니다.
전제는 아래와 같습니다.

- `backend/`는 장기 유지 대상이 아니라 제거 예정 폴더다.
- 제품 방향은 `무료 오픈소스 트레이딩 엔진 + 유료 개인 비서 클라우드`를 따른다.
- 공개 가치는 로컬 실행 구조와 안전장치의 투명성에 두고, 유료 가치는 동기화, 알림, 메모리, 운영 편의에 둔다.

## 한 줄 결론

지금 당장 자른다면 `3개 저장소 + 1개 후보`가 가장 현실적입니다.

1. `stockvision-core` (`sv_core`) — 공개
2. `stockvision-local` (`local_server` + 로컬 UI/패키징) — 공개
3. `stockvision-cloud` (`cloud_server` + 운영 코드) — 비공개
4. `stockvision-web` (`frontend`의 클라우드 웹 부분) — 나중에 분리 후보

`backend/`는 별도 저장소로 만들지 않고 폐기 경로로 보냅니다.

## 왜 이렇게 자르는가

현재 코드 의존성은 거의 이렇게 정리됩니다.

- `local_server` -> `sv_core`
- `cloud_server` -> `sv_core`
- `frontend` -> `local_server API` + `cloud_server API`
- `backend` -> 사실상 레거시, 현재 활성 경로의 중심이 아님

즉, 구조상 가장 먼저 독립 가능한 것은 `sv_core`입니다.
그 다음이 `local_server`와 `cloud_server`이고, 가장 늦게 잘라야 하는 것은 둘을 동시에 붙들고 있는 `frontend`입니다.

## 저장소별 권장 역할

### 1. `stockvision-core`

가장 먼저 분리할 저장소입니다.

포함:

- `sv_core/`
- `sv_core/parsing/tests/`
- `sv_core/broker/`
- 최소한의 패키징 파일 (`pyproject.toml`, `README`, `LICENSE`)

역할:

- 전략 DSL 파싱/평가
- 브로커 공통 인터페이스와 공통 모델
- 로컬/클라우드 양쪽이 공유하는 가장 작은 공용 계층

원칙:

- `local_server`, `cloud_server`, `frontend`를 몰라야 함
- 순수 라이브러리여야 함
- 버전 태그로 배포 가능해야 함

### 2. `stockvision-local`

오픈소스 엔진 저장소의 중심입니다.

포함:

- `local_server/`
- 로컬 패키징 관련 파일 (`pyinstaller.spec`, 설치 스크립트)
- 로컬 제어용 최소 UI
- 로컬 전용 테스트

역할:

- 전략 엔진
- 브로커 어댑터
- 주문 실행, 가격 검증, 안전장치
- 로컬 로그, 트레이, 키 보관
- 클라우드와의 동기화 클라이언트

의존:

- `stockvision-core`
- `cloud_server`에는 직접 import 금지, HTTP 계약만 허용

### 3. `stockvision-cloud`

유료/운영 서비스 저장소입니다.

포함:

- `cloud_server/`
- Alembic 마이그레이션
- 수집기, 관리자 기능, 인증, AI, 템플릿, 동기화
- 배포 설정, Dockerfile, 운영용 문서

역할:

- 인증과 사용자 계정
- 전략 원본 저장소, 동기화, 버전 관리
- 종목 메타/컨텍스트/AI/알림/관리자 기능
- 내부 데이터 수집과 운영 기능

의존:

- `stockvision-core`
- `stockvision-local`에는 직접 import 금지

### 4. `stockvision-web` (후보)

당장 바로 독립시키기보다, `frontend`를 먼저 두 덩어리로 분해한 뒤 빼는 게 좋습니다.

최종적으로는 아래 역할을 가질 수 있습니다.

- 로그인/회원가입/프로필
- 전략 동기화 UI
- 종목 검색, 관심종목, 클라우드 컨텍스트
- 비서, 브리핑, 리포트
- 관리자 UI

의존:

- `cloud_server` API
- 선택적으로 `local_server` 브리지 API

## `backend/`는 어떻게 할까

`backend/`는 새 저장소를 만들 가치가 없습니다.

권장 처리:

1. `backend`를 분리 대상으로 취급하지 않는다.
2. 현재 활성 코드가 `cloud_server`와 `local_server`로 완전히 대체되는지 마지막 점검만 한다.
3. 필요한 참고 구현이 있으면 이관한다.
4. 그 뒤 `backend/`는 `legacy` 표기 후 삭제한다.

즉, `찢어서 살리는 폴더`가 아니라 `정리 후 없앨 폴더`로 봐야 합니다.

## 프런트엔드는 어떻게 자를까

현재 `frontend`는 가장 애매한 층입니다.

관찰된 상태:

- `AuthContext`는 클라우드 로그인과 로컬 토큰 동기화를 동시에 처리한다.
- `StrategyBuilder`, `StrategyList`는 클라우드 규칙 CRUD 후 로컬 sync를 호출한다.
- `TrafficLightStatus`는 클라우드 헬스와 로컬 상태를 동시에 본다.
- `MainDashboard`, `Settings`는 로컬 제어 성격이 강하다.
- 로그인, 관리자, 종목 검색, 클라우드 컨텍스트는 클라우드 성격이 강하다.

즉, 지금 `frontend`는 독립 제품이 아니라 `브리지 셸`에 가깝습니다.

그래서 권장 순서는 이렇습니다.

### 먼저 할 일: 코드상 두 앱으로 분리

현재 한 Vite 앱 안에서 아래처럼 경계를 나눕니다.

- `frontend/src/local-app/`
- `frontend/src/cloud-app/`
- `frontend/src/shared-ui/`

예시 분류:

로컬 앱 후보:

- `MainDashboard.tsx`
- `Settings.tsx`
- `ExecutionLog.tsx`
- `BridgeInstaller.tsx`
- `useLocalBridgeWS.ts`
- `services/localClient.ts`
- 엔진 제어, 계좌 상태, 로컬 로그 관련 컴포넌트

클라우드 앱 후보:

- `Login.tsx`, `Register.tsx`, `ForgotPassword.tsx`, `ResetPassword.tsx`
- `StockList.tsx`, `StockSearch.tsx`
- `Admin/*`
- `services/cloudClient.ts`
- 클라우드 컨텍스트, 관심종목, AI 분석 관련 컴포넌트

경계 재설계가 필요한 혼합 화면:

- `AuthContext.tsx`
- `StrategyBuilder.tsx`
- `StrategyList.tsx`
- `TrafficLightStatus.tsx`
- `components/main/Header.tsx`

### 그 다음: 실제 저장소 분리

프런트를 바로 저장소로 떼지 말고, 먼저 코드상으로 `local-app`과 `cloud-app`이 분리된 뒤에 움직입니다.

- 로컬 제어용 UI는 `stockvision-local`로 이동
- 클라우드 웹 UI는 `stockvision-web`로 이동
- 공용 컴포넌트는 둘 중 하나로 복사하지 말고, 아주 작으면 각자 보유하고 크면 별도 패키지 고려

## 추천 분리 순서

### 1단계: 분리 기준 확정

현재 모노레포에서 아래 규칙을 먼저 세웁니다.

- `local_server`는 `cloud_server`를 import하지 않는다.
- `cloud_server`는 `local_server`를 import하지 않는다.
- 공유 코드는 `sv_core`에만 둔다.
- `backend`에는 새 코드 추가 금지

### 2단계: `sv_core` 패키지화

먼저 `sv_core`를 독립 저장소로 옮깁니다.

필수 작업:

- `pyproject.toml` 추가
- 버전 체계 도입
- 테스트 독립 실행 가능하게 정리
- 로컬/클라우드에서 `pip install -e` 또는 git dependency로 참조 가능하게 설정

이 단계가 가장 중요합니다.
이게 되면 나머지 저장소는 공통 기반을 공유하면서도 독립적으로 움직일 수 있습니다.

### 3단계: `stockvision-local` 분리

`local_server`와 로컬 패키징, 로컬 UI 최소셋을 분리합니다.

포함 권장:

- `local_server/`
- `local_server/tests/`
- 로컬 대시보드에 필요한 프런트 코드 일부
- 설치/빌드 스크립트

이 저장소는 오픈소스 대상의 중심입니다.

### 4단계: `stockvision-cloud` 분리

`cloud_server`와 운영 코드를 별도 비공개 저장소로 분리합니다.

포함 권장:

- `cloud_server/`
- `cloud_server/tests/`
- `alembic`
- `Dockerfile`
- 배포 문서, 운영 스크립트

### 5단계: `frontend`를 둘로 쪼갠 뒤 `stockvision-web` 분리

이 단계는 마지막에 합니다.

바로 분리하면 안 되는 이유:

- 현재 인증 흐름이 로컬/클라우드 브리지를 전제로 설계돼 있음
- 전략 UI가 클라우드 CRUD와 로컬 sync를 한 화면에서 처리함
- 일부 상태 컴포넌트가 양쪽 API를 동시에 참조함

그래서 먼저 화면과 서비스 계층을 둘로 나누고, 그 다음에 저장소를 분리해야 합니다.

## 실제 파일 기준 권장 귀속

### `stockvision-core`

- `sv_core/`

### `stockvision-local`

- `local_server/`
- `frontend/src/services/localClient.ts`
- `frontend/src/hooks/useLocalBridgeWS.ts`
- `frontend/src/hooks/useAccountStatus.ts`
- `frontend/src/hooks/useAccountBalance.ts`
- `frontend/src/pages/MainDashboard.tsx`
- `frontend/src/pages/Settings.tsx`
- `frontend/src/pages/ExecutionLog.tsx`
- 로컬 로그/엔진/설정/브리지 관련 컴포넌트

### `stockvision-cloud`

- `cloud_server/`
- 운영 스크립트
- 배포 설정
- 관리자/수집/인증/AI/동기화 관련 문서

### `stockvision-web` 후보

- `frontend/src/context/AuthContext.tsx` 재설계 후 이동
- `frontend/src/pages/Login.tsx`
- `frontend/src/pages/Register.tsx`
- `frontend/src/pages/StockList.tsx`
- `frontend/src/pages/StrategyBuilder.tsx` 재설계 후 이동
- `frontend/src/pages/StrategyList.tsx` 재설계 후 이동
- `frontend/src/pages/Admin/*`
- `frontend/src/services/cloudClient.ts`

## 저장소 분리 전에 꼭 할 리팩터링

1. `backend`에 대한 문서/스크립트 참조 제거
2. `sv_core`에 패키징 메타 추가
3. `frontend`의 로컬/클라우드 서비스 의존을 화면 단위로 분리
4. `AuthContext`에서 `cloud auth`와 `local bridge sync`를 분리
5. `StrategyBuilder`를 `cloud 저장`과 `local 배포` 두 유스케이스로 나누기
6. 환경변수 이름과 포트 규약 문서화

## 운영 관점에서의 장점

이렇게 자르면 아래가 좋아집니다.

- 오픈소스 공개 범위가 선명해짐
- 유료 클라우드 기능과 운영 코드 보호가 쉬워짐
- 로컬 엔진 릴리스와 클라우드 배포 주기를 분리할 수 있음
- `sv_core`를 기준으로 계약 테스트와 버전 호환성을 관리할 수 있음
- `backend` 정리가 쉬워짐

## 운영 관점에서의 주의점

이렇게 자르면 아래는 별도로 관리해야 합니다.

- API 계약 버전
- `sv_core` 버전 호환성
- 프런트와 서버의 릴리스 순서
- 로컬 앱과 클라우드의 최소 호환 버전 매트릭스

## 추천 실행 순서

가장 현실적인 실행 순서는 아래입니다.

1. `backend` 폐기 선언
2. `sv_core` 독립 패키지화
3. `local_server` 저장소 분리
4. `cloud_server` 저장소 분리
5. `frontend`를 로컬/클라우드 앱으로 논리 분리
6. 마지막에 `stockvision-web` 저장소 분리

즉, `backend`는 버리고, `sv_core`부터 떼고, `frontend`는 가장 마지막에 자르는 게 맞습니다.
