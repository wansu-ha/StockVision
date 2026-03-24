# 코드 리뷰 수정 보고서

> 리뷰일: 2026-03-18 | 리뷰어: Claude Code (Opus 4.6)
> 대상 커밋: `2a42fe2 fix: 리뷰 지적 사항 수정 (CRITICAL-3, CRITICAL-4, WARNING-1)`

---

## 수정 완료 (4건)

### CRITICAL-2: `bars.py` — 인증 누락 수정

**문제**: `/api/v1/bars/{symbol}` 라우터에 `Depends(require_local_secret)` 미적용.
**수정**: `local_server/routers/bars.py` — `require_local_secret` 의존성 추가.

### CRITICAL-3: `market_data.py` — `groupby` 정렬 누락 수정

**문제**: `itertools.groupby`는 연속된 동일 키만 그루핑. 정렬 없이 사용 시 주봉/월봉 집계 결과가 파편화됨.
**수정**: `cloud_server/api/market_data.py` — `groupby` 호출 전 `sorted()` 적용으로 날짜순 정렬 보장.

### CRITICAL-4: `dslConverter.ts` — `!=` 연산자 타입 불일치 수정

**문제**: DSL 파서가 `!=`를 수용하지만 `Condition['operator']` 타입에 `!=` 미포함. `as` 캐스트로 TypeScript 컴파일 오류를 우회하여 런타임 불일치 발생 가능.
**수정**:
- `frontend/src/services/rules.ts` — `Condition['operator']`에 `'!='` 추가
- `frontend/src/utils/dslConverter.ts` — `as` 캐스트 제거, 타입 안전 변환

### WARNING-1: `minute_bar.py` — SQLite thread safety 수정

**문제**: `sqlite3.connect()` 기본값 `check_same_thread=True`. FastAPI의 멀티스레드 환경에서 다른 스레드 접근 시 `ProgrammingError` 발생.
**수정**: `local_server/storage/minute_bar.py` — `check_same_thread=False` 옵션 추가.

---

## 설계 의도 유지 (수정 불필요, 2건)

### CRITICAL-1: `factory.py` — mock 모드 자동 감지

리뷰 지적: 실계좌를 mock으로 오버라이드할 위험.
판단: KIS 계좌 `"50"` 접두사는 한국투자증권 모의투자 전용 번호 체계. `None` 반환 시 미개입. 경고 로그 출력 존재. 설계 의도대로 유지.

### WARNING-2: `heartbeat.py` — `_flush_sync_queue` 서버 우선 정책

리뷰 지적: 오프라인 규칙 변경이 서버 버전으로 덮어씌워짐.
판단: spec "last-write-wins" 정책에 따른 의도적 설계. 오프라인 중 로컬 변경은 서버 정본과 충돌 시 서버 우선.

---

## 잔여 WARNING/INFO (향후 검토, 5건)

| # | 항목 | 심각도 | 조치 계획 |
|---|------|--------|----------|
| WARNING-5 | 1분봉+1년 조합 대량 데이터 | Medium | Stage 3 완성 시 UX 가드 추가 |
| WARNING-6 | `sync_queue.py` `pop(0)` + 무락 | Medium | max 100건 제약으로 실질 영향 미미 |
| INFO-1 | `purge_old` 미호출 | Low | 스케줄러 연동 시 해결 |
| INFO-2 | AND/OR 혼재 시 마지막 연산자 | Low | DSL v1 의도적 단순화 |
| INFO-5 | `isoformat()` 포맷 불일치 | Low | 프론트엔드 통일 시 해결 |

---

## 변경 파일 목록

| 파일 | 변경 내용 |
|------|----------|
| `local_server/routers/bars.py` | `require_local_secret` 의존성 추가 |
| `cloud_server/api/market_data.py` | `groupby` 전 정렬 추가 |
| `frontend/src/services/rules.ts` | `Condition['operator']`에 `'!='` 추가 |
| `frontend/src/utils/dslConverter.ts` | `as` 캐스트 제거, 타입 안전 변환 |
| `local_server/storage/minute_bar.py` | `check_same_thread=False` 추가 |
