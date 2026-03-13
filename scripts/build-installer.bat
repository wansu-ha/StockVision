@echo off
chcp 65001 >nul
REM StockVision Bridge installer build + GitHub release upload
REM Prerequisites: PyInstaller, Inno Setup 6, gh CLI

setlocal

cd /d "%~dp0\.."

REM Read version
for /f "usebackq tokens=2 delims='" %%v in (`findstr /C:"__version__" local_server\__version__.py`) do set "VERSION=%%v"
echo [1/6] Version: %VERSION%
if "%VERSION%"=="" (
    echo Version parsing failed. Check local_server\__version__.py
    exit /b 1
)

REM Clean old build
echo [2/6] Cleaning old build...
if exist dist\stockvision-local rd /s /q dist\stockvision-local
if exist dist\installer rd /s /q dist\installer

REM PyInstaller build
echo [3/6] PyInstaller build...
pyinstaller local_server\pyinstaller.spec --noconfirm
if errorlevel 1 (
    echo PyInstaller build failed
    exit /b 1
)

REM Find Inno Setup
set "ISCC="
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if "%ISCC%"=="" (
    echo Inno Setup 6 not found. Install it first.
    exit /b 1
)

REM Inno Setup build
echo [4/6] Inno Setup build...
"%ISCC%" local_server\installer.iss
if errorlevel 1 (
    echo Inno Setup build failed
    exit /b 1
)

set "INSTALLER=dist\installer\StockVision-Bridge-Setup.exe"
if not exist "%INSTALLER%" (
    echo Installer not found: %INSTALLER%
    exit /b 1
)

REM Find gh CLI
set "GH=gh"
where gh >nul 2>&1
if errorlevel 1 (
    if exist "C:\Program Files\GitHub CLI\gh.exe" (
        set "GH=C:\Program Files\GitHub CLI\gh.exe"
    ) else (
        echo gh CLI not found. Install it first.
        exit /b 1
    )
)

REM Clean old releases
echo [5/6] Cleaning old releases...
"%GH%" release delete v0.1.0-dev --yes >nul 2>&1
"%GH%" release delete v%VERSION% --yes >nul 2>&1
git push origin :refs/tags/v0.1.0-dev >nul 2>&1
git push origin :refs/tags/v%VERSION% >nul 2>&1
git tag -d v0.1.0-dev >nul 2>&1
git tag -d v%VERSION% >nul 2>&1

REM Create GitHub release + upload
echo [6/6] Creating GitHub release... (v%VERSION%)
"%GH%" release create v%VERSION% "%INSTALLER%" --title "v%VERSION% - StockVision Bridge" --notes "StockVision Bridge v%VERSION% installer"
if errorlevel 1 (
    echo GitHub upload failed. Manual upload: %INSTALLER%
    exit /b 1
)

echo Done! https://github.com/wansu-ha/StockVision/releases/tag/v%VERSION%
