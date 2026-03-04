# strategy-builder 구현 보고서

> 작성일: 2026-03-04 | 커밋 대기

## 생성/수정 파일 목록

| 파일 | 내용 |
|------|------|
| `local_server/routers/config.py` | 규칙 CRUD (GET/POST/PUT/DELETE/PATCH toggle) + `/api/variables` |
| `frontend/src/services/rules.ts` | 로컬 서버 규칙 API 클라이언트 |
| `frontend/src/components/ConditionRow.tsx` | 조건 행 (변수/연산자/값 + 현재 값 미리보기) |
| `frontend/src/components/RuleList.tsx` | 규칙 목록 + ON/OFF 토글 + 수정/삭제 |
| `frontend/src/pages/StrategyBuilder.tsx` | 전략 빌더 페이지 (폼 + 목록) |
| `frontend/src/App.tsx` | `/strategy` 라우트 추가 |

## 주요 기능

### 규칙 CRUD API
- `GET /api/rules` — 규칙 목록
- `POST /api/rules` — 규칙 생성 (auto increment ID)
- `PUT /api/rules/{id}` — 규칙 수정
- `DELETE /api/rules/{id}` — 규칙 삭제
- `PATCH /api/rules/{id}/toggle` — is_active 토글
- 모든 변경 → `config_manager.update()` → 500ms debounce 클라우드 동기화

### 변수 목록 API
- `GET /api/variables` → market 변수 + price 변수 + 연산자 목록
- 현재 컨텍스트 캐시의 실제 값 포함 (UI 미리보기용)

### React UI
- 조건 행: 변수 드롭다운 + 연산자 셀렉트 + 값 입력 + 현재 값 배지 (충족/미충족 색상)
- 규칙 목록: ON/OFF 토글 + 수정/삭제 인라인 버튼
- 폼: 규칙 생성/수정 모드 공유

## 비고
- 백테스팅 연동(Step 4)은 기존 백테스팅 엔진과 연동 필요 — 별도 이터레이션 예정
- config.py의 `from main import config_manager` → `get_config_manager()` 싱글톤으로 교체됨
