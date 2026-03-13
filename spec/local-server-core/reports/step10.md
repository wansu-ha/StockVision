# Step 10 보고서: PyInstaller .exe 번들 설정

## 생성/수정된 파일

- `local_server/pyinstaller.spec` — PyInstaller 단일 .exe 번들 설정

## 구현 내용 요약

### pyinstaller.spec
- 진입점: `local_server/main.py`
- 출력: `dist/stockvision-local/stockvision-local.exe`
- 단일 .exe (onefile 모드 아닌 EXE 직접 구성 — 시작 속도 vs 크기 트레이드오프)

### 주요 설정
- `console=False`: 콘솔 창 숨김 (트레이 앱이므로)
- `hiddenimports`: 동적 임포트 되는 모듈 명시
  - pystray._win32, keyring.backends.Windows
  - uvicorn 내부 모듈 (auto 프로토콜 선택기)
  - FastAPI, httpx, PIL
- `excludes`: tkinter, matplotlib, numpy, pandas 제외 (크기 절감)
- `datas`: sv_core 패키지 포함

### 빌드 방법
```bash
pip install pyinstaller
pyinstaller local_server/pyinstaller.spec
```

## 리뷰 발견 사항

- uvicorn의 auto 모듈들은 importlib 기반 동적 로딩이므로 hiddenimports 필수
- pystray는 Windows에서 pystray._win32를 내부적으로 import
- keyring도 플랫폼별 백엔드를 동적으로 선택하므로 hiddenimports 필요
- console=False이므로 오류 발생 시 로그 파일 확인이 유일한 디버그 수단
  - configure_logging()에서 파일 핸들러 추가 권장 (추후 개선 항목)

## 테스트 결과

- spec 파일 Python 문법 검증: 정상
- 실제 빌드는 pyinstaller 설치 후 수동으로 수행해야 함
