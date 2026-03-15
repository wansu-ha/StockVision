# 로컬 서버 견고성 — Config Atomic Write · Mock 자동감지 · SyncQueue · Heartbeat 버전

> 작성일: 2026-03-15 | 상태: 초안

## 1. 배경

로컬 서버의 안정성과 클라우드 동기화를 강화하는 4건의 개선 사항을 묶어 처리한다.
모두 기존 코드에 기반이 있어 확장/연결 작업 위주이다.

## 2. 범위

### 2.1 포함

| # | 항목 | 분류 |
|---|------|------|
| R1 | Config 파일 atomic write (race condition 방지) | 안정성 |
| R2 | 브로커 mock/실전 자동 감지 | 편의성 |
| R3 | SyncQueue 오프라인 큐 연동 | 동기화 |
| R4 | Heartbeat WS ack 버전 파싱 | 동기화 |

### 2.2 제외

- 키움 어댑터 Reconciler 추가 (외부 주문 감지 spec에서 처리)
- 클라우드 서버 heartbeat 응답 구조 변경

## 3. 요구사항

### R1: Config Atomic Write

**문제**: `local_server/config.py`의 `save()`가 파일을 직접 덮어쓴다.
동시 호출 시 파일이 잘리거나 일부만 기록될 수 있다.

**현재 코드** (`config.py:95-99`):
```python
def save(self) -> None:
    self._path.parent.mkdir(parents=True, exist_ok=True)
    with self._path.open("w", encoding="utf-8") as f:
        json.dump(self._data, f, ensure_ascii=False, indent=2)
```

**요구사항**:
- 임시 파일에 기록 후 `os.replace()`로 atomic rename
- 임시 파일은 동일 디렉터리에 생성 (같은 파일시스템 보장)
- Windows에서 `os.replace()`가 기존 파일을 덮어쓸 수 있도록 처리
- 쓰기 실패 시 기존 파일이 손상되지 않음을 보장

### R2: Mock/실전 자동 감지

**문제**: `local_server/broker/factory.py`에서 `is_mock` 플래그를 수동 설정에 의존한다.
사용자가 모의/실전을 혼동하면 실전 계좌에서 테스트 주문이 실행될 수 있다.

**현재 코드** (`factory.py:69`):
```python
is_mock = kwargs.get("is_mock") or (os.getenv("KIS_IS_MOCK", "false").lower() == "true")
```

**요구사항**:
- 브로커 초기화 시 계좌번호 패턴으로 모의/실전 자동 판별
  - KIS: 모의 계좌번호 접두사 규칙 확인 (KIS API 문서 참조)
  - 키움: 모의서버 URL 도메인으로 판별 (이미 다른 base_url 사용)
- 자동 감지 결과와 수동 설정이 불일치하면 경고 로그 출력
- 자동 감지 결과를 `config.json`에 기록 (재시작 시 참조)
- 자동 감지 실패 시 수동 설정 폴백

### R3: SyncQueue 연동

**문제**: `local_server/storage/sync_queue.py`에 완전한 SyncQueue 구현체가 있으나
어디에서도 호출하지 않는 고아 코드이다.

**현재 구현** (`sync_queue.py:28-88`):
- `enqueue(action_type, data)` — 오프라인 변경 저장
- `dequeue()` — 가장 오래된 항목 pop
- `peek_all()` — 전체 조회
- 저장 경로: `~/.stockvision/sync_queue.json`
- action_type: `rule_create`, `rule_update`, `rule_delete`, `watchlist_add`, `watchlist_remove`

**요구사항**:
- 클라우드 연결 실패 시 규칙/관심종목 변경을 SyncQueue에 적재
- 클라우드 재연결 시 (heartbeat 복구 감지) 큐를 순서대로 플러시
- 플러시 실패 항목은 큐에 잔류 (재시도)
- 큐 크기 제한 (최대 100건, 초과 시 오래된 것부터 제거)

**연동 지점**:
- `local_server/routers/rules.py` — 규칙 CRUD 실패 시 enqueue
- `local_server/cloud/heartbeat.py` — 연결 복구 시 flush

### R4: Heartbeat WS Ack 버전 파싱

**문제**: HTTP heartbeat에서는 `rules_version`, `context_version` 등을 파싱하여
변경 감지 → 자동 fetch를 수행하지만, WS heartbeat_ack에서는 버전 정보를 파싱하지 않는다.

**현재 코드** (`heartbeat.py:104-105`):
```python
# WS heartbeat_ack는 ws_relay_client._handle_heartbeat_ack에서 처리
# 버전 체크를 위해 HTTP 응답 형식으로 변환은 후속 개선
```

**요구사항**:
- WS heartbeat_ack 메시지에서 버전 필드 추출
- 기존 `_check_version_changes()` 로직 재활용
- HTTP heartbeat과 동일한 버전 변경 감지 + fetch 트리거
- WS 모드에서도 규칙/컨텍스트 변경이 즉시 반영됨

## 4. 변경 파일 (예상)

| 파일 | 변경 |
|------|------|
| `local_server/config.py` | R1: `save()` atomic write |
| `local_server/broker/factory.py` | R2: 자동 감지 로직 추가 |
| `local_server/broker/kis/auth.py` | R2: 계좌번호 패턴 판별 헬퍼 |
| `local_server/routers/rules.py` | R3: 클라우드 실패 시 enqueue |
| `local_server/cloud/heartbeat.py` | R3: 복구 시 flush, R4: 버전 파싱 공통화 |
| `local_server/cloud/ws_relay_client.py` | R4: ack에서 버전 필드 추출 |
| `local_server/storage/sync_queue.py` | R3: 크기 제한 추가 |

## 5. 수용 기준

- [ ] Config 동시 저장 시 파일이 손상되지 않는다
- [ ] 모의 계좌로 접속 시 `is_mock=true`가 자동 설정된다
- [ ] 수동 설정과 자동 감지가 불일치하면 경고 로그가 출력된다
- [ ] 클라우드 연결 끊김 시 규칙 변경이 SyncQueue에 저장된다
- [ ] 클라우드 재연결 시 큐가 자동 플러시된다
- [ ] WS 모드에서 규칙 버전 변경 시 자동 fetch가 실행된다
- [ ] HTTP/WS 모드 모두 동일한 버전 변경 감지가 동작한다

## 6. 참고

- Config: `local_server/config.py`
- SyncQueue: `local_server/storage/sync_queue.py`
- Heartbeat: `local_server/cloud/heartbeat.py`
- WS Relay: `local_server/cloud/ws_relay_client.py`
- Broker Factory: `local_server/broker/factory.py`
