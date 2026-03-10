> 작성일: 2026-03-10 | 상태: 구현 완료

# 레거시 백엔드 제거

## 목표

Phase 1-2 모노리스 백엔드(`backend/`)를 삭제한다. Phase 3 아키텍처(cloud_server + local_server + frontend)로 전환 완료되어 더 이상 사용되지 않는 코드를 정리한다.

## 배경

- `backend/app/` — FastAPI 모노리스, :8000. Phase 1-2 전용
- Phase 3에서 cloud_server(:4010) + local_server(:4020)로 분리 완료
- 프론트엔드는 이미 cloud_server/local_server만 호출 (레거시 서비스 파일은 스텁화 완료)
- docker-compose.yml에 backend 서비스 없음

## 마이그레이션 현황 (~75%)

| 기능 | 레거시 | Phase 3 | 상태 |
|------|--------|---------|------|
| 인증 (7 endpoints) | backend/app/api/auth | cloud_server/api/auth | 마이그레이션 완료 |
| 규칙/템플릿 CRUD | backend/app/api/rules,templates | cloud_server/api/rules,templates | 마이그레이션 완료 (확장) |
| 어드민 | backend/app/api/admin | cloud_server/api/admin | 마이그레이션 완료 (7 서브페이지) |
| AI 분석 | scikit-learn/TensorFlow 로컬 | Claude API 호출 | 다른 구현으로 대체 |
| 종목 메타 | backend/app/api/stocks | cloud_server 내 처리 | 마이그레이션 |
| 가상 거래 (12 ep) | backend/app/api/virtual_trading | — | 의도적 미마이그레이션 (실거래로 대체) |
| 포트폴리오 (3 ep) | backend/app/api/portfolio | — | 의도적 미마이그레이션 |
| 온보딩 (3 ep) | backend/app/api/onboarding | — | 의도적 미마이그레이션 |
| 실행 로그 (4 ep) | backend/app/api/logs | local_server /api/logs | 마이그레이션 완료 |

미마이그레이션 항목은 Phase 3 아키텍처에서 설계적으로 불필요 (가상 거래 → 실거래, 포트폴리오 → 로컬 서버 엔진).

## 삭제 대상

### 1차: backend/ 디렉토리 (필수)

| 경로 | 내용 | 크기 |
|------|------|------|
| backend/app/ | FastAPI 앱 (라우터, 모델, 서비스) | ~40 파일 |
| backend/models/ | 학습된 ML 모델 (.pkl) | ~5 파일 |
| backend/scripts/ | seed, template 스크립트 | ~3 파일 |
| backend/logs/ | 로그 파일 | — |
| backend/stockvision.db | SQLite DB (Phase 1-2) | 217KB |
| backend/requirements.txt | Python 의존성 | 1 파일 |
| backend/test_*.py | 테스트 파일 | 2 파일 |
| backend/*.py | collect_all_stocks, stock_symbols | 2 파일 |

### 2차: 프론트엔드 스텁 서비스 (연쇄 정리)

| 파일 | 상태 | 비고 |
|------|------|------|
| services/api.ts | STUB | console.warn, 빈 데이터 반환 |
| services/dashboard.ts | STUB | console.warn, 빈 데이터 반환 |
| services/portfolio.ts | STUB | console.warn, 빈 데이터 반환 |
| services/templates.ts | STUB | console.warn, 빈 데이터 반환. StrategyTemplate 타입 포함 |
| services/onboarding.ts | STUB | console.warn, 빈 데이터 반환 |

### 3차: 스텁 의존 페이지 (연쇄 정리)

| 페이지 | 사용 스텁 | 비고 |
|--------|----------|------|
| pages/Trading.tsx | tradingApi, stockApi | Phase 1 가상 거래 UI |
| pages/StockDetail.tsx | stockApi | Phase 1 종목 상세 |
| pages/Portfolio.tsx | portfolioApi | Phase 1 포트폴리오 |
| pages/Onboarding.tsx | onboardingApi | Phase 1 온보딩 |
| pages/Templates.tsx | templatesApi | Phase 1 템플릿 (어드민에 대체) |
| pages/Dashboard.tsx | dashboardApi | Phase 1 대시보드 (MainDashboard로 대체) |
| components/AIStockAnalysis.tsx | aiAnalysisApi | Phase 1 AI 분석 컴포넌트 |

### 4차: 문서/설정 정리

| 파일 | 변경 내용 |
|------|----------|
| CLAUDE.md | backend 빌드 섹션 제거, 테스트 섹션 갱신 |
| frontend/.env.example | VITE_API_URL (8000) 라인 제거 |
| frontend/.env.local | VITE_API_URL (8001) 라인 제거 |
| App.tsx | 삭제된 페이지 import/route 제거 |

## 보존 대상 (삭제 금지)

- `services/logs.ts` — ACTIVE (local_server :4020 호출)
- `services/auth.ts` — ACTIVE (cloud_server 인증)
- `services/rules.ts` — ACTIVE (변환 유틸리티)
- `services/cloudClient.ts` — ACTIVE
- `services/localClient.ts` — ACTIVE
- `services/admin.ts` — ACTIVE
- `pages/ExecutionLog.tsx` — ACTIVE (logs.ts 사용)
- `pages/StrategyBuilder.tsx`, `pages/StrategyList.tsx` — cloud_server 사용 확인 필요

## 수용 기준

- [x] `backend/` 디렉토리 완전 삭제
- [x] 프론트엔드 스텁 서비스 5개 삭제
- [x] 스텁 의존 페이지/컴포넌트 삭제
- [x] App.tsx에서 삭제된 페이지 import/route 제거
- [x] `npm run build` — 삭제 관련 에러 0건 (기존 TS 이슈만 존재)
- [x] 문서/설정 파일 갱신
- [x] git에 `localhost:8000` 참조 0건 (삭제된 파일 제외)

## 범위

**포함**: backend/ 삭제, 프론트엔드 데드코드 정리, 문서 갱신
**미포함**: Phase 3 새 페이지 구현 (가상 거래 대체 UI 등), cloud_server/local_server 코드 변경
