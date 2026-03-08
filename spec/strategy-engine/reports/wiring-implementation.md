# Unit 3 전략 엔진 연동 구현 보고서

> 작성일: 2026-03-08

## 목표

엔진 코어 모듈(engine/)과 라우터/스토리지/WS를 연결하여 실제 동작 가능한 상태로 만든다.

## 변경 파일

### 수정
| 파일 | 변경 내용 |
|------|----------|
| `local_server/config.py` | `broker` 섹션 추가 (type, is_mock) |
| `local_server/broker/factory.py` | `create_broker_from_config()` 추가 — keyring + config 기반 |
| `local_server/routers/trading.py` | 전면 재작성 — 엔진/브로커 실제 호출, WS 콜백, logs.db 기록 |
| `local_server/routers/status.py` | app.state에서 실제 엔진/브로커 상태 읽기 |
| `local_server/engine/engine.py` | evaluate_all에 max loss 체크 추가 (logs.db 당일 실현손익) |
| `local_server/engine/executor.py` | `realized_pnl` 필드 추가, 매도 시 PnL 계산 |
| `local_server/storage/log_db.py` | `today_realized_pnl()` 메서드 추가 |
| `local_server/tests/test_engine.py` | v2 API 시그니처에 맞게 갱신 |

### 삭제
| 파일 | 사유 |
|------|------|
| `local_server/engine/signal.py` | v0 레거시, signal_manager.py로 완전 대체 |

## 연동 포인트 (이번에 완성)

1. **라우터 → 엔진**: start/stop에서 실제 engine.start()/stop() 호출
2. **라우터 → 브로커**: factory에서 config+keyring 기반 어댑터 생성, app.state에 저장
3. **엔진 → logs.db**: _on_execution 콜백에서 FILL 로그 기록 (realized_pnl 포함)
4. **엔진 → WS**: _on_execution 콜백에서 execution 이벤트 브로드캐스트
5. **Kill Switch CANCEL_OPEN**: broker.get_open_orders() → cancel_order() 루프
6. **Kill Switch OFF**: 해제 모드 추가 (수동 재개)
7. **손실 락 해제**: safeguard.unlock_loss_lock() 실제 호출
8. **수동 주문**: broker.place_order() 실제 호출
9. **Max Loss 체크**: evaluate_all에서 logs.db 당일 실현손익 → safeguard.check_max_loss()
10. **Status API**: 실제 엔진/브로커/safeguard 상태 반환

## 테스트 결과

- `local_server/tests/test_engine.py`: 41 passed
- `tests/test_kiwoom_broker.py`: 60 passed
