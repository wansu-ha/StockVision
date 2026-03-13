# Trading Safety — 거래 안전 버그 수정

> 작성일: 2026-03-13 | 상태: 초안

---

## 목표

실거래 시 금전 손실을 유발할 수 있는 Critical/High 이슈를 수정하여 **거래 안전성**을 확보한다.

근거 자료: `docs/research/review-local-server.md`

---

## 범위

### 포함 (9건)

Kill Switch, 주문 실행 안전장치, 손익 기록 정확성, 예산 제한 신뢰성, 브로커 TR ID.

### 미포함

- 인증/보안 → `spec/auth-security/`
- WS 재연결, asyncio → `spec/stability/`
- 미완성 기능 (KIS WS approval_key, 모의/실전 감지 등) → 별도 spec

---

## TS-1: Kill Switch → 실제 엔진 중지 (LS-C1)

**현상**: `tray_app.py:135` `_on_kill_switch()`가 `set_engine_running(False)`만 호출. safeguard를 건드리지 않아 **신규 주문이 계속 실행됨**.
**수정**:
- `_on_kill_switch()` → `_call_engine_api("kill")` 호출 (기존 헬퍼 함수 활용)
- `/api/strategy/kill` 엔드포인트에서 `safeguard.set_kill_switch(KillSwitchLevel.STOP_NEW)` 실행
**파일**: `local_server/tray/tray_app.py`, `local_server/routers/trading.py`
**검증**: 트레이 긴급 정지 → 엔진 `running=False` + safeguard 활성 확인

## TS-2: alerts 라우터 인증 추가 (LS-C2)

**현상**: GET/PUT `/api/settings/alerts`에 `require_local_secret` 없음. `master_enabled` 포함 경고 설정 무단 변경 가능.
**수정**: 두 엔드포인트에 `Depends(require_local_secret)` 추가.
**파일**: `local_server/routers/alerts.py:23, 31`
**검증**: 인증 없이 호출 → 403 확인

## TS-3: FILL 로그 타이밍 수정 (LS-H9)

**현상**: `executor.py:233` `place_order()` 반환 즉시 `LOG_TYPE_FILL` 기록. `result.status`는 `SUBMITTED`이지 `FILLED`가 아님.
**재검토**: executor.py에 ORDER(line 191/220) + FILL(line 233) 분리 기록이 이미 존재하나, FILL 기록 시점이 제출 직후(SUBMITTED)인 점은 spec 원안과 불일치.
**수정** (택 1):
- Option A: Reconciler 콜백 — `executor.py:233`의 FILL 제거, Reconciler 체결 감지 시 FILL 기록
- Option B: 현행 유지 + `LOG_TYPE_FILL`을 "제출 완료" 의미로 재정의하고 `today_realized_pnl()` 계산에 영향 없는지 확인
**파일**: `local_server/engine/executor.py`, 선택에 따라 `local_server/broker/kis/reconciler.py`
**검증**: FILL 로그 타이밍 정의가 `today_realized_pnl()` 계산과 일관

## TS-4: LimitChecker 일일 금액 복원 (LS-H4)

**현상**: `limit_checker.py:29` `_today_executed`가 인메모리, 재시작 시 항상 `Decimal(0)`.
**수정**: 엔진 시작 시 LogDB에서 당일 FILL 로그 합산으로 `_today_executed` 초기화.
**파일**: `local_server/engine/limit_checker.py`
**검증**: 엔진 재시작 후 `_today_executed` ≠ 0 (당일 체결 있을 때)

## TS-5: LimitChecker 자정 자동 리셋 (신규)

**현상**: `reset_daily()` 메서드는 있으나 호출하는 스케줄러가 없음. 서버를 하루 이상 켜두면 전날 누적 금액이 계속 쌓임.
**수정**: 엔진 평가 루프에서 날짜 경계 감지 시 `reset_daily()` 자동 호출.
**파일**: `local_server/engine/limit_checker.py`, `local_server/engine/engine.py`
**검증**: 자정 경과 후 `_today_executed` = 0 리셋 확인

## TS-6: Watchdog 엔진 참조 주입 (LS-H7)

**현상**: `main.py:144` 주석에 "엔진 시작 시 주입"이라 했으나, `trading.py` `start_strategy()`에서 `watchdog.set_engine(engine)` 호출 없음. `health_watchdog.py:106` `if self._engine is None: return`으로 항상 스킵.
**수정**: `start_strategy()` 내에서 `app.state.watchdog.set_engine(engine)` 호출.
**파일**: `local_server/routers/trading.py`, `local_server/engine/health_watchdog.py`
**검증**: 엔진 시작 후 `watchdog._engine` ≠ None

## TS-7: 수동 주문 safeguard 체크 누락 (신규)

**현상**: `trading.py:248` `/api/trading/order` 수동 주문에 `safeguard.is_trading_enabled()` 체크 없음. Kill Switch 활성 중에도 수동 주문 통과.
**수정**: `place_order()` 진입부에 safeguard 체크 추가. Kill Switch 활성 시 400 반환.
**파일**: `local_server/routers/trading.py`
**검증**: Kill Switch 활성 → 수동 주문 → 400 응답

## TS-8: KIS 모의투자 TR ID 미분기 (LS-H3 재분류)

**현상**: `order.py:57` `_is_mock` 필드 저장만 하고, TR ID 선택 시 모의투자 TR ID(`VTTT*`)로 전환하는 로직 없음. 모의투자에서 실전 TR ID 사용 → 주문 거부.
**수정**: `_get_tr_id()` 내에서 `is_mock=True`이면 `V` 접두어 TR ID 사용.
**파일**: `local_server/broker/kis/order.py`
**검증**: 모의투자 환경에서 매수/매도 주문 성공

## TS-9: KIS 매도 시장가 TR ID 검증 (LS-H3)

**현상**: `TTTC0801U`가 매도 시장가에 올바른지 KIS 문서 재확인 필요. 코드 주석에 "동일 tr_id, ord_dvsn으로 구분"이라 의도적 설계로 보이나 KIS 공식 문서와 대조 필요.
**수정**: KIS API 문서 확인 후 필요시 수정. 이미 올바르면 이슈 해제.
**파일**: `local_server/broker/kis/order.py:25-30`
**검증**: KIS 모의투자에서 매도 시장가 주문 성공

---

## 수용 기준

- [ ] 트레이 Kill Switch → 엔진 실제 중지 + safeguard 활성
- [ ] alerts 엔드포인트 인증 필수
- [ ] FILL 로그 타이밍 정의 명확 (Option A 또는 B 선택 후 일관 적용)
- [ ] LimitChecker 재시작 후 당일 금액 복원
- [ ] LimitChecker 자정 자동 리셋
- [ ] Watchdog 엔진 하트비트 체크 동작
- [ ] 수동 주문도 safeguard 체크 적용
- [ ] KIS 모의투자 TR ID 올바르게 전환
- [ ] KIS 매도 시장가 TR ID 정확

---

## API 변경

### 새 엔드포인트
- `POST /api/strategy/kill` — 긴급 정지, safeguard 활성화 (이미 존재할 수 있음 — 확인 후 추가)

---

## 참고 파일

- `local_server/tray/tray_app.py` — Kill Switch (TS-1)
- `local_server/routers/alerts.py` — 인증 누락 (TS-2)
- `local_server/engine/executor.py` — FILL 로그 (TS-3)
- `local_server/engine/limit_checker.py` — 일일 예산 (TS-4, TS-5)
- `local_server/engine/engine.py` — 날짜 경계 (TS-5)
- `local_server/engine/health_watchdog.py` — Watchdog (TS-6)
- `local_server/routers/trading.py` — Watchdog 주입 + 수동 주문 (TS-6, TS-7)
- `local_server/broker/kis/order.py` — TR ID (TS-8, TS-9)
- `docs/research/review-local-server.md` — 근거 자료
