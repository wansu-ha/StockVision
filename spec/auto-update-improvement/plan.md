> 작성일: 2026-03-29 | 상태: 초안

# 자동 업데이트 개선 — 구현 계획서

spec: `spec/auto-update-improvement/spec.md`

## 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│ main.py (lifespan)                                          │
│  startup:                                                   │
│    UpdateManager.startup()          ← S1: 초기 체크         │
│    UpdateManager.start_background_tasks()  ← S1: 루프 등록  │
│    set_install_guard(can_install_now)      ← S6: 안전 콜백  │
│    pending_rollback.json 처리              ← S7: 롤백 정리  │
│  shutdown:                                                  │
│    UpdateManager.shutdown()         ← S1: 태스크 cancel     │
└──────┬──────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│ UpdateManager (manager.py)                                   │
│                                                              │
│  상태: UpdateState (S4)                                      │
│    status | download_progress | ready_to_install | ...       │
│                                                              │
│  루프 (S1):                                                  │
│    _check_loop()   ─── 1시간마다 → check_update()            │
│    _install_loop() ─── 첫 1회 즉시 + 10분마다 → try_install()│
│                                                              │
│  안전 (S6):                                                  │
│    _can_install() = is_in_update_window() + is_safe_to_install()│
│    is_safe_to_install() = _install_guard 콜백                │
│                                                              │
│  설치 (S6→S7):                                               │
│    _execute_install() → backup → pending_rollback.json → bat │
└──────┬──────────────────────────────────────────────────────┘
       │ on_heartbeat()
       │
┌──────┴──────────────────────────────────────────────────────┐
│ heartbeat.py (S2)                                            │
│  _on_heartbeat_ack / HTTP 폴백                               │
│    → _check_server_version() (기존 토스트)                    │
│    → _notify_update_manager() (신규 — 같은 레벨)             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ downloader.py (S3)                                           │
│  fail-closed SHA256 + RETRY_DELAY_SEC sleep                  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ installer.py (S7)                                            │
│  _write_pending_rollback() + 확장 .bat (health check 포함)   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ routers/update.py (S5 — 신규)                                │
│  GET /status, POST /check, POST /install, GET /release-notes │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Frontend (S8)                                                │
│  localClient.ts → localUpdate API                            │
│  OpsPanel.tsx → 버전 상시 + 배너 + 프로그레스                │
│  Settings.tsx → 버전 정보 + 수동 제어                        │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ tray_app.py (S9)                                             │
│  이벤트 콜백 → show_toast() + 메뉴 "업데이트 확인"           │
└─────────────────────────────────────────────────────────────┘
```

## 수정 파일 목록

| 파일 | 변경 | Step | 라인수 |
|------|------|------|--------|
| `local_server/updater/manager.py` | 상태 모델 확장 + 루프 + guard + force install + `start_background_tasks`/`shutdown` + 이벤트 콜백 | S1,S4,S6,S9 | 140→~300 |
| `local_server/updater/downloader.py` | fail-closed + retry delay | S3 | 104→~110 |
| `local_server/updater/installer.py` | `_write_pending_rollback` + bat 확장 (verifier) | S7 | 125→~200 |
| `local_server/updater/version_checker.py` | 릴리즈 노트 캐싱 (`release_notes` 반환) | S4 | 99→~115 |
| `local_server/cloud/heartbeat.py` | `_notify_update_manager()` 추가 + 2곳 호출 | S2 | 357→~380 |
| `local_server/routers/update.py` | **신규** — 4 엔드포인트 | S5 | ~60 |
| `local_server/main.py` | 루프 등록 + guard 주입 + rollback 정리 + shutdown + 라우터 등록 | S1,S6,S7 | 413→~450 |
| `frontend/src/services/localClient.ts` | `localUpdate` 4 메서드 + `UpdateStatus` 타입 확장 | S8 | 207→~230 |
| `frontend/src/components/main/OpsPanel.tsx` | 버전 상시 + 배너(status 분기) + 프로그레스 | S8 | 318→~380 |
| `frontend/src/pages/Settings.tsx` | Bridge 섹션 버전 + 수동 제어 | S8 | 423→~480 |
| `local_server/tray/tray_app.py` | 이벤트 콜백 + 메뉴 항목 | S9 | 262→~300 |
| `local_server/tests/test_updater.py` | 14건 테스트 추가 | S10 | 173→~350 |

## 구현 순서

### Step 1: S3 — downloader fail-closed + retry delay

가장 독립적이고 작은 변경. 다른 Step에 의존 없음.

**변경:**
- `downloader.py:100-101` — `return True` → `return False`
- `downloader.py:84-86` — 재시도 루프에 `await asyncio.sleep(RETRY_DELAY_SEC)` 추가

**verify:**
- `pytest local_server/tests/test_updater.py` — 기존 테스트 전체 통과 (동작 변경이므로)
- S10에서 `test_sha256_fail_closed`, `test_retry_with_delay` 추가 예정

---

### Step 2: S4 — 상태 모델 확장

S5 API가 의존하는 기반. manager.py 중심 변경.

**변경:**
- `manager.py` — `UpdateState`에 `status`, `last_error`, `release_notes`, `last_checked_at`, `mandatory` 추가
- `manager.py` — `to_dict()` 확장 (release_notes 제외 주석)
- `manager.py` — `check_update()`, `start_download()`에서 `status` 전이 로직 추가
- `version_checker.py` — `check_from_github()`에서 GitHub Release `body` 필드 캐싱, `UpdateInfo`에 `release_notes` 추가

**verify:**
- `pytest local_server/tests/test_updater.py -k "UpdateState"` — `to_dict()` 새 필드 확인
- 수동: `python -c "from local_server.updater.manager import UpdateState; print(UpdateState().to_dict())"` — 새 필드 존재

---

### Step 3: S1 — 설치 스케줄러 + 주기적 재체크

manager.py에 루프 2개 + 공개 메서드. main.py 연결.

**변경:**
- `manager.py` — `_check_loop()`, `_install_loop()` 구현
  - 주의: 이 시점에서 `try_install`은 아직 기존 시그니처 `(no_update_start, no_update_end)`. `_install_loop`은 config에서 읽어 기존 시그니처로 호출. Step 5에서 시그니처 변경 시 `_install_loop`도 같이 수정.
- `manager.py` — `start_background_tasks()`, `shutdown()` 구현
- `manager.py` — `_download_in_progress` 플래그 추가
- `main.py` — lifespan startup에서 `start_background_tasks()` 호출
- `main.py` — lifespan shutdown에서 `shutdown()` 호출

**verify:**
- 서버 시작 → 로그에 "체크 루프 시작", "설치 루프 시작" 확인
- 서버 종료 → 로그에 태스크 cancel 확인
- `pytest local_server/tests/test_updater.py` — 기존 테스트 통과

---

### Step 4: S2 — 하트비트 ↔ UpdateManager 연결

heartbeat.py에 `_notify_update_manager()` 추가.

**변경:**
- `heartbeat.py` — `_notify_update_manager(resp)` 함수 추가
- `heartbeat.py:105` — `_on_heartbeat_ack` 콜백에서 `_check_server_version()` 다음 줄에 호출
- `heartbeat.py:145` — HTTP 폴백에서 `_check_server_version()` 다음 줄에 호출

**verify:**
- 서버 시작 + 클라우드 연결 → 하트비트 응답에 `latest_version` 있으면 로그에 `on_heartbeat` 갱신 확인
- `pytest local_server/tests/test_updater.py -k "heartbeat"` — S10 테스트

---

### Step 5: S6 — 거래 안전 상태 검사

manager.py에 guard 구조 + main.py에 콜백 주입.

**변경:**
- `manager.py` — `_install_guard`, `set_install_guard()`, `is_safe_to_install()`, `_can_install()` (시간+안전)
- `manager.py` — `try_install()` 시그니처 변경 (인자 없음 → `_can_install()` 내부) + `_install_loop` 호출부도 같이 수정
- `manager.py` — `try_install_force()`, `_execute_install()` 추가
- `main.py` — `can_install_now()` 정의 + `set_install_guard()` 호출
  - `has_pending_orders()` 미존재 → `get_open_orders()` 결과 len > 0 으로 대체, 주석 남김

**verify:**
- `pytest local_server/tests/test_updater.py -k "install_blocked"` — guard False → 설치 안 됨
- `pytest local_server/tests/test_updater.py -k "can_install"` — 시간+안전 조합 테스트

---

### Step 6: S7 — 외부 verifier 롤백

installer.py 확장 + main.py 마커 처리.

**변경:**
- `installer.py` — `_write_pending_rollback()` 함수 추가
- `installer.py` — `_INSTALL_BAT_TEMPLATE` 확장 (verifier + rollback + Inno 실패 fallback)
- `installer.py` — `execute_update()` 수정: 시그니처 확장 (port, target_version, backup_dir 추가) + bat에 주입
- `manager.py` — `_execute_install()`의 `execute_update()` 호출부도 새 시그니처에 맞게 수정
- `main.py` — startup에서 `pending_rollback.json` 읽기 + 상태 분기 (rolled_back/installing/verifying)

**verify:**
- `pytest local_server/tests/test_updater.py -k "rollback_marker"` — 마커 생성/삭제
- bat 템플릿에 `{target_version}`, `{backup_dir}`, `{port}` 플레이스홀더 존재 확인
- 수동: `pending_rollback.json` 수동 생성 후 서버 시작 → 상태 반영 확인

---

### Step 7: S5 — 수동 제어 API

router 신규 생성.

**변경:**
- `local_server/routers/update.py` — **신규** 파일
  - `GET /api/update/status` → `to_dict()`
  - `POST /api/update/check` → `check_update()` + 자동 다운로드
  - `POST /api/update/install` → `is_safe_to_install()` / `try_install_force()`
  - `GET /api/update/release-notes` → `state.release_notes`
- `main.py` — `create_app()`에 `update` 라우터 등록

**verify:**
- `curl http://localhost:4020/api/update/status` — 200 + 상태 JSON
- `curl -X POST http://localhost:4020/api/update/check` — 200 + 체크 실행
- `curl -X POST http://localhost:4020/api/update/install` — 400 (준비 안 됨) 또는 409 (안전 조건)
- `pytest local_server/tests/test_updater.py -k "api"` — S10 API 테스트

---

### Step 8: S8 — 프론트엔드

**변경:**
- `localClient.ts` — `localUpdate` 객체 추가 (status, check, install, releaseNotes)
- `localClient.ts` — `UpdateStatus` 타입에 `status`, `current`, `last_error`, `last_checked_at`, `mandatory` 추가
- `OpsPanel.tsx` — 로컬 상태 옆에 `v{version}` 상시 표시
- `OpsPanel.tsx` — 배너를 `status` 필드 기반 분기 (downloading/ready/installing/rolled_back/error)
- `OpsPanel.tsx` — 다운로드 중 프로그레스 바 + "지금 설치" 버튼 + 릴리즈 노트 접이식
- `Settings.tsx` — Bridge 섹션에 현재/최신 버전 + "업데이트 확인" + "지금 설치" 버튼

**verify:**
- `cd frontend && npm run build` — 빌드 성공
- `npm run lint` — lint 통과
- 브라우저: OpsPanel에 버전 표시 확인
- 브라우저: Settings Bridge 섹션에 버전 정보 확인

---

### Step 9: S9 — 트레이 알림

**변경:**
- `manager.py` — 이벤트 콜백 등록 메커니즘 (`set_event_callback`)
- `tray_app.py` — 메뉴에 "업데이트 확인" 항목 추가 (`_on_check_update`)
- `main.py` — UpdateManager 이벤트 콜백 → `show_toast()` 연결

**verify:**
- 서버 시작 → 트레이 우클릭 → "업데이트 확인" 항목 존재
- 로그에서 이벤트 콜백 등록 확인

---

### Step 10: S10 — 테스트 보강

**변경:**
- `test_updater.py` — 14건 테스트 추가:

| # | 테스트 | 대상 |
|---|--------|------|
| 1 | `test_sha256_fail_closed` | SHA256 못 받으면 False |
| 2 | `test_retry_with_delay` | 재시도 사이 sleep 호출 |
| 3 | `test_duplicate_download_blocked` | `_download_in_progress` 중복 방지 |
| 4 | `test_install_loop_calls_try_install` | 스케줄러 → `try_install()` |
| 5 | `test_start_background_tasks_idempotent` | 중복 호출 무시 |
| 6 | `test_shutdown_cancels_tasks` | shutdown → cancel |
| 7 | `test_heartbeat_triggers_on_heartbeat` | 하트비트 → `on_heartbeat()` |
| 8 | `test_install_blocked_engine_running` | guard False → 설치 안 됨 |
| 9 | `test_install_api_409_engine_running` | POST /install → 409 |
| 10 | `test_rollback_marker_written` | 설치 전 마커 생성 |
| 11 | `test_rollback_marker_cleaned` | 정상 시작 시 삭제 |
| 12 | `test_rolled_back_state_on_startup` | 마커 `rolled_back` → 상태 반영 |
| 13 | `test_status_transitions` | idle → checking → downloading → ... |
| 14 | `test_verifier_checks_target_version` | bat 템플릿에 버전 포함 |

**verify:**
- `pytest local_server/tests/test_updater.py -v` — 전체 통과
- `pytest local_server/tests/ -v` — 기존 테스트 포함 전체 통과

---

## 검증 방법 (전체)

| 검증 | 명령 |
|------|------|
| Python 테스트 | `pytest local_server/tests/ -v` |
| Frontend 빌드 | `cd frontend && npm run build` |
| Frontend lint | `cd frontend && npm run lint` |
| 서버 기동 | `python -m uvicorn local_server.main:app --port 4020` |
| API 수동 확인 | `curl http://localhost:4020/api/update/status` |
| 브라우저 확인 | OpsPanel 버전 표시 + Settings 버전 정보 |

## 커밋 계획

| # | 메시지 | 포함 파일 |
|---|--------|----------|
| 1 | `docs: auto-update-improvement spec/plan 초안` | spec.md, plan.md, research doc |
| 2 | `fix(updater): SHA256 fail-closed + 재시도 delay` | downloader.py |
| 3 | `feat(updater): 상태 모델 확장 + 릴리즈 노트 캐싱` | manager.py, version_checker.py |
| 4 | `feat(updater): 설치 스케줄러 + 주기적 재체크 루프` | manager.py, main.py |
| 5 | `feat(updater): 하트비트 ↔ UpdateManager 연결` | heartbeat.py |
| 6 | `feat(updater): 거래 안전 상태 검사 + try_install 통일` | manager.py, main.py |
| 7 | `feat(updater): 외부 verifier 롤백 (.bat health check)` | installer.py, main.py |
| 8 | `feat(updater): 수동 제어 API` | routers/update.py, main.py |
| 9 | `feat(frontend): 업데이트 UX — 버전 표시 + 진행률 + 수동 제어` | localClient.ts, OpsPanel.tsx, Settings.tsx |
| 10 | `feat(tray): 업데이트 토스트 + 메뉴` | tray_app.py, manager.py, main.py |
| 11 | `test(updater): 흐름 테스트 14건 추가` | test_updater.py |
