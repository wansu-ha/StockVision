> 작성일: 2026-03-12 | Phase C 분석 A: 상태별 UI 매트릭스

# A. 프론트엔드 컴포넌트별 데이터 소스 매핑

## 1. API 클라이언트 요약

| 클라이언트 | 서버 | 인증 | 비고 |
|-----------|------|------|------|
| cloudClient | Cloud :4010 | JWT (sessionStorage `sv_jwt`) | 401 시 자동 갱신 |
| localClient | Local :4020 | X-Local-Secret 헤더 | setAuthToken 시 획득 |
| logs | Local :4020 | localClient 기반 | 로그 전용 |
| admin | Cloud :4010 | JWT + admin role | 어드민 전용 |

## 2. cloudClient API 목록

| 모듈 | 함수 | 엔드포인트 | 설명 |
|------|------|-----------|------|
| cloudAuth | register | POST `/api/v1/auth/register` | 회원가입 |
| | login | POST `/api/v1/auth/login` | 로그인 |
| | refresh | POST `/api/v1/auth/refresh` | JWT 갱신 |
| | logout | POST `/api/v1/auth/logout` | 로그아웃 |
| | verifyEmail | GET `/api/v1/auth/verify-email` | 이메일 인증 |
| | updateProfile | N/A | 미구현 (placeholder) |
| cloudRules | list | GET `/api/v1/rules` | 규칙 목록 |
| | create | POST `/api/v1/rules` | 규칙 생성 |
| | update | PUT `/api/v1/rules/{id}` | 규칙 수정 |
| | remove | DELETE `/api/v1/rules/{id}` | 규칙 삭제 |
| cloudContext | get | GET `/api/v1/context` | 시장 컨텍스트 |
| cloudStocks | search | GET `/api/v1/stocks/search?q={q}&limit={limit}` | 종목 검색 |
| | get | GET `/api/v1/stocks/{symbol}` | 종목 상세 |
| cloudWatchlist | list | GET `/api/v1/watchlist` | 관심종목 목록 |
| | add | POST `/api/v1/watchlist` | 관심종목 추가 |
| | remove | DELETE `/api/v1/watchlist/{symbol}` | 관심종목 제거 |
| cloudBars | get | GET `/api/v1/stocks/{symbol}/bars` | 일봉 데이터 |
| cloudQuote | get | GET `/api/v1/stocks/{symbol}/quote` | 현재가 |
| cloudHealth | check | GET `/health` | 헬스 체크 |

## 3. localClient API 목록

| 모듈 | 함수 | 엔드포인트 | 설명 |
|------|------|-----------|------|
| localAuth | setAuthToken | POST `/api/auth/token` | JWT 전달, local_secret 획득 |
| | logout | POST `/api/auth/logout` | 로그아웃 |
| | status | GET `/api/auth/status` | 인증 상태 |
| | restore | POST `/api/auth/restore` | 토큰 복구 |
| localStatus | get | GET `/api/status` | 서버 상태 |
| localConfig | get | GET `/api/config` | 설정 조회 |
| | update | PATCH `/api/config` | 설정 수정 |
| | setBrokerKeys | POST `/api/config/broker-keys` | 증권사 키 등록 (30s) |
| localRules | sync | POST `/api/rules/sync` | 규칙 동기화 |
| | lastResults | GET `/api/rules/last-results` | 규칙 실행 결과 |
| localLogs | get | GET `/api/logs` | 로그 조회 |
| | summary | GET `/api/logs/summary` | 로그 요약 |
| localAccount | balance | GET `/api/account/balance` | 잔고+보유종목 |
| | orders | GET `/api/account/orders` | 미체결 주문 |
| localEngine | start | POST `/api/strategy/start` | 엔진 시작 (30s) |
| | stop | POST `/api/strategy/stop` | 엔진 중지 (15s) |
| localBroker | reconnect | POST `/api/broker/reconnect` | 브로커 재연결 (15s) |
| localHealth | check | GET `/health` | 헬스 체크 |

## 4. 컴포넌트별 데이터 소스

### MainDashboard.tsx
- **API**: cloud + local both
- **cloud**: cloudRules.list (30s), cloudWatchlist.list (30s), cloudQuote.get (15s), cloudStocks.get, cloudContext.get (30s)
- **local**: localLogs.get (15s), localStatus.get (5s), localAccount.balance (30s), localAccount.orders (15s), localEngine.start/stop
- **에러 처리**: 조용히 무시, 기본값 사용

### OpsPanel.tsx
- **API**: cloud + local both
- **cloud**: cloudHealth.check (10s)
- **local**: localHealth.check (10s), localLogs.summary (30s, localReady 시만)
- **에러 처리**: 상태 미표시, 경고 배너

### DetailView.tsx
- **API**: cloud + local both
- **cloud**: cloudRules.update/remove, cloudWatchlist.remove, cloudContext.get
- **local**: logsApi.getLogs (30s)
- **에러 처리**: 조용히 무시

### PriceChart.tsx
- **API**: cloud + local
- **cloud**: cloudBars.get(symbol, start, end) — 일봉
- **local**: localLogs.get — 이벤트 마커용
- **에러 처리**: 빈 배열 기본값

### Header.tsx
- **API**: cloud + local
- **cloud**: cloudStocks.search (200ms 디바운스)
- **local**: localEngine.stop
- **에러 처리**: 빈 배열

### Settings.tsx
- **API**: local
- **local**: localStatus.get, localConfig.setBrokerKeys, localEngine.start/stop
- **에러 처리**: alert

### ExecutionLog.tsx
- **API**: local (logs)
- **local**: logsApi.getLogs (10s), logsApi.getSummary (10s)
- **에러 처리**: 빈 배열

### BridgeInstaller.tsx
- **API**: HTTP fetch (직접)
- **엔드포인트**: GET `/health` (5s 폴링)
- **에러 처리**: 연결 재시도

### TrafficLightStatus.tsx
- **API**: cloud + local
- **cloud**: cloudHealth.check
- **local**: localStatus.get, localHealth.check
- **에러 처리**: 상태 자동 새로고침

### OnboardingWizard.tsx
- **API**: local
- **local**: localConfig.setBrokerKeys, localBroker.reconnect
- **에러 처리**: 에러 메시지 표시

### RuleCard.tsx / RuleList.tsx / ExecutionTimeline.tsx / ListView.tsx
- **API 호출 없음** — 부모에서 props 전달

## 5. hooks 데이터 소스

| Hook | API | 엔드포인트 | refetch | 조건 |
|------|-----|-----------|---------|------|
| useAccountStatus | local | localStatus.get | 5s | localReady |
| useAccountBalance | local | localAccount.balance, orders | 30s/15s | localReady && brokerConnected |
| useStockData | cloud | cloudRules.list, cloudWatchlist.list, cloudQuote.get, cloudStocks.get | 15~30s | JWT |
| useMarketContext | cloud | cloudContext.get | 30s | JWT |
| useLocalBridgeWS | WS | /ws | 재연결 3회 | localReady |
| useOnboarding | localStorage | - | - | - |

## 6. 상태별 기능 매트릭스 (분석 결과)

| 기능 | 미가입 | 가입만 | +로컬서버 | +증권사 | 완전체 |
|------|--------|--------|----------|---------|--------|
| 종목 검색 | X | O | O | O | O |
| 차트 보기 (일봉) | X | O | O | O | O |
| 전략/규칙 생성 | X | O | O | O | O |
| 전략 목록 조회 | X | O | O | O | O |
| 관심종목 관리 | X | O | O | O | O |
| 시장 컨텍스트 | X | O | O | O | O |
| 전략 로컬 배포 | X | X | △* | O | O |
| 실시간 시세 (WS) | X | X | X | O | O |
| 계좌 잔고 조회 | X | X | X | O | O |
| 보유종목 목록 | X | X | X | O | O |
| 미체결 주문 조회 | X | X | X | O | O |
| 자동매매 시작/정지 | X | X | X | △** | O |
| 체결 로그 조회 | X | X | △*** | △*** | O |
| 설정 변경 | X | X | O | O | O |
| 증권사 키 등록 | X | X | O | - | - |
| AI 분석 (향후) | X | O? | O? | O? | O |

- *△ 로컬 배포: 규칙 sync는 가능하나 증권사 없이 엔진 실행 불가
- **△ 자동매매: 증권사 연동 O이지만 전략(규칙) 없으면 의미 없음
- ***△ 체결 로그: 로컬 서버 있으면 API 호출 가능하지만 체결 데이터 없음

## 7. 에러 처리 현황 요약

| 시나리오 | 현재 처리 |
|---------|----------|
| 로컬 서버 미연결 | 경고 배너, 기능 비활성화 (enabled 조건) |
| 클라우드 서버 미연결 | 헬스 체크 빨간불, 재시도 0회 |
| JWT 401 | 로컬 복구 → 클라우드 갱신 폴백 |
| 브로커 미연결 | 노란불, 계좌 기능 비활성화 |
| 증권사 키 미등록 | 온보딩 강제, Settings 안내 |

## 8. 발견사항

1. **StrategyBuilder 미존재**: 전략/규칙 CRUD는 DetailView 내부에서만 수행. 독립 전략 생성 페이지 없음.
2. **조용한 에러 처리**: 대부분 `.catch(() => null)` — 사용자에게 에러 원인 미표시
3. **refetch 간격 불통일**: 5초~30초 다양 (최적화 필요)
4. **cloudAuth.updateProfile 미구현**: TODO placeholder
5. **"가입만" 상태에서도 종목 검색/차트/규칙 생성 가능**: cloud API만 필요
6. **로컬 서버 없이도 대시보드 접근 가능**: local 데이터만 빠짐 (잔고, 체결 등)

## 9. 데이터 흐름 맵

```
[Login] → JWT 발급
    ↓
[MainDashboard]
    ├─ cloudRules → 규칙 (내 종목)
    ├─ cloudWatchlist → 관심종목
    ├─ cloudQuote → 현재가
    ├─ cloudContext → 시장 컨텍스트
    ├─ localStatus → 엔진/브로커 상태
    ├─ localAccount → 잔고/보유종목
    ├─ localLogs → 체결 기록
    └─ localHealth → 로컬 버전
        ↓
    [ListView] ← 종목 목록 + 계좌 정보
        ↓
    [DetailView] ← 선택된 종목
        ├─ cloudBars → 일봉 데이터
        ├─ cloudContext → 시장 컨텍스트
        ├─ cloudRules → 규칙 (종목별)
        ├─ logsApi → 실행 로그
        └─ [PriceChart] + [RuleCard]

[WebSocket /ws]
    ├─ signal_sent → 주문 전송 알림
    ├─ execution_result → 체결 알림
    ├─ engine_error → 엔진 오류 알림
    └─ broker_error → 브로커 오류 알림
```
