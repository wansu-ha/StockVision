# 아키텍처 리뷰 결과 — v3 개발 계획서 + 핵심 Spec

> 작성일: 2026-03-17 | 리뷰어: Opus (Architecture Reviewer)
> 대상: `docs/development-plan-v3.md`, `docs/architecture.md`, `spec/relay-infra/spec.md`, `spec/engine-live-execution/spec.md`, `spec/chart-timeframe/spec.md`

---

## 1. 3프로세스 정합성

**판정: ✅ 통과**

모든 spec이 클라우드/로컬/프론트 3프로세스 경계를 올바르게 준수한다.

| Spec | 클라우드 | 로컬 | 프론트 | 정합성 |
|------|---------|------|--------|--------|
| engine-live-execution | 규칙 저장/sync | 지표 계산+엔진 실행 | 규칙 CRUD UI | OK |
| chart-timeframe | 일/주/월봉 API | 분봉 API (사용자 키) | 해상도 UI 분기 | OK |
| relay-infra | WS relay hub | WS 클라이언트 | 원격 디바이스 WS | OK |

**근거**:
- engine-live-execution: 지표 계산이 로컬 서버에서 수행되며, 클라우드는 규칙 저장소 역할만 담당. 매매 판단이 로컬에 격리되어 법적 포지션(시스템매매) 유지.
- chart-timeframe: 분봉은 로컬(사용자 키), 일봉 이상은 클라우드(yfinance DB). 법적 제약에 맞게 데이터 소스가 분리됨.
- relay-infra: 클라우드가 relay hub(라우팅만), 금융 데이터는 E2E 암호화로 클라우드가 복호화 불가. 아키텍처 원칙("클라우드에 금융정보 미보유") 준수.

---

## 2. 데이터 흐름 + 법적 제약 준수

**판정: ⚠️ 주의 (1건)**

### ✅ 시세 재배포 금지 준수
- chart-timeframe: 분봉은 로컬 서버가 사용자 본인 KIS 키로 조회. 클라우드 분봉 수집/재배포를 명시적으로 제외.
- engine-live-execution: IndicatorProvider가 yfinance로 일봉을 **로컬에서 직접** 조회하여 지표 계산. 클라우드 시세를 사용자에게 재배포하지 않음.
- relay-infra: 금융 데이터(잔고, 손익, 체결)는 E2E 암호화. 클라우드가 열어볼 수 없는 구조.

### ⚠️ relay-infra: `encrypted_for` 구조의 데이터 흐름 비용

relay-infra spec 5.2에서 로컬 서버가 상태를 보낼 때 "등록된 디바이스 수만큼 암호화 블록을 생성"하는 설계는 정확하나, 데이터 흐름 관점에서 주의사항이 있다:

- 로컬 서버가 5대 디바이스의 E2E 키를 전부 보유해야 한다. 디바이스 등록/해제 시 키 동기화 흐름이 spec에 명시되지 않았다.
- **권고**: auth-extension spec에서 디바이스 키 등록 시 로컬 서버로의 키 전파 경로를 명확히 정의할 것.

---

## 3. 의존성 순서 (T1 → T2 → T3)

**판정: ✅ 통과**

### 의존 그래프 검증

```
T1-1 (engine-live) ─────────────────── 독립
T1-2 (dsl-parser) ──────────────────── 독립
T1-3 (chart-timeframe backend) ─────── 독립
T1-4 (chart-timeframe frontend) ─────← T1-3
T1-5 (local-resilience R1~R3,R5) ──── 독립

T2 relay-infra Step 1~4 ───────────← (T1-5 R3 SyncQueue 권장)
T2 auth-extension ──────────────────── relay Step 5 전 완료 필요
T2 relay-infra Step 5~8 ───────────← auth-extension
T2 R4 (heartbeat WS ack) ──────────← relay-infra
T2 remote-ops ──────────────────────← relay-infra + auth-extension
```

- **순환 의존 없음**: 모든 화살표가 한 방향. T1→T2→T3 순서가 기술적으로 올바름.
- T1 항목 간 병렬 가능. T1-4만 T1-3에 순차 의존.
- T2 내부에서 relay-infra → auth-extension → relay Step 5~8 → remote-ops 순서가 명확.

**한 가지 확인 사항**: T1-5의 R3(SyncQueue 연동)이 완료되지 않아도 relay-infra 착수는 가능하나, SyncQueue가 relay-infra의 오프라인 명령 큐(spec 5.5)와 유사한 패턴이므로 T1-5를 먼저 완료하면 코드 재사용 가능성이 높아진다.

---

## 4. 파일 충돌

**판정: ✅ 통과 (매트릭스 이미 존재)**

development-plan-v3.md 10장에 파일 충돌 매트릭스가 이미 정의되어 있으며 순서가 명시됨. 추가 발견:

| 파일 | 충돌 가능 Spec | 위험도 |
|------|--------------|--------|
| `local_server/cloud/ws_relay_client.py` | relay-infra(재작성) + R4(heartbeat WS ack) | 매트릭스에 이미 포함 ✅ |
| `frontend/src/hooks/useStockData.ts` | chart-timeframe(데이터 소스 분기) + engine-live(규칙 sync UI) | 낮음 (다른 부분 수정) |
| `local_server/engine/engine.py` | engine-live(IndicatorProvider 주입) + local-resilience(R5 LimitChecker) | **⚠️ 매트릭스에 누락** |

**권고**: `engine.py`를 충돌 매트릭스에 추가. T1-1(engine-live) → T1-5(R5) 순서 명시 필요.

---

## 5. 확장성 (v2 기능 호환)

**판정: ✅ 통과**

| v2 기능 | 차단 요소 | 판정 |
|---------|----------|------|
| 백테스팅 | IndicatorProvider가 순수 함수 기반 (`_calc_rsi` 등). 히스토리컬 데이터에도 동일 함수 적용 가능 | OK |
| 리밸런싱 | BrokerAdapter에 `get_positions()` 존재. 포트폴리오 레벨 로직만 추가하면 됨 | OK |
| 2FA | auth-extension에서 OAuth2 인프라 구축. 2FA는 동일 인증 레이어에 추가 가능 | OK |
| 텔레그램/Slack | relay-infra의 메시지 프로토콜이 확장 가능 (`type` 필드 자유 추가). alert 타입으로 외부 채널 전달 가능 | OK |
| BYO LLM | strategy_type 분기 구조가 이미 존재 (`"dsl"` / `"llm"`). 프로바이더 추가만 필요 | OK |

**확장을 막는 설계 없음**. 특히:
- BrokerAdapter 추상화가 복수 증권사 지원의 기반
- 메시지 프로토콜 envelope의 `v` 필드가 프로토콜 버전 관리 지원
- DSL과 LLM 전략 타입이 공통 안전장치/실행 경로를 공유하여 새 전략 타입 추가 시 최소 변경

---

## 6. 단일 장애점 (SPOF) 분석

**판정: ⚠️ 주의 (2건)**

### 6.1 클라우드 서버 SPOF — relay-infra

relay-infra에서 클라우드 서버는 relay hub 역할. 클라우드 다운 시:

| 기능 | 클라우드 다운 시 | 폴백 |
|------|----------------|------|
| 로컬 자동매매 | **계속 동작** (캐시 규칙 + KIS 직접 연결) | ✅ |
| 같은 PC 프론트엔드 | **계속 동작** (localhost 직접 연결) | ✅ |
| 원격 상태 조회 | **중단** | ❌ 폴백 없음 |
| 원격 킬스위치 | **중단** (pending 큐도 클라우드 DB) | ❌ 폴백 없음 |
| 하트비트 | WS 실패 → **HTTP 폴백** | ✅ spec에 명시 |

**핵심 판단**: 클라우드 다운 시 원격 제어가 불가하지만, **핵심 기능(자동매매)은 영향 없음**. 이것은 아키텍처 설계 의도("로컬 서버 자립 동작")와 일치.

**그러나** 원격 킬스위치의 SPOF는 위험하다. 사용자가 외출 중 긴급 상황에서 클라우드 다운이면 매매를 멈출 수 없다.

**권고**:
1. SMS/전화 기반 킬스위치 폴백 (v2) 또는
2. 로컬 서버 자체 안전장치 강화 (일일 손실 한도 초과 시 자동 정지 — 이미 safeguard.py에 부분 구현)
3. 원격 킬스위치 불가 시 "로컬 안전장치가 활성 상태"임을 명확히 사용자에게 안내

### 6.2 yfinance SPOF — engine-live-execution

IndicatorProvider가 yfinance에 100% 의존. yfinance 장애 시:

- 지표 계산 불가 → 기술적 지표 규칙 전부 `None` → 매매 불발
- "봉 데이터 부족 시 graceful 처리" 수용 기준이 있으나, 구체적 폴백이 없음

**권고**:
1. 클라우드 서버가 이미 yfinance로 일봉을 수집/저장하고 있으므로, 로컬 → 클라우드 일봉 API를 폴백 경로로 추가 (시세 재배포가 아닌 "히스토리컬 일봉 조회"는 약관 위반 여부 검토 필요)
2. 또는 KIS REST API의 일봉 조회를 폴백으로 사용 (사용자 본인 키이므로 법적 문제 없음)

---

## 7. 기술 부채 식별

**판정: ⚠️ 주의 (5건 식별)**

### 7.1 yfinance 한국 주식 KOSDAQ 미분류 — ❌ 차단급

`indicator_provider.py` L96-98:
```python
def _to_yf_ticker(symbol: str) -> str:
    if "." in symbol:
        return symbol
    return f"{symbol}.KS"  # 항상 KOSPI로 가정
```

**KOSDAQ 종목이 전부 잘못된 티커로 조회된다.** 예: 카카오게임즈(293490)는 `.KQ`여야 하나 `.KS`로 요청됨. yfinance가 데이터를 반환하지 않아 해당 종목의 지표가 전부 `None`이 된다.

**수정안**: 클라우드의 StockMaster(종목 메타데이터)에 exchange 정보가 있으므로, IndicatorProvider 초기화 시 exchange 매핑을 전달하거나, KIS REST 일봉 API를 대안으로 사용.

### 7.2 하드코딩된 공휴일 — ⚠️ 주의

development-plan-v3.md A8의 Q5에서 "장 상태 공휴일 (useMarketContext 활용)" 이 미구현으로 추적 중. 현재 코드에 공휴일 처리 로직이 없으며, `cloud_server/services/stock_service.py`와 `briefing_service.py`에서만 부분적으로 참조.

**영향**: 공휴일에 엔진이 시세를 기다리며 대기하거나, 불필요한 API 호출 발생 가능.

### 7.3 yfinance Rate Limiting — ⚠️ 주의

IndicatorProvider가 종목별 순차 `yf.download()` 호출. 활성 규칙이 20종목이면 20번 호출. yfinance는 Yahoo Finance를 스크래핑하므로:
- Rate limit에 걸릴 수 있음
- 응답 시간이 불안정 (2~10초/종목)
- `yf.download(tickers="SYM1 SYM2", ...)`로 배치 요청하면 호출 수 감소 가능

### 7.4 relay-infra: heartbeat_ack 미처리 — ⚠️ 주의

`ws_relay_client.py` L189-193에서 `heartbeat_ack` 수신 시 "로깅만" 하고 버전 체크를 하지 않는다. 주석에 "heartbeat 모듈에 위임" 가능성을 언급하나, 실제 연결이 없음. 현재는 HTTP heartbeat가 병행 동작하므로 문제 없지만, WS 전환 완료 후 HTTP를 제거하면 버전 동기화가 깨진다.

**이것은 relay-infra Step 3 (Heartbeat WS 전환)에서 해소 예정이므로 추적만 하면 됨.**

### 7.5 E2E 암호화 키 관리 미명세 — ⚠️ 주의

relay-infra spec에서 "디바이스별 키, 페어링 시 생성"이라고 했으나:
- 키 생성 프로토콜 (ECDH? 수동 공유?)
- 키 저장 위치 (로컬: Credential Manager? 프론트: IndexedDB?)
- 키 교체/폐기 절차

이 모두 auth-extension spec에서 정의될 예정이나, auth-extension spec이 아직 작성되지 않음. relay-infra와 auth-extension이 병렬 착수 가능하다고 했으므로, **키 관리 인터페이스를 먼저 합의해야** 충돌을 방지할 수 있다.

---

## 8. 종합 판정

| 기준 | 판정 | 요약 |
|------|------|------|
| 3프로세스 정합성 | ✅ 통과 | 모든 spec이 경계를 올바르게 준수 |
| 데이터 흐름 + 법적 제약 | ✅ 통과 | 시세 재배포 금지, E2E 암호화 적절 |
| 의존성 순서 | ✅ 통과 | 순환 없음, T1→T2→T3 올바름 |
| 파일 충돌 | ✅ 통과 | 매트릭스 존재, `engine.py` 1건 추가 권고 |
| 확장성 | ✅ 통과 | v2 기능으로의 확장 경로 열려 있음 |
| 단일 장애점 | ⚠️ 주의 | 원격 킬스위치 SPOF + yfinance SPOF |
| 기술 부채 | ⚠️ 주의 | KOSDAQ 티커 오분류(차단급), 공휴일, rate limit 등 5건 |

### 차단 이슈 (구현 전 반드시 해결)

1. **KOSDAQ 종목 yfinance 티커 오분류** (7.1): IndicatorProvider가 KOSDAQ 종목 지표를 전혀 계산하지 못함. StockMaster의 exchange 필드를 활용하여 `.KS`/`.KQ` 분기 필수.

### 우선 해결 권고

2. **원격 킬스위치 SPOF 대응** (6.1): 로컬 safeguard 자동정지가 존재하더라도, 사용자 안내 문구에 "클라우드 장애 시 로컬 안전장치가 자동 보호" 명시. SMS 폴백은 v2 이후.
3. **auth-extension 키 관리 인터페이스 선정의** (7.5): relay-infra Step 6(E2E 암호화) 착수 전에 키 생성/저장/교환 프로토콜을 확정.
4. **yfinance 배치 요청** (7.3): 단순 코드 변경으로 해결 가능. T1-1 구현 시 같이 처리.
5. **engine.py 파일 충돌 매트릭스 추가** (4): development-plan-v3.md 10장에 반영.

---

## 9. 전체 평가

v3 개발 계획과 핵심 spec들은 **전반적으로 잘 설계되어 있다**. 3프로세스 아키텍처의 경계가 명확하고, 법적 제약(시세 재배포 금지, 투자자문 회피)을 구조적으로 보장하는 설계 패턴이 일관되게 적용되어 있다.

특히 우수한 점:
- relay-infra의 E2E 암호화 범위 구분 (금융 데이터 O / 시스템 상태 X)이 실용적
- chart-timeframe의 분봉(로컬) / 일봉(클라우드) 소스 분리가 법적 요건에 정확히 부합
- 오프라인 내성 설계가 전체 spec에 걸쳐 일관적 (캐시 규칙, HTTP 폴백, pending 큐)

**차단 이슈 1건(KOSDAQ 티커)만 해결하면 T1 착수 가능.**
