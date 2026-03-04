# 전략 빌더 기능 명세서 (strategy-builder)

> 작성일: 2026-03-04 | 상태: 초안 | 우선순위: Phase 3

## 1. 개요

**전략 빌더**는 StockVision의 핵심 기능으로, 사용자가 코딩 없이 자동매매 규칙을 시각적으로 구성하고 검증할 수 있는 UI 기반 전략 설정 도구다.

### 배경
- 현재(Phase 2): AutoTradingRule을 JSON 파라미터로만 관리 → 사용자 진입장벽 높음
- 필요성: "투자판단 주체 = 사용자"를 기술적으로 보장하려면, 사용자가 직접 규칙을 구성·검증·승인하는 과정이 필수
- 전략 빌더는 이 프로세스의 UI 레이어 역할

### 핵심 가치
1. **Low-code 전략 구성**: 드래그 드롭 또는 폼 기반 조건식 작성
2. **서버 컨텍스트 변수 활용**: 시장 변동성, 섹터 모멘텀 등 실시간 계산 변수를 전략에 주입
3. **백테스팅 통합 검증**: 전략 저장 전 과거 데이터로 성과를 사전 확인
4. **투자판단 추적성**: 규칙 생성~실행 전체 히스토리 유지 (감시 대상 요건)

---

## 2. 목표

### 2.1 기능 목표
- [ ] 사용자가 UI를 통해 매수/매도 조건을 명시적으로 구성할 수 있다
- [ ] 구성된 전략이 컨텍스트 변수를 참조하고 있음을 명확히 표시한다
- [ ] 전략 저장 전 백테스팅으로 성과를 실시간 미리 본다
- [ ] 구성된 전략이 code-free로 자동매매 스케줄러에 바로 반영된다

### 2.2 기술 목표
- 매수/매도 조건을 **조건식 객체** 형태로 직렬화하여 DB 저장
- 조건식 실행기(evaluator)가 컨텍스트 변수 + 종목 지표를 입력받아 True/False 판정
- REST API와 React UI의 느슨한 결합 (백엔드는 UI 구체 사항 모름)

### 2.3 비기능 목표
- 전략 편집 응답 시간 < 500ms (조건 추가/삭제)
- 백테스팅 즉시 실행 < 10초 (UI 잠금 없음)
- 규칙 적용 후 스케줄러 반영 < 1초 (reload_rules 호출)

---

## 3. 사용자 시나리오

### 시나리오 1: 기술적 지표 기반 전략 구성
```
사용자 "김투자자"는 RSI + 거래량 기반 전략을 만들고 싶다.

1. Strategy Builder 페이지 진입 → "New Strategy" 클릭
2. 매수 조건 작성:
   - (RSI(14) < 30) AND (거래량배수 > 2.0)
3. 매도 조건 작성:
   - (수익률 > +5%) OR (손실 < -3%)
4. 전략명: "RSI-Volume Breakout", 계좌 선택, 예산 비율 70% 설정
5. "Quick Backtest" → 최근 3개월 데이터 수행, 결과(승률, 수익률) 표시
6. 만족 → "Save & Activate" → 스케줄러 즉시 적용
```

### 시나리오 2: 시장 상황 기반 동적 전략
```
사용자는 "시장이 안정적일 때만 매수" 전략을 원한다.

1. 매수 조건 추가:
   - (RSI < 30) AND
   - [시장_변동성] < 20  ← 서버 컨텍스트 변수
2. 컨텍스트 변수 항목을 클릭하면 설명 팝업:
   "시장_변동성: 코스피 20일 변동성. 실시간 업데이트"
3. Backtest 실행 → 서버가 과거 각 시점의 시장_변동성 계산 후 조건식 평가
4. 결과 확인 후 저장
```

### 시나리오 3: 규칙 수정 및 버전 관리
```
사용자의 전략이 수익률 5% → 2%로 하락했다.

1. "Edit Strategy" → 기존 조건 표시
2. 매도 조건 수정: +5% → +3%로 변경
3. 변경사항 미리보기 (diff 표시)
4. "Compare with Backtest"로 새 백테스트 실행 후 비교 (수익률 변화 시각화)
5. 만족 시 "Update & Activate" → 기존 규칙 교체 (이력 유지)
```

---

## 4. 전략 구조 정의

### 4.1 조건식 문법 (조건식 DSL)

전략의 매수/매도 조건을 **평가 가능한 조건식 객체**로 표현한다.

```typescript
// 조건식 트리 구조
type ConditionExpr =
  | SimpleCondition
  | BinaryOp
  | UnaryOp;

// 단순 조건: 지표 또는 컨텍스트 변수 비교
interface SimpleCondition {
  type: "simple";
  variable: string;           // "RSI(14)", "시장_변동성", "거래량배수"
  operator: ">" | "<" | "==" | ">=" | "<=";
  value: number;
  unit?: string;             // "%" 등
}

// 이진 연산 (AND/OR)
interface BinaryOp {
  type: "binary";
  operator: "AND" | "OR";
  left: ConditionExpr;
  right: ConditionExpr;
}

// 단항 연산 (NOT)
interface UnaryOp {
  type: "unary";
  operator: "NOT";
  operand: ConditionExpr;
}

// 전체 전략
interface Strategy {
  id?: number;
  name: string;                        // "RSI-Volume Breakout"
  description?: string;
  account_id: number;                  // 연결 계좌
  buy_condition: ConditionExpr;       // 매수 조건식
  sell_condition: ConditionExpr;      // 매도 조건식
  buy_quantity_mode: "fixed" | "ratio";  // 고정수량 vs 비율
  buy_quantity: number;               // 고정: 100주, 비율: 0.5 (자본금의 50%)
  max_position_count: number;         // 최대 보유 종목 수 (default: 5)
  budget_ratio: number;               // 예산 사용 비율 (default: 0.7)
  schedule_buy: string;               // Cron: "30 9 * * 1-5" (평일 09:30)
  schedule_sell: string;              // Cron: "0 15 * * 1-5" (평일 15:00)
  is_active: boolean;
  created_at: datetime;
  updated_at: datetime;
  last_executed_at?: datetime;
}
```

### 4.2 컨텍스트 변수 카탈로그

**서버가 제공하는 실시간/배치 계산 변수들**. 전략식에서 참조 가능.

| 변수명 | 설명 | 계산 주기 | 범위 | 예시 |
|--------|------|----------|------|------|
| `시장_변동성` | 코스피 20일 변동성 | 일 1회 (장 마감 후) | 0~100 | 18.5 |
| `시장_RSI` | 코스피 RSI(14) | 실시간 | 0~100 | 52.3 |
| `섹터_모멘텀_{섹터}` | 섹터별 14일 수익률 | 일 1회 | -100~100 (%) | 금융: +2.3% |
| `코스피_추세` | 코스피 EMA(20,50) 위치도 | 실시간 | -1~1 | 0.8 (상향) |
| `VIX_지수` | 변동성 지수 (외부 API) | 실시간 | 0~100 | 24.5 |
| `내종목_거래량배수` | 20일 평균 대비 현재 거래량 | 실시간 | 0~ | 2.1 |
| `내종목_수익률` | 평균매입가 대비 현재가 수익률 | 실시간 | -100~100 (%) | +3.5% |

### 4.3 미리 정의된 템플릿

사용자가 빠르게 시작할 수 있도록 자주 쓰이는 조건식 템플릿 제공.

1. **RSI 과매도 역발동**:
   - Buy: RSI < 30 AND 거래량배수 > 1.5
   - Sell: 수익률 > +5% OR 손실 < -3%

2. **이동평균 골든크로스**:
   - Buy: EMA(12) > EMA(26) AND 시장_변동성 < 25
   - Sell: EMA(12) < EMA(26)

3. **섹터 모멘텀 추종**:
   - Buy: 섹터_모멘텀 > +3% AND 시장_RSI < 70
   - Sell: 섹터_모멘텀 < 0%

4. **저변동성 고수익률 추구**:
   - Buy: 시장_변동성 < 15 AND RSI < 40
   - Sell: 시장_변동성 > 30 OR 수익률 > +3%

---

## 5. UI 기능 상세

### 5.1 전략 빌더 페이지 레이아웃

```
┌─────────────────────────────────────────────────────────┐
│ Strategy Builder                                          │
├─────────────────────────────────────────────────────────┤
│ [New Strategy] [My Strategies] [Templates]               │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────────────────┬──────────────────────────┐  │
│  │ 좌측 패널: 조건식 빌더   │ 우측 패널: 설정 & 백테스트 │  │
│  │                         │                          │  │
│  │ ◆ 매수 조건              │ 전략명: RSI-Volume      │  │
│  │  ┌──────────────────┐   │ 계좌: [SELECT]          │  │
│  │  │ RSI(14) < [30]   │   │ 예산비율: [70%]         │  │
│  │  └──────────────────┘   │ 최대종목: [5]           │  │
│  │  [AND/OR ▼] [+조건]     │                         │  │
│  │  ┌──────────────────┐   │ 매수수량:               │  │
│  │  │거래량배수 > [2.0]│   │  ○ 고정: [100]주       │  │
│  │  └──────────────────┘   │  ○ 비율: [50]%         │  │
│  │                         │                         │  │
│  │ ◆ 매도 조건              │ 스케줄:                │  │
│  │  ┌──────────────────┐   │  매수: [09:30]         │  │
│  │  │ 수익률 > [+5%]   │   │  매도: [15:00]         │  │
│  │  └──────────────────┘   │                         │  │
│  │  [OR] [+조건]           │ ┌─────────────────────┐ │  │
│  │  ┌──────────────────┐   │ │ Quick Backtest      │ │  │
│  │  │ 손실 < [-3%]     │   │ │ [기간: 3개월 ▼]    │ │  │
│  │  └──────────────────┘   │ │ [실행 중...]        │ │  │
│  │                         │ │                     │ │  │
│  │ [템플릿 로드] [초기화]    │ │ 결과:               │ │  │
│  │                         │ │ 수익률: +8.2%       │ │  │
│  │                         │ │ 승률: 64%           │ │  │
│  │                         │ │ 거래: 14회          │ │  │
│  │                         │ └─────────────────────┘ │  │
│  │                         │                         │  │
│  │                         │ [Save & Activate]     │  │
│  │                         │ [Save as Draft]       │  │
│  └─────────────────────────┴──────────────────────────┘  │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

### 5.2 조건식 빌더 (좌측 패널)

#### 5.2.1 조건 추가/편집
- **단순 조건 입력**:
  - 변수 선택 dropdown (RSI(14), 거래량배수, 시장_변동성 등)
  - 연산자 선택 (<, >, ==, <=, >=)
  - 값 입력 필드 (숫자 또는 슬라이더)
  - 단위 표시 (%, 배수 등)

- **복합 조건 구성**:
  - 조건 추가 시 기존 조건과 AND/OR로 결합
  - 최대 3단계 중첩 허용 (복잡도 제어)
  - 괄호 자동 추가 (우선순위 명시)

#### 5.2.2 컨텍스트 변수 팝오버
- 변수명에 마우스 hover → 팝오버 표시
  - 설명: "코스피 20일 변동성. 실시간 업데이트"
  - 현재값: "18.5"
  - 계산 로직 링크: "Learn more"
  - 백테스팅 시 처리: "과거 데이터로 계산됨"

#### 5.2.3 템플릿 로드
- "Load Template" → 선택지 표시
- 템플릿 선택 → 조건식 자동 채우기
- 사용자는 편집/커스터마이징 가능

### 5.3 전략 설정 패널 (우측 패널)

#### 5.3.1 기본 정보
- **전략명** (text input)
- **설명** (textarea)
- **연결 계좌** (select dropdown - VirtualAccount 목록)

#### 5.3.2 매매 설정
- **매수 수량 모드**:
  - ○ 고정: N주 입력
  - ○ 자본금 비율: %입력
- **최대 보유 종목**: 슬라이더 (1~20, default 5)
- **예산 사용 비율**: 슬라이더 (0%~100%, default 70%)

#### 5.3.3 스케줄 설정
- **매수 시간**: 시간선택 UI (기본: 09:30)
- **매도 시간**: 시간선택 UI (기본: 15:00)
- **요일 선택**: 체크박스 (월~금 기본)
- Cron 표현식 자동 생성 및 미리보기

#### 5.3.4 백테스팅 섹션
- **기간 선택**:
  - Preset: "지난 1개월", "3개월", "1년", "All"
  - Custom: 날짜 범위 선택
- **실행 버튼**: "Quick Backtest" (UI 블로킹 없음, 진행률 표시)
- **결과 표시**:
  - 수익률 (%), 승률 (%), 총거래 (회)
  - 샤프비율, 최대낙폭 (상세 접기/펼치기)
  - 에쿼티 차트 미니 프리뷰

#### 5.3.5 액션 버튼
- **Save & Activate**: DB 저장 후 즉시 스케줄러 반영
- **Save as Draft**: 저장만 (비활성 상태)
- **Preview**: 현재 설정을 YAML/JSON 형태로 표시
- **Discard**: 편집 취소

### 5.4 전략 목록 페이지

```
┌──────────────────────────────────────────────────┐
│ My Strategies                  [+ New Strategy]   │
├──────────────────────────────────────────────────┤
│                                                  │
│ ○ RSI-Volume Breakout        활성 | 수익률 +8.2% │
│   수정일: 2026-03-03 | 실행: 2h 전 | Edit...    │
│                                                  │
│ ○ Golden Cross MA             비활성 | 백테스팅  │
│   수정일: 2026-03-01 | 미실행     | Edit...    │
│                                                  │
│ ○ [Draft] Volatility Hunter   드래프트           │
│   수정일: 2026-02-28 | 미실행     | Edit...    │
│                                                  │
│ [필터] 활성/비활성/드래프트                       │
│ [정렬] 수정일 / 실행일 / 수익률                  │
│                                                  │
└──────────────────────────────────────────────────┘
```

### 5.5 상세 조회/히스토리

```
┌──────────────────────────────────────────────────┐
│ RSI-Volume Breakout — History & Logs             │
├──────────────────────────────────────────────────┤
│                                                  │
│ 현재 규칙 (활성)                                  │
│ ──────────────────────────────────                │
│ 매수: RSI(14) < 30 AND 거래량배수 > 2.0          │
│ 매도: 수익률 > +5% OR 손실 < -3%                 │
│                                                  │
│ 실행 이력                                        │
│ ──────────────────────────────────                │
│ 2026-03-04 09:30 | 매수 실행 | 종목: SK하이닉스  │
│ 2026-03-03 15:00 | 매도 실행 | 총 +3.2%         │
│ 2026-03-02 09:30 | 매수 실행 | 종목: 삼성전자    │
│                                                  │
│ 수정 이력 (백업)                                  │
│ ──────────────────────────────────                │
│ v3 (현재) 2026-03-03  [Restore] [Compare]      │
│ v2       2026-02-28   [Restore] [Compare]      │
│ v1       2026-02-20   [Restore] [Compare]      │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

## 6. 컨텍스트 변수 연동

### 6.1 컨텍스트 계산 파이프라인

```
[매일 16:00] → 지표 계산 (RSI, EMA, MACD, 거래량)
            → 시장 변수 계산 (코스피 RSI, 변동성, 섹터 모멘텀)
            → ContextCloud 객체 생성 & Redis 캐시 저장

[조건식 평가] → 전략 조건식 + ContextCloud 입력
            → 각 종목마다 True/False 판정
            → 매수 대상 종목 결정
```

### 6.2 백테스팅 시 과거 컨텍스트 복원

```
Backtest(from=2025-01-01, to=2026-03-04)
  for each date in range:
    # 과거 데이터로 각 시점의 컨텍스트 재계산
    historical_context = compute_context(date, end=date)
    for each stock:
      buy_signal = eval(buy_condition, stock_data[date], historical_context)
      if buy_signal:
        execute_buy(stock, date)
```

### 6.3 API 엔드포인트

```python
GET /api/v1/strategy/context/variables
# 응답
{
  "success": true,
  "data": [
    {
      "name": "시장_변동성",
      "description": "코스피 20일 변동성",
      "current_value": 18.5,
      "unit": "%",
      "calculation_period": "daily",
      "updated_at": "2026-03-04T16:00:00Z"
    },
    {
      "name": "시장_RSI",
      "description": "코스피 RSI(14)",
      "current_value": 52.3,
      "unit": null,
      "calculation_period": "realtime",
      "updated_at": "2026-03-04T15:30:00Z"
    },
    ...
  ]
}

GET /api/v1/strategy/context/historical
# 파라미터: from_date, to_date
# 응답: 시간대별 컨텍스트 값 시계열

POST /api/v1/strategy/validate
# 요청
{
  "buy_condition": { /* ConditionExpr */ },
  "sell_condition": { /* ConditionExpr */ },
  "test_data": { "RSI(14)": 28, "거래량배수": 2.1, ... }
}
# 응답
{
  "success": true,
  "data": {
    "buy_signal": true,
    "sell_signal": false,
    "validation_errors": []
  }
}
```

---

## 7. 전략 저장/관리

### 7.1 DB 확장

기존 `AutoTradingRule` 모델 확장:

```python
class AutoTradingRule(Base):
    __tablename__ = "auto_trading_rules"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    account_id = Column(Integer, ForeignKey("virtual_accounts.id"))

    # 조건식 (JSON 직렬화)
    buy_condition = Column(JSON, nullable=False)   # ConditionExpr 객체
    sell_condition = Column(JSON, nullable=False)

    # 매매 설정
    buy_quantity_mode = Column(String(20), default="fixed")  # fixed | ratio
    buy_quantity = Column(Float, nullable=False)
    max_position_count = Column(Integer, default=5)
    budget_ratio = Column(Float, default=0.7)

    # 스케줄
    schedule_buy = Column(String(20), default="30 9 * * 1-5")
    schedule_sell = Column(String(20), default="0 15 * * 1-5")

    # 상태
    is_active = Column(Boolean, default=False)
    is_draft = Column(Boolean, default=True)  # 드래프트 vs 저장완료
    version = Column(Integer, default=1)      # 수정 버전 관리

    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_executed_at = Column(DateTime)

# 수정 이력 추적 (별도 테이블)
class AutoTradingRuleHistory(Base):
    __tablename__ = "auto_trading_rule_history"

    id = Column(Integer, primary_key=True)
    rule_id = Column(Integer, ForeignKey("auto_trading_rules.id"), nullable=False)
    version = Column(Integer, nullable=False)
    buy_condition = Column(JSON)
    sell_condition = Column(JSON)
    parameters = Column(JSON)  # 모든 설정 스냅샷
    changed_by = Column(String(100))  # 향후: 사용자 ID
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index('idx_rule_version', 'rule_id', 'version'),
    )
```

### 7.2 API 엔드포인트

```
# 전략 CRUD
POST   /api/v1/strategy/rules          # 신규 생성
GET    /api/v1/strategy/rules          # 목록 조회 (필터, 정렬)
GET    /api/v1/strategy/rules/{id}     # 상세 조회
PATCH  /api/v1/strategy/rules/{id}     # 수정 (새 버전 생성)
DELETE /api/v1/strategy/rules/{id}     # 삭제 (soft delete)

# 상태 관리
PATCH  /api/v1/strategy/rules/{id}/activate    # 활성화 (스케줄러 반영)
PATCH  /api/v1/strategy/rules/{id}/deactivate  # 비활성화

# 백테스팅
POST   /api/v1/strategy/backtest       # 백테스팅 실행 (async)
GET    /api/v1/strategy/backtest/{id}  # 결과 조회

# 이력
GET    /api/v1/strategy/rules/{id}/history     # 수정 이력
GET    /api/v1/strategy/rules/{id}/executions  # 실행 이력

# 템플릿
GET    /api/v1/strategy/templates      # 템플릿 목록
POST   /api/v1/strategy/templates      # 템플릿 저장 (사용자)
```

### 7.3 활성화 워크플로우

```
사용자: "Save & Activate" 클릭

1. UI 검증
   - 조건식 문법 체크
   - 필수 필드 확인

2. API: POST /api/v1/strategy/rules/{id}/activate

3. 백엔드:
   - AutoTradingRule.is_active = True
   - AutoTradingRule.is_draft = False
   - scheduler.reload_rules() 호출

4. 스케줄러 반응:
   - 기존 job 제거 (있으면)
   - 신규 job 등록
   - 로깅

5. UI: "활성화됨" 상태로 목록 업데이트
```

---

## 8. 기술 요구사항

### 8.1 백엔드 구현

#### 8.1.1 조건식 평가기 (Evaluator)
- **위치**: `backend/app/services/condition_evaluator.py` (신규)
- **기능**: ConditionExpr 객체 + 데이터 입력 → True/False 판정
- **의존성**: 없음 (순수 로직)
- **테스트**: 유닛 테스트 필수 (복합 조건식, edge case)

```python
class ConditionEvaluator:
    """조건식 평가"""

    def evaluate(
        self,
        expr: dict,  # ConditionExpr JSON
        stock_data: dict,  # {"RSI(14)": 28, "거래량배수": 2.1}
        context: dict  # {"시장_변동성": 18.5, "시장_RSI": 52.3}
    ) -> bool:
        """expr이 True인지 판정"""
        ...

    def validate_expr(self, expr: dict) -> List[str]:
        """문법 검증, 에러 리스트 반환"""
        ...
```

#### 8.1.2 컨텍스트 관리자
- **위치**: `backend/app/services/context_cloud.py` (신규)
- **기능**: 실시간/과거 컨텍스트 계산
- **배치**: 매일 16:00 실행 (APScheduler)

```python
class ContextCloud:
    """시장 컨텍스트 변수 관리"""

    def compute_current(self) -> dict:
        """현재 시점 컨텍스트 계산"""
        # 시장_변동성, 시장_RSI, 섹터_모멘텀, ...
        ...

    def compute_historical(self, from_date, to_date) -> dict:
        """과거 기간 컨텍스트 재계산"""
        # Backtest용
        ...
```

#### 8.1.3 API 라우터
- **위치**: `backend/app/api/strategy_builder.py` (신규)
- **기능**: 전전략 CRUD, 백테스팅, 활성화 등

#### 8.1.4 기존 코드 수정
- `backend/app/services/auto_trade_scheduler.py`:
  - `reload_rules()` 이미 존재 ✓
  - 조건식 평가 로직 추가 (기존 score_threshold 대체)

### 8.2 프론트엔드 구현

#### 8.2.1 컴포넌트 구조
```
frontend/src/pages/StrategyBuilder.tsx
  ├── StrategyForm.tsx (좌측 조건식 + 우측 설정)
  │   ├── ConditionBuilder.tsx (조건식 트리 에디터)
  │   │   ├── ConditionNode.tsx (개별 조건)
  │   │   └── ContextVariablePopover.tsx
  │   └── StrategySettingsPanel.tsx (설정 폼)
  │       ├── ScheduleSelector.tsx
  │       └── BacktestWidget.tsx
  ├── StrategyList.tsx (목록 페이지)
  └── StrategyHistory.tsx (상세/이력)
```

#### 8.2.2 상태 관리
- React Query: API 데이터 (strategies, backtest results)
- Zustand 또는 Context: 폼 상태 (draft 조건식, 설정)
- 로컬 스토리지: 임시 저장 (페이지 이탈 전 복구)

#### 8.2.3 라이브러리
- Recharts: 백테스트 결과 차트
- React Hook Form + Zod: 폼 검증
- Day.js: 날짜 처리

### 8.3 데이터베이스

- SQLite (개발) / PostgreSQL (운영)
- 마이그레이션: Alembic으로 `AutoTradingRule` 확장
- 인덱스: `(rule_id, version)`, `(rule_id, is_active)`

### 8.4 테스트

- **유닛**: ConditionEvaluator (단순/복합 조건식)
- **통합**: API 엔드포인트 (CRUD, 활성화)
- **E2E**: "전략 생성 → 백테스팅 → 활성화 → 스케줄러 반영" 플로우

---

## 9. 미결 사항

### 9.1 설계 결정 대기

1. **조건식 UI 방식**
   - 방안 A: 드래그 드롭 (복잡, 강력)
   - 방안 B: 폼 기반 (단순, 가독성 좋음)
   - **결정**: 방안 B로 초안 작성. 방안 A는 추후 고도화

2. **컨텍스트 변수 확장성**
   - 사용자 정의 변수 추가 가능하게?
   - 시계열 테크니컬 지표 (ATR, Stoch) 추가 타이밍?
   - **결정**: MVP는 서버 고정 변수 7개만. 사용자 정의는 Phase 4

3. **백테스팅 UI/UX**
   - "Real-time" 진행률 표시?
   - 결과 상세 탭 (거래 로그, 차트 등)?
   - **결정**: 미니 프리뷰만 먼저. 상세는 별도 페이지 (BacktestDetail)

4. **다중 계좌 지원**
   - 하나의 전략을 여러 계좌에 적용?
   - 계좌별 예산 비율 별도 설정?
   - **결정**: MVP는 계좌 1:1 (확장성은 구조에 내재)

5. **권한 관리 (향후)**
   - 팀 멤버와 전략 공유?
   - 감사 로깅 (누가 언제 활성화)?
   - **결정**: Phase 4 (현재 1인 개발)

### 9.2 구현 세부사항 정리 필요

- [ ] ConditionExpr 정확한 JSON 스키마 (JSON Schema 표준)
- [ ] 컨텍스트 변수 계산 로직 상세 (각 변수별)
- [ ] 백테스팅 실행 시 조건식 평가 통합 방식
- [ ] 드래프트 저장 vs 자동저장 정책
- [ ] 에러 처리 & 사용자 메시지 카탈로그

### 9.3 이전 단계 완료 필수

- Phase 2 "가상 자동매매 시스템" 완성 (AutoTradingRule 구조)
- BacktestResult 평가 결과 정확성 검증
- 스케줄러 reload_rules() 안정성 확인

---

## 10. 참고

### 10.1 기존 코드 위치

| 영역 | 경로 | 역할 |
|------|------|------|
| 자동매매 규칙 모델 | `backend/app/models/auto_trading.py` | AutoTradingRule, BacktestResult |
| 스케줄러 | `backend/app/services/auto_trade_scheduler.py` | 규칙 실행, reload_rules() |
| 스코어링 엔진 | `backend/app/services/scoring_engine.py` | 종목 스코어 계산 |
| 거래 엔진 | `backend/app/services/trading_engine.py` | 매수/매도 로직 |
| 기술적 지표 | `backend/app/services/technical_indicators.py` | RSI, EMA, MACD, 볼린저밴드 |
| Trading API | `backend/app/api/trading.py` | 규칙 CRUD 엔드포인트 |

### 10.2 외부 참고자료

- Cron 표현식: https://crontab.guru/
- JSON Schema: https://json-schema.org/
- React Hook Form: https://react-hook-form.com/

### 10.3 다음 단계 (plan.md 작성 시 상세화)

1. **Step 1**: 백엔드 조건식 평가기 + 컨텍스트 관리자 구현
2. **Step 2**: API 라우터 (strategy_builder.py) 구현
3. **Step 3**: DB 마이그레이션 + 기존 코드 통합
4. **Step 4**: React 페이지 & 컴포넌트 구현
5. **Step 5**: E2E 테스트 & 운영 배포

---

**문서 이력**
- 2026-03-04: 초안 작성 (명세서만, 구현 아님)
