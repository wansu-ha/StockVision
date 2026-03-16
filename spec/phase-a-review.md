# Phase A 프론트엔드 종합 리뷰

> 작성일: 2026-03-11 | 갱신일: 2026-03-16 | 리뷰어: Claude Code
>
> **Phase A 구현 상태**: A1~A9 구현 완료 (브랜치 `claude/review-missing-features-UhJr7`)
> 상세: `spec/review-missing-features/reports/phase-a-implementation.md`

## 1. 페이지/컴포넌트 현황

### 페이지

| 파일 | 역할 | Phase A 관련성 |
|------|------|--------------|
| `pages/MainDashboard.tsx` | 메인 화면 오케스트레이터 | 핵심. 계좌 카드·엔진 버튼 추가 대상 |
| `pages/Settings.tsx` | API Key 등록, 엔진 제어, 계정 | 핵심. 키 등록 흐름 이미 존재 |
| `pages/Login.tsx` | 이메일/비밀번호 로그인 | 완성 |
| `pages/Register.tsx` | 회원가입 | 완성이나 테마 불일치 (§4) |
| `pages/StrategyList.tsx` | 전략 CRUD. RuleCard 그리드 | strategy-list-info 대상 |
| `pages/StrategyBuilder.tsx` | 전략 생성/수정 | Phase A 직접 관련 없음 |
| `pages/ExecutionLog.tsx` | 체결/이벤트 로그 조회 | Phase A 직접 관련 없음 |
| `pages/Admin/*` | 어드민 7개 서브페이지 | Phase A 무관 |

### 주요 컴포넌트/훅

| 파일 | 역할 | 상태 |
|------|------|------|
| `components/main/Header.tsx` | 로고 + 신호등 + 검색 + 톱니바퀴 | 신호등 제거 대상 (U5) |
| `components/main/ListView.tsx` | 계좌 카드 + 종목 리스트 | 신호등+버튼 추가 대상 (U2~U4) |
| `components/RuleCard.tsx` | 전략 카드 | 종목명+방향+상태 추가 대상 |
| `hooks/useAccountStatus.ts` | 로컬 `/api/status` 5초 폴링 | 완성 |
| `hooks/useAccountBalance.ts` | 잔고 + 미체결 폴링 | 완성 |
| `hooks/useStockData.ts` | rules + 현재가 + 종목명 병합 | 완성 |

## 2. 스펙 Gap 분석

### broker-auto-connect
- 백엔드 전용 스펙. 프론트엔드 구조는 대부분 준비됨
- ~~**Gap 1**: `useAccountStatus`의 `LocalStatusData.broker` 타입에 `reason?: string` 없음~~ → ✅ 이미 존재 확인
- ~~**Gap 2**: F8 (키 등록 후 즉시 재연결) — `Settings.tsx`에 `POST /api/broker/reconnect` 호출 없음~~ → ✅ A9에서 수정

### frontend-ux-v2

| 수용 기준 | 현재 상태 |
|----------|----------|
| U1 장 상태 카드 표시 | ✅ 완료 |
| U2 엔진 신호등 카드 이동 | ✅ 이미 구현됨 (A5 확인) |
| U3 전략 실행/중지 버튼 | ✅ 이미 구현됨 (A5 확인) |
| U4 신호등 3색 | ✅ 이미 구현됨 (A5 확인) |
| U5 Header 신호등 제거 | ✅ 이미 구현됨 (A5 확인) |

### strategy-list-info

| 수용 기준 | 현재 상태 |
|----------|----------|
| S1 종목명 표시 | ✅ 이미 구현됨 (A5 확인) |
| S2 방향 표시 | ✅ 이미 구현됨 (A5 확인) |
| S3 실행 상태 | ✅ 이미 구현됨 (A5 확인) |

## 3. 스펙에 빠진 Phase A 필수 항목

### (1) 설정 — 키 등록 후 reconnect 트리거
`Settings.tsx`의 `handleSaveKeys` 성공 후 `POST /api/broker/reconnect` 호출 필요. broker-auto-connect F8의 프론트엔드 대응이 어느 스펙에도 없음.

### (2) 키 미등록 온보딩 CTA
브로커 미연결 시 계좌 카드에 "설정에서 증권사 키를 등록하세요 →" 같은 안내가 없음. "켜면 바로 쓸 수 있다"를 충족하려면 유도가 필요.

### (3) 로컬 서버 미실행 상태 미구분
서버 꺼짐 vs 브로커 미연결을 UI에서 구분하지 않음. `useAccountStatus`의 `error` 상태 활용 가능.

### (4) 미체결 주문 취소 버튼 미연결
`ListView.tsx:284` "취소" 버튼에 `onClick` 없음. `PendingOrder` 타입에 `orderId` 누락.

## 4. 추가 발견 UI 버그/문제

### (1) Register.tsx 라이트 테마 불일치
`bg-gray-50`, `bg-white`, `text-blue-600` — 앱 전체 다크 테마와 불일치. 또한 `cloudAuth.register()` 대신 별도 `auth.ts`의 중복 구현 사용.

### (2) PendingOrder 타입 orderId 누락
`ListView.tsx:27`에 `orderId` 없음. `MainDashboard.tsx:90`에서 `orderId: o.order_id` 매핑하지만 타입에 없어 버려짐.

### (3) 장 상태 — 공휴일 무시
`MainDashboard.tsx:95-101`에서 `new Date()`로만 계산. `useMarketContext()`의 서버 데이터 미사용.

### (4) Header 신호등 툴팁 불일치
노란 상태(브로커만 연결)인데 "엔진 정지"가 뜸. → U5 구현 시 자동 해결.

## 5. 종합 판단

### Phase A 졸업까지 남은 작업

**졸업 블로커 — 구현 완료 (2026-03-16):**
1. ~~frontend-ux-v2 U2~U5~~ → ✅ 이미 구현됨 확인
2. ~~Settings.tsx — 키 등록 후 reconnect 트리거~~ → ✅ A9
3. ~~strategy-list-info S1, S2, S3~~ → ✅ 이미 구현됨 확인
4. ~~AuthContext setState 경쟁 조건~~ → ✅ A1+A2
5. ~~useStockData 클로저 race condition~~ → ✅ A4
6. ~~cloudClient 401 인터셉터 정리~~ → ✅ A1+A2
7. ~~Settings 키 등록 캐시 미갱신~~ → ✅ A9
8. ~~App.tsx 404 fallback~~ → ✅ A8 확인 (이미 존재)
9. ~~useAccountStatus localReady 가드~~ → ✅ A8 확인 (이미 존재)

**잔여 항목 (Phase A 비블로커):**
- 미체결 "취소" 버튼 stub — onClick 없음, PendingOrder.orderId 누락
- 키 미등록 온보딩 CTA
- Register.tsx 라이트 테마 불일치 + auth.ts 중복 구현
- 장 상태 공휴일 무시
- localClient 에러 처리 불일치
- ListView pendingOrders key에 인덱스 사용
