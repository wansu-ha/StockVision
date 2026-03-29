# AI 코어 서비스 — 기능 명세서

> 작성일: 2026-03-29 | 상태: 초안

## 1. 목표

사용자가 자연어로 전략을 생성/수정/분석할 수 있는 AI 코파일럿과, 초보자를 안내하는 기본 비서를 제공한다. AI 없이도 모든 기능을 직접 사용할 수 있으며, AI는 편의 레이어다.

### 해결하는 문제

- DSL 문법을 모르는 80% 사용자가 전략을 만들 수 없다
- 초보자가 기능을 찾아 헤맨다
- 전략 수정 시 실수 추적이 안 된다

---

## 2. 요구사항

### 2.1 기능 요구사항

#### Unit 1 — 전략 빌더 (코파일럿)

| ID | 요구사항 |
|----|---------|
| F1.1 | 사용자가 자연어로 전략을 설명하면 v2 DSL 코드를 생성한다 |
| F1.2 | 기존 DSL에 대해 수정 요청을 처리한다 ("트레일링 추가해줘") |
| F1.3 | DSL 코드에 대한 설명/분석 요청을 처리한다 ("이 전략 리스크가 뭐야") |
| F1.4 | 생성된 DSL은 서버에서 parse_v2()로 검증한다. 실패 시 에러 피드백 포함하여 최대 3회 자동 재시도 |
| F1.5 | 응답은 SSE(Server-Sent Events)로 스트리밍한다 |
| F1.6 | SSE 이벤트로 단계 표시를 전송한다 (분석 중, 생성 중, 검증 완료, 재시도 등) |
| F1.7 | extended thinking 옵션을 설정에서 토글할 수 있다. ON 시 thinking 내용을 접기/펴기로 확인 가능 |

#### Unit 2 — 기본 비서

| ID | 요구사항 |
|----|---------|
| F2.1 | Haiku 모델로 범용 안내/FAQ/기능 설명을 제공한다 |
| F2.2 | 운영자 키를 사용하며 사용자에게 무료다 |
| F2.3 | 개인화 없음. 대화를 저장하지 않는다 |
| F2.4 | 전략 빌더와 같은 대화 패널에서 모드 전환으로 동작한다 (StrategyBuilder 내 한정) |

#### Unit 3 — 크레딧제 + BYO Key

| ID | 요구사항 |
|----|---------|
| F3.1 | 전략 빌더/종목 분석기 사용 시 토큰 기반 크레딧을 차감한다 |
| F3.2 | 일일 토큰 한도를 설정한다 (환경변수, 기본 50K) |
| F3.3 | 크레딧 잔량을 % + "약 N회 대화 가능" 형태로 프론트에 표시한다 |
| F3.4 | 매일 자정(KST) 크레딧을 초기화한다 |
| F3.5 | 검증/백테스트는 크레딧 차감하지 않는다 |
| F3.6 | 재시도(parse_v2 검증 실패)는 크레딧 차감하지 않는다 |
| F3.7 | 기본 비서(Haiku)는 크레딧 차감하지 않는다 |
| F3.8 | 사용자가 자신의 Anthropic API Key를 등록할 수 있다 (BYO Key) |
| F3.9 | BYO Key 사용자는 크레딧 무제한이다. 본인 키로 직접 과금된다 |
| F3.10 | BYO Key는 서버 DB에 암호화 저장한다 |

#### Unit 4 — 대화 히스토리

| ID | 요구사항 |
|----|---------|
| F4.1 | 전략 빌더 대화를 서버 DB에 전체 저장한다 (멀티 디바이스 동기화) |
| F4.2 | 전략 ID별로 대화를 연결한다. 새 전략은 임시 ID → 저장 시 전략 ID로 전환 |
| F4.3 | 프론트에서 전체 대화 히스토리를 스크롤로 표시한다 |
| F4.4 | LLM 전송 시에는 시스템 프롬프트 + 현재 DSL + 최근 N턴만 보낸다 (고정 윈도우) |
| F4.5 | 대화 목록을 조회할 수 있다 |
| F4.6 | 대화를 삭제할 수 있다 |

#### Unit 5 — 전략 버전 스냅샷

| ID | 요구사항 |
|----|---------|
| F5.1 | AI가 DSL을 수정할 때마다 자동으로 버전 스냅샷을 저장한다 |
| F5.2 | 수동 저장(사용자가 직접 편집 후 저장) 시에도 스냅샷을 저장한다 |
| F5.3 | 각 스냅샷에 변경 요약 메시지를 포함한다 |
| F5.4 | 버전 목록을 조회할 수 있다 |
| F5.5 | 두 버전 간 디프를 비교할 수 있다 |
| F5.6 | 이전 버전으로 되돌릴 수 있다 |

#### Unit 6 — 코드 인텔리전스

> S3 자동완성, S1 스키마 API는 `spec/dsl-schema-api`에서 구현. 여기서는 AI 대화 패널과 통합되는 부분만 다룬다.

| ID | 요구사항 |
|----|---------|
| F6.1 | DSL 편집기에 구문 하이라이팅을 적용한다 (키워드, 상수, 숫자, 함수, 연산자 색 구분) |
| F6.2 | parse_v2 실패 시 에러 위치에 인라인 에러 표시 (빨간 밑줄) |
| F6.3 | ~~자동완성~~ → `dsl-schema-api` S3에서 구현 |
| F6.4 | ~~builtins API~~ → `dsl-schema-api` S1에서 구현 (`GET /api/v1/dsl/schema`) |

#### Unit 7 — UI 레이아웃

| ID | 요구사항 |
|----|---------|
| F7.1 | 데스크톱(≥1024px): AI 대화 패널 + DSL 편집기 나란히 표시 |
| F7.2 | 모바일(<1024px): [대화] [편집기] 탭 전환, 각각 전체 화면 |
| F7.3 | 종목 페이지에서 동일 컴포넌트를 모달로 표시 |
| F7.4 | 새 전략 생성 시: 스트리밍과 함께 편집기에 실시간 타이핑 |
| F7.5 | 기존 전략 수정 시: 디프 하이라이트 (추가=초록, 삭제=빨강) + [적용] 버튼 |
| F7.6 | 크레딧 바를 대화 패널 하단에 상시 표시 |
| F7.7 | 전략 상태 요약을 표시한다 (preset-expansion spec Unit 3에서 구현) |

### 2.2 비기능 요구사항

| ID | 요구사항 |
|----|---------|
| NF1 | SSE 스트리밍 첫 토큰 응답 시간 ≤ 3초 (Sonnet 기준) |
| NF2 | 시스템 프롬프트는 서버에서 관리. 프론트에 노출하지 않는다 |
| NF3 | 시스템 프롬프트 변경은 서버 배포만으로 반영 (프론트 빌드 불필요) |
| NF4 | BYO API Key는 AES-256 또는 Fernet으로 암호화 저장 |
| NF5 | AI 응답에서 "매수하세요" 같은 직접 투자 조언을 하지 않도록 프롬프트에 명시 |
| NF6 | 동시 요청 차단: 사용자당 1개 AI 요청만 처리 (중복 전송 방지) |
| NF7 | Claude API 타임아웃 30초. 초과 시 에러 반환 |

---

## 3. 범위

### 포함

- 전략 빌더 코파일럿 (생성/수정/설명)
- 기본 비서 (Haiku, 무료)
- 토큰 크레딧제 + BYO API Key
- SSE 스트리밍 + extended thinking 토글
- 대화 히스토리 DB 저장 (멀티 디바이스)
- 전략 버전 스냅샷 + 디프 + 되돌리기
- 코드 인텔리전스 (하이라이팅, 에러 표시, 자동완성)
- 반응형 레이아웃 (데스크톱 분할 / 모바일 탭)

### 미포함

- 프리미엄 비서 (사용자 키, 개인화, 사이트 조작) → 별도 spec
- 대화 요약 자동 생성 (토큰 초과 시) → 2차
- thinking 자동 판단 (요청 복잡도 기반) → 3차
- 다른 종목 데이터 참조 (`종목()` 함수) → 별도
- AI 자율 전략 탐색 → 아이디어 단계

---

## 4. 수용 기준

### Unit 1 — 전략 빌더

- [ ] "골든크로스 매수, 3% 손절 전략 만들어줘" → 유효한 v2 DSL 생성
- [ ] "트레일링 추가해줘" → 기존 DSL에 고점 대비 조건 추가
- [ ] "이 전략 설명해줘" → DSL 로직을 자연어로 설명
- [ ] parse_v2 검증 실패 시 자동 재시도 후 유효한 DSL 반환
- [ ] SSE 스트리밍으로 응답 수신 (단계 표시 → 텍스트 → DSL)
- [ ] thinking ON 시 사고 과정 접기/펴기 동작

### Unit 2 — 기본 비서

- [ ] "전략 어떻게 만들어요?" → Haiku가 가이드 응답
- [ ] "RSI가 뭐예요?" → 지표 설명 응답
- [ ] 크레딧 차감 없음 확인

### Unit 3 — 크레딧제

- [ ] 전략 빌더 사용 시 토큰 차감 확인
- [ ] 크레딧 바에 잔량 % + 예상 횟수 표시
- [ ] 일일 한도 초과 시 429 에러 + "크레딧 소진" 메시지
- [ ] BYO Key 등록 → 크레딧 무제한 확인
- [ ] 재시도 토큰은 차감되지 않음 확인

### Unit 4 — 대화 히스토리

- [ ] 대화 저장 후 다른 기기에서 동일 대화 조회
- [ ] 전략 저장 시 대화에 strategy_id 연결
- [ ] 전체 대화 스크롤 표시
- [ ] 대화 삭제 가능

### Unit 5 — 버전 스냅샷

- [ ] AI 수정 시 자동 스냅샷 생성
- [ ] 버전 목록 표시 (버전 번호, 변경 요약, 시간)
- [ ] 두 버전 디프 비교
- [ ] 되돌리기로 이전 DSL 복원

### Unit 6 — 코드 인텔리전스

- [ ] DSL 키워드/함수/상수에 색상 적용
- [ ] 문법 에러 위치에 빨간 밑줄
- [ ] "MA" 입력 시 [MA, MACD, MACD_SIGNAL, MACD_HIST] 드롭다운

### Unit 7 — UI 레이아웃

- [ ] 데스크톱: 대화 + 편집기 나란히
- [ ] 모바일: 탭 전환
- [ ] 새 전략: 편집기에 실시간 타이핑
- [ ] 기존 수정: 디프 하이라이트 + [적용] 버튼
- [ ] SSE 에러 이벤트 시 사용자 친화적 메시지 표시
- [ ] 전략 상태 요약 표시 (preset-expansion spec에서 구현)

---

## 5. API 변경

### 5.1 신규 엔드포인트

| 메서드 | 경로 | 설명 | 인증 |
|--------|------|------|------|
| POST | `/api/v1/ai/chat` | AI 대화 (SSE 응답) | JWT |
| GET | `/api/v1/ai/conversations` | 대화 목록 | JWT |
| GET | `/api/v1/ai/conversations/{id}` | 대화 히스토리 | JWT |
| DELETE | `/api/v1/ai/conversations/{id}` | 대화 삭제 | JWT |
| GET | `/api/v1/ai/credit` | 크레딧 잔량 | JWT |
| GET | `/api/v1/ai/builtins` | DSL 필드/함수 목록 | 공개 |
| POST | `/api/v1/ai/apikey` | BYO API Key 등록 | JWT |
| DELETE | `/api/v1/ai/apikey` | BYO API Key 삭제 | JWT |
| GET | `/api/v1/rules/{id}/versions` | 전략 버전 목록 | JWT |
| GET | `/api/v1/rules/{id}/versions/{v1}/diff/{v2}` | 두 버전 디프 | JWT |
| POST | `/api/v1/rules/{id}/versions/{v}/restore` | 버전 되돌리기 | JWT |

### 5.2 POST /api/v1/ai/chat — 상세

**요청:**
```json
{
  "conversation_id": "uuid | null",
  "message": "골든크로스 매수 전략 만들어줘",
  "current_dsl": "기존 DSL 코드 | null",
  "mode": "builder | assistant",
  "thinking": true
}
```

**SSE 응답 이벤트:**
```
event: status
data: {"step": "analyzing", "message": "전략 분석 중..."}

event: status
data: {"step": "generating", "message": "DSL 생성 중..."}

event: thinking
data: {"content": "골든크로스를 사용하려면 MA(20)과 MA(60)이..."}

event: token
data: {"content": "골든크로스"}

event: token
data: {"content": " + 3% 손절 전략을"}

event: status
data: {"step": "validating", "message": "문법 검증 중..."}

event: status
data: {"step": "retrying", "message": "재시도 1/3..."}

event: dsl
data: {"script": "RSI(14) < 30 AND ...", "valid": true}

event: error
data: {"code": "credit_exhausted", "message": "일일 크레딧이 소진되었습니다"}

event: error
data: {"code": "timeout", "message": "응답 시간이 초과되었습니다"}

event: error
data: {"code": "api_error", "message": "AI 서비스에 일시적 오류가 발생했습니다"}

event: done
data: {"conversation_id": "uuid", "credit_remaining": 78, "credit_estimate": "약 12회", "tokens_used": 1523}
```

### 5.3 GET /api/v1/ai/credit

**응답:**
```json
{
  "success": true,
  "data": {
    "tokens_used": 11000,
    "tokens_limit": 50000,
    "remaining_percent": 78,
    "estimate_turns": 12,
    "resets_at": "2026-03-30T00:00:00+09:00",
    "has_byo_key": false
  }
}
```

### 5.4 GET /api/v1/ai/builtins

**응답:**
```json
{
  "success": true,
  "data": {
    "fields": [
      {"name": "현재가", "description": "현재 가격", "type": "number"},
      {"name": "거래량", "description": "현재 봉 거래량", "type": "number"},
      {"name": "RSI", "description": "상대강도지수", "type": "function", "args": "(기간)"}
    ],
    "keywords": ["매수", "매도", "전량", "나머지", "AND", "OR", "NOT", "BETWEEN"],
    "operators": ["→", "->", ">", "<", ">=", "<=", "==", "!=", "+", "-", "*", "/", "%"]
  }
}
```

---

## 6. DB 스키마 변경

### 6.1 신규 테이블

```sql
-- 대화 히스토리
CREATE TABLE ai_conversations (
    id VARCHAR(36) PRIMARY KEY,          -- UUID
    user_id VARCHAR(36) NOT NULL REFERENCES users(id),
    strategy_id INTEGER REFERENCES trading_rules(id) ON DELETE SET NULL,
    title VARCHAR(200),                  -- 대화 제목 (첫 메시지 기반)
    messages JSON NOT NULL DEFAULT '[]', -- [{role, content, timestamp, tokens?}]
    current_dsl TEXT,
    mode VARCHAR(20) NOT NULL DEFAULT 'builder',  -- builder | assistant
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);

-- 크레딧 추적
CREATE TABLE ai_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id),
    date DATE NOT NULL,                  -- 일별
    tokens_used INTEGER NOT NULL DEFAULT 0,
    tokens_limit INTEGER NOT NULL,       -- 해당 일자 한도 (스냅샷)
    updated_at TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE(user_id, date)
);

-- BYO API Key
CREATE TABLE ai_api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id VARCHAR(36) NOT NULL UNIQUE REFERENCES users(id),
    encrypted_key TEXT NOT NULL,          -- AES-256 / Fernet 암호화
    created_at TIMESTAMP NOT NULL DEFAULT now()
);

-- 전략 버전 스냅샷
CREATE TABLE strategy_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id INTEGER NOT NULL REFERENCES trading_rules(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    script TEXT NOT NULL,
    message VARCHAR(500),                -- 변경 요약
    created_by VARCHAR(20) DEFAULT 'user', -- user | ai
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    UNIQUE(rule_id, version)
);
```

### 6.2 기존 테이블 변경

없음. `trading_rules` 테이블은 변경하지 않는다 (버전은 별도 테이블로 관리).

---

## 7. 정확도 전략

### 7.1 시스템 프롬프트 구성 (~3K 토큰)

| 섹션 | 내용 | 토큰 (추정) |
|------|------|-----------|
| 역할 정의 | "당신은 StockVision DSL 전문가입니다" + 투자조언 금지 | ~200 |
| 문법 요약 | v2 DSL 핵심 문법 (상수, 규칙, 연산자, 우선순위) | ~800 |
| 필드/함수 목록 | builtins.py 전체 (이름 + 시그니처 + 한줄 설명) | ~600 |
| few-shot 예시 | 프리셋 3~4개 (다양한 유형) | ~1000 |
| 제약사항 | DSL 외 코드 금지, 없는 함수 사용 금지, 손절 포함 권장 | ~200 |
| 출력 형식 | DSL 코드는 ```dsl 블록으로, 설명은 자연어로 | ~100 |

### 7.2 검증 루프

```
1. AI 응답에서 ```dsl 블록 추출
2. parse_v2(dsl) 실행
3. 성공 → DSL 반환
4. 실패 → AI에 에러 메시지 전달 + "이 에러를 수정해주세요" → 재시도
5. 3회 실패 → 마지막 DSL + 에러 메시지를 프론트에 반환
```

### 7.3 LLM 전송 윈도우

```
messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": f"현재 DSL:\n{current_dsl}"},
    ...최근 N턴 (토큰 합산 4K 이하),
    {"role": "user", "content": new_message}
]
```

- 현재 DSL이 이전 대화의 결과물이므로 오래된 턴 제거해도 맥락 유지
- N턴 결정: 최신부터 역순으로 추가하되 토큰 합산이 4K 초과 시 중단

---

## 8. 환경변수

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `ANTHROPIC_API_KEY` | 운영자 API 키 (기존) | 필수 |
| `CLAUDE_MODEL` | 전략 빌더 모델 (기존) | `claude-sonnet-4-20250514` |
| `CLAUDE_MODEL_ASSISTANT` | 기본 비서 모델 | `claude-haiku-4-5-20251001` |
| `AI_DAILY_TOKEN_LIMIT` | 일일 토큰 한도 | `50000` |
| `AI_ENCRYPTION_KEY` | BYO Key 암호화 키 (Fernet) | 필수 (운영) |
| `AI_MAX_RETRIES` | DSL 검증 실패 시 최대 재시도 | `3` |
| `AI_WINDOW_MAX_TOKENS` | LLM 전송 윈도우 토큰 상한 | `4000` |

---

## 9. 참고 — 기존 코드 경로

| 영역 | 경로 | 참고 |
|------|------|------|
| Claude API 패턴 | `cloud_server/services/ai_service.py` | `_call_claude()` 패턴 재사용 |
| 레이트 리밋 | `cloud_server/core/rate_limit.py` | `RateLimiter` 클래스 확장 |
| AI 라우터 | `cloud_server/api/ai.py` | 엔드포인트 추가 |
| Rules 라우터 | `cloud_server/api/rules.py` | 버전 엔드포인트 추가 |
| ORM 모델 | `cloud_server/models/` | 신규 모델 추가 |
| DSL 파서 | `sv_core/parsing/parser.py` | `parse_v2()` 검증용 |
| 내장 목록 | `sv_core/parsing/builtins.py` | 자동완성 데이터 소스 |
| 프리셋 | `frontend/src/data/strategyPresets.ts` | few-shot 예시 소스 |
| 전략 빌더 | `frontend/src/pages/StrategyBuilder.tsx` | UI 확장 대상 |
| API 클라이언트 | `frontend/src/services/` | SSE 클라이언트 추가 |
| 설정 | `cloud_server/core/config.py` | 환경변수 추가 |
| brainstorming 설계 | `docs/superpowers/specs/2026-03-29-ai-core-service-design.md` | 설계 배경 |
