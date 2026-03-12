# Dev 환경 자동화 — Plan

> 작성일: 2026-03-12 | 상태: 초안

## 구현 순서

의존성 순서: 설정 파일 → CI → 배포 연동 → 가이드

### Step 1: .env.example 정리 (R5)

env 템플릿을 먼저 정리해야 Render/Cloudflare 설정 시 참조 가능.

**생성: `cloud_server/.env.example`**
```env
# === 필수 ===
SECRET_KEY=               # JWT 서명 키 (32자+ 랜덤 문자열)

# === 데이터베이스 ===
DATABASE_URL=sqlite:///./cloud_server.db   # dev: SQLite / prod: postgresql://...

# === AI (Claude API) ===
ANTHROPIC_API_KEY=        # Claude API 키 (AI 기능 사용 시 필수)
CLAUDE_MODEL=claude-sonnet-4-20250514
AI_DAILY_LIMIT=100
AI_CACHE_TTL=3600
AI_STOCK_LIMIT=50

# === 외부 API ===
DART_API_KEY=             # 금감원 전자공시 API

# === 서버 설정 ===
ENV=development           # development | production
CLOUD_URL=http://localhost:4010
CORS_ORIGINS=http://localhost:5173

# === Redis (선택 — 비우면 in-memory 폴백) ===
REDIS_URL=

# === 이메일 (선택) ===
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=noreply@stockvision.com

# === OAuth2 (선택) ===
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=
KAKAO_CLIENT_ID=
KAKAO_CLIENT_SECRET=
KAKAO_REDIRECT_URI=

# === 암호화 (선택) ===
CONFIG_ENCRYPTION_KEY=
```

**수정: `frontend/.env.example`**
```env
# 클라우드 서버 API URL
VITE_CLOUD_API_URL=http://localhost:4010
# VITE_CLOUD_API_URL=https://stockvision-api.onrender.com   # dev 환경

# 로컬 서버 API URL (항상 localhost — 사용자 PC에서 실행)
VITE_LOCAL_API_URL=http://localhost:4020
```

**verify**: 파일 내용 확인, 기존 `.env`와 대조하여 누락 변수 없는지 확인

---

### Step 2: .dockerignore + _redirects (R3, R7)

**생성: `.dockerignore`**
```
frontend/
docs/
spec/
.github/
.git/
*.md
.env
.env.*
__pycache__/
*.pyc
.pytest_cache/
node_modules/
dist/
*.spec
```

**생성: `frontend/public/_redirects`**
```
/* /index.html 200
```

**verify**: 파일 존재 확인

---

### Step 3: render.yaml (R4)

Render Blueprint — 서비스 정의.

**생성: `render.yaml`**
```yaml
services:
  - type: web
    name: stockvision-api
    runtime: docker
    dockerfilePath: cloud_server/Dockerfile
    dockerContext: .
    branch: dev
    plan: free
    healthCheckPath: /health
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: stockvision-db
          property: connectionString
      - key: SECRET_KEY
        sync: false        # Render 대시보드에서 수동 입력
      - key: ANTHROPIC_API_KEY
        sync: false
      - key: DART_API_KEY
        sync: false
      - key: CORS_ORIGINS
        value: https://stockvision.pages.dev
      - key: CLOUD_URL
        value: https://stockvision-api.onrender.com
      - key: ENV
        value: production
      - key: REDIS_URL
        fromService:
          name: stockvision-redis
          type: redis
          property: connectionString

databases:
  - name: stockvision-db
    plan: free
    databaseName: stockvision
    user: stockvision_user

services:
  - type: redis
    name: stockvision-redis
    plan: free
    maxmemoryPolicy: allkeys-lru
```

**주의**: render.yaml에서 `services` 키가 두 번 나오면 안 됨. 최종 파일에서는 web + redis를 하나의 `services` 배열 아래 병합.

**verify**: YAML 문법 검증 (`python -c "import yaml; yaml.safe_load(open('render.yaml'))"`)

---

### Step 4: GitHub Actions CI (R1)

**생성: `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  push:
    branches: [dev]
  pull_request:
    branches: [dev, main]

jobs:
  frontend:
    name: Frontend (lint + build)
    runs-on: ubuntu-latest
    if: |
      github.event_name == 'push' ||
      contains(join(github.event.pull_request.changed_files.*.filename, ','), 'frontend/')
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npm run lint
      - run: npm run build
        env:
          VITE_CLOUD_API_URL: https://stockvision-api.onrender.com

  cloud-server:
    name: Cloud Server (import check)
    runs-on: ubuntu-latest
    if: |
      github.event_name == 'push' ||
      contains(join(github.event.pull_request.changed_files.*.filename, ','), 'cloud_server/') ||
      contains(join(github.event.pull_request.changed_files.*.filename, ','), 'sv_core/')
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
          cache: pip
          cache-dependency-path: cloud_server/requirements.txt
      - run: pip install -r cloud_server/requirements.txt
      - run: python -c "from cloud_server.main import app; print('OK')"
```

**참고**: `changed_files` 컨텍스트는 push 이벤트에서 지원 안 될 수 있음. 대안으로 `paths` 필터 사용. 최종 구현에서 검증.

**verify**: YAML 문법 검증, GitHub Actions 문법 확인

---

### Step 5: GitHub Actions Release (R2)

**생성: `.github/workflows/release.yml`**

```yaml
name: Release Local Server

on:
  push:
    tags: ['v*']
  workflow_dispatch:
    inputs:
      version:
        description: 'Version tag (e.g., v1.0.0)'
        required: true

jobs:
  build-exe:
    name: Build Windows Executable
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.13'
          cache: pip
          cache-dependency-path: local_server/requirements.txt
      - run: pip install -r local_server/requirements.txt
      - run: pyinstaller local_server/pyinstaller.spec
      - name: Upload to Release
        uses: softprops/action-gh-release@v2
        if: startsWith(github.ref, 'refs/tags/')
        with:
          files: dist/stockvision-local/*
```

**verify**: YAML 문법 검증

---

### Step 6: 셋업 가이드 문서 (사용자 매뉴얼)

**생성: `docs/setup/dev-environment.md`**

사용자가 웹 대시보드에서 직접 수행해야 하는 작업을 상세히 기술.
내용은 spec의 "사용자 매뉴얼 액션" 섹션을 기반으로 확장.

섹션 구성:
1. 사전 준비 (GitHub 레포 push 상태 확인)
2. Cloudflare Pages 설정 (스크린샷 경로 포함)
3. Render 설정 (Blueprint, 환경변수)
4. UptimeRobot 설정
5. 첫 배포 테스트 체크리스트
6. exe 릴리스 테스트
7. 트러블슈팅 (CORS, 빌드 실패, 슬립 등)

**verify**: 문서 내 URL, 명령어 정확성 확인

---

## 구현 순서 요약

```
Step 1: .env.example 정리          ← 독립, 먼저
Step 2: .dockerignore + _redirects ← 독립
Step 3: render.yaml                ← 독립
Step 4: ci.yml                     ← 독립
Step 5: release.yml                ← 독립
Step 6: 셋업 가이드 문서            ← Step 1-5 참조
```

Step 1-5는 모두 독립적이므로 병렬 구현 가능. Step 6은 전체 참조 필요.

## 검증 방법

### Claude가 검증하는 것
- [ ] 모든 파일 YAML/문법 검증
- [ ] render.yaml 구조 정확성
- [ ] GitHub Actions 워크플로우 문법
- [ ] .env.example이 config.py의 모든 변수를 커버하는지
- [ ] _redirects SPA 라우팅 규칙

### 사용자가 검증하는 것
- [ ] Cloudflare Pages 대시보드에서 빌드 성공
- [ ] Render 대시보드에서 배포 성공
- [ ] `*.pages.dev` 접속 → 로그인 페이지 표시
- [ ] `*.onrender.com/health` → 정상 응답
- [ ] 프론트 → API 호출 성공 (CORS)
- [ ] UptimeRobot 모니터 정상 동작
- [ ] 태그 푸시 → Releases에 exe 업로드

## 커밋 계획

단일 커밋으로 묶음:
```
docs: dev 환경 자동화 spec/plan + CI/CD 설정

- GitHub Actions CI (lint + build 검증)
- GitHub Actions Release (PyInstaller exe)
- Render Blueprint (render.yaml)
- Cloudflare Pages SPA 라우팅 (_redirects)
- .env.example 정리
- .dockerignore 추가
- 셋업 가이드 문서
```
