# 전략 템플릿 관리 명세서 (strategy-template)

> 작성일: 2026-03-04 | 상태: **→ Unit 6 (admin)에 통합** | 의존성: strategy-builder
>
> 이 spec의 내용은 `spec/admin/`에서 통합 구현합니다.

## 1. 개요

**전략 템플릿 (Strategy Template)** 은 운영자(관리자)가 미리 설계하고 검증한 자동매매 전략 예시를 사용자에게 제공하는 기능이다.

### 배경
- **문제**: 사용자가 처음부터 자동매매 규칙을 설계하기는 어려움 → 진입장벽 높음
- **해결책**: 운영자가 검증된 템플릿을 미리 준비 → 사용자가 템플릿을 불러와 필요시 커스터마이징해서 사용
- **법적 포지션**: 템플릿은 "예시 코드"와 같음 — 투자 추천이 아님. 사용자가 규칙을 이해하고 동의 후 활성화

### 핵심 가치
1. **사용자 진입 가속화**: 템플릿을 통해 기술적 지표를 학습하면서 전략 구성
2. **모범 사례 제시**: 운영자가 검증한 조건식 조합 (예: RSI + 거래량)
3. **법적 명확성**: "이것은 전략 예시입니다" 명시 → 투자 추천 아님을 분명히
4. **마켓플레이스 기반 구축**: 향후 사용자가 템플릿을 공유/판매할 때를 대비한 설계

---

## 2. 템플릿 vs 마켓플레이스 구분

### 2.1 템플릿 (본 스펙 범위)

| 속성 | 설명 |
|------|------|
| **작성자** | 운영자 (StockVision) |
| **검증** | 백테스팅 + 운영팀 승인 |
| **배포** | UI 내 "Templates" 섹션에 노출 |
| **비용** | 무료 |
| **사용자 상호작용** | 불러오기 → 읽기 전용 모드 → 복제 후 커스터마이징 |
| **용도** | 초급자 학습, 빠른 시작 |
| **법적 명시** | "예시 전략입니다. 수익을 보장하지 않습니다" |

### 2.2 마켓플레이스 (향후 Phase 4+)

| 속성 | 설명 |
|------|------|
| **작성자** | 사용자, 전문가 |
| **검증** | 커뮤니티 평가, 선택적 |
| **배포** | 별도 마켓플레이스 페이지 |
| **비용** | 유료 가능 |
| **사용자 상호작용** | 구매 → 다운로드 → 사용 |
| **용도** | 전문 전략 유통 |
| **법적 명시** | 판매자 책임 (StockVision은 중개 역할만) |

---

## 3. 템플릿 구조 정의

### 3.1 템플릿 객체 스키마

```typescript
interface StrategyTemplate {
  id: string;                          // UUID 또는 slug (예: "rsi-oversold-v1")
  name: string;                        // 템플릿 이름 (예: "RSI 과매도 역발동")
  description: string;                 // 한 줄 설명
  detailed_description: string;        // 상세 설명 (전략 철학, 적용 조건)
  author: "StockVision";               // 운영자만 가능
  version: string;                     // 버전 (예: "1.0.0")
  category: string;                    // 분류 (technical, momentum, volatility, sector, context)

  // 법적 면책
  disclaimer: string;                  // "이 전략은 투자 추천이 아닙니다..."
  risk_level: "low" | "medium" | "high";  // 위험도

  // 전략 조건식 (strategy-builder의 ConditionExpr 형식)
  buy_condition: object;               // { type, operator, variable, ... }
  sell_condition: object;

  // 매매 설정 (권장값)
  recommended_buy_quantity_mode: "fixed" | "ratio";
  recommended_buy_quantity: number;
  recommended_max_position_count: number;
  recommended_budget_ratio: number;
  recommended_schedule_buy: string;    // Cron 표현
  recommended_schedule_sell: string;

  // 백테스팅 통계 (제공용)
  backtest_summary: {
    period_start: string;              // YYYY-MM-DD
    period_end: string;
    initial_balance: number;
    final_balance: number;
    total_return: number;              // %
    sharpe_ratio: number;
    max_drawdown: number;              // %
    win_rate: number;                  // %
    total_trades: number;
    last_backtest_date: string;        // 언제 마지막 검증했는지
  };

  // 메타데이터
  tags: string[];                      // ["RSI", "거래량", "역발동"]
  difficulty: "beginner" | "intermediate" | "advanced";
  popularity_score?: number;           // 사용률 기반 점수 (0~5)
  is_published: boolean;               // 운영팀 승인 여부
  published_at?: datetime;
  created_at: datetime;
  updated_at: datetime;
}
```

### 3.2 템플릿 저장 구조 (DB)

```python
class StrategyTemplate(Base):
    __tablename__ = "strategy_templates"

    id = Column(String(50), primary_key=True)  # slug: "rsi-oversold-v1"
    name = Column(String(100), nullable=False)
    description = Column(String(200))
    detailed_description = Column(Text)
    author = Column(String(50), default="StockVision", nullable=False)
    version = Column(String(20), nullable=False)  # "1.0.0"
    category = Column(String(30), nullable=False)  # technical, momentum, ...

    # 면책
    disclaimer = Column(Text, nullable=False)
    risk_level = Column(String(20))  # low, medium, high

    # 조건식
    buy_condition = Column(JSON, nullable=False)
    sell_condition = Column(JSON, nullable=False)

    # 권장 설정
    recommended_buy_quantity_mode = Column(String(20), default="fixed")
    recommended_buy_quantity = Column(Float)
    recommended_max_position_count = Column(Integer, default=5)
    recommended_budget_ratio = Column(Float, default=0.7)
    recommended_schedule_buy = Column(String(20))
    recommended_schedule_sell = Column(String(20))

    # 백테스팅 결과
    backtest_summary = Column(JSON)

    # 메타
    tags = Column(JSON)  # ["RSI", "거래량"]
    difficulty = Column(String(20))  # beginner, intermediate, advanced
    popularity_score = Column(Float, default=0)
    is_published = Column(Boolean, default=False)
    published_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_category', 'category'),
        Index('idx_is_published', 'is_published'),
    )
```

---

## 4. 제공 템플릿 목록 (초기)

### 4.1 Template 1: RSI 과매도 역발동

```
ID: rsi-oversold-v1
분류: technical
위험도: low
난이도: beginner

설명:
  RSI가 과매도 구간(< 30)에 진입하면 반발을 노린 전략.
  거래량이 함께 증가하는 조건으로 오신호 필터링.

매수 조건:
  (RSI(14) < 30) AND (거래량배수 > 1.5)

매도 조건:
  (수익률 > +5%) OR (손실 < -3%)

권장 설정:
  - 매수수량: 고정 100주
  - 최대종목: 5개
  - 예산비율: 70%
  - 매수시간: 09:30 (평일)
  - 매도시간: 15:00 (평일)

백테스팅 결과 (2024-01-01 ~ 2026-03-04):
  수익률: +8.2%
  승률: 64%
  최대낙폭: -5.3%
  샤프비율: 1.12
  총거래: 14회

태그: ["RSI", "과매도", "거래량"]
```

### 4.2 Template 2: 이동평균 골든크로스

```
ID: golden-cross-ma-v1
분류: technical
위험도: medium
난이도: intermediate

설명:
  EMA(12)와 EMA(26)의 교차를 기반으로 한 전형적인 추세 추종 전략.
  시장 변동성이 안정적일 때 신호 신뢰도 증가.

매수 조건:
  (EMA(12) > EMA(26)) AND (시장_변동성 < 25)

매도 조건:
  EMA(12) < EMA(26)

권장 설정:
  - 매수수량: 자본금 비율 30%
  - 최대종목: 8개
  - 예산비율: 60%
  - 매수시간: 10:00
  - 매도시간: 15:00

백테스팅 결과 (2024-01-01 ~ 2026-03-04):
  수익률: +12.5%
  승률: 58%
  최대낙폭: -8.2%
  샤프비율: 1.35
  총거래: 23회

태그: ["EMA", "골든크로스", "추세"]
```

### 4.3 Template 3: 섹터 모멘텀 추종

```
ID: sector-momentum-v1
분류: sector
위험도: high
난이도: advanced

설명:
  강한 모멘텀을 보이는 섹터의 대표주를 매수.
  시장 RSI가 과열되면 제약을 걸어 위험 제어.

매수 조건:
  (섹터_모멘텀 > +3%) AND (시장_RSI < 70)

매도 조건:
  (섹터_모멘텀 < 0%) OR (수익률 < -5%)

권장 설정:
  - 매수수량: 고정 50주
  - 최대종목: 10개
  - 예산비율: 80%
  - 매수시간: 09:30
  - 매도시간: 14:30

백테스팅 결과 (2024-01-01 ~ 2026-03-04):
  수익률: +15.8%
  승률: 52%
  최대낙폭: -12.1%
  샤프비율: 1.28
  총거래: 31회

태그: ["섹터", "모멘텀", "고위험"]
```

### 4.4 Template 4: 저변동성 고수익률 추구

```
ID: low-volatility-profit-v1
분류: volatility
위험도: low
난이도: intermediate

설명:
  시장이 안정적인 국면에서만 거래.
  보유 종목의 수익률이 조기에 실현 (손절은 느슨함).
  보수적이고 안정적인 수익 추구.

매수 조건:
  (시장_변동성 < 15) AND (RSI(14) < 40)

매도 조건:
  (시장_변동성 > 30) OR (수익률 > +3%)

권장 설정:
  - 매수수량: 자본금 비율 20%
  - 최대종목: 4개
  - 예산비율: 50%
  - 매수시간: 11:00
  - 매도시간: 15:30

백테스팅 결과 (2024-01-01 ~ 2026-03-04):
  수익률: +6.8%
  승률: 71%
  최대낙폭: -2.1%
  샤프비율: 1.64
  총거래: 8회

태그: ["변동성", "보수적", "저위험"]
```

### 4.5 Template 5: 맥스 (MAX) 전략 — VIX 역상관 활용

```
ID: vix-inverse-correlation-v1
분류: context
위험도: medium
난이도: advanced

설명:
  공포지수(VIX)가 상승하면 매도 압박.
  VIX < 20일 때만 진공매 진행 (위험 제어).
  코스피 추세와 결합하여 손실 최소화.

매수 조건:
  (VIX_지수 < 20) AND (코스피_추세 > 0)

매도 조건:
  (VIX_지수 > 25) OR (손실 < -4%) OR (수익률 > +4%)

권장 설정:
  - 매수수량: 자본금 비율 40%
  - 최대종목: 6개
  - 예산비율: 65%
  - 매수시간: 10:30
  - 매도시간: 14:30

백테스팅 결과 (2024-01-01 ~ 2026-03-04):
  수익률: +9.5%
  승률: 60%
  최대낙폭: -6.8%
  샤프비율: 1.42
  총거래: 18회

태그: ["VIX", "공포지수", "위험제어"]
```

---

## 5. 사용자 UI/UX: 템플릿 탐색 및 적용

### 5.1 템플릿 갤러리 페이지

```
┌──────────────────────────────────────────────────────────────┐
│ Strategy Templates                          [+ Create Custom]  │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│ 필터 & 정렬:                                                  │
│ [분류 ▼] [난이도 ▼] [위험도 ▼] [정렬: 인기순 ▼]              │
│                                                               │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────┐  ┌─────────────────────┐             │
│  │ RSI 과매도 역발동    │  │ 이동평균 골든크로스  │             │
│  │ ────────────────    │  │ ────────────────    │             │
│  │ 난이도: 초급         │  │ 난이도: 중급        │             │
│  │ 위험도: 낮음         │  │ 위험도: 중간        │             │
│  │ 수익률: +8.2%       │  │ 수익률: +12.5%     │             │
│  │ ★★★★☆ (4.2/5)    │  │ ★★★★☆ (4.5/5)    │             │
│  │                    │  │                    │             │
│  │ RSI + 거래량        │  │ EMA + 변동성       │             │
│  │ 피필터: 거래 14회   │  │ 피필터: 거래 23회   │             │
│  │                    │  │                    │             │
│  │ [자세히 보기] [사용] │  │ [자세히 보기] [사용] │             │
│  └─────────────────────┘  └─────────────────────┘             │
│                                                               │
│  ┌─────────────────────┐  ┌─────────────────────┐             │
│  │ 섹터 모멘텀 추종     │  │ 저변동성 고수익률    │             │
│  │ ...                 │  │ ...                 │             │
│  └─────────────────────┘  └─────────────────────┘             │
│                                                               │
│  ┌─────────────────────┐                                     │
│  │ VIX 역상관 (MAX)    │                                     │
│  │ ...                 │                                     │
│  └─────────────────────┘                                     │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### 5.2 템플릿 상세 보기 페이지

```
┌──────────────────────────────────────────────────────────┐
│ RSI 과매도 역발동 전략 (rsi-oversold-v1)                  │
├──────────────────────────────────────────────────────────┤
│                                                          │
│ ⚠️ 중요 면책 공지                                       │
│ ─────────────────────────────────────────────────      │
│ 이 전략은 StockVision이 제공하는 예시 전략입니다.       │
│ 수익을 보장하지 않으며, 사용자 책임하에 활용해야 합니다. │
│ 필요시 재무전문가와 상담하세요.                        │
│                                                          │
│ [✓ 이해했습니다]                                        │
│                                                          │
├──────────────────────────────────────────────────────────┤
│                                                          │
│ 전략 개요                                              │
│ ─────────────────────────────────────────────────────  │
│ 난이도: 초급 | 위험도: 낮음                             │
│ 인기도: ★★★★☆ (4.2/5, 287명 사용 중)                 │
│                                                          │
│ RSI가 과매도 구간(< 30)에 진입하면 반발을 노린 전략.   │
│ 거래량이 함께 증가하는 조건으로 오신호 필터링.         │
│                                                          │
│ 매수 조건:                                             │
│   RSI(14) < 30 AND 거래량배수 > 1.5                   │
│                                                          │
│ 매도 조건:                                             │
│   수익률 > +5% OR 손실 < -3%                          │
│                                                          │
├──────────────────────────────────────────────────────────┤
│                                                          │
│ 백테스팅 성과 (2024-01-01 ~ 2026-03-04)               │
│ ─────────────────────────────────────────────────────  │
│ 수익률:         +8.2%                                 │
│ 승률:           64%  (9승/14회)                        │
│ 최대낙폭:       -5.3%                                 │
│ 샤프비율:       1.12                                  │
│ 총 거래 횟수:   14회                                  │
│                                                          │
│ [에쿠이티 차트 보기]                                    │
│                                                          │
├──────────────────────────────────────────────────────────┤
│                                                          │
│ 권장 설정                                              │
│ ─────────────────────────────────────────────────────  │
│ 매수수량:       고정 100주                              │
│ 최대종목:       5개                                    │
│ 예산비율:       70%                                   │
│ 매수시간:       09:30 (평일)                           │
│ 매도시간:       15:00 (평일)                           │
│                                                          │
├──────────────────────────────────────────────────────────┤
│                                                          │
│ 관련 태그                                              │
│ [RSI] [과매도] [거래량] [역발동]                        │
│                                                          │
├──────────────────────────────────────────────────────────┤
│                                                          │
│ [이 템플릿으로 전략 생성] [다른 템플릿 보기]             │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### 5.3 템플릿을 통한 전략 생성 플로우

```
사용자: "RSI 과매도" 템플릿 클릭 → "사용" 버튼

↓

Step 1: 면책 확인
  - ⚠️ "이 전략은 투자 추천이 아닙니다" 재확인
  - [동의하고 계속] 버튼 필수

↓

Step 2: Strategy Builder로 점프
  - 템플릿의 조건식이 자동으로 폼에 채워짐
  - 권장 설정(매수수량, 스케줄 등)도 프리필 됨
  - 사용자는 필요시 커스터마이징

↓

Step 3: 백테스팅 (선택)
  - "템플릿 백테스팅 결과 보기" (제공된 통계)
  - "내 조건으로 재백테스팅" (사용자 수정 후)

↓

Step 4: 저장 & 활성화
  - "Save & Activate" → 스케줄러 반영
  - 원본 템플릿은 유지되고, 사용자 전략은 별개 저장
```

---

## 6. 관리자(운영팀) UI: 템플릿 생성/관리

### 6.1 관리자 패널 (Admin Dashboard)

```
┌─────────────────────────────────────────────────┐
│ Strategy Templates Management                    │
├─────────────────────────────────────────────────┤
│                                                 │
│ [+ Create New Template] [Sync from Backtest]    │
│                                                 │
├─────────────────────────────────────────────────┤
│                                                 │
│ 게시된 템플릿 (5)                               │
│ ─────────────────────────────────────────────  │
│ ID                | 이름            | 수익률   │
│ rsi-oversold-v1   | RSI 과매도      | +8.2%  │
│ golden-cross-v1   | 골든크로스      | +12.5% │
│ sector-momentum-v1| 섹터 모멘텀     | +15.8% │
│                                                 │
│ [Edit] [Delete] [Unpublish] [View Stats]       │
│                                                 │
├─────────────────────────────────────────────────┤
│                                                 │
│ 드래프트 (2)                                     │
│ ─────────────────────────────────────────────  │
│ (작업 중인 템플릿들)                            │
│                                                 │
│ [Edit] [Preview] [Publish] [Delete]            │
│                                                 │
└─────────────────────────────────────────────────┘
```

### 6.2 템플릿 생성/편집 폼

```
┌──────────────────────────────────────────────────┐
│ Create/Edit Strategy Template                    │
├──────────────────────────────────────────────────┤
│                                                  │
│ 기본 정보                                       │
│ ─────────────────────────────────────────────  │
│ ID (Slug):           [rsi-oversold-v1]         │
│ 이름:                [RSI 과매도 역발동]        │
│ 한 줄 설명:          [RSI < 30일 때 진공매]    │
│                                                  │
│ 상세 설명 (Markdown):                           │
│ ┌──────────────────────────────────────────┐   │
│ │ RSI가 과매도 구간에 진입하면 반발을...     │   │
│ │ 거래량 필터링으로 신호 신뢰도 확보...     │   │
│ └──────────────────────────────────────────┘   │
│                                                  │
│ 분류:               [technical ▼]              │
│ 위험도:             [low ▼]                    │
│ 난이도:             [beginner ▼]               │
│ 인기도 (수동):      [3.5/5.0]                  │
│                                                  │
├──────────────────────────────────────────────────┤
│ 면책 & 위험 공시                                │
│ ─────────────────────────────────────────────  │
│ 면책문:                                        │
│ ┌──────────────────────────────────────────┐   │
│ │ 이 전략은 StockVision이 제공하는 예시    │   │
│ │ 전략입니다. 수익을 보장하지 않습니다...   │   │
│ └──────────────────────────────────────────┘   │
│                                                  │
├──────────────────────────────────────────────────┤
│ 조건식 (Strategy Builder 형식)                  │
│ ─────────────────────────────────────────────  │
│ 매수 조건:   [JSON 입력/시각화 편집기]          │
│ 매도 조건:   [JSON 입력/시각화 편집기]          │
│                                                  │
├──────────────────────────────────────────────────┤
│ 권장 설정                                       │
│ ─────────────────────────────────────────────  │
│ 매수수량 모드:      [fixed ▼]                  │
│ 매수수량 값:        [100]                      │
│ 최대종목:          [5]                         │
│ 예산비율:          [70%]                       │
│ 매수 스케줄:       [09:30 ▼]                  │
│ 매도 스케줄:       [15:00 ▼]                  │
│                                                  │
├──────────────────────────────────────────────────┤
│ 백테스팅 결과 (자동 업로드)                     │
│ ─────────────────────────────────────────────  │
│ 백테스팅 기간:      [2024-01-01 ~ 2026-03-04] │
│ 수익률:            [+8.2%]                    │
│ 승률:              [64%]                      │
│ 최대낙폭:          [-5.3%]                    │
│ 샤프비율:          [1.12]                     │
│ 총 거래:           [14]                       │
│                                                  │
│ [백테스팅 다시 실행]                            │
│                                                  │
├──────────────────────────────────────────────────┤
│ 태그                                            │
│ ─────────────────────────────────────────────  │
│ [RSI] [과매도] [거래량] [+ 태그 추가]           │
│                                                  │
├──────────────────────────────────────────────────┤
│                                                  │
│ [Save as Draft] [Publish] [Preview] [Cancel]   │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

## 7. 기술 요구사항

### 7.1 백엔드 구현

#### 7.1.1 DB 확장

새로운 테이블: `strategy_templates`

```python
class StrategyTemplate(Base):
    __tablename__ = "strategy_templates"

    id = Column(String(50), primary_key=True)  # slug
    name = Column(String(100), nullable=False, index=True)
    description = Column(String(200))
    detailed_description = Column(Text)
    author = Column(String(50), default="StockVision", nullable=False)
    version = Column(String(20), nullable=False)
    category = Column(String(30), nullable=False, index=True)  # technical, momentum, ...

    disclaimer = Column(Text, nullable=False)
    risk_level = Column(String(20))  # low, medium, high

    buy_condition = Column(JSON, nullable=False)
    sell_condition = Column(JSON, nullable=False)

    recommended_buy_quantity_mode = Column(String(20), default="fixed")
    recommended_buy_quantity = Column(Float)
    recommended_max_position_count = Column(Integer, default=5)
    recommended_budget_ratio = Column(Float, default=0.7)
    recommended_schedule_buy = Column(String(20))
    recommended_schedule_sell = Column(String(20))

    backtest_summary = Column(JSON)  # {period_start, period_end, total_return, ...}

    tags = Column(JSON)
    difficulty = Column(String(20))  # beginner, intermediate, advanced
    popularity_score = Column(Float, default=0.0)

    is_published = Column(Boolean, default=False, index=True)
    published_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_category_published', 'category', 'is_published'),
        Index('idx_difficulty', 'difficulty'),
    )
```

기존 `AutoTradingRule` 모델에 필드 추가:

```python
class AutoTradingRule(Base):
    # 기존 필드...

    # 템플릿 소스 추적
    created_from_template_id = Column(
        String(50),
        ForeignKey("strategy_templates.id"),
        nullable=True
    )  # 이 규칙이 어느 템플릿에서 파생되었는지
```

#### 7.1.2 API 엔드포인트

```python
# 사용자 API
GET    /api/v1/strategy/templates                  # 템플릿 목록 (필터, 정렬)
GET    /api/v1/strategy/templates/{id}             # 템플릿 상세
POST   /api/v1/strategy/templates/{id}/apply       # 템플릿→전략 생성

# 관리자 API (추후)
POST   /api/v1/admin/strategy/templates            # 템플릿 생성
PATCH  /api/v1/admin/strategy/templates/{id}       # 템플릿 수정
DELETE /api/v1/admin/strategy/templates/{id}       # 템플릿 삭제
PATCH  /api/v1/admin/strategy/templates/{id}/publish   # 게시

# 통계
GET    /api/v1/strategy/templates/{id}/stats       # 사용 통계
```

**엔드포인트 상세:**

```python
# GET /api/v1/strategy/templates?category=technical&difficulty=beginner&sort=popularity
# 응답
{
  "success": true,
  "data": [
    {
      "id": "rsi-oversold-v1",
      "name": "RSI 과매도 역발동",
      "description": "RSI < 30일 때 진공매",
      "category": "technical",
      "difficulty": "beginner",
      "risk_level": "low",
      "tags": ["RSI", "과매도", "거래량"],
      "popularity_score": 4.2,
      "user_count": 287,
      "backtest_summary": {
        "total_return": 8.2,
        "sharpe_ratio": 1.12,
        "win_rate": 64,
        "last_backtest_date": "2026-03-04"
      }
    },
    ...
  ],
  "count": 5
}

# POST /api/v1/strategy/templates/{id}/apply
# 요청
{
  "name": "My RSI Strategy",  # 사용자가 부여할 전략명
  "account_id": 1,           # 연결할 계좌
  "customize": {             # 선택: 권장값 수정
    "recommended_buy_quantity": 50,  # 100 → 50으로 변경
    "recommended_budget_ratio": 0.5
  }
}
# 응답
{
  "success": true,
  "data": {
    "rule_id": 123,
    "name": "My RSI Strategy",
    "created_from_template_id": "rsi-oversold-v1",
    "is_draft": true,
    "created_at": "2026-03-04T..."
  }
}
```

#### 7.1.3 서비스 계층

**새로운 파일: `backend/app/services/template_manager.py`**

```python
class TemplateManager:
    """전략 템플릿 관리"""

    def get_published_templates(
        self,
        category: Optional[str] = None,
        difficulty: Optional[str] = None,
        sort_by: str = "popularity"
    ) -> List[StrategyTemplate]:
        """게시된 템플릿 목록 조회"""
        ...

    def get_template(self, template_id: str) -> StrategyTemplate:
        """특정 템플릿 조회"""
        ...

    def create_strategy_from_template(
        self,
        template_id: str,
        strategy_name: str,
        account_id: int,
        customize: Optional[dict] = None
    ) -> AutoTradingRule:
        """템플릿으로부터 사용자 전략 생성"""
        # 1. 템플릿 조회
        # 2. AutoTradingRule 인스턴스 생성 (조건식, 권장설정 복사)
        # 3. 사용자 커스터마이징 적용 (있으면)
        # 4. 드래프트 상태로 저장
        # 5. created_from_template_id 링크
        ...

    def increment_template_usage(self, template_id: str):
        """템플릿 사용 횟수 증가 (인기도 업데이트)"""
        ...
```

### 7.2 프론트엔드 구현

#### 7.2.1 컴포넌트 구조

```
frontend/src/pages/StrategyTemplates.tsx
  ├── TemplateGallery.tsx (필터, 갤러리 그리드)
  │   ├── TemplateFilter.tsx (분류, 난이도, 위험도, 정렬)
  │   └── TemplateCard.tsx (카드 디자인)
  │
  ├── TemplateDetail.tsx (상세 페이지)
  │   ├── DisclaimerModal.tsx (면책 확인)
  │   ├── BacktestSummary.tsx (백테스팅 결과)
  │   └── ApplyTemplateButton.tsx (전략 생성)
  │
  └── (기존) StrategyBuilder.tsx
      - 템플릿 적용 시 폼 프리필 기능 추가
```

#### 7.2.2 핵심 컴포넌트 상세

**TemplateCard.tsx**
```tsx
interface TemplateCardProps {
  template: StrategyTemplate;
  onSelect: (templateId: string) => void;
}

export function TemplateCard({ template, onSelect }: TemplateCardProps) {
  return (
    <Card>
      <CardHeader>
        <h3>{template.name}</h3>
        <Badge variant={template.risk_level}>{template.risk_level}</Badge>
      </CardHeader>
      <CardBody>
        <p>{template.description}</p>
        <div className="stats">
          <Stat label="수익률" value={`${template.backtest_summary.total_return}%`} />
          <Stat label="승률" value={`${template.backtest_summary.win_rate}%`} />
          <Stars rating={template.popularity_score} />
        </div>
        <Tags tags={template.tags} />
      </CardBody>
      <CardFooter>
        <Button onClick={() => onSelect(template.id)}>사용</Button>
      </CardFooter>
    </Card>
  );
}
```

**DisclaimerModal.tsx**
```tsx
// 템플릿 상세 진입 시 강제 표시
export function DisclaimerModal({ onAccept }: { onAccept: () => void }) {
  return (
    <Modal isOpen={true}>
      <ModalHeader>⚠️ 중요 면책 공지</ModalHeader>
      <ModalBody>
        <p>이 전략은 StockVision이 제공하는 예시 전략입니다.</p>
        <p>수익을 보장하지 않으며, 사용자 책임하에 활용해야 합니다.</p>
        <Checkbox>위 내용을 이해했습니다</Checkbox>
      </ModalBody>
      <ModalFooter>
        <Button onPress={onAccept}>동의하고 계속</Button>
      </ModalFooter>
    </Modal>
  );
}
```

#### 7.2.3 API 클라이언트

```typescript
// frontend/src/services/api.ts (추가)

export const templateAPI = {
  getTemplates: (
    category?: string,
    difficulty?: string,
    sortBy?: string
  ) =>
    client.get('/api/v1/strategy/templates', {
      params: { category, difficulty, sort_by: sortBy }
    }),

  getTemplate: (id: string) =>
    client.get(`/api/v1/strategy/templates/${id}`),

  applyTemplate: (templateId: string, data: ApplyTemplateRequest) =>
    client.post(`/api/v1/strategy/templates/${templateId}/apply`, data),
};
```

### 7.3 데이터베이스 마이그레이션

```bash
# Alembic 마이그레이션 파일 생성
alembic revision --autogenerate -m "Add strategy_templates table and created_from_template_id to AutoTradingRule"

# 마이그레이션 내용
# - strategy_templates 테이블 생성 (schema 위 참조)
# - auto_trading_rules.created_from_template_id 컬럼 추가
# - 인덱스 생성
```

### 7.4 테스트

#### 유닛 테스트
```python
# backend/tests/test_template_manager.py

def test_get_published_templates():
    """게시된 템플릿만 조회"""
    ...

def test_create_strategy_from_template():
    """템플릿으로부터 전략 생성"""
    ...

def test_apply_template_with_customization():
    """커스터마이징 적용"""
    ...
```

#### 통합 테스트
```python
# 사용자가 템플릿 갤러리 → 선택 → 면책 동의 → 전략 생성까지의 플로우
```

---

## 8. 법적/정책 요구사항

### 8.1 면책 문안 (기본 템플릿)

```
⚠️ 중요 공지

이 전략은 StockVision이 제공하는 자동매매 규칙 예시입니다.
과거 데이터를 기반한 백테스팅 결과이며 향후 수익을 보장하지 않습니다.

본 전략의 사용에 따른 모든 투자 결정의 책임은 사용자에게 있으며,
StockVision은 손실에 대해 책임지지 않습니다.

투자에 앞서 충분한 검토와 필요시 전문가 상담을 권고합니다.
```

### 8.2 정책

1. **템플릿 게시 승인 절차**
   - 운영팀 내부 검증 (백테스팅, 로직 검토)
   - 법무팀 면책 검토
   - 최종 승인자 서명 후 게시

2. **버전 관리**
   - 템플릿 수정 시 마이너/메이저 버전 업데이트
   - 이전 버전은 아카이브 (사용자 추적성)

3. **사용 통계**
   - 활성 사용자 수 추적
   - 템플릿별 평균 수익률 / 손실률 집계
   - 분기별 성과 리포트

4. **사용자 신청 템플릿 (향후)**
   - Phase 4에서 사용자가 검증된 전략을 템플릿으로 등록 가능
   - "커뮤니티 템플릿" 섹션으로 분리 (면책 강화)

---

## 9. 미결 사항

### 9.1 설계 결정 대기

1. **템플릿 커뮤니티 공유 (향후 페이즈)**
   - 사용자가 자신의 전략을 템플릿으로 등록 가능?
   - 검증 절차는?
   - **결정**: Phase 4+로 미룸. 현재는 운영자만.

2. **다국어 지원**
   - 초기: 한국어만
   - 향후: 영문 번역?
   - **결정**: MVP는 한국어만. 국제화 고려는 추후.

3. **템플릿 AI 추천**
   - 사용자 포트폴리오 분석 후 적합한 템플릿 추천?
   - **결정**: Phase 5 고급 기능. MVP는 수동 필터/정렬만.

4. **판매 시장 (마켓플레이스)**
   - 전문가 또는 사용자가 검증된 전략을 판매?
   - 수익 배분 방식?
   - **결정**: Phase 4+로 미룸. 현재는 무료 템플릿만.

### 9.2 구현 체크리스트

- [ ] StrategyTemplate DB 스키마 정의 및 마이그레이션
- [ ] 초기 5개 템플릿 데이터 생성 (백테스팅 결과 포함)
- [ ] TemplateManager 서비스 구현
- [ ] API 엔드포인트 구현 (CRUD, apply)
- [ ] React 컴포넌트 (갤러리, 상세, 적용)
- [ ] 면책 모달 UI
- [ ] AutoTradingRule에 created_from_template_id 추가
- [ ] 사용 통계 추적 기능
- [ ] E2E 테스트 (템플릿 선택 → 전략 생성 → 활성화)
- [ ] 법무팀 면책 검토 및 확정
- [ ] 운영 매뉴얼 작성

### 9.3 이전 단계 의존성

- strategy-builder 스펙 확정 및 기본 구현
- AutoTradingRule 모델 구조 안정화
- BacktestResult 정확성 검증

---

## 10. 일정 및 우선순위

| 단계 | 항목 | 기한 | 담당 |
|------|------|------|------|
| Phase 3.1 | 초기 5개 템플릿 설계 및 백테스팅 | 2026-03-15 | 운영팀 |
| Phase 3.2 | 백엔드 구현 (DB + API) | 2026-03-31 | Backend |
| Phase 3.3 | 프론트엔드 구현 (갤러리 + 상세) | 2026-04-15 | Frontend |
| Phase 3.4 | 테스트 및 품질 검증 | 2026-04-30 | QA |
| Phase 3.5 | 배포 및 모니터링 | 2026-05-15 | DevOps |

---

## 11. 참고 자료

### 기존 코드 위치

| 영역 | 경로 |
|------|------|
| 자동매매 규칙 모델 | `backend/app/models/auto_trading.py` |
| 거래 API | `backend/app/api/trading.py` |
| Strategy Builder 스펙 | `spec/strategy-builder/spec.md` |
| StrategyBuilder 페이지 (향후) | `frontend/src/pages/StrategyBuilder.tsx` |

### 외부 참고자료

- [Pydantic: Data validation](https://docs.pydantic.dev/)
- [React Hook Form: Efficient form management](https://react-hook-form.com/)
- [Recharts: React charting library](https://recharts.org/)

### 다음 단계

1. **plan.md 작성**: 구현 단계별 세부 계획
2. **초기 5개 템플릿 백테스팅**: 통계 확정
3. **법무팀 면책 검토**: 최종 문안 확정
4. **개발팀 킥오프**: 백엔드 → 프론트엔드 → 테스트 순서

---

**문서 이력**
- 2026-03-04: 초안 작성 (명세만, 구현 아님)
