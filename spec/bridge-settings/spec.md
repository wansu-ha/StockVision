> 작성일: 2026-03-13 | 상태: 구현 완료 | bridge-settings

# Bridge 상태 & 다운로드 — 설정 페이지

## 목표

온보딩 완료 후에도 Bridge(로컬 서버) 다운로드/실행 안내에 접근할 수 있게 한다.
현재는 온보딩 위저드에서만 `BridgeInstaller`를 보여주고, 완료 후 설정 페이지에는 Bridge 관련 UI가 없다.

## 요구사항

### 기능적

1. **설정 페이지 최상단에 "로컬 서버 (Bridge)" 섹션 추가**
   - "엔진 상태" 섹션 위에 배치 (Bridge가 선행 조건)

2. **Bridge 미연결 시 표시 내용**
   - 상태: "미연결" (빨간/노란 인디케이터)
   - 다운로드 링크: GitHub releases latest (`stockvision-local.zip`)
   - "서버 시작" 버튼 (딥링크 `stockvision://launch`) — 이전 설치 이력 있을 때만
   - 수동 실행 경로 안내 (`%LOCALAPPDATA%\StockVision\stockvision-local.exe`)

3. **Bridge 연결 시 표시 내용**
   - 상태: "연결됨" (초록 인디케이터)
   - 서버 업타임 표시 (useAccountStatus의 `raw.server.uptime`)

4. **연결 감지**
   - `localReady` 상태와 무관하게 `/health` 직접 폴링 (10초 간격)
   - AuthContext의 `localReady`는 토큰 동기화 성공 여부이므로, Bridge 물리적 연결은 별도 체크 필요

### 비기능적

- 기존 `BridgeInstaller` 컴포넌트를 **재사용하지 않음** — 온보딩용 3단계 위저드 UI와 설정용 상태 카드는 UX가 다름
- 설정 페이지의 기존 스타일(회색 카드, rounded-xl, border)에 맞춤
- 폴링은 설정 페이지에 있을 때만 활성

## 수용 기준

- [ ] 설정 페이지에 "로컬 서버" 섹션이 "엔진 상태" 위에 표시됨
- [ ] Bridge 미실행 시: 다운로드 링크 + 실행 안내 표시
- [ ] Bridge 실행 시: "연결됨" + 업타임 표시
- [ ] Bridge 시작/종료 시 UI가 자동으로 갱신됨 (폴링)
- [ ] 기존 온보딩 플로우에 영향 없음

## 범위

### 포함
- Settings.tsx에 Bridge 상태 섹션 추가
- `/health` 폴링 훅 (또는 인라인 useEffect)

### 미포함
- BridgeInstaller 컴포넌트 수정
- 온보딩 플로우 변경
- 별도 `/download` 페이지

## API/DB 변경

없음. 로컬 서버 `/health` 엔드포인트 (기존)만 사용.

## 참고

- `frontend/src/components/BridgeInstaller.tsx` — 온보딩용 Bridge 설치 UI (참고용)
- `frontend/src/pages/Settings.tsx` — 수정 대상
- `frontend/src/hooks/useAccountStatus.ts` — 기존 로컬 서버 상태 폴링 (토큰 동기화 후에만 동작)
- `frontend/src/context/AuthContext.tsx` — `localReady` = 토큰 동기화 성공 여부
