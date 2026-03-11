# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 번들 설정.

onedir 모드로 로컬 서버를 패키징한다.
빌드 명령: pyinstaller local_server/pyinstaller.spec

출력: dist/stockvision-local/stockvision-local.exe
"""
import sys
from pathlib import Path

# 프로젝트 루트 (pyinstaller.spec 위치의 상위)
ROOT = Path(SPECPATH).parent  # noqa: F821 — PyInstaller 내장 변수

block_cipher = None

a = Analysis(
    # 진입점: local_server.main 모듈
    scripts=[str(ROOT / "local_server" / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        # sv_core 패키지 포함
        (str(ROOT / "sv_core"), "sv_core"),
    ],
    hiddenimports=[
        # pystray는 런타임에 플랫폼별 백엔드를 동적 임포트
        "pystray._win32",
        # keyring 백엔드
        "keyring.backends.Windows",
        "keyring.backends.fail",
        # aiosqlite
        "aiosqlite",
        # uvicorn 내부 모듈
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        # FastAPI / Starlette
        "fastapi",
        "starlette",
        # httpx
        "httpx",
        # PIL (pystray 아이콘 생성)
        "PIL",
        "PIL.Image",
        "PIL.ImageDraw",
        # yfinance + 의존성
        "yfinance",
        "packaging",
        # 토스트 알림
        "winotify",
        # 딥링크 + 뮤텍스
        "local_server.utils.deeplink",
        "local_server.utils.mutex",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 불필요한 대형 패키지 제외
        "tkinter",
        "matplotlib",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="stockvision-local",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,         # 콘솔 창 숨김 (트레이 앱이므로)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Windows 아이콘 (선택적 — 파일이 없으면 기본 아이콘 사용)
    # icon=str(ROOT / "assets" / "tray_icon.ico"),
    version_file=None,
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="stockvision-local",
)
