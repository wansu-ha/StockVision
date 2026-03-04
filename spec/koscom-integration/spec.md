# 코스콤 오픈플랫폼 연동 명세서 (koscom-integration)

> 작성일: 2026-03-04 | 상태: **미래 계획으로 보류** | 우선순위: Phase 4+

---

> ⚠️ **2026-03-04 업데이트**: 로컬 단일 사용자 모델 전환으로 **현재 구현 대상에서 제외**.
>
> **보류 이유:**
> - 코스콤 핀테크기업 등록: 사업자 등록 필요 (개인 프로젝트 단계에서 어려움)
> - 로컬 모델에서는 키움 COM API로 계좌 직접 조회 가능 → 코스콤 불필요
> - 다중 증권사 지원(KB, 삼성 등)이 필요한 시점에 재검토
>
> **재검토 조건:** 유료 SaaS 확장 + 다중 증권사 지원 필요 시

---

## 1. 개요

### 목적
StockVision이 사용자의 실제 증권 계좌 정보(잔고, 거래 내역, 자산 구성)를 안전하게 연동하여, 시스템매매 시뮬레이션(백테스팅)을 실제 계좌 상태로 검증하고, 장기 운영 시 실시간 포트폴리오 모니터링 기능 제공.

### 핵심 가치
- **합법적 데이터 경로**: 코스콤 공식 등록 → 증권사 데이터 조회 권한 확보
- **감시제약 우회**: 키움증권 제5조③(시세 중계 금지) 규정 우회 가능
- **사용자 신뢰**: 공식 핀테크기업 지위로 보안/컴플라이언스 신뢰성 강화

### 범위
- StockVision 자체의 코스콤 핀테크기업 등록 (1회)
- 사용자별 OAuth 2.0 기반 동의 플로우 (연 1회 갱신)
- 계좌 정보 조회 API 연동 (읽기 전용)
- 프론트엔드 "실제 계좌 연동" UI 추가

### 미포함 항목
- 자동매매 실행 (KIS(한국투자증권) API 별도 계획)
- 계좌 이체, 주문 실행 (읽기 전용 한정)

---

## 2. 코스콤 오픈플랫폼 구조

### 2.1 조직도
```
코스콤 (㈜코스콤, http://open.koscom.co.kr)
├─ 핀테크기업 등록/승인 부서
├─ OAuth 인증 서버
├─ 증권사 브릿지 (키움, KB, 삼성, NH 등)
└─ 데이터 포맷 표준 (JSON)
```

### 2.2 인증 방식
- **프로토콜**: OAuth 2.0 (Authorization Code Flow)
- **토큰 유효기간**:
  - Access Token: 1시간
  - Refresh Token: 12개월 (동의 유효기간)
- **스코프 (권한)**:
  - `readaccount` — 계좌 조회
  - `readtrade` — 거래 내역 조회
  - `readasset` — 자산 구성 조회

### 2.3 데이터 제공 경로
```
사용자 (StockVision 앱)
  ↓ (OAuth 동의)
StockVision 백엔드 (Access Token 발급)
  ↓ (Refresh Token 갱신)
코스콤 OAuth 서버
  ↓ (토큰 검증)
증권사 API (키움/KB/삼성/NH)
  ↓ (실시간 조회)
증권 계좌 정보
```

---

## 3. 등록 절차 (핀테크기업 등록)

### 3.1 사전 준비
1. **회사 정보**
   - 상호: StockVision (또는 운영사)
   - 대표자명, 사업자등록번호
   - 사무실 주소, 대표전화

2. **개발팀 정보**
   - 개발팀장 이름, 직급
   - 기술담당자 이메일, 휴대폰

3. **서비스 정보**
   - 서비스명: StockVision AI 시스템매매 자동화
   - 서비스 URL: https://stockvision.com (예시)
   - 기능 설명: "사용자 실제 계좌 연동 포트폴리오 모니터링"

### 3.2 코스콤 신청 절차
```
Step 1. 코스콤 사이트 (open.koscom.co.kr) 접속
Step 2. "핀테크기업 등록" 신청서 작성
        - 회사 정보
        - 서비스 개요
        - 데이터 사용 목적 (포트폴리오 모니터링)
        - 개인정보처리방침 (필수)
        - 이용약관 (필수)
Step 3. 서류 심사 (1~2주)
        - 회사 자격 검증
        - 서비스 적정성 검토
Step 4. 심사 통과 후
        - Client ID 발급
        - Client Secret 발급
        - Redirect URI 등록 (https://stockvision.com/auth/koscom/callback)
Step 5. 개발팀이 토큰 검증 및 테스트
```

### 3.3 필수 문서
- 개인정보처리방침 (한국어)
- 이용약관 (한국어)
- 서비스 보안 정책서
- API 사용 계획서

### 3.4 코스콤 발급 정보 (환경변수에 저장)
```
KOSCOM_CLIENT_ID=<발급받은 Client ID>
KOSCOM_CLIENT_SECRET=<발급받은 Client Secret>
KOSCOM_OAUTH_URL=https://oauth.koscom.co.kr
KOSCOM_API_URL=https://api.koscom.co.kr/v1
KOSCOM_REDIRECT_URI=https://stockvision.com/auth/koscom/callback
```

---

## 4. 제공 데이터 및 활용

### 4.1 제공 데이터 (코스콤 제6조)

#### (1) 실시간 잔고 (Balance API)
```json
GET /account/balance
Response: {
  "accountId": "1234567890",
  "accountName": "홍길동 계좌",
  "totalAsset": 50000000,
  "cashBalance": 10000000,
  "evaluatedAmount": 40000000,
  "evaluationGain": 500000,
  "evaluationRate": 1.25,
  "timestamp": "2026-03-04T14:30:00Z"
}
```

**활용**:
- 포트폴리오 시작 자산 → 백테스팅과 실제 자산 비교
- 현재 보유 현금 → 추가 매수 가능 여부 판단
- 손익 실시간 모니터링 (차트)

#### (2) 거래 내역 (Trade History API)
```json
GET /account/trades?from=2026-01-01&to=2026-03-04
Response: {
  "trades": [
    {
      "tradeId": "TRD-001",
      "symbol": "005930",  // 삼성전자
      "tradeName": "삼성전자",
      "tradeType": "buy|sell",
      "quantity": 10,
      "price": 70000,
      "amount": 700000,
      "commission": 1000,
      "timestamp": "2026-03-01T09:30:00Z"
    }
  ]
}
```

**활용**:
- 실제 거래 로그 시각화
- 전월/분기별 수익률 계산
- 거래 빈도, 승률 분석

#### (3) 자산별 구성 (Asset Allocation API)
```json
GET /account/allocation
Response: {
  "allocation": [
    {
      "assetType": "stock",
      "holdings": 40000000,
      "percentage": 80,
      "stocks": [
        {
          "symbol": "005930",
          "name": "삼성전자",
          "quantity": 10,
          "currentPrice": 70000,
          "evaluatedAmount": 700000
        }
      ]
    },
    {
      "assetType": "cash",
      "holdings": 10000000,
      "percentage": 20
    }
  ]
}
```

**활용**:
- 포트폴리오 구성 비율 (원형 차트)
- 섹터별/종목별 비중 분석
- 리밸런싱 제안

#### (4) 관심종목 (Watchlist API)
```json
GET /account/watchlist
Response: {
  "watchlist": [
    {
      "symbol": "005930",
      "name": "삼성전자"
    }
  ]
}
```

**활용**:
- 사용자 추천 종목과의 연관성 검토
- 알람 설정 대상 (가격 변동 시 알림)

### 4.2 데이터 조회 권한 및 주기

| 데이터 | 권한 | 조회 주기 | 지연도 |
|--------|------|---------|-------|
| 실시간 잔고 | 읽기전용 | 3시간마다 | 1분 이내 |
| 거래 내역 | 읽기전용 | 1일 1회 (야간) | 당일 종가 후 |
| 자산 구성 | 읽기전용 | 3시간마다 | 1분 이내 |
| 관심종목 | 읽기전용 | 1주 1회 | 즉시 |

---

## 5. 사용자 동의 플로우 (연 1회 갱신)

### 5.1 초기 연동 (First-time Setup)
```
[프론트엔드] "계좌 연동하기" 클릭
  ↓
[프론트엔드] 코스콤 OAuth 페이지로 리다이렉트
  ↓ (사용자가 본인인증 + 동의)
[코스콤] Authorization Code 발급
  ↓
[프론트엔드] /auth/koscom/callback으로 리다이렉트
  (query: code=xxxxxx, state=yyyyy)
  ↓
[백엔드] Authorization Code로 Access Token 요청
  ↓
[코스콤] Access Token + Refresh Token 발급
  ↓
[백엔드] DB에 저장 (암호화)
  ├─ refresh_token (12개월 유효)
  ├─ access_token (1시간 유효)
  ├─ token_issued_at
  ├─ consent_expires_at (발급일 + 365일)
  └─ account_id
  ↓
[프론트엔드] "계좌 연동 완료" 메시지 + Dashboard 리로드
```

### 5.2 토큰 갱신 (Token Refresh)
```
[백엔드] 매일 00시에 배치 작업 실행
  ↓
[백엔드] DB에서 모든 사용자의 refresh_token 조회
  ↓
[백엔드] 각 사용자별 access_token 갱신 요청
  (POST /oauth/token with refresh_token)
  ↓
[코스콤] 새로운 Access Token 발급
  ↓
[백엔드] DB 업데이트
  ├─ access_token (NEW)
  ├─ token_issued_at (NOW)
  └─ 갱신 실패 시 사용자에게 재동의 알림
```

### 5.3 동의 만료 (Consent Expiry)
```
consent_expires_at이 30일 미만일 때:
  ↓
[프론트엔드] Dashboard에 "계좌 동의 갱신 필요" 배너 표시
  ↓
[사용자] "동의 갱신하기" 클릭
  ↓
[동의 재확인 페이지 리다이렉트] (Step 5.1 반복)
```

---

## 6. 기술 요구사항

### 6.1 백엔드 변경사항

#### (1) 새 테이블: `koscom_accounts`
```sql
CREATE TABLE koscom_accounts (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL UNIQUE,
  account_id VARCHAR(50) NOT NULL,
  refresh_token TEXT NOT NULL ENCRYPTED,
  access_token TEXT NOT NULL ENCRYPTED,
  token_issued_at TIMESTAMP NOT NULL,
  consent_expires_at DATE NOT NULL,
  last_data_sync_at TIMESTAMP,
  status VARCHAR(20) DEFAULT 'active',  -- active, expired, revoked
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id)
);
```

#### (2) 새 테이블: `account_data_cache`
```sql
CREATE TABLE account_data_cache (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL,
  data_type VARCHAR(50),  -- balance, trades, allocation, watchlist
  data_json JSONB NOT NULL,
  cached_at TIMESTAMP NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id),
  INDEX (user_id, data_type)
);
```

#### (3) 환경변수 (.env 추가)
```
# Koscom OAuth
KOSCOM_CLIENT_ID=...
KOSCOM_CLIENT_SECRET=...
KOSCOM_OAUTH_URL=https://oauth.koscom.co.kr
KOSCOM_API_URL=https://api.koscom.co.kr/v1
KOSCOM_REDIRECT_URI=https://stockvision.com/auth/koscom/callback

# Encryption (for token storage)
KOSCOM_TOKEN_CIPHER_KEY=...
```

#### (4) 백엔드 라우터 신규 추가 (`app/api/koscom.py`)
```python
# Auth endpoints
POST /api/v1/koscom/auth/start
  → 코스콤 OAuth URL 생성 후 리다이렉트

POST /api/v1/koscom/auth/callback
  → Authorization Code → Access Token 변환 + DB 저장

POST /api/v1/koscom/auth/revoke
  → 동의 취소 (사용자 요청)

# Data endpoints
GET /api/v1/koscom/account/balance
  → 캐시된 잔고 조회 (3시간 TTL)

GET /api/v1/koscom/account/trades
  → 거래 내역 조회 (1일 TTL)

GET /api/v1/koscom/account/allocation
  → 자산 구성 조회 (3시간 TTL)

# Status endpoints
GET /api/v1/koscom/account/status
  → 동의 상태 및 갱신 예정일 조회
```

#### (5) 백그라운드 배치 작업 (scheduler)
```python
# Daily 00:00 - Token refresh
@scheduler.scheduled_job('cron', hour=0, minute=0)
def refresh_all_koscom_tokens():
    users = get_users_with_koscom_consent()
    for user in users:
        try:
            new_access_token = refresh_access_token(user.refresh_token)
            update_koscom_account(user, new_access_token)
        except TokenRefreshError:
            notify_user_consent_expired(user)
```

#### (6) 암호화 서비스 (`app/services/encryption.py`)
```python
class KoscomTokenEncryption:
    def encrypt_token(token: str) -> str:
        # AES-256 기반 암호화
        pass

    def decrypt_token(encrypted_token: str) -> str:
        # AES-256 기반 복호화
        pass
```

### 6.2 프론트엔드 변경사항

#### (1) 새 페이지: `src/pages/KoscomAuth.tsx`
```typescript
// OAuth 콜백 처리
// query: code, state, error 검증
// 백엔드로 Authorization Code 전달
// 성공 시 Dashboard로 리다이렉트
```

#### (2) Dashboard 컴포넌트 수정 (`src/components/Portfolio.tsx`)
```typescript
// 기존: 가상 자산만 표시
// 신규:
//   - "실제 계좌 연동 여부" 탭 추가
//   - Koscom 계좌 잔고 표시
//   - 거래 내역 히스토리 표시
//   - 동의 만료 배너 표시
```

#### (3) 설정 페이지 추가 (`src/pages/AccountSettings.tsx`)
```typescript
// 연동된 계좌 목록
// "계좌 연동하기" 버튼
// "동의 취소하기" 버튼
// 동의 유효 기간 표시
// 마지막 동기화 시간 표시
```

#### (4) API 클라이언트 추가 (`src/services/koscomApi.ts`)
```typescript
export const koscomApi = {
  getAuthUrl(): Promise<string>,
  getAccountStatus(): Promise<KoscomAccountStatus>,
  getBalance(): Promise<Balance>,
  getTrades(): Promise<Trade[]>,
  getAllocation(): Promise<AssetAllocation>,
  revokeConsent(): Promise<void>,
};
```

#### (5) TypeScript 타입 추가 (`src/types/koscom.ts`)
```typescript
interface Balance {
  accountId: string;
  totalAsset: number;
  cashBalance: number;
  evaluatedAmount: number;
  evaluationGain: number;
  evaluationRate: number;
  timestamp: string;
}

interface Trade {
  tradeId: string;
  symbol: string;
  tradeName: string;
  tradeType: 'buy' | 'sell';
  quantity: number;
  price: number;
  amount: number;
  commission: number;
  timestamp: string;
}

interface AssetAllocation {
  allocation: Array<{
    assetType: 'stock' | 'cash' | 'bond';
    holdings: number;
    percentage: number;
    stocks?: Array<{ symbol: string; name: string; quantity: number }>;
  }>;
}

interface KoscomAccountStatus {
  isConnected: boolean;
  accountId?: string;
  consentExpiresAt?: string;
  lastSyncAt?: string;
  status: 'active' | 'expired' | 'revoked';
}
```

### 6.3 보안 요구사항

#### (1) 토큰 저장
- Refresh Token, Access Token 모두 **AES-256 암호화** 후 DB 저장
- 메모리 또는 환경변수에는 절대 노출 안 함

#### (2) HTTPS 필수
- Redirect URI는 반드시 HTTPS 스킴
- 비 HTTPS는 코스콤에서 거부

#### (3) State Parameter
- OAuth 인증 요청 시 `state` 파라미터 필수 (CSRF 방지)
- 콜백 시 State 값 검증

#### (4) Rate Limiting
- 코스콤 API 호출 제한: 분당 100회 (계약에 따라 변동)
- 캐싱으로 중복 요청 최소화

#### (5) 개인정보보호
- 사용자 계좌번호, 이름 민감정보 암호화 저장
- 로그에는 계좌번호 끝 4자리만 기록
- 동의 취소 시 관련 데이터 즉시 삭제

---

## 7. 미결 사항

### 7.1 추가 조사 필요

| 항목 | 상태 | 담당 |
|------|------|------|
| 코스콤 핀테크기업 등록 비용 여부 | TBD | 운영팀 |
| 데이터 SLA (Service Level Agreement) | TBD | 기술팀 |
| 각 증권사별 API 응답 시간 | TBD | 기술팀 |
| 과거 거래 내역 조회 기간 제한 | TBD | 기술팀 |
| 실시간 push 가능 여부 | TBD | 기술팀 |
| 캐시 정책 최적화 | TBD | 백엔드 |

### 7.2 순차 의존성

```
Step 1: 코스콤 핀테크기업 등록 신청 (2주 소요)
  ↓
Step 2: Client ID/Secret 발급 받음
  ↓
Step 3: 백엔드 OAuth 라우터 구현 + 테스트
  ↓
Step 4: 프론트엔드 Auth/Dashboard UI 구현
  ↓
Step 5: End-to-End 테스트 (Sandbox 환경)
  ↓
Step 6: 운영 배포
```

### 7.3 향후 확장 (Phase 4+)

- **자동매매 실행**: KIS(한국투자증권) Open API 별도 등록
- **실시간 알림**: 시세 변동 시 푸시/이메일 알림
- **포트폴리오 최적화**: 현재 자산 기반 리밸런싱 제안
- **세금 계산**: 기간별 손익 통계 + 세무 보고서 생성

---

## 8. 참고 자료

- 코스콤 공식 사이트: http://open.koscom.co.kr
- OAuth 2.0 표준: https://tools.ietf.org/html/rfc6749
- 관련 규제: 금융위원회 "핀테크 기업 데이터 조회권 가이드라인"
