# UX Polish — 프론트엔드 UX 개선

> 작성일: 2026-03-13 | 상태: 초안

---

## 목표

완전히 안 되거나 사용자 경험을 해치는 프론트엔드 이슈를 수정하여 **기본 UX 품질**을 확보한다.

근거 자료: `docs/research/review-frontend.md`

---

## 범위

### 포함 (4건)

데이터 손실 방지, 테마 통일, WS 재연결, 프로토타입 라우트 정리.

### 미포함

- 프론트엔드 인증 이슈 → `spec/auth-security/` (AS-5, AS-6)
- OAuth 콜백 → `spec/stability/` (ST-8)
- 미완성 기능 (ProtoA/B/C 내용, StrategyBuilder DSL 역파싱) → 별도 spec

---

## UX-1: StrategyBuilder 편집 모드 보호 (FE-I5)

**현상**: `StrategyBuilder.tsx:114-122` `startEdit()`에서 `buyConditions: EMPTY_FORM.buyConditions`로 하드코딩. 기존 전략 편집 시 조건이 기본값으로 리셋되어 데이터 손실. TODO 주석 있음: "script → 폼 역파싱 (복잡한 DSL은 읽기 전용)".
**수정**: 편집 버튼 클릭 시 조건 섹션을 읽기 전용으로 표시 + "DSL 역파싱 미지원" 안내. 또는 script 필드를 직접 편집할 수 있는 textarea 제공.
**파일**: `frontend/src/pages/StrategyBuilder.tsx`
**검증**: 기존 전략 편집 시 조건 데이터 유지 (손실 불가)

## UX-2: Layout.tsx 다크 테마 통일 (FE-I8)

**현상**: `Layout.tsx:29-31` `bg-gray-50`, `bg-white shadow-lg`로 라이트 테마 고정. `MainDashboard`, `Settings` 등은 `bg-gray-950` 다크 테마 사용. 페이지 이동 시 시각적 불일치.
**수정**: Layout 배경/네비게이션을 다크 테마로 통일.
**파일**: `frontend/src/components/Layout.tsx`
**검증**: 모든 페이지 이동 시 테마 일관성

## UX-3: WS 재연결 개선 (FE-I1)

**현상**: `useLocalBridgeWS.ts:79-83` `retries.current < 3` 조건으로 연속 3회 실패 후 영구 중단. 재연결 불가.
**수정**: 지수 백오프 (1s → 2s → 4s → 8s → 16s → 30s max) + 무한 재시도. UI에 연결 상태 표시.
**파일**: `frontend/src/hooks/useLocalBridgeWS.ts`
**검증**: 브릿지 5분 중단 → 재시작 후 자동 재연결

## UX-4: proto 라우트 프로덕션 보호 (FE-I9)

**현상**: `App.tsx:61-63` `/proto-a`, `/proto-b`, `/proto-c`가 `ProtectedRoute` 없이 공개 라우트. 개발용 프로토타입이 프로덕션에 노출.
**수정**: `import.meta.env.DEV` 가드로 개발 환경에서만 라우트 등록, 또는 `ProtectedRoute` 래핑.
**파일**: `frontend/src/App.tsx`
**검증**: 프로덕션 빌드에서 `/proto-*` 접근 불가 (404)

---

## 수용 기준

- [ ] 전략 편집 시 데이터 손실 방지
- [ ] 다크 테마 통일 (Layout ↔ 페이지 일관)
- [ ] WS 지수 백오프 무한 재연결
- [ ] proto 라우트 프로덕션 접근 불가

---

## 참고 파일

- `frontend/src/pages/StrategyBuilder.tsx` — 편집 모드 (UX-1)
- `frontend/src/components/Layout.tsx` — 테마 (UX-2)
- `frontend/src/hooks/useLocalBridgeWS.ts` — WS 재연결 (UX-3)
- `frontend/src/App.tsx` — proto 라우트 (UX-4)
- `docs/research/review-frontend.md` — 근거 자료
