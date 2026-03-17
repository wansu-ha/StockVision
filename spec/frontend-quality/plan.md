# 프론트엔드 품질 — 구현 계획

> 작성일: 2026-03-16 | 상태: 부분 구현 | F1 ✅ F2 ⚠️40% F3 ❌ | spec: `spec/frontend-quality/spec.md`

## 의존관계

```
F1 (ErrorBoundary)   ─── 독립
F2 (staleTime)       ─── 독립
F3 (프로필 수정)      ─── ⚠️ legal spec 완료 후 (auth.py, Settings.tsx 공유)

→ F1, F2 병렬 가능. F3은 legal spec의 L2(약관 동의 UI) 완료 후 진행.
  사유: legal이 auth.py에 동의 필드 추가 + Settings.tsx에 동의 관리 UI 추가하므로,
  F3이 먼저 들어가면 충돌 발생.
```

## Step 1: ErrorBoundary (F1)

**파일**: `frontend/src/components/ErrorBoundary.tsx` (신규), `frontend/src/App.tsx` (수정)

### 1.1 ErrorBoundary 컴포넌트

```tsx
import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props { children: ReactNode }
interface State { hasError: boolean; error: Error | null }

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('ErrorBoundary caught:', error, info.componentStack)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-gray-950 flex items-center justify-center">
          <div className="text-center space-y-4">
            <h1 className="text-xl font-bold text-gray-100">오류가 발생했습니다</h1>
            {import.meta.env.DEV && (
              <pre className="text-xs text-red-400 max-w-md overflow-auto">
                {this.state.error?.message}
              </pre>
            )}
            <button
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg"
            >
              새로고침
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
```

### 1.2 App.tsx 래핑

```tsx
// App.tsx
import ErrorBoundary from './components/ErrorBoundary'

// QueryClientProvider 바로 안쪽에 래핑
<QueryClientProvider client={queryClient}>
  <ErrorBoundary>
    <AppRoutes />
  </ErrorBoundary>
</QueryClientProvider>
```

**검증**:
- [ ] 컴포넌트 throw 시 폴백 UI 표시
- [ ] 개발 모드에서 에러 메시지 표시
- [ ] "새로고침" 버튼 동작
- [ ] 라우트 전환으로 복구 가능

## Step 2: staleTime 설정 (F2)

**파일**: 다수 (아래 표 참조)

### 2.1 가이드라인

| 데이터 | staleTime | 파일 |
|--------|-----------|------|
| 시세/잔고 (refetchInterval 있음) | 설정 안 함 | `MainDashboard.tsx`, `useStockData.ts` |
| 규칙 목록 | `2 * 60_000` (2분) | `StrategyList.tsx`, `StrategyBuilder.tsx` |
| 종목명/마스터 | `5 * 60_000` (5분) | `useStockData.ts` (이미 설정) |
| 관심종목 | `2 * 60_000` (2분) | `useStockData.ts` |
| AI 브리핑 | `30 * 60_000` (30분) | `BriefingCard.tsx` (이미 설정) |
| 실행 로그 | `30_000` (30초) | `ExecutionLog.tsx` |
| Admin 통계 | `30_000` (30초) | `Admin/*.tsx` |
| 마켓 컨텍스트 | `30_000` (30초) | `useMarketContext.ts` |

### 2.2 수정 패턴

```tsx
// 예: StrategyList.tsx
const { data } = useQuery({
  queryKey: ['rules'],
  queryFn: fetchRules,
  staleTime: 2 * 60_000,  // ← 추가
  refetchInterval: 10_000,
})
```

**검증**:
- [ ] 규칙 목록: 2분 이내 재마운트 시 네트워크 요청 없음
- [ ] 시세 쿼리: 기존 refetchInterval 동작 유지
- [ ] 종목명: 5분 캐시 동작

## Step 3: 프로필 수정 (F3)

**파일**: `cloud_server/api/auth.py` (수정), `frontend/src/services/cloudClient.ts` (수정), `frontend/src/pages/Settings.tsx` (수정)

### 3.1 백엔드 엔드포인트

```python
# cloud_server/api/auth.py
class UpdateProfileBody(BaseModel):
    nickname: str = Field(..., min_length=2, max_length=20)

    @field_validator("nickname")
    @classmethod
    def strip_nickname(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("닉네임은 2자 이상이어야 합니다.")
        return v

@router.patch("/profile", summary="프로필 수정")
async def update_profile(
    body: UpdateProfileBody,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.nickname = body.nickname
    db.commit()
    return {"success": True, "data": {"nickname": current_user.nickname}}
```

### 3.2 프론트엔드 API

```typescript
// cloudClient.ts — 기존 스텁 교체
updateProfile: async (nickname: string) => {
  const { data } = await cloudApi.patch('/auth/profile', { nickname })
  return data
},
```

### 3.3 Settings UI

```tsx
// Settings.tsx 계정 섹션에 닉네임 인라인 편집 추가
const [editingNickname, setEditingNickname] = useState(false)
const [nickname, setNickname] = useState(user?.nickname || '')

// 표시 모드: 닉네임 + 편집 아이콘
// 편집 모드: input + 저장/취소 버튼
```

**검증**:
- [ ] PATCH `/api/v1/auth/profile` → 닉네임 변경 성공
- [ ] 2자 미만 → 422 에러
- [ ] Settings에서 닉네임 편집 + 저장 동작
- [ ] 저장 성공 시 토스트 알림

## 변경 파일 요약

| 파일 | Step | 변경 |
|------|------|------|
| `frontend/src/components/ErrorBoundary.tsx` | F1 | **신규** |
| `frontend/src/App.tsx` | F1 | ErrorBoundary 래핑 |
| `frontend/src/pages/StrategyList.tsx` | F2 | staleTime 추가 |
| `frontend/src/pages/StrategyBuilder.tsx` | F2 | staleTime 추가 |
| `frontend/src/hooks/useStockData.ts` | F2 | staleTime 조정 |
| `frontend/src/hooks/useMarketContext.ts` | F2 | staleTime 추가 |
| `frontend/src/pages/Admin/*.tsx` | F2 | staleTime 추가 |
| `cloud_server/api/auth.py` | F3 | PATCH /profile |
| `frontend/src/services/cloudClient.ts` | F3 | updateProfile 구현 |
| `frontend/src/pages/Settings.tsx` | F3 | 닉네임 편집 UI |
