# 키움 모의서버 검증 보고서

> 작성일: 2026-03-08

## 환경

- 서버: `https://mockapi.kiwoom.com` (모의투자)
- 자격증명: keyring `stockvision:test@stockvision.dev`
- 테스트: `tests/test_kiwoom_broker.py` (mock 60개), `tests/test_kiwoom_live.py` (모의서버 13개)

## 결과: 72 passed, 1 skipped

| 카테고리 | 결과 | 비고 |
|----------|:----:|------|
| F1 토큰 발급/캐싱/재발급 | PASS | |
| F2 모의/실전 URL 전환 | PASS | |
| F3 주문 API 통신 | PASS | `RC4010` 모의서버 주문가능 종목 제한 (API 포맷 정상) |
| F4 현재가 → Decimal | PASS | 삼성전자 188,200원 |
| F5 잔고 조회 | PASS | 빈 계좌 (모의) |
| F6-F7 WebSocket | SKIP | 모의서버 미지원 (timeout) |
| R1 RateLimiter 경유 | PASS | mock 검증 |
| R2 StateMachine 전환 | PASS | mock 검증 |
| R4 Reconciler 대사 | PASS | mock 검증 |
| R5 IdempotencyGuard | PASS | mock 검증 |
| R6 ErrorClassifier | PASS | mock 검증 |

## 발견된 버그 (수정 완료)

리서치 문서(`docs/research/kiwoom-rest-api-spec.md`)의 명세가 실제 API와 불일치:

| 필드 | 리서치 문서 | 실제 API |
|------|------------|----------|
| `dmst_stex_tp` | `"01"` KOSPI, `"02"` KOSDAQ | `"KRX"`, `"NXT"`, `"SOR"` |
| `trde_tp` | `"00"` 지정가, `"01"` 시장가 | `"0"` 보통/지정가, `"3"` 시장가 |
| `ord_qty`, `ord_uv` | int | str (API가 문자열 기대) |

수정 파일: `local_server/broker/kiwoom/order.py`

## 미검증 (실전 서버 필요)

- WS 연결/구독/체결통보 (모의서버 미지원)
- 실제 주문 체결 (모의서버 종목 제한)
