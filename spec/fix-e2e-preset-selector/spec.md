# E2E 프리셋 셀렉터 수정 명세서

> 작성일: 2026-03-31 | 상태: 구현 완료

---

## 1. 문제

`frontend/e2e/strategy-v2.spec.ts`에서 5개 테스트가 실패한다. 원인은 2가지.

### 원인 A: 셀렉터 부정확 (V1, V2, V4, V6)

`page.getByText('추세 추종')`이 두 요소에 매칭된다:
1. 프리셋 "추세 추종" (id: `trend-following`)
2. 프리셋 "EMA 크로스 **추세 추종**" (id: `ema-cross`)

Playwright strict mode에서 2개 이상 매칭은 에러.

### 원인 B: React 렌더 타이밍 (V3)

V3(DCA)은 셀렉터 문제가 아니다. "DCA (분할 매수)"는 유니크한 이름이라 클릭 자체는 성공한다. 문제는 클릭 후 textarea 값을 너무 빨리 읽는 것.

프리셋 클릭 시 `StrategyBuilder.tsx`에서 3개 setState가 배치된다:
```
setDslText(preset.script)   // 1. 스크립트 텍스트
setCondMode('script')       // 2. DSL 모드로 전환
setShowPresets(false)       // 3. 패널 닫기
```

React가 이 3개를 배치 렌더하므로, DOM 업데이트 전에 `inputValue()`를 읽으면 빈 문자열이 나온다.

V2는 `await expect(page.getByText('추세 추종')).not.toBeVisible()`이 동기화 배리어 역할을 해서 우연히 통과하지만, V3에는 그런 대기가 없다.

## 2. 수정 방향

**테스트만 수정. UI 컴포넌트, 프리셋 이름 변경 없음.**

| 원인 | 수정 |
|------|------|
| A: 셀렉터 부정확 | `getByText('추세 추종', { exact: true })` 사용 |
| B: 렌더 타이밍 | `toHaveValue(/50%/)` 자동 대기 사용 또는 패널 닫힘 대기 후 읽기 |

## 3. 영향 테스트 목록

| 테스트 | 원인 | 수정 |
|--------|------|------|
| V1 (line 27) | A: 셀렉터 | `{ exact: true }` 추가 |
| V2 (line 43, 46, 49) | A: 셀렉터 | `{ exact: true }` 추가 |
| V3 (line 70~77) | B: 타이밍 | `toHaveValue` 자동 대기 또는 패널 닫힘 대기 추가 |
| V4 (line 86, 90) | A: 셀렉터 | `{ exact: true }` 추가 |
| V6 (line 126) | A: 셀렉터 | `{ exact: true }` 추가 |

## 4. 수용 기준

- [ ] `npx playwright test e2e/strategy-v2.spec.ts` 8개 전부 PASS
- [ ] 프리셋 이름 변경 없음
- [ ] UI 컴포넌트 변경 없음 (테스트만 수정)
