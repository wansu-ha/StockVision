> 작성일: 2026-03-10 | 상태: 구현 완료

# 레거시 백엔드 제거 — 구현 계획서

## §0 현황

- `backend/` — Phase 1-2 FastAPI 모노리스, 프론트엔드에서 호출 0건 (스텁화 완료)
- docker-compose.yml에 backend 서비스 없음
- cloud_server + local_server가 모든 기능 담당
- 프론트엔드 스텁 서비스 5개 + 의존 페이지 7개 = 데드코드

## §1 삭제 안전성 확인 결과

| 항목 | 결과 |
|------|------|
| docker-compose.yml | backend 참조 없음 ✅ |
| Python import | backend/ import 없음 ✅ |
| 프론트엔드 API 호출 | localhost:8000 직접 호출 0건 ✅ |
| CI/CD | backend 참조 없음 ✅ |
| .env | VITE_API_URL만 정리 필요 ⚠️ |

## §2 구현 순서

### Step 1: backend/ 디렉토리 삭제

**작업**: `rm -rf backend/`

**삭제 파일**:
- backend/app/ (FastAPI 앱 전체)
- backend/models/ (ML 모델 .pkl)
- backend/scripts/ (seed, template)
- backend/logs/
- backend/stockvision.db
- backend/requirements.txt
- backend/env.example
- backend/test_*.py
- backend/collect_all_stocks.py
- backend/stock_symbols.py

**verify**: `ls backend/` → "No such file or directory"

### Step 2: 프론트엔드 스텁 서비스 삭제

**삭제 파일** (5개):
- frontend/src/services/api.ts
- frontend/src/services/dashboard.ts
- frontend/src/services/portfolio.ts
- frontend/src/services/templates.ts
- frontend/src/services/onboarding.ts

**보존** (ACTIVE):
- services/auth.ts, cloudClient.ts, localClient.ts, admin.ts, logs.ts, rules.ts

**verify**: 삭제 후 파일 존재 확인

### Step 3: 스텁 의존 페이지/컴포넌트 삭제

**삭제 파일** (7개):
- frontend/src/pages/Trading.tsx
- frontend/src/pages/StockDetail.tsx
- frontend/src/pages/Portfolio.tsx
- frontend/src/pages/Onboarding.tsx
- frontend/src/pages/Templates.tsx
- frontend/src/pages/Dashboard.tsx
- frontend/src/components/AIStockAnalysis.tsx

**보존**:
- pages/StrategyBuilder.tsx, StrategyList.tsx (cloudClient 사용)
- pages/ExecutionLog.tsx (logs.ts ACTIVE)
- pages/MainDashboard.tsx (현재 메인)
- pages/Admin/* (cloud admin)

**verify**: 삭제 파일 목록 확인

### Step 4: App.tsx 라우트 정리

**변경 파일**: frontend/src/App.tsx

**삭제할 import**:
- Dashboard, StockDetail, Trading, Portfolio, Templates, Onboarding

**삭제할 Route**:
- `/legacy-dashboard`
- `/stocks/:symbol`
- `/trading`
- `/portfolio`
- `/templates`
- `/onboarding`

**보존할 Route**:
- `/` (MainDashboard)
- `/login`, `/register`, `/forgot-password`, `/reset-password`
- `/admin/*`
- `/settings`
- `/stocks` (StockList — cloudClient 사용 확인 필요)
- `/strategies/*` (StrategyBuilder, StrategyList)
- `/logs` (ExecutionLog)
- `/proto-*`

**verify**: import 에러 없음

### Step 5: 문서/설정 정리

**변경 파일**:
| 파일 | 변경 |
|------|------|
| CLAUDE.md | Backend 빌드 섹션 제거, 테스트 경로 갱신 |
| frontend/.env.example | VITE_API_URL 제거 |
| frontend/.env.local | VITE_API_URL 제거 |

**verify**: 문서 내 localhost:8000 참조 0건

### Step 6: 빌드 검증

```bash
cd frontend && npm run build
```

**verify**: 빌드 성공, 0 에러

## §3 추가 확인 사항

- `pages/StockList.tsx` — cloudClient 사용 여부 확인. 스텁이면 삭제 대상 추가
- `components/TemplateCard.tsx` — templates.ts에서 타입만 import. 삭제 시 타입 이동 또는 컴포넌트 삭제
- `components/Layout.tsx` — 삭제된 페이지의 사이드바 메뉴 항목 정리 필요

## §4 검증 체크리스트

- [ ] `backend/` 존재하지 않음
- [ ] 프론트엔드 스텁 5개 삭제
- [ ] 데드 페이지 7개 삭제
- [ ] App.tsx 라우트 정리
- [ ] `npm run build` 성공
- [ ] 문서 갱신
