@echo off
REM StockVision Bridge 설치파일 빌드 + GitHub 릴리즈 업로드
REM 사전 조건: PyInstaller, Inno Setup 6, gh CLI 설치

setlocal
cd /d "%~dp0\.."

REM 버전 읽기
for /f "tokens=3 delims= """ %%v in ('findstr /C:"__version__" local_server\__version__.py') do set VERSION=%%v
echo [1/5] 버전: %VERSION%

REM PyInstaller 빌드
echo [2/5] PyInstaller 빌드 중...
pyinstaller local_server\pyinstaller.spec --noconfirm
if errorlevel 1 (
    echo PyInstaller 빌드 실패
    exit /b 1
)

REM Inno Setup 빌드
echo [3/5] Inno Setup 빌드 중...
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" local_server\installer.iss
if errorlevel 1 (
    echo Inno Setup 빌드 실패
    exit /b 1
)

set INSTALLER=dist\installer\StockVision-Bridge-Setup.exe
if not exist "%INSTALLER%" (
    echo 설치파일을 찾을 수 없습니다: %INSTALLER%
    exit /b 1
)

REM 기존 릴리즈 정리
echo [4/5] 기존 릴리즈 정리 중...
gh release delete v0.1.0-dev --yes >nul 2>&1
gh release delete v%VERSION% --yes >nul 2>&1
git push origin :refs/tags/v0.1.0-dev >nul 2>&1
git push origin :refs/tags/v%VERSION% >nul 2>&1
git tag -d v0.1.0-dev >nul 2>&1
git tag -d v%VERSION% >nul 2>&1

REM GitHub 릴리즈 생성 + 업로드
echo [5/5] GitHub 릴리즈 생성 중... (v%VERSION%)
gh release create v%VERSION% "%INSTALLER%" --title "v%VERSION% - StockVision Bridge" --notes "StockVision Bridge v%VERSION% 설치파일"
if errorlevel 1 (
    echo GitHub 업로드 실패. 수동 업로드: %INSTALLER%
    exit /b 1
)

echo 완료! https://github.com/wansu-ha/StockVision/releases/tag/v%VERSION%
