# 어드민 페이지 구현 계획서 (admin)

> 작성일: 2026-03-05 | 상태: 초안 | Unit 7 (Phase 3-C)

---

## 0. 현황

### 기존 코드 상태

**백엔드 (backend/app/api/admin.py)**
- ✅ 통계 API (`GET /api/admin/stats`) — 유저 수, 템플릿 수, 온보딩 현황
- ✅ 유저 목록 API (`GET /api/admin/users`) — 페이지네이션 지원
- ✅ 템플릿 CRUD API — POST/PUT/DELETE 구현 완료
- ❌ 유저 상태 변경 (비활성화) — 미구현
- ❌ 접속 통계 (하트비트) — 미구현
- ❌ 시세 데이터 상태 모니터링 — 미구현
- ❌ 서비스 키 관리 API — 미구현
- ❌ 에러 로그 API — 미구현

**프론트엔드 (frontend/src/)**
- ✅ `services/admin.ts` — 백엔드 API 클라이언트 기본 구조
- ✅ `pages/AdminDashboard.tsx` — 통계 카드 4개, 사용자 목록, 템플릿 관리 (기본 레이아웃)
- ❌ 별도 페이지 라우팅 — `/admin/users`, `/admin/stats`, `/admin/data` 등 미구현
- ❌ 권한 가드 — 일반 유저 접근 차단 미구현
- ❌ 상태 변경 UI — 유저 비활성화 버튼 미구현
- ❌ 차트 통계 — 접속 추이, 시장 지표 미구현
- ❌ 에러 로그 뷰어 — 미구현

### 설계 원칙 (spec.md 재확인)
- **개인 금융정보 차단**: 어드민도 체결, 잔고, 수익률, API Key 접근 불가 (구조적 보장)
- **클라우드 API 의존**: Unit 4 어드민 API에 의존
- **역할 기반 접근**: JWT role=admin만 접근 가능

> **경로 참고**: 현재 `backend/app/`으로 참조하지만 cloud-server plan Step 11에서
> `cloud_server/`로 마이그레이션 예정. 구현 시점의 실제 경로를 따를 것.

---

## 1. 구현 단계

### Step 1 — 어드민 라우팅 + 권한 가드

**목표**: 어드민 라우팅 구조 구성 및 비어드민 접근 차단

**파일**:
- `frontend/src/pages/Admin.tsx` — 어드민 레이아웃 (사이드바, 네비게이션)
- `frontend/src/components/AdminGuard.tsx` — 권한 검사 컴포넌트
- `frontend/src/App.tsx` — 라우트 등록

**구현 내용**:
```
1. ProtectedRoute 또는 AdminGuard 컴포넌트 작성
   - localStorage JWT 토큰 검증
   - role == "admin" 확인
   - 권한 없으면 403 또는 홈으로 리다이렉트

2. 어드민 레이아웃 컴포넌트
   - 좌측 네비게이션 (대시보드, 유저, 통계, 시세, 서비스키, 템플릿, 에러로그)
   - 우측 콘텐츠 영역 (Outlet)

3. 라우트 구조
   /admin
     /users
     /stats
     /data
     /service-keys
     /templates
     /errors
```

**검증**:
- [ ] 어드민 계정으로 `/admin` 접근 → 대시보드 표시
- [ ] 일반 유저로 `/admin` 접근 → 403 또는 홈으로 리다이렉트
- [ ] 네비게이션 링크 모두 정상 동작

---

### Step 2 — 어드민 대시보드 (통계 요약)

**목표**: 시스템 상태, 사용자 활동, 최근 에러를 한눈에 보기

**파일**:
- `frontend/src/pages/Admin/Dashboard.tsx` — 대시보드 메인 페이지
- `frontend/src/services/admin.ts` — API 클라이언트 추가 (클라우드 상태, 에러 로그)

**구현 내용**:
```
1. 통계 카드 4개
   - 전체 유저: stats.users.total
   - 온라인 유저: stats.connections.online (NEW)
   - 활성 규칙: stats.rules.active (NEW)
   - 1시간 내 에러: stats.errors.count_1h (NEW)

2. 클라우드 서버 상태
   - 상태: 🟢 정상 / 🟡 경고 / 🔴 오류
   - 마지막 시세 수신 시간
   - 구독 종목 수
   - 일봉 수집량 (건/일)

3. 최근 에러 로그 (5건)
   - 타임스탬프
   - 로그 레벨 (ERROR, WARN)
   - 메시지
```

**API 필요** (Unit 4):
- `GET /api/v1/admin/stats/connections` → 온라인 유저 수
- `GET /api/v1/admin/data/status` → 클라우드 서버 상태
- `GET /api/v1/admin/errors?limit=5` → 최근 에러

**검증**:
- [ ] 통계 카드 4개 모두 표시
- [ ] 클라우드 상태 실시간 갱신 (10초 폴링)
- [ ] 에러 로그 최근 5건 표시

---

### Step 3 — 유저 관리 페이지

**목표**: 유저 목록 조회, 상태 변경 (비활성화)

**파일**:
- `frontend/src/pages/Admin/Users.tsx` — 유저 목록 페이지
- `backend/app/api/admin.py` — PATCH /api/admin/users/:id 추가

**구현 내용**:
```
1. 유저 목록 테이블
   - 이메일, 닉네임, 가입일, 상태 (온라인/오프라인)
   - 페이지네이션 (기존 API)
   - 검색 필터 (이메일, 닉네임)

2. 액션 버튼
   - [비활성화] → soft delete (is_active = false)
   - 비활성화된 유저 목록에 표시

3. UI
   - 테이블 형식
   - 상태 배지 (🟢 활성, ⚫ 비활성)
```

**API 필요**:
- `PATCH /api/admin/users/:id` → { "is_active": false }

**백엔드 추가 구현**:
```python
@router.patch("/users/{user_id}")
def update_user_status(user_id: str, body: dict, _admin=Depends(require_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    user.is_active = body.get("is_active", user.is_active)
    db.commit()
    return {"success": True}
```

**검증**:
- [ ] 유저 목록 조회 성공
- [ ] 비활성화 버튼 클릭 → is_active = false 변경
- [ ] 비활성화된 유저 상태 업데이트 확인

---

### Step 4 — 접속 통계 차트

**목표**: 하트비트 기반 온라인 추이, DAU, MAU 차트 표시

**파일**:
- `frontend/src/pages/Admin/Stats.tsx` — 통계 차트 페이지
- `backend/app/api/admin.py` — GET /api/admin/stats/connections 추가

**구현 내용**:
```
1. 차트 (Recharts)
   - 온라인 유저 시계열 (30분 단위, 24시간)
   - DAU (일별, 최근 30일)
   - MAU (월별, 최근 12개월)
   - 주기 선택 (24시간, 7일, 30일, 90일)

2. 데이터 구조
   {
     "period": "7d",
     "data": [
       { "timestamp": "2026-03-05T10:00:00Z", "online": 45, "dau": 123, "mau": 1234 }
     ]
   }
```

**API 필요** (Unit 4):
- `GET /api/v1/admin/stats/connections?period=7d` → 하트비트 통계

**검증**:
- [ ] 온라인 유저 차트 표시
- [ ] DAU, MAU 차트 표시
- [ ] 주기 선택 기능 정상 동작

---

### Step 5 — 서비스 키 관리

**목표**: 시세 수집용 KOSCOM/키움 서비스 키 관리 (클라우드 서버)

**파일**:
- `frontend/src/pages/Admin/ServiceKeys.tsx` — 키 관리 페이지
- `backend/app/api/admin.py` — GET/POST/DELETE /api/admin/service-keys 추가

**구현 내용**:
```
1. 키 목록 테이블
   - 키 ID
   - 소스 (KOSCOM, Kiwoom, yfinance)
   - 상태 (활성, 만료, 오류)
   - 마지막 검증 시간
   - 액션 (삭제)

2. 키 등록 폼
   - 소스 선택 (드롭다운)
   - API 키 입력
   - 설명 (선택)
   - [등록] 버튼

3. 삭제 확인 대화
   - "정말 삭제하시겠습니까?" 경고
```

**API 필요** (Unit 4):
- `GET /api/v1/admin/service-keys` → 키 목록
- `POST /api/v1/admin/service-keys` → 키 등록 (source, key, description)
- `DELETE /api/v1/admin/service-keys/:id` → 키 삭제

**백엔드 추가 구현**:
```python
class ServiceKeyBody(BaseModel):
    source: str  # "KOSCOM", "Kiwoom", "yfinance"
    key: str
    description: str | None = None

@router.get("/service-keys")
def list_service_keys(...):
    # DB에서 조회 (마스킹: key 앞 4글자만)
    pass

@router.post("/service-keys")
def create_service_key(body: ServiceKeyBody, ...):
    # 새 키 저장
    pass

@router.delete("/service-keys/{key_id}")
def delete_service_key(key_id: int, ...):
    # 키 삭제
    pass
```

**검증**:
- [ ] 서비스 키 목록 조회
- [ ] 새 키 등록 (DB 저장)
- [ ] 키 삭제 (소프트 삭제)

---

### Step 6 — 전략 템플릿 CRUD

**목표**: 전략 템플릿 생성/수정/삭제 UI 완성

**파일**:
- `frontend/src/pages/Admin/Templates.tsx` — 템플릿 관리 페이지 개선
- `frontend/src/components/TemplateForm.tsx` — 템플릿 폼 컴포넌트 (신규)

**구현 내용**:
```
1. 템플릿 목록
   - 기존 AdminDashboard의 템플릿 테이블 확장
   - 이름, 카테고리, 난이도, 사용 수, 액션
   - [수정], [비활성화], [삭제] 버튼

2. 템플릿 생성/수정 모달
   - 이름, 설명, 카테고리, 난이도
   - 규칙 JSON 에디터 (또는 폼)
   - 백테스트 요약 (CAGR, MDD, Sharpe)
   - 태그 (쉼표 구분)
   - [저장], [취소] 버튼

3. 기존 API 활용
   - POST /api/admin/templates
   - PUT /api/admin/templates/{id}
   - DELETE /api/admin/templates/{id}
```

**프론트엔드 추가 구현**:
```typescript
export const adminApi = {
  // 기존
  createTemplate: (body: TemplateBody) =>
    api.post('/api/admin/templates', body).then(r => r.data),

  updateTemplate: (id: number, body: TemplateBody) =>
    api.put(`/api/admin/templates/${id}`, body).then(r => r.data),

  deleteTemplate: (id: number) =>
    api.delete(`/api/admin/templates/${id}`).then(r => r.data),
}
```

**검증**:
- [ ] 템플릿 목록 조회 및 필터 정상 동작
- [ ] 새 템플릿 생성 → DB 저장
- [ ] 기존 템플릿 수정 → DB 업데이트
- [ ] 템플릿 비활성화 → is_active = false

---

### Step 7 — 시세 데이터 모니터링

**목표**: 클라우드 서버 시세 수집 상태, 에러 모니터링

**파일**:
- `frontend/src/pages/Admin/DataStatus.tsx` — 시세 모니터링 페이지

**구현 내용**:
```
1. 클라우드 서버 상태
   - 연결 상태 (🟢 정상 / 🟡 경고 / 🔴 오류)
   - 마지막 시세 수신 시간
   - 구독 종목 수
   - 일봉 수집량 (건/일)

2. 데이터 소스별 상태
   - yfinance: ✅ 정상 / ⚠️ 지연 / ❌ 오류
   - KOSCOM: 상태 정보
   - 키움: 상태 정보

3. 최근 데이터 수집 로그
   - 타임스탠프, 종목, 건수, 상태
```

**API 필요** (Unit 4):
- `GET /api/v1/admin/data/status` → 클라우드 상태

**검증**:
- [ ] 클라우드 서버 상태 표시
- [ ] 데이터 소스별 상태 표시
- [ ] 수집 로그 10초 자동 갱신

---

### Step 8 — 에러 로그 뷰어

**목표**: 시스템 에러 로그 조회, 필터링, 검색

**파일**:
- `frontend/src/pages/Admin/ErrorLogs.tsx` — 에러 로그 페이지

**구현 내용**:
```
1. 에러 로그 테이블
   - 타임스탠프, 레벨 (ERROR/WARN/INFO), 메시지, 스택 트레이스
   - 페이지네이션
   - 필터: 레벨, 날짜 범위, 검색어

2. 상세 보기
   - 클릭 시 모달에서 전체 스택 트레이스 표시

3. 내보내기
   - CSV 다운로드 기능 (선택)
```

**API 필요** (Unit 4):
- `GET /api/v1/admin/errors?limit=100&level=ERROR&start_date=2026-03-01` → 에러 로그

**검증**:
- [ ] 에러 로그 목록 조회
- [ ] 필터 및 검색 정상 동작
- [ ] 상세 보기 모달 표시

---

## 2. 파일 목록

### 신규 생성 파일

| 파일 | 설명 |
|------|------|
| `frontend/src/pages/Admin.tsx` | 어드민 레이아웃 (사이드바, 라우트 정의) |
| `frontend/src/pages/Admin/Dashboard.tsx` | 어드민 대시보드 |
| `frontend/src/pages/Admin/Users.tsx` | 유저 관리 |
| `frontend/src/pages/Admin/Stats.tsx` | 접속 통계 차트 |
| `frontend/src/pages/Admin/ServiceKeys.tsx` | 서비스 키 관리 |
| `frontend/src/pages/Admin/Templates.tsx` | 템플릿 관리 (기존 AdminDashboard 템플릿 부분 분리) |
| `frontend/src/pages/Admin/DataStatus.tsx` | 시세 모니터링 |
| `frontend/src/pages/Admin/ErrorLogs.tsx` | 에러 로그 뷰어 |
| `frontend/src/components/AdminGuard.tsx` | 권한 검사 컴포넌트 |
| `frontend/src/components/TemplateForm.tsx` | 템플릿 폼 컴포넌트 (재사용 가능) |

### 수정 파일

| 파일 | 변경 사항 |
|------|---------|
| `backend/app/api/admin.py` | PATCH /api/admin/users/:id, 추가 API 스텁 |
| `backend/app/models/auth.py` | User 모델에 is_active 필드 추가 (필요시) |
| `frontend/src/App.tsx` | 어드민 라우트 등록 |
| `frontend/src/services/admin.ts` | API 클라이언트 메서드 추가 |
| `frontend/src/pages/AdminDashboard.tsx` | 기존 코드 유지 또는 통합 (거대 화면화 방지) |

---

## 3. 의존성

### Unit 4 (클라우드 서버 어드민 API)

Step 2-8 모든 단계가 Unit 4의 어드민 API에 의존:

```
⚠️ Unit 4 구현 완료 대기:
- GET /api/v1/admin/stats/connections
- GET /api/v1/admin/data/status
- GET /api/v1/admin/errors
- GET /api/v1/admin/service-keys
- POST /api/v1/admin/service-keys
- DELETE /api/v1/admin/service-keys/:id
```

**Step 1 (라우팅) 은 Unit 4 대기 불필요 → 먼저 구현 가능**

---

## 4. 미결 사항 처리

### 미결 사항 (spec.md §10)

| 항목 | 결정 | 비고 |
|------|------|------|
| 어드민이 유저 규칙 내용 볼 수 있는지 | **불가능** | 개인 금융정보 보호 원칙. 어드민도 규칙 내용 비표시. 통계만 표시. |
| 어드민 계정 생성 방식 | DB 수동 INSERT | 초기 구현 단계. v2에서 관리 페이지 추가 예정. |
| 클라우드 서버 모니터링 세부 지표 | spec.md §4.1 따름 | 상태, 마지막 시세, 구독 종목, 일봉 수집량 |
| 접속 통계 차트 기간 | **선택 가능 (24h/7d/30d/90d)** | Step 4에서 드롭다운 제공 |

### 설계 원칙 확인

- ✅ **개인 금융정보 차단**: 어드민이 접근할 수 없는 데이터 (체결, 잔고, 수익률, API Key)는 API 자체에서 응답하지 않음 (백엔드 구조적 보장)
- ✅ **역할 기반 접근**: 모든 어드민 API는 `require_admin` 의존성 확인
- ✅ **클라우드 API 의존**: Unit 4 구현 완료까지 Step 1 먼저, Step 2-8은 병렬 개발 가능 (Mock/Stub)

---

## 5. 커밋 계획

| 단계 | 커밋 메시지 | 파일 |
|------|------------|------|
| Step 1 | `feat: Step 1 — 어드민 라우팅 + 권한 가드` | App.tsx, Admin.tsx, AdminGuard.tsx |
| Step 2 | `feat: Step 2 — 어드민 대시보드 (통계 요약)` | Admin/Dashboard.tsx, admin.ts (API 스텁) |
| Step 3 | `feat: Step 3 — 유저 관리 페이지 + PATCH 상태 변경` | Admin/Users.tsx, admin.py (PATCH /users/:id) |
| Step 4 | `feat: Step 4 — 접속 통계 차트` | Admin/Stats.tsx, admin.ts (Mock) |
| Step 5 | `feat: Step 5 — 서비스 키 관리` | Admin/ServiceKeys.tsx, admin.py (GET/POST/DELETE) |
| Step 6 | `feat: Step 6 — 템플릿 CRUD UI` | Admin/Templates.tsx, TemplateForm.tsx, admin.ts |
| Step 7 | `feat: Step 7 — 시세 데이터 모니터링` | Admin/DataStatus.tsx |
| Step 8 | `feat: Step 8 — 에러 로그 뷰어` | Admin/ErrorLogs.tsx |

---

## 6. 검증 체크리스트

### 최종 수용 기준 (spec.md §7)

- [ ] admin 계정으로 `/admin` 접근 → 대시보드 표시
- [ ] 일반 유저로 `/admin` 접근 → 403 또는 리다이렉트
- [ ] 유저 목록 조회 (이메일, 닉네임, 가입일, 접속 상태) 정상
- [ ] 시스템 통계 (유저 수, 온라인 수, 에러 수) 표시
- [ ] 전략 템플릿 CRUD 정상 동작
- [ ] 서비스 키 등록/삭제 정상 동작
- [ ] 클라우드 서버 상태 표시
- [ ] 개인 금융정보 접근 불가 (구조적 확인)

---

## 7. 개발 프로세스

### 병렬 개발 가능성

- **Step 1 (라우팅)**: 즉시 시작 가능 (Unit 4 대기 없음)
- **Step 2-8**: Unit 4 API 스펙 확정 후, Mock 데이터로 병렬 개발 가능

### 주의사항

- `git commit` 절대 금지 — 모든 Step 완료 후 일괄 커밋
- 각 Step 완료 시 `spec/admin/reports/stepN.md`에 기록
- 단위별로 작은 PR 크기 유지 (리뷰 용이)

---

**마지막 갱신**: 2026-03-05
