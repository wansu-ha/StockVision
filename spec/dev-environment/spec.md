# Dev 환경 자동화 — Spec

> 작성일: 2026-03-12 | 상태: 초안

## 목표

`dev` 브랜치에 머지하면 프론트엔드 + 클라우드 서버가 자동 배포되는 dev 환경 구축.
로컬 서버는 태그 푸시 시 exe 빌드 → GitHub Releases 업로드.
전부 무료 티어.

## 아키텍처

```
GitHub (feat/* → dev 머지)
  │
  ├── Cloudflare Pages (자동 감지)
  │     └── frontend/ 빌드 → stockvision.pages.dev
  │
  ├── Render (자동 감지)
  │     └── cloud_server/ Docker → stockvision-api.onrender.com
  │           ├── PostgreSQL (Render 무료)
  │           └── Redis (Render 무료)
  │
  ├── GitHub Actions (CI)
  │     ├── PR/push → lint + build 검증
  │     └── 태그 v* → PyInstaller exe → GitHub Releases
  │
  └── UptimeRobot
        └── 5분마다 /health 핑 → Render 슬립 방지
```

### 배포 트리거

| 이벤트 | 프론트엔드 | 클라우드 서버 | 로컬 서버 exe |
|--------|-----------|-------------|--------------|
| PR 생성 | Cloudflare 프리뷰 URL | CI 빌드 검증만 | X |
| `dev` 머지 | 자동 배포 | 자동 배포 | X |
| 태그 `v*` 푸시 | X | X | exe 빌드 → Releases |

### URL 구조 (dev 환경)

| 서비스 | URL |
|--------|-----|
| 프론트엔드 | `https://stockvision.pages.dev` |
| 클라우드 API | `https://stockvision-api.onrender.com` |
| 로컬 서버 exe | `https://github.com/{org}/StockVision/releases/latest/download/stockvision-local.exe` |

## 요구사항

### R1: GitHub Actions CI

- `dev` 브랜치 push 및 PR 시 트리거
- **프론트엔드**: Node 22 → `npm ci` → `npm run lint` → `npm run build`
- **클라우드 서버**: Python 3.13 → `pip install -r requirements.txt` → 임포트 검증
- 경로 필터: 각 컴포넌트 변경 시에만 해당 job 실행

### R2: GitHub Actions — exe 릴리스

- 태그 `v*` 푸시 시 트리거 (+ 수동 dispatch 가능)
- Windows runner에서 PyInstaller 빌드
- 빌드 산출물: `stockvision-local-{version}.exe`
- GitHub Releases에 자동 업로드

### R3: Cloudflare Pages 연동

- GitHub 연결 → `dev` 브랜치 감지
- 빌드 설정:
  - 빌드 명령: `cd frontend && npm install && npm run build`
  - 출력 디렉토리: `frontend/dist`
  - 환경변수: `VITE_CLOUD_API_URL=https://stockvision-api.onrender.com`
- SPA 라우팅: `frontend/public/_redirects` 파일 (`/* /index.html 200`)
- PR 프리뷰: 자동 생성 (Cloudflare 기본 기능)

### R4: Render 연동

- `render.yaml` Blueprint로 서비스 정의
- 서비스:
  - Web Service: Docker (cloud_server/Dockerfile), 포트 4010
  - PostgreSQL: 무료 인스턴스 (1GB)
  - Redis: 무료 인스턴스 (선택 — 없으면 in-memory 폴백)
- GitHub 연결 → `dev` 브랜치 자동 배포
- 환경변수: Render 대시보드에서 설정 (`.env`는 커밋 안 함)
- CORS: Cloudflare Pages URL 허용

### R5: 환경변수 관리

- `cloud_server/.env.example` — 필요한 모든 변수 목록 (값은 플레이스홀더)
- `frontend/.env.example` — 업데이트 (dev URL 예시 포함)
- 민감 정보는 절대 커밋하지 않음
- Render 대시보드에서 환경변수 설정

### R6: UptimeRobot 슬립 방지

- 무료 계정으로 HTTP 모니터 등록
- URL: `https://stockvision-api.onrender.com/health`
- 간격: 5분
- 다운 시 이메일 알림

### R7: Docker 정비

- 기존 `cloud_server/Dockerfile` 그대로 활용
- `.dockerignore` 추가 (불필요 파일 제외)
- health check는 `render.yaml`의 `healthCheckPath`로 처리 (Dockerfile 수정 불필요)

## 수용 기준

- [ ] `dev` 브랜치에 프론트 코드 머지 → Cloudflare Pages 자동 빌드/배포
- [ ] `dev` 브랜치에 서버 코드 머지 → Render 자동 빌드/배포
- [ ] `stockvision.pages.dev`에서 프론트엔드 로딩 가능
- [ ] `stockvision-api.onrender.com/health`에서 `{"status": "healthy"}` 응답
- [ ] 프론트엔드 → 클라우드 서버 API 호출 성공 (CORS OK)
- [ ] PR 생성 시 GitHub Actions CI 통과
- [ ] 태그 `v1.0.0` 푸시 → GitHub Releases에 exe 업로드
- [ ] UptimeRobot 모니터 등록 → 5분 간격 핑 확인

## 범위

### 포함
- GitHub Actions CI/CD 워크플로우
- Cloudflare Pages 연동 (프론트엔드)
- Render 연동 (클라우드 서버 + DB + Redis)
- UptimeRobot 슬립 방지
- `.env.example` 정리
- `.dockerignore` 추가
- 셋업 가이드 문서

### 미포함
- 커스텀 도메인 (프로덕션 때)
- HTTPS 인증서 관리 (Cloudflare/Render가 자동 처리)
- 프로덕션 환경 (main 브랜치 배포)
- Alembic 마이그레이션 설정 (별도 작업)
- 코드 서명 / 인스톨러 (M4 공개 릴리스 때)

## 생성/수정 파일

### 신규
| 파일 | 내용 |
|------|------|
| `.github/workflows/ci.yml` | PR/push CI — 린트, 빌드 검증 |
| `.github/workflows/release.yml` | 태그 → PyInstaller → Releases |
| `frontend/public/_redirects` | Cloudflare Pages SPA 라우팅 |
| `render.yaml` | Render Blueprint (서비스 정의) |
| `.dockerignore` | Docker 빌드 제외 패턴 |
| `cloud_server/.env.example` | 클라우드 서버 환경변수 템플릿 |
| `docs/setup/dev-environment.md` | 셋업 가이드 (사용자 매뉴얼) |

### 수정
| 파일 | 변경 |
|------|------|
| `frontend/.env.example` | dev URL 예시 추가 |

## 사용자 매뉴얼 액션 (Claude가 못 하는 것)

아래는 웹 대시보드에서 직접 수행해야 하는 작업 목록.
상세 단계는 `docs/setup/dev-environment.md`에 작성.

### 1. Cloudflare Pages 설정

1. [dash.cloudflare.com](https://dash.cloudflare.com) 가입
2. Workers & Pages → Create → Pages → Connect to Git
3. GitHub 계정 연결 → StockVision 레포 선택
4. 설정:
   - Production branch: `dev`
   - Build command: `cd frontend && npm install && npm run build`
   - Build output directory: `frontend/dist`
   - Root directory: `/` (프로젝트 루트)
5. 환경변수 추가:
   - `VITE_CLOUD_API_URL` = `https://stockvision-api.onrender.com`
   - `NODE_VERSION` = `22`
6. Save and Deploy 클릭
7. 완료 후 `*.pages.dev` URL 확인

### 2. Render 설정

1. [render.com](https://render.com) 가입 (GitHub 계정으로)
2. Dashboard → New → Blueprint
3. GitHub 레포 연결 → StockVision 선택
4. `render.yaml` 자동 감지 → Apply
5. 환경변수 설정 (Render 대시보드 → Environment):
   - `SECRET_KEY` = 강한 랜덤 문자열 (32자+)
   - `ANTHROPIC_API_KEY` = Claude API 키
   - `DART_API_KEY` = 금감원 API 키
   - `CORS_ORIGINS` = `https://stockvision.pages.dev`
   - `CLOUD_URL` = `https://stockvision-api.onrender.com`
   - `ENV` = `production`
   - (OAuth, SMTP는 나중에 필요할 때)
6. Manual Deploy → Deploy latest commit
7. 완료 후 `*.onrender.com` URL 확인
8. `/health` 엔드포인트 응답 확인

### 3. UptimeRobot 설정

1. [uptimerobot.com](https://uptimerobot.com) 가입
2. Add New Monitor:
   - Monitor Type: HTTP(s)
   - Friendly Name: `StockVision API (dev)`
   - URL: `https://stockvision-api.onrender.com/health`
   - Monitoring Interval: 5 minutes
3. Create Monitor 클릭
4. 알림 이메일 확인

### 4. GitHub Secrets 설정 (exe 릴리스용)

- GitHub Actions의 `GITHUB_TOKEN`은 자동 제공 → 별도 설정 불필요
- 추가 시크릿 불필요 (Cloudflare/Render는 자체 GitHub 연동)

### 5. 첫 배포 테스트

1. `feat/*` 브랜치에서 작업 후 `dev`에 머지
2. Cloudflare Pages 대시보드에서 빌드 상태 확인
3. Render 대시보드에서 배포 상태 확인
4. `stockvision.pages.dev` 접속 → 로그인 페이지 확인
5. `stockvision-api.onrender.com/health` 응답 확인
6. 프론트에서 API 호출 확인 (CORS, 로그인 등)

### 6. exe 릴리스 테스트

1. `git tag v1.0.0-dev && git push origin v1.0.0-dev`
2. GitHub Actions → release 워크플로우 실행 확인
3. Releases 페이지에서 exe 다운로드 확인

## 비용 요약

| 서비스 | 비용 | 제한 |
|--------|------|------|
| GitHub Actions | 무료 | 2,000분/월 |
| Cloudflare Pages | 무료 | 500빌드/월, 무제한 트래픽 |
| Render Web Service | 무료 | 750h/월, 15분 슬립 |
| Render PostgreSQL | 무료 | 1GB, 90일 만료 (재생성 가능) |
| Render Redis | 무료 | 25MB (선택, 없으면 in-memory) |
| UptimeRobot | 무료 | 50모니터, 5분 간격 |
| GitHub Releases | 무료 | 2GB/파일 |
| **합계** | **$0/월** | |

## 참고

- Render PostgreSQL 90일 만료: 만료 전 이메일 알림 옴. 새 인스턴스 생성 후 연결만 변경하면 됨. dev 환경 데이터는 휘발되어도 무방.
- Cloudflare Pages 이름 `stockvision`이 이미 점유되었으면 `stockvision-dev` 등으로 변경.
- Render 서비스 이름도 마찬가지 (`stockvision-api-dev` 등).
