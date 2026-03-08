# Custom LLM 통합 자동매매 시스템 — 기능 명세서

## 목표

StockVision에 **사용자 소유 LLM을 연동한 자동매매 파이프라인**을 구축한다.

핵심 설계 원칙: **"최대한의 편의를 제공하되, 투자 판단은 사용자에게 미룬다."**

```
우리가 제공하는 것 (편의)          사용자가 하는 것 (판단)
─────────────────────────         ─────────────────────────
데이터 수집 & 포맷팅                LLM 선택 & API 키 입력
기술적 지표 자동 계산               전략 프롬프트 작성
프롬프트 템플릿 구조 (빈 틀)        매매 규칙 & 조건 설정
LLM 응답 파싱 & 검증               실행 여부 최종 결정
주문 실행 래퍼                     증권사 계좌 연동
안전장치 프레임워크                 안전장치 임계값 설정
백테스팅 엔진                      전략 평가 & 조정
모니터링 대시보드                   모니터링 & 개입
```

기존 Phase 2의 스코어링 엔진(규칙 기반)과 **병렬 옵션**으로 존재한다.
사용자는 기존 스코어링 전략 또는 LLM 기반 전략을 선택할 수 있다.

## 아키텍처

```
[1. 데이터 레이어]     yfinance(과거) + 키움 REST API(실시간) + 기술적 지표
        ↓
        ↓  자동 포맷팅 (컨텍스트 빌더)
        ↓
[2. LLM 레이어]       사용자 LLM ← 사용자 프롬프트 + 포맷된 데이터
        ↓
        ↓  응답 파싱 & 검증
        ↓
[3. 안전장치 레이어]   손실 한도 / 포지션 한도 / 쿨다운 / 킬 스위치
        ↓
[4. 실행 레이어]       주문 실행 (드라이런 or 실매매)
        ↓
[5. 모니터링 레이어]   로그 / 대시보드 / 알림
```

## 요구사항

### 기능적 요구사항

#### FR-1: LLM 프로바이더 관리

사용자가 다양한 LLM을 연결할 수 있는 통합 인터페이스.

- FR-1.1: LLM 프로바이더 등록 (이름, API 키, 엔드포인트 URL, 모델명)
- FR-1.2: 지원 프로바이더 프리셋 — OpenAI, Anthropic, 로컬(Ollama) 선택 시 엔드포인트 자동 채움
- FR-1.3: 커스텀 프로바이더 등록 — OpenAI 호환 API 엔드포인트 직접 입력
- FR-1.4: API 키 암호화 저장 (Fernet 대칭 암호화, 마스터 키는 환경변수)
- FR-1.5: 연결 테스트 — 등록 시 간단한 ping 요청으로 연결 확인
- FR-1.6: 프로바이더 활성화/비활성화/삭제

#### FR-2: 컨텍스트 빌더 (데이터 → 프롬프트 입력)

LLM에게 보낼 시장 데이터를 자동으로 수집·포맷하는 엔진.
**우리는 "무엇을 보여줄지"만 결정하고, "어떻게 해석할지"는 프롬프트(사용자)가 결정한다.**

- FR-2.1: 종목별 컨텍스트 자동 생성
  - 최근 N일 OHLCV 데이터
  - 기술적 지표 (RSI, MACD, 볼린저밴드, EMA)
  - 기존 스코어링 엔진 점수 (참고용)
  - 현재 포지션 정보 (보유 여부, 평균가, 손익)
- FR-2.2: 포트폴리오 컨텍스트 자동 생성
  - 계좌 잔고, 총 자산, 수익률
  - 전체 보유 종목 리스트 & 비중
  - 오늘의 실현/미실현 손익
- FR-2.3: 컨텍스트 항목 선택 — 사용자가 어떤 데이터를 포함할지 체크박스로 선택
- FR-2.4: 출력 포맷 선택 — JSON / Markdown / Plain Text

#### FR-3: 프롬프트 템플릿 시스템

사용자가 전략 프롬프트를 쉽게 작성할 수 있도록 **구조만 제공**한다.
**판단 로직(매수/매도 기준)은 절대 우리가 채우지 않는다.**

- FR-3.1: 프롬프트 템플릿 CRUD
  - 이름, 시스템 프롬프트, 유저 프롬프트, 변수 목록
- FR-3.2: 템플릿 변수 바인딩
  - `{{ticker}}`, `{{prices}}`, `{{indicators}}`, `{{portfolio}}` 등
  - 컨텍스트 빌더 출력이 자동으로 변수에 바인딩
- FR-3.3: 응답 포맷 스키마 정의
  - 사용자가 LLM 응답의 JSON 스키마를 정의
  - 기본 제공 스키마 (빈 구조만):
    ```json
    {
      "decisions": [
        {
          "ticker": "string",
          "action": "buy | sell | hold",
          "quantity": "number (optional)",
          "confidence": "number 0-1 (optional)",
          "reasoning": "string (optional)"
        }
      ]
    }
    ```
  - 사용자는 이 스키마를 수정하거나 완전히 새로 정의 가능
- FR-3.4: 프롬프트 버전 관리 — 수정 시 이전 버전 보존, 백테스트 결과와 연결
- FR-3.5: 프롬프트 테스트 — 실제 데이터로 LLM 호출 후 응답 미리보기 (주문 실행 없이)

#### FR-4: LLM 응답 파싱 & 검증

LLM 응답을 안전하게 파싱하여 실행 가능한 주문으로 변환한다.

- FR-4.1: JSON 파싱 — LLM 응답에서 JSON 블록 추출 (markdown 코드블록 내부 포함)
- FR-4.2: 스키마 검증 — 사용자 정의 스키마에 맞는지 검증
- FR-4.3: 액션 정규화 — `"action": "매수"` → `BUY`, 대소문자/한영 변환
- FR-4.4: 수량 검증 — 잔고 초과, 미보유 매도 등 불가능한 주문 필터링
- FR-4.5: 파싱 실패 시 처리 — 재시도 (최대 1회) 또는 해당 사이클 스킵, 로그 기록

#### FR-5: 안전장치 (Safety Guards)

사용자가 임계값을 설정하고, 시스템은 그 범위 내에서만 실행한다.

- FR-5.1: 일일 최대 손실 한도 — 설정 금액 초과 시 당일 자동 중단
- FR-5.2: 주문당 최대 금액 — 단일 주문 금액 상한
- FR-5.3: 최대 포지션 수 — 동시 보유 종목 수 제한
- FR-5.4: 최대 포지션 비율 — 단일 종목이 포트폴리오에서 차지하는 최대 비율
- FR-5.5: 쿨다운 타이머 — 같은 종목 연속 주문 간 최소 간격
- FR-5.6: 킬 스위치 — 즉시 전체 자동매매 중단 (UI 원클릭)
- FR-5.7: 드라이런 모드 — 모든 로직 실행하되 실제 주문은 미전송 (기본값: ON)
- FR-5.8: 안전장치 위반 로그 — 어떤 주문이 왜 차단되었는지 기록

#### FR-6: 자동매매 루프 엔진

기존 `AutoTradeScheduler`를 확장하여 LLM 기반 전략을 지원한다.

- FR-6.1: 전략 유형 확장 — `strategy_type`에 `"llm"` 추가 (기존 `"score_based"` 유지)
- FR-6.2: LLM 실행 사이클
  ```
  스케줄 트리거 → 컨텍스트 빌드 → 프롬프트 조립 → LLM 호출
  → 응답 파싱 → 안전장치 검증 → 주문 실행 (or 드라이런 로그)
  ```
- FR-6.3: 실행 간격 설정 — cron 표현식 또는 분 단위 인터벌
- FR-6.4: 수동 트리거 — "지금 한 번 실행" 버튼
- FR-6.5: 실행 이력 — 각 사이클의 입력(컨텍스트), LLM 응답, 파싱 결과, 최종 주문을 모두 저장

#### FR-7: LLM 전략 백테스팅

기존 BacktestEngine을 확장하여 LLM 프롬프트 전략을 과거 데이터로 검증한다.

- FR-7.1: 과거 데이터로 날짜별 컨텍스트 재생성
- FR-7.2: LLM을 날짜별로 호출하여 매매 결정 수집
- FR-7.3: 기존 백테스트 메트릭 동일 적용 (수익률, 샤프비율, MDD, 승률)
- FR-7.4: 프롬프트 버전별 비교 — 같은 기간, 다른 프롬프트로 성과 비교
- FR-7.5: LLM 호출 비용 추정 — 토큰 사용량 기록 및 예상 비용 표시

#### FR-8: API 엔드포인트

| Method | Path | 설명 |
|--------|------|------|
| POST | `/api/v1/llm/providers` | LLM 프로바이더 등록 |
| GET | `/api/v1/llm/providers` | 프로바이더 목록 조회 |
| PATCH | `/api/v1/llm/providers/{id}` | 프로바이더 수정 |
| DELETE | `/api/v1/llm/providers/{id}` | 프로바이더 삭제 |
| POST | `/api/v1/llm/providers/{id}/test` | 연결 테스트 |
| POST | `/api/v1/llm/templates` | 프롬프트 템플릿 생성 |
| GET | `/api/v1/llm/templates` | 템플릿 목록 조회 |
| GET | `/api/v1/llm/templates/{id}` | 템플릿 상세 (버전 포함) |
| PUT | `/api/v1/llm/templates/{id}` | 템플릿 수정 (새 버전 생성) |
| DELETE | `/api/v1/llm/templates/{id}` | 템플릿 삭제 |
| POST | `/api/v1/llm/templates/{id}/test` | 프롬프트 테스트 (LLM 호출, 주문 없음) |
| POST | `/api/v1/llm/context/preview` | 컨텍스트 빌더 미리보기 |
| GET | `/api/v1/llm/safety` | 현재 안전장치 설정 조회 |
| PUT | `/api/v1/llm/safety` | 안전장치 설정 변경 |
| POST | `/api/v1/llm/safety/kill` | 킬 스위치 (즉시 중단) |
| GET | `/api/v1/llm/executions` | 실행 이력 조회 |
| GET | `/api/v1/llm/executions/{id}` | 실행 상세 (컨텍스트, 응답, 주문) |
| POST | `/api/v1/llm/executions/trigger` | 수동 실행 트리거 |

자동매매 규칙 관련은 기존 `/api/v1/trading/rules` 확장 (`strategy_type: "llm"`)

#### FR-9: 프론트엔드

- FR-9.1: LLM 설정 페이지
  - 프로바이더 관리 (등록/테스트/삭제)
  - 프롬프트 템플릿 에디터 (코드 에디터 스타일, 변수 자동완성)
  - 컨텍스트 항목 선택 체크박스
  - 응답 스키마 에디터
- FR-9.2: 안전장치 설정 패널
  - 각 항목 슬라이더/입력 + 현재 상태 표시
  - 킬 스위치 버튼 (빨간색, 확인 다이얼로그)
  - 드라이런 모드 토글 (기본 ON, 끄면 경고)
- FR-9.3: 실행 모니터링 대시보드
  - 실시간 실행 상태 (마지막 실행 시간, 다음 예정 시간)
  - 최근 LLM 응답 뷰어 (JSON pretty-print)
  - 주문 실행/차단 로그
  - 일일 손익 차트
- FR-9.4: LLM 백테스트 결과 페이지
  - 기존 백테스트 UI 확장
  - 프롬프트 버전별 성과 비교 차트
  - LLM 호출 비용 요약

### 비기능적 요구사항

- NFR-1: LLM 호출 타임아웃 30초, 타임아웃 시 해당 사이클 스킵
- NFR-2: API 키 평문 노출 금지 — 저장 시 암호화, 조회 시 마스킹 (`sk-...xxxx`)
- NFR-3: 드라이런 모드 기본 활성화 — 사용자가 명시적으로 끄기 전까지 실주문 안 됨
- NFR-4: 실행 이력 90일 보존 (이후 자동 정리)
- NFR-5: LLM 호출 실패 시 자동 재시도 최대 1회, 연속 3회 실패 시 규칙 자동 비활성화
- NFR-6: 기존 API 패턴 준수 (`{ success, data, count }` 형식)
- NFR-7: 기존 스코어링 기반 자동매매와 독립적으로 동작 (상호 간섭 없음)

## 수용 기준

- [ ] OpenAI API 키를 등록하고 연결 테스트가 통과한다
- [ ] Anthropic API 키를 등록하고 연결 테스트가 통과한다
- [ ] Ollama 로컬 모델을 등록하고 연결 테스트가 통과한다
- [ ] 프롬프트 템플릿에 `{{ticker}}`, `{{prices}}` 등 변수를 사용하면 실제 데이터로 치환된다
- [ ] 프롬프트 테스트 실행 시 LLM 응답이 정의한 스키마에 맞게 파싱된다
- [ ] 드라이런 모드에서 자동매매 루프가 LLM 호출 → 응답 파싱 → 로그 기록까지 동작한다
- [ ] 드라이런 OFF 시 확인 다이얼로그가 표시되고, 승인 후 실제 주문이 실행된다
- [ ] 안전장치(일일 손실 한도)에 걸리면 주문이 차단되고 사유가 로그에 기록된다
- [ ] 킬 스위치를 누르면 모든 LLM 자동매매 규칙이 즉시 비활성화된다
- [ ] 실행 이력에서 각 사이클의 컨텍스트, LLM 응답, 최종 주문을 확인할 수 있다
- [ ] LLM 백테스트로 과거 기간의 프롬프트 전략 성과를 확인할 수 있다
- [ ] 기존 스코어링 기반 자동매매가 LLM 통합 후에도 정상 동작한다
- [ ] API 키가 암호화 저장되고 API 응답에서 마스킹되어 반환된다
- [ ] 프론트엔드에서 프로바이더 관리, 프롬프트 편집, 안전장치 설정, 모니터링이 가능하다

## 범위

### 포함

- LLM 프로바이더 관리 (OpenAI, Anthropic, Ollama, 커스텀 OpenAI 호환)
- 컨텍스트 빌더 (시장 데이터 자동 포맷팅)
- 프롬프트 템플릿 시스템 (변수 바인딩, 버전 관리)
- LLM 응답 파싱 & 검증
- 안전장치 프레임워크 (손실 한도, 포지션 한도, 킬 스위치, 드라이런)
- 자동매매 루프 엔진 확장 (`strategy_type: "llm"`)
- LLM 전략 백테스팅
- 실행 이력 저장 & 모니터링 대시보드
- 프론트엔드 UI (설정, 모니터링, 백테스트)

### 미포함

- 전략 프롬프트 내용 제공 (투자 판단에 해당, 사용자가 직접 작성)
- LLM 파인튜닝/학습 기능
- 실시간 WebSocket 스트리밍
- 사용자 인증/권한 시스템
- 멀티 사용자 지원
- 프롬프트 마켓플레이스/공유 기능 (향후 고려)
- 텔레그램/슬랙 알림 (별도 feature)

## DB 스키마 변경

### 신규 모델

```python
class LLMProvider(Base):
    """사용자가 등록한 LLM 프로바이더"""
    __tablename__ = "llm_providers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)           # 사용자 지정 이름
    provider_type = Column(String(50), nullable=False)    # openai, anthropic, ollama, custom
    api_key_encrypted = Column(Text)                      # Fernet 암호화된 API 키
    endpoint_url = Column(String(500))                    # API 엔드포인트 URL
    model_name = Column(String(100))                      # 모델명 (gpt-4o, claude-sonnet-4-20250514 등)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PromptTemplate(Base):
    """사용자가 작성한 프롬프트 템플릿"""
    __tablename__ = "prompt_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    version = Column(Integer, default=1)                  # 수정 시 자동 증가
    system_prompt = Column(Text)                          # 시스템 프롬프트
    user_prompt = Column(Text, nullable=False)             # 유저 프롬프트 (변수 포함)
    response_schema = Column(JSON)                        # 기대 응답 JSON 스키마
    context_config = Column(JSON)                         # 컨텍스트 빌더 설정 (어떤 데이터 포함할지)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PromptTemplateVersion(Base):
    """프롬프트 템플릿 버전 이력"""
    __tablename__ = "prompt_template_versions"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("prompt_templates.id"), nullable=False)
    version = Column(Integer, nullable=False)
    system_prompt = Column(Text)
    user_prompt = Column(Text, nullable=False)
    response_schema = Column(JSON)
    context_config = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_template_version', 'template_id', 'version'),
    )


class SafetyConfig(Base):
    """안전장치 설정 (계좌당 하나)"""
    __tablename__ = "safety_configs"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("virtual_accounts.id"), nullable=False, unique=True)
    daily_loss_limit = Column(Float, default=500000.0)    # 일일 최대 손실 (원)
    max_order_amount = Column(Float, default=1000000.0)   # 주문당 최대 금액 (원)
    max_position_count = Column(Integer, default=10)      # 최대 포지션 수
    max_position_ratio = Column(Float, default=0.3)       # 단일 종목 최대 비율 (30%)
    cooldown_minutes = Column(Integer, default=30)        # 같은 종목 재주문 쿨다운 (분)
    dry_run = Column(Boolean, default=True)               # 드라이런 모드 (기본 ON)
    kill_switch = Column(Boolean, default=False)          # 킬 스위치 (True면 전체 중단)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LLMExecution(Base):
    """LLM 자동매매 실행 이력"""
    __tablename__ = "llm_executions"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey("auto_trading_rules.id"), nullable=False)
    provider_id = Column(Integer, ForeignKey("llm_providers.id"), nullable=False)
    template_id = Column(Integer, ForeignKey("prompt_templates.id"), nullable=False)
    template_version = Column(Integer)

    # 입력
    context_data = Column(JSON)                           # LLM에 보낸 컨텍스트
    full_prompt = Column(Text)                            # 조립된 전체 프롬프트

    # LLM 응답
    raw_response = Column(Text)                           # LLM 원본 응답
    parsed_response = Column(JSON)                        # 파싱된 JSON
    parse_success = Column(Boolean, default=False)

    # 실행 결과
    decisions = Column(JSON)                              # 매매 결정 리스트
    orders_executed = Column(JSON)                        # 실제 실행된 주문
    orders_blocked = Column(JSON)                         # 안전장치에 의해 차단된 주문
    is_dry_run = Column(Boolean, default=True)

    # 메타
    token_usage = Column(JSON)                            # {"prompt_tokens": N, "completion_tokens": N}
    execution_time_ms = Column(Integer)                   # LLM 호출 소요 시간
    status = Column(String(20), default="pending")        # pending, success, parse_error, llm_error, safety_blocked
    error_message = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_execution_rule', 'rule_id', 'created_at'),
    )
```

### 기존 모델 확장

```python
# AutoTradingRule에 추가할 필드
class AutoTradingRule:
    # ... 기존 필드 ...
    provider_id = Column(Integer, ForeignKey("llm_providers.id"))     # LLM 프로바이더
    template_id = Column(Integer, ForeignKey("prompt_templates.id"))  # 프롬프트 템플릿
    # strategy_type 기존 값: "score_based" → 새 값 추가: "llm"
```

## "편의 vs 판단" 경계선 상세

이 시스템의 법적·윤리적 안전을 위해 아래 경계를 엄격히 지킨다.

### 우리가 제공하는 것 (도구 = 편의)

| 항목 | 설명 | 예시 |
|------|------|------|
| 데이터 포맷터 | 시장 데이터를 LLM이 읽기 좋은 형태로 변환 | OHLCV → JSON |
| 프롬프트 틀 | 변수 바인딩 구조, 응답 스키마 구조 | `{{ticker}}`, `{{prices}}` |
| 응답 파서 | LLM 출력을 실행 가능한 주문으로 변환 | JSON 추출, 액션 정규화 |
| 주문 래퍼 | 증권사 API 호출 코드 | `place_order(BUY, ...)` |
| 안전장치 | 위험한 주문 차단 프레임워크 | 손실 한도, 킬 스위치 |
| 백테스팅 | 과거 데이터로 전략 검증 도구 | 수익률, 샤프비율 계산 |
| 모니터링 | 실행 로그, 대시보드 | 실행 이력, 차트 |

### 사용자가 하는 것 (판단)

| 항목 | 설명 | 절대 우리가 제공하지 않는 것 |
|------|------|------------------------------|
| LLM 선택 | 어떤 모델을 쓸지 | 모델 추천 |
| 전략 프롬프트 | 매수/매도 판단 기준 | "RSI 30 이하면 매수" 같은 전략 |
| 매매 규칙 | 실행 조건, 간격, 금액 | 기본 전략 프리셋 |
| 안전장치 값 | 한도 금액, 비율 수치 | "500만원이 적당합니다" |
| 실행 결정 | 드라이런 해제, 규칙 활성화 | 자동 실행 |

### 경계선 위의 것들 (주의 필요)

| 항목 | 처리 방식 |
|------|-----------|
| 프롬프트 작성 가이드 | "변수 사용법, 응답 포맷 설명" 수준만 제공 (전략 예시 X) |
| 기본 응답 스키마 | 빈 구조만 제공 (`action`, `ticker` 필드 정의), 판단 로직 없음 |
| 백테스트 결과 해석 | 숫자만 제공 (샤프비율 1.5), "좋다/나쁘다" 평가 안 함 |

## 참고: 기존 코드 경로

| 영역 | 경로 | 활용 방식 |
|------|------|-----------|
| 자동매매 스케줄러 | `backend/app/services/auto_trade_scheduler.py` | `strategy_type: "llm"` 분기 추가 |
| 거래 엔진 | `backend/app/services/trading_engine.py` | 주문 실행 래퍼로 재사용 |
| 스코어링 엔진 | `backend/app/services/scoring_engine.py` | 컨텍스트 빌더에서 참고 데이터로 제공 |
| 기술적 지표 | `backend/app/services/technical_indicators.py` | 컨텍스트 빌더에서 지표 데이터 수집 |
| 백테스트 엔진 | `backend/app/services/backtest_engine.py` | LLM 백테스트용 확장 |
| 주식 데이터 | `backend/app/services/stock_data_service.py` | 컨텍스트 빌더에서 가격 데이터 수집 |
| DB 모델 (자동매매) | `backend/app/models/auto_trading.py` | `provider_id`, `template_id` 필드 추가 |
| 거래 API 라우터 | `backend/app/api/trading.py` | LLM 라우터 별도 생성 (`llm.py`) |
| 프론트 거래 페이지 | `frontend/src/pages/TradingCenter.tsx` | LLM 설정 탭 추가 |
| 프론트 API 클라이언트 | `frontend/src/services/api.ts` | `llmApi` 네임스페이스 추가 |
| 프론트 타입 | `frontend/src/types/` | `llm.ts` 타입 파일 추가 |
