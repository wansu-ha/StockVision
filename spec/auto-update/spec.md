> 작성일: 2026-03-28 | 상태: 초안

# 로컬 서버 자동 업데이트

## 배경

프론트엔드(Vercel)는 자동 배포되지만 로컬 서버(exe)는 수동 업데이트.
버전 불일치 시 `Invalid local secret` 등 호환성 문제 발생.
현재는 토스트 알림만 있고, 다운로드/설치는 사용자가 직접 해야 함.

## 목표

1. 버전 호환성 체크로 불일치 시 안내
2. GitHub Releases에서 최신 버전 감지 + 백그라운드 다운로드
3. 허용 시간 내 자동 설치 + 재시작
4. 업데이트 전 백업 보관

## 버전 규칙

| 버전 구성 | 의미 | 예시 |
|----------|------|------|
| MAJOR.MINOR.PATCH | SemVer | 0.2.0, 1.0.0 |
| **MAJOR 동일** | 호환 가능 — 경고만 | 0.2.0 ↔ 0.5.0 ✅ |
| **MAJOR 다름** | 호환 불가 — 강제 안내 | 0.x ↔ 1.x ⚠️ |

- MAJOR 변경 = API 계약 변경 (경로, 인증 방식 등)
- MINOR 변경 = 기능 추가 (하위 호환)
- PATCH 변경 = 버그 수정

### 버전 단일 원천

`local_server/__version__.py`가 유일한 버전 소스.
- `config.json`의 `server.version` 키는 사용하지 않음 (제거 대상)
- heartbeat 응답의 `version` 필드도 `__version__`에서 읽음
- 선행 수정:
  - `heartbeat.py:63 _build_heartbeat_payload` — `cfg.get("server.version", _VERSION)` → `_VERSION` 직접 사용
  - `heartbeat.py:198 _check_server_version` — 기본값 `"1.0.0"` → `_VERSION` 교체

## 버전 체크 소스

| 소스 | 용도 | 시점 |
|------|------|------|
| **클라우드 하트비트 응답** (`latest_version`) | 주기적 체크 (30초~1분) | 우선 |
| **GitHub Releases API** | 서버 시작 시 1회 + 클라우드 미연결 시 폴백 | 폴백 |

클라우드가 연결돼 있으면 하트비트로 감지 (추가 API 호출 불필요).
클라우드 미연결 시 GitHub API로 직접 확인.

## 흐름

```
서버 시작
  → GitHub Releases API로 최신 버전 확인 (1회)
  → 이후: 클라우드 하트비트 응답의 latest_version으로 감지

  → 현재 == 최신? → 아무것도 안 함
  → 현재 < 최신?
      → MAJOR 동일? → "업데이트 가능" 트레이 🟡 + OpsPanel 배너
      → MAJOR 다름? → "업데이트 필요" 트레이 🔴 + OpsPanel 경고 배너
      → 자동 업데이트 ON?
          → 백그라운드 다운로드 (인스톨러 + SHA256)
          → SHA256 검증 실패? → 임시 파일 삭제 + 재다운로드
          → 다운로드 완료
          → 허용 시간 내?
              → backup/ 보관
              → 현재 프로세스 종료 (SIGTERM)
              → 인스톨러 /SILENT 실행
              → 인스톨러가 재시작
          → 허용 시간 외? → 대기 → 허용 시간 진입 시 설치
```

## 설치 시퀀스 (Windows 파일 잠금 대응)

실행 중인 exe는 Windows가 파일 잠금을 걸어 덮어쓸 수 없다.

```
1. updater: 임시 .bat 스크립트 생성
   @echo off
   timeout /t 3 /nobreak >nul
   start "" "{다운로드된 인스톨러}" /SILENT /SUPPRESSMSGBOXES
   del "%~f0"

2. updater: .bat 실행 (detached process)
3. updater: 현재 서버 프로세스 종료 (sys.exit)
4. .bat: 3초 대기 → 인스톨러 실행 → 자신 삭제
5. Inno Setup /SILENT: 파일 교체 → [Run] 섹션으로 서버 재시작
```

Inno Setup 수정:
- `CloseApplications=yes` 추가
- `[Run]` 섹션의 `skipifsilent` 플래그 제거 → /SILENT 모드에서도 서버 재시작 실행
- `RestartApplications` 불사용 (sys.exit으로 먼저 종료하므로 Inno가 추적 불가)

## 설정

| 키 | 기본값 | 설명 |
|----|--------|------|
| `update.auto_enabled` | `true` | 자동 다운로드 + 설치 |
| `update.no_update_start` | `"08:00"` | 이 시간부터 업데이트 차단 |
| `update.no_update_end` | `"17:00"` | 이 시간까지 업데이트 차단 |

- 업데이트 허용 시간 = `17:00 ~ 08:00` (no_update 구간 바깥)
- 장 마감(15:30) + 시간외(~16:00) 이후 여유
- 설정 UI: 프론트 설정 페이지에서 변경 가능 (localConfig API 경유)

## 알림

### 트레이
- 업데이트 가능: 아이콘 🟡 + 토스트 "새 버전 v0.3.0 사용 가능"
- 업데이트 필요 (MAJOR 차이): 아이콘 🔴 + 토스트 "업데이트가 필요합니다"
- 다운로드 완료: 토스트 "업데이트 준비됨. 허용 시간에 자동 설치됩니다"
- 자동 업데이트 OFF: 토스트 "새 버전 v0.3.0. 설정에서 업데이트하세요"

### 웹 (OpsPanel)

데이터 흐름:
- 로컬 서버 `GET /api/health` 응답에 `update_status` 필드 추가
  ```json
  {
    "status": "healthy",
    "version": "0.2.0",
    "update_status": {
      "available": true,
      "latest": "0.3.0",
      "major_mismatch": false,
      "download_progress": 0.75,
      "ready_to_install": false
    }
  }
  ```
- 프론트: `useLocalHealth` 훅에서 `update_status` 읽기 → OpsPanel 배너 렌더링

표시:
- 상단 배너: "로컬 서버 업데이트 가능 (v0.2.0 → v0.3.0)"
- MAJOR 불일치: 경고 배너 (빨간색) "로컬 서버 버전이 호환되지 않습니다"

## 다운로드 소스

- `GET https://api.github.com/repos/wansu-ha/StockVision/releases/latest`
- asset 중 `StockVision-Bridge-Setup.exe` + `StockVision-Bridge-Setup.exe.sha256` 선택
- pre-release 제외 (향후 베타 채널 추가 시 옵션)

### 무결성 검증

- 릴리즈 시 `sha256sum` 파일을 asset에 함께 업로드
- 다운로드 후 SHA256 해시 비교 → 불일치 시 파일 삭제 + 재다운로드
- `/release` 스킬에 sha256 생성 단계 추가

## 백업

- 설치 전 현재 exe 디렉토리를 `{install_dir}/backup/v{현재버전}/`에 복사
  - `{install_dir}` = `{localappdata}/StockVision` (installer.iss DefaultDirName)
- 최근 2개 버전만 보관 (디스크 절약)
- 롤백은 수동 (backup/에서 복원 또는 GitHub에서 재다운로드)

## 다운로드 실패/중단 처리

- 다운로드는 임시 디렉토리(`{install_dir}/temp/`)에 저장
- 앱 종료 시 불완전 파일 잔류 → 다음 시작 시 임시 파일 삭제 + 재다운로드
- 네트워크 에러 시 5분 후 재시도 (최대 3회)
- SHA256 불일치 시 파일 삭제 + 재다운로드

## 수용 기준

- [ ] 서버 시작 시 GitHub Releases에서 최신 버전 감지
- [ ] 하트비트 응답의 latest_version으로 주기적 감지
- [ ] 현재 < 최신이면 트레이 🟡 + OpsPanel 배너
- [ ] MAJOR 불일치면 트레이 🔴 + 경고 배너
- [ ] auto_enabled=true 시 백그라운드 다운로드
- [ ] 다운로드 후 SHA256 검증
- [ ] 허용 시간 내 자동 설치 (프로세스 종료 → .bat → 인스톨러)
- [ ] 설치 전 {install_dir}/backup/ 보관 (최근 2개)
- [ ] auto_enabled=false 시 알림만, 설치 안 함
- [ ] 설정 UI에서 auto_enabled / no_update 시간 변경 가능
- [ ] MAJOR 동일하면 엔진 실행 허용 (경고만)
- [ ] 다운로드 중단 시 임시 파일 정리 (재시작 시)
- [ ] GET /api/health에 update_status 포함
- [ ] 기존 테스트 전체 통과

## 변경 대상

| 파일 | 변경 |
|------|------|
| local_server/updater/ | 신규 — 버전 체크, 다운로더, 설치 로직 |
| local_server/updater/installer.bat.template | 신규 — 설치 시퀀스 템플릿 |
| local_server/tray/tray_app.py | 아이콘 색상 + 메뉴에 "업데이트" 항목 |
| local_server/main.py | startup에 업데이트 체크 등록 |
| local_server/routers/health.py | /api/health에 update_status 추가 |
| local_server/storage/config_store.py | update.* 설정 키 추가 |
| local_server/cloud/heartbeat.py | _check_server_version 기본값 버그 수정 |
| local_server/installer.iss | CloseApplications=yes 추가 |
| frontend/src/components/main/OpsPanel.tsx | 업데이트 배너 |
| frontend/src/services/localClient.ts | `/health` → `/api/health` 경로 수정 + update_status 타입 |
| frontend/src/pages/Settings.tsx | 자동 업데이트 ON/OFF + 허용 시간 설정 UI |
| .claude/commands/release.md | sha256 생성 단계 추가 |

## 버전 불일치 시 엔진 동작

- **MAJOR 동일**: 엔진 실행 허용, 경고 배너만 표시
- **MAJOR 다름**: 엔진 실행 허용, 강한 경고 배너 (엔진 차단은 하지 않음)
- 차단하지 않는 이유: 업데이트 불가 상황(네트워크 없음 등)에서도 기존 전략은 돌아가야 함

## 클라우드 서버 download_url

현재 하트비트 응답에 `download_url` 필드가 있으나 빈 문자열.
- 클라우드 서버 수정 없이 진행: `download_url`이 비어있으면 GitHub API로 URL 조회
- 향후 클라우드에서 `download_url`을 채우면 GitHub API 폴백 불필요

## 선행 수정 (기존 코드 버그)

- `heartbeat.py:63` — `cfg.get("server.version", _VERSION)` → `_VERSION` 직접 사용
- `heartbeat.py:198` — `get_config().get("server.version", "1.0.0")` → `_VERSION` 사용
- `localClient.ts:188` — `GET /health` → `GET /api/health` 경로 수정
- `config.json`에 `server.version` 키가 있으면 제거
