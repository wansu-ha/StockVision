> 작성일: 2026-03-29 | 상태: 구현 완료

# 자동 업데이트 개선

## 배경

자동 업데이트 v1 (`spec/auto-update/spec.md`)이 구현됐으나:
1. `try_install()` 호출부가 없어 자동 설치가 실제로 발동하지 않음
2. `on_heartbeat()`이 heartbeat.py에서 호출되지 않음 — 하트비트 버전 감지가 사실상 미연결
3. SHA256 검증이 fail-open (해시 파일 못 받으면 통과)
4. `RETRY_DELAY_SEC` 선언만 있고 재시도 사이 sleep 없음
5. 설치 조건이 "시간"만 봄 — 엔진/미체결/위험 상태 미검사
6. 설치 실패 시 외부에서 검증할 수단 없음 (앱 못 뜨면 앱 내부 롤백 불가)
7. 상태 모델이 빈약 (status, last_error, release_notes 등 없음)
8. 버전 정보가 평소에 안 보임, 수동 제어 UI 없음

## 목표

1. **기능 완성**: 설치 스케줄러 연결 + 하트비트 연결 + SHA 검증 fail-closed
2. **안전성**: 거래 안전 상태 검사 + 외부 verifier 롤백
3. **UX**: 버전 가시성 + 진행률 + 수동 제어 + 릴리즈 노트

## 구현 순서

P0 (기능 완성) → P1 (안전성) → P2 (UX) 순서로 진행.

| Step | 우선순위 | 범위 |
|------|---------|------|
| S1 | P0 | 설치 스케줄러 + 주기적 재체크 루프 |
| S2 | P0 | 하트비트 ↔ UpdateManager 연결 |
| S3 | P0 | SHA256 fail-closed + 재시도 delay |
| S4 | P0 | 상태 모델 확장 |
| S5 | P0 | 수동 제어 API (`update.py` 라우터) — S4 상태 모델에 의존 |
| S6 | P1 | 거래 안전 상태 검사 (can_install_now 콜백) |
| S7 | P1 | 외부 verifier 롤백 (.bat health check) |
| S8 | P2 | 프론트 — 버전 표시 + 진행률 + 수동 제어 |
| S9 | P2 | 트레이 알림 |
| S10 | P2 | 테스트 보강 |

---

## S1: 설치 스케줄러 + 주기적 재체크

### 설치 루프 (`_install_loop`)

`manager.py`의 `_install_task`를 실제 루프로 교체:
- `ready_to_install=True` 시 **10분마다** `try_install()` 호출
- 허용 시간 + 안전 조건 (S6) 충족 시 설치 실행

```python
# manager.py
async def _install_loop(self) -> None:
    """ready_to_install이면 주기적으로 설치 시도.
    첫 1회는 즉시 평가 (부팅 시 이미 ready 상태 대응)."""
    first = True
    while True:
        if first:
            first = False
        else:
            await asyncio.sleep(600)  # 10분
        if not self.state.ready_to_install:
            continue
        self.try_install()  # 내부에서 _can_install() 검사
```

### 체크 루프 (`_check_loop`)

`_check_task`를 실제 루프로 교체:
- **1시간마다** 새 버전 확인
- 하트비트 연결 중이면 하트비트가 이미 갱신하므로 GitHub 스킵
- 새 버전 감지 + auto_enabled → 다운로드 시작

```python
async def _check_loop(self) -> None:
    """1시간마다 새 버전 확인 + 자동 다운로드."""
    while True:
        await asyncio.sleep(3600)
        # 하트비트가 이미 최신 정보를 넣었으면 GitHub 재확인 불필요
        if not self.state.info or not self.state.info.available:
            await self.check_update()
        if (self.state.info and self.state.info.available
                and not self.state.ready_to_install):
            cfg = get_config()
            if cfg.get("update.auto_enabled", True):
                await self.start_download()
```

### 공개 API: start_background_tasks / shutdown

main.py가 private 루프를 직접 만지지 않도록 공개 메서드로 감싼다.
중복 생성 방지 + shutdown 시 cancel 처리 포함.

```python
class UpdateManager:
    async def start_background_tasks(self) -> None:
        """체크 루프 + 설치 루프 시작. 중복 호출 무시."""
        if self._check_task is None or self._check_task.done():
            self._check_task = asyncio.create_task(self._check_loop())
        if self._install_task is None or self._install_task.done():
            self._install_task = asyncio.create_task(self._install_loop())

    async def shutdown(self) -> None:
        """백그라운드 태스크 정리."""
        for task in (self._check_task, self._install_task):
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self._check_task = None
        self._install_task = None
```

### main.py 연결

```python
# main.py lifespan, 기존 startup() 후:
update_mgr = get_update_manager()
await update_mgr.startup()
if update_mgr.state.info and update_mgr.state.info.available:
    if cfg.get("update.auto_enabled", True):
        asyncio.create_task(update_mgr.start_download())
# 신규: 공개 메서드로 루프 등록
await update_mgr.start_background_tasks()

# lifespan shutdown:
await update_mgr.shutdown()
```

---

## S2: 하트비트 ↔ UpdateManager 연결

### 호출 위치: `_check_server_version()` 안이 아니라, 하트비트 응답 직후

`_check_server_version()`에는 early return이 4군데 있다 (latest 없음, 같은 버전,
파싱 실패, 현재가 더 높음). 이 안에 넣으면 대부분의 경우 `on_heartbeat()`가
호출되지 않는다.

따라서 `_on_heartbeat_ack()` 콜백과 HTTP 폴백 응답 처리부에서
`_check_server_version()` 호출과 **같은 레벨**에서 `on_heartbeat()`를 호출한다.

```python
# heartbeat.py — _on_heartbeat_ack 콜백 (WS 경로, line ~96)
async def _on_heartbeat_ack(ack_payload: dict) -> None:
    ...
    _check_server_version(ack_payload)
    # 신규: UpdateManager 상태 갱신 (early return과 독립)
    _notify_update_manager(ack_payload)
    ...

# heartbeat.py — HTTP 폴백 경로 (line ~136)
if resp:
    ...
    _check_server_version(resp)
    # 신규: UpdateManager 상태 갱신
    _notify_update_manager(resp)
    ...
```

헬퍼 함수:

```python
def _notify_update_manager(resp: dict[str, Any]) -> None:
    """하트비트 응답으로 UpdateManager 상태를 갱신하고 필요 시 다운로드 예약."""
    from local_server.updater.manager import get_update_manager
    mgr = get_update_manager()
    mgr.on_heartbeat(resp)

    if (mgr.state.info and mgr.state.info.available
            and not mgr.state.ready_to_install
            and not mgr._download_in_progress):
        from local_server.config import get_config
        cfg = get_config()
        if cfg.get("update.auto_enabled", True):
            asyncio.create_task(mgr.start_download())
```

`_download_in_progress` 플래그를 `manager.py`에 추가하여 중복 다운로드 방지:

```python
class UpdateManager:
    def __init__(self):
        ...
        self._download_in_progress = False

    async def start_download(self) -> bool:
        if self._download_in_progress or self.state.ready_to_install:
            return False
        self._download_in_progress = True
        try:
            # ... 기존 다운로드 로직
        finally:
            self._download_in_progress = False
```

---

## S3: SHA256 fail-closed + 재시도 delay

### fail-closed

`downloader.py:100-101`의 `return True` → `return False`로 변경.
SHA256 파일을 못 받으면 검증 실패 처리, 재다운로드 시도.

```python
async def _verify_sha256(file_path: Path, sha256_url: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(sha256_url)
            resp.raise_for_status()
            expected = resp.text.strip().split()[0].lower()
    except Exception:
        logger.warning("SHA256 파일 다운로드 실패 — 검증 실패 처리")
        return False  # fail-closed
    ...
```

### 재시도 delay

`RETRY_DELAY_SEC`를 실제로 사용:

```python
async def download_installer(...) -> Path | None:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # ... 다운로드 + 검증
            return dest
        except Exception:
            ...
            dest.unlink(missing_ok=True)
            if attempt < MAX_RETRIES:
                logger.info("재시도 대기: %d초", RETRY_DELAY_SEC)
                await asyncio.sleep(RETRY_DELAY_SEC)
    ...
```

---

## S4: 상태 모델 확장

`UpdateState` 필드 추가:

```python
@dataclass
class UpdateState:
    info: UpdateInfo | None = None
    download_progress: float = 0.0
    ready_to_install: bool = False
    installer_path: Path | None = None
    # 신규
    status: str = "idle"           # idle | checking | downloading | ready | installing | verifying | rolled_back | error
    last_error: str | None = None  # 마지막 오류 메시지
    release_notes: str | None = None  # GitHub Release body (Markdown)
    last_checked_at: str | None = None  # ISO 포맷 타임스탬프
    mandatory: bool = False        # MAJOR 불일치 시 True
```

`to_dict()`에 신규 필드 포함:

```python
def to_dict(self) -> dict[str, Any]:
    base = {
        "status": self.status,
        "available": self.info.available if self.info else False,
        "latest": self.info.latest if self.info else "",
        "current": self.info.current if self.info else "",
        "major_mismatch": self.info.major_mismatch if self.info else False,
        "download_progress": self.download_progress,
        "ready_to_install": self.ready_to_install,
        "last_error": self.last_error,
        "last_checked_at": self.last_checked_at,
        "mandatory": self.mandatory,
        # release_notes는 의도적 제외 — 본문이 길어 별도 엔드포인트(GET /api/update/release-notes)로 분리
    }
    return base
```

상태 전이:
```
idle → checking → idle (최신)
                ↘ downloading → ready → installing → verifying → idle (성공)
                                  ↓                      ↓
                                error → idle (재시도)   rolled_back
```

| 상태 | 의미 | 진입 시점 |
|------|------|----------|
| `idle` | 대기 / 최신 버전 | 초기, 체크 후 최신, 롤백 후 안정 |
| `checking` | 버전 확인 중 | `check_update()` 시작 |
| `downloading` | 다운로드 중 | `start_download()` 시작 |
| `ready` | 설치 대기 | 다운로드 + SHA256 검증 완료 |
| `installing` | 설치 중 | `try_install()` / `try_install_force()` |
| `verifying` | 외부 verifier가 health check 중 | .bat이 Inno 실행 후 health 폴링 |
| `rolled_back` | 롤백 완료 | verifier가 health 실패 → 백업 복원 |
| `error` | 오류 | 다운로드/SHA/네트워크 실패 |

`verifying`과 `rolled_back`는 앱이 아닌 .bat 스크립트가 제어하는 구간이라
앱 내 `self.state.status`로 직접 전이되지 않는다. 대신:
- `pending_rollback.json`에 `"status": "verifying"` 기록
- 새 버전 정상 시작 시 마커 삭제 → `idle`
- verifier가 롤백 실행 시 마커에 `"status": "rolled_back"` 기록
- 복원된 이전 버전이 시작 시 마커 읽고 `self.state.status = "rolled_back"` 세팅
  + 트레이 토스트 "업데이트 실패, 이전 버전으로 복원됨"

각 단계에서 `self.state.status` 갱신 → 프론트/트레이가 단일 필드로 분기 가능.

---

## S5: 수동 제어 API

`local_server/routers/update.py` 신규. S4의 확장된 상태 모델에 의존.

| 엔드포인트 | 설명 |
|-----------|------|
| `GET /api/update/status` | 현재 업데이트 상태 전체 |
| `POST /api/update/check` | 즉시 버전 체크 (+ auto면 다운로드) |
| `POST /api/update/install` | 설치 시도 — 시간 무시, 안전 조건은 기본 준수, `force=true` 시 강제 |
| `GET /api/update/release-notes` | 최신 릴리즈 노트 |

```python
router = APIRouter(prefix="/api/update", tags=["update"])

@router.get("/status")
async def update_status():
    mgr = get_update_manager()
    return mgr.state.to_dict()

@router.post("/check")
async def check_now():
    mgr = get_update_manager()
    await mgr.check_update()
    if (mgr.state.info and mgr.state.info.available
            and not mgr.state.ready_to_install
            and not mgr._download_in_progress):
        cfg = get_config()
        if cfg.get("update.auto_enabled", True):
            asyncio.create_task(mgr.start_download())
    return mgr.state.to_dict()

@router.post("/install")
async def install_now(force: bool = False):
    mgr = get_update_manager()
    if not mgr.state.ready_to_install:
        raise HTTPException(400, detail="설치 준비되지 않음")

    if not force:
        # 안전 조건만 검사 (시간은 무시 — 수동 설치 의도)
        if not mgr.is_safe_to_install():
            raise HTTPException(
                409,
                detail="안전 조건 미충족 (엔진 실행 중 또는 미체결 주문 존재)",
            )
    mgr.try_install_force()
    return {"message": "설치 시작됨"}

@router.get("/release-notes")
async def release_notes():
    mgr = get_update_manager()
    return {"notes": mgr.state.release_notes or ""}
```

---

## S6: 거래 안전 상태 검사

### can_install_now 콜백

업데이터가 앱 상태를 직접 읽지 않고, `main.py`에서 콜백 주입:

```python
# main.py
def can_install_now() -> bool:
    """엔진 정지 + 미체결 없음 + kill switch 아님."""
    engine = app.state.strategy_engine
    if engine and engine.running:
        return False
    broker = app.state.broker
    if broker and broker.has_pending_orders():
        return False
    # kill switch, loss lock 등 위험 상태 체크
    return True

update_mgr.set_install_guard(can_install_now)
# 주의: broker.has_pending_orders()는 현재 어댑터에 미구현일 수 있음.
# 구현 시 KIS/키움 어댑터에 메서드 추가 필요 — 없으면 해당 검사 생략하고 주석 남김.
```

```python
# manager.py
class UpdateManager:
    def __init__(self):
        ...
        self._install_guard: Callable[[], bool] | None = None

    def set_install_guard(self, guard: Callable[[], bool]) -> None:
        self._install_guard = guard

    def is_safe_to_install(self) -> bool:
        """안전 조건만 확인 (시간 무관). 수동 API에서 사용."""
        if self._install_guard and not self._install_guard():
            return False
        return True

    def _can_install(self) -> bool:
        """시간 + 안전 조건 모두 확인. 자동 루프에서 사용."""
        cfg = get_config()
        if not is_in_update_window(
            cfg.get("update.no_update_start", "08:00"),
            cfg.get("update.no_update_end", "17:00"),
        ):
            return False
        return self.is_safe_to_install()
```

### try_install 시그니처 통일

기존 `try_install(no_update_start, no_update_end)` → 인자 없는 `try_install()` + `_can_install()` 내부 호출로 변경. 시간 설정은 `_can_install()`이 config에서 직접 읽는다.

스펙 전체에서 `try_install()`은 항상 **인자 없음** — S1 루프, S4 API, S7 롤백 모두 동일 시그니처.

```python
def try_install(self) -> bool:
    """안전 조건 + 시간 확인 후 설치."""
    if not self.state.ready_to_install or not self.state.installer_path:
        return False
    if not self._can_install():
        return False
    return self._execute_install()

def try_install_force(self) -> bool:
    """시간/안전 조건 무시 — 수동 API용."""
    if not self.state.ready_to_install or not self.state.installer_path:
        return False
    return self._execute_install()

def _execute_install(self) -> bool:
    """공통 설치 실행 로직."""
    self.state.status = "installing"
    backup_current(self._install_dir)
    _write_pending_rollback(self._install_dir, self.state.info)  # S7
    execute_update(self.state.installer_path)
    return True  # 실제로는 sys.exit으로 도달 안 함
```

---

## S7: 외부 verifier 롤백

### 문제

`execute_update()`는 `sys.exit(0)` 후 .bat → Inno 설치. 새 버전이 아예 안 뜨면 앱 내부 코드는 실행 자체가 안 됨.

### 해결: verify-and-rollback .bat

설치 .bat을 확장하여 **앱 재시작 + health check + 버전 검증 + 롤백**을 포함:

**핵심 원칙:** "앱이 떴다"가 아니라 "목표 버전으로 떴고 health가 안정적이다"를 확인한 뒤 마커를 지운다.

```batch
@echo off
REM === StockVision 업데이트 + 검증 스크립트 ===

REM 1. 서버 종료 대기
timeout /t 3 /nobreak >nul

REM 2. pending_rollback.json 상태를 verifying으로 갱신 (전체 필드 유지)
echo {"status":"verifying","from_version":"{from_version}","to_version":"{target_version}","backup_dir":"{backup_dir}"} > "{install_dir}\pending_rollback.json"

REM 3. 인스톨러 실행 (종료까지 대기)
start /wait "" "{installer_path}" /SILENT /SUPPRESSMSGBOXES

REM 4. 새 서버 프로세스 시작
REM    Inno [Run] 섹션이 시작하지만, 실패 시 명시적 fallback
timeout /t 5 /nobreak >nul
tasklist /FI "IMAGENAME eq stockvision-local.exe" | findstr "stockvision-local.exe" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    REM Inno [Run]이 실패한 경우 — 직접 시작
    start "" "{install_dir}\stockvision-local.exe"
    timeout /t 5 /nobreak >nul
)

REM 5. health check — 목표 버전으로 떴는지 확인
REM    최대 60초 (3초 간격 × 20회)
REM    조건: HTTP 200 + 응답 JSON에 목표 버전 포함
set ATTEMPTS=0
:health_loop
if %ATTEMPTS% GEQ 20 goto rollback
timeout /t 3 /nobreak >nul
set /a ATTEMPTS+=1

REM health 체크 + 버전 검증
curl -s http://127.0.0.1:{port}/health > "%TEMP%\sv_health.tmp" 2>nul
if %ERRORLEVEL% NEQ 0 goto health_loop
findstr /C:"{target_version}" "%TEMP%\sv_health.tmp" >nul 2>&1
if %ERRORLEVEL%==0 goto version_ok
goto health_loop

:version_ok
REM 6. 안정성 확인 — 추가 15초 후 한 번 더 체크 (시작 직후 크래시 방지)
timeout /t 15 /nobreak >nul
curl -s -o nul -w "%%{http_code}" http://127.0.0.1:{port}/health | findstr "200" >nul
if %ERRORLEVEL% NEQ 0 goto rollback

REM 7. 성공 — pending_rollback 삭제
del "{install_dir}\pending_rollback.json" 2>nul
del "%TEMP%\sv_health.tmp" 2>nul
del "%~f0"
exit /b 0

:rollback
REM 8. 실패 — 새 서버 프로세스 종료 시도
taskkill /IM stockvision-local.exe /F >nul 2>&1
timeout /t 3 /nobreak >nul

REM 9. 백업에서 복원
echo %DATE% %TIME% 업데이트 실패, 롤백 시작 >> "{install_dir}\logs\update.log"
xcopy /E /Y /Q "{backup_dir}\*" "{install_dir}\" >nul 2>&1

REM 10. pending_rollback 상태를 rolled_back으로 갱신 (전체 필드 유지)
echo {"status":"rolled_back","from_version":"{from_version}","to_version":"{target_version}","backup_dir":"{backup_dir}"} > "{install_dir}\pending_rollback.json"

REM 11. 이전 버전 서버 시작
start "" "{install_dir}\stockvision-local.exe"

del "%TEMP%\sv_health.tmp" 2>nul
del "%~f0"
exit /b 1
```

### pending_rollback.json

설치 전 마커 파일 생성. .bat 스크립트가 상태를 `verifying` → 성공(삭제) / `rolled_back`으로 갱신한다.

```python
def _write_pending_rollback(install_dir: Path, info: UpdateInfo) -> None:
    import json
    from datetime import datetime
    marker = install_dir / "pending_rollback.json"
    marker.write_text(json.dumps({
        "status": "installing",
        "from_version": info.current,
        "to_version": info.latest,
        "timestamp": datetime.now().isoformat(),
        "backup_dir": str(install_dir / "backup" / f"v{info.current}"),
    }))
```

### main.py 시작 시 마커 처리

마커가 있으면 상태에 따라 분기:

```python
# main.py startup
marker = install_dir / "pending_rollback.json"
if marker.exists():
    import json
    data = json.loads(marker.read_text())
    status = data.get("status")

    if status == "rolled_back":
        # 롤백으로 복원된 이전 버전 — 사용자에게 알림
        logger.warning(
            "업데이트 실패: v%s → v%s 롤백됨",
            data.get("from_version"), data.get("to_version"),
        )
        update_mgr.state.status = "rolled_back"
        update_mgr.state.last_error = (
            f"v{data.get('to_version')} 업데이트 실패, "
            f"v{data.get('from_version')}으로 복원됨"
        )
        # 트레이 토스트 예약 (S9)
        marker.unlink()
    elif status in ("installing", "verifying"):
        # .bat이 완료 전에 앱이 뜬 경우 (비정상) 또는
        # 새 버전이 정상 시작됐지만 .bat보다 먼저 뜬 경우
        # → .bat이 처리할 테니 마커 유지 (삭제하지 않음)
        logger.info("pending_rollback 마커 발견 (status=%s) — .bat 처리 대기", status)
    else:
        # 알 수 없는 상태 — 정리
        logger.warning("pending_rollback 알 수 없는 상태: %s — 마커 삭제", status)
        marker.unlink()
```

### 한계

- 이전 버전으로 롤백했는데 이전 버전도 시작 실패하면 서버 없는 상태가 됨.
  이 경우 사용자가 수동으로 재설치해야 함 (GitHub에서 다운로드).
  자동화 범위 밖 — 무한 롤백 체인은 복잡도 대비 가치 없음.

---

## S8: 프론트 — 버전 표시 + 진행률 + 수동 제어

### OpsPanel 버전 상시 표시

로컬 상태 옆에 버전 번호:
```
● 로컬 연결됨 v0.3.0  ● 브로커 ...
```
업데이트 가능 시:
```
● 로컬 연결됨 v0.3.0 → v0.4.0  ● 브로커 ...
```

### 업데이트 배너 개선

`status` 필드 기반 분기:

| status | 배너 |
|--------|------|
| `downloading` | 프로그레스 바 + `XX%` |
| `ready` | "지금 설치" 버튼 + "허용 시간에 자동 설치" |
| `installing` | "설치 중... 서버가 재시작됩니다" |
| `verifying` | "업데이트 검증 중..." (실제로는 .bat이 관리, 앱 재시작 전엔 표시 안 됨) |
| `rolled_back` | "업데이트 실패, 이전 버전으로 복원됨" (경고 배너) |
| `error` | `last_error` 표시 + "재시도" 버튼 |

릴리즈 노트: 접이식 표시 (▸ 변경사항 보기)

### Settings Bridge 섹션

- 현재 버전 + 최신 버전
- "업데이트 확인" 버튼 → `POST /api/update/check`
- "지금 설치" 버튼 → `POST /api/update/install`
- 엔진 실행 중이면 409 → "엔진을 먼저 중지하세요" 안내

### localClient 확장

```typescript
export const localUpdate = {
  status: () => axios.get<UpdateStatus>(`${LOCAL_URL}/api/update/status`).then(r => r.data),
  check: () => axios.post<UpdateStatus>(`${LOCAL_URL}/api/update/check`).then(r => r.data),
  install: (force = false) =>
    axios.post(`${LOCAL_URL}/api/update/install`, null, { params: { force } }).then(r => r.data),
  releaseNotes: () =>
    axios.get<{ notes: string }>(`${LOCAL_URL}/api/update/release-notes`).then(r => r.data),
}
```

---

## S9: 트레이 알림

`UpdateManager`에 이벤트 콜백 등록 → `tray_app.py`에서 `show_toast()`:

| 이벤트 | 토스트 |
|--------|--------|
| 업데이트 감지 | "새 버전 v0.4.0 사용 가능" |
| 다운로드 완료 | "업데이트 준비됨. 허용 시간에 자동 설치됩니다" |
| 설치 시작 | "업데이트 설치 중... 서버가 재시작됩니다" |
| MAJOR 불일치 | "서버 버전이 호환되지 않습니다. 업데이트가 필요합니다" |
| 설치 실패 (롤백) | "업데이트 실패, 이전 버전으로 복원됨" |

트레이 컨텍스트 메뉴에 "업데이트 확인" 항목 추가.

---

## S10: 테스트 보강

`test_updater.py`에 추가:

| 테스트 | 검증 대상 |
|--------|----------|
| `test_duplicate_download_blocked` | `_download_in_progress` 플래그로 중복 방지 |
| `test_install_loop_calls_try_install` | 스케줄러가 `try_install()` 호출하는지 |
| `test_sha256_fail_closed` | SHA256 못 받으면 다운로드 실패 |
| `test_retry_with_delay` | 재시도 사이 `RETRY_DELAY_SEC` 대기 |
| `test_rollback_marker_written` | 설치 전 `pending_rollback.json` 생성 |
| `test_rollback_marker_cleaned` | 정상 시작 시 마커 삭제 |
| `test_install_blocked_engine_running` | 엔진 실행 중 → `_can_install()` False |
| `test_install_api_409_engine_running` | `POST /install` → 409 |
| `test_heartbeat_triggers_on_heartbeat` | 하트비트 응답 → `on_heartbeat()` 호출 |
| `test_status_transitions` | idle → checking → downloading → ready → installing → verifying/rolled_back |
| `test_start_background_tasks_idempotent` | 중복 호출 시 태스크 재생성 안 함 |
| `test_shutdown_cancels_tasks` | shutdown() 호출 시 루프 태스크 cancel |
| `test_verifier_checks_target_version` | .bat이 HTTP 200 + 목표 버전 일치 확인 |
| `test_rolled_back_state_on_startup` | 마커 `rolled_back` → state.status 반영 + 마커 삭제 |

---

## 변경 대상

| 파일 | 변경 | Step |
|------|------|------|
| `local_server/updater/manager.py` | 루프 태스크 + 상태 모델 + guard + force install | S1,S4,S6 |
| `local_server/updater/downloader.py` | fail-closed + retry delay | S3 |
| `local_server/updater/installer.py` | pending_rollback 마커 + bat 확장 | S7 |
| `local_server/updater/version_checker.py` | 릴리즈 노트 캐싱 | S4 |
| `local_server/cloud/heartbeat.py` | `on_heartbeat()` 호출 추가 | S2 |
| `local_server/routers/update.py` | **신규** — 수동 제어 API | S5 |
| `local_server/main.py` | 루프 등록 + guard 주입 + rollback 정리 | S1,S6,S7 |
| `frontend/src/services/localClient.ts` | `localUpdate` API | S8 |
| `frontend/src/components/main/OpsPanel.tsx` | 버전 표시 + 진행률 + 배너 | S8 |
| `frontend/src/pages/Settings.tsx` | 버전 정보 + 수동 제어 | S8 |
| `local_server/tray/tray_app.py` | 토스트 + 메뉴 | S9 |
| `local_server/tests/test_updater.py` | 흐름 테스트 추가 | S10 |

## 수용 기준

### P0 — 기능 완성 (S1~S5)
- [ ] `_install_loop`: 첫 1회 즉시 + 이후 10분마다 try_install() 호출
- [ ] `_check_loop`: 1시간마다 GitHub 재확인 + 자동 다운로드
- [ ] `start_background_tasks()` / `shutdown()` 공개 메서드로 루프 관리 (중복 생성 방지, cancel 처리)
- [ ] main.py에서 `start_background_tasks()` 호출, shutdown에서 `shutdown()` 호출
- [ ] heartbeat.py — `_check_server_version()`과 같은 레벨에서 `_notify_update_manager()` 호출 (early return 영향 안 받음)
- [ ] 하트비트 감지 시 중복 방지(`_download_in_progress`) 후 다운로드 예약
- [ ] SHA256 fail-closed (해시 파일 못 받으면 검증 실패)
- [ ] 재시도 사이 `RETRY_DELAY_SEC` sleep
- [ ] UpdateState에 status(verifying/rolled_back 포함), last_error, release_notes, last_checked_at, mandatory 추가 (S4)
- [ ] `to_dict()`에 release_notes 제외 — 별도 엔드포인트로 분리 (본문 길이)
- [ ] `GET /api/update/status` — 상태 전체 반환 (S5)
- [ ] `POST /api/update/check` — 즉시 체크 (S5)
- [ ] `POST /api/update/install` — **안전 조건만** 검사 (시간 무시), force=true 시 강제 (S5)
- [ ] `GET /api/update/release-notes` — 릴리즈 노트 (S5)
- [ ] `try_install()` 시그니처 통일: 인자 없음, 내부에서 `_can_install()` 호출

### P1 — 안전성 (S6~S7)
- [ ] `can_install_now()` 콜백: 엔진 정지 + 미체결 없음 + 위험 상태 아님 (`has_pending_orders` 미구현 시 생략 + 주석)
- [ ] `is_safe_to_install()`: 안전 조건만 (수동 API용), `_can_install()`: 시간 + 안전 (자동 루프용)
- [ ] `try_install()` → `_can_install()` → `_execute_install()` 구조
- [ ] `try_install_force()`는 `_can_install()` 생략 (수동 API용)
- [ ] 설치 전 `pending_rollback.json` 마커 생성 (status: installing)
- [ ] .bat이 Inno 실행 후 새 서버를 시작하고 health check (60초 + 안정성 15초)
- [ ] health check가 **목표 버전**으로 떴는지 확인 (HTTP 200 + version 일치)
- [ ] 안정성 확인: 첫 health 성공 후 15초 대기 → 한 번 더 체크 (시작 직후 크래시 방지)
- [ ] health 실패 시: 새 프로세스 kill → 백업 복원 → 마커 `rolled_back` → 이전 버전 시작
- [ ] main.py 시작 시 마커 상태 분기: `rolled_back` → 알림 + 삭제, `installing/verifying` → .bat 대기

### P2 — UX (S8~S10)
- [ ] OpsPanel에 로컬 서버 버전 항상 표시
- [ ] status 기반 배너 분기 (downloading/ready/installing/verifying/rolled_back/error)
- [ ] 다운로드 중 프로그레스 바
- [ ] "지금 설치" 버튼 (엔진 실행 중 → 409 안내)
- [ ] 릴리즈 노트 접이식 표시
- [ ] Settings Bridge 섹션 버전 정보 + 수동 제어
- [ ] 트레이 토스트 (감지/완료/설치/실패/롤백)
- [ ] 트레이 메뉴 "업데이트 확인"
- [ ] 테스트 보강 (S10 목록 참조)
- [ ] 기존 테스트 전체 통과
