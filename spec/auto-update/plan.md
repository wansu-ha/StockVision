> 작성일: 2026-03-28 | 상태: 구현 완료

# 로컬 서버 자동 업데이트 — 구현 계획

## 구현 순서

### Step 0: 선행 버그 수정

**파일**: `local_server/cloud/heartbeat.py`

- `heartbeat.py:63 _build_heartbeat_payload` — `cfg.get("server.version", _VERSION)` → `_VERSION` 직접 사용
- `heartbeat.py:198 _check_server_version` — `get_config().get("server.version", "1.0.0")` → `_VERSION` 교체
- `localClient.ts:188` — `GET /health` → `GET /api/health` 경로 수정
- config에서 `server.version` 키 참조 제거

**verify**: 기존 heartbeat 테스트 통과 + `_VERSION`이 `"0.2.0"` 반환 확인

### Step 1: updater 코어 모듈

**파일**: `local_server/updater/__init__.py`, `version_checker.py`, `downloader.py`

#### version_checker.py
- `check_github_latest()`: GitHub Releases API → `(version, download_url, sha256_url)`
- `check_from_heartbeat(resp)`: 하트비트 응답 → `(version, download_url)`
- `is_major_mismatch(current, latest)`: MAJOR 비교
- `is_update_available(current, latest)`: 단순 비교
- rate limit: GitHub API 시작 시 1회, 이후 1시간마다

#### downloader.py
- `download_installer(url, sha256_url, dest_dir)`: 백그라운드 다운로드
- `verify_sha256(file_path, expected_hash)`: 무결성 검증
- 임시 디렉토리: `{install_dir}/temp/`
- 불완전 파일 정리: 시작 시 temp/ 내 .exe 삭제
- 네트워크 에러: 5분 후 재시도, 최대 3회

**verify**: mock으로 다운로드 + SHA256 검증 테스트

### Step 2: 설치 시퀀스 (Step 4 완료 후)

**의존**: Step 4 (설정 키) — `is_in_update_window`가 no_update 설정을 읽음

**파일**: `local_server/updater/installer.py`

- `backup_current(install_dir, current_version)`: 현재 exe → `backup/v{ver}/` 복사, 최근 2개만 유지
- `create_install_script(installer_path)`: .bat 템플릿 생성
  ```bat
  @echo off
  timeout /t 3 /nobreak >nul
  start "" "{installer_path}" /SILENT /SUPPRESSMSGBOXES
  del "%~f0"
  ```
- `execute_update(installer_path)`: .bat 실행 (detached) → sys.exit
- `is_in_update_window(no_update_start, no_update_end)`: 현재 시간이 허용 구간인지

**verify**: .bat 생성 + 내용 검증 테스트 (실제 설치는 수동)

### Step 3: installer.iss 수정

**파일**: `local_server/installer.iss`

- `CloseApplications=yes` 추가 (실행 중 프로세스 자동 종료)
- `[Run]` 섹션의 `skipifsilent` 플래그 제거 → /SILENT에서도 재시작
- `RestartApplications` 불사용 (sys.exit으로 먼저 종료, Inno가 추적 불가)

**verify**: Inno Setup 컴파일 성공

### Step 4: 설정 키 추가

**파일**: `local_server/storage/config_store.py` (또는 DEFAULT_CONFIG)

- `update.auto_enabled`: bool, 기본 true
- `update.no_update_start`: str, 기본 "08:00"
- `update.no_update_end`: str, 기본 "17:00"

**verify**: config 조회/변경 테스트

### Step 5: 트레이 통합

**파일**: `local_server/tray/tray_app.py`

- 업데이트 상태에 따른 아이콘 색상 변경 (🟡 가능 / 🔴 필요)
- 우클릭 메뉴에 "업데이트 확인" 항목 추가
- 메뉴 클릭 → 수동 체크 + 다운로드 트리거

**verify**: 트레이 메뉴에 항목 표시 확인 (수동)

### Step 6: health API 확장

**파일**: `local_server/routers/health.py`

- `/api/health` 응답에 `update_status` 객체 추가:
  ```json
  {
    "available": true,
    "latest": "0.3.0",
    "major_mismatch": false,
    "download_progress": 0.75,
    "ready_to_install": false
  }
  ```
- updater 모듈의 상태를 읽어서 반환

**verify**: API 호출 → update_status 포함 확인

### Step 7: main.py 통합

**파일**: `local_server/main.py`

- startup 이벤트에 updater 초기화:
  - temp/ 정리
  - GitHub 최신 버전 체크 (1회)
  - 자동 업데이트 ON이면 다운로드 시작
- heartbeat 콜백에 version_checker 연결
- 허용 시간 진입 시 설치 트리거 (APScheduler 또는 asyncio task)

**verify**: 서버 시작 → 로그에 버전 체크 결과 출력

### Step 8: 프론트엔드 배너 + 설정 UI

**파일**: `frontend/src/components/main/OpsPanel.tsx`, `frontend/src/services/localClient.ts`, `frontend/src/pages/Settings.tsx`

- localClient: `/health` → `/api/health` 경로 수정 (선행 수정에서 누락 시 여기서)
- localClient: health 응답 타입에 `update_status` 추가
- OpsPanel: `update_status.available` 이면 상단 배너 표시
  - MAJOR 불일치: 빨간 배너 "로컬 서버 버전이 호환되지 않습니다"
  - MINOR/PATCH: 노란 배너 "업데이트 가능 (v0.2.0 → v0.3.0)"
- Settings: 자동 업데이트 ON/OFF 토글 + 업데이트 차단 시간 설정 (localConfig API)

**verify**: npm run build 성공 + E2E mock 업데이트 + 설정 변경 동작

### Step 9: /release 스킬 수정

**파일**: `.claude/commands/release.md`

- 릴리즈 산출물에 `StockVision-Bridge-Setup.exe.sha256` 추가
- `sha256sum` 또는 `certutil -hashfile` 으로 생성

**verify**: 릴리즈 스킬 실행 시 sha256 파일 생성 확인

### Step 10: 테스트

- updater 유닛 테스트 (version_checker, downloader, installer)
- health API update_status 테스트
- config 설정 키 테스트
- heartbeat 기본값 버그 수정 회귀 테스트
- 전체 기존 테스트 통과

## 위험 요소

| 리스크 | 완화 |
|--------|------|
| .bat 스크립트가 백신에 차단 | Inno Setup CloseApplications 방식 우선, .bat은 폴백 |
| GitHub API rate limit (60회/시간 비인증) | 시작 시 1회 + 1시간 간격, 하트비트 우선 사용 |
| 다운로드 중 디스크 부족 | 다운로드 전 여유 공간 확인 (인스톨러 ~50MB) |
| Inno Setup /SILENT가 UAC 팝업 | PrivilegesRequired=lowest 이미 설정됨 → UAC 불필요 |
