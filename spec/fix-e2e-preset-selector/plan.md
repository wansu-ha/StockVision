# E2E 프리셋 셀렉터 수정 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** `strategy-v2.spec.ts`의 5개 실패 테스트를 수정하여 8개 전부 PASS 달성.

**Architecture:** 테스트 파일 1개만 수정. 원인 A(셀렉터)는 `page.locator('button', { hasText: /^추세 추종$/ })`로 정확 매칭, 원인 B(타이밍)는 패널 닫힘 대기 배리어로 해결.

**Spec:** `spec/fix-e2e-preset-selector/spec.md`

---

## 설계 결정

### 왜 `{ exact: true }` 대신 `locator('button', { hasText })`인가

`getByText('추세 추종', { exact: true })`는 텍스트가 정확히 일치하는 **모든 요소**를 매칭한다. 프리셋 버튼 구조가 `<button>` > `<span>추세 추종</span>` 이면, `<span>`과 부모 `<button>` 양쪽이 매칭되어 strict mode 에러가 재발할 수 있다.

`page.locator('button', { hasText: /^추세 추종$/ })`는 `<button>` 요소만 대상으로 하고, 내부 텍스트에 정규식을 적용한다. 단, `<button>` 안에 카테고리/설명 span이 있으면 전체 innerText가 합쳐져서 `^추세 추종$`가 매칭 안 될 수 있다.

**가장 안전한 접근: 먼저 `{ exact: true }`로 시도하고, strict mode 에러가 나면 locator로 전환.**

실제 DOM 구조를 테스트 실행으로 확인하는 게 가장 빠르다.

### V3 타이밍: 왜 `toHaveValue` 대신 `.not.toBeVisible()` 배리어인가

프리셋 클릭 시 3개 setState (`setDslText`, `setCondMode`, `setShowPresets`)가 React 18에서 단일 배치 렌더된다. `setShowPresets(false)`로 패널이 사라지는 시점이 곧 `dslText`가 커밋된 시점이다. `.not.toBeVisible()`은 이 렌더 완료를 의미적으로 정확하게 대기한다. V2가 이미 이 패턴을 사용하고 있다.

---

## 파일 구조

| 구분 | 파일 | 역할 |
|------|------|------|
| 수정 | `frontend/e2e/strategy-v2.spec.ts` | 셀렉터 + 타이밍 수정 |

---

### Task 1: 모든 수정 적용

**Files:**
- Modify: `frontend/e2e/strategy-v2.spec.ts`

#### V1 (line 27)

```typescript
// 현재
await expect(page.getByText('추세 추종')).toBeVisible()

// 변경
await expect(page.getByText('추세 추종', { exact: true })).toBeVisible()
```

#### V2 (line 43, 46, 49)

```typescript
// line 43
await expect(page.getByText('추세 추종', { exact: true })).toBeVisible()

// line 46
await page.getByText('추세 추종', { exact: true }).click()

// line 49 — React 배치 렌더 완료 대기 배리어 (기존과 동일 역할)
await expect(page.getByText('추세 추종', { exact: true })).not.toBeVisible({ timeout: 3_000 })
```

#### V3 (line 70~77) — 타이밍 수정

```typescript
// 현재
await page.getByText('DCA (분할 매수)').click()

const dslTextarea = page.locator('textarea').first()
await expect(dslTextarea).toBeVisible()
const value = await dslTextarea.inputValue()
expect(value).toContain('50%')
expect(value).toContain('30%')

// 변경 — 패널 닫힘 배리어 추가 (V2와 동일 패턴)
await page.getByText('DCA (분할 매수)').click()

// React 배치 렌더 완료 대기: 패널이 닫히면 dslText도 커밋됨
await expect(page.getByText('DCA (분할 매수)')).not.toBeVisible({ timeout: 3_000 })

const dslTextarea = page.locator('textarea').first()
await expect(dslTextarea).toBeVisible()
const value = await dslTextarea.inputValue()
expect(value).toContain('50%')
expect(value).toContain('30%')
```

#### V4 (line 86, 90)

```typescript
// line 86
await expect(page.getByText('추세 추종', { exact: true })).toBeVisible()

// line 90
await expect(page.getByText('추세 추종', { exact: true })).not.toBeVisible({ timeout: 3_000 })
```

#### V6 (line 125~126) — 셀렉터 + 배리어 추가

```typescript
// 현재
await page.getByText('추세 추종').click()

// 변경
await page.getByText('추세 추종', { exact: true }).click()
// React 배치 렌더 완료 대기
await expect(page.getByText('추세 추종', { exact: true })).not.toBeVisible({ timeout: 3_000 })
```

---

### Task 2: 검증 + strict mode 대응

- [ ] **Step 1: 테스트 실행**

```bash
cd frontend && npx playwright test e2e/strategy-v2.spec.ts -v
```

Expected: 8 passed, 0 failed

- [ ] **Step 2: strict mode 에러 확인**

만약 `{ exact: true }`에서 여전히 strict mode 에러가 발생하면, 해당 셀렉터를 다음으로 교체:

```typescript
// 폴백: locator로 button 요소만 매칭
const presetBtn = page.locator('[class*="preset"]').filter({ hasText: '추세 추종' }).first()
// 또는
const presetBtn = page.getByRole('button', { name: /추세 추종/ }).first()
```

`.first()`를 쓰면 strict mode를 우회하지만, 정확한 요소를 가리키는지 스크린샷으로 확인.

- [ ] **Step 3: 커밋**

```bash
git add frontend/e2e/strategy-v2.spec.ts
git commit -m "fix(e2e): 프리셋 셀렉터 exact 매칭 + 렌더 타이밍 배리어 추가"
```
