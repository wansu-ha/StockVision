# Dev 환경 자동화 — Spec

> 작성일: 2026-03-12 | 상태: 구현 완료 | 갱신일: 2026-03-15
>
> **변경 이력**: Cloudflare Pages → Vercel 변경 (Cloudflare 연동 이슈로 전환)

## 목표

`dev` 브랜치에 머지하면 프론트엔드 + 클라우드 서버가 자동 배포되는 dev 환경 구축.
로컬 서버는 태그 푸시 시 exe 빌드 → GitHub Releases 업로드.
전부 무료 티어.

## 아키텍처

```
GitHub (feat/* → dev 머지)
  │
  ├── Vercel (자동 감지)
  │     └── frontend/ 빌드 → stock-vision-two.vercel.app
  │
  ├── Render (자동 감지)
  │     └── cloud_server/ Docker → stockvision-api-1cy4.onrender.com
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
| PR 생성 | Vercel 프리뷰 URL | CI 빌드 검증만 | X |
| `dev` 머지 | 자동 배포 | 자동 배포 | X |
| 태그 `v*` 푸시 | X | X | exe 빌드 → Releases |

### URL 구조 (dev 환경)

| 서비스 | URL |
|--------|-----|
| 프론트엔드 | `https://stock-vision-two.vercel.app` |
| 클라우드 API | `https://stockvision-api-1cy4.onrender.com` |
| 로컬 서버 exe | `https://github.com/wansu-ha/StockVision/releases/latest` |

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

### R3: Vercel 연동

- GitHub 연결 → `main` 브랜치 감지
- 빌드 설정:
  - Framework: Vite
  - Root directory: `frontend`
  - 환경변수: `VITE_CLOUD_API_URL=https://stockvision-api-1cy4.onrender.com`
- SPA 라우팅: `frontend/vercel.json` (rewrites 규칙)
- PR 프리뷰: 자동 생성 (Vercel 기본 기능)

### R4: Render 연동

- `render.yaml` Blueprint로 서비스 정의
- 서비스:
  - Web Service: Docker (cloud_server/Dockerfile), 포트 4010
  - PostgreSQL: 무료 인스턴스 (1GB)
  - Redis: 무료 인스턴스 (선택 — 없으면 in-memory 폴백)
- GitHub 연결 → `dev` 브랜치 자동 배포
- 환경변수: Render 대시보드에서 설정 (`.env`는 커밋 안 함)
- CORS: Vercel URL + localhost 허용

### R5: 환경변수 관리

- `cloud_server/.env.example` — 필요한 모든 변수 목록 (값은 플레이스홀더)
- `frontend/.env.example` — 업데이트 (dev URL 예시 포함)
- 민감 정보는 절대 커밋하지 않음
- Render 대시보드에서 환경변수 설정

### R6: UptimeRobot 슬립 방지

- 무료 계정으로 HTTP 모니터 등록
- URL: `https://stockvision-api-1cy4.onrender.com/health`
- 간격: 5분
- 다운 시 이메일 알림

### R7: Docker 정비

- 기존 `cloud_server/Dockerfile` 그대로 활용
- `.dockerignore` 추가 (불필요 파일 제외)
- health check는 `render.yaml`의 `healthCheckPath`로 처리 (Dockerfile 수정 불필요)

## 수용 기준

- [x] `dev` 머지 → Vercel 자동 빌드/배포
- [x] `dev` 머지 → Render 자동 빌드/배포
- [x] `stock-vision-two.vercel.app`에서 프론트엔드 로딩 가능
- [x] `stockvision-api-1cy4.onrender.com/health`에서 정상 응답
- [x] 프론트엔드 → 클라우드 서버 API 호출 성공 (CORS OK)
- [x] PR 생성 시 GitHub Actions CI 통과
- [x] 태그 푸시 → GitHub Releases에 exe 업로드
- [x] UptimeRobot 모니터 등록 → 5분 간격 핑 확인

## 범위

### 포함
- GitHub Actions CI/CD 워크플로우
- Vercel 연동 (프론트엔드)
- Render 연동 (클라우드 서버 + DB + Redis)
- UptimeRobot 슬립 방지
- `.env.example` 정리
- `.dockerignore` 추가
- 셋업 가이드 문서

### 미포함
- 커스텀 도메인 (프로덕션 때)
- HTTPS 인증서 관리 (Vercel/Render가 자동 처리)
- 프로덕션 환경 (main 브랜치 배포)
- Alembic 마이그레이션 설정 (별도 작업)
- 코드 서명 / 인스톨러 (M4 공개 릴리스 때)

## 생성/수정 파일

### 신규
| 파일 | 내용 |
|------|------|
| `.github/workflows/ci.yml` | PR/push CI — 린트, 빌드 검증 |
| `.github/workflows/release.yml` | 태그 → PyInstaller → Releases |
| `frontend/public/_redirects` | SPA 라우팅 |
| `frontend/vercel.json` | Vercel SPA rewrite 규칙 |
| `render.yaml` | Render Blueprint (서비스 정의) |
| `.dockerignore` | Docker 빌드 제외 패턴 |
| `cloud_server/.env.example` | 클라우드 서버 환경변수 템플릿 |
| `docs/setup/dev-environment.md` | 셋업 가이드 (사용자 매뉴얼) |

### 수정
| 파일 | 변경 |
|------|------|
| `frontend/.env.example` | dev URL 예시 추가 |

## 비용 요약

| 서비스 | 비용 | 제한 |
|--------|------|------|
| GitHub Actions | 무료 | 2,000분/월 |
| Vercel | 무료 | 100GB 대역폭/월 |
| Render Web Service | 무료 | 750h/월, 15분 슬립 |
| Render PostgreSQL | 무료 | 1GB, 90일 만료 (재생성 가능) |
| Render Redis | 무료 | 25MB (선택, 없으면 in-memory) |
| UptimeRobot | 무료 | 50모니터, 5분 간격 |
| GitHub Releases | 무료 | 2GB/파일 |
| **합계** | **$0/월** | |

## 참고

- Render PostgreSQL 90일 만료: 만료 전 이메일 알림 옴. 새 인스턴스 생성 후 연결만 변경하면 됨. dev 환경 데이터는 휘발되어도 무방.
- Vercel 프로젝트명 `stock-vision-two` (기본 자동 생성).
- Render 서비스명 `stockvision-api-1cy4` (자동 생성 suffix).
