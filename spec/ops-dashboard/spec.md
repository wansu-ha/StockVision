# 운영 대시보드 강화 (Operations Dashboard)

> 작성일: 2026-03-12 | 상태: 구현 완료 | Phase C

## 1. 배경

현재 상태 표시는 TrafficLightStatus(3등, cloud/local/broker)와 Header 드롭다운에 분산되어 있다.
엔진 상태, 오늘의 신호/체결/오류 요약, 실행 로그 타임라인이 없어서 "지금 시스템이 안전하게 돌고 있는지" 3초 안에 파악하기 어렵다.

Phase C의 핵심 목표는 "안 보고 있어도 시스템이 안전하게 돌아간다는 확신"이며, 이 spec은 **로컬 환경에서의 운영 가시성**을 담당한다.

## 2. 목표

메인 화면에서 시스템 전체 상태를 한눈에 읽고, 실행 흐름을 시간순으로 추적할 수 있다.

## 3. 범위

### 3.1 포함

**A. 운영 패널 강화**
- 메인 헤더/ListView 상단에 운영 요약 패널 노출
- 4개 상태 (로컬 서버, 브로커, 클라우드, 엔진) + 실전/모의 모드
- 각 상태를 색상 + 텍스트로 표시 (현재는 색상만)
- 오늘의 요약: 신호 수, 체결 수, 오류 수
- 비정상 상태 시 원인 텍스트 노출

**B. 실행 로그 타임라인**
- 실행 흐름을 `Triggered → Submitted → Filled/Failed/Cancelled` 단계로 표현
- 기존 ExecutionLog 테이블을 타임라인 뷰로 확장 (테이블 뷰 유지, 타임라인 뷰 추가)
- 실패 사유, 브로커 응답, 재시도 여부 표시
- 종목 상세에서도 해당 종목의 실행 타임라인 확인 가능

### 3.2 제외

- 원격 상태 조회 (Spec 2: 원격 제어 범위)
- 킬스위치/긴급 정지 UI (Spec 2: 원격 제어 범위)
- 외부 주문 감지 표시 (Spec 3: 외부 주문 감지 범위)
- 설정 화면 제어판화 (별도 이터레이션)

## 4. 의존성

| 의존 대상 | 상태 | 비고 |
|-----------|------|------|
| Phase A (broker-auto-connect, frontend-ux-v2) | 완료 | 기존 TrafficLightStatus, Header 위에 확장 |
| System Trader Phase 1 | 완료 | candidate → intent → submitted/filled 상태 모델 존재 |
| 로그 API (`GET /api/logs`) | 완료 | log_type 필터, symbol 필터 지원 |

**선행 조건 없음 — 바로 착수 가능**

## 5. 운영 패널 설계

### 5.1 위치

ListView 상단, 기존 계좌 요약 패널 위 또는 병합.

### 5.2 표시 항목

| 항목 | 데이터 소스 | 정상 | 비정상 |
|------|------------|------|--------|
| 로컬 서버 | `localHealth.check()` | 🟢 연결됨 | 🔴 연결 불가 |
| 브로커 | `localStatus.get()` → broker | 🟢 연결됨 (모의/실전) | 🟡 미연결 / 🔴 오류 |
| 클라우드 | `cloudHealth.check()` | 🟢 정상 | 🔴 연결 불가 |
| 엔진 | `localStatus.get()` → engine | 🟢 실행 중 / 🟡 대기 | 🔴 정지 / 오류 |
| 모드 | broker 상태 내 mode | `모의투자` / `실전` | - |

### 5.3 오늘의 요약

| 지표 | 데이터 소스 | 표시 |
|------|------------|------|
| 신호 수 | `GET /api/logs?log_type=STRATEGY&date_from=today` → count | `신호 12건` |
| 체결 수 | `GET /api/logs?log_type=FILL&date_from=today` → count | `체결 3건` |
| 오류 수 | `GET /api/logs?log_type=ERROR&date_from=today` → count | `오류 0건` / 🔴 `오류 2건` |

### 5.4 비정상 상태 피드백

하나라도 비정상이면 패널 상단에 경고 배너:
- "브로커 미연결 — 설정에서 API 키를 확인하세요"
- "엔진 정지됨 — 전략 실행 버튼을 눌러 시작하세요"
- "클라우드 연결 불가 — 네트워크를 확인하세요"

## 6. 실행 로그 타임라인 설계

### 6.1 상태 단계 모델

System Trader의 OrderIntent 상태를 프론트엔드에서 시각화:

```
DETECTED → SELECTED → SUBMITTED → FILLED
                ↘ DROPPED       ↘ PARTIAL_FILLED
                ↘ BLOCKED       ↘ CANCELLED
                                ↘ REJECTED
```

### 6.2 타임라인 아이템

각 실행 이벤트를 타임라인 카드로 표시:

```
14:30:45  ● FILLED   매수 005930 삼성전자 100주 @72,500
          ├ 14:30:43 SUBMITTED → 브로커 제출
          └ 14:30:40 DETECTED  → RSI 과매도 전략

14:28:12  ✕ REJECTED  매수 035420 NAVER 50주
          ├ 14:28:10 SUBMITTED → 브로커 제출
          ├ 14:28:10 REJECTED  → 주문가격 제한 초과
          └ 14:28:08 DETECTED  → 이동평균 돌파 전략
```

### 6.3 데이터 소스

현재 로그 API 응답에서 타임라인 재구성:
- `log_type=STRATEGY` → DETECTED/SELECTED/DROPPED/BLOCKED 단계
- `log_type=ORDER` → SUBMITTED 단계
- `log_type=FILL` → FILLED/PARTIAL_FILLED/REJECTED/CANCELLED 단계

같은 `intent_id` 또는 `cycle_id`로 연결하여 하나의 타임라인으로 묶는다.

### 6.4 뷰 모드

ExecutionLog 페이지에 두 가지 뷰:
- **테이블 뷰** (기존) — 빠른 스캔용
- **타임라인 뷰** (신규) — 흐름 추적용

토글 버튼으로 전환.

### 6.5 종목 상세 연동

DetailView에서 해당 종목의 최근 실행 타임라인을 간략 표시 (최근 5건).

## 7. API 변경

### 7.1 기존 API 변경 필요

현재 `GET /api/logs`에는 날짜 필터(`date_from`)가 없음 (log_type, symbol, limit, offset만 존재).
오늘의 요약을 위해 날짜 필터 추가 필요:

```
GET /api/logs?log_type=FILL&date_from=2026-03-12&limit=1000
```

또는 요약 전용 엔드포인트 (기존 `GET /api/logs/summary` 존재 여부 확인 필요):

```
GET /api/logs/summary?date=2026-03-12
→ { signals: 12, fills: 3, errors: 0 }
```

### 7.2 로그 데이터 요구사항 (백엔드 변경)

타임라인 재구성을 위해 로그의 `meta` 필드에 다음이 **반드시** 포함되어야 한다:
- `intent_id` (같은 실행 흐름 연결용) — System Trader가 intent 생성 시 발급
- `cycle_id` (같은 평가 주기 연결용)
- `state` (DETECTED/SUBMITTED/FILLED 등)

**현재 상태**: System Trader가 intent_id를 생성하지만, 모든 로그 기록 경로에서 meta에 포함하는지 미확인.
**필요 작업**: 로그 기록 코드(`log_db.insert`)를 점검하여 intent_id/cycle_id가 meta에 일관되게 포함되도록 보장.

## 8. 수용 기준

### 운영 패널
- [ ] 로컬/브로커/클라우드/엔진 4개 상태가 색상 + 텍스트로 한 패널에 보인다
- [ ] 실전/모의 모드가 표시된다
- [ ] 오늘의 신호/체결/오류 수가 표시된다
- [ ] 비정상 상태 시 원인 텍스트가 노출된다
- [ ] 모든 정상일 때 불필요한 경고 없이 깔끔하다

### 실행 로그 타임라인
- [ ] 실행 흐름이 Triggered → Submitted → Filled/Failed 단계로 표현된다
- [ ] 실패 사유가 타임라인에서 바로 읽힌다
- [ ] 테이블 뷰와 타임라인 뷰를 토글할 수 있다
- [ ] 종목 상세에서 해당 종목의 최근 실행 타임라인을 볼 수 있다
- [ ] 체결 여부와 주문 제출 여부가 혼동되지 않는다
