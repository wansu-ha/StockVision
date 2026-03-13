# Step 4: 프론트엔드 로컬 서버 세션 복원 + 401 로컬 우선 refresh

## 변경 파일

| 파일 | 변경 |
|------|------|
| `frontend/src/services/localClient.ts` | `localAuth.restore()` 추가 (POST /auth/restore + localSecret 저장) |
| `frontend/src/context/AuthContext.tsx` | else 분기에 `localAuth.restore()` 추가, cloudAuth.refresh catch에 localReady: true 설정 |
| `frontend/src/services/cloudClient.ts` | `localAuth` import 추가, 401 인터셉터를 로컬 서버 우선 → 클라우드 폴백으로 변경, 폴백 성공 시 로컬에도 전달 |

## 검증 결과

- 순환 import 없음 (localClient → cloudClient 참조 없음)
- 프론트엔드 빌드 성공 (18.64s)
- lint: 기존 에러 6건만 (내 변경으로 인한 신규 에러 0건)
