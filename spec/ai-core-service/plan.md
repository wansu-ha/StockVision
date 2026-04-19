# AI 코어 서비스 — 구현 계획서

> 작성일: 2026-03-29 | 상태: 구현 완료 | spec: spec/ai-core-service/spec.md

## 의존성

- **preset-expansion** ✅ 완료 (few-shot 예시용 프리셋, 전략 상태 요약 컴포넌트)
- **dsl-schema-api** 먼저 완료해야 함 (스키마 API, 자동완성, DslEditor v2 전환, validators v2)

## 아키텍처

```
cloud_server/
├─ services/
│  ├─ ai_chat_service.py     ← 신규: 전략 빌더/비서 대화 서비스
│  └─ credit_service.py      ← 신규: 크레딧 관리
├─ api/
│  └─ ai.py                  ← 확장: SSE 대화, 크레딧, 대화 히스토리, BYO Key API
├─ models/
│  ├─ ai_conversation.py     ← 신규: 대화 히스토리
│  ├─ ai_usage.py            ← 신규: 크레딧 추적
│  ├─ ai_api_key.py          ← 신규: BYO Key 암호화 저장
│  └─ strategy_version.py    ← 신규: 전략 버전 스냅샷
├─ core/
│  ├─ config.py              ← 확장: 환경변수 추가
│  └─ encryption.py          ← 신규: Fernet 암호화 유틸
└─ prompts/
   └─ strategy_builder.py    ← 신규: 시스템 프롬프트 관리

frontend/src/
├─ components/
│  ├─ ai/
│  │  ├─ AIChatPanel.tsx     ← 신규: AI 대화 패널
│  │  ├─ ChatMessage.tsx     ← 신규: 메시지 컴포넌트 (thinking 접기/펴기)
│  │  ├─ CreditBar.tsx       ← 신규: 크레딧 잔량 바
│  │  ├─ DslDiffView.tsx     ← 신규: DSL 디프 하이라이트
│  │  └─ StatusIndicator.tsx ← 신규: SSE 단계 표시
│  └─ editor/
│     ├─ DslEditor.tsx       ← 신규: 코드 에디터 (하이라이팅 + 자동완성)
│     └─ DslHighlighter.tsx  ← 신규: 구문 하이라이팅 로직
├─ hooks/
│  ├─ useAIChat.ts           ← 신규: SSE 대화 훅
│  └─ useCredit.ts           ← 신규: 크레딧 조회 훅
├─ services/
│  └─ cloudClient.ts         ← 확장: AI 대화/크레딧/버전 API
├─ pages/
│  └─ StrategyBuilder.tsx    ← 확장: 분할 레이아웃 + 대화 패널 통합
└─ types/
   └─ ai.ts                  ← 신규: AI 관련 타입
```

## 수정 파일 목록

| 파일 | 변경 |
|------|------|
| **백엔드 — 신규** | |
| `cloud_server/services/ai_chat_service.py` | 대화 서비스 (Claude 스트리밍, 검증 루프, 윈도우 구성) |
| `cloud_server/services/credit_service.py` | 크레딧 차감/조회/초기화 |
| `cloud_server/core/encryption.py` | Fernet 암호화/복호화 유틸 |
| `cloud_server/prompts/strategy_builder.py` | 시스템 프롬프트 (~3K 토큰) |
| `cloud_server/models/ai_conversation.py` | AIConversation 모델 |
| `cloud_server/models/ai_usage.py` | AIUsage 모델 |
| `cloud_server/models/ai_api_key.py` | AIApiKey 모델 |
| `cloud_server/models/strategy_version.py` | StrategyVersion 모델 |
| **백엔드 — 수정** | |
| `cloud_server/api/ai.py` | SSE 대화, 크레딧, 대화 히스토리, BYO Key 엔드포인트 추가 |
| `cloud_server/api/rules.py` | 버전 목록/디프/되돌리기 엔드포인트 추가 |
| `cloud_server/core/config.py` | 환경변수 7개 추가 |
| `cloud_server/models/__init__.py` | 신규 모델 import |
| `render.yaml` | 환경변수 추가 |
| **프론트엔드 — 신규** | |
| `frontend/src/components/ai/AIChatPanel.tsx` | AI 대화 패널 |
| `frontend/src/components/ai/ChatMessage.tsx` | 메시지 (thinking, DSL 블록) |
| `frontend/src/components/ai/CreditBar.tsx` | 크레딧 바 |
| `frontend/src/components/ai/DslDiffView.tsx` | DSL 디프 하이라이트 |
| `frontend/src/components/ai/StatusIndicator.tsx` | SSE 단계 표시 |
| `frontend/src/components/editor/DslEditor.tsx` | 코드 에디터 |
| `frontend/src/components/editor/DslHighlighter.tsx` | 구문 하이라이팅 |
| `frontend/src/hooks/useAIChat.ts` | SSE 대화 훅 |
| `frontend/src/hooks/useCredit.ts` | 크레딧 조회 훅 |
| `frontend/src/types/ai.ts` | 타입 정의 |
| **프론트엔드 — 수정** | |
| `frontend/src/services/cloudClient.ts` | AI 대화/크레딧/버전 API 추가 |
| `frontend/src/pages/StrategyBuilder.tsx` | 분할 레이아웃 + 대화 패널 통합 |
| `frontend/src/pages/Settings.tsx` | BYO Key 등록/삭제, thinking 토글 |

---

## 구현 순서

### Step 1 — DB 모델 + 마이그레이션

**작업:**
- `ai_conversation.py`: AIConversation (id, user_id, strategy_id, title, messages JSON, current_dsl, mode, timestamps)
- `ai_usage.py`: AIUsage (id, user_id, date, tokens_used, tokens_limit, UNIQUE(user_id, date))
- `ai_api_key.py`: AIApiKey (id, user_id UNIQUE, encrypted_key, timestamp)
- `strategy_version.py`: StrategyVersion (id, rule_id, version, script, message, created_by, timestamp, UNIQUE(rule_id, version))
- `models/__init__.py` import 추가
- Alembic 마이그레이션 생성

**검증:**
- `alembic upgrade head` 성공
- 각 테이블 생성 확인
- `python -m pytest cloud_server/tests/ -v`

### Step 2 — 크레딧 서비스 + 암호화

**작업:**
- `credit_service.py`:
  - `get_or_create_daily(user_id, date)` → AIUsage 레코드
  - `deduct(user_id, tokens)` → 차감, 한도 초과 시 raise
  - `get_balance(user_id)` → 잔량 %, 예상 횟수
  - `is_byo_user(user_id)` → BYO Key 등록 여부
- `encryption.py`:
  - `encrypt(plaintext)` → Fernet 암호화
  - `decrypt(ciphertext)` → 복호화
- `config.py` 환경변수 추가: AI_DAILY_TOKEN_LIMIT, AI_ENCRYPTION_KEY 등

**검증:**
- 크레딧 차감/조회 단위 테스트
- 암호화/복호화 왕복 테스트
- `python -m pytest cloud_server/tests/ -v`

### Step 3 — 시스템 프롬프트 + 대화 서비스

**작업:**
- `prompts/strategy_builder.py`:
  - 시스템 프롬프트 ~3K 토큰 (역할, 문법 요약, 필드/함수 목록, few-shot, 제약사항)
  - builtins.py에서 자동 생성하는 함수 목록 섹션
- `ai_chat_service.py`:
  - `chat(conversation_id, message, current_dsl, mode, thinking, user_id)` → AsyncGenerator
  - 내부 흐름:
    1. 크레딧 확인 (BYO 분기)
    2. 대화 히스토리 DB 조회
    3. LLM 윈도우 구성 (시스템 프롬프트 + 현재 DSL + 최근 N턴)
    4. Claude API 스트리밍 호출
    5. DSL 추출 → parse_v2 검증 → 실패 시 재시도 (최대 3회)
    6. 대화 히스토리 DB 저장
    7. 크레딧 차감 (재시도 토큰 제외)
  - builder 모드: Sonnet + DSL 검증
  - assistant 모드: Haiku + 검증 없음

**검증:**
- 프롬프트 토큰 수 확인 (~3K)
- 대화 서비스 단위 테스트 (mock Claude API)
- 검증 루프 테스트 (parse_v2 실패 → 재시도 → 성공)
- `python -m pytest cloud_server/tests/ -v`

### Step 4 — API 엔드포인트

**작업:**
- `api/ai.py` 확장:
  - `POST /ai/chat` — SSE StreamingResponse
  - `GET /ai/conversations` — 대화 목록
  - `GET /ai/conversations/{id}` — 대화 상세
  - `DELETE /ai/conversations/{id}` — 대화 삭제
  - `GET /ai/credit` — 크레딧 잔량
  - `GET /ai/builtins` — 필드/함수 목록
  - `POST /ai/apikey` — BYO Key 등록
  - `DELETE /ai/apikey` — BYO Key 삭제
- `api/rules.py` 확장:
  - `GET /rules/{id}/versions` — 버전 목록
  - `GET /rules/{id}/versions/{v1}/diff/{v2}` — 디프
  - `POST /rules/{id}/versions/{v}/restore` — 되돌리기

**검증:**
- 각 엔드포인트 HTTP 테스트 (httpx/TestClient)
- SSE 스트리밍 이벤트 순서 확인
- 인증/권한 테스트
- `python -m pytest cloud_server/tests/ -v`

### Step 5 — 프론트 타입 + API 클라이언트

**작업:**
- `types/ai.ts`: SSE 이벤트 타입, 대화 타입, 크레딧 타입
- `cloudClient.ts` 확장:
  - `cloudAI.chat(params)` → EventSource SSE 연결
  - `cloudAI.conversations()` → 대화 목록
  - `cloudAI.credit()` → 크레딧 잔량
  - `cloudAI.registerKey(key)` / `cloudAI.deleteKey()`
  - `cloudRules.versions(id)` / `cloudRules.diff(id, v1, v2)` / `cloudRules.restore(id, v)`
- `useAIChat.ts`: SSE 연결, 메시지 관리, 스트리밍 상태
  - **주의**: 표준 EventSource는 GET만 지원하고 커스텀 헤더(JWT) 불가. `fetch` + ReadableStream으로 POST SSE 구현하거나, GET + query param에 JWT 토큰 전달 방식 사용
- `useCredit.ts`: React Query로 크레딧 폴링

**검증:**
- TypeScript 컴파일: `cd frontend && npm run build`
- 훅 단위 테스트

### Step 6 — 코드 인텔리전스 (에디터)

> 자동완성, DslEditor v2 전환, 스키마 API는 `dsl-schema-api`에서 구현 완료 전제.
> 여기서는 dsl-schema-api가 제외한 **구문 하이라이팅 + 인라인 에러**만 추가.

**작업:**
- `DslHighlighter.tsx`: 토큰별 색상 매핑 (키워드, 함수, 상수, 숫자)
- `DslEditor.tsx`에 하이라이팅 오버레이 통합 (dsl-schema-api의 자동완성과 공존)
- 인라인 에러: parse_v2 실패 위치에 빨간 밑줄 (dsl-schema-api S2의 errors 배열 활용)

**검증:**
- 프리셋 DSL 입력 시 하이라이팅 정상
- 에러 있는 DSL 입력 시 빨간 밑줄
- `cd frontend && npm run build && npm run lint`

### Step 7 — AI 대화 패널 + 레이아웃

**작업:**
- `AIChatPanel.tsx`: 대화 UI (메시지 목록, 입력, 모드 전환)
- `ChatMessage.tsx`: 메시지 렌더링 (thinking 접기/펴기, DSL 코드 블록)
- `StatusIndicator.tsx`: SSE 단계 표시 (분석 중, 생성 중, 검증 중...)
- `CreditBar.tsx`: 크레딧 잔량 바 (% + 예상 횟수)
- `DslDiffView.tsx`: 디프 하이라이트 (추가=초록, 삭제=빨강)
- `StrategyBuilder.tsx` 레이아웃 변경:
  - 데스크톱: 대화 패널 + 편집기 나란히
  - 모바일: [대화] [편집기] 탭 전환
  - 새 전략: 스트리밍 → 편집기 실시간 반영
  - 기존 수정: 디프 하이라이트 + [적용] 버튼

**검증:**
- 데스크톱: 분할 레이아웃 확인
- 모바일: 탭 전환 확인
- 대화 → DSL 생성 → 편집기 반영 흐름
- `cd frontend && npm run build && npm run lint`

### Step 8 — 전략 버전 + BYO Key UI

**작업:**
- 버전 스냅샷:
  - AI 수정 / 수동 저장 시 자동 스냅샷
  - 버전 목록 패널 (편집기 하단)
  - 디프 비교 + 되돌리기
- BYO Key:
  - Settings 페이지에 API Key 등록/삭제 UI
  - thinking 토글 (설정)
- 크레딧 초기화:
  - 자정 리셋 스케줄러 (APScheduler, 기존 패턴)

**검증:**
- AI 수정 → 버전 생성 확인
- 되돌리기 → 이전 DSL 복원 확인
- BYO Key 등록 → 크레딧 무제한 확인
- Settings 페이지 UI 확인
- `cd frontend && npm run build && npm run lint`

### Step 9 — E2E 통합 테스트

**작업:**
- 전체 플로우 테스트:
  1. 자연어 → DSL 생성 → 편집기 반영 → 저장
  2. 수정 요청 → 디프 → 적용 → 버전 스냅샷
  3. 설명 요청 → 텍스트 응답
  4. 크레딧 소진 → 에러 메시지
  5. BYO Key 등록 → 무제한
  6. 기본 비서 → Haiku 응답 → 크레딧 미차감
  7. 모바일 탭 전환

**검증:**
- 기존 테스트 전체 통과
- `python -m pytest --tb=short`
- `cd frontend && npm run build && npm run lint`

---

## 검증 방법 (전체)

| 단계 | 검증 |
|------|------|
| Step 1~4 | `python -m pytest cloud_server/tests/ -v` |
| Step 5~8 | `cd frontend && npm run build && npm run lint` |
| Step 9 | E2E 통합 테스트 |
| 전체 | 기존 테스트 회귀 없음 + 신규 테스트 추가 |
| 브라우저 | 대화 → 생성 → 수정 → 버전 → 크레딧 전체 흐름 |
