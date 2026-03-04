# strategy-template 구현 보고서

> 작성일: 2026-03-04 | 커밋 대기

## 생성/수정 파일 목록

| 파일 | 내용 |
|------|------|
| `backend/app/models/templates.py` | `StrategyTemplate` SQLAlchemy 모델 |
| `backend/app/api/templates.py` | `GET /api/templates`, `GET /api/templates/{id}` |
| `backend/scripts/seed_templates.py` | 초기 템플릿 4개 시딩 스크립트 |
| `backend/app/main.py` | `templates_router` 등록 |
| `frontend/src/services/templates.ts` | API 클라이언트 |
| `frontend/src/components/TemplateCard.tsx` | 템플릿 카드 (백테스트 요약 + 태그 + 사용하기) |
| `frontend/src/pages/Templates.tsx` | 템플릿 브라우저 (카테고리/난이도 필터) |
| `frontend/src/App.tsx` | `/templates` 라우트 추가 |

## 주요 기능

### 백엔드
- `StrategyTemplate` 테이블: name, description, category, difficulty, rule_json (JSON), backtest_summary (JSON), tags (JSON), is_active
- SQLite 호환: `ARRAY(String)` 대신 `JSON` 타입으로 tags 저장
- `GET /api/templates` — is_active=True 목록 반환 (인증 불필요)
- `GET /api/templates/{id}` — 단건 조회, 비활성 시 404

### 초기 데이터 (4개)
1. RSI 과매도 역추세 — 초급, KOSPI RSI < 30 매수 (CAGR 12.3%, MDD -18.5%)
2. RSI 과매수 매도 — 초급, KOSPI RSI > 70 매도 (CAGR 8.7%, MDD -12.1%)
3. 저변동성 매수 — 중급, 변동성 < 0.01 매수 (CAGR 9.4%, MDD -14.2%)
4. 이중 조건 역추세 — 중급, RSI < 35 + 변동성 < 0.015 매수 (CAGR 14.1%, MDD -16.3%)

### 프론트엔드
- `TemplateCard`: CAGR/MDD/Sharpe 지표, 태그, 난이도 배지
- `Templates` 페이지: 카테고리/난이도 필터, 그리드 레이아웃
- [사용하기] → `navigate('/strategy', { state: { template } })` — StrategyBuilder에서 자동 채우기 연동 가능

## 비고
- 시딩: `cd backend && python -m scripts.seed_templates` (사용자 직접 실행)
- 관리자 CRUD (POST/PUT/DELETE /api/admin/templates)는 admin-dashboard spec에서 구현
- `StrategyBuilder` 에서 `location.state.template` 수신 시 자동 채우기 로직은 추후 연동
