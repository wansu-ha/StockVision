# 프론트엔드 테스트 확장 — Frontend Test Expansion

> 작성일: 2026-03-26 | 상태: 구현 완료

---

## 목표

핵심 유틸리티 유닛 테스트 + 비즈니스 로직 E2E 테스트를 추가하여
프론트엔드 회귀 감지 능력을 스모크 수준에서 비즈니스 검증 수준으로 올린다.

---

## 범위

### 포함

1. **Vitest 설치 + 설정** — 유닛 테스트 인프라
2. **dslParser 유닛 테스트** — 파서 회귀 방지 (최우선)
3. **dslConverter 유닛 테스트** — DSL ↔ 조건 배열 변환
4. **e2eCrypto 유닛 테스트** — 원격 모드 복호화
5. **StrategyBuilder E2E** — 전략 CRUD 흐름
6. **MainDashboard E2E** — 메인 화면 데이터 로딩

### 미포함

- 컴포넌트 단위 테스트 (DslEditor, OpsPanel 등) — ROI 낮음, 나중에
- 비주얼 리그레션 테스트

---

## FT-1: Vitest 설치 + 설정

**수용 기준**:
- [ ] `vitest`, `happy-dom` devDependency 추가
- [ ] `vite.config.ts`에 test 설정 추가
- [ ] `package.json`에 `test`, `test:coverage` 스크립트
- [ ] `src/utils/__tests__/` 디렉토리 구조

**파일**:
- `frontend/package.json` (수정)
- `frontend/vite.config.ts` (수정)

---

## FT-2: dslParser 유닛 테스트

**설명**: DSL 파서의 토크나이저 + 파서 로직을 테스트. 파서 버그는 StrategyBuilder 전체를 망가뜨리므로 최우선.

**수용 기준**:
- [ ] 토크나이저 테스트 (숫자, 키워드, 연산자, 한글 식별자)
- [ ] 유효한 매수/매도 파싱
- [ ] AND/OR 혼합 조건
- [ ] 에러 케이스 (콜론 누락, 피연산자 누락, 빈 입력)
- [ ] 음수, 소수점 숫자
- [ ] 라운드트립: DSL → parse → serialize → DSL 동일

**예상 테스트 수**: 25~35개

**파일**:
- `frontend/src/utils/__tests__/dslParser.test.ts` (신규)

---

## FT-3: dslConverter 유닛 테스트

**수용 기준**:
- [ ] DSL → Condition[] 변환
- [ ] Condition[] → DSL 문자열 변환
- [ ] 빈 조건, null 처리
- [ ] 라운드트립 검증

**예상 테스트 수**: 8~12개

**파일**:
- `frontend/src/utils/__tests__/dslConverter.test.ts` (신규)

---

## FT-4: e2eCrypto 유닛 테스트

**수용 기준**:
- [ ] IndexedDB mock (fake-indexeddb 또는 수동 mock)
- [ ] 키 저장/로드/삭제 라이프사이클
- [ ] AES-256-GCM 복호화 (올바른 키 / 잘못된 키)
- [ ] 손상된 데이터 처리

**예상 테스트 수**: 15~20개

**파일**:
- `frontend/src/utils/__tests__/e2eCrypto.test.ts` (신규)

---

## FT-5: StrategyBuilder E2E

**전제**: cloud_server 실행 중 또는 MSW(Mock Service Worker)로 API mock

**수용 기준**:
- [ ] 전략 생성 → 이름 입력 → DSL 조건 입력 → 저장
- [ ] 전략 목록에서 방금 생성한 전략 확인
- [ ] 전략 수정 → 조건 변경 → 저장
- [ ] 스크립트 모드 ↔ 폼 모드 전환
- [ ] data-testid 추가: StrategyBuilder 폼 필드

**파일**:
- `frontend/e2e/strategy-crud.spec.ts` (신규)
- `frontend/src/pages/StrategyBuilder.tsx` (수정) — data-testid

---

## FT-6: MainDashboard E2E

**수용 기준**:
- [ ] 로그인 → 대시보드 렌더링 (실제 로그인 흐름)
- [ ] 종목 리스트 로딩 확인
- [ ] 종목 클릭 → 상세 패널 전환
- [ ] 관심종목 토글

**파일**:
- `frontend/e2e/dashboard.spec.ts` (신규)

---

## 커버리지 목표

| 영역 | 현재 | 목표 |
|------|------|------|
| 유틸리티 (dslParser, dslConverter, e2eCrypto) | 0% | 90%+ |
| E2E 시나리오 | 9개 (스모크) | 20개+ (비즈니스 로직) |
| 전체 페이지 커버 | 4/25 | 8/25 |
