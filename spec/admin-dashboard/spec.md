# 관리자 대시보드 명세서 (admin-dashboard)

> 작성일: 2026-03-04 | 상태: **→ Unit 6 (admin)에 통합**
>
> 이 spec의 내용은 `spec/admin/`에서 통합 구현합니다.

---

## 1. 개요

StockVision은 AI 기반 주식 예측 및 가상 시스템매매 자동화 플랫폼이다.
현재 Phase 2 (가상 거래 + 백테스팅)가 진행 중이며, **Phase 3에서 관리자 대시보드**를 구축한다.

### 1.1 대시보드의 역할

관리자(개발자 또는 SaaS 운영팀)가 **서버 상태, 사용자 활동, 전략 템플릿, API 에러**를 한눈에 모니터링하고 관리하는 웹 인터페이스.

### 1.2 기본 전제

- **SaaS 규모**: 소규모 (운영자 = 개발자 또는 소수 팀)
- **인증**: JWT 기반 관리자 권한 체크 (향후 RBAC 확장 가능)
- **데이터 민감도**: 높음 (API 키, 개인 거래 기록 표시 금지)
- **실시간성**: 준-실시간 (5~10초 주기 폴링 또는 WebSocket)

---

## 2. 관리자 권한 범위

### 2.1 관리자가 볼 수 있는 것 (서버 측)

| 항목 | 설명 | 실시간 | 비고 |
|------|------|--------|------|
| **사용자 통계** | 가입 사용자 수, 활성 사용자(24h), 무계정 사용자 | 5초 | DB 조회 |
| **플랫폼 메트릭** | 일일 백테스팅 작업 수, 자동매매 규칙 활성도 | 5초 | 로그 수집 |
| **서버 상태** | CPU, 메모리, 디스크, DB 연결 수 | 실시간 | psutil, system APIs |
| **API 헬스** | 최근 1시간 에러율, 느린 엔드포인트 | 1초 | 로그 분석 |
| **브릿지 연결** | 로컬 브릿지 하트비트, 마지막 ping 시각 | 실시간 | WebSocket/heartbeat |
| **백테스팅 큐** | 대기/진행 중/완료 작업 수, 예상 시간 | 실시간 | 백그라운드 작업 상태 |
| **컨텍스트 클라우드** | 최근 계산 현황, 성능 지표 | 5초 | 서비스 상태 |
| **전략 템플릿** | 등록된 템플릿 목록, 사용자별 커스텀 전략 수 | 30초 | DB 조회 |
| **에러 로그** | 최근 100개 에러, 심각도별 분류, 스택 트레이스 | 실시간 | 구조화 로그 |
| **시스템 설정** | Feature flags, 파라미터, 환경 변수 (민감정보 제외) | 수동 | .env 편집 |

### 2.2 관리자가 볼 수 없는 것 (법적/보안 제약)

| 항목 | 이유 |
|------|------|
| **사용자 API 키** | 로컬 브라우저에만 저장, 서버에 미저장 (보안 설계) |
| **개인 거래 내역** | 키움증권 서버에만 저장, 관리자는 접근 불가 (법적 제약) |
| **계좌 잔고** | 개인정보 (법적 제약) |
| **개별 사용자 전략 상세** | 사용자 재산권 (저작권) |
| **사용자 이메일 리스트** | 개인정보 (GDPR/PIPA) |

---

## 3. 화면 구성

### 3.1 메인 대시보드

**경로:** `/admin` (또는 `/admin/dashboard`)

**레이아웃:**

```
┌─────────────────────────────────────────────────┐
│  StockVision Admin Dashboard                     │
│  [사용자] [서버] [API] [자동매매] [로그] [설정]  │
├─────────────────────────────────────────────────┤
│                                                 │
│  📊 주요 지표 (KPI)                             │
│  ┌──────┬──────┬──────┬──────┐                  │
│  │ 등록  │ 활성 │ 무  │ 주간 │                  │
│  │ 사용자 │사용자│계정│신규  │                  │
│  │ 1,234 │ 456 │ 789 │ 45  │                  │
│  └──────┴──────┴──────┴──────┘                  │
│                                                 │
│  🖥️ 서버 상태                                   │
│  CPU: ▓▓░░░░░░░░ 25%  | Mem: ▓▓▓░░░░░░░ 35%  │
│  DB: ✓ Connected (450/500) | Redis: ✓ OK      │
│                                                 │
│  ⚠️ 최근 에러 (Top 5)                           │
│  [ERROR] PredictionService timeout (3건)       │
│  [ERROR] BacktestQueue overflow (2건)          │
│                                                 │
│  🔄 백테스팅 큐                                 │
│  대기: 12 | 진행 중: 3 | 완료: 1,234           │
│                                                 │
└─────────────────────────────────────────────────┘
```

### 3.2 탭 구성

#### 3.2.1 "사용자" 탭 (`/admin/users`)

- 사용자 통계 (가입일별, 활성도별 그룹화)
- 활성 사용자 목록 (최근 7일 접속자)
- 무계정 사용자 통계
- 사용자별 가상계좌 수, 전략 수 (집계만, 개인 전략 상세는 미노출)

```
┌─────────────────────────────────────────┐
│ 사용자 관리                              │
├─────────────────────────────────────────┤
│  통계:                                  │
│  - 전체 가입: 1,234명                   │
│  - 최근 24h 활성: 456명 (37%)            │
│  - 최근 7d 활성: 789명 (64%)             │
│  - 무계정 세션: 2,345개                  │
│                                         │
│  활성 사용자 TOP 10                     │
│  [그래프: 일자별 신규가입 추이]          │
│  [그래프: 시간대별 활성도]               │
│                                         │
│  사용자별 활동 요약 (표)                 │
│  | 사용자 | 가입일 | 마지막 | 계좌 | 전략 |
│  | user1@.. | 2026-01-15 | 2h | 2 | 5 |
│  | user2@.. | 2026-02-01 | 1d | 1 | 2 |
│  ...
│                                         │
└─────────────────────────────────────────┘
```

#### 3.2.2 "서버" 탭 (`/admin/server`)

- CPU/메모리/디스크 사용률 (실시간 그래프)
- DB 연결 풀 상태
- Redis 상태
- 시스템 이벤트 로그 (시작, 재부팅, 경고)

```
┌─────────────────────────────────────────┐
│ 서버 모니터링                            │
├─────────────────────────────────────────┤
│  시스템 리소스 (실시간)                  │
│                                         │
│  CPU: ▓▓▓░░░░░░░ 30%                   │
│  [라인 그래프: 1시간 추이]               │
│                                         │
│  메모리: ▓▓▓▓░░░░░░ 42%                 │
│  사용: 8.2GB / 19.5GB                  │
│                                         │
│  디스크: ▓▓▓▓▓░░░░░ 56%                 │
│  사용: 112GB / 200GB                   │
│                                         │
│  데이터베이스 상태                       │
│  ✓ SQLite (로컬개발)                     │
│  - 활성 연결: 5/20                      │
│  - 최근 쿼리 시간: 12ms                 │
│  - DB 크기: 1.2GB                      │
│                                         │
│  Redis 상태                             │
│  ✓ Connected (127.0.0.1:6379)          │
│  - 메모리: 256MB / 512MB                │
│  - Hit Rate: 78%                       │
│                                         │
│  시스템 이벤트                           │
│  [2026-03-04 10:32] 시작됨              │
│  [2026-03-04 08:15] 메모리 경고 (80%)   │
│                                         │
└─────────────────────────────────────────┘
```

#### 3.2.3 "API" 탭 (`/admin/api`)

- 최근 1시간 에러율
- 느린 엔드포인트 (P95 > 200ms)
- 엔드포인트별 요청 수
- 에러 타입별 분류

```
┌─────────────────────────────────────────┐
│ API 헬스 체크                            │
├─────────────────────────────────────────┤
│  최근 1시간 통계                         │
│  - 전체 요청: 12,456                    │
│  - 성공: 12,234 (98.2%)                 │
│  - 에러: 222 (1.8%)                     │
│  - 평균 응답: 45ms                      │
│                                         │
│  느린 엔드포인트 (P95 > 200ms)           │
│  1. POST /api/v1/trading/backtest: 1.2s │
│  2. POST /api/v1/trading/scores: 450ms │
│  3. GET /api/v1/stocks/{id}: 235ms     │
│                                         │
│  에러 요약                               │
│  | 엔드포인트 | 에러 | 타입 | 최근 |
│  | /trading/backtest | 45 | timeout | 5m |
│  | /trading/orders | 12 | validation | 1h |
│  ...
│                                         │
│  상세 에러 로그 (최근 20개)               │
│  [ERROR] POST /trading/backtest         │
│          timeout after 30s (2026-03-04 10:32)
│  [ERROR] POST /trading/orders           │
│          ValidationError: invalid qty (10:31)
│                                         │
└─────────────────────────────────────────┘
```

#### 3.2.4 "자동매매" 탭 (`/admin/auto-trading`)

- 활성 자동매매 규칙 수
- 백테스팅 작업 큐 상태
- 최근 백테스팅 결과 (성과 순위)
- 스케줄 실행 이력

```
┌─────────────────────────────────────────┐
│ 자동매매 & 백테스팅                      │
├─────────────────────────────────────────┤
│  활성 규칙: 34개 (활성 중: 28개)        │
│  - 매수 조건별 집계:                    │
│    RSI 기반: 12개                       │
│    MACD 기반: 8개                       │
│    복합: 8개                            │
│                                         │
│  백테스팅 큐 (실시간)                   │
│  - 대기: 12 (ETA: ~5분)                 │
│  - 진행 중: 3                           │
│  - 완료 (24h): 89                       │
│  - 완료 (총): 1,234                     │
│                                         │
│  상위 성과 백테스트 (최근 30일)          │
│  | 전략 | 기간 | Sharpe | MDD | 승률 |
│  | RSI_EMA | 1y | 1.45 | 18% | 58% |
│  | MACD_BB | 1y | 1.12 | 22% | 54% |
│  ...
│                                         │
│  스케줄 실행 이력                        │
│  [✓] 2026-03-04 09:00 자동매매 실행     │
│  [✓] 2026-03-03 17:00 일괄 청산         │
│  [⚠] 2026-03-02 09:00 부분 실패         │
│                                         │
└─────────────────────────────────────────┘
```

#### 3.2.5 "로그" 탭 (`/admin/logs`)

- 실시간 구조화 로그 스트림
- 심각도별 필터 (DEBUG/INFO/WARNING/ERROR)
- 서비스별 필터 (DataCollector/PredictionModel/Trading 등)
- 로그 검색 (키워드, 날짜 범위)

```
┌─────────────────────────────────────────┐
│ 시스템 로그                              │
├─────────────────────────────────────────┤
│  필터: [심각도 ▼] [서비스 ▼] [검색 🔍]  │
│                                         │
│  📋 실시간 로그 스트림                   │
│  [ERROR] 2026-03-04 10:35:12            │
│  BacktestService.run_backtest           │
│  strategy=rsi_ema stock=AAPL            │
│  Error: Data fetching timeout           │
│  Traceback: ...                         │
│                                         │
│  [WARNING] 2026-03-04 10:34:45          │
│  DataCollectorService.fetch_prices     │
│  ⚠️ Slow query (2.3s)                   │
│                                         │
│  [INFO] 2026-03-04 10:34:32             │
│  SchedulerService.execute_rules         │
│  Executed: 28 active rules               │
│  Bought: 3, Sold: 5                     │
│                                         │
│  [INFO] 2026-03-04 10:33:00             │
│  PredictionService.inference            │
│  Processed 50 stocks in 4.2s             │
│                                         │
│  ...                                    │
│                                         │
└─────────────────────────────────────────┘
```

#### 3.2.6 "설정" 탭 (`/admin/settings`)

- Feature flags 토글
- 파라미터 편집 (수수료율, 슬리피지, 수익률 임계값 등)
- 환경 변수 관리 (보안: 민감정보는 마스킹)
- 백업/복구

```
┌─────────────────────────────────────────┐
│ 시스템 설정                              │
├─────────────────────────────────────────┤
│  Feature Flags                          │
│  [✓] USE_PREDICTION                    │
│  [✓] USE_RULE_SIGNALS                  │
│  [✗] ALLOW_SHORT_SELLING                │
│  [✓] INTRADAY_MODE (비활성)              │
│                                         │
│  거래 파라미터                           │
│  ┌─────────────────────────────────────┐
│  │ 수수료율: 0.015% [입력]              │
│  │ 세금율: 0.23% [입력]                 │
│  │ 슬리피지 계수: 1.0 [입력]            │
│  │ 일일 손실 한도: -50,000 [입력]      │
│  │ 연속 손실 횟수: 5 [입력]             │
│  │ [저장] [초기화]                     │
│  └─────────────────────────────────────┘
│                                         │
│  환경 변수 (마스킹됨)                    │
│  SMTP_HOST: ✓ smtp.gmail.com            │
│  SMTP_PASSWORD: •••••••• [수정]         │
│  JWT_SECRET_KEY: •••••••• [수정]        │
│  DATABASE_URL: ✓ sqlite:///db.sqlite   │
│                                         │
│  백업/복구                               │
│  [DB 백업 다운로드] [파일 복원]         │
│  마지막 백업: 2026-03-04 09:00          │
│                                         │
└─────────────────────────────────────────┘
```

---

## 4. 사용자 관리

### 4.1 API: 사용자 통계

**GET `/api/v1/admin/users/stats`**

```json
{
  "success": true,
  "data": {
    "totalUsers": 1234,
    "activeUsers24h": 456,
    "activeUsers7d": 789,
    "anonymousUsers": 2345,
    "newUsersToday": 12,
    "newUsersThisWeek": 89,
    "signupTrendDaily": [
      { "date": "2026-03-04", "count": 12 },
      { "date": "2026-03-03", "count": 15 }
    ]
  },
  "count": 1
}
```

### 4.2 API: 활성 사용자 목록

**GET `/api/v1/admin/users?limit=20&offset=0`**

```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "email": "user1@example.com",
      "createdAt": "2026-01-15T10:30:00Z",
      "lastLoginAt": "2026-03-04T08:15:00Z",
      "accountCount": 2,
      "strategyCount": 5,
      "lastActivityType": "backtest_run"
    }
  ],
  "count": 1
}
```

---

## 5. 서비스 모니터링

### 5.1 API: 서버 상태

**GET `/api/v1/admin/server/status`**

```json
{
  "success": true,
  "data": {
    "timestamp": "2026-03-04T10:35:00Z",
    "cpu": {
      "percent": 25.3,
      "cores": 8,
      "threadsPerCore": 2
    },
    "memory": {
      "total": 20906432512,
      "available": 12084125696,
      "percent": 42.1,
      "used": 8822306816
    },
    "disk": {
      "total": 214748364800,
      "used": 120357761024,
      "percent": 56.0,
      "free": 94390603776
    },
    "database": {
      "connected": true,
      "activeConnections": 5,
      "maxConnections": 20,
      "lastQueryMs": 12
    },
    "redis": {
      "connected": true,
      "memory": 268435456,
      "maxMemory": 536870912,
      "hitRate": 0.78
    },
    "uptime": {
      "seconds": 86400,
      "readable": "1 day, 0 hours"
    }
  },
  "count": 1
}
```

### 5.2 API: 에러 로그 (최근 N개)

**GET `/api/v1/admin/logs/errors?limit=100&hours=1`**

```json
{
  "success": true,
  "data": [
    {
      "id": "log_123",
      "timestamp": "2026-03-04T10:35:12Z",
      "level": "ERROR",
      "service": "BacktestService",
      "message": "Backtest timeout after 30s",
      "context": {
        "strategy": "rsi_ema",
        "stock": "AAPL"
      },
      "stackTrace": "File 'backtest_engine.py'...",
      "count": 3
    }
  ],
  "count": 222
}
```

---

## 6. 전략 템플릿 관리

### 6.1 역할

관리자가 **사전 구성된 거래 전략**을 사용자에게 제공.
- 내장 템플릿 (RSI_EMA, MACD_BB 등)
- 사용자 커스텀 전략 통계 (집계만)

### 6.2 API: 템플릿 목록

**GET `/api/v1/admin/strategies/templates`**

```json
{
  "success": true,
  "data": [
    {
      "id": "template_rsi_ema",
      "name": "RSI + EMA Crossover",
      "description": "RSI 과매도 + EMA 상향 신호",
      "category": "technical_indicators",
      "buySignal": {
        "rsiThreshold": 30,
        "emaDirection": "uptrend"
      },
      "sellSignal": {
        "rsiThreshold": 70
      },
      "usageCount": 156,
      "avgSharpe": 1.45,
      "approved": true
    }
  ],
  "count": 12
}
```

### 6.3 API: 커스텀 전략 통계

**GET `/api/v1/admin/strategies/stats`**

```json
{
  "success": true,
  "data": {
    "customStrategies": {
      "total": 456,
      "byStatus": {
        "active": 340,
        "paused": 89,
        "archived": 27
      },
      "avgPerformance": {
        "sharpe": 1.12,
        "mdd": 0.22,
        "winRate": 0.54
      }
    }
  },
  "count": 1
}
```

---

## 7. 기술 요구사항

### 7.1 백엔드 구현

#### 의존성

```
# requirements.txt 추가
psutil==5.9.8              # 시스템 리소스 모니터링
aiofiles==23.2.1           # 파일 스트리밍 (로그)
python-json-logger==2.0.7  # 구조화 로그
```

#### 모델 (새로 추가되는 것 없음)

기존 모델 활용:
- `User` (인증 spec에서)
- `VirtualAccount`, `VirtualPosition`, `VirtualTrade` (거래 모델)
- `AutoTradingRule`, `BacktestResult` (자동매매 모델)

#### 서비스 계층

```python
# backend/app/services/admin_service.py (신규)

class AdminService:
    """관리자 대시보드 서비스"""

    def __init__(self, db: Session):
        self.db = db

    def get_user_stats(self) -> dict:
        """사용자 통계 조회"""
        # 가입 사용자 수, 활성 사용자 수, 무계정 세션 등

    def get_server_status(self) -> dict:
        """서버 리소스 상태"""
        # psutil로 CPU, 메모리, 디스크, DB, Redis 조회

    def get_api_health(self, hours: int = 1) -> dict:
        """API 헬스 체크 (최근 N시간 에러율, 느린 엔드포인트)"""
        # 구조화 로그에서 API 응답 시간 분석

    def get_error_logs(self, limit: int = 100, hours: int = 1) -> list:
        """최근 에러 로그"""
        # 심각도별 필터링, 중복 제거

    def get_strategy_stats(self) -> dict:
        """전략 템플릿 및 커스텀 전략 통계"""
        # 활성 규칙 수, 평균 성과 등
```

#### API 라우터

```python
# backend/app/api/admin.py (신규)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

@router.get("/users/stats")
async def get_user_stats(db: Session = Depends(get_db)):
    """사용자 통계"""
    service = AdminService(db)
    return {
        "success": True,
        "data": service.get_user_stats(),
        "count": 1
    }

@router.get("/server/status")
async def get_server_status():
    """서버 상태"""
    # psutil 호출
    return {"success": True, "data": {...}, "count": 1}

@router.get("/logs/errors")
async def get_error_logs(limit: int = 100, hours: int = 1):
    """에러 로그"""
    # 로그 파일 또는 DB에서 읽기
    return {"success": True, "data": [...], "count": N}

@router.get("/logs/stream")
async def stream_logs(severity: str = "INFO"):
    """실시간 로그 스트림 (SSE)"""
    # EventSource로 클라이언트에 로그 전송
    return StreamingResponse(...)

@router.get("/strategies/templates")
async def list_templates(db: Session = Depends(get_db)):
    """전략 템플릿 목록"""
    return {"success": True, "data": [...], "count": N}

@router.patch("/settings")
async def update_settings(settings: dict):
    """시스템 설정 수정 (Feature flags, 파라미터)"""
    # .env 또는 DB에 저장
    return {"success": True, "data": {...}, "count": 1}
```

#### 인증 미들웨어

```python
# backend/app/core/security.py에 추가

from fastapi import Depends, HTTPException

def verify_admin(token: str = Depends(oauth2_scheme)) -> dict:
    """JWT 토큰에서 관리자 여부 확인"""
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    user_id = payload.get("sub")

    # DB에서 사용자 조회 후 role 확인
    user = db.query(User).filter(User.id == user_id).first()
    if not user or user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")

    return user

@router.get("/admin/users")
async def list_users(admin: User = Depends(verify_admin)):
    """관리자만 접근 가능"""
    ...
```

### 7.2 프론트엔드 구현

#### 디렉터리 구조

```
frontend/src/
├── pages/
│   └── AdminDashboard.tsx          # 메인 페이지
├── components/
│   ├── AdminLayout.tsx              # 레이아웃 (네비게이션 + 탭)
│   └── admin/
│       ├── UserStats.tsx            # 사용자 탭
│       ├── ServerMonitor.tsx        # 서버 탭
│       ├── ApiHealth.tsx            # API 탭
│       ├── AutoTrading.tsx          # 자동매매 탭
│       ├── LogViewer.tsx            # 로그 탭
│       └── Settings.tsx             # 설정 탭
├── services/
│   └── adminService.ts              # API 클라이언트
├── hooks/
│   └── useAdminWebSocket.ts         # 실시간 데이터 (WebSocket)
└── types/
    └── admin.ts                     # TypeScript 타입
```

#### 타입 정의

```typescript
// frontend/src/types/admin.ts

export interface UserStats {
  totalUsers: number;
  activeUsers24h: number;
  activeUsers7d: number;
  anonymousUsers: number;
  newUsersToday: number;
  signupTrendDaily: { date: string; count: number }[];
}

export interface ServerStatus {
  timestamp: string;
  cpu: { percent: number; cores: number };
  memory: { total: number; available: number; percent: number };
  disk: { total: number; used: number; percent: number };
  database: { connected: boolean; activeConnections: number };
  redis: { connected: boolean; memory: number; hitRate: number };
  uptime: { seconds: number; readable: string };
}

export interface ApiHealthMetric {
  totalRequests: number;
  successCount: number;
  errorCount: number;
  errorRate: number;
  avgResponseTime: number;
  slowEndpoints: Array<{ path: string; method: string; p95Ms: number }>;
  errorsByType: Array<{ type: string; count: number }>;
}

export interface ErrorLog {
  id: string;
  timestamp: string;
  level: "DEBUG" | "INFO" | "WARNING" | "ERROR";
  service: string;
  message: string;
  context: Record<string, any>;
  stackTrace?: string;
  count: number; // 중복 제거
}

export interface StrategyTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  buySignal: Record<string, any>;
  sellSignal: Record<string, any>;
  usageCount: number;
  avgSharpe: number;
  approved: boolean;
}
```

#### 서비스 계층

```typescript
// frontend/src/services/adminService.ts

class AdminService {
  private baseUrl = 'http://localhost:8000/api/v1/admin';
  private token: string | null = null;

  constructor() {
    this.token = localStorage.getItem('token');
  }

  async getUserStats(): Promise<UserStats> {
    const response = await axios.get(`${this.baseUrl}/users/stats`, {
      headers: { Authorization: `Bearer ${this.token}` }
    });
    return response.data.data;
  }

  async getServerStatus(): Promise<ServerStatus> {
    const response = await axios.get(`${this.baseUrl}/server/status`, {
      headers: { Authorization: `Bearer ${this.token}` }
    });
    return response.data.data;
  }

  async getApiHealth(hours: number = 1): Promise<ApiHealthMetric> {
    const response = await axios.get(`${this.baseUrl}/api/health`, {
      params: { hours },
      headers: { Authorization: `Bearer ${this.token}` }
    });
    return response.data.data;
  }

  async getErrorLogs(limit: number = 100, hours: number = 1): Promise<ErrorLog[]> {
    const response = await axios.get(`${this.baseUrl}/logs/errors`, {
      params: { limit, hours },
      headers: { Authorization: `Bearer ${this.token}` }
    });
    return response.data.data;
  }

  async streamLogs(severity: string = 'INFO'): Promise<EventSource> {
    return new EventSource(
      `${this.baseUrl}/logs/stream?severity=${severity}`,
      { headers: { Authorization: `Bearer ${this.token}` } }
    );
  }

  async listStrategies(): Promise<StrategyTemplate[]> {
    const response = await axios.get(`${this.baseUrl}/strategies/templates`, {
      headers: { Authorization: `Bearer ${this.token}` }
    });
    return response.data.data;
  }
}

export default new AdminService();
```

#### 컴포넌트 예시 (UserStats)

```typescript
// frontend/src/components/admin/UserStats.tsx

import { useQuery } from '@tanstack/react-query';
import adminService from '../../services/adminService';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';

export default function UserStats() {
  const { data: stats, isLoading } = useQuery({
    queryKey: ['admin', 'users'],
    queryFn: () => adminService.getUserStats(),
    refetchInterval: 5000
  });

  if (isLoading) return <div>Loading...</div>;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="가입 사용자" value={stats?.totalUsers || 0} />
        <StatCard label="활성 (24h)" value={stats?.activeUsers24h || 0} />
        <StatCard label="활성 (7d)" value={stats?.activeUsers7d || 0} />
        <StatCard label="무계정" value={stats?.anonymousUsers || 0} />
      </div>

      <div className="bg-white p-6 rounded-lg shadow">
        <h3 className="text-lg font-bold mb-4">신규 가입 추이</h3>
        <LineChart width={800} height={300} data={stats?.signupTrendDaily || []}>
          <CartesianGrid />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip />
          <Legend />
          <Line type="monotone" dataKey="count" stroke="#8884d8" />
        </LineChart>
      </div>
    </div>
  );
}

interface StatCardProps {
  label: string;
  value: number;
}

function StatCard({ label, value }: StatCardProps) {
  return (
    <div className="bg-gradient-to-br from-blue-500 to-blue-600 text-white p-6 rounded-lg">
      <p className="text-sm text-blue-100">{label}</p>
      <p className="text-3xl font-bold">{value.toLocaleString()}</p>
    </div>
  );
}
```

#### 실시간 데이터 (WebSocket)

```typescript
// frontend/src/hooks/useAdminWebSocket.ts

import { useEffect, useState } from 'react';

export function useAdminWebSocket(endpoint: string) {
  const [data, setData] = useState(null);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/admin/${endpoint}`;
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => setIsConnected(true);
    ws.onmessage = (event) => setData(JSON.parse(event.data));
    ws.onclose = () => setIsConnected(false);

    return () => ws.close();
  }, [endpoint]);

  return { data, isConnected };
}
```

### 7.3 라우팅

#### 프론트엔드 라우트

```typescript
// frontend/src/App.tsx에 추가

import AdminDashboard from './pages/AdminDashboard';
import { ProtectedRoute } from './components/ProtectedRoute';

<Routes>
  <Route
    path="/admin/*"
    element={
      <ProtectedRoute requireAuth={true} requireAdmin={true}>
        <AdminDashboard />
      </ProtectedRoute>
    }
  />
</Routes>
```

### 7.4 보안 고려사항

| 항목 | 대책 |
|------|------|
| **인증** | JWT + 관리자 role 확인 |
| **권한** | `verify_admin` 미들웨어 필수 |
| **감시** | 관리자 활동 로깅 (접근 시간, IP, 변경사항) |
| **민감정보** | API 키, 이메일, 계좌번호 마스킹 |
| **Rate Limit** | 관리자 API도 DDoS 방지 (너그러운 한도) |

---

## 8. 미결 사항

### 8.1 추후 논의 필요

- [ ] 관리자 권한 체계: 단순 binary (admin/user) vs RBAC (역할별 세부 권한)
- [ ] 감시 대상: 관리자 활동 로깅 수준 (변경사항만 vs 모든 접근)
- [ ] 백업 정책: 자동 백업 주기 (일 1회 vs 주 1회)
- [ ] 실시간성: WebSocket vs 폴링 (네트워크 부하 고려)
- [ ] 외부 모니터링: Prometheus/Grafana 통합 여부
- [ ] 알림: Slack/이메일 자동 알림 기준 (CPU >80% 등)

### 8.2 Phase 4에서 구현 예정

```markdown
- [ ] RBAC (Role-Based Access Control)
- [ ] 관리자 활동 감시 대시보드
- [ ] Prometheus/Grafana 메트릭 수집
- [ ] 자동 백업 + 복구 기능
- [ ] 사용자 지원 티켓 시스템 (관리자가 처리)
- [ ] 비용 분석 대시보드 (클라우드 VM 인스턴스 비용)
- [ ] A/B 테스트 관리 (전략 템플릿 승인 프로세스)
```

---

## 9. 수용 기준 (Acceptance Criteria)

### Phase 3 — 기본 구조

- [ ] 관리자가 `/admin`에 접근하면 대시보드가 로드된다 (JWT 확인)
- [ ] "사용자" 탭에서 가입/활성 사용자 통계를 볼 수 있다
- [ ] "서버" 탭에서 CPU/메모리/디스크 실시간 상태를 볼 수 있다
- [ ] "API" 탭에서 최근 1시간 에러율과 느린 엔드포인트를 볼 수 있다
- [ ] "로그" 탭에서 실시간 구조화 로그 스트림을 볼 수 있다 (심각도별 필터링)
- [ ] "설정" 탭에서 Feature flags와 거래 파라미터를 수정할 수 있다
- [ ] 로그인하지 않은 사용자는 `/admin` 접근 불가 (403)
- [ ] 관리자가 아닌 사용자는 `/admin` 접근 불가 (403)

### 예상 구현 순서

1. **Step 1**: 백엔드 API (사용자, 서버 상태, 에러 로그)
2. **Step 2**: 프론트엔드 UI (탭 구조, 기본 차트)
3. **Step 3**: 실시간 데이터 (WebSocket 또는 폴링)
4. **Step 4**: 설정 관리 페이지
5. **Step 5**: 로그 스트리밍 및 검색

---

## 10. 참고: 기존 코드 경로

| 영역 | 경로 | 비고 |
|------|------|------|
| API 라우터 | `backend/app/api/` | admin.py 신규 생성 |
| 서비스 계층 | `backend/app/services/` | admin_service.py 신규 생성 |
| 인증 | `backend/app/core/security.py` | verify_admin 미들웨어 추가 |
| DB 모델 | `backend/app/models/` | 기존 모델 활용 (신규 모델 불필요) |
| 프론트 페이지 | `frontend/src/pages/` | AdminDashboard.tsx 신규 생성 |
| 컴포넌트 | `frontend/src/components/admin/` | 6개 탭 컴포넌트 신규 생성 |

---

## 11. 정리표

| 항목 | 내용 |
|------|------|
| **목적** | 운영자가 서버 상태, 사용자 활동, API 헬스, 전략 성과를 한눈에 모니터링 |
| **인증** | JWT + 관리자 role 확인 |
| **데이터 민감도** | 높음 (개인 API 키, 거래 내역 비노출) |
| **실시간성** | 준-실시간 (5~10초 주기) |
| **주요 화면** | 6개 탭 (사용자, 서버, API, 자동매매, 로그, 설정) |
| **구현 기간** | ~3주 (Step 1~5) |
| **복잡도** | 중간 (기존 모델 활용, 신규 API 8개) |

