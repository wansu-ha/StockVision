> 작성일: 2026-03-25 | 상태: 구현 완료 | Risk Mitigation

# 리스크 개선 구현 계획서

## 개요

Spec: `spec/risk-mitigation/spec.md` (RM-1 ~ RM-3)

프로덕션 안정성을 위한 3가지 리스크 개선:
1. **RM-1: WS Relay 테스트** — kill-switch 경로 신뢰성 확보
2. **RM-2: 스케줄러 catch-up** — 서버 재시작 시 누락 작업 보정
3. **RM-3: 프론트엔드 E2E** — 핵심 사용자 흐름 회귀 방지

---

## 아키텍처

```
[Step 1] WS Relay 테스트 (cloud_server)
  cloud_server/tests/test_ws_relay.py  ← 신규
  ├── _wait_auth() 인증 검증
  ├── relay → local 메시지 라우팅
  ├── device → relay → local 명령 전달
  └── pending queue flush

[Step 2] 스케줄러 catch-up (cloud_server)
  cloud_server/collector/scheduler.py  ← 수정
  cloud_server/tests/test_scheduler.py ← 신규
  └── lifespan 시작 시 누락 작업 보정

[Step 3] 프론트엔드 E2E (frontend)
  frontend/e2e/*.spec.ts               ← 신규
  frontend/playwright.config.ts        ← 신규
  ├── 로그인 → 대시보드
  ├── 전략 생성 → 저장 → 목록
  ├── 온보딩 위자드
  └── 어드민 접근 차단
```

---

## 수정 파일 목록

### Step 1: WS Relay 테스트

| 파일 | 변경 | 설명 |
|------|------|------|
| `cloud_server/tests/test_ws_relay.py` | 신규 | WS relay 테스트 6~8개 |
| `cloud_server/tests/conftest.py` | 수정 | JWT 생성 헬퍼 추가 (있으면 재사용) |

**테스트 케이스:**

1. **인증 성공** (`/ws/relay`)
   - JWT 발급 → auth 메시지 전송 → 연결 유지 확인
   - verify: WS가 close 되지 않음

2. **인증 거부 — 토큰 없음**
   - auth 메시지 없이 대기 → 4001 close
   - verify: close code == 4001

3. **인증 거부 — 잘못된 토큰**
   - 만료/변조 JWT 전송 → 4001 close
   - verify: close code == 4001

4. **device_id 누락** (`/ws/remote`)
   - device_id 없이 auth → 4002 close
   - verify: close code == 4002

5. **명령 전달 (kill-switch)**
   - local 연결 → device 연결 → device가 kill 명령 전송
   - verify: local이 command 메시지 수신

6. **오프라인 큐**
   - local 미연결 상태에서 device가 명령 전송
   - verify: DB에 PendingCommand 저장 + device에 command_queued 응답

7. **오프라인 큐 flush**
   - pending 명령 존재 → local 연결
   - verify: local이 pending 명령 수신

8. **heartbeat 라우팅**
   - local이 heartbeat 전송 → heartbeat_ack 수신
   - verify: ack 메시지 type == "heartbeat_ack"

---

### Step 2: 스케줄러 catch-up 보정

| 파일 | 변경 | 설명 |
|------|------|------|
| `cloud_server/collector/scheduler.py` | 수정 | `catch_up_missed_jobs()` 추가 + KIS guard |
| `cloud_server/tests/test_scheduler_catchup.py` | 신규 | catch-up 로직 테스트 |

**분석 결과:**
- 7개 작업 중 **6개는 이미 멱등** (DB unique 제약 + 존재 체크)
- **KIS WS Start만 취약** (중복 리스너 위험)

**변경 내용:**

1. **KIS WS Start guard** (scheduler.py)
   ```python
   async def start_kis_ws(self):
       if self._listen_task and not self._listen_task.done():
           logger.warning("KIS WS already running, skip")
           return
       # ... 기존 로직
   ```

2. **catch_up_missed_jobs()** (scheduler.py)
   - lifespan 시작 시 호출
   - 각 작업의 "오늘 실행 여부"를 DB 조회로 판단
   - 누락된 작업만 즉시 실행

   | 작업 | 보정 조건 | 감지 쿼리 |
   |------|----------|----------|
   | daily_bars (16:00) | 현재 ≥ 16시 AND 오늘 bar 없음 | `DailyBar.date == today` count |
   | stock_master (08:00) | 현재 ≥ 08시 AND updated_at > 20h | `StockMaster.updated_at` max |
   | yfinance (17:00) | 현재 ≥ 17시 AND 글로벌 인덱스 bar 없음 | `DailyBar` where symbol in indices |
   | integrity (18:00) | 현재 ≥ 18시 | 항상 실행 (멱등) |
   | briefing (06:00, 평일) | 현재 ≥ 06시 AND 오늘 briefing 없음 | `MarketBriefing.date == today` |
   | stock_analysis (07:00, 평일) | 현재 ≥ 07시 AND 오늘 분석 부족 | `StockBriefing.date == today` count |

3. **APScheduler 설정 강화**
   - 모든 job에 `coalesce=True, max_instances=1` 추가

**테스트:**
- DB에 오늘 데이터 없는 상태 → catch_up 호출 → 보정 함수 호출 확인 (mock)
- DB에 오늘 데이터 있는 상태 → catch_up 호출 → skip 확인
- KIS guard: 이미 running 상태에서 재호출 → skip 확인

---

### Step 3: 프론트엔드 E2E

| 파일 | 변경 | 설명 |
|------|------|------|
| `frontend/package.json` | 수정 | playwright 의존성 + test:e2e 스크립트 |
| `frontend/playwright.config.ts` | 신규 | Playwright 설정 |
| `frontend/e2e/auth.spec.ts` | 신규 | 로그인 → 대시보드 |
| `frontend/e2e/strategy.spec.ts` | 신규 | 전략 생성 → 저장 → 목록 |
| `frontend/e2e/onboarding.spec.ts` | 신규 | 온보딩 위자드 흐름 |
| `frontend/e2e/admin.spec.ts` | 신규 | 어드민 접근 차단 |
| `frontend/src/pages/Login.tsx` | 수정 | data-testid 3개 추가 |
| `frontend/src/pages/Register.tsx` | 수정 | data-testid 3개 추가 |
| `frontend/src/pages/StrategyBuilder.tsx` | 수정 | data-testid 2~3개 추가 |

**Playwright 설정:**
```typescript
// playwright.config.ts
{
  testDir: './e2e',
  webServer: {
    command: 'npm run dev',
    port: 5173,
    reuseExistingServer: true,
  },
  use: {
    baseURL: 'http://localhost:5173',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
}
```

**테스트 시나리오:**

1. **auth.spec.ts — 로그인 → 대시보드**
   - 전제: cloud_server 실행 중, 테스트 계정 존재
   - `/login` 이동 → 이메일/비번 입력 → 제출
   - verify: URL이 `/`로 변경, 대시보드 요소 visible

2. **strategy.spec.ts — 전략 CRUD**
   - 전제: `VITE_AUTH_BYPASS=true` (인증 우회)
   - `/strategy` 이동 → 규칙명 입력 → DSL 조건 입력 → 저장
   - `/strategies` 이동 → 목록에 방금 생성한 규칙 존재
   - verify: 규칙명이 리스트에 표시됨

3. **onboarding.spec.ts — 온보딩 흐름**
   - 전제: `VITE_AUTH_BYPASS=true`
   - `/onboarding` 이동 → Step 1 위험 고지 수락
   - verify: Step 2로 이동 (또는 local 연결 시 Step 3으로 skip)

4. **admin.spec.ts — 어드민 접근 차단**
   - 일반 유저 JWT로 `/admin` 접근 시도
   - verify: `/`로 리다이렉트
   - `VITE_AUTH_BYPASS=true`일 때는 접근 가능
   - verify: 어드민 대시보드 렌더링

**data-testid 추가 (최소한):**
```tsx
// Login.tsx
<input data-testid="login-email" type="email" ... />
<input data-testid="login-password" type="password" ... />
<button data-testid="login-submit" ... />

// Register.tsx
<input data-testid="register-email" type="email" ... />
<input data-testid="register-password" type="password" ... />
<button data-testid="register-submit" ... />

// StrategyBuilder.tsx
<input data-testid="strategy-name" ... />
<button data-testid="strategy-save" ... />
```

---

## 구현 순서

### Step 1: WS Relay 테스트 (~3h)
1. conftest.py에 JWT 헬퍼 확인/추가
2. test_ws_relay.py 작성 (8 케이스)
3. `pytest cloud_server/tests/test_ws_relay.py -v` 통과
4. verify: 전체 테스트 `pytest cloud_server/tests/ -v` 기존 테스트 깨지지 않음

### Step 2: 스케줄러 catch-up (~2h)
1. scheduler.py — KIS guard 추가
2. scheduler.py — `catch_up_missed_jobs()` 함수 추가
3. main.py lifespan에서 catch_up 호출
4. test_scheduler_catchup.py 작성 (3~4 케이스)
5. verify: `pytest cloud_server/tests/test_scheduler_catchup.py -v` 통과

### Step 3: 프론트엔드 E2E (~3h)
1. `npm install -D @playwright/test` + `npx playwright install chromium`
2. playwright.config.ts 작성
3. Login/Register/StrategyBuilder에 data-testid 추가
4. e2e/auth.spec.ts 작성 + 통과
5. e2e/strategy.spec.ts 작성 + 통과
6. e2e/onboarding.spec.ts 작성 + 통과
7. e2e/admin.spec.ts 작성 + 통과
8. verify: `npx playwright test` 전체 통과

---

## 검증 체크리스트

- [x] WS relay 테스트 8개 통과
- [x] 기존 cloud_server 테스트 전체 통과 (기존 56개 + 신규)
- [x] KIS WS 중복 실행 guard 동작 확인
- [x] catch-up: 서버 시작 시 누락 작업 보정 확인
- [x] 기존 local_server 테스트 전체 통과 (182개)
- [x] Playwright E2E 4 시나리오 통과
- [x] data-testid 추가가 기존 빌드에 영향 없음 (`npm run build`)
