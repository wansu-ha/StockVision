# Dev 환경 셋업 가이드

> 이 문서는 StockVision dev 환경을 처음 구축할 때 따라하는 가이드입니다.
> 관련 spec: `spec/dev-environment/spec.md`

## 사전 준비

- [ ] GitHub에 StockVision 레포가 push되어 있는지 확인
- [ ] `dev` 브랜치가 존재하는지 확인 (`git branch -a`)
- [ ] 프로젝트 루트에 `render.yaml`, `.github/workflows/ci.yml`, `.github/workflows/release.yml`이 있는지 확인

---

## 1. Netlify 설정 (프론트엔드)

### 1-1. 계정 생성 + 프로젝트 연결
1. [app.netlify.com](https://app.netlify.com) 접속
2. **GitHub 계정으로 로그인**
3. **Add new site** → **Import an existing project**
4. **GitHub** 선택 → StockVision 레포 선택

### 1-2. 빌드 설정

| 항목 | 값 |
|------|-----|
| **Branch to deploy** | `dev` |
| **Base directory** | `frontend` |
| **Build command** | `npm install && npm run build` |
| **Publish directory** | `frontend/dist` |

### 1-3. 환경변수 설정

같은 화면 아래 **Environment variables** 섹션에서 추가:

| 변수 | 값 |
|------|-----|
| `VITE_CLOUD_API_URL` | `https://stockvision-api.onrender.com` |

### 1-4. 배포

1. **Deploy site** 클릭
2. 빌드 로그 실시간 확인 (1-2분 소요)
3. 성공 시 URL 부여: `https://{랜덤}.netlify.app`

### 1-5. 사이트 이름 변경

1. **Site configuration** → **Site details** → **Change site name**
2. `stockvision`으로 변경 → `https://stockvision.netlify.app`
3. 이미 점유되었으면 `stockvision-dev` 등

> ⚠️ 사이트 이름 변경 시 Render의 `CORS_ORIGINS`도 새 URL로 맞춰야 합니다.

### 1-6. 배포 확인

- [ ] `https://stockvision.netlify.app` 접속 가능
- [ ] 로그인 페이지 표시
- [ ] SPA 라우팅 동작 (`/settings` 직접 접속 시 404 아닌 정상 표시)

> SPA 라우팅은 `frontend/public/_redirects` 파일(`/* /index.html 200`)이 처리합니다.
> Netlify도 `_redirects` 파일을 동일하게 지원합니다.

### 1-7. 자동 배포

- `dev` 브랜치에 push하면 Netlify가 자동 빌드 + 배포
- PR을 열면 프리뷰 URL 자동 생성 (Deploy Previews)
- **Deploys** 탭에서 빌드 기록 확인 가능

---

## 2. Render 설정 (클라우드 서버)

### 2-1. 계정 생성
1. [render.com](https://render.com) 접속
2. **GitHub 계정으로 가입** (GitHub 연동이 자동으로 됨)

### 2-2. Blueprint으로 서비스 생성
1. Dashboard → **New** → **Blueprint**
2. GitHub 레포 연결 → StockVision 선택
3. `render.yaml` 자동 감지 → 서비스 목록 표시:
   - `stockvision-api` (Web Service)
   - `stockvision-db` (PostgreSQL)
   - `stockvision-redis` (Redis)
4. **Apply** 클릭

### 2-3. 환경변수 설정
Dashboard → `stockvision-api` → **Environment** 탭:

| 변수 | 값 | 설명 |
|------|-----|------|
| `SECRET_KEY` | `python -c "import secrets; print(secrets.token_urlsafe(32))"` 결과 | JWT 서명 키 |
| `ANTHROPIC_API_KEY` | Claude API 키 | AI 분석용 |
| `DART_API_KEY` | 금감원 API 키 | 재무 데이터 |
| `CORS_ORIGINS` | `https://stockvision.netlify.app` | Netlify URL (정확히 일치해야 함) |
| `CLOUD_URL` | `https://stockvision-api.onrender.com` | 이메일 링크 등에 사용 |
| `ENV` | `production` | 환경 구분 |

> `DATABASE_URL`, `REDIS_URL`은 render.yaml에서 자동 주입됩니다.
> OAuth, SMTP는 나중에 필요할 때 추가하면 됩니다.

### 2-4. 배포 확인
1. **Manual Deploy** → **Deploy latest commit** 클릭
2. 빌드 로그 확인 (Docker 빌드, 3-5분 소요)
3. 배포 완료 후 URL 확인: `https://stockvision-api.onrender.com`
4. `/health` 접속 → `{"success": true, "status": "healthy", ...}` 응답 확인

### 2-5. CORS 확인
프론트엔드에서 API 호출이 되는지 확인:
1. `https://stockvision.netlify.app` 접속
2. 로그인 시도 → API 호출이 CORS 에러 없이 처리되면 성공
3. CORS 에러 발생 시 → Render 환경변수 `CORS_ORIGINS` 값 확인

---

## 3. UptimeRobot 설정 (슬립 방지)

Render 무료 티어는 15분 미활동 시 서버가 슬립됩니다. UptimeRobot이 5분마다 핑을 보내서 방지.

### 3-1. 계정 생성
1. [uptimerobot.com](https://uptimerobot.com) 접속
2. 이메일로 가입 (무료 — 50개 모니터, 5분 간격)

### 3-2. 모니터 생성
1. Dashboard → **Add New Monitor**
2. 설정:

| 항목 | 값 |
|------|-----|
| Monitor Type | HTTP(s) |
| Friendly Name | `StockVision API (dev)` |
| URL | `https://stockvision-api.onrender.com/health` |
| Monitoring Interval | 5 minutes |

3. **Create Monitor** 클릭
4. 이메일 알림 설정 확인

### 3-3. 동작 확인
- Dashboard에서 모니터 상태가 **Up** (초록색)인지 확인
- Render 대시보드에서 5분마다 `/health` 요청이 들어오는지 로그 확인

---

## 4. 첫 배포 테스트

모든 서비스 설정 후 아래 체크리스트를 확인:

### 자동 배포 테스트
1. `feat/*` 브랜치에서 프론트엔드 파일 수정
2. `dev` 브랜치에 머지 (PR 또는 직접 머지)
3. 확인:
   - [ ] Netlify 대시보드 → 빌드 시작됨
   - [ ] Render 대시보드 → 배포 시작됨
   - [ ] GitHub Actions → CI 워크플로우 실행됨

### 프론트엔드 확인
- [ ] `https://stockvision.netlify.app` 접속 가능
- [ ] 로그인 페이지 표시
- [ ] SPA 라우팅 동작 (`/settings` 직접 접속 시 404 아닌 정상 표시)

### 클라우드 서버 확인
- [ ] `https://stockvision-api.onrender.com/health` → 정상 응답
- [ ] 프론트에서 로그인 시도 → API 호출 성공 (CORS OK)

### UptimeRobot 확인
- [ ] 모니터 상태 Up
- [ ] Render 서버가 15분 후에도 슬립하지 않음

---

## 5. exe 릴리스 테스트

### 태그 기반 릴리스
```bash
git tag v1.0.0-dev
git push origin v1.0.0-dev
```

### 확인
- [ ] GitHub Actions → `Release Local Server` 워크플로우 실행
- [ ] Windows runner에서 PyInstaller 빌드 성공
- [ ] Releases 페이지에 `stockvision-local` 에셋 업로드됨
- [ ] exe 다운로드 가능

### 수동 빌드 (태그 없이)
1. GitHub → Actions → `Release Local Server`
2. **Run workflow** → 브랜치 선택 → **Run**
3. 빌드 완료 후 Artifacts에서 다운로드

---

## 6. 트러블슈팅

### Netlify

| 증상 | 원인 | 해결 |
|------|------|------|
| `npm install` 실패 | Node 버전 불일치 | 환경변수 `NODE_VERSION=22` 추가 |
| `tsc` 에러 | TypeScript 빌드 에러 | 로컬에서 `cd frontend && npm run build` 먼저 확인 |
| SPA 라우팅 404 | `_redirects` 파일 누락 | `frontend/public/_redirects` 존재 확인 |
| 환경변수 변경 후 반영 안 됨 | 재빌드 필요 | Deploys 탭 → Trigger deploy → Deploy site |
| `dev`가 아닌 `main`으로 배포됨 | Branch 설정 | Site configuration → Branch & deploy contexts → Production branch를 `dev`로 변경 |

### Render

| 증상 | 원인 | 해결 |
|------|------|------|
| Docker 빌드 실패 | Dockerfile 문제 | 로컬에서 `docker build -f cloud_server/Dockerfile .` 테스트 |
| health check 실패 | SECRET_KEY 미설정 | `SECRET_KEY` 환경변수 확인 (없으면 서버 시작 실패) |
| DB 연결 실패 | DATABASE_URL 미주입 | render.yaml의 `fromDatabase` 설정 확인 |

### CORS 에러
- Render 환경변수 `CORS_ORIGINS`가 Netlify URL과 **정확히** 일치하는지 확인
- 프로토콜 (`https://`) 포함, 끝에 `/` 없이

### Render 슬립
- UptimeRobot 모니터가 **Up** 상태인지 확인
- URL이 정확한지 확인 (`/health` 포함)
- 5분 간격이 설정되었는지 확인

### exe 빌드 실패
- `local_server/requirements.txt`의 의존성이 Windows에서 설치 가능한지 확인
- PyInstaller 버전이 Python 3.13을 지원하는지 확인
- `local_server/pyinstaller.spec`의 경로가 정확한지 확인

---

## 7. 일상 운영

### dev 브랜치 워크플로우
```
feat/my-feature → dev (머지) → 자동 배포
```

### Render PostgreSQL 90일 갱신
- 만료 2주 전 이메일 알림이 옴
- 새 PostgreSQL 인스턴스 생성 → `DATABASE_URL` 환경변수 변경
- dev 환경 데이터는 휘발되어도 무방

### 프로덕션 배포 (나중에)
- `main` 브랜치 기반 별도 환경 구성
- 커스텀 도메인 구매 후 연결
- Render 유료 플랜으로 업그레이드 (슬립 방지)
