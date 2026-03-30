# E2E 프리셋 셀렉터 수정 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** `strategy-v2.spec.ts`의 5개 실패 테스트를 수정하여 8개 전부 PASS 달성.

**Architecture:** 테스트 파일 1개만 수정. 원인 A(셀렉터)는 `{ exact: true }`, 원인 B(타이밍)는 `toHaveValue` 자동 대기로 해결.

**Spec:** `spec/fix-e2e-preset-selector/spec.md`

---

## 파일 구조

| 구분 | 파일 | 역할 |
|------|------|------|
| 수정 | `frontend/e2e/strategy-v2.spec.ts` | 셀렉터 + 타이밍 수정 |

---

### Task 1: V1, V2, V4, V6 — 셀렉터 exact 매칭

**Files:**
- Modify: `frontend/e2e/strategy-v2.spec.ts`

V1, V2, V4, V6에서 `getByText('추세 추종')`을 `getByText('추세 추종', { exact: true })`로 교체.

- [ ] **Step 1: V1 (line 27) 수정**

```typescript
// 현재
await expect(page.getByText('추세 추종')).toBeVisible()

// 변경
await expect(page.getByText('추세 추종', { exact: true })).toBeVisible()
```

- [ ] **Step 2: V2 (line 43, 46, 49) 수정**

```typescript
// line 43 — 프리셋 표시 확인
await expect(page.getByText('추세 추종', { exact: true })).toBeVisible()

// line 46 — 클릭
await page.getByText('추세 추종', { exact: true }).click()

// line 49 — 패널 닫힘 확인
await expect(page.getByText('추세 추종', { exact: true })).not.toBeVisible({ timeout: 3_000 })
```

- [ ] **Step 3: V4 (line 86, 90) 수정**

```typescript
// line 86 — 열기 확인
await expect(page.getByText('추세 추종', { exact: true })).toBeVisible()

// line 90 — 닫기 확인
await expect(page.getByText('추세 추종', { exact: true })).not.toBeVisible({ timeout: 3_000 })
```

- [ ] **Step 4: V6 (line 126) 수정**

```typescript
// 현재
await page.getByText('추세 추종').click()

// 변경
await page.getByText('추세 추종', { exact: true }).click()
```

---

### Task 2: V3 — React 렌더 타이밍 대기

**Files:**
- Modify: `frontend/e2e/strategy-v2.spec.ts`

V3에서 DCA 프리셋 클릭 후 textarea 값을 바로 읽지 않고, `toHaveValue`로 자동 대기.

- [ ] **Step 1: V3 (line 70~77) 수정**

```typescript
// 현재
await page.getByText('DCA (분할 매수)').click()

const dslTextarea = page.locator('textarea').first()
await expect(dslTextarea).toBeVisible()
const value = await dslTextarea.inputValue()
// DCA 프리셋 핵심 요소: 분할 진입 비율 두 개
expect(value).toContain('50%')
expect(value).toContain('30%')
```

```typescript
// 변경 — toHaveValue로 React 렌더 완료 대기
await page.getByText('DCA (분할 매수)').click()

const dslTextarea = page.locator('textarea').first()
// React 배치 렌더 완료 대기: textarea에 값이 들어올 때까지 자동 대기
await expect(dslTextarea).toHaveValue(/50%/, { timeout: 5_000 })
// 첫 번째 대기 통과 시 두 번째는 이미 렌더 완료
const value = await dslTextarea.inputValue()
expect(value).toContain('30%')
```

---

### Task 3: 검증

- [ ] **Step 1: 테스트 실행**

```bash
cd frontend && npx playwright test e2e/strategy-v2.spec.ts -v
```

Expected: 8 passed, 0 failed

- [ ] **Step 2: 커밋**

```bash
git add frontend/e2e/strategy-v2.spec.ts
git commit -m "fix(e2e): 프리셋 셀렉터 exact 매칭 + DCA 렌더 타이밍 대기"
```
