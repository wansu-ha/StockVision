> 작성일: 2026-03-10 | 상태: 구현 완료 | Branch: feat/engine-live-execution

# 전략 엔진 E2E 실행 — Spec

## 목표

키움 모의서버 환경에서 전략 엔진이 **실시간 시세 수신 → 지표 계산 → 규칙 평가 → 주문 실행**까지
End-to-End로 동작하게 만든다.

현재 파이프라인의 4개 갭을 모두 해소하여, 프론트엔드에서 등록한 매매 규칙이
모의 거래로 실제 체결되는 것을 확인한다.

## 현황 분석

```
WS 시세 ──→ BarBuilder ──→ Evaluator ──→ Executor ──→ Broker
  ✅           ⚠️             ❌            ✅           ✅

✅ = 구현+동작  ⚠️ = 구현됐으나 갭 있음  ❌ = 핵심 누락
```

## 문제 정의 (4개)

### P1. WS 실시간 시세 파서 ✅ 해결됨

- **문제**: `_handle_message`가 `stk_cd`, `cur_prc` 평문 키를 기대했으나,
  실제 WS는 `{"trnm":"REAL","data":[{"item":"종목","values":{"10":"+72300",...}}]}` 형식
- **해결**: 파서를 `trnm=="REAL"` 분기 + 숫자 키 매핑으로 교체 완료
- **파일**: `local_server/broker/kiwoom/ws.py` L158-216

### P2. 지표 계산 누락 ❌ 핵심 갭

- **문제**: Evaluator가 `market_data["indicators"]["rsi_14"]` 등을 참조하나,
  BarBuilder의 `get_latest()`는 `{price, volume, timestamp}`만 반환.
  **지표를 계산하는 코드가 어디에도 없다.**
- **영향**: RSI, 볼린저, 골든크로스 등 기술적 지표 규칙이 전부 `None` 평가 → 매매 불발
- **요구 데이터**:

| 지표 키 | 설명 | 필요 기간 |
|---------|------|----------|
| `rsi_{N}` | RSI(N) | N+1일 종가 |
| `ma_{N}` | 단순이동평균(N) | N일 종가 |
| `ema_{N}` | 지수이동평균(N) | N×2일 종가 |
| `bb_upper_{N}`, `bb_lower_{N}` | 볼린저밴드(N) | N일 종가 |
| `macd`, `macd_signal` | MACD(12,26,9) | 35일 종가 |
| `avg_volume_{N}` | 평균거래량(N) | N일 거래량 |

- **설계 결정**: 사용자의 규칙(RSI(14), 볼린저(20))은 **일봉 기준** 지표.
  1분봉 RSI(14)와 일봉 RSI(14)는 완전히 다른 값.
  → **일봉 기반 지표 계산** 필요

### P3. 규칙 동기화 E2E 미검증

- **문제**: `POST /api/rules/sync` 엔드포인트, heartbeat 자동동기화 모두 코드 존재하나
  실제 클라우드↔로컬 간 E2E 동작 미확인
- **잠재 버그**: heartbeat의 `rules_version` 비교 시 타입 불일치 (cloud: int, local: str|None)
- **영향**: 프론트엔드에서 규칙 생성 → 엔진에 반영되지 않을 수 있음

### P4. 엔진 E2E 실행 검증

- **문제**: P2+P3 해결 후에도, 전체 파이프라인을 실제로 돌려서 모의 주문이
  나가는지 확인한 적이 없음
- **확인 필요**: 엔진 시작 → WS 구독 → 시세 수신 → 지표 주입 → 규칙 평가 →
  주문 실행 → 체결 로그

## 요구사항

### 기능적 요구사항

1. **지표 제공자 (IndicatorProvider)**
   - 엔진 시작 시 활성 규칙의 종목별 일봉 지표를 계산/캐싱
   - 평가 주기(1분)마다 `market_data["indicators"]`에 주입
   - 로컬에서 직접 계산 (pandas + yfinance) — 시세 재배포 회피
   - 일봉 데이터 소스: yfinance (60일, 한국 종목 `.KS`/`.KQ` 형식)

2. **규칙 동기화 검증**
   - heartbeat 버전 비교 타입 수정 (int 통일)
   - 프론트엔드 규칙 생성 → 로컬 엔진 반영까지 E2E 확인

3. **E2E 실행 흐름**
   - 엔진 시작 → WS 구독 → 규칙 평가 → 모의 주문 체결
   - 체결 로그가 프론트엔드에 표시

### 비기능적 요구사항

- 지표 계산은 엔진 평가 루프를 1초 이상 블로킹하지 않아야 함
- 일봉 데이터는 1일 1회 갱신이면 충분 (장중 변하지 않음)
- cloud 서버 다운 시에도 캐시된 지표로 동작

## 수용 기준

- [ ] P1: WS 파서가 실시간 시세를 QuoteEvent로 변환 (단위 테스트 통과) ✅
- [ ] P2: `evaluate_all()` 시 `market_data["indicators"]`에 rsi_14, bb_lower_20 등 값이 존재
- [ ] P3: 프론트엔드에서 규칙 생성 후 30초 내 로컬 엔진 rules 목록에 반영
- [ ] P4: 모의서버에서 매수 주문이 체결되고 `logs.db`에 fill 로그 기록

## 범위

### 포함
- 일봉 기반 지표 계산 모듈 (`local_server/engine/indicator_provider.py`)
- BarBuilder → Evaluator 사이 지표 주입 로직
- heartbeat 버전 비교 버그 수정
- E2E 수동 검증 (모의서버 주문 체결)

### 미포함
- 1분봉 기반 실시간 지표 (향후 확장)
- 자동화된 E2E 테스트 스위트
- 프론트엔드 UI 변경
- 실전 서버 테스트

## 참고 코드 경로

| 모듈 | 경로 | 역할 |
|------|------|------|
| WS 클라이언트 | `local_server/broker/kiwoom/ws.py` | 실시간 시세 수신+파싱 |
| BarBuilder | `local_server/engine/bar_builder.py` | 틱→1분봉, latest 반환 |
| Evaluator | `local_server/engine/evaluator.py` | DSL/JSON 규칙 평가 |
| Engine | `local_server/engine/engine.py` | 평가 루프 오케스트레이터 |
| Executor | `local_server/engine/executor.py` | 주문 실행 + 안전장치 |
| Cloud 지표 계산 | `cloud_server/services/context_service.py` | RSI/MACD/볼린저 함수 |
| 규칙 캐시 | `local_server/storage/rules_cache.py` | JSON 파일 캐시 |
| Heartbeat | `local_server/cloud/heartbeat.py` | 자동 동기화 |
