> 작성일: 2026-03-12 | 상태: 확정 | Unit 2 잔여

# 로컬 서버 exe 패키징 + 딥링크 — 구현 계획

## 아키텍처

```
[PyInstaller onedir]
  local_server/main.py (진입점)
    ├─ Named Mutex 체크 → 이미 실행 중이면 종료
    ├─ 파일 로깅 설정 → ~/.stockvision/logs/
    ├─ 포트 점유 감지 → 실패 시 토스트 + 종료
    ├─ 딥링크 프로토콜 등록/검증 → HKCU 레지스트리
    └─ lifespan (기존) → 트레이, 하트비트, 브로커 ...

[프론트엔드]
  BridgeInstaller.tsx
    ├─ health 폴링
    ├─ 실패 시 "서버 시작" 버튼 (딥링크)
    └─ 2초 후 미응답 → "설치 필요" 안내
```

## 수정 파일 목록

| 파일 | 변경 |
|------|------|
| `local_server/pyinstaller.spec` | onedir 전환, numpy/pandas excludes 제거, hiddenimports 추가 |
| `local_server/main.py` | Named Mutex, 포트 점유 감지, 파일 로깅, 딥링크 등록 호출, sys.argv 화이트리스트 |
| `local_server/utils/deeplink.py` | 신규: register_protocol(), verify_protocol() |
| `local_server/utils/mutex.py` | 신규: acquire_mutex(), Windows Named Mutex 래퍼 |
| `frontend/src/components/BridgeInstaller.tsx` | 딥링크 시작 버튼, 미설치 감지 로직 |

## 구현 순서

### Step 1: 파일 로깅 설정

`local_server/main.py`의 `configure_logging()` 수정.

변경:
- `~/.stockvision/logs/` 디렉토리 자동 생성
- `RotatingFileHandler` 추가 (console=False일 때도 로그 기록)
- 기존 basicConfig 유지 + 파일 핸들러 추가 (개발 시 콘솔도 출력)

verify:
- `python -m uvicorn local_server.main:app --port 4020` 실행 → `~/.stockvision/logs/server.log` 생성 확인

### Step 2: Named Mutex 다중 인스턴스 방지

`local_server/utils/mutex.py` 신규 생성.

변경:
- `acquire_mutex(name: str) -> bool` — `ctypes.windll.kernel32.CreateMutexW` 래퍼
- Windows 외 OS → 항상 True 반환 (no-op)
- `main.py`의 `__name__ == "__main__"` 블록에서 mutex 획득 후 실행

verify:
- exe(또는 uvicorn) 실행 중 → 같은 프로세스 두 번째 실행 시 즉시 종료 확인

### Step 3: 포트 점유 감지

`local_server/main.py`의 `__name__ == "__main__"` 블록에 추가.

변경:
- uvicorn 시작 전 `socket.bind(("127.0.0.1", port))` 시도
- 실패 시 토스트 알림 + logger.error + sys.exit(1)
- 성공 시 소켓 닫고 uvicorn에 위임

verify:
- 포트 4020에 다른 프로세스 띄워놓고 → 실행 시 토스트 표시 + 종료 확인

### Step 4: 딥링크 프로토콜 등록

`local_server/utils/deeplink.py` 신규 생성.

변경:
- `register_protocol()` — `HKCU\Software\Classes\stockvision` 레지스트리 키 생성
- `verify_protocol()` — 등록된 경로가 현재 exe와 일치하는지 확인
- `autostart.py`의 레지스트리 패턴 참고 (winreg 사용)
- `main.py`의 `__name__ == "__main__"` 블록에서 `verify_protocol()` → 불일치 시 `register_protocol()` 호출
- 개발 중: `python local_server/main.py`로 실행 → `sys.executable`이 python.exe를 가리킴 → 레지스트리에 python 경로 등록
- exe 빌드 후: exe 경로로 자동 갱신 (시작 시 verify → 재등록)

verify:
- 실행 후 `regedit`에서 `HKCU\Software\Classes\stockvision` 키 확인
- 브라우저 주소창에 `stockvision://launch` 입력 → exe 실행 확인

### Step 5: sys.argv 화이트리스트 검증

`local_server/main.py`의 `__name__ == "__main__"` 블록에 추가.

변경:
- `sys.argv`에서 `stockvision://` 접두사가 있으면 파싱
- `launch` 외 인자 무시 + 로그 경고
- 인자 없이 실행해도 정상 동작 (기본 = launch)

verify:
- `stockvision://launch` → 정상 시작
- `stockvision://--evil` → 경고 로그 + 정상 시작 (evil 무시)
- 인자 없이 실행 → 정상 시작

### Step 6: PyInstaller spec 수정 + 빌드

`local_server/pyinstaller.spec` 수정.

변경:
- onefile → onedir (EXE에서 a.binaries/a.zipfiles/a.datas를 COLLECT로 분리)
- excludes에서 `numpy`, `pandas` 제거
- hiddenimports에 `yfinance`, `packaging`, `winotify` 추가
- hiddenimports에 `local_server.utils.deeplink`, `local_server.utils.mutex` 추가

verify:
- `pyinstaller local_server/pyinstaller.spec` 빌드 성공
- `dist/stockvision-local/stockvision-local.exe` 더블클릭 → 트레이 아이콘 + `/health` 응답
- Named Mutex 동작 확인 (두 번째 실행 시 종료)
- `~/.stockvision/logs/server.log` 생성 확인

### Step 7: health 응답에 app 식별자 추가

`local_server/main.py`의 `health_check` 수정.

변경:
- 응답에 `"app": "stockvision"` 필드 추가
- 프론트엔드가 포트 겹침(다른 서버가 4020에 떠있는 경우)을 감지할 수 있게 함

verify:
- `GET /health` → `{"status": "ok", "version": "...", "app": "stockvision"}` 확인

### Step 8: 프론트엔드 딥링크 시작 버튼

`frontend/src/components/BridgeInstaller.tsx` 수정.

변경:
- health 응답에서 `app === "stockvision"` 검증 추가
- health 실패 또는 app 불일치 시 "서버 시작" 버튼 추가 (딥링크 호출)
- 클릭 → `window.location.href = 'stockvision://launch'`
- 2초 타이머: 페이지 유지 시 → "설치가 필요합니다" 메시지 + 다운로드 안내
- `localStorage`에 `sv_installed` 플래그 — 최초 연결 성공 시 설정
- 플래그 있으면 딥링크 우선, 없으면 설치 안내 우선

verify:
- 로컬 서버 꺼진 상태 → "서버 시작" 버튼 표시
- 클릭 → 서버 시작 → 자동 연결
- 미설치 상태 → 2초 후 설치 안내 표시
- `npm run build` 성공

## 검증 방법

| 항목 | 방법 |
|------|------|
| 빌드 | `pyinstaller local_server/pyinstaller.spec` 성공 |
| exe 실행 | 더블클릭 → 트레이 + health 응답 |
| 다중 인스턴스 | 두 번째 실행 → 즉시 종료 |
| 딥링크 | 브라우저에서 `stockvision://launch` → exe 시작 |
| 포트 감지 | 4020 점유 → 토스트 + 종료 |
| 파일 로깅 | `~/.stockvision/logs/server.log` 존재 |
| health app 필드 | `GET /health` 응답에 `app: "stockvision"` 포함 |
| 프론트엔드 | 서버 꺼짐 → 시작 버튼 → 연결 성공 |
| 프론트엔드 빌드 | `npm run build` 성공 |
