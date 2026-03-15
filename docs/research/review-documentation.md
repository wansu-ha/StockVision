# 문서 정합성 리뷰

> 작성일: 2026-03-13 | 대상: docs/, spec/, CLAUDE.md, README.md 전체

---

## 요약

전반적으로 문서 규율이 좋은 편. 핵심 문제: (1) CLAUDE.md 서버 기동 명령어 2개 모두 틀림, (2) 핵심 spec 5개 상태 헤더 미갱신, (3) roadmap.md C6 "미착수"로 표시되어 있으나 실제 구현 완료, (4) Phase 1/2 문서 5개에 SUPERSEDED 마커 없음.

---

## Critical

### 1. CLAUDE.md 서버 기동 명령어 오류

**Cloud Server:**
```bash
# 문서: cd cloud_server && python -m uvicorn main:app --port 4010 --reload
# 정확: python -m uvicorn cloud_server.main:app --port 4010 --reload (프로젝트 루트에서)
```

**Local Server:**
```bash
# 문서: cd local_server && python -m uvicorn api.main:app --port 4020 --reload
# 정확: python -m uvicorn local_server.main:app --port 4020 --reload (프로젝트 루트에서)
```

두 가지 오류: (1) `cd` 후 실행하면 ModuleNotFoundError, (2) local_server에는 `api/main.py`가 없음.

### 2. roadmap.md — C6 "미착수" 표시 (실제 구현 완료)

Git 커밋으로 확인: C6-a 릴레이 인프라, C6-b 인증 확장, C6-c 원격 제어 모두 구현됨. 16/16 브라우저 테스트 PASS 리포트 존재.

---

## Spec 상태 헤더 불일치

| Spec 파일 | 현재 상태 | 실제 상태 |
|-----------|----------|----------|
| spec/system-trader/spec.md | 초안 | 구현 완료 |
| spec/rule-card-structured/spec.md | 초안 | 구현 완료 |
| spec/cloud-server/spec.md | 진행 중 | 구현 완료 |
| spec/local-server-core/spec.md | 초안 | 구현 완료 |
| spec/strategy-engine/spec.md | 초안 | 구현 완료 |
| spec/remote-control/spec.md | 확정 | 구현 완료 (C6) |

---

## SUPERSEDED 마커 필요 (Phase 1/2 문서)

| 파일 | 내용 |
|------|------|
| docs/project-blueprint.md | 2024-12 Phase 1; LSTM, backtrader, localhost:3000 |
| docs/development-plan.md | Phase 1; LSTM, Celery, 가상매매 1억 |
| docs/future-improvements.md | Phase 1/2 ML 개선 목록 |
| docs/log-system-improvements.md | Phase 1/2 로그 시스템 |
| docs/integrated-development-plan.md | Phase 1/2 통합 계획 |

docs/README.md에서 project-blueprint.md를 "먼저 읽으면 좋은 문서 #1"로 안내 — 오해 유발.

---

## CLAUDE.md 기타 불일치

- cloud_server api/ 주석: "(auth, rules, admin, stocks, ai)" → 실제: admin, ai, auth, context, dependencies, devices, heartbeat, market_data, rules, stocks, sync, version, watchlist, ws_relay
- frontend pages 주석: "(MainDashboard, Admin/*, Settings)" → 실제 13개 페이지
- frontend 구조에 hooks/, context/, stores/ 누락
- CORS 설명: "localhost:5173, localhost:3000 허용됨" → 프로덕션은 Vercel URL 사용

---

## docs/README.md 깨진 링크

- `docs/research/spec-review-result.md` — 파일 없음
- `docs/research/code-analysis-result.md` — 파일 없음

---

## architecture.md 누락 항목

코드에 존재하지만 문서에 없는 기능:
- E2E 암호화 (AES-256-GCM)
- WS Relay (/ws/relay, /ws/remote)
- OAuth2 소셜 로그인
- 디바이스 관리 API
- Pending command queue
- Inno Setup 설치파일
- Bridge Settings 페이지
- Frontend stores (alertStore, toastStore)

---

## 우선순위 액션

1. CLAUDE.md 기동 명령어 수정
2. roadmap.md C6 → "구현 완료" 갱신
3. 6개 spec 상태 헤더 갱신
4. docs/README.md 깨진 링크 수정
5. Phase 1/2 문서 5개에 SUPERSEDED 헤더 추가
6. architecture.md C6 기능 추가
7. CLAUDE.md 프로젝트 구조 갱신
