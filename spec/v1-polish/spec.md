> 작성일: 2026-03-30 | 상태: 구현 완료

# v1 완성 — 필수 4건

제품으로 쓸 수 있는 최소 완성. "전략 짜고 → 돌리고 → 결과 보고 → 개선" 사이클 완성.

## 항목 요약

| # | 항목 | 목적 | 복잡도 |
|---|------|------|--------|
| F1 | 비서 tool 확장 + BYO 키 빌더 연동 | AI가 실행 데이터에 접근 + 빌더 LLM 선택 | 중 |
| F2 | Sentry 에러 모니터링 | 운영 에러 추적 | 소 |
| F3 | 포지션 동기화 | 엔진 ↔ 브로커 잔고 불일치 해소 | 중 |
| F4 | 대시보드 전략 탭 | 전략 목록 접근 경로 확보 | 소 |

---

## F1: 비서 tool 확장 + BYO 키 빌더 연동

### 배경

비서(assistant)가 대화는 할 수 있지만, 실행 로그/백테스트/잔고/DSL에 접근하지 못한다.
"오늘 전략 어땠어?" 같은 질문에 데이터 기반 답변 불가.

별도 "리뷰 기능"은 불필요 — 비서가 데이터를 조회할 수 있으면 사용자가 대화로 자유롭게 리뷰/분석/수정 요청 가능.

### 목표

1. 비서에 tool 추가 — 실행 데이터 조회 + DSL 수정
2. 빌더 LLM 선택 — 설정에서 "플랫폼 크레딧" 또는 "내 API 키" 선택

### F1-1. 비서 tool

비서(AIChatService, mode: assistant)에 Claude tool_use로 제공할 도구:

| tool | 설명 | 데이터 소스 |
|------|------|-----------|
| `get_execution_logs` | 실행 로그 조회 (기간, 종목, 타입 필터) | 로컬 서버 `/api/logs` |
| `get_daily_pnl` | 일일 P&L (실현 손익, 승률) | 로컬 서버 `/api/logs/daily-pnl` |
| `get_backtest_result` | 백테스트 결과 조회 (규칙 ID) | 클라우드 `/api/v1/backtest/history` |
| `get_positions` | 현재 보유 종목 + 잔고 | 로컬 서버 `/api/account/balance` |
| `get_rule` | 규칙 DSL + 설정 조회 | 클라우드 `/api/v1/rules/{id}` |
| `update_rule_dsl` | 규칙 DSL 수정 (새 버전 생성) | 클라우드 `PUT /api/v1/rules/{id}` |
| `list_rules` | 전체 규칙 목록 | 클라우드 `/api/v1/rules` |

**구현 방식:**
- `AIChatService`에서 assistant 모드일 때 Claude API 호출에 `tools` 파라미터 추가
- tool 실행 시 해당 API를 내부 호출 → 결과를 Claude에 다시 전달
- 로컬 서버 데이터는 클라우드 → 로컬 relay (기존 하트비트/WS 경로) 또는 프론트 경유

**로컬 데이터 접근 문제:**
비서는 클라우드에서 실행되는데, 실행 로그/잔고는 로컬에 있다.
- 방법 A: 프론트가 로컬 데이터를 가져와서 비서 대화에 컨텍스트로 주입
- 방법 B: 클라우드가 WS relay로 로컬에 요청

**추천: 방법 A.** 프론트가 이미 로컬 API를 폴링하고 있으므로, 비서 대화 시작 시 최신 데이터를 컨텍스트로 첨부. 추가 인프라 불필요.
**한계:** 대화 시점 스냅샷이라 실시간은 아님. v1에서는 충분 — 실시간 데이터는 로컬 UI가 이미 제공.

### F1-2. BYO 키 빌더 연동

현재 빌더(copilot)는 플랫폼 크레딧만 사용.
BYO API 키 등록 사용자는 빌더에서도 자기 키를 쓰고 싶음.

**변경:**
- 설정 페이지에 "AI LLM 소스" 드롭다운: `플랫폼 (기본)` / `내 API 키`
- `AIChatService`에서 mode 무관하게 사용자 BYO 키가 있고 선택했으면 해당 키로 호출
- `CreditService`에 이미 BYO 키 지원 있음 — 빌더 모드에서도 같은 로직 적용

### 변경 대상

| 파일 | 변경 |
|------|------|
| `cloud_server/services/ai_chat_service.py` | assistant 모드 tool 정의 + tool 실행 핸들러 |
| `cloud_server/services/credit_service.py` | 빌더 모드에서도 BYO 키 라우팅 |
| `frontend/src/pages/Settings.tsx` | "AI LLM 소스" 드롭다운 |
| `frontend/src/components/ai/` | 비서 대화 시 로컬 데이터 컨텍스트 주입 |

### 수용 기준

- [ ] 비서에게 "오늘 전략 성과 알려줘" → 실행 로그 기반 답변
- [ ] 비서에게 "삼성전자 규칙 보여줘" → DSL 표시
- [ ] 비서에게 "RSI 조건 65로 바꿔줘" → DSL 수정 + 새 버전 생성
- [ ] 비서에게 "내 포트폴리오 요약해줘" → 잔고 + 보유 종목 기반 답변
- [ ] BYO 키 등록 시 빌더에서 "내 API 키" 선택 가능
- [ ] 키 미등록 시 빌더는 플랫폼 크레딧 사용 (기존 동작)

---

## F2: Sentry 에러 모니터링

### 배경

기존 하드닝 spec 10개 중 7개 완료. HTTPS는 Render 자동 처리로 완료. DB 백업은 오라클 이전 후.
남은 건 에러 모니터링 1건.

### 목표

운영 서버 에러를 Sentry 대시보드에서 추적.

### 변경 대상

| 파일 | 변경 |
|------|------|
| `cloud_server/main.py` | Sentry SDK 초기화 (DSN 환경변수) |
| `requirements.txt` | `sentry-sdk[fastapi]` 추가 |
| Render 환경변수 | `SENTRY_DSN` 추가 |

### 수용 기준

- [ ] `sentry-sdk[fastapi]` 설치 + main.py 초기화 (DSN 환경변수)
- [ ] 의도적 에러 발생 → Sentry 대시보드에 표시 확인
- [ ] DSN 미설정 시 Sentry 비활성 (에러 안 남)

---

## F3: 포지션 동기화

### 배경

사용자가 HTS/MTS에서 직접 주문하면 엔진의 PositionState와 실제 브로커 잔고가 달라진다.
`수익률()`, `보유수량()`, `매입가()` 등 포지션 기반 DSL 함수가 잘못된 값을 반환할 수 있다.

"감지 + 경고"가 아니라, 엔진이 주기적으로 브로커 잔고와 자기 상태를 동기화하면 문제 자체가 없어진다.

### 목표

엔진 PositionState를 브로커 실제 잔고와 주기적으로 동기화.

### 동기화 시점

| 시점 | 방식 |
|------|------|
| 엔진 시작 시 | 1회 즉시 동기화 |
| 주문 체결 후 | 이벤트 기반 |
| 60초 주기 | 폴백 (외부 주문 대비) |

### 동기화 로직

```
_sync_positions():
  1. broker.get_balance() → 전체 보유 종목 + 수량 + 평균 단가
  2. 엔진 등록 종목만 필터
  3. 각 종목의 PositionState와 비교:
     - 수량 다름 → PositionState 수량 갱신
     - 평균 단가 다름 → PositionState 매입가 갱신
     - 잔고에 없음 (전량 매도) → PositionState 리셋
  4. 변경 있으면 로그 기록 (debug 레벨)
```

엔진 밖 종목은 무시. 경고/자동정지 없음. 조용히 동기화.

### 변경 대상

| 파일 | 변경 |
|------|------|
| `local_server/engine/engine.py` | `_sync_positions()` + 호출 시점 3곳 |
| `local_server/config.py` | `position_sync.interval` 기본값 60 |

### 수용 기준

- [ ] 엔진 시작 시 브로커 잔고와 PositionState 동기화
- [ ] 주문 체결 후 동기화
- [ ] 60초 주기 폴백 동기화
- [ ] 엔진 등록 종목만 대상 (밖 종목 무시)
- [ ] 수량/단가 불일치 시 PositionState 갱신
- [ ] 동기화 변경 사항 debug 로그
- [ ] 기존 테스트 전체 통과

---

## F4: 대시보드 전략 탭

### 배경

전략 목록 페이지(`/strategies`)가 존재하지만 MainDashboard에서 접근 경로가 없다.
MainDashboard는 Layout(상단 네비게이션) 밖에서 자체 헤더를 사용.

### 목표

MainDashboard ListView에 "전략" 탭 추가. 기존 "내 종목 | 관심 종목" 옆에 세 번째 탭.

### 변경 대상

| 파일 | 변경 |
|------|------|
| `frontend/src/components/main/ListView.tsx` | "전략" 탭 추가 — 전체 규칙 목록 표시 |
| `frontend/src/pages/MainDashboard.tsx` | 탭 상태에 `'strategy'` 추가 |

### 수용 기준

- [ ] "내 종목 | 관심 종목 | 전략" 세 탭
- [ ] 전략 탭에서 전체 규칙 목록 표시 (종목명, DSL 요약, ON/OFF, 실행 상태)
- [ ] 규칙 클릭 → 전략 빌더 모달로 편집

---

## 구현 순서

```
Step 1: F2 Sentry (반나절) — 가장 작고 독립적
Step 2: F4 대시보드 전략 탭 (1일) — 전략 접근 경로 확보
Step 3: F3 포지션 동기화 (1-2일) — 엔진 안전
Step 4: F1 비서 tool 확장 + BYO 키 (2-3일) — 사이클 완성
```

**총 예상: 4-6일**
