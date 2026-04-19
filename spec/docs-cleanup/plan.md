# Docs Cleanup — 구현 계획

> 작성일: 2026-03-13 | 상태: 구현 완료

---

## 아키텍처

문서 간 참조 관계:

```
CLAUDE.md (기동 명령어, 프로젝트 구조)
  ↔ 실제 디렉토리 구조

docs/architecture.md (아키텍처)
  ↔ docs/roadmap.md (로드맵) — Phase C/D 갭

docs/README.md
  → docs/research/*.md (깨진 링크 2건)

docs/development-plan.md → SUPERSEDED by development-plan-v2.md
docs/integrated-development-plan.md → SUPERSEDED

spec/system-trader/spec.md — 상태 "초안" → "구현 완료"
spec/rule-card-structured/spec.md — 상태 "초안" → "구현 완료"
```

---

## 수정 파일 목록

| 파일 | 변경 내용 |
|------|----------|
| `CLAUDE.md` | 기동 명령어 수정 (cd 제거, 루트 실행), 프로젝트 구조 `api/` → `routers/` |
| `spec/system-trader/spec.md` | 상태 헤더 초안 → 구현 완료 |
| `spec/rule-card-structured/spec.md` | 상태 헤더 초안 → 구현 완료 |
| `docs/README.md` | 깨진 링크 2건 제거 또는 수정 |
| `docs/development-plan.md` | SUPERSEDED 헤더 추가 |
| `docs/integrated-development-plan.md` | SUPERSEDED 헤더 추가 |
| `docs/architecture.md` | §12 로드맵에 Phase C/D 완료 항목 추가 |

---

## 구현 순서

### Step 1: CLAUDE.md 기동 명령어 + 구조 (DC-1, DC-6)

기동 명령어 수정 — `cd` 제거, 프로젝트 루트에서 실행:

```markdown
### Cloud Server
```bash
source .venv/Scripts/activate  # Windows
python -m uvicorn cloud_server.main:app --port 4010 --reload
```

### Local Server
```bash
source .venv/Scripts/activate
python -m uvicorn local_server.main:app --port 4020 --reload
```
```

프로젝트 구조: `local_server/` 하위 `api/` → `routers/` 수정.

**verify**: 수정된 명령어로 서버 기동 확인 (import 에러 없음)

### Step 2: spec 상태 헤더 갱신 (DC-2)

두 파일의 상태 헤더 수정:

```markdown
# spec/system-trader/spec.md
> 작성일: ... | 상태: 구현 완료

# spec/rule-card-structured/spec.md
> 작성일: ... | 상태: 구현 완료
```

**verify**: roadmap.md와 상태 일치

### Step 3: README 깨진 링크 (DC-3)

`docs/README.md`에서 존재하지 않는 파일 참조 제거:
- `./research/spec-review-result.md`
- `./research/code-analysis-result.md`

해당 섹션 삭제 또는 실제 리뷰 문서(`review-summary-2026-03-13.md`)로 교체.

**verify**: README 내 모든 링크 → 실제 파일 존재

### Step 4: SUPERSEDED 헤더 (DC-4)

두 파일 최상단에 추가:

```markdown
> ⚠️ SUPERSEDED — 최신 문서: `docs/development-plan-v2.md`
```

```markdown
> ⚠️ SUPERSEDED — Phase 3 아키텍처로 대체됨. 참고: `docs/architecture.md`
```

**verify**: 파일 열면 SUPERSEDED 안내 즉시 확인

### Step 5: architecture.md Phase C/D 갱신 (DC-5)

**확인 완료**: `docs/architecture.md` §12 로드맵 섹션 (v1/v2/v3+ 구조, line 553-584). `docs/roadmap.md` Phase C/D 모두 "구현 완료" 확인.

§12 `### v1 (현재 목표)` 다음에 Phase A~D 완료 내역 추가:

```markdown
### Phase A (완료, 2026-03-11)
- System Trader, 규칙 카드 구조화, 차트 타입 전환, 이벤트 마커

### Phase B (완료, 2026-03-11)
- 전략 목록, 자동 연결, ops 패널

### Phase C (완료, 2026-03-12)
- C1: 일일 P&L API + OpsPanel
- C2: 운영 패널 확장
- C3: 실행 로그 타임라인
- C4: exe 패키징
- C5: 온보딩 신뢰 강화

### Phase D (완료, 2026-03-12)
- D1: 실시간 경고 (9종 규칙 기반)
- D2: 시장 브리핑 (1회/일)
- D3: 종목별 분석 (1회/일)
```

**verify**: architecture.md ↔ roadmap.md 주요 항목 일치

---

## 검증 방법

1. CLAUDE.md 명령어로 서버 기동 → 성공
2. spec 상태 헤더 ↔ roadmap.md 일치
3. README 링크 전수 확인 (파일 존재 여부)
4. SUPERSEDED 문서에 안내 헤더 있음
5. architecture.md에 Phase C/D 항목 있음
