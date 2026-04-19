# 문서 갱신 구현 계획 (T3-D2)

> 작성일: 2026-03-17 | 상태: 구현 완료

---

## 선행 조건

- Phase B~D 구현이 완료되어 반영할 기능 목록이 확정된 상태
- `architecture.md` 기존 구조 파악 완료

---

## Step 1: SUPERSEDED 헤더 추가 (4건)

각 파일 첫 줄에 SUPERSEDED 헤더를 삽입한다. 본문은 수정하지 않는다.

| 파일 | 대체 문서 |
|------|----------|
| `docs/project-blueprint.md` | → `docs/roadmap.md` |
| `docs/future-improvements.md` | → `docs/roadmap.md` |
| `docs/architecture-diagram.md` | → `docs/architecture.md` |
| `docs/development-plan-v2.md` | → `docs/development-plan-v3.md` |

**헤더 형식**:
```markdown
> ⚠️ SUPERSEDED — 이 문서는 더 이상 유지되지 않습니다. 최신 문서: `{대체 문서 경로}`
```

**변경 파일**: 위 4개
**검증**: 각 파일의 첫 줄에 SUPERSEDED 헤더 존재 확인

---

## Step 2: architecture.md 갱신

기존 섹션 구조를 유지하면서 Phase B~D 기능을 삽입한다.

### 2-1. §3 데이터 흐름 다이어그램에 relay/WS 경로 추가

```
[프론트엔드] ──WS──→ [클라우드 서버] ──WS──→ [로컬 서버]
                     (relay hub)         (원격 제어)
```

### 2-2. §로컬 서버 섹션에 추가

| 기능 | 설명 (1~2줄) | 참고 spec |
|------|-------------|----------|
| System Trader (전략 엔진) | 규칙 기반 자동매매 엔진. 지표 계산 + DSL 평가 + 주문 실행 | `spec/system-trader/` |
| exe 패키징 + 딥링크 | Inno Setup 설치 파일 + `stockvision://` 프로토콜 핸들러 | `spec/local-exe-deeplink/` |

### 2-3. §클라우드 서버 섹션에 추가

| 기능 | 설명 (1~2줄) | 참고 spec |
|------|-------------|----------|
| 시장 브리핑 | Claude API로 당일 시장 요약 생성 | `spec/market-briefing/` |
| 종목별 분석 | 개별 종목 AI 분석 리포트 | `spec/stock-analysis/` |
| 실시간 경고 | SSE 기반 알림 (체결, 손절, 에러) | `spec/realtime-alerts/` |
| relay 허브 | WS 릴레이로 프론트↔로컬 중계 | `spec/relay-infra/` |

### 2-4. §프론트엔드 섹션에 추가

| 기능 | 설명 (1~2줄) | 참고 spec |
|------|-------------|----------|
| OpsPanel v2 | 운영 대시보드 (시스템 상태, 전략 제어) | `spec/ops-panel-v2/` |
| 원격 제어 | 외부에서 엔진 시작/중지/킬스위치 | `spec/remote-ops/` |
| 규칙 카드 구조화 | DSL 기반 조건 폼 + 스크립트 모드 | `spec/rule-card-structured/` |

### 2-5. 갱신일 헤더 업데이트

```markdown
> 최종 갱신: {날짜} | Phase B~D 기능 반영
```

**변경 파일**: `docs/architecture.md`
**검증**: 8개 기능 키워드가 본문에 존재하는지 grep 확인

---

## 의존성 그래프

```
Step 1 (독립) ──┐
                ├→ 완료
Step 2 (독립) ──┘
```

두 Step은 완전 독립. 병렬 작업 가능.

---

## 수정 파일 종합

| # | 파일 | Step | 작업 |
|---|------|------|------|
| 1 | `docs/project-blueprint.md` | 1 | SUPERSEDED 헤더 |
| 2 | `docs/future-improvements.md` | 1 | SUPERSEDED 헤더 |
| 3 | `docs/architecture-diagram.md` | 1 | SUPERSEDED 헤더 |
| 4 | `docs/development-plan-v2.md` | 1 | SUPERSEDED 헤더 |
| 5 | `docs/architecture.md` | 2 | Phase B~D 기능 삽입 + 헤더 갱신 |

**예상 공수**: 1~2시간
