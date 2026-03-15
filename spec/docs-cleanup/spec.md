# Docs Cleanup — 문서 정비

> 작성일: 2026-03-13 | 상태: 구현 완료

---

## 목표

CLAUDE.md, roadmap, spec 상태 헤더, 깨진 링크 등 **문서 정합성**을 확보한다.

근거 자료: `docs/research/review-documentation.md`

---

## 범위

### 포함 (6건)

기동 명령어 수정, spec 상태 갱신, 링크 수정, SUPERSEDED 표기, architecture 갱신, 프로젝트 구조 갱신.

### 미포함

- roadmap.md C6 상태 — 재검토 결과 "미착수" 표기가 정확. 이슈 아님.
- architecture.md 전면 재작성 — 최소 갱신만 포함

---

## DC-1: CLAUDE.md 서버 기동 명령어 수정

**현상**: 두 명령어 모두 오류.
- Cloud: `cd cloud_server` 후 실행 → `ModuleNotFoundError`
- Local: `cd local_server` 후 `python -m uvicorn api.main:app` → `local_server/api/` 없음

**수정**:
```
### Cloud Server
python -m uvicorn cloud_server.main:app --port 4010 --reload

### Local Server
python -m uvicorn local_server.main:app --port 4020 --reload
```
(프로젝트 루트에서 실행, `cd` 제거)

**파일**: `CLAUDE.md`
**검증**: 수정된 명령어로 실제 서버 기동 성공

## DC-2: spec 상태 헤더 갱신 (2건)

**현상**: 구현 완료된 spec의 상태 헤더가 "초안"으로 남아있음.
- `spec/system-trader/spec.md` — 초안 → 구현 완료
- `spec/rule-card-structured/spec.md` — 초안 → 구현 완료

**수정**: 상태 헤더를 `구현 완료`로 갱신.
**검증**: 상태 헤더 ↔ roadmap.md 일치

## DC-3: docs/README.md 깨진 링크 수정

**현상**: 2개 링크가 존재하지 않는 파일 참조.
- `./research/spec-review-result.md` — 파일 없음
- `./research/code-analysis-result.md` — 파일 없음

**수정**: 해당 링크 제거 또는 실제 파일 경로로 수정.
**파일**: `docs/README.md`
**검증**: README 내 모든 링크가 실제 파일로 연결

## DC-4: SUPERSEDED 헤더 추가 (2건)

**현상**: 대체된 문서에 SUPERSEDED 표기 없음.
- `docs/development-plan.md` — `development-plan-v2.md`로 대체됨
- `docs/integrated-development-plan.md` — 대체됨

**참고**: `docs/architecture-phase3.md`는 이미 SUPERSEDED 표기 있음.
**수정**: 파일 최상단에 `> ⚠️ SUPERSEDED — 최신 문서: [대체 문서 경로]` 추가.
**검증**: 대체된 문서에 SUPERSEDED 안내 명시

## DC-5: architecture.md Phase C/D 갱신

**현상**: `architecture.md` 최종 갱신일 2026-03-09. Phase C (C1-C5) + Phase D (D1-D3) 완료 내역 미반영. §12 로드맵이 v1/v2/v3+ 구조로 roadmap.md의 Phase A~E 체계와 불일치.
**수정**: §12 로드맵에 Phase C/D 완료 항목 추가. 전면 재작성은 하지 않음.
**파일**: `docs/architecture.md`
**검증**: architecture.md 로드맵 ↔ roadmap.md 주요 항목 일치

## DC-6: CLAUDE.md 프로젝트 구조 갱신

**현상**: `local_server/` 하위에 `api/` 표기 → 실제는 `routers/`. 일부 디렉토리 미열거.
**수정**: `api/` → `routers/`로 수정. 주요 디렉토리만 반영 (포괄 표현 유지).
**파일**: `CLAUDE.md`
**검증**: CLAUDE.md 구조 ↔ 실제 디렉토리 일치

---

## 수용 기준

- [x] CLAUDE.md 기동 명령어로 서버 기동 성공
- [x] spec 상태 헤더 2건 갱신
- [x] README 깨진 링크 해소
- [x] SUPERSEDED 헤더 2건 추가
- [x] architecture.md Phase C/D 반영
- [x] CLAUDE.md 프로젝트 구조 정확

---

## 참고 파일

- `CLAUDE.md` — 기동 명령어, 구조 (DC-1, DC-6)
- `spec/system-trader/spec.md` — 상태 헤더 (DC-2)
- `spec/rule-card-structured/spec.md` — 상태 헤더 (DC-2)
- `docs/README.md` — 깨진 링크 (DC-3)
- `docs/development-plan.md` — SUPERSEDED (DC-4)
- `docs/integrated-development-plan.md` — SUPERSEDED (DC-4)
- `docs/architecture.md` — Phase C/D (DC-5)
- `docs/research/review-documentation.md` — 근거 자료
