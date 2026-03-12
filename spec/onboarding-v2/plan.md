# 온보딩 신뢰 강화 구현 계획

> 작성일: 2026-03-12 | 상태: 확정 | Phase C (C5)

## 아키텍처

### 온보딩 위저드 4단계 흐름 (변경 없음, UI 개선만)

```
Step 1: RiskDisclosure (위험고지 + 맥락)
  ├─ 카드 3개 레이아웃 (🔒 로컬 실행 / ⚖ 사용자 책임 / 🧪 모의투자 권장)
  ├─ 각 카드에 아이콘 + 설명문
  └─ 동의 체크박스

Step 2: BridgeInstaller (로컬 서버 설치 + 세분화)
  ├─ 맥락 설명: 왜 로컬 서버인지
  ├─ 하위 진행 상태 3단계 (다운로드 ✓ / 실행 ⏳ / 연결 ○)
  ├─ 각 단계의 상태 시각화 (진행 중 / 완료)
  ├─ 딥링크 실패 시 수동 실행 안내 (exe 경로)
  └─ 포트 충돌/연결 실패 안내

Step 3: BrokerKeyForm (증권사 연결)
  ├─ 기존 로직 유지
  └─ 맥락 설명 추가: 왜 API 키가 필요한지

Step 4: Summary (연결 상태 요약)
  ├─ 실시간 연결 상태 표시 (로컬/브로커/클라우드)
  ├─ 미완료 항목에 "돌아가기" 링크
  └─ "대시보드로 이동" 애니메이션
```

각 단계는 독립적이며, 단계 진입 시 **왜 필요한지**를 명확히 설명한다.

---

## 수정 파일 목록

### 1. `frontend/src/components/onboarding/RiskDisclosure.tsx` (신규 또는 개선)

**변경 내용:**
- 카드 레이아웃 3개로 재구성 (기존 텍스트 + 체크박스 형식 → 아이콘 + 카드)
- 아이콘 추가:
  - 🔒 (Lock) — "로컬 실행" 설명
  - ⚖ (Balance) — "사용자 책임" 설명
  - 🧪 (Flask) — "모의투자 권장" 설명
- 각 카드에 제목, 설명, 배경색 구분
- 하단 "확인했습니다" 체크박스 통합
- Tailwind: `bg-gray-800`, 각 카드마다 border + rounded-lg

**사용 리소스:**
- HeroUI 컴포넌트 (필요 시) 또는 vanilla HTML
- Tailwind CSS grid (3열 또는 responsive 2줄)

---

### 2. `frontend/src/components/BridgeInstaller.tsx` (개선)

**변경 내용:**
- 맥락 설명 추가 (상단에 작은 텍스트)
  - "주문은 이 PC에서만 실행됩니다. API 키와 비밀번호는 외부로 전송되지 않습니다."
- 하위 진행 상태 세분화:
  - 기존: 3단계 (download / run / connect)
  - 개선: 동일 3단계지만 상태 표시 강화
    - "✅ 완료" → 녹색 배경 + 체크
    - "⏳ 진행 중" → 노란색/파란색 배경 + 스피너
    - "○ 대기" → 회색 배경 + 숫자
- 딥링크 실패 시 수동 실행 안내 개선:
  - 현재: "프로그램이 설치되어 있지 않거나..."
  - 개선: "⚠ 자동 시작이 안 되나요?" + exe 경로 표시
    - Windows 경로 예: `C:\Users\{username}\AppData\Local\StockVision\stockvision.exe`
    - 또는 "직접 실행" 버튼 추가
- 포트 충돌 감지 안내:
  - 현재: "포트 4020이 이미 사용 중인 경우" 텍스트만 있음
  - 개선: 실제로 health check에서 `data.app !== 'stockvision'`이면 명확한 메시지
- 상태 폴링 재시도 횟수 표시 유지

**사용 리소스:**
- 기존 로직 유지 (phase 상태, health check 폴링)
- Tailwind 배경색: done=green-900/20, active=indigo-600/20 또는 yellow-600/20
- 아이콘: 이모지 또는 simple SVG

---

### 3. `frontend/src/pages/OnboardingWizard.tsx` (개선)

**변경 내용:**
- Step 2, 3 맥락 설명 강화:
  - 기존 `<p className="text-xs text-gray-500 mb-5">` 텍스트 개선
  - Step 2: "주문 실행을 위한 로컬 프로그램을 설치하고 실행하세요." → 더 상세하게
    - "StockVision 로컬 서버는 주문을 이 PC에서만 실행합니다. 비밀번호는 Windows 자격 증명에 안전하게 저장됩니다."
  - Step 3: "증권사 API 키를 등록하여 주문 기능을 활성화하세요." → 유지
- Step 4 요약 강화:
  - 기존 `SummaryRow` 유지하되, 색상/상태 표시 더 강화
  - 연결 상태 실시간 갱신 (useAccountStatus 이미 연결됨)
  - 미완료 항목 링크 추가 (예: "로컬 서버 미연결 → 2단계로 돌아가기")
  - "대시보드로 이동" 버튼에 간단한 fade-in 애니메이션

**사용 리소스:**
- 기존 RiskDisclosure, BridgeInstaller, BrokerKeyForm 컴포넌트 호출 (개선된 버전)
- useAccountStatus hook 이미 있음 (brokerConnected, isMock, localReady)
- Tailwind: `animate-fade-in` 또는 기본 transition

---

### 4. `frontend/src/components/onboarding/StepIndicator.tsx` (기존 유지)

**변경 내용:**
- 변경 없음 (현재 구현 이미 충분)
- 필요 시 각 단계별 진행률 시각화 추가 (선택적)

---

## 구현 순서

### Step 1: 위험 고지 시각화 강화
**담당:** Frontend dev
**예상 시간:** 2-3시간

**작업:**
1. `frontend/src/components/onboarding/RiskDisclosure.tsx` 확인 또는 신규 작성
   - 기존 파일이 있다면 카드 레이아웃으로 재구성
   - 없다면 신규 작성 (이미 `OnboardingWizard.tsx`에서 import 중)
2. 카드 3개: 🔒 로컬 실행 / ⚖ 사용자 책임 / 🧪 모의투자
   - 각 카드 배경색: gray-800/50 + border-gray-700
   - 아이콘 크기: text-2xl, margin-right 일관성
   - 설명 텍스트: text-xs, text-gray-300
3. 하단 체크박스 + "다음" 버튼 통합
   - 체크 전 버튼 disabled

**검증 (verify):**
- [ ] 브라우저에서 `npm run dev` 실행
- [ ] Step 1 진입: 3개 카드 표시 확인
- [ ] 각 아이콘과 텍스트가 정렬됨
- [ ] 체크박스 체크 전 "다음" 버튼 disabled 상태
- [ ] 반응형 확인 (mobile 뷰에서 1열로 표시)

---

### Step 2: 브릿지 설치 단계 세분화 및 수동 실행 안내
**담당:** Frontend dev
**예상 시간:** 3-4시간

**작업:**
1. `frontend/src/components/BridgeInstaller.tsx` 개선
2. 맥락 설명 추가 (상단 작은 텍스트)
   ```
   "주문은 이 PC에서만 실행됩니다. API 키와 비밀번호는 외부로 전송되지 않습니다."
   ```
3. 3단계 진행 상태 시각화 강화
   - done: `✅ 완료` (green-600, green-900/20 배경)
   - active: `⏳ 진행 중` (indigo-600 또는 blue-600)
   - pending: `○ 대기` (gray-600)
4. 딥링크 실패 시 수동 실행 안내
   - 현재 `deeplinkFailed && wasInstalled` 조건은 유지
   - 메시지 개선: "⚠️ 자동 시작이 안 되나요?"
   - exe 경로 표시:
     ```
     %APPDATA%\Local\StockVision\stockvision.exe
     또는
     직접 경로: C:\Users\{username}\AppData\Local\StockVision\stockvision.exe
     ```
   - "수동으로 실행" 링크/버튼 추가 (Windows 탐색기 열기)
5. 포트 충돌 감지:
   - health check에서 `data.app !== 'stockvision'` 시
   - 메시지: "포트 4020이 다른 프로그램에서 사용 중입니다. 방화벽 또는 바이러스 백신을 확인하세요."
6. 재시도 횟수 표시 유지 (현재 `${retries}회 시도`)

**검증 (verify):**
- [ ] Step 2 진입: 맥락 설명 표시
- [ ] 3단계 진행 상태 색상 구분 확인
- [ ] 딥링크 2초 후 실패 시 "자동 시작이 안 되나요?" 메시지 표시
- [ ] exe 경로 문자열이 명확하게 표시됨 (복사 가능한 텍스트)
- [ ] 재시도 3회 이상 시 "연결이 안 되나요?" 팁 표시
- [ ] 수동 실행 버튼 클릭 시 탐색기 열림 (또는 명령어 복사)

---

### Step 3: 각 단계 맥락 설명 추가
**담당:** Frontend dev
**예상 시간:** 1-2시간

**작업:**
1. `OnboardingWizard.tsx` Step 2, 3, 4 subtitle 개선
   - Step 2 (로컬 서버):
     ```
     기존: "주문 실행을 위한 로컬 프로그램을 설치하고 실행하세요."
     개선: "StockVision 로컬 서버는 주문을 이 PC에서만 실행합니다.
            비밀번호는 Windows 자격 증명에 안전하게 저장됩니다."
     ```
   - Step 3 (증권사): 기존 유지 (이미 충분)
   - Step 4 (완료): "설정이 완료되었습니다. 대시보드에서 시작하세요." 유지

2. RiskDisclosure 스타일링 최종 점검

**검증 (verify):**
- [ ] Step 2 subtitle 개선된 텍스트 표시
- [ ] 텍스트가 줄 바뀜 없이 최대 2줄 정도로 깔끔함
- [ ] 텍스트 색상 일관성 (text-gray-500 또는 text-gray-400)

---

### Step 4: 요약 단계 강화 및 애니메이션
**담당:** Frontend dev
**예상 시간:** 2-3시간

**작업:**
1. Step 4 SummaryRow 강화
   - 현재 구현 이미 상태 표시함 (ok boolean)
   - 시각적 개선:
     - ok=true: "● 연결됨" (green-400) + 버전/모드 표시
     - ok=false: "● 미연결" (yellow-400) + "설정하기" 링크
2. 미완료 항목 "돌아가기" 링크
   ```tsx
   {!ok && (
     <button
       onClick={() => setStep(해당_단계)}
       className="text-xs text-indigo-400 hover:underline"
     >
       설정하기
     </button>
   )}
   ```
3. "대시보드로 이동" 버튼 애니메이션
   - 현재: 단순 클릭
   - 개선: fade-in 또는 slide-up 애니메이션
   ```css
   /* Tailwind: 기존 .tsx에 inline style 또는 global CSS */
   animate-fade-in = "opacity-0 animate-[fadeIn_0.5s_ease-in-out]"
   ```
4. 다음 단계 안내 (현재 있음, 스타일 점검)
   - "대시보드에서 관심 종목을 추가하세요" 등
   - 색상: indigo-900/20 + border-indigo-800/50 유지

**검증 (verify):**
- [ ] Step 4 진입: 3개 연결 상태 표시
- [ ] localReady=false 시 "미연결" + "2단계로 이동" 링크 클릭 가능
- [ ] brokerConnected=false 시 "미연결" + "3단계로 이동" 링크
- [ ] 모든 상태가 ok=true일 때 "대시보드로 이동" 버튼 활성화
- [ ] 버튼 클릭 시 부드러운 애니메이션 후 대시보드(/) 이동

---

## 검증 방법

### 로컬 빌드 & 브라우저 테스트

1. **빌드 및 기동**
   ```bash
   cd frontend
   npm run dev   # http://localhost:5173
   ```

2. **Step 1 (위험 고지)**
   - [ ] 3개 카드 표시 확인
   - [ ] 아이콘과 텍스트 정렬
   - [ ] 체크박스 unchecked 상태에서 "다음" 버튼 disabled
   - [ ] 체크 후 버튼 enabled
   - [ ] "다음" 클릭 → Step 2 이동

3. **Step 2 (로컬 서버 설치)**
   - [ ] 맥락 설명 텍스트 표시
   - [ ] 3단계 진행 상태 (다운로드 ✓ / 실행 ⏳ / 연결 ○)
   - [ ] 다운로드 버튼 클릭 → 다운로드 스타트
   - [ ] 서버 실행 시 연결 확인 (재시도 횟수 증가)
   - [ ] 연결 완료 시 "✅ 연결됨!" 표시 + Step 3 자동 이동 (자동 스킵)
   - [ ] 딥링크 실패 시 "⚠️ 자동 시작이 안 되나요?" 메시지 + exe 경로 표시
   - [ ] 재시도 3회 이상 → "연결이 안 되나요?" 팁 표시

4. **Step 3 (증권사 연결)**
   - [ ] 기존 로직 유지 (키 입력/저장)
   - [ ] 성공 시 → Step 4 이동 (또는 자동 스킵)

5. **Step 4 (완료)**
   - [ ] 3개 연결 상태 표시 (계정 / 로컬 / 브로커)
   - [ ] 모두 ok=true 상태 확인
   - [ ] "대시보드로 이동" 버튼 활성화
   - [ ] 클릭 → 부드러운 애니메이션 후 대시보드(/) 이동

6. **전체 플로우**
   - [ ] 온보딩 4단계 완료 후 다시 `/onboarding` 접근 → 대시보드로 리다이렉트
   - [ ] localStorage `onboarding_complete` 확인

### ESLint & 빌드

```bash
cd frontend
npm run lint   # 에러 없음
npm run build  # 성공
```

---

## 추가 고려사항

### UX 우선순위
- 명확한 상태 표시: "지금 뭐가 되고 있나?" 한눈에 알 수 있어야 함
- 실패 시 대안: "막혔을 때 뭘 해야 하나?" 명확한 가이드
- 신뢰감: "이 과정이 왜 필요한지?" 각 단계마다 설명

### 성능
- health check 폴링: 5초 간격 (현재 구현 유지)
- 장시간 미응답 시: 최대 몇 분까지 재시도할지 명시 (현재 무한)

### 향후 개선
- Step 2에서 exe 자동 다운로드 링크 추가 (Phase C6+)
- Step 4에서 "모의투자 시뮬레이션 시작" 버튼 추가
- 모바일 PWA 온보딩 (Phase C6)

---

## 참고 파일

- Spec: `spec/onboarding-v2/spec.md`
- 온보딩 위저드: `frontend/src/pages/OnboardingWizard.tsx` (157줄)
- 브릿지 설치: `frontend/src/components/BridgeInstaller.tsx` (145줄)
- UX PRD: `docs/product/frontend-ux-priority-prd-2026-03-10.md` §P1
