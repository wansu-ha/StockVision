# StockVision

AI 기반 주식 동향 예측 및 가상 거래 시스템. 현재 Phase 2 (프론트엔드 차트, 가상 거래, 백테스팅).

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| Backend | Python 3.13.7, FastAPI, SQLAlchemy, yfinance, scikit-learn, TensorFlow/Keras |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS, HeroUI, React Query, Recharts |
| Infra | Docker, PostgreSQL (운영), SQLite (개발), Redis |

## 프로젝트 구조

```
backend/
  app/
    api/           # FastAPI 라우터 (stocks, ai_analysis, logs)
    core/          # DB, 캐싱, 로깅, 모니터링
    models/        # SQLAlchemy 모델
    services/      # 비즈니스 로직 (데이터 수집, 예측, 캐시)
    main.py        # FastAPI 앱 진입점
  models/          # 학습된 ML 모델 (.pkl)
  requirements.txt
frontend/
  src/
    components/    # React 컴포넌트
    pages/         # 페이지 (Dashboard, StockDetail, StockList)
    services/      # API 클라이언트 (Axios)
    types/         # TypeScript 타입
    App.tsx        # 라우팅
docs/              # 아키텍처, 개발 계획서
spec/              # 기능별 spec/plan/reports
```

## 빌드 & 실행

### Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload          # http://localhost:8000
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

### 테스트
```bash
cd backend
python test_core_business.py
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
