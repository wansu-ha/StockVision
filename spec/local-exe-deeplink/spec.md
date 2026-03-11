> 작성일: 2026-03-11 | 상태: 확정 | Unit 2 잔여

# 로컬 서버 exe 패키징 + 딥링크

## 1. 목표

로컬 서버를 Windows 실행파일(.exe)로 패키징한다.
딥링크(`stockvision://`)를 등록하여 프론트엔드에서 로컬 서버가 꺼져 있을 때 시작을 요청할 수 있게 한다.
최종 배포는 인스톨러(별도 spec)로 감싸서 진행 — 이 spec은 exe 빌드 + 딥링크까지가 범위.

## 2. 요구사항

### 2.1 기능적 요구사항

| ID | 요구사항 |
|----|---------|
| F1 | PyInstaller `--onedir` 모드로 exe + 의존성 폴더 생성 |
| F2 | 콘솔 창 숨김 (`console=False`) — 트레이 앱으로만 동작 |
| F3 | sv_core 패키지를 exe 내에 번들 |
| F4 | 실행 시 `stockvision://` 커스텀 프로토콜을 Windows 레지스트리에 등록 (+ 시작 시 검증) |
| F5 | 프론트엔드: 로컬 서버 미응답 시 딥링크로 시작 요청 버튼 표시 |
| F6 | 다중 인스턴스 방지 — Named Mutex로 이미 실행 중이면 종료 |
| F7 | `~/.stockvision/` 디렉토리 자동 생성 (config.json, logs.db) |
| F8 | 파일 로깅 (`~/.stockvision/logs/`) — console=False 시 stdout/stderr 대체 |
| F9 | 포트 4020 점유 시 시작 실패 + 토스트 알림 ("포트 4020이 사용 중입니다") |

### 2.2 비기능적 요구사항

| ID | 요구사항 |
|----|---------|
| NF1 | 서버 시작 시간 < 5초 |
| NF2 | 메모리 사용량 < 200MB (아이들) |
| NF3 | Windows 10/11 지원 |

## 3. 수용 기준

- [ ] `pyinstaller local_server/pyinstaller.spec` 빌드 성공
- [ ] 생성된 exe 더블클릭 → 트레이 아이콘 표시 + `/health` 응답
- [ ] 두 번째 exe 실행 시 기존 프로세스 유지, 신규 프로세스 종료 (Named Mutex)
- [ ] `stockvision://launch` 브라우저 주소창 입력 → exe 실행
- [ ] 프론트엔드 BridgeInstaller에서 "시작" 버튼 → 딥링크 호출 → 서버 시작 → 자동 연결
- [ ] exe 종료 후 재시작 시 `~/.stockvision/config.json` 유지
- [ ] 포트 4020 점유 시 토스트 알림 표시 + 정상 종료
- [ ] `~/.stockvision/logs/` 에 로그 파일 생성 확인

## 4. 설계

### 4.1 PyInstaller 설정 수정

기존 `local_server/pyinstaller.spec` 수정:

- **onefile → onedir 전환** — 인스톨러 배포 결정으로 onefile 불필요, 시작 속도 향상
- **numpy/pandas excludes 제거** — `indicator_provider.py`가 pandas 의존
- **yfinance, packaging hiddenimports 추가**
- **ico 파일** — `assets/tray_icon.ico` 생성 및 적용 (선택적)

### 4.2 다중 인스턴스 방지

`local_server/main.py` 시작 시 Windows Named Mutex 사용:

```
CreateMutexW("StockVision_LocalServer")
  ├─ 성공 (새로 생성) → 정상 시작
  └─ ERROR_ALREADY_EXISTS → 이미 실행 중 → 종료
```

Named Mutex는 프로세스 크래시 시에도 OS가 자동 해제 → file lock의 잔류 문제 없음.

### 4.3 딥링크 등록

`local_server/utils/deeplink.py` 신규:

```python
def register_protocol() -> None:
    """stockvision:// 프로토콜을 Windows 레지스트리에 등록."""
    # HKCU\Software\Classes\stockvision
    #   (Default) = "URL:StockVision Protocol"
    #   URL Protocol = ""
    #   \shell\open\command
    #     (Default) = "exe경로" "%1"

def verify_protocol() -> bool:
    """레지스트리의 프로토콜 경로가 현재 exe와 일치하는지 검증."""
```

- `sys.executable`로 현재 exe 경로 획득
- 매 실행 시 검증 → 불일치 시 재등록 + 로그 경고
- 관리자 권한 불필요 (HKCU에 등록)

### 4.4 프론트엔드 연결 흐름

기존 `BridgeInstaller.tsx` 수정:

```
health 체크 실패 (서버 꺼짐)
  → "서버 시작" 버튼 표시
  → 클릭 시 window.location.href = 'stockvision://launch'
  → 2초 후 앱이 안 열리면 "설치가 필요합니다" + 설치 안내 표시
  → 5초 폴링 계속
  → 서버 응답 오면 자동 전환
```

### 4.5 exe 시작 인자

딥링크에서 전달하는 URL (`stockvision://launch`)을 `sys.argv`로 수신:
- `stockvision://launch` → 서버 시작 (기본 동작과 동일)
- **화이트리스트 검증**: `launch` 외 모든 인자 무시 (URI 인자 주입 방어)

### 4.6 포트 점유 감지

서버 시작 전 4020 포트 바인딩 시도:
- 성공 → 정상 시작
- 실패 (EADDRINUSE) → 토스트 알림 + 로그 + 종료
- 자동 포트 전환은 하지 않음 (프론트엔드가 포트를 알 수 없으므로)

## 5. 위협 모델

| 위협 | 심각도 | 방어 | 비고 |
|------|--------|------|------|
| 악성 사이트가 `stockvision://` 호출 | 낮음 | 브라우저 확인 다이얼로그 (OS 기본) | 실행돼도 서버 시작일 뿐, 위험 동작 아님 |
| 딥링크 URI 인자 주입 (`stockvision://--evil`) | 중간 | `sys.argv` 화이트리스트 검증 — `launch` 외 무시 | 인자 파싱 최소화 원칙 |
| 프로토콜 레지스트리 변조 (다른 exe로 교체) | 낮음 | 시작 시 레지스트리 경로 검증 + 불일치 시 재등록 | 웹에서 레지스트리 접근 불가, 로컬 악성코드만 가능 |
| 로컬 프로세스의 API 무단 접근 | 낮음 | local_secret (매 실행 생성, 메모리 전용, timing-safe 비교) | 업계 표준 수준 (VS Code, Docker Desktop 등 동일 구조) |
| 포트 스쿼팅 (악성 앱이 4020 선점) | 중간 | 포트 점유 감지 + 토스트 경고 | 프론트가 진짜 서버인지 검증 불가 — 로컬 앱 공통 한계 |
| SmartScreen 경고 (서명 미적용) | 낮음 | 오픈소스 공개 후 SignPath.io 무료 서명 | 배포 시 별도 처리 |
| 백신 오탐 (PyInstaller exe 차단) | 중간 | 코드 서명 + 주요 백신사 false positive 신고 | 배포 시 별도 처리 |

**설계 전제**: 로컬 악성코드(같은 Windows 계정 권한)는 앱 레벨 방어 대상이 아님. 모든 데스크톱 앱(증권 HTS, 브라우저, 패스워드 관리자)이 동일한 한계를 가지며, OS 사용자 세션 격리 + DPAPI(keyring)가 업계 표준 방어선.

## 6. 범위

### 포함

- PyInstaller onedir 빌드 + 검증
- 다중 인스턴스 방지 (Named Mutex)
- 딥링크 레지스트리 등록 + 시작 시 검증
- 프론트엔드 딥링크 시작 버튼 + 미설치 감지
- URI 인자 화이트리스트 검증
- 파일 로깅 설정
- 포트 점유 감지 + 알림

### 미포함

- 인스톨러 (MSI/NSIS) — 별도 spec (딥링크 등록, 약관 동의, 언인스톨 포함)
- 자동 업데이트 — 별도 spec
- 코드 서명 + 백신 화이트리스트 — 오픈소스 공개 후 배포 시 별도 처리
- macOS/Linux 지원 — Windows 전용
- 약관 동의 UI — 인스톨러 spec에서 처리 (설치 시 약관 표시, 레지스트리 변경 고지 포함)
- 라이선스 고지 (번들 의존성 OSS 라이선스) — 인스톨러 spec에서 NOTICE 파일로 처리

## 7. 변경 파일 (예상)

| 파일 | 변경 |
|------|------|
| `local_server/pyinstaller.spec` | onedir 전환, excludes 수정, hiddenimports 추가 |
| `local_server/main.py` | Named Mutex 다중 인스턴스 방지, 포트 점유 감지, 파일 로깅 설정 |
| `local_server/utils/deeplink.py` | 신규: 프로토콜 등록 + 검증 |
| `frontend/src/components/BridgeInstaller.tsx` | 딥링크 시작 버튼 + 미설치 감지 |

## 8. 참고

- 기존 PyInstaller 설정: `local_server/pyinstaller.spec`
- 자동 시작 구현: `local_server/utils/autostart.py` (레지스트리 패턴 참고)
- 프론트엔드 연결 감지: `frontend/src/components/BridgeInstaller.tsx`
- 트레이 아이콘: `local_server/tray/tray_app.py` (이미 완성)
- 설정 파일: `local_server/config.py` (`~/.stockvision/config.json`)
