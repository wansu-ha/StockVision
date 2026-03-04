# data-source 구현 보고서

> 작성일: 2026-03-04 | 커밋 대기

## 생성/수정 파일 목록

| 파일 | 내용 |
|------|------|
| `backend/app/services/data_collector.py` | `collect_stock_prices` 재시도 3회 지수 백오프 + 결측 거래일 탐지 |

## 주요 기능

### yfinance 안정화

**재시도 로직**
- 최대 3회 시도 (2초, 4초 간격 지수 백오프)
- 최종 실패 시 빈 DataFrame 반환 + ERROR 로그
- 각 재시도마다 WARN 로그 (시도 횟수 포함)

**결측 거래일 탐지**
- `pd.bdate_range()` 기준 영업일 수 vs 수집 레코드 수 비교
- 결측 일자 발생 시 WARN 로그

**기존 유지 사항**
- `to_yfinance_symbol()`: 6자리 한국 심볼 → `.KS` 자동 변환 (기존)
- rate_limit_monitor / api_logger_instance 호출 순서 유지

## 비고
- Step 2 (market_context.py + context API): context-cloud spec 구현 시 완료
- Step 3 (키움 실시간): kiwoom-integration spec 구현 시 완료 (G5 제5조③ 준수)
- `collect_stock_info()`의 재시도는 낮은 우선순위로 추후 적용 가능
