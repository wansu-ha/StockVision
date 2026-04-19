# DSL 스키마 API + 프론트 파서 개선 + 자동완성 — 기능 명세서

> 작성일: 2026-03-29 | 상태: 구현 완료

## 1. 목표

DSL v2의 문법 계약을 단일화하고, 에디터 UX를 강화한다.

### 해결하는 문제

1. 프론트 `dslParserV2.ts`가 커스텀 함수 선언을 인식 못 함 (silent discard)
2. DSL 문법 변경 시 프론트 파서도 매번 수정해야 하는 구조적 문제
3. 내장 함수/필드 20개+를 사용자가 다 외워야 함 (자동완성 없음)
4. `DslEditor.tsx`가 v1 파서(`parseDsl`)로 검증 중 — v2 스크립트와 불일치
5. `validators.py`가 `parse()`(v1)로 검증 — v2 스크립트 저장 시 오류 가능

---

## 2. 범위

### 2.1 포함

| # | 항목 |
|---|------|
| S1 | 스키마 API (`GET /api/v1/dsl/schema`) — 내장 필드/함수/패턴 목록 반환 |
| S2 | 프론트 파서 개선 — 커스텀 함수 인식 + 스키마 기반 어휘 판단 |
| S3 | 자동완성 UI — 에디터에서 타이핑 시 함수/필드/패턴 후보 표시 |
| S4 | parse-meta 캐싱 — 규칙 저장 시 `parse_v2` 실행, `dsl_meta` 필드에 결과 저장 |
| S5 | DslEditor v2 전환 — v1 `parseDsl` → v2 `parseDslV2` 기반 검증 |
| S6 | validators.py v2 전환 — `parse()` → `parse_v2()` |

### 2.2 제외

- TS full 파서 포팅 (Python 파서를 TypeScript로 전체 재작성)
- 구문 하이라이팅 (색상별 토큰 구분)
- 에디터 인라인 에러 위치 표시 (커서 위치 기반 밑줄)

---

## 3. 요구사항

### S1: 스키마 API

**엔드포인트:** `GET /api/v1/dsl/schema`
**서버:** cloud_server (:4010)
**구현:** `sv_core/parsing/builtins.py`에 `to_schema()` 직렬화 함수 추가, 라우터에서 호출

**응답:**
```json
{
  "success": true,
  "data": {
    "version": "2026-03-29T...",
    "fields": ["현재가", "거래량", "수익률", "보유수량", "고점 대비", "수익률고점", "진입가", "보유일", "보유봉", "시간", "장시작후", "요일", "실행횟수"],
    "compound_fields": {"고점": "고점 대비"},
    "functions": {
      "RSI": {"min_args": 1, "max_args": 2, "return_type": "number"},
      "MA": {"min_args": 1, "max_args": 2, "return_type": "number"},
      "상향돌파": {"min_args": 2, "max_args": 2, "return_type": "boolean"},
      ...
    },
    "patterns": {
      "골든크로스": {"definition": "상향돌파(MA(5), MA(20))"},
      "RSI과매도": {"definition": "RSI(14) <= 30"},
      ...
    }
  }
}
```

**요구사항:**
- `version` 필드 포함 — 스키마 변경 감지용 (서버 빌드 시점 또는 builtins.py 해시)
- 인증 불필요 (공개 메타데이터)
- 캐시 헤더: `Cache-Control: public, max-age=86400`

### S2: 프론트 파서 개선

**파일:** `frontend/src/utils/dslParserV2.ts`

**변경사항:**
- `parseFloat` 실패 시 silent discard → `customFunctions` 배열로 분류
- 스키마 데이터를 선택적으로 받아 내장 필드/함수 판별에 활용
- 스키마 미로드 시 기존 로직으로 fallback

**반환 타입 확장:**
```typescript
interface DslParseResult {
  constants: DslConstant[]
  customFunctions: DslCustomFunction[]  // 신규
  rules: DslRule[]
  errors: DslParseError[]               // 신규 — DslEditor 검증용
  isV2: boolean
}

interface DslCustomFunction {
  name: string
  body: string  // 우변 원문
}

interface DslParseError {
  line: number
  column: number
  message: string
}
```

### S3: 자동완성 UI

**파일:** `frontend/src/components/DslEditor.tsx`

**동작:**
- 트리거: 알파벳/한글 2글자 이상 타이핑 시 자동 표시 (디바운스 150ms)
- 현재 커서 위치의 토큰을 추출, 스키마의 필드/함수/패턴 목록에서 prefix 매칭
- 드롭다운으로 후보 표시 (최대 8개), 클릭 또는 Tab/Enter로 삽입
- 함수 선택 시 인자 힌트 표시 (예: `RSI(기간, 타임프레임?)`)
- Esc로 닫기, 화살표 키로 후보 탐색

**데이터 소스:** `useDslSchema` 훅이 반환하는 캐시된 스키마

**스키마 훅:**
```typescript
// frontend/src/hooks/useDslSchema.ts
export function useDslSchema() {
  return useQuery({
    queryKey: ['dsl-schema'],
    queryFn: () => cloudClient.get('/dsl/schema').then(r => r.data.data),
    staleTime: Infinity,
  })
}
```

### S4: parse-meta 캐싱

**모델 변경:** `cloud_server/models/rule.py`에 `dsl_meta` JSON 컬럼 추가
- `parameters` (기존) — 상수 슬라이더용, 유지
- `dsl_meta` (신규) — 정식 파싱 결과

**dsl_meta 형식:**
```json
{
  "constants": [{"name": "기간", "value": 14}],
  "custom_functions": [{"name": "손절", "body": "-3"}, {"name": "과매도", "body": "RSI(14) <= 30"}],
  "rules": [{"index": 0, "condition": "RSI(14) < 30 AND 보유수량 == 0", "side": "매수", "qty": "100%"}],
  "is_v2": true,
  "errors": []
}
```

**저장 흐름:**
- `rule_service.py`의 create/update에서 script가 있으면 `parse_v2()` 실행
- 파싱 성공 → `dsl_meta`에 결과 저장, `parameters`도 상수에서 추출하여 갱신
- 파싱 실패 → `dsl_meta.errors`에 에러 기록, `dsl_meta.parse_status`를 `"error"`로 설정
- 저장은 허용하되, `parse_status`가 `"error"`인 규칙은 엔진 활성화(is_active=true) 불가

**parse_status 값:**
- `"ok"` — 파싱 성공, 실행 가능
- `"error"` — 파싱 실패, 편집만 가능 (is_active 전환 시 400 반환)

**조회 응답:** 기존 Rule 응답에 `dsl_meta` 필드 추가

### S5: DslEditor v2 전환

**파일:** `frontend/src/components/DslEditor.tsx`

**변경사항:**
- `import { parseDsl } from '../utils/dslParser'` → `import { parseDslV2 } from '../utils/dslParserV2'`
- 300ms 디바운스 검증을 v2 파서 기반으로 전환
- 자동완성 드롭다운 통합
- placeholder를 v2 예시로 변경

### S6: v2 파서 소비 경로 통일

**변경 대상:**

| 파일 | 현재 | 변경 |
|------|------|------|
| `cloud_server/core/validators.py` | `parse()` (v1) | `parse_v2()` |
| `cloud_server/services/backtest_runner.py` | `parse()` (v1) | `parse_v2()` |
| `cloud_server/services/rule_service.py` | `validate_dsl_script()` 실패 시 400 | 실패 시 저장 허용, `dsl_meta.parse_status="error"` |

**동작 변경:**
- `validate_dsl_script()` 내부: `parse()` → `parse_v2()`
- v1 스크립트도 `parse_v2`가 호환 처리하므로 하위 호환 유지
- 검증 실패 시: 저장은 허용하되 `dsl_meta.parse_status="error"`, `is_active=true` 전환은 차단
- backtest_runner도 `parse_v2`로 전환하여 저장/검증/실행 경로 일치
- backtest API가 `parse_status="error"`인 규칙을 받으면 400 반환: `{"success": false, "detail": "DSL 파싱 오류가 있는 규칙은 백테스트할 수 없습니다"}`

---

## 4. 변경 파일 (예상)

| 파일 | 변경 |
|------|------|
| `sv_core/parsing/builtins.py` | `to_schema()` 직렬화 함수 추가 |
| `cloud_server/api/dsl.py` | **신규** — 스키마 API 라우터 |
| `cloud_server/main.py` | dsl 라우터 등록 |
| `cloud_server/models/rule.py` | `dsl_meta` JSON 컬럼 추가 |
| `cloud_server/services/rule_service.py` | 저장 시 `parse_v2` 실행 + dsl_meta 저장 |
| `cloud_server/core/validators.py` | `parse()` → `parse_v2()` |
| `cloud_server/services/backtest_runner.py` | `parse()` → `parse_v2()` |
| `frontend/src/hooks/useDslSchema.ts` | **신규** — 스키마 fetch 훅 |
| `frontend/src/utils/dslParserV2.ts` | 커스텀 함수 인식 + 스키마 기반 분류 |
| `frontend/src/utils/__tests__/dslParserV2.test.ts` | 테스트 추가 |
| `frontend/src/components/DslEditor.tsx` | v2 파서 전환 + 자동완성 UI |
| `frontend/src/types/condition-status.ts` 또는 `strategy.ts` | DslMeta 타입 추가 |

---

## 5. 수용 기준

- [ ] `GET /api/v1/dsl/schema`가 현재 builtins.py의 필드/함수/패턴을 정확히 반환한다
- [ ] 스키마 응답에 `version` 필드가 포함된다
- [ ] `parseDslV2("과매도 = RSI(14) <= 30")`이 `customFunctions`에 포함된다
- [ ] `parseDslV2`가 스키마 없이도 fallback으로 동작한다
- [ ] DSL 에디터에서 `RSI` 타이핑 시 자동완성 후보가 표시된다
- [ ] 자동완성에서 함수 선택 시 인자 힌트가 표시된다
- [ ] 규칙 저장 시 `dsl_meta`가 자동 생성되어 DB에 저장된다
- [ ] 규칙 조회 응답에 `dsl_meta` 필드가 포함된다
- [ ] `DslEditor`가 v2 파서로 검증한다
- [ ] `validate_dsl_script()`가 v2 스크립트를 정상 검증한다
- [ ] v1 스크립트(`매수:/매도:` 형식)도 여전히 저장/검증 가능하다
- [ ] 파싱 실패한 스크립트도 저장 가능하되, `parse_status="error"`이고 활성화 불가하다
- [ ] backtest_runner가 `parse_v2`로 v2 스크립트를 백테스트할 수 있다
- [ ] `parseDslV2`가 `errors` 배열을 반환하고, DslEditor가 이를 표시한다

---

## 6. 흐름 요약

```
앱 시작       →  GET /api/v1/dsl/schema (1회) → 캐시 (staleTime: Infinity)
타이핑 중     →  프론트 파서(S2)로 상수/함수 추출 → ParameterSliders
              →  캐시된 스키마(S1)로 자동완성 후보 표시(S3)
              →  v2 파서(S5)로 300ms 디바운스 검증 → 에러 표시
저장          →  기존 저장 API 호출 (추가 호출 없음)
              →  cloud_server가 validate_dsl_script(S6)으로 검증
              →  cloud_server가 parse_v2 실행 → dsl_meta 저장(S4)
다음 로드     →  규칙 응답에 dsl_meta 포함 → 프론트가 정식 파싱 결과 사용
```
