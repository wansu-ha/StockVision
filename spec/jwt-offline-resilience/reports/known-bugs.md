# 기존 버그 (JWT spec 범위 밖)

## 키움 balance 파싱 버그
- **파일**: `tests/test_kiwoom_broker.py:480` — `TestKiwoomQuote::test_get_balance_positions`
- **증상**: `result.cash == Decimal('0')` (기대값 `Decimal('5000000')`)
- **원인**: 키움 응답 필드 매핑 오류 추정
- **발견일**: 2026-03-11 (Step 1 검증 중)
