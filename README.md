# StockVision

AI 기반 주식 시스템매매 자동화 플랫폼

## 프로젝트 개요

StockVision은 규칙 기반 시스템매매와 AI 분석을 결합한 자동화 플랫폼입니다. 사용자가 설정한 전략 규칙에 따라 실시간 시세를 감시하고, 조건 충족 시 증권사 API를 통해 자동 주문을 실행합니다.

## 주요 기능

- 규칙 기반 전략 엔진 (조건 조합, 지표 연산)
- 증권사 REST API 연동 (KIS, 키움증권)
- Claude AI 기반 종목 분석
- 실시간 시세 수신 (WebSocket)
- 어드민 대시보드 (유저/서비스키/템플릿/AI/에러 관리)

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| Cloud Server | Python 3.13, FastAPI, SQLAlchemy, Claude API |
| Local Server | Python 3.13, FastAPI, 증권사 REST API |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS, React Query |
| Infra | Docker, PostgreSQL (운영), SQLite (개발), Redis |

## 빠른 시작

```bash
# 클라우드 서버
source .venv/Scripts/activate
cd cloud_server && python -m uvicorn main:app --port 4010 --reload

# 로컬 서버
cd local_server && python -m uvicorn api.main:app --port 4020 --reload

# 프론트엔드
cd frontend && npm install && npm run dev
```

## 문서

- [아키텍처 설계](docs/architecture.md)
- [개발 계획](docs/development-plan-v2.md)

---

**개발 시작일**: 2025년 1월 27일
