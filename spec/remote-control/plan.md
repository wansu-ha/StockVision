# 원격 제어 — 구현 계획

> 작성일: 2026-03-12 | 상태: 초안 | spec: `spec/remote-control/spec.md`
> **구현 보류**: 권한 모델 확정(초안→확정) 후 착수

## 선행 작업

1. `docs/product/remote-permission-model.md` 상태를 초안→확정으로 전환
   - 채널별 권한 표 최종 리뷰
   - 확인 코드 메커니즘 합의
2. 클라우드↔로컬 통신 채널 결정 (WS relay vs long-poll)

## 구현 단계 (개요)

### Step 1: 로컬→클라우드 상태 동기화

**파일**: `local_server/` (새 모듈)

로컬 서버가 주기적으로(30초) 상태 스냅샷을 클라우드에 push.
- `RemoteStatusSnapshot` 모델 정의
- 클라우드 API: `POST /api/v1/remote/sync` (스냅샷 수신)
- 클라우드 DB: 최신 스냅샷 1건 저장 (user별)

### Step 2: 원격 상태 조회 API

**파일**: `cloud_server/api/remote.py` (신규)

- `GET /api/v1/remote/status` → 최신 스냅샷 반환
- 인증: JWT + 원격 모드 권한 확인

### Step 3: 킬스위치 API

**파일**: `cloud_server/api/remote.py`, `local_server/`

- `POST /api/v1/remote/kill` → 클라우드가 로컬에 정지 명령 전달
- 오프라인 시: pending_kill 저장 → 로컬 복귀 시 적용

### Step 4: 엔진 재개/무장 API

**파일**: `cloud_server/api/remote.py`, `local_server/`

- `POST /api/v1/remote/arm` → 2단계 확인 (확인 코드)
- 재개 조건 검증 로직

### Step 5: 프론트엔드 원격 모드 UI

**파일**: `frontend/src/`

- 원격 모드 감지 로직
- 원격 상태 조회 화면
- 킬스위치 버튼 + 확인 다이얼로그
- 재개 버튼 + 확인 코드 입력

### Step 6: 오프라인 킬스위치 처리

- 클라우드에 pending_kill 저장
- 로컬 서버 복귀 시 동기화 → 즉시 정지

## 변경 파일 요약 (예상)

| 파일 | 변경 |
|------|------|
| `cloud_server/api/remote.py` | 신규 — 원격 API (status, kill, arm) |
| `cloud_server/models/remote_snapshot.py` | 신규 — 스냅샷 DB 모델 |
| `local_server/sync/cloud_sync.py` | 신규 — 상태 동기화 모듈 |
| `local_server/routers/remote.py` | 신규 — 원격 명령 수신 |
| `frontend/src/hooks/useRemoteMode.ts` | 신규 — 원격 모드 감지 |
| `frontend/src/components/remote/*` | 신규 — 원격 제어 UI |
