# StockVision 로드맵

## Phase 1 — 기반 구축 (완료)
- 데이터 수집 (yfinance)
- 기술적 지표 계산 (RSI, EMA, MACD, 볼린저밴드)
- RF 예측 모델
- 프론트엔드 기본 페이지 (Dashboard, StockDetail, StockList)
- 캐싱, 로깅 인프라

## Phase 2 — 가상 자동매매 시스템 (현재)
- 가상 거래 엔진 (매수/매도/포지션 관리)
- 스코어링 엔진 (기술적 지표 + RF 예측)
- 백테스팅 엔진
- 자동매매 스케줄러
- 키움증권 REST API 연동 (모의투자 시세)
- 거래 관련 프론트엔드 UI
- spec: `spec/virtual-auto-trading/spec.md`

## Phase 3 — AI 고도화
- LSTM 시계열 예측 모델
- 앙상블 모델 (RF + LSTM + SVM)
- AI 전략 리뷰 시스템 (Claude API 활용, 전략 분석/수정 제안)

## Phase 4 — 실전 매매 연동
- 키움증권 REST API 실전 계좌 매매 실행
- 리스크 관리 시스템 (손절/익절, 최대 손실 한도)
- 실시간 WebSocket 데이터 스트리밍

## Phase 5 — 운영 안정화
- 사용자 인증/권한 시스템
- 알림 시스템 (텔레그램 봇)
- 모니터링/대시보드 고도화
- 프로덕션 배포 (Docker, PostgreSQL)
