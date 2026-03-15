# StockVision

AI 기반 주식 시스템매매 자동화 플랫폼. Phase 3 (3프로세스 아키텍처).

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| Cloud Server | Python 3.13.7, FastAPI, SQLAlchemy, Claude API |
| Local Server | Python 3.13.7, FastAPI, 증권사 REST API (KIS/키움) |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS, HeroUI, React Query, Recharts |
| Infra | Docker, PostgreSQL (운영), SQLite (개발), Redis |

## 프로젝트 구조

```
cloud_server/      # 클라우드 서버 (:4010)
  api/             # FastAPI 라우터 (auth, rules, admin, stocks, ai)
  models/          # SQLAlchemy 모델
  services/        # 비즈니스 로직
  main.py          # 진입점
local_server/      # 로컬 서버 (:4020)
  broker/          # 증권사 어댑터 (KIS, 키움)
  engine/          # 전략 엔진
  routers/         # FastAPI 라우터
sv_core/           # 공유 코어 모듈
frontend/
  src/
    components/    # React 컴포넌트
    pages/         # 페이지 (MainDashboard, Admin/*, Settings)
    services/      # API 클라이언트 (cloudClient, localClient)
    types/         # TypeScript 타입
    App.tsx        # 라우팅
docs/              # 아키텍처, 개발 계획서
spec/              # 기능별 spec/plan/reports
```

## 빌드 & 실행

### Cloud Server
```bash
source .venv/Scripts/activate  # Windows
python -m uvicorn cloud_server.main:app --port 4010 --reload
```

### Local Server
```bash
source .venv/Scripts/activate
python -m uvicorn local_server.main:app --port 4020 --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev      # http://localhost:5173
npm run build    # 프로덕션 빌드
npm run lint     # ESLint
```

### 인프라
```bash
docker-compose up -d   # PostgreSQL :5432, Redis :6379
```

## 코딩 규칙

- **언어**: 한국어 주석 및 문서화
- **네이밍**: snake_case (Python), camelCase (TypeScript), PascalCase (클래스), UPPER_SNAKE_CASE (상수)
- **타입**: Python type hints, TypeScript strict 모드
- **API 응답**: `{ success, data, count }` 형식 통일
- **API 경로**: `/api/v1/` 접두어

## 주의사항

- CORS: `localhost:5173`, `localhost:3000` 허용됨
- `git add` 전 `git diff` 확인 필수 — 사용자 수정사항 미포함 확인
- 머지는 사용자 허가 후에만 `--no-ff` 병합
- 로컬 브랜치 삭제 금지
