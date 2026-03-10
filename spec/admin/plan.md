# 어드민 페이지 구현 계획서 (admin)

> 작성일: 2026-03-05 | 상태: 초안 | Unit 6 (Phase 3-C)

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

**API 필요** (Unit 4):
- `GET /api/v1/admin/stats/connections` → 활성 유저 수
- `GET /api/v1/admin/data/status` → 클라우드 서버 상태 (업타임, CPU/MEM 포함)
- `GET /api/v1/admin/ai/stats` → AI 분석 통계
- `GET /api/v1/admin/errors?limit=5` → 최근 에러

**검증**:
- [ ] 통계 카드 4개 모두 표시
- [ ] 클라우드 상태 + AI 분석 요약 실시간 갱신 (10초 폴링)
- [ ] 에러 로그 최근 5건 표시

---

### Step 3 — 유저 관리 페이지

**목표**: 유저 목록 조회, 상태 변경 (비활성화)

**파일**:
- `frontend/src/pages/Admin/Users.tsx` — 유저 목록 페이지
- `cloud_server/api/admin.py` — PATCH /api/v1/admin/users/:id 추가

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
- `frontend/src/pages/Admin/Templates.tsx` — 템플릿 관리 페이지
- `frontend/src/components/TemplateForm.tsx` — 템플릿 폼 컴포넌트 (신규)

**구현 내용**:
```
1. 템플릿 목록
   - 이름, 카테고리, 사용 수, 액션
   - [수정], [삭제] 버튼

2. 템플릿 생성/수정 모달
   - 이름, 설명, 카테고리
   - buy/sell_conditions JSON 에디터 (또는 폼)
   - default_params (수량, 예산 비율 등)
   - [저장], [취소] 버튼
```

**API 필요** (Unit 4):
- `GET/POST/PUT/DELETE /api/v1/admin/templates`

**검증**:
- [ ] 템플릿 목록 조회
- [ ] 새 템플릿 생성 → DB 저장
- [ ] 기존 템플릿 수정 → DB 업데이트
- [ ] 템플릿 삭제

---

### Step 7 — 시세 데이터 모니터링

**목표**: 클라우드 서버 시세 수집 상태 모니터링

**파일**:
- `frontend/src/pages/Admin/DataStatus.tsx` — 시세 모니터링 페이지

**구현 내용**:
```
1. 클라우드 서버 상태
   - 연결 상태 (🟢 정상 / 🟡 경고 / 🔴 오류)
   - 업타임, CPU/메모리
   - 마지막 시세 수신 시간
   - 구독 종목 수, 일봉 수집량 (건/일)
   - 연결된 클라이언트 수

2. 최근 데이터 수집 로그
   - 타임스탬프, 종목, 건수, 상태
```

**API 필요** (Unit 4):
- `GET /api/v1/admin/data/status` → 클라우드 상태

**검증**:
- [ ] 클라우드 서버 상태 표시 (업타임, CPU/MEM 포함)
- [ ] 수집 로그 10초 자동 갱신

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
| `frontend/src/pages/Admin.tsx` | 어드민 레이아웃 (사이드바, 라우트 정의) |
| `frontend/src/pages/Admin/Dashboard.tsx` | 어드민 대시보드 |
| `frontend/src/pages/Admin/Users.tsx` | 유저 관리 |
| `frontend/src/pages/Admin/Stats.tsx` | 접속 통계 차트 |
| `frontend/src/pages/Admin/ServiceKeys.tsx` | 서비스 키 관리 |
| `frontend/src/pages/Admin/Templates.tsx` | 템플릿 관리 |
| `frontend/src/pages/Admin/DataStatus.tsx` | 시세 모니터링 |
| `frontend/src/pages/Admin/AiMonitor.tsx` | AI 분석 모니터링 |
| `frontend/src/pages/Admin/ErrorLogs.tsx` | 에러 로그 뷰어 |
| `frontend/src/components/AdminGuard.tsx` | 권한 검사 컴포넌트 |
| `frontend/src/components/TemplateForm.tsx` | 템플릿 폼 컴포넌트 |

### 수정 파일

| 파일 | 변경 사항 |
|------|---------|
| `frontend/src/App.tsx` | 어드민 라우트 등록 |
| `frontend/src/services/admin.ts` | API 클라이언트 메서드 추가 |

---

## 3. 의존성

### Unit 4 (클라우드 서버 어드민 API)

Step 2-9 모든 단계가 Unit 4의 어드민 API에 의존:

```
⚠️ Unit 4 구현 완료 대기:
- GET /api/v1/admin/stats/connections
- GET /api/v1/admin/data/status
- GET /api/v1/admin/ai/stats
- GET /api/v1/admin/ai/recent
- GET /api/v1/admin/errors
- GET/POST/DELETE /api/v1/admin/service-keys
```

**Step 1 (라우팅) 은 Unit 4 대기 불필요 → 먼저 구현 가능**

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

## 5. 커밋 계획

| 단계 | 커밋 메시지 | 파일 |
|------|------------|------|
| Step 1 | `feat: 어드민 라우팅 + 권한 가드` | App.tsx, Admin.tsx, AdminGuard.tsx |
| Step 2 | `feat: 어드민 대시보드 (통계 + 서버 상태 + AI 요약)` | Admin/Dashboard.tsx, admin.ts |
| Step 3 | `feat: 유저 관리 페이지` | Admin/Users.tsx |
| Step 4 | `feat: 접속 통계 차트 (7/30/90일)` | Admin/Stats.tsx |
| Step 5 | `feat: 서비스 키 관리` | Admin/ServiceKeys.tsx |
| Step 6 | `feat: 템플릿 CRUD UI` | Admin/Templates.tsx, TemplateForm.tsx |
| Step 7 | `feat: 시세 데이터 모니터링` | Admin/DataStatus.tsx |
| Step 8 | `feat: AI 분석 모니터링 (토큰/비용)` | Admin/AiMonitor.tsx |
| Step 9 | `feat: 에러 로그 뷰어` | Admin/ErrorLogs.tsx |

---

## 6. 검증 체크리스트

### 최종 수용 기준 (spec.md §7)

- [ ] admin 계정으로 `/admin` 접근 → 대시보드 표시
- [ ] 일반 유저로 `/admin` 접근 → 403 또는 리다이렉트
- [ ] 유저 목록 조회 (이메일, 닉네임, 역할, 인증 여부, 활성 상태, 가입일, 마지막 로그인)
- [ ] 시스템 통계 (유저 수, 활성 유저 수, 규칙 수, 활성 클라이언트 수) 표시
- [ ] 접속 통계 차트 (7/30/90일 선택)
- [ ] 클라우드 서버 상태 (업타임, CPU/메모리, 시세 수집, 클라이언트 수)
- [ ] AI 분석 모니터링 (분석 수, 토큰/비용, 최근 결과 샘플)
- [ ] 전략 템플릿 CRUD 정상 동작
- [ ] 서비스 키 등록/삭제 정상 동작
- [ ] 에러 로그 조회/필터링

---

## 7. 개발 프로세스

### 병렬 개발 가능성

- **Step 1 (라우팅)**: 즉시 시작 가능 (Unit 4 대기 없음)
- **Step 2-9**: Unit 4 API 스펙 확정 후, Mock 데이터로 병렬 개발 가능

### 주의사항

- 각 Step 완료 시 `spec/admin/reports/stepN.md`에 기록
- 커밋은 전체 완료 후 일괄 (workflow 규칙)

---

**마지막 갱신**: 2026-03-10
