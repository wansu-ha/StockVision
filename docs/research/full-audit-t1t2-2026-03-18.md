# T1/T2 전체 코드 감사 보고서

> 작성일: 2026-03-18 | 감사 범위: T1 (5개 항목) + T2 (3개 항목)

---

## T1-1: IndicatorProvider

### 항목 1 — `local_server/engine/indicator_provider.py`

**EXISTS (완전 구현)**

- 클래스: `IndicatorProvider` (L23-52)
- 메서드: `refresh(symbols)`, `get(symbol)`, `_is_stale()`, `_fetch_and_calc_batch()`, `_fetch_and_calc()`
- 계산 함수: `_calc_rsi`, `_calc_sma`, `_calc_ema`, `_calc_macd`, `_calc_bollinger`, `_calc_avg_volume`
- 반환 지표: rsi_14, rsi_21, ma_5/10/20/60, ema_12/20/26, macd, macd_signal, bb_upper_20, bb_lower_20, avg_volume_20
- 캐시: 1일 유효 (`_is_stale`에서 `date.today()` 비교)

### 항목 2 — `local_server/engine/engine.py`에서의 통합

**EXISTS (완전 통합)**

- import: L18 `from local_server.engine.indicator_provider import IndicatorProvider`
- 인스턴스 생성: L71 `self._indicator_provider = IndicatorProvider()`
- `start()`에서 활성 종목 refresh: L101-102 `await self._indicator_provider.refresh(symbols)`
- `_collect_candidates()`에서 지표 주입: L322 `latest["indicators"] = self._indicator_provider.get(symbol)`
- evaluator에 indicators가 market_data dict에 포함되어 전달됨

### 항목 3 — KOSDAQ 티커 이슈

**EXISTS (버그 확인)**

- `_to_yf_ticker()` (L90-98):
  ```python
  def _to_yf_ticker(symbol: str) -> str:
      if "." in symbol:
          return symbol  # 이미 yfinance 형식
      return f"{symbol}.KS"
  ```
- **문제**: KOSDAQ 종목도 항상 `.KS` (KOSPI) suffix 사용. `.KQ` (KOSDAQ) 분기 없음.
- 주석(L93-94)에 "KOSPI: .KS, KOSDAQ: .KQ" 언급하지만 실제 코드는 `.KS` 고정.
- KOSDAQ 종목의 일봉 지표가 조회 실패하거나 잘못된 데이터 반환 가능.

### 항목 4 — `local_server/requirements.txt` 의존성

**EXISTS**

- L10: `pandas>=2.2.0         # 지표 계산`
- L11: `numpy>=2.0.0          # pandas 의존`
- L12: `yfinance>=0.2.40      # 일봉 데이터 조회`
- L13: `packaging>=24.0       # 버전 비교 (heartbeat)`

### 항목 5 — Heartbeat 버전 비교 타입 불일치

**NOT EXISTS (수정 완료)**

- `heartbeat.py` L122-130: 버전 비교 시 `str()` 변환으로 통일:
  ```python
  if resp.get("rules_version") is not None:
      last_rules_version = str(resp["rules_version"])
  ```
- `_check_version_changes()` (L206-254): 모든 버전을 `str()` 캐스트 후 문자열 비교.
- L122 주석: "cloud가 int를 보내도 str로 통일"
- **결론**: 타입 불일치 버그는 이미 해결됨.

---

## T1-2: DSL Parser

### 항목 6 — Frontend DSL 파서

**EXISTS (완전 구현)**

파일 2개:

1. **`frontend/src/utils/dslParser.ts`** (256줄)
   - `tokenize()`: 렉서 — KEYWORD(매수/매도), COLON, IDENT, NUMBER, OP(>=,<=,!=,==,>,<), AND, OR, NEWLINE, EOF
   - `parseDsl()`: 파서 — `매수: field op value AND field op value\n매도: ...` 형식
   - 타입: `Token`, `ParseError`, `ParsedCondition`, `ConditionGroup`, `ParseResult`
   - 에러 복원: 파싱 오류 시 errors 배열에 수집, 파싱된 만큼 반환

2. **`frontend/src/utils/dslConverter.ts`** (57줄)
   - `dslToConditions()`: DSL 문자열 → 앱 Condition 배열
   - `conditionsToDsl`: 역방향 변환 (services/rules.ts에서 import)
   - `DslConvertResult` 인터페이스: success, buyConditions, sellConditions, operator, errors

---

## T1-3: Chart Backend

### 항목 7 — `local_server/storage/minute_bar.py`, `local_server/routers/bars.py`

**EXISTS (완전 구현)**

- **`minute_bar.py`** (170줄):
  - `MinuteBarStore`: SQLite 기반, 1분봉 CRUD (`save_bars`, `get_bars`, `get_range`, `purge_old`)
  - `aggregate_bars()`: 1분봉 → 5m/15m/1h 집계 (L106-147)
  - 싱글턴: `get_minute_bar_store()`

- **`bars.py`** (39줄):
  - `GET /api/v1/bars/{symbol}?resolution=1m&start=...&end=...`
  - resolution 패턴: `^(1m|5m|15m|1h)$` (L18)
  - 1m이 아닌 경우 `aggregate_bars()` 호출 (L27-28)
  - `require_local_secret` 인증 (L21)

### 항목 8 — `cloud_server/api/market_data.py` resolution 지원

**EXISTS (완전 구현)**

- `GET /api/v1/stocks/{symbol}/bars` (L26-108)
- resolution 패턴: `^(1d|1w|1mo)$` (L31)
- 일봉 → 주봉/월봉 집계: `_aggregate_daily_bars()` (L111-141)
  - 1w: `isocalendar()` 기반 주간 그룹핑
  - 1mo: 년-월 기반 월간 그룹핑
- DB 캐시 + on-demand yfinance 수집 폴백

---

## T1-4: Chart Frontend

### 항목 9 — `frontend/src/components/main/PriceChart.tsx`

**EXISTS (완전 구현, 453줄)**

- **해상도 옵션** (L28-42):
  - 로컬(분봉): 1m, 5m, 15m, 1h (source: 'local')
  - 클라우드(일봉+): 1d, 1w, 1mo (source: 'cloud')
  - `ResolutionOption` 타입으로 source 분기

- **데이터 소스 분기** (L295-310):
  - `isIntraday` 분기 → `cloudBars.get()` vs `localBars.get()`
  - React Query로 각각 별도 queryKey

- **Lazy Load** (L179-218, 256-273):
  - `loadedRangeRef`로 로드된 범위 추적
  - `fetchMoreBars()`: 좌측 스크롤 시 30일분 추가 로드
  - `subscribeVisibleTimeRangeChange`로 좌측 끝 도달 감지
  - 250ms 디바운스

- **차트 타입** (L17-25): candle, hollow, heikin, ohlc, line
- **기간 선택** (L44-50): 1W, 1M, 3M, 6M, 1Y
- **이벤트 마커** (L125-158): 체결 로그 기반 매수/매도 화살표
- **볼륨 바** (L244-248): HistogramSeries, 양/음 색상 구분

---

## T1-5: Resilience

### 항목 10 — R1 Config Atomic Write

**EXISTS (완전 구현)**

- `local_server/config.py` L96-117:
  ```python
  def save(self) -> None:
      fd, tmp_path = tempfile.mkstemp(
          dir=str(self._path.parent), suffix=".tmp", prefix=".config-",
      )
      try:
          with os.fdopen(fd, "w", encoding="utf-8") as f:
              json.dump(self._data, f, ensure_ascii=False, indent=2)
          os.replace(tmp_path, str(self._path))
      except Exception:
          with contextlib.suppress(OSError):
              os.unlink(tmp_path)
          raise
  ```
- `tempfile.mkstemp` → `os.replace` 패턴으로 atomic write 구현.

### 항목 11 — R2 Mock Auto-Detect

**EXISTS (완전 구현)**

- `local_server/broker/factory.py`:
  - `_detect_mock_mode()` (L145-160):
    - KIS: 계좌번호 앞 2자리 "50"이면 모의투자
    - Kiwoom: base_url에 "mock"/"virtual" 포함이면 모의투자
  - `create_broker_from_config()` (L163-230):
    - 자동 감지 결과와 수동 설정 불일치 시 경고 + 자동감지 값 사용
    - `cfg.set("broker.is_mock", auto_detected)` + `cfg.save()`로 설정 갱신

### 항목 12 — R3 SyncQueue

**EXISTS (완전 구현)**

- `local_server/storage/sync_queue.py` (105줄):
  - `SyncQueue` 클래스: JSON 파일 기반 (`sync_queue.json`)
  - `enqueue()`, `dequeue()`, `peek_all()`, `clear()`, `is_empty()`, `count()`
  - `MAX_QUEUE_SIZE = 100` 초과 시 오래된 항목 제거
  - `ActionType`: rule_create/update/delete, watchlist_add/remove
  - `heartbeat.py`에서 `_flush_sync_queue()` (L309-333)로 연결 복구 시 플러시

- **주의**: `_save()` (L51-54)는 atomic write 미사용 (직접 `open/write`). Config와 달리 sync_queue는 `tempfile+os.replace` 미적용.

### 항목 13 — R5 LimitChecker `restore_from_db()`

**EXISTS (완전 구현)**

- `local_server/engine/limit_checker.py` L77-81:
  ```python
  def restore_from_db(self, log_db: LogDB) -> None:
      self._today_executed = log_db.today_executed_amount()
      self._last_date = date.today()
  ```
- `engine.py` L96-97에서 시작 시 호출:
  ```python
  from local_server.storage.log_db import get_log_db
  self._limit_checker.restore_from_db(get_log_db())
  ```
- `check_date_boundary()` (L83-88): 날짜 경계 감지 시 자동 리셋

---

## T2: relay-infra

### 항목 14 — `cloud_server/api/ws_relay.py`

**EXISTS (완전 구현, 136줄)**

- `/ws/relay` (L61-86): 로컬 서버 전용
  - auth 첫 메시지 → JWT 검증 → `register_local`
  - 재연결 시 `flush_pending_commands()`
  - 무한 recv 루프 → `relay.handle_local_message()`
  - disconnect 시 `unregister_local`

- `/ws/remote` (L89-135): 원격 디바이스 전용
  - auth + device_id 필수
  - JWT 만료 추적 (`jwt_exp` 전달)
  - `re_auth` 메시지로 JWT 갱신
  - `pong` 무시, `command` → relay
  - max devices 초과 시 4003 close

- `_wait_auth()` (L26-58): 10초 타임아웃, query string 대신 첫 메시지 패턴

### 항목 15 — `cloud_server/services/session_manager.py`

**EXISTS (완전 구현, 158줄)**

- **ping/pong**: `_ping_loop()` (L89-116)
  - 30초 간격 ping 전송 (`{"type": "ping", "ts": ...}`)
  - 전송 실패 시 세션 종료
  - **참고**: pong 타임아웃 미검사 — `PONG_TIMEOUT = 10` 상수 정의만 있고, 실제 pong 도착 대기/타임아웃 로직 없음 (ping 전송 실패로만 감지)

- **JWT 만료 추적**: L97-106
  - `_jwt_exp` dict에 epoch timestamp 저장
  - ping_loop에서 `time.time() > exp` 검사 → `auth_expired` 전송 + close(4004)
  - `refresh_jwt()` 메서드로 갱신 가능

- **동시 접속 제한**: `MAX_DEVICES_PER_USER = 5`
- **브로드캐스트**: `broadcast_to_devices()`, dead 세션 자동 정리
- **세션 킬**: `kill_session()` — 강제 종료 + unregister

### 항목 16 — `cloud_server/services/relay_manager.py`

**EXISTS (완전 구현, 283줄)**

- **RateLimiter** (L21-56):
  - `max_commands_per_min=10`, `max_total_per_min=60`
  - user_id 기반, 1분 윈도우 슬라이딩

- **PendingCommand**:
  - `_save_pending_command()` (L222-239): DB 저장 (`cloud_server/models/pending_command.py` 확인됨)
  - `flush_pending_commands()` (L137-167): 재연결 시 pending 큐 순서대로 flush
  - 실행 후 `status = "executed"`, `executed_at` 갱신

- **AuditLog**:
  - `_write_audit_log()` (L241-260): DB 저장 (`cloud_server/models/audit_log.py` 확인됨)
  - command, sync_request 타입에 대해 기록

- **메시지 라우팅**:
  - `handle_local_message()`: heartbeat, state, alert, command_ack
  - `handle_device_message()`: command, sync_request, ack
  - `_handle_heartbeat()`: HeartbeatService 호출 → ack 응답

### 항목 17 — `local_server/cloud/ws_relay_client.py` heartbeat_ack 처리

**PARTIAL (로깅만)**

- `_handle_heartbeat_ack()` (L189-193):
  ```python
  def _handle_heartbeat_ack(self, msg: dict) -> None:
      """heartbeat_ack 처리 → 버전 체크는 heartbeat 모듈에 위임."""
      # heartbeat 모듈에서 이 데이터를 polling 대신 받을 수 있도록
      # 이벤트나 콜백으로 전달할 수 있음. 초기에는 로깅만.
      logger.debug("heartbeat_ack 수신")
  ```
- **문제**: payload에서 versions(rules_version, context_version 등)을 파싱하지 않음. 로깅만 하고 버전 데이터를 버림.
- heartbeat.py의 `_check_version_changes()`는 HTTP 응답에서만 버전 체크 (L111: `resp = None` when WS). WS 경로에서는 버전 변경 감지 불가.

---

## T2: R4 Heartbeat WS Ack

### 항목 18 — `_handle_heartbeat_ack` 상태

**PARTIAL (로깅만, 미구현)**

- 위 항목 17과 동일. L189-193에서 로깅만 수행.
- WS heartbeat 경로 (L101-106):
  ```python
  if ws_client and ws_client.is_connected:
      await ws_client.send_heartbeat(payload)
      resp = None  # ← ack 응답을 받지 않음
  ```
- HTTP 폴백 경로에서만 `resp`가 설정되어 `_check_version_changes()` 호출됨.

### 항목 19 — heartbeat.py 콜백 메커니즘

**NOT EXISTS**

- `heartbeat.py`에 WS 버전 변경 콜백 등록 메커니즘 없음.
- `ws_relay_client.py`에도 콜백 필드/setter 없음 (command_handler만 존재).
- WS heartbeat_ack → 버전 비교 → fetch 트리거 파이프라인이 연결되지 않음.
- **결론**: WS를 통한 heartbeat ack 버전 체크는 아키텍처적으로 설계되었으나 실제 구현은 HTTP 폴백에만 작동.

---

## T2: E2E Crypto

### 항목 20 — E2E 암호화 구현

**PARTIAL**

- **`sv_core/e2e_crypto.py`**: **NOT EXISTS** — 파일 없음. Python 서버 측 암호화 모듈 미구현.
- **`frontend/src/utils/e2eCrypto.ts`**: **EXISTS (완전 구현, 123줄)**
  - 복호화 전용 (AES-256-GCM)
  - IndexedDB 키 저장: `saveDeviceKey()`, `loadDeviceKey()`, `deleteDeviceKey()`, `getStoredDeviceId()`
  - `decrypt()`: base64 → ArrayBuffer → Web Crypto API `subtle.decrypt`
  - ciphertext + tag 연결 방식 (GCM 표준)

- **결론**: 프론트엔드 복호화만 구현. 서버 측 암호화(`sv_core/e2e_crypto.py`)가 없어 실제 E2E 암호화 파이프라인은 동작하지 않음.

---

## 요약 테이블

| # | 항목 | 상태 | 비고 |
|---|------|------|------|
| 1 | IndicatorProvider 파일 | **EXISTS** | 190줄, 전체 지표 계산 |
| 2 | Engine 통합 | **EXISTS** | refresh + get + evaluator 연결 완료 |
| 3 | KOSDAQ 티커 이슈 | **EXISTS (버그)** | `.KS` 고정, `.KQ` 분기 없음 |
| 4 | requirements.txt | **EXISTS** | pandas, numpy, yfinance, packaging |
| 5 | 버전 비교 타입 불일치 | **NOT EXISTS (수정됨)** | str() 변환으로 해결 |
| 6 | DSL Parser | **EXISTS** | lexer+parser+converter 완전 구현 |
| 7 | Chart Backend (분봉) | **EXISTS** | minute_bar.py + bars.py 완전 구현 |
| 8 | Chart Backend (일봉) | **EXISTS** | market_data.py resolution 1d/1w/1mo |
| 9 | Chart Frontend | **EXISTS** | 해상도 7종, lazy load, 소스 분기 |
| 10 | R1 Atomic Write | **EXISTS** | tempfile + os.replace |
| 11 | R2 Mock Auto-Detect | **EXISTS** | KIS 계좌번호 + Kiwoom URL 패턴 |
| 12 | R3 SyncQueue | **EXISTS** | JSON 파일, MAX 100, flush 연결됨 |
| 13 | R5 LimitChecker restore | **EXISTS** | restore_from_db + date boundary |
| 14 | WS /relay + /remote | **EXISTS** | auth, routing, pending flush 완전 |
| 15 | SessionManager | **EXISTS** | ping/pong, JWT 만료, broadcast |
| 16 | RelayManager | **EXISTS** | PendingCommand, AuditLog, RateLimiter |
| 17 | ws_relay_client ack 파싱 | **PARTIAL** | 로깅만, versions 미파싱 |
| 18 | heartbeat_ack WS 경로 | **PARTIAL** | resp=None, HTTP에서만 버전 체크 |
| 19 | heartbeat 콜백 메커니즘 | **NOT EXISTS** | WS→버전체크 파이프라인 미연결 |
| 20 | E2E Crypto | **PARTIAL** | FE 복호화만, sv_core 암호화 없음 |

## 잔존 이슈 (수정 필요)

1. **KOSDAQ 티커** (`indicator_provider.py` L98): `.KQ` 분기 필요
2. **WS heartbeat_ack 버전 체크** (`ws_relay_client.py` L189-193 + `heartbeat.py` L101-106): 콜백 파이프라인 구현 필요
3. **sv_core/e2e_crypto.py**: 서버 측 AES-256-GCM 암호화 모듈 미구현
4. **SyncQueue atomic write**: `sync_queue.py` L51-54는 직접 write (Config처럼 atomic 미적용)
5. **SessionManager pong 타임아웃**: `PONG_TIMEOUT=10` 상수만 정의, 실제 pong 대기 로직 없음
