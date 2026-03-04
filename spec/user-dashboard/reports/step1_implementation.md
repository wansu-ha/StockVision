# user-dashboard 구현 보고서

> 작성일: 2026-03-04 | 커밋 대기

## 생성/수정 파일 목록

| 파일 | 내용 |
|------|------|
| `local_server/routers/health.py` | `GET /api/dashboard` 통합 API 추가 |
| `frontend/src/services/dashboard.ts` | 로컬 브릿지 대시보드 API 클라이언트 |
| `frontend/src/components/BridgeStatus.tsx` | 브릿지 연결 상태 + 요약 표시 바 |
| `frontend/src/components/MarketContext.tsx` | 시장 컨텍스트 카드 (RSI, 추세) |
| `frontend/src/pages/Dashboard.tsx` | BridgeStatus 바 추가 (최상단) |

## 주요 기능

### /api/dashboard 통합 API
- 키움 연결 상태 + 활성 전략 수 + 오늘 실행 요약 + 시장 컨텍스트 + 최근 로그 5건

### BridgeStatus 컴포넌트
- 10초 폴링, retry: false (로컬 서버 없으면 빨간 상태)
- 연결 시: 녹색 + 모의/실계좌 표시 + 전략 수 + 오늘 체결 수 + 로그/전략 링크
- 미연결 시: 빨간 "브릿지 미연결" 표시

### MarketContext 컴포넌트
- KOSPI RSI(14) 값 + 과매도/과매수 색상 표시
- 시장 흐름: bullish/bearish/neutral → 한국어

## 비고
- BridgeStatus를 Dashboard.tsx Hero 위에 최소한으로 삽입 (기존 UI 미변경)
- MarketContext는 독립 컴포넌트 — 필요한 페이지에서 import해서 사용
