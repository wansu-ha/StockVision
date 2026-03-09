# 어드민 페이지 구현 계획서 (admin)

> 작성일: 2026-03-05 | 상태: 초안 | Unit 6 (Phase 3-C)
> 갱신: 2026-03-09 — 규칙 열람 기능 추가, 미결사항 해소, 구현 단계 재정리

---

## 0. 현황

### 기존 코드 상태

**프론트엔드 (frontend/src/)**
- ✅ `services/admin.ts` — 백엔드 API 클라이언트 기본 구조
- ✅ `pages/AdminDashboard.tsx` — 통계 카드 4개 + 사용자 목록 + 템플릿 관리 (단일 페이지)
- ✅ `components/AdminGuard.tsx` — 권한 검사 컴포넌트
- ❌ 사이드바 레이아웃 — 미구현 (현재 유저 Layout 공유)
- ❌ 서브라우트 (`/admin/users`, `/admin/stats` 등) — 미구현
- ❌ 유저 규칙 열람 — 미구현
- ❌ 접속 통계 차트 — 미구현
- ❌ 서비스 키 관리 — 미구현
- ❌ 에러 로그 뷰어 — 미구현

**백엔드 (cloud_server/)**
- ✅ 통계 API (`GET /api/v1/admin/stats`)
- ✅ 유저 목록 API (`GET /api/v1/admin/users`) — 페이지네이션
- ✅ 템플릿 CRUD API
- ❌ 유저 규칙 열람 API (`GET /admin/users/:id/rules`) — 미구현
- ❌ 유저 비활성화 API (`PATCH /admin/users/:id`) — 미구현
- ❌ 접속 통계 API — 미구현
- ❌ 서비스 키 관리 API — 미구현
- ❌ 에러 로그 API — 미구현

### 설계 원칙 (spec 재확인)

- ✅ **규칙 내용 열람 가능** — 어드민이 유저의 규칙 조건을 읽기 전용으로 조회 가능
- ❌ **개인 금융정보 차단** — 체결, 잔고, 수익률, API Key 접근 불가 (구조적 보장)
- ✅ **역할 기반 접근** — JWT role=admin만 접근 가능

---

## 1. 구현 단계

### Step 1 — 어드민 레이아웃 + 라우팅

**목표**: 사이드바 레이아웃 + 7개 서브라우트 구성

**파일**:
- `components/AdminLayout.tsx` (신규) — 사이드바 + 콘텐츠 영역
  - 사이드바: 대시보드, 유저, 접속통계, 데이터, 서비스키, 템플릿, 에러로그
  - 하단: "유저 화면으로" 링크 (`/`)
  - 상단 바: "StockVision Admin" + 신호등 + admin 유저 메뉴
- `pages/Admin/index.tsx` (리팩토링) — Outlet 기반 서브라우팅
- `App.tsx` (수정) — `/admin/*` 라우트 등록

**라우트 구조**:
```
/admin              → AdminOverview (index route)
/admin/users        → AdminUsers
/admin/stats        → AdminStats
/admin/data         → AdminData
/admin/service-keys → AdminServiceKeys
/admin/templates    → AdminTemplates
/admin/errors       → AdminErrors
```

**검증**:
- [ ] admin 계정으로 `/admin` 접근 → 사이드바 + 대시보드 표시
- [ ] 일반 유저로 `/admin` 접근 → 403 또는 홈으로 리다이렉트
- [ ] 사이드바 네비게이션 링크 모두 정상 동작
- [ ] "유저 화면으로" 클릭 → `/` 이동

---

### Step 2 — 어드민 대시보드 (통계 요약)

**목표**: 시스템 상태 한눈에 보기

**파일**:
- `pages/Admin/AdminOverview.tsx` (신규)

**구현 내용**:
1. **통계 카드 4개**
   - 전체 유저: stats.users.total
   - 온라인 유저: stats.connections.online
   - 활성 규칙: stats.rules.active
   - 1시간 내 에러: stats.errors.count_1h

2. **클라우드 서버 상태**
   - 상태 표시 (정상/경고/오류)
   - 마지막 시세 수신 시간
   - 구독 종목 수
   - 일봉 수집량 (건/일)

3. **최근 에러 로그 (5건)**
   - 타임스탬프 + 레벨 + 메시지

**API**:
- `GET /api/v1/admin/stats` — 시스템 통계
- `GET /api/v1/admin/data/status` — 클라우드 서버 상태
- `GET /api/v1/admin/errors?limit=5` — 최근 에러

**검증**:
- [ ] 통계 카드 4개 모두 표시
- [ ] 클라우드 상태 실시간 갱신 (10초 폴링)
- [ ] 에러 로그 최근 5건 표시

---

### Step 3 — 유저 관리 + 규칙 열람

**목표**: 유저 목록 조회, 비활성화, **규칙 내용 열람**

**파일**:
- `pages/Admin/AdminUsers.tsx` (신규)

**구현 내용**:
1. **유저 목록 테이블**
   - 컬럼: 이메일, 닉네임, 가입일, 상태(온/오프라인), 규칙 수
   - 페이지네이션 (기존 API)
   - 검색 필터 (이메일, 닉네임)

2. **액션 버튼**
   - [상세] → 유저 상세 모달
   - 모달 내 [비활성화] → soft delete (is_active = false)

3. **유저 상세 모달** (규칙 열람)
   - 기본 정보: 이메일, 닉네임, 가입일, 상태
   - **규칙 목록**: 종목, 규칙명, 조건 요약, 활성 여부
   - 읽기 전용 (수정/삭제 불가)
   - 경고 텍스트: "체결 내역, 잔고, 수익률, API Key는 조회할 수 없습니다"

**API**:
- `GET /api/v1/admin/users` — 유저 목록
- `PATCH /api/v1/admin/users/:id` — 유저 상태 변경 (`{ is_active: false }`)
- `GET /api/v1/admin/users/:id/rules` — **유저 규칙 열람** (NEW)

**백엔드 추가 구현 필요**:
```python
@router.get("/users/{user_id}/rules")
def get_user_rules(user_id: str, _admin=Depends(require_admin), db: Session = Depends(get_db)):
    """어드민이 특정 유저의 규칙 목록을 조회 (읽기 전용)"""
    rules = db.query(Rule).filter(Rule.user_id == user_id).all()
    return {"success": True, "data": [rule.to_dict() for rule in rules]}
```

**검증**:
- [ ] 유저 목록 조회 + 페이지네이션
- [ ] 검색 필터 동작
- [ ] [상세] 클릭 → 모달에서 규칙 목록 + 조건 내용 표시
- [ ] 규칙 수정/삭제 버튼 없음 (읽기 전용)
- [ ] [비활성화] → is_active = false 변경

---

### Step 4 — 접속 통계 차트

**목표**: 하트비트 기반 DAU 차트, 기간 선택

**파일**:
- `pages/Admin/AdminStats.tsx` (신규)

**구현 내용**:
1. **현재 온라인 수** — 큰 숫자로 표시
2. **DAU 차트** (Recharts AreaChart)
   - X축: 날짜, Y축: DAU
   - 기간 선택: 7일 / 30일 / 90일

**API**:
- `GET /api/v1/admin/stats/connections?period=7d` — 접속 통계

**검증**:
- [ ] 현재 온라인 수 표시
- [ ] DAU 차트 표시
- [ ] 기간 선택 기능 정상 동작

---

### Step 5 — 시세 데이터 모니터링

**목표**: 클라우드 서버 시세 수집 상태 모니터링

**파일**:
- `pages/Admin/AdminData.tsx` (신규)

**구현 내용**:
1. **클라우드 서버 상태 카드**
   - 연결 상태 (정상/경고/오류)
   - 마지막 시세 수신 시간
   - 구독 종목 수
   - 일봉 수집량 (건/일)

2. **데이터 소스별 상태**
   - yfinance: 상태
   - KIS: 상태
   - 기타: 상태

**API**:
- `GET /api/v1/admin/data/status` — 클라우드 상태

**검증**:
- [ ] 클라우드 서버 상태 표시
- [ ] 데이터 소스별 상태 표시
- [ ] 10초 자동 갱신

---

### Step 6 — 서비스 키 관리

**목표**: 시세 수집용 서비스 키 등록/삭제

**파일**:
- `pages/Admin/AdminServiceKeys.tsx` (신규)

**구현 내용**:
1. **키 목록 테이블**
   - 키 ID, 소스 (KOSCOM/KIS/yfinance), 상태, 마지막 검증 시간
   - 키 값은 마스킹 (앞 4자리만)

2. **키 등록 폼**
   - 소스 선택 (드롭다운)
   - API 키 입력
   - 설명 (선택)

3. **삭제** — 확인 다이얼로그

**API**:
- `GET /api/v1/admin/service-keys` — 키 목록
- `POST /api/v1/admin/service-keys` — 키 등록
- `DELETE /api/v1/admin/service-keys/:id` — 키 삭제

**검증**:
- [ ] 서비스 키 목록 조회
- [ ] 새 키 등록 (DB 저장)
- [ ] 키 삭제 (확인 후)

---

### Step 7 — 전략 템플릿 CRUD

**목표**: 전략 템플릿 생성/수정/삭제 UI

**파일**:
- `pages/Admin/AdminTemplates.tsx` (신규)

**구현 내용**:
1. **템플릿 목록 테이블**
   - 이름, 카테고리, 난이도, 사용 수, 액션
   - [수정], [비활성화], [삭제] 버튼

2. **템플릿 생성/수정 모달**
   - 이름, 설명, 카테고리, 난이도
   - 규칙 JSON 또는 폼
   - 태그 (쉼표 구분)

**API** (기존):
- `GET /api/v1/admin/templates`
- `POST /api/v1/admin/templates`
- `PUT /api/v1/admin/templates/:id`
- `DELETE /api/v1/admin/templates/:id`

**검증**:
- [ ] 템플릿 목록 조회
- [ ] 새 템플릿 생성 → DB 저장
- [ ] 기존 템플릿 수정 → DB 업데이트
- [ ] 템플릿 비활성화/삭제

---

### Step 8 — 에러 로그 뷰어

**목표**: 시스템 에러 로그 조회, 필터링

**파일**:
- `pages/Admin/AdminErrors.tsx` (신규)

**구현 내용**:
1. **에러 로그 테이블**
   - 타임스탬프, 레벨 (ERROR/WARN), 메시지
   - 페이지네이션
   - 필터: 레벨, 날짜 범위

2. **상세 보기**
   - 행 클릭 → 모달에서 스택 트레이스 표시

3. **자동 갱신** — 10초 폴링

**API**:
- `GET /api/v1/admin/errors?limit=100&level=ERROR&start_date=2026-03-01`

**검증**:
- [ ] 에러 로그 목록 조회
- [ ] 필터 (레벨, 기간) 정상 동작
- [ ] 행 클릭 → 상세 모달 표시
- [ ] 10초 자동 갱신

---

## 2. 파일 목록

### 신규 생성 파일

| 파일 | 설명 |
|------|------|
| `components/AdminLayout.tsx` | 어드민 레이아웃 (사이드바 + 콘텐츠) |
| `pages/Admin/index.tsx` | 어드민 라우팅 (리팩토링) |
| `pages/Admin/AdminOverview.tsx` | 통계 요약 |
| `pages/Admin/AdminUsers.tsx` | 유저 관리 + 규칙 열람 |
| `pages/Admin/AdminStats.tsx` | 접속 통계 차트 |
| `pages/Admin/AdminData.tsx` | 시세 데이터 모니터링 |
| `pages/Admin/AdminServiceKeys.tsx` | 서비스 키 관리 |
| `pages/Admin/AdminTemplates.tsx` | 템플릿 CRUD |
| `pages/Admin/AdminErrors.tsx` | 에러 로그 뷰어 |

### 수정 파일

| 파일 | 변경 사항 |
|------|---------|
| `App.tsx` | `/admin/*` 라우트 등록 (AdminLayout 적용) |
| `services/admin.ts` | 규칙 열람, 서비스키, 에러, 통계 API 추가 |

### 삭제 파일

| 파일 | 이유 |
|------|------|
| `pages/AdminDashboard.tsx` | Admin/ 서브라우트로 재편 |

---

## 3. 의존성

### Unit 4 (클라우드 서버 어드민 API)

Step 2-8 모든 단계가 Unit 4의 어드민 API에 의존:

```
⚠️ Unit 4 구현 완료 대기:
- GET    /api/v1/admin/stats/connections     (접속 통계)
- GET    /api/v1/admin/data/status           (클라우드 상태)
- GET    /api/v1/admin/users/:id/rules       (유저 규칙 열람 — NEW)
- PATCH  /api/v1/admin/users/:id             (유저 비활성화)
- GET    /api/v1/admin/errors                (에러 로그)
- GET    /api/v1/admin/service-keys          (서비스 키)
- POST   /api/v1/admin/service-keys          (키 등록)
- DELETE /api/v1/admin/service-keys/:id      (키 삭제)
```

**Step 1 (라우팅) 은 Unit 4 대기 불필요 → 먼저 구현 가능**

---

## 4. 미결 사항 해소

| 항목 | 결정 |
|------|------|
| 어드민이 유저 규칙 내용 볼 수 있는지 | **가능** — 읽기 전용. 수정/삭제 불가. `GET /admin/users/:id/rules` |
| 어드민 계정 생성 방식 | DB 수동 INSERT (초기). v2에서 관리 페이지 |
| 클라우드 서버 모니터링 세부 지표 | 상태, 마지막 시세, 구독 종목 수, 일봉 수집량 |
| 접속 통계 차트 기간 | 선택 가능: 7일 / 30일 / 90일 |

---

## 5. 커밋 계획

| Step | 커밋 메시지 |
|------|-----------|
| 1 | `feat: 어드민 레이아웃 + 사이드바 + 서브라우팅` |
| 2 | `feat: 어드민 대시보드 (통계 카드 + 클라우드 상태 + 에러)` |
| 3 | `feat: 유저 관리 + 규칙 열람 (읽기 전용)` |
| 4 | `feat: 접속 통계 차트 (DAU, 기간 선택)` |
| 5 | `feat: 시세 데이터 모니터링` |
| 6 | `feat: 서비스 키 관리 (등록/삭제)` |
| 7 | `feat: 전략 템플릿 CRUD` |
| 8 | `feat: 에러 로그 뷰어 (필터 + 상세)` |

---

## 6. 검증 체크리스트

### 최종 수용 기준

- [ ] admin 계정으로 `/admin` 접근 → 사이드바 + 대시보드 표시
- [ ] 일반 유저로 `/admin` 접근 → 403 또는 리다이렉트
- [ ] 유저 목록 조회 (이메일, 닉네임, 가입일, 접속 상태, 규칙 수) 정상
- [ ] **유저 [상세] → 규칙 내용 열람 (읽기 전용)**
- [ ] 유저 비활성화 동작
- [ ] 시스템 통계 (유저 수, 온라인 수, 활성 규칙, 에러 수) 표시
- [ ] 접속 통계 차트 (DAU, 기간 선택) 표시
- [ ] 전략 템플릿 CRUD 정상 동작
- [ ] 서비스 키 등록/삭제 정상 동작
- [ ] 클라우드 서버 상태 표시
- [ ] 에러 로그 조회 + 필터
- [ ] 개인 금융정보 접근 불가 (구조적 확인)
- [ ] `npm run lint` 통과
- [ ] `npm run build` 성공

---

**마지막 갱신**: 2026-03-09
