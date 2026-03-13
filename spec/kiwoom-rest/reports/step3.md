# Step 3 리포트: KiwoomQuote

## 생성/수정된 파일
- `local_server/broker/kiwoom/quote.py`

## 주요 구현 내용

### KiwoomQuote
- `get_price(symbol)`: GET /uapi/domestic-stock/v1/quotations/inquire-price
  - tr_id: FHKST01010100 (실전)
  - 응답 output.stck_prpr → price, output.acml_vol → volume
  - 매수/매도호가 파싱 (bidp, askp)
- `get_balance()`: GET /uapi/domestic-stock/v1/trading/inquire-balance
  - tr_id: TTTC8434R (실전)
  - output1: 종목별 보유 현황 → Position 목록
  - output2[0]: 계좌 잔고 합계 → cash, total_eval
  - 보유 수량 0인 종목 제외

### 파라미터 매핑
- 계좌번호 앞 8자리: CANO
- 계좌번호 뒤 2자리: ACNT_PRDT_CD
- Decimal 변환으로 부동소수점 정밀도 보장

## 리뷰에서 발견한 이슈 및 수정 사항
- 잔고 조회 시 output2가 빈 리스트일 수 있음 → `[{}])[0]` 기본값 처리 추가
- 모의/실전 tr_id 분기 가능하도록 `_is_mock` 플래그 추가 (현재는 실전 tr_id만 정의)

## 테스트 결과
- 구문 오류 없음 (정적 검토)
- 실제 API 호출은 Step 13 통합 테스트에서 대체

## 다음 Step과의 연결점
- Step 4 KiwoomOrder는 동일한 auth.build_headers() + httpx 패턴 사용
- Step 5 RateLimiter는 KiwoomQuote.get_price(), get_balance() 호출 전에 acquire() 삽입
