> 작성일: 2026-03-13 | 상태: 구현 완료 | inno-installer

# Inno Setup 설치 프로그램

## 목표

PyInstaller onedir 결과물(exe + _internal 99파일)을 Inno Setup으로 포장하여
**단일 설치파일(.exe)**을 배포한다.
사용자는 설치파일 하나만 다운로드하고, "다음 다음 설치"로 완료.

## 현재 상태

- PyInstaller onedir 빌드: `dist/stockvision-local/` (exe 21MB, 폴더 121MB)
- GitHub 릴리즈 `v0.1.0-dev`: `stockvision-local.zip` (48.9MB) 업로드 완료
- BridgeInstaller 다운로드 링크: `/releases/latest/download/stockvision-local.zip`
- 딥링크 프로토콜: exe 실행 시 `register_protocol()`로 HKCU 등록

## 요구사항

### 기능적

1. **Inno Setup 스크립트 (.iss) 작성**
   - 소스: `dist/stockvision-local/` 폴더 전체
   - 설치 경로: `{localappdata}\StockVision` (현재 BridgeInstaller 안내 경로와 일치)
   - 앱 이름: StockVision Bridge
   - 버전: `local_server/__version__.py`에서 가져옴 (현재 `0.1.0`)

2. **설치 시 자동 처리**
   - 시작메뉴 바로가기: `StockVision Bridge`
   - 바탕화면 아이콘: 선택 옵션 (체크박스)
   - 딥링크 프로토콜 등록: `stockvision://` → exe 경로 (HKCU 레지스트리)
     - exe 내부 `register_protocol()`과 동일한 키 경로 사용
   - 설치 완료 후 자동 실행 옵션 (체크박스, 기본 ON)

3. **언인스톨러**
   - Inno Setup 기본 언인스톨러 자동 생성
   - 언인스톨 시 딥링크 레지스트리 키 제거
   - 사용자 데이터(`~/.stockvision/`)는 삭제하지 않음

4. **출력물**
   - 파일명: `StockVision-Bridge-Setup-{version}.exe` (예: `StockVision-Bridge-Setup-0.1.0.exe`)
   - 출력 경로: `dist/installer/`

5. **GitHub 릴리즈 업데이트**
   - ZIP 대신 설치파일(.exe)을 릴리즈 asset으로 업로드
   - BridgeInstaller 다운로드 링크 변경: `.zip` → `.exe`

### 비기능적

- Inno Setup 6 기준 (현재 최신)
- `.iss` 파일은 `local_server/installer.iss`에 위치
- 빌드 순서: PyInstaller → Inno Setup (2단계)
- 아이콘: 현재 없음 → Inno Setup 기본 아이콘 사용 (추후 커스텀 아이콘 추가 가능)

## 수용 기준

- [ ] `installer.iss` 스크립트 작성 완료
- [ ] Inno Setup 빌드 → 단일 설치파일 생성
- [ ] 설치 → `{localappdata}\StockVision\`에 파일 배치 확인
- [ ] 시작메뉴 바로가기 생성 확인
- [ ] 딥링크 `stockvision://launch` → exe 실행 확인
- [ ] 언인스톨 → 파일 제거 + 레지스트리 정리 확인
- [ ] BridgeInstaller 다운로드 링크가 `.exe`를 가리킴
- [ ] GitHub 릴리즈에 설치파일 업로드

## 범위

### 포함
- Inno Setup 스크립트 작성
- BridgeInstaller 다운로드 링크 변경 (`.zip` → `.exe`)
- GitHub 릴리즈 asset 교체

### 미포함
- PyInstaller onefile 전환 (onedir 유지)
- 자동 업데이트 기능
- 코드 사이닝 (code signing)
- 커스텀 아이콘 제작

## API/DB 변경

없음.

## 참고

- `local_server/pyinstaller.spec` — PyInstaller 빌드 설정
- `local_server/__version__.py` — 버전 원천 (`0.1.0`)
- `local_server/utils/deeplink.py` — 딥링크 레지스트리 등록 로직 (iss에서 동일 키 사용)
- `frontend/src/components/BridgeInstaller.tsx:120` — 다운로드 링크 (수정 대상)
- `cloud_server/core/config.py:81-84` — `LOCAL_SERVER_DOWNLOAD_URL` (수정 대상)
