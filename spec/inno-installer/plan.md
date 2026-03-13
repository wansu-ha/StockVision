> 작성일: 2026-03-13 | 상태: 구현 완료 | inno-installer

# Inno Setup 설치 프로그램 — 구현 계획

## 아키텍처

```
PyInstaller onedir 빌드
  dist/stockvision-local/       ← 입력
      stockvision-local.exe
      _internal/ (99파일)

Inno Setup 컴파일
  local_server/installer.iss    ← 스크립트
      ↓
  dist/installer/
      StockVision-Bridge-Setup-0.1.0.exe  ← 출력 (단일 파일)
```

설치 시:
```
{localappdata}\StockVision\
  stockvision-local.exe
  _internal/
  unins000.exe (자동 생성)
```

레지스트리:
```
HKCU\Software\Classes\stockvision\            "URL:stockvision Protocol"
HKCU\Software\Classes\stockvision\shell\open\command   "...exe" "%1"
```

## 수정 파일 목록

| 파일 | 변경 |
|------|------|
| `local_server/installer.iss` | **신규** — Inno Setup 스크립트 |
| `frontend/src/components/BridgeInstaller.tsx` | 다운로드 링크 `.zip` → `.exe` |
| `cloud_server/core/config.py` | `LOCAL_SERVER_DOWNLOAD_URL` 기본값 수정 |

## 구현 순서

### Step 1: Inno Setup 스크립트 작성

`local_server/installer.iss` 생성:

- `[Setup]` 섹션: 앱 이름, 버전, 설치 경로, 출력 파일명
- `[Files]` 섹션: `dist/stockvision-local/` 하위 전체 복사
- `[Icons]` 섹션: 시작메뉴 + 바탕화면(선택) 바로가기
- `[Registry]` 섹션: `stockvision://` 딥링크 프로토콜 등록
  - `deeplink.py`의 `_REG_KEY_PATH`와 동일한 경로 사용
  - `UninsDeleteKey` 플래그로 언인스톨 시 자동 제거
- `[Run]` 섹션: 설치 완료 후 exe 실행 옵션 (`postinstall`)
- `[UninstallDelete]` 섹션: 로그 파일 등 런타임 생성물 정리 (사용자 데이터 `~/.stockvision/`은 미삭제)

**verify**: `.iss` 파일이 유효한 Inno Setup 6 문법인지 확인

### Step 2: 다운로드 링크 변경

`BridgeInstaller.tsx:120`:
```
stockvision-local.zip → StockVision-Bridge-Setup-0.1.0.exe
```

다운로드 버튼 텍스트:
```
"StockVision 다운로드 (.zip)" → "StockVision 설치파일 다운로드"
```

`config.py` `LOCAL_SERVER_DOWNLOAD_URL` 기본값:
```
https://github.com/wansu-ha/StockVision/releases/latest/download/StockVision-Bridge-Setup-0.1.0.exe
```

**verify**: 프론트엔드 빌드 (`npm run build`) 성공

### Step 3: Inno Setup 빌드 & 릴리즈

이 단계는 수동 실행 (로컬 PC에서):

1. Inno Setup 6 설치 (없으면)
2. PyInstaller 빌드: `pyinstaller local_server/pyinstaller.spec`
3. Inno Setup 컴파일: `iscc local_server/installer.iss`
4. 출력 확인: `dist/installer/StockVision-Bridge-Setup-0.1.0.exe`
5. GitHub 릴리즈 생성 + asset 업로드

**verify**: 설치파일 실행 → 설치 → exe 실행 → `/health` 응답 → 딥링크 동작

## 검증 방법

| 항목 | 방법 |
|------|------|
| iss 문법 | Inno Setup 컴파일 에러 없음 |
| 설치 경로 | `%LOCALAPPDATA%\StockVision\stockvision-local.exe` 존재 |
| 시작메뉴 | 시작메뉴에 "StockVision Bridge" 표시 |
| 딥링크 | 브라우저에서 `stockvision://launch` → exe 실행 |
| 언인스톨 | 제어판에서 삭제 → 파일 제거 + 레지스트리 정리 |
| 프론트엔드 | 빌드 성공, 다운로드 링크 `.exe` 확인 |
