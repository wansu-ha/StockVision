# 운영 패널 v2 (OpsPanel v2)

> 작성일: 2026-03-12 | 상태: 구현 완료 | Phase C (C1 + C2)

## 1. 배경

현재 OpsPanel은 4개 상태 도트(로컬/브로커/클라우드/엔진) + 경고 배너 + Kill Switch/Loss Lock 긴급 배너를 표시한다. 트레이더가 가장 먼저 확인하는 "오늘 얼마 벌었는지"가 없고, 상세 상태 확인은 설정 페이지로 이동해야 한다.

벤치마크: `docs/research/phase-c-dashboard-benchmark.md` §6, §7

## 2. 목표

메인 대시보드 진입 시 3초 안에 "시스템 정상/비정상" + "오늘 손익"을 파악할 수 있다.

## 3. 범위

### 3.1 C1 — 일일 P&L API + OpsPanel 표시

**백엔드**:
- `GET /api/logs/daily-pnl` 엔드포인트 추가
- `LogDB.today_realized_pnl()` 활용 (이미 존재)
- 응답: `{ success, data: { date, realized_pnl, fill_count, win_count, loss_count, win_rate } }`

**프론트엔드**:
- OpsPanel 우측에 "오늘 +32,000원 (+0.4%)" 표시
- 양수 → 초록, 음수 → 빨강, 0 → 회색
- 계좌바(ListView 상단)에도 일일 손익 표시

**데이터 소스**:
- `log_db.py`의 FILL 로그 `meta.realized_pnl` 합산 (기존 메서드)
- 승률 계산: FILL 로그의 `meta.realized_pnl > 0` 건수 / 전체 FILL 건수
- 수익률 계산: 일일 실현손익 / 당일 시작 잔고 (브로커 API에서 조회)

### 3.2 C2 — 운영 패널 확장

**상태 표시 개선**:
- 각 상태 도트에 호버/클릭 시 상세 정보 드롭다운
  - 로컬: 서버 버전, 가동 시간, 마지막 하트비트
  - 브로커: 증권사 종류, 실전/모의, 연결 시각
  - 클라우드: 응답 시간, 마지막 동기화
  - 엔진: 활성 전략 수, 마지막 평가 시각, safeguard 상태

**요약 확장**:
- 기존: 신호 N / 체결 N / 오류 N
- 추가: 일일 P&L (C1), 활성 전략 수, 엔진 가동 시간

**경고 배너 개선**:
- 경고 메시지에 복구 액션 버튼 추가 (예: "브로커 미연결" → "설정으로 이동" 버튼)

### 3.3 제외

- 원격 모드 UI (Phase C6에서 처리)
- 알림 패널 재설계 (별도 이터레이션)
- 모바일 반응형 (Phase C6 PWA에서 처리)

## 4. 의존성

| 의존 대상 | 상태 | 비고 |
|-----------|------|------|
| `log_db.py` `today_realized_pnl()` | 구현됨 | 합산 로직 존재, API만 추가. 단, FILL 로그 기록 시 `meta.realized_pnl` 필드가 포함되어야 함 — Executor 로깅 확인 필요 |
| `routers/logs.py` | 구현됨 | `/summary` 엔드포인트 패턴 참고 |
| `routers/status.py` | 구현됨 | safeguard, broker 상태 데이터 참고 |
| OpsPanel 컴포넌트 | 구현됨 | 153줄, 확장만 필요 |

## 5. API 설계

### 5.1 일일 P&L 엔드포인트

```
GET /api/logs/daily-pnl?date=2026-03-12
```

응답:
```json
{
  "success": true,
  "data": {
    "date": "2026-03-12",
    "realized_pnl": 32000,
    "fill_count": 3,
    "win_count": 2,
    "loss_count": 1,
    "win_rate": 0.667
  },
  "count": 1
}
```

- `date` 미지정 시 오늘
- `win_rate`: 서버에서 `win_count / fill_count` 계산하여 반환
- 수익률(`pnl_pct`)은 프론트에서 계산 (일일P&L / 총평가금액 — 브로커 잔고 데이터 활용)

### 5.2 확장 상태 엔드포인트

기존 `GET /api/status` 응답에 추가 필드:
```json
{
  "data": {
    "server": "running",
    "uptime_seconds": 3600,
    "broker": { "...기존...", "connected_at": "2026-03-12T09:00:00" },
    "strategy_engine": {
      "...기존...",
      "active_rules": 3,
      "last_eval_at": "2026-03-12T09:31:00"
    }
  }
}
```

## 6. 프론트엔드 설계

### 6.1 OpsPanel 레이아웃 변경

```
현재:
[로컬●] [브로커●] [클라우드●] [엔진●]     신호 5  체결 3  오류 0
Kill Switch / Loss Lock 배너
경고 배너

변경 후:
[로컬●] [브로커●] [클라우드●] [엔진●]     오늘: +32,000원  신호 5  체결 3  오류 0
Kill Switch / Loss Lock 배너
경고 배너 (+ 복구 액션 버튼)
```

### 6.2 상태 드롭다운 (C2)

각 상태 도트 클릭 시 `Popover` 또는 `Dropdown`으로 상세 정보 표시. 읽기 전용.

### 6.3 계좌바 표시

ListView 상단 계좌바에 기존 잔고 옆에 "오늘 +32,000 (+0.26%)" 추가.

## 7. 수용 기준

### C1 — 일일 P&L
- [ ] `GET /api/logs/daily-pnl` 엔드포인트가 오늘 실현손익을 반환한다
- [ ] OpsPanel에 일일 P&L이 색상과 함께 표시된다
- [ ] 계좌바에 일일 P&L이 표시된다
- [ ] 체결 0건일 때 "0원"으로 표시된다 (에러 아님)

### C2 — 운영 패널 확장
- [ ] 각 상태 도트 클릭 시 상세 정보가 드롭다운으로 표시된다
- [ ] 경고 배너에 복구 액션 버튼이 포함된다
- [ ] 엔진 가동 시간, 활성 전략 수가 표시된다

## 8. 참고

- 기존 OpsPanel: `frontend/src/components/main/OpsPanel.tsx`
- 로그 DB: `local_server/storage/log_db.py` (today_realized_pnl 메서드)
- 로그 API: `local_server/routers/logs.py`
- 상태 API: `local_server/routers/status.py`
- UX PRD: `docs/product/frontend-ux-priority-prd-2026-03-10.md` §P1 운영 패널 강화
