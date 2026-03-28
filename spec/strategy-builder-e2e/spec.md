> 작성일: 2026-03-28 | 상태: 확정

# StrategyBuilder E2E 테스트

## 배경

StrategyBuilder는 프로젝트 핵심 기능 (전략 생성/편집/삭제). 현재 Playwright E2E가
로그인/가드/온보딩/백테스트만 커버하며 **전략 CRUD 테스트 0개**.

## 테스트 시나리오

### S1: 전략 생성 (Happy path)
1. /strategy 접근 (AUTH_BYPASS 사용)
2. 폼 영역 표시 확인 (StrategyBuilder는 단일 페이지, 상태 변경으로 폼 토글)
3. 이름, 종목코드 입력
4. 매수 조건 설정 (RSI < 30)
5. 저장 → 성공 토스트
6. /strategies 목록에 표시

### S2: 전략 편집
1. /strategies에서 전략 카드 클릭 → /strategy?id=N
2. 폼에 기존 값 표시 확인
3. 이름 수정
4. 저장 → 성공 토스트

### S3: 전략 삭제
1. 전략 카드 삭제 버튼
2. 확인 → 목록에서 사라짐

### S4: 유효성 검증
1. 이름 빈 채로 저장 → 에러
2. 종목코드 빈 채로 저장 → 에러

### S5: 백테스트 버튼
1. 전략 편집 화면에서 "백테스트" 버튼 클릭
2. 결과 표시 확인 (인라인)

## 기술적 접근

- **API mock**: Playwright `page.route()`로 cloud_server API 응답을 가로채서 mock
- 서버 불필요 — 프론트엔드만으로 테스트
- **인증**: spec 파일 내에서 page.route()로 /api/v1/auth/me mock (전역 AUTH_BYPASS 사용 안 함 — 기존 auth E2E 보호)

## 수용 기준

- [ ] S1: 전략 생성 흐름 통과
- [ ] S2: 전략 편집 흐름 통과
- [ ] S3: 전략 삭제 흐름 통과
- [ ] S4: 유효성 에러 표시
- [ ] S5: 백테스트 인라인 결과 표시
- [ ] 기존 E2E 11개 (5파일) 깨지지 않음

## 변경 대상

| 파일 | 변경 |
|------|------|
| frontend/e2e/strategy-builder.spec.ts | 신규 |
| frontend/e2e/helpers/mock-auth.ts | API mock 헬퍼 (인증 우회) |
| frontend/src/pages/StrategyBuilder.tsx | data-testid 추가 (필요 시) |
| frontend/src/components/RuleList.tsx | data-testid 추가 (필요 시) |
