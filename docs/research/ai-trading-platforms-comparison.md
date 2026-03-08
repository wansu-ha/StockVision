# AI/LLM 기반 자동매매 서비스 비교 분석

> 조사일: 2026-03-08
> 목적: "편의성 vs 사용자 판단" 경계를 기존 제품들이 어떻게 처리하는지 파악

---

## 1. 비교 총괄표

| 항목 | Composer.trade | QuantConnect | Alpaca | TradeGPT/GPTrader | Stoic AI | 핀트 (Fint) | QRAFT | OpenBB |
|------|---------------|-------------|--------|-------------------|---------|------------|-------|--------|
| **유형** | 노코드 자동매매 플랫폼 | 알고리즘 개발 플랫폼 | API 브로커 (인프라) | GPT 기반 매매봇 | 자동 크립토 봇 | 투자일임 (로보어드바이저) | AI ETF/기관 솔루션 | 오픈소스 금융 분석 |
| **플랫폼 제공물** | 전략 빌더, 백테스팅, 자동 실행, AI 전략 생성 | IDE, 데이터, 백테스팅, 라이브 트레이딩 서버, AI 어시스턴트(Mia) | 브로커리지 API, 시장 데이터, MCP 서버 | 차트 분석, 매매 시그널, 자동 실행 | 200+ 서브전략, 자동 리밸런싱, 리스크 관리 | AI엔진(ISAAC), 1:1 맞춤 포트폴리오, 자동매매/리밸런싱 | AI ETF 운용, 주문집행(AXE), 리스크 인디케이터 | AI Copilot, 데이터 플랫폼(ODP), MCP 서버 |
| **사용자 결정 영역** | 전략 로직 설계/선택, 자산 선택, 파라미터 조정 | 알고리즘 전체 설계, ML 모델 선택/학습, 매매 로직 | 전략 전체 (API만 제공), 실행 로직 | 분석 참고 후 수동 판단 (또는 자동 위임) | 전략 선택 (3종), 투자금 설정 | 투자성향 설정, 전략 유형 선택 (AI/성장/배당 등) | ETF 매수 판단 (개인), 기관은 위탁 | 분석/리서치 판단 전체 (매매 기능 없음) |
| **안전/리스크 관리** | 네이티브 서킷브레이커 없음 (Trade Conductor 써드파티로 보완) | 사용자 직접 구현 (프레임워크 제공) | 사용자 직접 구현 | 플랫폼마다 상이 (대부분 미흡) | 포지션 한도 3%, BTC 20%, 서브전략 클러스터 40% 상한, 자동 스톱로스 | 금융위 감독, 코스콤 검증, AI 자동 리밸런싱 | 금융위 감독, AI 리스크 인디케이터 | 해당 없음 (분석 전용) |
| **커스텀 모델 지원** | X (불가) | O (TensorFlow, PyTorch, scikit-learn 등, 외부 학습 모델 로드 가능) | O (API 기반, 어떤 모델이든 연결 가능) | 일부 (GPTrader: 멀티 LLM 선택) | X (불가, 자체 전략만) | X (불가) | X (자체 모델만) | O (Bring Your Own LLM, 오픈소스) |
| **가격** | $5~40/월 | 무료~$40/월 + 라이브서버 추가비용 | 무료 (커미션 0, 데이터 유료) | 무료~유료 (앱마다 상이) | $9/월~ 또는 자산의 ~5%/년 | 수익의 9.5% 또는 잔고의 연 0.38~1.18% | ETF 운용보수 (일반 ETF 수준) | 무료 (오픈소스) + Enterprise 유료 |
| **핵심 차별점** | 자연어 → 전략 변환, 노코드 | 오픈소스 LEAN 엔진, 기관급 데이터, 완전한 자유도 | 브로커+인프라 특화, MCP로 AI 에이전트 연결 | LLM 기반 분석/시그널 | 완전 자동, 헤지펀드팀 운영, 크립토 특화 | 한국 시장 1위, 제도권 투자일임, 증권사 앱 연동 | 세계 최초 AI ETF, 기관 솔루션 | 오픈소스, BYOLLM, 50k+ GitHub stars |

---

## 2. 서비스별 상세 분석

### 2.1 Composer.trade — AI 노코드 전략 빌더

**편의성 제공:**
- 자연어 프롬프트로 전략 생성 ("Trade with AI" 기능, 2025.10 출시)
- 노코드 비주얼 에디터로 "symphony"(전략) 조합
- 백테스팅 + 자동 실행 통합
- 커뮤니티 사전 구축 전략 제공

**사용자 판단 영역:**
- 어떤 전략을 사용할지 선택
- 전략 로직의 파라미터 및 조건 수정
- 언제 전략을 활성화/비활성화할지

**안전/리스크:**
- **주목할 점: 네이티브 서킷브레이커/리스크 관리 기능이 없음**
- Trade Conductor라는 써드파티가 이 간극을 메우고 있음 (자동 청산, 트레일링 스톱, 2008/2020/2022 시나리오 백테스트)
- 옵션 거래 리스크 고지 제공

**시사점:** 전략 생성의 편의성은 극대화했지만, 안전장치는 사용자 책임으로 남겨둠. StockVision에서 참고할 반면교사.

---

### 2.2 QuantConnect — 알고리즘 개발 플랫폼

**편의성 제공:**
- 클라우드 IDE + 리서치 환경
- 기관급 데이터 (375,000+ 라이브 전략 배포 이력)
- AI 어시스턴트 Mia (문서 900페이지 학습, 전략 구현 지원)
- 라이브 트레이딩 서버 (코로케이션)

**사용자 판단 영역:**
- 알고리즘 설계 전체 (완전한 자유도)
- ML 모델 선택, 학습, 배포
- 리스크 관리 로직 직접 구현

**커스텀 모델:**
- TensorFlow, PyTorch, scikit-learn, Keras 등 지원
- Object Store를 통해 외부 학습 모델 로드 가능
- REST 인터페이스로 외부 모델 호출 가능
- 리서치 노트북에서 학습 → 알고리즘으로 임포트

**시사점:** "인프라는 우리가, 전략은 당신이" 모델의 정석. 가장 높은 자유도를 제공하지만 진입장벽도 높음.

---

### 2.3 Alpaca — API-First 브로커

**편의성 제공:**
- 브로커리지 API (주식/옵션/크립토)
- MCP 서버 → ChatGPT, Claude, Cursor 등 AI 에이전트에서 직접 매매
- OpenAI ChatGPT 공식 통합 (시장 데이터 조회)
- 커미션 0, 공매도 대여비 0 (ETB)

**사용자 판단 영역:**
- 전략의 모든 것 (Alpaca는 순수 인프라)
- AI 모델 선택 및 연결
- 리스크 관리 로직

**커스텀 모델:**
- API 기반이므로 어떤 모델이든 연결 가능
- PredictNow.ai, Tradetron 등 써드파티 ML 플랫폼 연동

**시사점:** 브로커로서 철저하게 "파이프" 역할. MCP 서버 접근 방식은 AI 에이전트 시대에 적합한 인프라 설계.

---

### 2.4 TradeGPT / GPTrader — GPT 기반 매매 도구

**편의성 제공:**
- GPT-4 아키텍처 기반 차트 분석, 매매 시그널
- 자연어로 전략 설명 → 실행
- 기술적 분석, 센티먼트, 뉴스 컨텍스트 통합

**사용자 판단 영역:**
- GPTrader: "co-pilot" 모델 — 분석은 AI, 최종 판단은 사용자
- 일부 자동 실행 모드도 있지만 권장은 하이브리드

**커스텀 모델:**
- GPTrader: 멀티 LLM 선택 가능 (GPT, Claude, Gemini 등)
- 오픈소스 TradingAgents: 멀티 프로바이더 지원

**안전/리스크:**
- 대부분 "의사결정 지원 도구"로 포지셔닝, 자동 리스크 관리 미흡
- 앱 품질 편차가 큼 (iOS 앱 리뷰에서 과금 이슈 보고)

**시사점:** LLM을 매매에 직접 연결하는 가장 직접적인 시도. "co-pilot vs autopilot" 경계가 핵심 설계 과제.

---

### 2.5 Stoic AI — 크립토 자동매매 봇

**편의성 제공:**
- 완전 자동 매매 (설정 후 방치)
- 200+ 서브전략 동적 가중치 조절
- 시간당 리밸런싱
- 앱 기반 간편 설정

**사용자 판단 영역:**
- 전략 3가지 중 선택 (Long Only / Meta / Fixed Income)
- 투자금 설정
- 성과 모니터링 후 전략 변경

**안전/리스크:**
- 포지션 한도: 단일 자산 3% (BTC 예외 20%)
- 서브전략 클러스터 40% 상한
- 자동 스톱로스, 다이내믹 포지션 사이징
- 출금 권한 없는 API 키만 사용

**시사점:** "사용자 판단 최소화" 모델의 극단. 사용자는 전략 유형만 선택하고 나머지는 완전 위임. 리스크 관리는 플랫폼이 전담.

---

### 2.6 핀트 (Fint) — 한국 AI 투자일임

**편의성 제공:**
- AI엔진 ISAAC이 종목 선정부터 매매까지 전 과정 자동 처리
- 투자자 성향 기반 1:1 맞춤 포트폴리오
- KB증권 마블 앱 연동 (별도 앱 없이 사용 가능)
- 국내주식, 미국주식, ETF, 연금저축, IRP 대응

**사용자 판단 영역:**
- 투자 성향 설정 (AI형/가치형/성장형/배당형)
- 주식/채권 비율 설정
- 전략 유형 선택
- 투자금 설정

**안전/리스크:**
- 금융위원회/금감원 관리 감독
- 코스콤 로보어드바이저 테스트베드 검증
- 투자일임업 라이선스 보유

**시사점:** 한국 규제 환경에서의 정석적 접근. 사용자 판단은 "성향"과 "방향" 수준으로 제한, 세부 매매는 완전 위임. 제도적 안전장치(금융위 감독)가 핵심.

---

### 2.7 QRAFT Technologies — AI ETF/기관 솔루션

**편의성 제공:**
- AI ETF 상장 (NYSE, $QRFT 모닝스타 5성)
- AI 주문집행시스템 AXE (강화학습 기반)
- AI 리스크 인디케이터 (주간 리스크 예측)

**사용자 판단 영역:**
- 개인: ETF 매수/매도 판단
- 기관: 운용 위탁 결정, AXE 도입 결정

**시사점:** B2B/기관 특화 모델. 개인에게는 ETF라는 "패키지"로 제공, 기관에게는 주문집행/리스크 인프라로 제공. 소프트뱅크 1700억 투자 유치.

---

### 2.8 OpenBB — 오픈소스 금융 분석 플랫폼

**편의성 제공:**
- AI Copilot (에이전틱 워크플로우)
- Open Data Platform (ODP) — "connect once, consume everywhere"
- MCP 서버 (AI 에이전트용)
- 워크스페이스 기반 대시보드

**사용자 판단 영역:**
- 모든 투자 판단 (분석 도구만 제공, 매매 기능 없음)
- LLM 모델 선택 및 커스터마이징

**커스텀 모델:**
- **Bring Your Own LLM 명시적 지원**
- 오픈소스 리포지토리로 자체 Copilot 통합 가능
- 기업 내부 데이터 기반 파인튜닝/RAG 지원
- LangChain 등 프레임워크와 연동

**시사점:** "분석은 우리가 도와주지만 판단과 실행은 당신 몫" 모델. BYOLLM이 가장 성숙한 플랫폼. 50k+ GitHub stars.

---

## 3. 한국 로보어드바이저 시장 추가 정보

| 서비스 | 최소 투자금 | 수수료 | 특징 |
|--------|-----------|--------|------|
| **핀트** | 20만원 | 수익의 9.5% | 시장점유율 1위, 다양한 전략 |
| **파운트** | 10만원 | 수익의 15% | 다수 알고리즘, ETF 중심 |
| **콴텍** | - | - | 1년 수익률 35%+ (2025.4 기준) |
| **에임** | 높음 | - | 전문 자산관리 |

한국 시장 특성:
- 금융위원회 투자일임업 라이선스 필수
- 코스콤 로보어드바이저 테스트베드 검증 필수
- 퇴직연금(IRP) 혁신금융서비스 지정으로 시장 확대 중
- 사용자 판단 영역이 매우 제한적 (성향 설정 수준)

---

## 4. 신규 진입자 / 오픈소스 LLM 트레이딩 프레임워크

| 프로젝트 | 특징 | 커스텀 모델 |
|---------|------|------------|
| **TradingAgents** (UCLA/MIT) | 멀티에이전트 (분석가/트레이더/리스크팀 역할 분담), v0.2.0 멀티 LLM 지원 | GPT, Gemini, Claude, Grok 선택 가능 |
| **LLM-TradeBot** | 2단계 심볼 선택, 리스크 감사 에이전트, 4층 전략 필터 | LLM Provider API 키 설정 |
| **FinMem** | 계층적 메모리 + 캐릭터 설계, HuggingFace 모델 지원 | 로컬/클라우드 LLM 자유 선택 |
| **AI-Trader** (HKUDS) | 실시간 벤치마킹, $10k 시작, NASDAQ100/SSE50/크립토 | JSON 설정으로 모델 변경 |
| **DeepSeek Trading Bot** | 풀 백테스팅, Hyperliquid 라이브 연결 | DeepSeek 기반 |

---

## 5. "편의성 vs 사용자 판단" 경계 패턴 분석

### 패턴 A: 완전 위임 (Stoic AI, 핀트, QRAFT ETF)
- 사용자는 전략 유형/투자성향만 선택
- 종목 선정, 매수/매도 시점, 리밸런싱은 전부 AI가 처리
- 리스크 관리도 플랫폼이 전담
- **장점:** 진입장벽 최저, 감정 개입 차단
- **단점:** 사용자의 시장 인사이트 반영 불가, 블랙박스

### 패턴 B: AI 보조 전략 빌더 (Composer, GPTrader)
- AI가 전략을 "제안"하지만 사용자가 확인/수정 후 실행
- 노코드/자연어로 진입장벽 낮춤
- 실행은 자동이지만 전략 설계는 사용자 참여
- **장점:** 사용자 의도 반영 + 실행 편의성
- **단점:** Composer 사례처럼 리스크 관리가 빠질 수 있음

### 패턴 C: 인프라 제공 (QuantConnect, Alpaca, OpenBB)
- 데이터, 실행 인프라, AI 도구를 제공
- 전략, 모델, 리스크 관리는 전부 사용자 몫
- 커스텀 모델 지원 가장 충실
- **장점:** 최대 자유도, 전문가에게 최적
- **단점:** 진입장벽 높음, 리스크 관리 실수 가능

### 패턴 D: LLM Co-pilot (TradingAgents, OpenBB Copilot)
- LLM이 분석/추천하되 최종 판단은 사용자
- "AI 트레이딩 펌"을 시뮬레이션 (애널리스트/트레이더/리스크팀 역할 분담)
- **장점:** AI의 분석력 + 사용자의 최종 통제권
- **단점:** 아직 실험적, 프로덕션 검증 부족

---

## 6. StockVision을 위한 핵심 인사이트

### 6.1 리스크 관리는 선택이 아닌 필수
- Composer의 사례: 전략 빌더는 강력하지만 리스크 관리 부재로 써드파티(Trade Conductor)가 등장
- Stoic AI의 사례: 포지션 한도, 클러스터 상한, 자동 스톱로스 등 체계적 리스크 관리가 차별점
- **권장:** StockVision의 가상 거래 시스템에도 기본 리스크 관리 레이어 (최대 손실률, 포지션 한도, 일일 거래 한도 등) 내장

### 6.2 "편의성 vs 판단" 스펙트럼에서의 포지셔닝
- 완전 위임 (핀트/Stoic) ← → 완전 자유 (QuantConnect/Alpaca)
- StockVision은 "AI 보조 전략 빌더 + Co-pilot" (패턴 B+D) 영역이 적합할 수 있음
- AI가 분석/예측/전략 제안을 하되, 최종 매매 결정은 사용자가 확인

### 6.3 커스텀 모델 지원은 상위 사용자를 위한 차별점
- OpenBB의 BYOLLM, QuantConnect의 ML 프레임워크가 모범 사례
- StockVision은 현재 scikit-learn/TensorFlow 기반이므로, 향후 사용자 모델 업로드/교체 기능은 고급 기능으로 고려 가능

### 6.4 한국 시장 진출 시 규제 고려
- 투자일임업 라이선스 필수
- 코스콤 테스트베드 검증 필요
- 가상 거래/시뮬레이션은 규제 대상이 아니므로, "교육/시뮬레이션" 포지셔닝이 초기 전략으로 유효

### 6.5 MCP (Model Context Protocol) 트렌드
- Alpaca가 MCP 서버로 AI 에이전트(ChatGPT, Claude 등)와 직접 연결
- OpenBB도 MCP 서버로 AI 에이전트에 데이터 제공
- 향후 StockVision도 MCP 서버 제공을 고려하면 AI 에이전트 생태계와 연결 가능

---

## Sources

- [Composer.trade](https://www.composer.trade/)
- [Composer Trade with AI](https://www.composer.trade/ai)
- [Composer Yahoo Finance](https://finance.yahoo.com/news/composer-supercharges-investing-platform-trade-120000006.html)
- [Trade Conductor](https://tradeconductor.com/)
- [QuantConnect](https://www.quantconnect.com/)
- [QuantConnect Pricing](https://www.quantconnect.com/pricing/)
- [QuantConnect ML Docs](https://www.quantconnect.com/docs/v2/writing-algorithms/machine-learning/key-concepts)
- [QuantConnect LEAN Engine](https://www.lean.io/)
- [Alpaca Markets](https://alpaca.markets/)
- [Alpaca Algo Trading](https://alpaca.markets/algotrading)
- [Alpaca 2025 Review](https://alpaca.markets/blog/alpacas-2025-in-review/)
- [Alpaca OpenAI Integration](https://alpaca.markets/blog/openai-integrates-alpacas-market-data-functionality-as-part-of-chatgpt-for-financial-services/)
- [TradeGPT - WunderTrading](https://wundertrading.com/journal/en/reviews/article/what-is-tradegpt)
- [GPTrader](https://gptrader.app/)
- [TradeGPT Yahoo Finance](https://finance.yahoo.com/news/discover-future-trading-tradegpt-trans-124500600.html)
- [Stoic AI](https://stoic.ai/)
- [Stoic AI Meta Strategy](https://stoic.ai/meta)
- [핀트 Fint](https://www.fint.co.kr/)
- [핀트 KB증권 연동](https://platum.kr/archives/270700)
- [QRAFT Technologies](https://www.qraftec.com)
- [QRAFT AI 주문집행](https://medium.com/qraft/ai-%EC%A3%BC%EB%AC%B8%EC%A7%91%ED%96%89-cb05da2dcea1)
- [OpenBB](https://openbb.co/)
- [OpenBB Workspace](https://openbb.co/products/workspace/)
- [OpenBB AI Blog](https://openbb.co/blog/role-of-ai-and-openbb-in-future-of-investment-research)
- [OpenBB GitHub](https://github.com/OpenBB-finance/OpenBB)
- [TradingAgents Framework](https://tradingagents-ai.github.io/)
- [TradingAgents GitHub](https://github.com/TauricResearch/TradingAgents)
- [LLM Trading Bots Comparison - FlowHunt](https://www.flowhunt.io/blog/llm-trading-bots-comparison/)
- [FinMem GitHub](https://github.com/pipiku915/FinMem-LLM-StockTrading)
- [AI-Trader GitHub](https://github.com/HKUDS/AI-Trader)
- [한국 로보어드바이저 비교 - AI타임스](https://www.aitimes.com/news/articleView.html?idxno=136379)
- [한국 로보어드바이저 수익률 - 한국경제](https://www.hankyung.com/article/2025040635421)
- [Benzinga Best AI Trading Bots 2026](https://www.benzinga.com/money/best-ai-stock-trading-bots-software)
