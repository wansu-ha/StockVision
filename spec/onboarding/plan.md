# 온보딩 플로우 구현 계획서 (onboarding)

> 작성일: 2026-03-04 | 상태: 초안 | 범위: Phase 3 신규 사용자 셋업 | 의존: auth, local-bridge

---

## 0. 온보딩 단계 정의

| 단계 | 내용 | 완료 조건 |
|------|------|---------|
| 1 | 이메일 계정 생성 + 인증 | email_verified = true |
| 2 | 위험고지 수락 | 동의 저장 |
| 3 | 로컬 브릿지 설치 | WS 연결 성공 |
| 4 | 영웅문 HTS 로그인 안내 | kiwoom_connected = true |
| 5 | 연결 테스트 | `GET /api/kiwoom/status` 성공 |
| 6 | 첫 전략 설정 | 활성 규칙 >= 1 (또는 스킵) |

---

## 1. 구현 단계

### Step 1 — 온보딩 상태 추적

**목표**: 사용자별 온보딩 단계 저장 + 재방문 시 이어하기

파일: `backend/app/models/auth.py` 확장

```python
class OnboardingState(Base):
    __tablename__ = "onboarding_states"
    user_id        = Column(UUID, ForeignKey("users.id"), primary_key=True)
    step_completed = Column(Integer, default=0)  # 0~6
    risk_accepted  = Column(Boolean, default=False)
    risk_accepted_at = Column(DateTime, nullable=True)
    completed_at   = Column(DateTime, nullable=True)
```

API:
```
GET  /api/onboarding/status    → { step_completed, is_complete }
POST /api/onboarding/step/{n}  → 단계 완료 표시
POST /api/onboarding/accept-risk → risk_accepted = true
```

**검증:**
- [ ] 첫 로그인 → step_completed = 0 (이메일 인증 완료 = step 1)
- [ ] 중간 이탈 후 재접속 → 이어하기

### Step 2 — 위험고지 UI

파일: `frontend/src/pages/Onboarding.tsx` (단계별 컴포넌트)

위험고지 내용 (자본시장법 포지셔닝 반영):
```
⚠️ 투자 위험 고지

본 서비스는 사용자가 직접 정의한 자동매매 규칙을 실행하는
"시스템매매 도구"입니다. 투자 추천이나 투자 일임 서비스가 아닙니다.

- 모든 투자 의사결정의 주체는 사용자입니다
- 원금 손실이 발생할 수 있습니다
- 과거 성과가 미래 수익을 보장하지 않습니다

[동의하고 계속하기] ← 클릭 + 체크박스 2개 확인 후 활성화
```

**검증:**
- [ ] 체크박스 모두 선택 전 버튼 비활성화
- [ ] 동의 후 `/api/onboarding/accept-risk` 저장

### Step 3 — 브릿지 설치 안내 UI

**목표**: 로컬 서버 설치 + 실행 가이드 + 연결 자동 감지

```
[단계 3/6] 로컬 브릿지 설치

1. 아래 버튼으로 설치파일 다운로드
   [StockVision v1.0.0 다운로드 (.exe)]

2. 설치 후 실행하면 자동으로 백그라운드에서 시작됩니다

연결 상태 확인 중... (5초마다 자동 체크)
🔴 연결 대기 중
↓ (설치 + 실행 후)
🟢 연결됨! → [다음 단계] 버튼 활성화
```

React에서 5초마다 `ws://localhost:8765/ws` 연결 시도 → 성공 시 자동 다음 단계

**검증:**
- [ ] 로컬 서버 없음 → 설치 안내 + 대기
- [ ] 로컬 서버 시작 → 자동 감지 + 다음 단계 활성화

### Step 4 — 키움 HTS 연결 안내

```
[단계 4/6] 키움 HTS 로그인

영웅문 HTS에서 직접 로그인해 주세요.

[키움증권 HTS 다운로드] ← 외부 링크

StockVision은 사용자의 ID/PW를 저장하지 않습니다.
키움 자격증명은 영웅문 HTS에서만 관리됩니다.

연결 상태: 🟢 연결됨 (모의투자 모드)
           → [다음 단계]
```

**검증:**
- [ ] HTS 로그인 후 `kiwoom_connected = true` 감지 → 다음 단계

### Step 5 — 첫 전략 설정 (건너뛰기 가능)

```
[단계 6/6] 첫 전략 만들기 (선택)

[샘플 전략 불러오기]  [직접 만들기]  [나중에 하기]
```

**검증:**
- [ ] 샘플 전략 불러오기 → 전략 빌더로 이동
- [ ] 나중에 하기 → 온보딩 완료 (활성 규칙 0 허용)
- [ ] 완료 후 대시보드 이동

---

## 2. 파일 목록

| 파일 | 내용 |
|------|------|
| `backend/app/models/auth.py` | OnboardingState 모델 추가 |
| `backend/app/api/onboarding.py` | 온보딩 상태 API |
| `frontend/src/pages/Onboarding.tsx` | 단계별 온보딩 페이지 |
| `frontend/src/components/RiskDisclosure.tsx` | 위험고지 컴포넌트 |
| `frontend/src/components/BridgeInstaller.tsx` | 브릿지 설치 안내 |

---

## 3. 커밋 계획

| 커밋 | 메시지 |
|------|--------|
| 1 | `feat: Step 1 — 온보딩 상태 추적 DB + API` |
| 2 | `feat: Step 2 — 위험고지 UI` |
| 3 | `feat: Step 3~4 — 브릿지 설치 + 키움 연결 안내` |
| 4 | `feat: Step 5 — 첫 전략 설정 + 온보딩 완료` |
