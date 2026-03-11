> 작성일: 2026-03-11 | 상태: 구현 완료 | spec: frontend-ux-v2

# frontend-ux-v2 구현 계획

## 현재 상태 요약

| 항목 | 현재 위치 | 처리 |
|------|-----------|------|
| 장 상태 표시 | `ListView.tsx` L106-109, 계좌 카드 1행 우측 | 이미 구현됨. 위치 유지 |
| 엔진 신호등 | `Header.tsx` L87-91, 로고 옆 | 제거 + 계좌 카드로 이동 |
| 전략 start/stop API | `localClient.ts` L113-116 | 이미 있음. 호출부만 추가 |
| 전략 실행 버튼 | 없음 | 신규 추가 |

- `localEngine.start()`와 `localEngine.stop()` 모두 `localClient.ts`에 존재
- `MainDashboard.tsx`에서 `engineRunning`, `brokerConnected`는 `useAccountStatus`에서 받아옴
- `ListView`에는 아직 엔진 상태 props가 전달되지 않음

### 현재 계좌 카드 구조 (ListView L94-118)
- 1행: 총평가금액 + 일간 수익률 | 장 상태
- 2행: 주문가능금액 | 보유 종목 수 | 브로커명+모의여부

## 구현 단계

### Step 1: MainDashboard.tsx — ListView에 엔진 상태 + 콜백 전달
- 변경 파일: `frontend/src/pages/MainDashboard.tsx`
- 변경 내용:
  - `localEngine` import 추가
  - `useQueryClient` import 추가
  - `handleStrategyToggle` 핸들러 추가 — start/stop 호출 후 `invalidateQueries(['localStatus'])`
  - 로딩 상태 관리: `const [strategyLoading, setStrategyLoading] = useState(false)` — 핸들러에서 try/finally로 관리
  - `ListView`에 props 4개 추가: `engineRunning`, `brokerConnected`, `onStrategyToggle`, `strategyLoading`
- 검증: TypeScript 컴파일 오류 없음

### Step 2: ListView.tsx — props + 계좌 카드 하단 신호등+버튼
- 변경 파일: `frontend/src/components/main/ListView.tsx`
- 변경 내용:
  - `ListViewProps` 인터페이스에 `engineRunning`, `brokerConnected`, `onStrategyToggle`, `strategyLoading` 추가
  - 계좌 카드 2행에 신호등 + 전략 실행/중지 버튼 추가 (우측 정렬)
  - 신호등 색상: 회색=미연결, 노랑=브로커만, 초록=자동매매 중
  - 버튼: `engineRunning` → "중지" (빨강), else → "전략 실행" (인디고)
  - **브로커 미연결 시 버튼 disabled** — 클릭해도 실패할 상황 방지
  - **로딩 중 버튼 disabled** — start/stop 호출 중 중복 클릭 방지 (`strategyLoading` prop)
  - **키 미등록 시 안내 텍스트** — `brokerConnected === false` 상태에서 "설정에서 증권사 키를 등록하세요" CTA 표시
- 검증: 신호등 3색 + 버튼 클릭 + disabled 상태 + 안내 텍스트 확인

### Step 3: Header.tsx — 로고 옆 신호등 제거
- 변경 파일: `frontend/src/components/main/Header.tsx`
- 변경 내용: L87-90 신호등 `<span>` 제거
- 주의: `engineRunning`, `brokerConnected` props는 기어 드롭다운에서도 사용 → props 인터페이스 유지
- 검증: Header에 점 없음, 기어 드롭다운 정상

### Step 4: broker-auto-connect 프론트엔드 연동
- 변경 파일: `frontend/src/services/localClient.ts`, `frontend/src/hooks/useAccountStatus.ts`, `frontend/src/pages/Settings.tsx`
- 변경 내용:
  - `localClient.ts`에 `localBroker.reconnect()` 함수 추가 (`POST /api/broker/reconnect`)
  - `useAccountStatus.ts`의 `LocalStatusData.broker` 타입에 `reason?: string` 추가
  - `Settings.tsx`의 `handleSaveKeys` 성공 후 `localBroker.reconnect()` 호출
- 주의: broker-auto-connect 백엔드 완료 후에만 동작. 백엔드 미완료 시 404 → 무시 (catch)
- 검증: 키 저장 → reconnect 호출 → status 폴링으로 연결 확인

### Step 5: 빌드 확인
- `cd frontend && npm run build`
- TypeScript strict 오류, 미사용 import 없는지 확인

## 변경 파일 목록

| 파일 | 변경 유형 | 변경량 |
|------|-----------|--------|
| `frontend/src/pages/MainDashboard.tsx` | 수정 | +15줄 |
| `frontend/src/components/main/ListView.tsx` | 수정 | +20줄 |
| `frontend/src/components/main/Header.tsx` | 수정 | -2줄 |
| `frontend/src/services/localClient.ts` | 수정 | +3줄 |
| `frontend/src/hooks/useAccountStatus.ts` | 수정 | +1줄 |
| `frontend/src/pages/Settings.tsx` | 수정 | +5줄 |
