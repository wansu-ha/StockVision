# portfolio 구현 보고서

> 작성일: 2026-03-04 | 커밋 대기

## 생성/수정 파일 목록

| 파일 | 내용 |
|------|------|
| `backend/app/services/portfolio.py` | 포트폴리오 집계, equity curve, 섹터 배분 (yfinance 5분 캐시) |
| `backend/app/api/portfolio.py` | `GET /api/v1/portfolio/{id}`, `/equity-curve`, `/sector-allocation` |
| `backend/app/main.py` | portfolio_router 등록 |
| `frontend/src/services/portfolio.ts` | 포트폴리오 API 클라이언트 |
| `frontend/src/pages/Portfolio.tsx` | 포트폴리오 페이지 (요약 카드 + LineChart + PieChart + 보유 종목 테이블) |
| `frontend/src/App.tsx` | `/portfolio` 라우트 추가 |

## 주요 기능

### API
- `GET /api/v1/portfolio/{account_id}` — 총 자산, 예수금, 포지션별 현재가/손익/비중
- `GET /api/v1/portfolio/{account_id}/equity-curve?period=7d|30d|90d|180d` — 일별 자산 변화
- `GET /api/v1/portfolio/{account_id}/sector-allocation` — 섹터별 비중

### 현재가 조회
- yfinance `fast_info.last_price` 사용
- 종목당 5분 메모리 캐시

### React UI
- 요약 카드 4개 (총 자산, 예수금, 평가금액, 총 손익)
- Recharts LineChart — equity curve (기간 토글)
- Recharts PieChart — 섹터별 자산 배분
- 보유 종목 테이블 (수량, 평균가, 현재가, 손익, 비중)

## 비고
- 현재 ACCOUNT_ID = 1 하드코딩 (계좌 선택 UI는 onboarding spec에서 추가 예정)
- `get_db` → `app.core.database`에서 임포트 (dependencies.py에 없음)
- 전략 기여도 분석(Step 3)은 실전 연동 후 추가 예정
