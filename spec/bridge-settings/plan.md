> 작성일: 2026-03-13 | 상태: 구현 완료 | bridge-settings

# Bridge 상태 & 다운로드 — 구현 계획

## 아키텍처

```
Settings.tsx
  ┌─────────────────────────────────┐
  │ 로컬 서버 (Bridge)             │  ← 신규 섹션
  │  [미연결] 다운로드 + 실행 안내  │
  │  [연결됨] 초록 인디케이터       │
  ├─────────────────────────────────┤
  │ 엔진 상태                       │  ← 기존
  ├─────────────────────────────────┤
  │ 증권사 API 설정                 │  ← 기존
  └─────────────────────────────────┘
```

연결 감지 흐름:
```
Settings 마운트
  → useEffect: fetch localhost:4020/health (10초 폴링)
  → 성공: bridgeConnected = true, uptime 표시
  → 실패: bridgeConnected = false, 다운로드 안내 표시
```

`AuthContext.localReady`와 독립적으로 동작 (토큰 동기화 전에도 Bridge 물리 연결 상태 표시 가능).

## 수정 파일 목록

| 파일 | 변경 |
|------|------|
| `frontend/src/pages/Settings.tsx` | Bridge 상태 섹션 추가 (인라인 구현) |

## 구현 순서

### Step 1: Settings.tsx에 Bridge 상태 섹션 추가

"엔진 상태" 섹션 **위**에 새 섹션 삽입:

**상태 관리** (컴포넌트 내 인라인):
- `bridgeConnected: boolean` — `/health` 응답 성공 여부
- `bridgeUptime: number | null` — 서버 업타임 (초)
- `useEffect`로 10초 폴링, 컴포넌트 언마운트 시 클린업

**미연결 UI**:
- 빨간/노란 인디케이터 + "미연결"
- 설치파일 다운로드 링크 (GitHub releases latest)
- "서버 시작" 버튼 (딥링크 `stockvision://launch`) — `localStorage.getItem('sv_installed') === '1'`일 때만 표시
- 접힌 상태의 수동 실행 안내: `%LOCALAPPDATA%\StockVision\stockvision-local.exe`

**연결됨 UI**:
- 초록 인디케이터 + "연결됨"
- 업타임 표시 (분/시간 단위 변환)

**스타일**: 기존 섹션과 동일 (`bg-gray-900 border border-gray-800 rounded-xl p-6`)

**verify**: `npm run build` 성공, 브라우저에서 섹션 표시 확인

## 검증 방법

| 항목 | 방법 |
|------|------|
| 빌드 | `npm run build` 성공 |
| 미연결 UI | 로컬 서버 미실행 상태에서 설정 페이지 → 다운로드 링크 + "미연결" 표시 |
| 연결됨 UI | 로컬 서버 실행 후 설정 페이지 → "연결됨" + 업타임 표시 |
| 폴링 | 로컬 서버 시작/종료 시 10초 내 UI 자동 갱신 |
| 기존 기능 | 엔진 상태, 증권사 키 등 기존 섹션 정상 동작 |

## 의존성

- `inno-installer` 완료 후 다운로드 링크를 `.exe`로 맞춤
- 미완료 시 현재 `.zip` 링크로 먼저 구현, 이후 변경
