# Risk Mitigation — 프로덕션 안정성 개선

> 작성일: 2026-03-25 | 상태: 구현 완료

---

## 목표

프로덕션 배포 전 식별된 3가지 리스크를 최소 비용으로 완화한다.

근거 자료: 프로젝트 완성도 평가 (2026-03-25 대화)

---

## 범위

### 포함 (3건)

1. **WS Relay 테스트 부재** — kill-switch 원격 경로 무검증
2. **스케줄러 catch-up 부재** — 서버 재시작 시 일일 작업 누락
3. **프론트엔드 E2E 테스트 부재** — 핵심 흐름 회귀 감지 불가

### 미포함

- KIS 실API 검증 → 계정 확보 후 별도 진행
- Redis 영속 큐 → Phase E(백테스트)에서 도입
- 컴포넌트 단위 테스트 → ROI 낮음, E2E로 대체

---

## RM-1: WS Relay 테스트

**현상**: `cloud_server/api/ws_relay.py` + `cloud_server/services/relay_manager.py`에 테스트 0개. kill-switch 명령이 device → cloud → local 경로를 경유하는데, 이 경로가 실패하면 긴급 정지 작동 불가.

**수용 기준**:
- [x] `/ws/relay` 인증 성공/실패 테스트
- [x] `/ws/remote` device_id 누락 시 4002 close
- [x] 명령 전달: device → relay → local (kill-switch)
- [x] 오프라인 큐: local 미연결 시 PendingCommand 저장
- [x] 오프라인 큐 flush: local 재연결 시 pending 명령 전달
- [x] heartbeat 라우팅: local → heartbeat_ack 수신

**파일**: `cloud_server/tests/test_ws_relay.py` (신규)
**검증**: `pytest cloud_server/tests/test_ws_relay.py -v` 전체 통과

---

## RM-2: 스케줄러 catch-up 보정

**현상**: APScheduler 인메모리. 서버 재시작 시 스케줄 작업이 유실됨. 예: 16:00 daily_bars 전에 서버가 재시작되면 당일 데이터 수집 누락.

**분석**: 7개 작업 중 6개는 이미 멱등 (DB unique 제약). KIS WS Start만 중복 실행 취약.

**수용 기준**:
- [x] KIS WS Start: 이미 실행 중이면 skip (guard)
- [x] 서버 시작 시 `catch_up_missed_jobs()` 호출
- [x] 각 작업의 "오늘 실행 여부" DB 조회로 판단, 누락 시 즉시 보정
- [x] 모든 job에 `coalesce=True, max_instances=1` 설정
- [x] catch-up 로직 테스트 (mock 기반)

**파일**: `cloud_server/collector/scheduler.py` (수정), `cloud_server/tests/test_scheduler_catchup.py` (신규)
**검증**: 테스트 통과 + 기존 테스트 미파괴

---

## RM-3: 프론트엔드 E2E 테스트

**현상**: 프론트엔드 테스트 0개. 42개 컴포넌트, 25개 페이지에 대한 회귀 감지 불가.

**접근**: 컴포넌트 단위 테스트 대신 Playwright E2E로 핵심 4개 경로를 관통 테스트.

**수용 기준**:
- [x] Playwright 설치 + 설정
- [x] Login → 대시보드 진입 시나리오
- [x] 전략 생성 → 저장 → 목록 확인 시나리오
- [x] 온보딩 위자드 Step 1 수락 시나리오
- [x] 어드민 접근 차단 (일반 유저) 시나리오
- [x] Login/Register/StrategyBuilder에 data-testid 추가
- [x] `npm run build` 영향 없음

**파일**: `frontend/e2e/*.spec.ts` (신규), `frontend/playwright.config.ts` (신규), 기존 페이지 data-testid 추가
**검증**: `npx playwright test` 전체 통과
