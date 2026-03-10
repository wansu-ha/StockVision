# 어드민 페이지 구현 계획서 (admin)

> 작성일: 2026-03-05 | 상태: 구현 완료 | Unit 6 (Phase 3-C)

---

## 0. 현황 (구현 완료 시점)

### 백엔드 (cloud_server/api/admin.py)

- ✅ `GET /api/v1/admin/stats` — 유저 수, 활성 유저, 규칙 수, 클라이언트 수
- ✅ `GET /api/v1/admin/users` — 페이지네이션 + 검색 (`{ success, users, total, page, limit }`)
- ✅ `PATCH /api/v1/admin/users/:id` — 유저 상태 변경
- ✅ `GET/POST/DELETE /api/v1/admin/service-keys` — 서비스 키 CRUD
- ✅ `GET/POST/PUT/DELETE /api/v1/admin/templates` — 템플릿 CRUD
- ✅ `GET /api/v1/admin/collector-status` — 클라우드 서버 수집기 상태
- ❌ `GET /api/v1/admin/stats/connections` — 접속 통계 (미구현)
- ❌ `GET /api/v1/admin/ai/stats` — AI 분석 통계 (미구현)
- ❌ `GET /api/v1/admin/ai/recent` — AI 최근 분석 (미구현)
- ❌ `GET /api/v1/admin/errors` — 에러 로그 (미구현)

### 프론트엔드 (frontend/src/)

- ✅ `pages/Admin/index.tsx` — 사이드바 레이아웃 (7개 메뉴)
- ✅ `pages/Admin/Dashboard.tsx` — 통계 카드 + 클라우드 상태 + AI 요약 + 최근 에러
- ✅ `pages/Admin/Users.tsx` — 유저 목록 (검색, 페이지네이션, 역할/인증/마지막로그인)
- ✅ `pages/Admin/Stats.tsx` — 접속 통계 차트 (7/30/90일)
- ✅ `pages/Admin/ServiceKeys.tsx` — 서비스 키 관리 (api_key/api_secret/app_name)
- ✅ `pages/Admin/Templates.tsx` — 템플릿 CRUD (name/description/category/is_public)
- ✅ `pages/Admin/AiMonitor.tsx` — AI 분석 모니터링 (토큰/비용/최근결과)
- ✅ `pages/Admin/ErrorLogs.tsx` — 에러 로그 뷰어 (레벨 필터, 페이지네이션, 상세 모달)
- ✅ `components/AdminGuard.tsx` — JWT role 검사 + DEV bypass
- ✅ `services/admin.ts` — 어드민 API 클라이언트 (11개 메서드)
- 🗑️ `pages/AdminDashboard.tsx` — 삭제 (레거시, 새 Admin/ 레이아웃으로 대체)
- 🗑️ `pages/Admin/DataStatus.tsx` — 삭제 (대시보드에 통합)

### 설계 원칙
- **개인 금융정보 차단**: 어드민도 체결, 잔고, 수익률, API Key 접근 불가 (구조적 보장)
- **클라우드 API 의존**: `cloud_server/api/admin.py`의 어드민 API 사용
- **역할 기반 접근**: JWT role=admin만 접근 가능 (AdminGuard)
- **공유 계정**: 일반 유저/어드민 동일 users 테이블, role 컬럼으로 구분

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
     /service-keys
     /templates
     /ai
     /errors
```

**검증**:
- [ ] 어드민 계정으로 `/admin` 접근 → 대시보드 표시
- [ ] 일반 유저로 `/admin` 접근 → 403 또는 홈으로 리다이렉트
- [ ] 네비게이션 링크 모두 정상 동작

---

### Step 2 — 어드민 대시보드 (통계 요약)

**목표**: 시스템 상태, 사용자 활동, AI 비용, 최근 에러를 한눈에 보기

**파일**:
- `frontend/src/pages/Admin/Dashboard.tsx` — 대시보드 메인 페이지
- `frontend/src/services/admin.ts` — API 클라이언트 추가

**구현 내용**:
```
1. 통계 카드 4개
   - 전체 유저: stats.users.total
   - 활성 유저: stats.connections.online
   - 활성 규칙: stats.rules.active
   - 1시간 내 에러: stats.errors.count_1h

2. 클라우드 서버 상태
   - 상태: 🟢 정상 / 🟡 경고 / 🔴 오류
   - 업타임, CPU/메모리 (psutil)
   - 구독 종목 수, 마지막 수집 시각
   - 연결 클라이언트 수, 일봉 수집량 (건/일)

3. AI 분석 요약
   - 오늘 분석 수, 토큰 (in/out), 추정 비용, 에러 수

4. 최근 에러 로그 (5건)
   - 타임스탬프, 레벨 (ERROR/WARN), 메시지
```

**API 사용**:
- `GET /api/v1/admin/stats` → 통계 카드 (유저 수, 활성 유저, 규칙 수, 클라이언트 수)
- `GET /api/v1/admin/collector-status` → 클라우드 서버 상태 (업타임, CPU/MEM 포함)
- `GET /api/v1/admin/ai/stats` → AI 분석 통계 (미구현, 폴백 처리)
- `GET /api/v1/admin/errors?limit=5` → 최근 에러 (미구현, 폴백 처리)

**검증**:
- [ ] 통계 카드 4개 모두 표시
- [ ] 클라우드 상태 + AI 분석 요약 실시간 갱신 (10초 폴링)
- [ ] 에러 로그 최근 5건 표시

---

### Step 3 — 유저 관리 페이지

**목표**: 유저 목록 조회, 상태 변경 (비활성화)

**파일**:
- `frontend/src/pages/Admin/Users.tsx` — 유저 목록 페이지

**구현 내용**:
```
1. 유저 목록 테이블
   - 이메일, 닉네임, 역할, 이메일 인증 여부, 활성/비활성, 가입일, 마지막 로그인
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
- `PATCH /api/v1/admin/users/:id` → { "is_active": false }

**검증**:
- [ ] 유저 목록 조회 성공
- [ ] 비활성화 버튼 클릭 → is_active = false 변경
- [ ] 비활성화된 유저 상태 업데이트 확인

---

### Step 4 — 접속 통계 차트

**목표**: 하트비트 기반 온라인 추이, DAU 차트 표시

**파일**:
- `frontend/src/pages/Admin/Stats.tsx` — 통계 차트 페이지

**구현 내용**:
```
1. 차트 (Recharts)
   - 온라인 유저 시계열 (30분 단위)
   - DAU (일별)
   - 기간 선택: 7일 / 30일 / 90일

2. 데이터 구조
   {
     "period": "7d",
     "data": [
       { "timestamp": "2026-03-05T10:00:00Z", "online": 45, "dau": 123 }
     ]
   }
```

**API 필요** (Unit 4):
- `GET /api/v1/admin/stats/connections?period=7d` → 하트비트 통계

> raw 데이터: 1년 보관 후 자동 정리 (정보통신망법). MAU 차트는 v2.

**검증**:
- [ ] 온라인 유저 차트 표시
- [ ] DAU 차트 표시
- [ ] 기간 선택 (7/30/90일) 정상 동작

---

### Step 5 — 서비스 키 관리

**목표**: 시세 수집용 증권사 서비스 키 관리 (클라우드 서버)

**파일**:
- `frontend/src/pages/Admin/ServiceKeys.tsx` — 키 관리 페이지

**구현 내용**:
```
1. 키 목록 테이블
   - 키 ID, 앱 이름
   - 상태 (활성/비활성)
   - 마지막 사용 시각
   - Secret: 마스킹 (앞 4자리만)
   - 액션 (삭제)

2. 키 등록 폼
   - API Key, API Secret 입력
   - 앱 이름 (선택)
   - [등록] 버튼

3. 삭제 확인 대화
   - "정말 삭제하시겠습니까?" 경고
```

**API 필요** (Unit 4):
- `GET /api/v1/admin/service-keys` → 키 목록 (secret 마스킹)
- `POST /api/v1/admin/service-keys` → 키 등록
- `DELETE /api/v1/admin/service-keys/:id` → 키 삭제

**검증**:
- [ ] 서비스 키 목록 조회 (secret 마스킹 확인)
- [ ] 새 키 등록 (DB 저장)
- [ ] 키 삭제

---

### Step 6 — 전략 템플릿 CRUD

**목표**: 전략 템플릿 생성/수정/삭제 UI 완성

**파일**:
- `frontend/src/pages/Admin/Templates.tsx` — 템플릿 관리 페이지 (폼 인라인)

**구현 내용**:
```
1. 템플릿 목록
   - 이름, 카테고리, 설명, 공개 여부, 액션
   - [삭제] 버튼

2. 인라인 생성 폼 (토글)
   - 이름, 카테고리, 설명
   - [저장] 버튼

3. 스키마: id, name, description, category, is_public, created_by, created_at
```

**API 필요** (Unit 4):
- `GET/POST/PUT/DELETE /api/v1/admin/templates`

**검증**:
- [ ] 템플릿 목록 조회
- [ ] 새 템플릿 생성 → DB 저장
- [ ] 기존 템플릿 수정 → DB 업데이트
- [ ] 템플릿 삭제

---

### ~~Step 7 — 시세 데이터 모니터링~~ (삭제됨)

> 대시보드(Step 2)에 클라우드 서버 상태 섹션으로 통합.
> `/admin/data` 라우트 삭제, `DataStatus.tsx` 삭제.
> API: `GET /api/v1/admin/collector-status` (기존 `data/status` → `collector-status`로 변경)

---

### Step 8 — AI 분석 모니터링

**목표**: AI 분석 사용량, 토큰/비용 추적, 최근 결과 열람

**파일**:
- `frontend/src/pages/Admin/AiMonitor.tsx` — AI 모니터링 페이지

**구현 내용**:
```
1. 통계 카드
   - 오늘 분석 수, 이번 달 분석 수
   - 토큰 사용량 (input/output)
   - 추정 비용 (모델별 단가 × 토큰)
   - 에러율

2. 일별 추이 차트 (Recharts)
   - 분석 수, 토큰 사용량, 비용 시계열

3. 최근 분석 결과 샘플
   - 종목, 분석 타입, 점수, 텍스트 (접기/펼치기)
   - 유저 ID는 비표시 (전체 샘플만)
```

**API 필요** (Unit 4):
- `GET /api/v1/admin/ai/stats` → 일별/월별 분석 수, 토큰, 비용
- `GET /api/v1/admin/ai/recent` → 최근 분석 결과 (유저 ID 제외)

**검증**:
- [ ] AI 통계 카드 표시 (분석 수, 토큰, 비용)
- [ ] 일별 추이 차트 표시
- [ ] 최근 분석 결과 샘플 열람 (유저 ID 비표시)

---

### Step 9 — 에러 로그 뷰어

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
| `frontend/src/pages/Admin/index.tsx` | 어드민 레이아웃 (사이드바 7개 메뉴, Outlet) |
| `frontend/src/pages/Admin/Dashboard.tsx` | 어드민 대시보드 (통계 + 서버 + AI + 에러) |
| `frontend/src/pages/Admin/Users.tsx` | 유저 관리 (검색, 페이지네이션) |
| `frontend/src/pages/Admin/Stats.tsx` | 접속 통계 차트 (7/30/90일) |
| `frontend/src/pages/Admin/ServiceKeys.tsx` | 서비스 키 관리 (api_key/api_secret/app_name) |
| `frontend/src/pages/Admin/Templates.tsx` | 템플릿 관리 (인라인 폼) |
| `frontend/src/pages/Admin/AiMonitor.tsx` | AI 분석 모니터링 (토큰/비용/최근결과) |
| `frontend/src/pages/Admin/ErrorLogs.tsx` | 에러 로그 뷰어 (레벨필터, 상세모달) |
| `frontend/src/components/AdminGuard.tsx` | 권한 검사 (JWT role + DEV bypass) |

### 수정 파일

| 파일 | 변경 사항 |
|------|---------|
| `frontend/src/App.tsx` | 어드민 라우트 등록, 레거시 라우트 제거 |
| `frontend/src/services/admin.ts` | API 클라이언트 (11개 메서드, cloud_server 스키마 맞춤) |

### 삭제 파일

| 파일 | 이유 |
|------|------|
| `frontend/src/pages/AdminDashboard.tsx` | 레거시 단일 페이지, Admin/ 레이아웃으로 대체 |
| `frontend/src/pages/Admin/DataStatus.tsx` | 대시보드에 통합, 별도 페이지 불필요 |

---

## 3. 의존성

### Unit 4 (클라우드 서버 어드민 API)

구현 완료된 백엔드 API:
- ✅ `GET /api/v1/admin/stats` — 통계
- ✅ `GET /api/v1/admin/users` + `PATCH` — 유저 관리
- ✅ `GET/POST/DELETE /api/v1/admin/service-keys` — 서비스 키
- ✅ `GET/POST/PUT/DELETE /api/v1/admin/templates` — 템플릿
- ✅ `GET /api/v1/admin/collector-status` — 수집기 상태

미구현 (프론트 UI는 완료, 그레이스풀 폴백):
- ❌ `GET /api/v1/admin/stats/connections` — 접속 통계
- ❌ `GET /api/v1/admin/ai/stats` — AI 분석 통계
- ❌ `GET /api/v1/admin/ai/recent` — AI 최근 분석
- ❌ `GET /api/v1/admin/errors` — 에러 로그

---

## 4. 미결 사항 처리

### 미결 사항 (spec.md §10 — 전부 해결됨)

| 항목 | 결정 | 비고 |
|------|------|------|
| 어드민이 유저 규칙 내용 볼 수 있는지 | **접근 제외** | 규칙 "수"만 집계. 나중에 감사 로그 도입 시 재검토 |
| 어드민 계정 생성 방식 | **seed** (`admin@stockvision.dev`) | DB 직접 삽입 |
| 클라우드 서버 모니터링 세부 지표 | **5개 카테고리** | 서버 상태, 시세 수집, 클라이언트, 에러, AI 분석 (spec §6) |
| 접속 통계 차트 기간 | **7/30/90일 선택** | raw 데이터 1년 보관 (정보통신망법) |

### 데이터 접근 정책 (spec §6)

- **볼 수 있는 것**: 유저 메타, 운영 통계, 하트비트, 서버 상태, AI 분석 (비용 포함), 서비스 키 (마스킹), 템플릿, 관심종목 집계, 에러 로그
- **접근 제외**: 개별 유저 규칙 내용, 개별 유저 관심종목, AI 분석 유저별 이력
- **아키텍처상 불가**: 체결/잔고/수익률/증권사 키/거래 집계 (로컬에만 존재)

### 설계 원칙

- ✅ **개인 금융정보 차단**: 로컬 데이터는 클라우드에 올라오지 않음 (구조적 보장)
- ✅ **전략 규칙 보호**: 개인 투자 전략 = 개인정보 취급, 어드민도 열람 불가
- ✅ **역할 기반 접근**: 모든 어드민 API는 `require_admin` 의존성 확인
- ✅ **클라우드 API 의존**: Step 1 먼저, Step 2-9은 Mock으로 병렬 개발 가능

---

## 5. 커밋 계획 (실제)

> 일괄 커밋 방식으로 진행 (workflow 규칙)

| 커밋 | 메시지 | 주요 파일 |
|------|--------|---------|
| 1 | `docs: admin spec/plan 초안` | spec/admin/spec.md, plan.md |
| 2 | `feat: 어드민 UI 전체 구현 + 레거시 정리` | Admin/*.tsx, AdminGuard.tsx, admin.ts, App.tsx |
| 3 | `docs: admin spec/plan 구현 완료 반영` | spec/admin/spec.md, plan.md |

---

## 6. 검증 체크리스트

### 최종 수용 기준 (spec.md §7)

- [x] admin 계정으로 `/admin` 접근 → 대시보드 표시
- [x] 일반 유저로 `/admin` 접근 → 403 또는 리다이렉트 (AdminGuard)
- [x] 유저 목록 조회 (이메일, 닉네임, 역할, 인증 여부, 활성 상태, 가입일, 마지막 로그인)
- [x] 시스템 통계 (유저 수, 활성 유저 수, 규칙 수, 활성 클라이언트 수) 표시
- [x] 접속 통계 차트 (7/30/90일 선택) — UI 완료, 백엔드 미구현
- [x] 클라우드 서버 상태 (대시보드에 통합)
- [x] AI 분석 모니터링 (분석 수, 토큰/비용, 최근 결과 샘플) — UI 완료, 백엔드 미구현
- [x] 전략 템플릿 CRUD 정상 동작
- [x] 서비스 키 등록/삭제 정상 동작
- [x] 에러 로그 조회/필터링 — UI 완료, 백엔드 미구현
- [x] 어드민 전용 로그인 페이지 (Step 10)

---

## 7. 구현 노트

### 주요 변경점 (계획 대비)

1. **DataStatus.tsx 삭제** — 대시보드에 클라우드 서버 상태 통합. 별도 페이지 중복
2. **AdminDashboard.tsx 삭제** — 레거시 단일 페이지, Admin/ 디렉토리 구조로 대체
3. **TemplateForm.tsx 미생성** — Templates.tsx 내 인라인 폼으로 충분
4. **API 경로 변경** — `data/status` → `collector-status` (cloud_server 실제 엔드포인트)
5. **템플릿 스키마 변경** — `difficulty`/`usage_count`/`is_active` 제거, `is_public`/`description`/`created_by` 사용
6. **서비스 키 스키마 변경** — `source`/`key`/`description` → `api_key`/`api_secret`/`app_name`
7. **Users 응답 구조** — `{ success, users: [...], total, page, limit }` (data 래핑 아님)

### Step 10 — 어드민 전용 로그인 페이지

**목표**: `/admin/login` 별도 로그인 페이지 (흰색 테마, 미니멀)

**파일**:
- `frontend/src/pages/Admin/Login.tsx` — 어드민 로그인 (신규)
- `frontend/src/App.tsx` — `/admin/login` 공개 라우트 추가

**구현 내용**:
```
1. 흰색 배경 + 심플 폼 (이메일, 비밀번호)
2. 동일 auth API (useAuth → cloudAuth.login)
3. 로그인 성공 후 JWT role 확인
   - role=admin → /admin 리다이렉트
   - role!=admin → "관리자 권한이 없습니다" 에러 + 로그아웃
4. 회원가입/비밀번호 찾기 링크 없음 (어드민 전용)
5. AdminGuard 미인증 시 /admin/login으로 리다이렉트 (기존 /login → /admin/login)
```

### 잔여 작업

- 백엔드 미구현 API 4개 (stats/connections, ai/stats, ai/recent, errors)

---

**마지막 갱신**: 2026-03-10
