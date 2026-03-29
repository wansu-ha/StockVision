# DSL 스키마 API + 프론트 파서 개선 + 자동완성 — 구현 계획서

> 작성일: 2026-03-29 | 상태: 초안

## 아키텍처

```
builtins.py ──to_schema()──→ cloud_server/api/dsl.py ──GET /dsl/schema──→ useDslSchema 훅
                                                                              ↓
                                                                    dslParserV2.ts (스키마 기반 분류)
                                                                    DslEditor.tsx (자동완성 UI)

rule_service.py ──create/update──→ parse_v2() ──→ dsl_meta (DB 저장)
                                                    ↓
                                              Rule 조회 응답에 포함
```

## 구현 순서

### Step 1: 백엔드 기반 — 스키마 직렬화 + API

**작업:**
- `sv_core/parsing/builtins.py`에 `to_schema()` 함수 추가
  - `BUILTIN_FIELDS` → `fields` 리스트
  - `COMPOUND_FIELDS` → `compound_fields` dict
  - `BUILTIN_FUNCTIONS` → `functions` dict (min_args, max_args, return_type)
  - `BUILTIN_PATTERNS` → `patterns` dict (definition)
  - `version` 필드 (builtins 정의의 해시)
- `cloud_server/api/dsl.py` 신규 — `GET /api/v1/dsl/schema` 라우터
- `cloud_server/main.py` — dsl 라우터 등록

**변경 파일:**
- `sv_core/parsing/builtins.py`
- `cloud_server/api/dsl.py` (신규)
- `cloud_server/main.py`

**verify:** `pytest` — to_schema() 단위 테스트 + curl로 엔드포인트 응답 확인

---

### Step 2: 백엔드 — v2 파서 소비 경로 통일

**작업:**
- `cloud_server/core/validators.py`: `parse()` → `parse_v2()` 전환
- `cloud_server/services/backtest_runner.py`: `parse()` → `parse_v2()` 전환
- 기존 테스트가 있으면 v2 스크립트로 테스트 추가

**변경 파일:**
- `cloud_server/core/validators.py`
- `cloud_server/services/backtest_runner.py`

**verify:** `pytest` — v1/v2 스크립트 모두 검증 통과 확인

---

### Step 3: 백엔드 — dsl_meta 모델 + 저장 흐름

**작업:**
- `cloud_server/models/rule.py`: `dsl_meta = Column(JSON, nullable=True)` 추가
- DB 마이그레이션 (개발: SQLite, 운영: PostgreSQL)
- `cloud_server/api/rules.py`: `_extract_parameters()` 확장 → dsl_meta도 함께 생성
  - `parse_v2()` 1회 실행 → constants/custom_functions/rules/errors/parse_status 추출
  - 파싱 실패 시 errors + parse_status="error" 기록, 저장 허용
  - `validate_dsl_script()` 별도 호출 제거 — `_extract_parameters()`에서 파싱과 검증을 한 번에 처리 (이중 파싱 방지)
- `cloud_server/services/rule_service.py`:
  - validate_dsl_script 개별 호출 제거 → `_extract_parameters()`가 반환한 dsl_meta.parse_status로 판단
  - **create 경로**: 파싱 실패 시 `is_active`를 강제로 `False`로 설정 (기본값이 True이므로)
  - **update 경로**: `is_active=true` 전환 요청 시 `parse_status` 체크 (error면 400). script 변경으로 파싱 실패 시 `is_active`를 강제 `False`로 전환 (기존에 켜져 있던 전략이 깨진 DSL로 활성 상태 유지되는 것 방지)
  - updatable 리스트에 `dsl_meta` 추가
- 조회 응답에 dsl_meta 포함 확인
- **기존 규칙 마이그레이션**: DB에 이미 저장된 규칙(dsl_meta=null)을 한 번에 파싱하여 dsl_meta 채우는 스크립트 작성. 서버 시작 시 또는 일회성 마이그레이션으로 실행

**변경 파일:**
- `cloud_server/models/rule.py`
- `cloud_server/api/rules.py`
- `cloud_server/services/rule_service.py`

**verify:** 규칙 저장 → 조회 → dsl_meta 필드 존재 확인. 유효/무효 스크립트 모두 테스트. 기존 규칙에도 dsl_meta가 채워졌는지 확인

---

### Step 4: 프론트 — 스키마 훅 + 파서 개선

**작업:**
- `frontend/src/hooks/useDslSchema.ts` 신규
  - `cloudClient.get('/dsl/schema')` → `staleTime: Infinity`
- `frontend/src/utils/dslParserV2.ts` 개선
  - `DslParseResult`에 `customFunctions`, `errors` 필드 추가
  - `parseFloat` 실패 시 → customFunctions로 분류 (silent discard 제거)
  - `parseDslV2(script, schema?)` — 스키마 선택적 파라미터
  - 기본 에러 감지: 화살표 없는 줄이 상수/함수도 아니면 errors에 추가
- `frontend/src/types/strategy.ts` — `DslMeta`, `DslSchema` 타입 추가
- 테스트 추가

**변경 파일:**
- `frontend/src/hooks/useDslSchema.ts` (신규)
- `frontend/src/utils/dslParserV2.ts`
- `frontend/src/utils/__tests__/dslParserV2.test.ts`
- `frontend/src/types/strategy.ts`

**verify:** `vitest run` — 커스텀 함수 인식 테스트 + 에러 감지 테스트 통과

---

### Step 5: 프론트 — dsl_meta 소비 + DslEditor v2 전환

**작업:**
- `ParameterSliders.tsx` 수정:
  - props에 `dslMeta?: DslMeta` 추가. 있으면 그 안의 constants 사용, 없으면 `parseDslV2(script)` fallback
  - 서버 파싱 결과가 정본, 로컬 파서는 편집 중 실시간 피드백용
- `StrategyBuilder.tsx` 수정:
  - 규칙 로드 시 `rule.dsl_meta`를 `ParameterSliders`에 prop으로 전달
  - 편집 중(저장 전)에는 dsl_meta가 stale이므로 전달하지 않음 → 로컬 파서 fallback
- `DslEditor.tsx` 수정:
  - `parseDsl` → `parseDslV2` import 전환
  - 300ms 디바운스 검증을 v2 파서 기반으로
  - placeholder를 v2 예시로 변경 (예: `RSI(14) < 30 → 매수 100%`)

**변경 파일:**
- `frontend/src/components/ParameterSliders.tsx`
- `frontend/src/components/DslEditor.tsx`
- `frontend/src/pages/StrategyBuilder.tsx`

**verify:** `npm run build` + `vitest run`. ParameterSliders가 dsl_meta 기반으로 슬라이더 생성 확인. DslEditor가 v2 파서로 에러 표시 확인

---

### Step 6: 프론트 — 자동완성 UI

**작업:**
- `DslEditor.tsx`에 자동완성 추가:
  - textarea의 커서 위치에서 현재 토큰 추출
  - useDslSchema 데이터에서 prefix 매칭
  - 드롭다운 오버레이 (최대 8개 후보)
  - Tab/Enter로 삽입, Esc로 닫기, 화살표 키 탐색
  - 함수 선택 시 인자 힌트 표시
  - 트리거: 알파벳/한글 2글자+ (디바운스 150ms)

**변경 파일:**
- `frontend/src/components/DslEditor.tsx`

**verify:** `npm run build` + 브라우저에서 자동완성 동작 확인. 한글 입력 호환 확인

---

### Step 7: 통합 확인 + backtest 경로

**작업:**
- **backtest 400 처리**: `cloud_server/api/backtest.py`에서 규칙 로드 후 `dsl_meta.parse_status` 체크 → error면 400 반환. 실제 HTTP 응답 결정은 `backtest.py`가 담당 (backtest_runner.py는 실행기일 뿐)
- 전체 흐름 E2E 확인:
  - 앱 시작 → 스키마 fetch 확인
  - 규칙 편집 → 자동완성 동작
  - 저장 → dsl_meta 생성 확인
  - 유효하지 않은 스크립트 저장 → parse_status="error" + 활성화 차단 확인
  - 로드 → dsl_meta 포함 확인

**변경 파일:**
- `cloud_server/api/backtest.py` (parse_status 체크 + 400 반환)
- `cloud_server/services/backtest_runner.py` (parse_v2 전환은 Step 2에서 완료)

**verify:** 전체 흐름 수동 테스트 + 기존 테스트 전부 통과 확인

---

## 검증 방법

| 단계 | 검증 |
|------|------|
| Step 1 | `pytest sv_core/` + `curl /api/v1/dsl/schema` |
| Step 2 | `pytest cloud_server/` — v1/v2 스크립트 검증 |
| Step 3 | 규칙 CRUD → dsl_meta 필드 확인 + 기존 규칙 마이그레이션 |
| Step 4 | `vitest run` — 파서 테스트 |
| Step 5 | `npm run build` + ParameterSliders/DslEditor v2 동작 |
| Step 6 | `npm run build` + 브라우저 자동완성 |
| Step 7 | 전체 흐름 E2E + `pytest` + `vitest` |

## 브랜치

`feat/dsl-schema-api` (dev에서 분기)
