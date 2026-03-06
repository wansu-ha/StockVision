# 규칙 데이터 모델 명세서 (rule-model)

> 작성일: 2026-03-06 | 갱신: 2026-03-07 | 상태: v2 (DSL 기반 재작성)
>
> **의존**: `spec/strategy-engine/spec.md` (엔진이 규칙을 소비), `spec/cloud-server/spec.md` (규칙 CRUD/저장)
>
> **근거**: `docs/research/rule-dsl-design.md` (DSL 설계 리서치, GPT/Gemini/Claude 리뷰 반영)

---

## 1. 목표

전략 엔진이 평가하는 **규칙(Rule)의 데이터 모델**을 정의한다.

**분리 사유**: 규칙 모델은 클라우드(저장/CRUD)와 로컬(평가/실행) 양쪽에 걸쳐 있어,
별도 spec으로 분리하여 양쪽이 동일한 모델을 참조하도록 한다.

### v1 → v2 변경 요약

| 항목 | v1 (폐기) | v2 (현행) |
|------|----------|----------|
| 조건 표현 | `buy_conditions`/`sell_conditions` JSON 배열 | `script` 단일 필드 (DSL 텍스트) |
| 조건 구조 | `{type, field, op, value}` 객체 | DSL 파서가 AST로 변환 |
| 논리 조합 | `operator: "AND"` 단일 레벨 | `AND`, `OR`, `NOT`, 괄호 자유 중첩 |
| 교차 돌파 | `cross_above`/`cross_below` 연산자 | `상향돌파(A,B)`/`하향돌파(A,B)` 함수 |
| 커스텀 수식 | v2 확장 예정 | v1부터 커스텀 함수 지원 |
| 매도 조건 | 선택 (없으면 수동 매도) | **필수** (엔진 레벨 보호 포함) |

---

## 2. DSL 개요

> 정형 문법(EBNF): `spec/rule-model/grammar.md` 참조. 파서 구현은 해당 문법을 따른다.
>
> 설계 배경/의미론: `docs/research/rule-dsl-design.md` 참조. 여기서는 데이터 모델에 필요한 핵심만 요약.

### 2.1 핵심 원칙

- 모든 식별자는 현재 시세 컨텍스트에서 평가되는 **읽기 전용 값 또는 함수**
- 상태 변경 없음, 사이드이펙트 없음, 참조 투명성
- 타입: **숫자**와 **boolean** 2종. 암묵적 변환 금지
- 없는 것: if/else, 루프, 배열, 문자열, 가변 변수, import

### 2.2 DSL 구성 요소

| 구분 | 표기 | 예시 |
|------|------|------|
| 내장 필드 | 괄호 없음 | `현재가`, `거래량`, `수익률`, `보유수량` |
| 내장 함수 | 괄호 필수 | `RSI(14)`, `MA(20)`, `상향돌파(A, B)` |
| 내장 패턴 함수 | 괄호 필수, 인자 없음 | `골든크로스()`, `데드크로스()` (§3 참조) |
| 커스텀 함수 | 인자 없는 상수 함수 | `과매도() = RSI(14) <= 30` |
| 엔트리포인트 | `매수:` / `매도:` | `매수: 골든크로스() AND 과매도()` |
| 주석 | `--` | `-- 한 줄 주석` |

### 2.3 스크립트 예시

```
-- 골든크로스 + 과매도 진입, RSI 과매수 또는 목표수익 시 청산
과매도() = RSI(14) <= 30
거래량확인() = 거래량 > 평균거래량(20) * 2

매수: 골든크로스() AND 과매도() AND 거래량확인()
매도: RSI(14) >= 70 OR 수익률 >= 3 OR 수익률 <= -5
```

---

## 3. 내장 패턴 함수

공개된 기술적 지표 패턴을 편의 함수로 제공. 사용자가 직접 정의할 필요 없음.

| 함수 | 정의 | 설명 |
|------|------|------|
| `골든크로스()` | `상향돌파(MA(5), MA(20))` | 5일선이 20일선 상향 교차 |
| `데드크로스()` | `하향돌파(MA(5), MA(20))` | 5일선이 20일선 하향 교차 |
| `RSI과매도()` | `RSI(14) <= 30` | RSI 14일 기준 30 이하 |
| `RSI과매수()` | `RSI(14) >= 70` | RSI 14일 기준 70 이상 |
| `볼린저하단돌파()` | `현재가 <= 볼린저_하단(20)` | 볼린저밴드 하단 이탈 |
| `볼린저상단돌파()` | `현재가 >= 볼린저_상단(20)` | 볼린저밴드 상단 이탈 |
| `MACD골든크로스()` | `상향돌파(MACD(), MACD_SIGNAL())` | MACD 라인이 시그널 상향 교차 |
| `MACD데드크로스()` | `하향돌파(MACD(), MACD_SIGNAL())` | MACD 라인이 시그널 하향 교차 |

> **법적 근거**: 교과서/HTS에 공개된 수학 공식의 편의 포장. 종목/시기/수량 판단이 아님.
> **네이밍 규칙**: 패턴 이름은 업계 관행을 따름. `매수추천()` 같은 행동 유도형 이름은 사용 금지.
> **커스텀과 충돌 시**: 사용자가 같은 이름으로 커스텀 함수를 선언하면 커스텀이 우선 (오버라이드).

---

## 4. 규칙 모델

### 4.1 규칙 구조

```
TradingRule
├── id, name, symbol, is_active
├── script             # DSL 텍스트 (매수/매도 조건 + 커스텀 함수)
├── execution          # 주문 설정 (DSL 밖)
├── trigger_policy     # 트리거 정책 (DSL 밖)
└── priority           # 평가 순서 (높을수록 먼저)
```

**매수/매도:**
- `script` 안에 `매수:`, `매도:` 키워드로 정의
- **둘 다 필수** — 매도 없는 자동매매는 위험
- 엔진이 매도 주문 실행 전 `보유수량 > 0` 암묵적 확인 (실행 정책)

### 4.2 주문 설정 (execution)

```json
{
  "order_type": "MARKET",
  "qty_type": "FIXED",
  "qty_value": 10,
  "limit_price": null
}
```

| 필드 | 값 | 설명 |
|------|----|------|
| `order_type` | `MARKET`, `LIMIT` | 시장가/지정가 |
| `qty_type` | `FIXED` | 고정 수량 (v1) |
| `qty_value` | 정수 | 주문 수량 |
| `limit_price` | 숫자 or null | 지정가 주문 시 가격 |

### 4.3 트리거 정책 (trigger_policy)

```json
{
  "frequency": "ONCE_PER_DAY",
  "cooldown_minutes": null
}
```

| frequency | 설명 |
|-----------|------|
| `ONCE_PER_DAY` | 하루 1회 (v1 기본) |
| `ONCE` | 1회 실행 후 규칙 비활성화 |

### 4.4 전체 JSON 예시

```json
{
  "id": 1,
  "name": "삼성전자 RSI 역행",
  "symbol": "005930",
  "is_active": true,
  "priority": 10,
  "script": "과매도() = RSI(14) <= 30\n거래량확인() = 거래량 > 평균거래량(20) * 2\n\n매수: 골든크로스() AND 과매도() AND 거래량확인()\n매도: RSI과매수() OR 수익률 >= 3 OR 수익률 <= -5",
  "execution": {
    "order_type": "MARKET",
    "qty_type": "FIXED",
    "qty_value": 10,
    "limit_price": null
  },
  "trigger_policy": {
    "frequency": "ONCE_PER_DAY",
    "cooldown_minutes": null
  }
}
```

---

## 5. 클라우드 DB 모델

```python
class TradingRule(Base):
    __tablename__ = "trading_rules"

    id = Column(Integer, primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    symbol = Column(String(10), nullable=False)

    # DSL 스크립트 (하위 호환: 기존 규칙은 null 가능)
    script = Column(Text, nullable=True)

    # 하위 호환 (마이그레이션 완료 후 제거)
    buy_conditions = Column(JSON, nullable=True)
    sell_conditions = Column(JSON, nullable=True)

    # 주문 설정 (JSON)
    execution = Column(JSON, nullable=False)

    # 트리거 정책 (JSON)
    trigger_policy = Column(JSON, nullable=False, default={"frequency": "ONCE_PER_DAY"})

    # 메타
    priority = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
```

> `cloud-server/spec.md` §5.2의 `TradingRule`을 대체한다.
> 기존 `max_position_count`, `budget_ratio`는 사용자 전역 설정으로 이동 (§8).

### 5.1 하위 호환

- **우선순위**: `script`가 non-null이면 DSL로 평가. `script`가 null이면 `buy_conditions`/`sell_conditions` JSON으로 평가. 둘 다 없으면 규칙 스킵
- 폼 UI는 항상 DSL로 저장 (내부적으로)
- 마이그레이션: 기존 JSON 조건 → DSL 텍스트 변환 스크립트 제공

### 5.2 클라우드 DSL 검증

클라우드 서버는 규칙 저장(POST/PUT) 시 `script` 필드를 **파싱 검증**한다:

- 문법 에러 → 400 응답 + 에러 위치/메시지 반환
- 타입 에러 → 400 응답 + 에러 상세
- `매수:`/`매도:` 누락 → 400 응답
- 검증 통과 → 저장

> **이유**: 잘못된 DSL이 저장되면 로컬 엔진에서 매 평가마다 파싱 에러 발생.
> 클라우드에 경량 파서(검증 전용, 평가 불필요)를 두어 저장 시점에 차단.

---

## 6. 로컬 엔진 모델

```python
@dataclass
class RuleConfig:
    """규칙 JSON → 파싱 구조체."""

    id: int
    name: str
    symbol: str
    is_active: bool = True
    priority: int = 0

    # DSL 스크립트 (None이면 하위 호환 모드)
    script: str | None = None

    # 하위 호환
    buy_conditions: dict | None = None
    sell_conditions: dict | None = None

    execution: dict = field(default_factory=lambda: {
        "order_type": "MARKET", "qty_type": "FIXED", "qty_value": 1
    })
    trigger_policy: dict = field(default_factory=lambda: {
        "frequency": "ONCE_PER_DAY"
    })
```

> `local_server/engine/models.py`의 기존 `RuleConfig`를 대체한다.

---

## 7. 엔진 평가 로직

### 7.1 평가 흐름

```
매 1분:
  for rule in rules (priority 내림차순):
    if rule.script is not None:       # script 우선 (§5.1)
      → DSL 파서로 AST 변환 (캐시)
      → 매수 조건 평가: AST의 매수: 블록 실행
      → 매도 조건 평가: AST의 매도: 블록 실행
    elif rule.buy_conditions or rule.sell_conditions:
      → 기존 JSON 평가 (하위 호환)
    else:
      → 스킵

    매수 조건 true AND 미보유 → 매수 주문
    매도 조건 true AND 보유 중 → 매도 주문
```

### 7.2 null 전파 (결측치/런타임 에러)

- 평가 트리 어디서든 `null` 발생 → 해당 `매수:`/`매도:` 조건 **전체 미충족(false)**
- `NOT` 반전으로 true 되는 버그 방지
- 봇은 중지하지 않음 — 해당 평가 주기만 스킵, 로그 기록

### 7.3 매도 보호

- 엔진이 매도 주문 실행 전 `보유수량 > 0` 암묵적 확인
- DSL에 명시할 필요 없음 — 실행 정책이지 조건식이 아님

### 7.4 AST 캐시

- `script` 텍스트가 변경되지 않으면 파싱 결과(AST)를 캐시
- 규칙 업데이트(rules_version 변경) 시 캐시 무효화

---

## 8. 사용자 전역 설정 (규칙 밖)

규칙 단위가 아닌 사용자 단위 설정:

| 설정 | 기본값 | 설명 |
|------|--------|------|
| `max_position_count` | 5 | 동시 보유 최대 종목 수 |
| `budget_ratio` | 0.2 | 1회 주문 최대 예산 비율 |
| `daily_loss_limit` | 사용자 정의 | 당일 최대 손실 (원) |
| `order_rate_limit` | 10 | 분당 최대 주문 수 |

> 이 설정들은 `~/.stockvision/config.json`에 저장하며,
> 클라우드에도 동기화한다 (사용자 설정 sync).

---

## 9. v2 확장 계획

| 항목 | 설명 |
|------|------|
| `qty_type: "RATIO"` | 예산 비율 기반 수량 계산 (잔고 조회 필요) |
| `qty_type: "AMOUNT"` | 금액 기반 수량 계산 |
| `frequency: "COOLDOWN"` | N분 쿨다운 후 재실행 |
| `frequency: "UNLIMITED"` | 조건 충족 시 매번 실행 |
| 분봉 지표 | DSL 문법 확장 (timeframe 지정) |
| 봉 마감 기준 평가 | repainting 대응 옵션 |
| 커스텀 함수 인자 | `골든크로스(단기, 장기)` — 숫자 리터럴만 허용 |
| DSL 에디터 | CodeMirror 기반 고급 모드 (폼 ↔ DSL 전환) |
| 전략 템플릿 | 완성된 DSL 스크립트 갤러리 (어드민 관리, 기존 templates API 활용) |
| 규칙 체이닝 | 규칙 A 체결 → 규칙 B 활성화 |
| 시간 조건 | 특정 시간대만 활성화 (e.g., 09:30~10:00) |
| 알림 전용 모드 | 매매 없이 푸시 알림만. 문법 유지, `매도: false` 시스템 자동 삽입 |

---

## 10. 수용 기준

### 10.1 데이터 모델

- [ ] DSL `script` 필드로 규칙 생성/저장/조회
- [ ] 잘못된 DSL 저장 시 400 에러 + 에러 위치/메시지 반환 (§5.2)
- [ ] 내장 패턴 함수 (`골든크로스()` 등) 사용 가능
- [ ] 커스텀 함수 선언 + 참조 동작
- [ ] `execution`, `trigger_policy` JSON 필드 저장/조회
- [ ] 하위 호환: `script` null인 규칙도 JSON 방식으로 평가 가능

### 10.2 DSL 파서

- [ ] 내장 필드/함수 인식
- [ ] 내장 패턴 함수 인식 (§3)
- [ ] 연산자 우선순위 준수 (DSL 리서치 §3.3)
- [ ] 타입 체크 (숫자/boolean, 암묵적 변환 금지)
- [ ] 커스텀 함수 선언/참조 (후방 참조 금지, 재귀 금지)
- [ ] `매수:`/`매도:` 둘 다 필수, 각 1회, boolean만
- [ ] null 전파: 전체 블록 실패 (§7.2)
- [ ] 한국어 에러 메시지 (위치 표시)

### 10.3 엔진 평가

- [ ] 매수 조건 충족 + 미보유 → 매수 주문
- [ ] 매도 조건 충족 + 보유 중 → 매도 주문
- [ ] 보유 중 매수 조건 충족 → 스킵 (중복 매수 방지)
- [ ] 미보유 매도 조건 충족 → 스킵 (§7.3 매도 보호)
- [ ] `ONCE` 트리거 → 1회 실행 후 `is_active=false`
- [ ] AST 캐시 동작 (§7.4)

### 10.4 호환성

- [ ] 클라우드 DB 모델과 로컬 JSON 캐시 스키마 일치
- [ ] 기존 JSON 조건 → DSL 마이그레이션 스크립트

---

## 11. 범위

### 포함

- 규칙 JSON 스키마 정의 (script 기반)
- 내장 패턴 함수 목록 및 정의
- 클라우드 DB 모델 (TradingRule)
- 로컬 엔진 모델 (RuleConfig)
- 엔진 평가 흐름 (DSL 파서 + 하위 호환)
- null 전파/매도 보호 정책
- 주문 설정/트리거 정책 정의

### 미포함

- DSL 문법 상세/의미론 → `docs/research/rule-dsl-design.md`
- 프론트엔드 규칙 빌더 UI → `spec/frontend/spec.md` (Unit 5)
- DSL 에디터 (v2) → `docs/research/rule-dsl-design.md` §7
- LLM 연동 → `docs/research/rule-dsl-design.md` §10
- 전략 템플릿 갤러리 (v2) → 기존 templates API 확장
- 백테스팅 (v2)
- 커뮤니티 규칙 공유 (v2)

---

## 참고

- `docs/research/rule-dsl-design.md` (DSL 설계 리서치 — 문법, 의미론, LLM, 에디터)
- `docs/research/trading-platform-benchmark.md` (트레이딩 플랫폼 벤치마크)
- `spec/strategy-engine/spec.md` §4.2 (조건 평가)
- `spec/cloud-server/spec.md` §5 (규칙 API)
- `docs/architecture.md` §4.4 (로컬 서버)

---

**마지막 갱신**: 2026-03-07
