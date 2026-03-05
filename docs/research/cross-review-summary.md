# Phase 3-A 교차 리뷰 종합 보고서

> 작성일: 2026-03-05 | 리뷰 대상: Unit 1, 2, 4, 7

---

## 1. 개발 결과 요약

| Unit | 범위 | Steps | 파일 수 | 테스트 | 상태 |
|------|------|:-----:|:------:|:------:|------|
| 1. 키움 REST API | sv_core + local_server/broker/ | 13/13 | ~20 | 30+ 검증 | ✅ 완료 |
| 2. 로컬 서버 코어 | local_server/ 기반 구조 | 10/10 | 29 | 48 케이스 | ✅ 완료 |
| 4. 클라우드 서버 | cloud_server/ 확장 | 11/11 | 38 | 자체 검증 | ✅ 완료 |
| 7. 약관/법무 | docs/legal/ + 보고서 | 4/6 | 9 | N/A | ⚠️ Step 5-6 잔여 |

---

## 2. 교차 리뷰 결과

### 2.1 sv_core 정합성 (상세: cross-review-sv-core.md)

**핵심 문제**: Unit 1 정본과 Unit 2/4 stub 사이에 설계 패턴 차이.

| # | 심각도 | 내용 |
|---|--------|------|
| C1 | **Critical** | QuoteEvent import 경로 — Unit 4가 `sv_core.models.quote`를 import하지만 정본은 `sv_core.broker.models`에 정의 |
| C2 | **Critical** | QuoteEvent 필드 타입 — Unit 4 stub: `price: int`, 정본: `price: Decimal` |
| C3 | **Critical** | QuoteEvent 필드명 — Unit 4: `bid`/`ask`, 정본: `bid_price`/`ask_price` |
| C4 | **Critical** | `get_balance()` 시그니처 — stub: `(account_no) → dict`, 정본: `() → BalanceResult` |
| C5 | **Critical** | `_KiwoomStub` ABC 미구현 — 정본의 `connect`/`disconnect`/`is_connected`/`place_order`/`get_open_orders` 미구현 |
| M5 | Medium | `listen()` vs 콜백 — Unit 4가 `broker.listen()` 호출하지만 정본은 `subscribe_quotes(callback)` 패턴 |
| M1 | Medium | `get_positions()` — stub에서 독립 메서드, 정본에서 `BalanceResult.positions`로 통합 |

**원인**: 병렬 개발 시 ABC 인터페이스 방향이 사전 합의되지 않음.

### 2.2 API 계약 정합성 (상세: cross-review-api-contract.md)

#### 로컬 서버 (Unit 2)

| # | 심각도 | 내용 |
|---|--------|------|
| A1 | **Critical** | `POST /api/auth/token` 용도 불일치 — plan: JWT 전달, 구현: 키움 API Key 저장 |
| A2 | High | `POST /api/config/kiwoom` 누락 — 프론트엔드 Settings 동작 불가 |
| A3 | High | `POST /api/strategy/kill` 누락 — Kill Switch 불가 |
| A4 | High | `POST /api/strategy/unlock` 누락 — 손실 락 해제 불가 |
| A5 | Medium | `GET /api/status` 응답 구조 차이 — plan: 플랫, 구현: 중첩 |
| A6 | Medium | `GET /api/logs` 응답 구조 차이 — plan: 배열, 구현: 페이지네이션 객체 |

#### 클라우드 서버 (Unit 4)

| # | 심각도 | 내용 |
|---|--------|------|
| A7 | **Critical** | 토큰 필드명 — plan/프론트엔드 기대: `access_token`, 구현: `jwt` |
| A8 | High | `count` 필드 누락 — 23개 엔드포인트에서 `{ success, data, count }` 규격 미준수 |
| A9 | Medium | admin users 응답 — `data` 키 없이 spread 반환 |

#### WebSocket (Unit 2 ↔ 프론트엔드)

| # | 심각도 | 내용 |
|---|--------|------|
| W1 | **Critical** | WS 메시지 타입명 — 구현: `quote`/`fill`/`status`, 프론트엔드 기대: `price_update`/`execution`/`status_change` |
| W2 | Medium | `side` 값 대소문자 — 구현: `BUY`/`SELL`, 프론트엔드 기대: `buy`/`sell` |

### 2.3 보안 + 코드 품질 (상세: cross-review-security-quality.md)

#### 보안

| # | 심각도 | Unit | 내용 |
|---|--------|------|------|
| SEC-C1 | **Critical** | 1 | App Secret이 모든 API 요청 헤더에 포함 → 로그 노출 |
| SEC-C2 | **Critical** | 4 | SECRET_KEY 기본값 `"dev-secret-key-change-in-production"` → 운영 시 JWT 무력화 |
| SEC-H1 | High | 2 | 로컬 서버 API 인증 없음 → 로컬 네트워크에서 임의 주문 가능 |
| SEC-H2 | High | 4 | 이메일/비밀번호 재설정 토큰 평문 DB 저장 → DB 유출 시 계정 탈취 |
| SEC-H3 | High | 4 | X-Forwarded-For 스푸핑으로 Rate Limiting 우회 가능 |
| SEC-H4 | High | 2 | HTTPException detail에 내부 예외 메시지 노출 |
| + 7건 | Med/Low | 전체 | WS approval_key, 하트비트 인증, timezone-naive 등 |

#### 코드 품질

| # | 심각도 | Unit | 내용 |
|---|--------|------|------|
| QUA-A1 | High | 1 | Reconciler가 private 필드 `_local_orders` 직접 접근 |
| QUA-A2 | High | 2 | `LogDB.write()` blocking sqlite3 I/O in async handler |
| QUA-A3 | Medium | 1 | `httpx.AsyncClient` 매 요청마다 생성/소멸 (풀 낭비) |
| QUA-E3 | Medium | 4 | DB commit 예외를 모두 409로 처리 |
| QUA-E4 | Medium | 1 | Reconciler ORPHAN 주문 무조건 FILLED 처리 |
| QUA-AS1 | Low | 4 | `def`/`async def` 혼용 비일관 |
| QUA-T3 | Low | 4 | `date.fromisoformat()` ValueError 미처리 |

### 2.4 법률 문서 (상세: cross-review-legal.md)

**아키텍처 일치도: 92/100**

- ✅ 데이터 저장 위치, 법적 포지셔닝, 키움 약관 준수, API Key 분리 — 모두 일치
- ⚠️ 9개 경미한 개선 항목 (가격 용어, 익명 UUID 판단, 로컬 데이터 삭제 가이드 등)
- 📌 권장: 키움증권에 아키텍처 사전 승인 요청 (로컬 실행 = 제3자 위임 아님)

---

## 3. 이슈 요약 통계

| 심각도 | sv_core | API 계약 | 보안 | 코드 품질 | 법률 | 합계 |
|--------|:------:|:-------:|:----:|:--------:|:----:|:----:|
| **Critical** | 5 | 4 | 2 | 0 | 0 | **11** |
| **High** | 0 | 4 | 4 | 2 | 0 | **10** |
| **Medium** | 7 | 3 | 4 | 3 | 5 | **22** |
| **Low** | 0 | 0 | 3 | 2 | 4 | **9** |
| **합계** | 12 | 11 | 13 | 7 | 9 | **52** |

---

## 4. 수정 우선순위

### P0 — 병합 전 즉시 수정 (Critical 11건)

1. **sv_core 인터페이스 통일**: Unit 1 정본 기준으로 Unit 2/4의 import 경로, 메서드 시그니처, 데이터 모델을 일치시킨다.
   - QuoteEvent import → `sv_core.broker.models`
   - QuoteEvent 필드 → `price: Decimal`, `bid_price`/`ask_price`
   - `get_balance()` → 정본 시그니처 따르기
   - `_KiwoomStub` → 정본 ABC 전체 메서드 구현
   - `listen()` vs `subscribe_quotes()` → 정본 패턴(콜백) 통일

2. **API 계약 통일**:
   - `POST /api/auth/token` 용도 → plan 기준(JWT 전달)으로 재구현
   - 클라우드 토큰 필드명 → `jwt` → `access_token`
   - WS 메시지 타입명 → 프론트엔드 기대(`price_update`/`execution`/`status_change`) 기준

3. **보안 Critical**:
   - Unit 1 `build_headers()` → 토큰 발급 외 요청에서 appsecret 제거
   - Unit 4 SECRET_KEY → 환경변수 필수, 기본값 제거 (시작 시 예외)

### P1 — 병합 후 우선 수정 (High 10건)

- 누락 엔드포인트 3개 추가 (kill, unlock, config/kiwoom)
- 로컬 서버 Origin 검증 + 앱 토큰 인증 추가
- 이메일/비밀번호 토큰 해시 저장
- X-Forwarded-For 신뢰 설정 (프록시 뒤에서만)
- HTTPException detail에서 내부 정보 제거
- Reconciler private 접근 리팩토링
- LogDB async 래핑 (run_in_executor)

### P2 — 안정화 (Medium 22건 + Low 9건)

- 응답 형식 `count` 필드 통일
- 응답 구조 plan 기준 정렬
- timezone-aware datetime 통일
- 기타 코드 품질 개선

---

## 5. 리뷰 문서 목록

| 파일 | 내용 |
|------|------|
| `docs/research/cross-review-sv-core.md` | sv_core 패키지 정합성 리뷰 |
| `docs/research/cross-review-api-contract.md` | API 계약 정합성 리뷰 |
| `docs/research/cross-review-security-quality.md` | 보안 + 코드 품질 리뷰 |
| `docs/research/cross-review-legal.md` | 법률 문서 리뷰 |
| `docs/research/cross-review-summary.md` | 종합 보고서 (본 문서) |

---

## 6. 다음 단계

1. P0 이슈 11건 수정 → 워크트리 merge
2. P1 이슈 10건 수정
3. 통합 테스트 (빌드 + 유닛 테스트 + lint)
4. Unit 7 Step 5-6 (프론트엔드 UI + 백엔드 버전관리)
5. Unit 3 (전략 엔진) + Unit 5 (프론트엔드) 착수
