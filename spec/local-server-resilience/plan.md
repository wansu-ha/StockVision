# 로컬 서버 견고성 — 구현 계획

> 작성일: 2026-03-16 | 상태: 확정 | spec: `spec/local-server-resilience/spec.md`

## 의존관계

```
R1 (Config Atomic Write)  ─── 독립
R2 (Mock 자동감지)         ─── 독립
R3 (SyncQueue 연동)        ─── 독립 (heartbeat 복구 감지에서 flush)
R4 (Heartbeat 버전 파싱)   ─── ⚠️ relay-infra 의존 → Phase C로 이동
R5 (LimitChecker 복원)     ─── 독립

→ R1, R2, R3, R5 병렬 가능. R4는 Phase C.
```

## Step 1: Config Atomic Write (R1)

**파일**: `local_server/config.py` (수정)

현재 `save()` (line 95-99)가 파일을 직접 덮어쓴다. 임시 파일 → atomic rename으로 변경.

```python
import tempfile

def save(self) -> None:
    self._path.parent.mkdir(parents=True, exist_ok=True)
    # 같은 디렉터리에 임시 파일 생성 (같은 파일시스템 보장)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(self._path.parent),
        suffix=".tmp",
        prefix=".config-",
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, str(self._path))  # atomic on same FS
    except Exception:
        # 실패 시 임시 파일 정리
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        raise
```

**검증**:
- [ ] 정상 저장 시 config.json 내용 정확
- [ ] 쓰기 중 프로세스 종료 시 기존 파일 무손상
- [ ] Windows/Linux 모두 `os.replace` 동작

## Step 2: Mock/실전 자동 감지 (R2)

**파일**: `local_server/broker/factory.py` (수정)

### 2.1 감지 로직

```python
def _detect_mock_mode(broker_type: str, credentials: dict) -> bool | None:
    """계좌번호 패턴으로 mock/실전 자동 판별. 판별 불가 시 None."""
    account = credentials.get("account_number", "")
    if broker_type == BROKER_TYPE_KIS:
        # KIS 모의: 계좌번호가 "50" 또는 "00"으로 시작하는 패턴 (KIS 문서 확인 필요)
        # 실전: 8자리 숫자-2자리
        return None  # KIS 패턴 확정 후 구현
    elif broker_type == BROKER_TYPE_KIWOOM:
        # 키움: 모의서버 base_url이 다름 (이미 구분됨)
        base_url = credentials.get("base_url", "")
        return "mock" in base_url.lower() or "virtual" in base_url.lower()
    return None
```

### 2.2 팩토리에 경고 통합

```python
# factory.py create_broker_from_config() 내부
auto_detected = _detect_mock_mode(broker_type, credentials)
manual_setting = cfg.get("broker.is_mock", True)

if auto_detected is not None and auto_detected != manual_setting:
    logger.warning(
        "⚠️ mock 설정 불일치: 수동=%s, 자동감지=%s — 자동감지 값 사용",
        manual_setting, auto_detected,
    )
    is_mock = auto_detected
    cfg.set("broker.is_mock", auto_detected)
    cfg.save()
else:
    is_mock = manual_setting
```

**검증**:
- [ ] 키움 모의서버 URL → `is_mock=True` 자동 설정
- [ ] 수동 설정과 불일치 시 경고 로그 출력
- [ ] 자동감지 실패 시 수동 설정 폴백

## Step 3: Heartbeat WS Ack 버전 파싱 (R4) — ⚠️ Phase C로 이동

> **relay-infra가 ws_relay_client.py를 전면 재작성하므로, 이 Step은 relay-infra 완료 후 Phase C에서 구현한다.**
> 아래 설계는 참고용으로 유지한다.

**파일**: `local_server/cloud/ws_relay_client.py` (수정), `local_server/cloud/heartbeat.py` (수정)

### 3.1 heartbeat.py에서 버전 체크 함수 분리

현재 `_check_version_changes()`는 HTTP 응답 dict를 받는다. WS ack도 같은 형식이므로 재활용.

```python
# heartbeat.py — 기존 함수를 public으로 노출
def check_version_changes(response: dict) -> None:
    """규칙/컨텍스트/관심종목 버전 변경 감지 → fetch 트리거."""
    # 기존 _check_version_changes() 로직 그대로
```

### 3.2 ws_relay_client에서 버전 파싱

```python
# ws_relay_client.py
from local_server.cloud.heartbeat import check_version_changes

def _handle_heartbeat_ack(self, msg: dict) -> None:
    payload = msg.get("payload", {})
    if payload:
        check_version_changes(payload)
    logger.debug("heartbeat_ack 수신 (버전 체크 완료)")
```

**검증**:
- [ ] WS heartbeat_ack에 규칙 버전 변경 시 자동 fetch 실행
- [ ] HTTP heartbeat 기존 동작 유지
- [ ] 버전 필드 없는 ack도 에러 없이 처리

## Step 4: SyncQueue 연동 (R3)

**파일**: `local_server/routers/rules.py` (수정), `local_server/cloud/heartbeat.py` (수정), `local_server/storage/sync_queue.py` (수정)

### 4.1 SyncQueue 크기 제한 추가

```python
# sync_queue.py
MAX_QUEUE_SIZE = 100

def enqueue(self, action_type: str, data: dict) -> None:
    # 크기 초과 시 오래된 것부터 제거
    while len(self._queue) >= MAX_QUEUE_SIZE:
        removed = self._queue.pop(0)
        logger.warning("SyncQueue 초과 — 오래된 항목 제거: %s", removed["type"])
    # 기존 enqueue 로직
```

### 4.2 규칙 동기화 실패 시 enqueue

```python
# routers/rules.py sync_rules()
try:
    rules = await client.fetch_rules()
except Exception as e:
    # 클라우드 연결 실패 → SyncQueue에 적재
    from local_server.storage.sync_queue import get_sync_queue
    get_sync_queue().enqueue("rule_sync_failed", {"error": str(e)})
    raise HTTPException(...) from e
```

### 4.3 Heartbeat 복구 시 flush

```python
# heartbeat.py — 연결 복구 감지 후
async def _flush_sync_queue() -> None:
    queue = get_sync_queue()
    while not queue.is_empty():
        item = queue.peek_all()[0]
        try:
            await _process_queued_item(item)
            queue.dequeue()
        except Exception:
            logger.error("SyncQueue flush 실패 — 재시도 보류")
            break
```

**검증**:
- [ ] 클라우드 연결 실패 시 큐에 항목 저장
- [ ] 재연결 시 큐 자동 플러시
- [ ] 큐 크기 100건 초과 시 오래된 항목 제거
- [ ] 플러시 실패 시 항목 잔류

## Step 5: LimitChecker 재시작 복원 (R5)

**파일**: `local_server/engine/limit_checker.py` (수정)

### 5.1 시작 시 LogDB 조회

```python
# limit_checker.py
from local_server.storage.log_db import get_log_db
from datetime import date

class LimitChecker:
    def __init__(self, ...):
        self.today_executed: dict[int, int] = {}
        self._restore_from_log_db()

    def _restore_from_log_db(self) -> None:
        """서버 재시작 시 오늘 체결 로그에서 today_executed 복원."""
        try:
            log_db = get_log_db()
            today_logs = log_db.get_execution_logs(date=date.today())
            for log in today_logs:
                rule_id = log.get("rule_id")
                if rule_id is not None:
                    self.today_executed[rule_id] = self.today_executed.get(rule_id, 0) + 1
            if self.today_executed:
                logger.info(
                    "LimitChecker 복원: %d건 규칙의 실행 횟수 로드",
                    len(self.today_executed),
                )
        except Exception as e:
            logger.warning("LimitChecker 복원 실패 (0에서 시작): %s", e)
```

**검증**:
- [ ] 서버 재시작 후 `today_executed`가 LogDB 기반으로 복원
- [ ] LogDB 접근 실패 시 0에서 시작 (기존 동작 폴백)
- [ ] 장 종료 후 초기화 동작 유지

## 변경 파일 요약

| 파일 | Step | 변경 |
|------|------|------|
| `local_server/config.py` | R1 | atomic write |
| `local_server/broker/factory.py` | R2 | mock 자동감지 |
| `local_server/cloud/heartbeat.py` | R3 | 복구 시 flush |
| `local_server/cloud/ws_relay_client.py` | R4 | ack 버전 파싱 (**Phase C**) |
| `local_server/routers/rules.py` | R3 | 실패 시 enqueue |
| `local_server/storage/sync_queue.py` | R3 | 크기 제한 |
| `local_server/engine/limit_checker.py` | R5 | today_executed 복원 |
