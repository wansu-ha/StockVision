# 온보딩 플로우 명세서 (onboarding)

> 작성일: 2026-03-04 | 상태: **→ Unit 5 (frontend)에 통합**
>
> 이 spec의 내용은 `spec/frontend/`에서 통합 구현합니다.

---

## 1. 개요

**온보딩(Onboarding)**은 신규 사용자가 StockVision을 처음 사용할 때 거쳐야 하는 일련의 단계로,
자동매매를 시작하기 위해 필요한 계정 설정, 외부 서비스 연동, 로컬 브릿지 설치 등을 체계적으로 안내한다.

### 온보딩의 목표

1. **마찰 최소화**: 필수 설정을 < 30분 안에 완료 가능하도록
2. **명확한 진행**: 각 단계의 목적, 소요 시간, 완료 기준을 명확히
3. **이탈 방지**: "나중에 계속하기" 옵션으로 부분 완료 지원
4. **스스로 해결**: FAQ, 자동 검증, 1-클릭 재시도 기능

### 온보딩 완료 조건

사용자가 다음을 모두 만족할 때 온보딩 완료:

- ✅ 이메일로 계정 생성/로그인
- ✅ 시스템매매 위험고지 수락
- ✅ 로컬 브릿지 설치 및 실행 (모의투자 기준)
- ✅ 키움증권 API 키 설정
- ✅ 연결 테스트 완료 (서버 ↔ 브릿지 ↔ 키움)
- ✅ 첫 전략 만들기 (또는 샘플 전략 로드)

---

## 2. 온보딩 단계 전체 흐름

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Step 0: 사전 준비물 확인                    (소요: 1분)                    │
│ [자동 체크] Windows 버전, 인터넷 연결 확인                               │
└──────────────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ Step 1: 계정 생성/로그인                   (소요: 2분)                    │
│ [매직 링크] 이메일 → 링크 클릭 → 로그인                                 │
│ 또는 [계정 없이 시작] → UUID 발급                                        │
└──────────────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ Step 2: 위험고지 수락                      (소요: 3분)                    │
│ [필수] 시스템매매 위험 및 면책사항 읽기 + 체크박스 동의                  │
└──────────────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ Step 3: 로컬 브릿지 설치 안내               (소요: 5분)                    │
│ [Windows 서비스] 1-클릭 설치 또는 수동 설치                              │
│ • Python 설치 (자동/수동)                                                │
│ • pip install stockvision-bridge                                        │
│ • 설치 완료 확인 (상태 체크)                                             │
└──────────────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ Step 4: API 키 설정                        (소요: 10분)                   │
│ [UI 가이드] 키움증권 앱키/시크릿키 입력 + 자동 검증                     │
│ • 키움 OpenAPI+ 발급 링크 제공                                           │
│ • 계좌번호 입력 (모의투자 or 실거래)                                    │
│ • 암호화 저장 (로컬 전용)                                               │
└──────────────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ Step 5: 연결 테스트                        (소요: 2분)                    │
│ [자동 검증] 서버 → 브릿지 → 키움 3단계 연결 확인                        │
│ • 신호 송수신 테스트                                                    │
│ • 모의 주문 실행 테스트                                                 │
│ • 실시간 데이터 수신 테스트                                             │
└──────────────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ Step 6: 첫 전략 만들기 (또는 로드)          (소요: 5분)                    │
│ [빠른 시작] 샘플 전략 선택 또는 직접 만들기                              │
│ • RSI + EMA 콤보 (추천)                                                 │
│ • MACD 트레이딩                                                         │
│ • 직접 작성 (고급 사용자)                                               │
└──────────────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────────────────────────────────────────────────────────┐
│ ✅ 온보딩 완료!                                                           │
│ 대시보드로 이동 → 전략 실행 또는 백테스팅 시작                            │
└──────────────────────────────────────────────────────────────────────────┘
```

### 소요 시간 요약
- **최소 (빠른 경로)**: 13분 (모의 앱키 사전 준비)
- **평균 (일반 사용자)**: 25분 (앱키 발급 포함)
- **최대 (수동 설치)**: 35분 (Python 설치부터 시작)

---

## 3. 단계별 상세 (UI + 안내 문구)

### Step 0: 사전 준비물 확인

#### 목적
사용자 환경이 온보딩 진행 가능 여부를 판단하기 위해 자동으로 확인.

#### UI 화면
```
┌─────────────────────────────────────────┐
│ StockVision 온보딩 체크리스트             │
│━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                         │
│ ✅ Windows 10 이상 감지됨                 │
│ ✅ 인터넷 연결 OK                         │
│ ⚠️  .NET Framework 4.5 미확인             │
│    (키움 API 필요)                      │
│                                         │
│ [다음: 계정 만들기] →                    │
└─────────────────────────────────────────┘
```

#### 백엔드 로직
```python
# backend/app/services/onboarding_service.py
def check_client_environment():
    """클라이언트 환경 사전 검사"""
    return {
        "os": "windows",
        "os_version": "11",
        "internet": True,
        "dotnet_framework": "4.8",  # 또는 None
        "warnings": [
            ".NET Framework 확인 권장: https://..."
        ],
        "ready": True  # 진행 가능 여부
    }
```

#### 프론트엔드 로직
```typescript
// frontend/src/pages/Onboarding/Step0.tsx
useEffect(() => {
  const checkEnv = async () => {
    try {
      const res = await api.get('/api/v1/onboarding/env-check');
      setEnvStatus(res.data.data);
      if (!res.data.data.ready) {
        setWarning(res.data.data.warnings[0]);
      }
    } catch (err) {
      setWarning('환경 확인 실패');
    }
  };
  checkEnv();
}, []);
```

---

### Step 1: 계정 생성/로그인

#### 목적
StockVision 계정을 통해 사용자 전략, 설정, 거래 기록을 클라우드에 동기화.

#### 두 가지 경로

##### 경로 A: 이메일로 가입 (권장)
```
┌─────────────────────────────────────────┐
│ StockVision 계정 만들기                  │
│━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                         │
│ 📧 이메일 주소                           │
│ ┌───────────────────────────────┐       │
│ │ your@example.com              │       │
│ └───────────────────────────────┘       │
│                                         │
│ 💡 매직 링크로 로그인됩니다.              │
│    비밀번호는 필요 없습니다.             │
│                                         │
│ [매직 링크 받기]                         │
│                                         │
│ 또는 계정 없이 시작 ↓                    │
└─────────────────────────────────────────┘
```

**흐름:**
1. 이메일 입력 → "매직 링크 받기" 클릭
2. 백엔드: 매직 링크 토큰 생성 + 이메일 발송
3. 사용자: 이메일의 링크 클릭
4. 프론트엔드: JWT 저장 + 다음 단계로

**API 엔드포인트:**
```
POST /api/v1/auth/magic-link
{ "email": "user@example.com" }

응답:
{
  "success": true,
  "data": {
    "message": "매직 링크가 이메일로 발송되었습니다",
    "expiresIn": 600
  }
}
```

##### 경로 B: 계정 없이 시작 (선택)
```
┌─────────────────────────────────────────┐
│ 계정 없이 시작할까요?                    │
│━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                         │
│ ℹ️  계정 없이도 기본 기능을 사용할 수    │
│    있습니다 (이 기기에서만).              │
│                                         │
│ ⚠️  다음은 나중에 필요합니다:            │
│    • 다른 기기에서 전략 불러오기         │
│    • 거래 기록 클라우드 백업              │
│                                         │
│ [지금은 건너뛰기]                        │
└─────────────────────────────────────────┘
```

**API 엔드포인트:**
```
POST /api/v1/auth/anonymous

응답:
{
  "success": true,
  "data": {
    "uuid": "550e8400-...",
    "expiresAt": null
  }
}
```

#### 프론트엔드 로직 예시
```typescript
// frontend/src/pages/Onboarding/Step1.tsx
const [email, setEmail] = useState('');
const [step, setStep] = useState<'input' | 'confirm'>('input');

const handleMagicLink = async () => {
  const res = await authService.sendMagicLink(email);
  if (res.success) {
    setStep('confirm');
    // 60초 후 자동으로 /onboarding/step2로 이동 (링크 클릭 후)
  }
};

const handleAnonymous = async () => {
  const res = await authService.createAnonymous();
  if (res.success) {
    authService.saveAnonymousId(res.data.uuid);
    navigate('/onboarding/step2');
  }
};
```

---

### Step 2: 위험고지 수락

#### 목적
사용자에게 시스템매매의 위험성을 충분히 인지하도록 하고, 법적 책임을 명확히.

#### UI 화면
```
┌──────────────────────────────────────────────────┐
│ 시스템매매 위험고지                              │
│━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                  │
│ 📋 아래 내용을 읽고 동의해주세요.                 │
│                                                  │
│ ┌──────────────────────────────────────────┐   │
│ │ 1. 손실 위험                              │   │
│ │ 자동매매는 손실을 초래할 수 있습니다.       │   │
│ │ StockVision은 손실에 대해 책임지지 않습니다. │   │
│ │                                          │   │
│ │ 2. 기술적 위험                            │   │
│ │ • 네트워크 오류로 주문 실패                │   │
│ │ • 시스템 오류로 예상치 못한 주문            │   │
│ │ • AI 모델의 부정확한 예측                  │   │
│ │                                          │   │
│ │ 3. 규제                                  │   │
│ │ • 키움증권 G5 조건 준수 필수               │   │
│ │ • 한국 금융감시원 규정 준수                │   │
│ │                                          │   │
│ │ 4. API 키 보안                            │   │
│ │ • API 키를 타인과 공유하지 마세요.          │   │
│ │ • 유출 시 계좌 도용 위험                  │   │
│ │                                          │   │
│ │ [전문 보고서 다운로드]                      │   │
│ └──────────────────────────────────────────┘   │
│                                                  │
│ ☐ 위 내용을 모두 읽고 이해했습니다.               │
│ ☐ 손실 발생 시 StockVision을 탓하지 않겠습니다.  │
│ ☐ 자신의 자산으로 책임감 있게 운영하겠습니다.    │
│                                                  │
│ [3개 모두 체크해야 다음으로 이동]                  │
│                                                  │
│ [계속하기]  [나중에]                             │
└──────────────────────────────────────────────────┘
```

#### 데이터 저장
```python
# 사용자가 3개 체크박스 모두 선택했을 때
PUT /api/v1/onboarding/step2-agree

Request:
{
  "agreed_risk_notice": True,
  "agreed_no_liability": True,
  "agreed_responsible_operation": True,
  "timestamp": "2026-03-04T10:00:00Z"
}

Response:
{
  "success": true,
  "data": {
    "step_completed": 2,
    "next_step": 3
  }
}
```

---

### Step 3: 로컬 브릿지 설치 안내

#### 목적
사용자의 PC에 StockVision Local Bridge를 설치하고, 키움 OpenAPI+ 호출 준비 완료.

#### 세 가지 설치 옵션

##### 옵션 A: 1-클릭 설치 (권장, Windows만)
```
┌─────────────────────────────────────────┐
│ 로컬 브릿지 설치 (자동)                  │
│━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                         │
│ 🚀 1-클릭으로 설치를 시작합니다.         │
│                                         │
│ 설치될 항목:                             │
│ ✓ Python 3.13 (없을 경우)               │
│ ✓ Local Bridge 바이너리                 │
│ ✓ Windows 서비스 등록 (자동 시작)       │
│                                         │
│ 소요 시간: ~2분 (인터넷 속도에 따름)     │
│                                         │
│ [설치 시작]                             │
│                                         │
│ 또는 수동 설치: ↓                        │
└─────────────────────────────────────────┘
```

**백엔드 로직:**
```python
# backend/app/services/bridge_installer.py
async def generate_installer(user_id: int, bridge_config: dict):
    """사용자 맞춤 설치 스크립트 생성"""
    script = f"""
    # StockVision Local Bridge 설치 스크립트
    # Windows PowerShell Admin 에서 실행

    # Step 1: Python 3.13 설치
    if (-not (python --version)) {{
        Write-Host "Python 설치 중..."
        # Chocolatey 또는 공식 설치
    }}

    # Step 2: Local Bridge 설치
    pip install stockvision-bridge

    # Step 3: 설정
    $token = "{generate_bridge_token(user_id)}"
    bridge-cli --config-init --token=$token

    # Step 4: 서비스 등록
    nssm install StockVisionBridge "python -m stockvision_bridge"
    nssm start StockVisionBridge
    """
    return script
```

**프론트엔드 로직:**
```typescript
// frontend/src/pages/Onboarding/Step3.tsx
const [installProgress, setInstallProgress] = useState<'idle' | 'installing' | 'done'>('idle');

const startAutoInstall = async () => {
  setInstallProgress('installing');

  // IPC로 설치 스크립트 실행 (Electron이 있는 경우)
  const success = await window.ipcRenderer.invoke('install-bridge');

  if (success) {
    setInstallProgress('done');
    // 30초마다 헬스체크
    const checkHealth = setInterval(async () => {
      const res = await api.get('/api/v1/onboarding/bridge-health');
      if (res.data.data.status === 'running') {
        clearInterval(checkHealth);
        // Step 4로 자동 이동
        navigate('/onboarding/step4');
      }
    }, 5000);
  }
};
```

##### 옵션 B: 수동 설치 (고급 사용자)
```
┌─────────────────────────────────────────┐
│ 로컬 브릿지 수동 설치                    │
│━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                         │
│ Step 1: Python 3.13 설치                │
│ https://www.python.org/downloads/      │
│ ✅ "PATH에 추가" 체크해주세요!           │
│                                         │
│ Step 2: 명령 프롬프트 열기               │
│ (Win + R → cmd → Enter)                 │
│                                         │
│ Step 3: 아래 명령 실행                   │
│                                         │
│ ┌──────────────────────────────────┐   │
│ │ pip install stockvision-bridge    │   │
│ └──────────────────────────────────┘   │
│                                         │
│ 설치 완료 메시지:                        │
│ "Successfully installed stockvision..." │
│                                         │
│ [✅ 설치 완료했습니다]                   │
└─────────────────────────────────────────┘
```

##### 옵션 C: Docker 설치 (클라우드 VM)
```
┌─────────────────────────────────────────┐
│ Docker로 클라우드 VM에 배포               │
│━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                         │
│ (미래 기능: Phase 4)                     │
│                                         │
│ AWS EC2 또는 Google Cloud 에서 24/7    │
│ 자동매매 시스템 실행 가능                 │
│                                         │
│ [더 알아보기]                            │
└─────────────────────────────────────────┘
```

#### 설치 상태 체크
```
API: GET /api/v1/onboarding/bridge-health

Response:
{
  "success": true,
  "data": {
    "status": "running",  // or "stopped", "error"
    "version": "1.0.0",
    "uptime_seconds": 125,
    "last_signal": "2026-03-04T10:05:00Z"
  }
}
```

---

### Step 4: API 키 설정

#### 목적
사용자의 키움증권 OpenAPI+ 키를 로컬 브릿지에 설정하고, 연결 검증.

#### UI 화면
```
┌──────────────────────────────────────────────────┐
│ 키움증권 API 키 설정                             │
│━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                  │
│ 🔐 키움에서 받은 API 키를 입력하세요.            │
│ (로컬 암호화 저장, 서버에는 저장 안 함)          │
│                                                  │
│ 1️⃣  App Key (32자리)                            │
│ ┌────────────────────────────────────┐         │
│ │                                    │         │
│ └────────────────────────────────────┘         │
│                                                  │
│ 2️⃣  App Secret (40자리)                         │
│ ┌────────────────────────────────────┐         │
│ │                                    │         │
│ └────────────────────────────────────┘         │
│                                                  │
│ 3️⃣  계좌 번호                                    │
│ ┌────────────────────────────────────┐         │
│ │ 예: 12345678-01                    │         │
│ └────────────────────────────────────┘         │
│                                                  │
│ 4️⃣  거래 모드                                    │
│ ◉ 모의투자 (데모)                              │
│ ○ 실거래 (실제 자산)                           │
│                                                  │
│ [키움 OpenAPI+ 발급받기]                         │
│ 아직 API 키가 없다면:                            │
│ https://openapi.kiwoom.com/ (새 창)             │
│                                                  │
│ [검증 및 저장]                                   │
│                                                  │
│ ⚠️  모의투자: 손실 걱정 없음 ✓                   │
│     (권장: 먼저 모의투자로 테스트)               │
└──────────────────────────────────────────────────┘
```

#### API 키 저장 흐름

```
[프론트엔드]
  ↓
  사용자 입력: app_key, secret_key, account, mode
  ↓
  로컬 암호화 (XChaCha20)
  ↓
  로컬 스토리지에만 저장

[로컬 브릿지]
  ↓
  프론트엔드에서 수신 (또는 파일에서 로드)
  ↓
  키움 API 테스트 호출
  ↓
  백엔드로 "설정 완료" 리포트 (키 제외)
```

#### 백엔드 API
```python
# /api/v1/onboarding/step4-api-keys
# 프론트엔드는 키를 **절대** 서버로 전송 금지

POST /api/v1/onboarding/step4-config-init
{
  "bridge_id": "uuid-xxx",
  "account_number": "12345678-01",
  "mode": "demo"  # or "real"
}

Response:
{
  "success": true,
  "data": {
    "step_completed": 4,
    "message": "브릿지 설정이 초기화되었습니다",
    "next_step": 5
  }
}
```

#### 프론트엔드 로직 (암호화)
```typescript
// frontend/src/utils/cryptoUtils.ts
import { box, randomBytes } from 'tweetnacl';

export async function encryptAPIKey(
  appKey: string,
  secretKey: string
): Promise<string> {
  const plaintext = JSON.stringify({ appKey, secretKey });
  const nonce = randomBytes(24);
  const encrypted = box.secretbox(
    Buffer.from(plaintext),
    nonce,
    deriveMasterKey()  // 브라우저 내부 암호화 키
  );
  return Buffer.concat([nonce, encrypted]).toString('base64');
}

export async function decryptAPIKey(encrypted: string): Promise<any> {
  // 필요할 때만 복호화
  const buffer = Buffer.from(encrypted, 'base64');
  const nonce = buffer.slice(0, 24);
  const ciphertext = buffer.slice(24);
  const plaintext = box.secretbox.open(
    ciphertext,
    nonce,
    deriveMasterKey()
  );
  return JSON.parse(Buffer.from(plaintext!).toString());
}
```

---

### Step 5: 연결 테스트

#### 목적
서버 ↔ 로컬 브릿지 ↔ 키움 3단계 연결이 모두 정상인지 검증.

#### UI 화면
```
┌──────────────────────────────────────────────────┐
│ 연결 테스트                                       │
│━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                  │
│ 아래 3단계 테스트를 진행합니다...                 │
│                                                  │
│ [1️⃣  서버 연결]                                 │
│     ⏳ 테스트 중...                              │
│                                                  │
│ [2️⃣  브릿지 상태]                               │
│     ⏳ 대기 중...                                │
│                                                  │
│ [3️⃣  키움 API]                                  │
│     ⏳ 대기 중...                                │
│                                                  │
│ ───────────────────────────────────────────┐  │
│ 예상 소요 시간: ~10초                        │  │
│ ───────────────────────────────────────────┘  │
└──────────────────────────────────────────────────┘

[완료 후]

┌──────────────────────────────────────────────────┐
│ 연결 테스트 완료! ✅                             │
│━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                  │
│ ✅ StockVision 서버            [OK]             │
│    응답 시간: 45ms                             │
│                                                  │
│ ✅ 로컬 브릿지                  [OK]             │
│    상태: 실행 중                                │
│    포트: 9090                                   │
│                                                  │
│ ✅ 키움 OpenAPI+              [OK]             │
│    계좌: 12345678-01                           │
│    모드: 모의투자                               │
│    잔고: 5,000,000원                           │
│                                                  │
│ 🎉 모든 준비가 완료되었습니다!                    │
│                                                  │
│ [다음: 첫 전략 만들기]  →                        │
└──────────────────────────────────────────────────┘
```

#### 테스트 항목 상세

| # | 테스트 | 내용 | 실패 시 대응 |
|----|--------|------|------------|
| 1 | 서버 연결 | HTTP GET /health | 네트워크/VPN 확인 |
| 2 | 브릿지 상태 | WebSocket ping/pong | 브릿지 재시작 |
| 3 | 키움 API | 잔고 조회 테스트 | API 키 재확인 |

#### 백엔드 테스트 API
```python
# /api/v1/onboarding/test

POST /api/v1/onboarding/test-connection
{
  "bridge_id": "uuid-xxx"
}

Response:
{
  "success": true,
  "data": {
    "tests": [
      {
        "name": "server_health",
        "status": "passed",
        "latency_ms": 45,
        "message": "서버 응답 OK"
      },
      {
        "name": "bridge_websocket",
        "status": "passed",
        "latency_ms": 23,
        "message": "브릿지 연결 OK"
      },
      {
        "name": "kiwoom_api",
        "status": "passed",
        "latency_ms": 156,
        "message": "키움 API 응답 OK",
        "details": {
          "account": "12345678-01",
          "balance": 5000000,
          "mode": "demo"
        }
      }
    ],
    "overall_status": "all_passed"
  }
}
```

---

### Step 6: 첫 전략 만들기

#### 목적
사용자가 첫 자동매매 전략을 구성하고, 즉시 실행 또는 백테스팅 가능하도록.

#### UI 화면
```
┌──────────────────────────────────────────────────┐
│ 첫 전략 만들기                                   │
│━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                  │
│ 추천 전략을 선택하거나 직접 만드세요.             │
│                                                  │
│ 📊 [추천] RSI + EMA 콤보                        │
│     초보자 친화적, 검증된 신호율                 │
│     • 셀 범위: 20~30 (과매도)                    │
│     • 매도 범위: 70~80 (과매수)                  │
│     • EMA 필터: 단기/장기 교차                  │
│     [이 전략으로 시작]                           │
│                                                  │
│ 📈 MACD 트레이딩                                │
│     중급 난이도                                  │
│     [이 전략으로 시작]                           │
│                                                  │
│ 🔧 나만의 전략 만들기                            │
│     고급 사용자용                                │
│     [커스텀 전략 작성]                           │
│                                                  │
│ ───────────────────────────────────────────────┐ │
│ 💡 팁: 먼저 백테스팅으로 성능을 확인하세요!     │ │
│ ───────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

#### 선택 후

```
┌──────────────────────────────────────────────────┐
│ 전략 설정: RSI + EMA 콤보                         │
│━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│                                                  │
│ 전략명:                                          │
│ [RSI + EMA 콤보 (내 버전)]                       │
│                                                  │
│ 종목 선택:                                       │
│ ☐ 삼성전자 (005930)                             │
│ ☐ SK하이닉스 (000660)                           │
│ ☐ NAVER (035420)                                │
│ ☐ 카카오 (035720)                               │
│ ☑ KOSPI 200 ETF (069500) ← 포트폴리오 분산용    │
│                                                  │
│ RSI 설정:                                        │
│ • 기간: 14일                                     │
│ • 과매도: 30 ─────●───── 70 과매수              │
│                                                  │
│ EMA 필터:                                        │
│ • 단기: 12일                                     │
│ • 장기: 26일                                     │
│                                                  │
│ 거래 설정:                                       │
│ • 1회 주문 수량: 1~3주                           │
│ • 일일 최대 손실: 100,000원                      │
│                                                  │
│ [백테스팅 실행]  [지금 시작]                     │
│                 (권장: 먼저 백테스팅)             │
└──────────────────────────────────────────────────┘
```

#### 프론트엔드 로직
```typescript
// frontend/src/pages/Onboarding/Step6.tsx
const [strategy, setStrategy] = useState('rsi_ema_combo');
const [symbols, setSymbols] = useState(['069500']);

const handleSelectStrategy = (template: string) => {
  // 샘플 전략 로드
  const templates: Record<string, any> = {
    rsi_ema_combo: {
      name: 'RSI + EMA 콤보',
      indicators: [
        { type: 'rsi', period: 14, oversold: 30, overbought: 70 },
        { type: 'ema', periods: [12, 26] }
      ]
    },
    macd: {
      name: 'MACD 트레이딩',
      indicators: [
        { type: 'macd', fast: 12, slow: 26, signal: 9 }
      ]
    }
  };

  setStrategy(templates[template]);
};

const handleBacktest = async () => {
  // 백테스팅으로 리다이렉트
  navigate('/backtest', {
    state: { strategy, symbols, onboard: true }
  });
};

const handleStart = async () => {
  // 지금 시작 (실시간 시그널)
  const res = await api.post('/api/v1/strategies', {
    name: strategy.name,
    config: strategy,
    symbols,
    enabled: true
  });

  if (res.data.success) {
    // 온보딩 완료
    navigate('/dashboard', {
      state: { newStrategyId: res.data.data.id }
    });
  }
};
```

---

## 4. 진행 상태 추적

### 데이터 모델 (Backend)

```python
# backend/app/models/onboarding.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime

class OnboardingProgress(Base):
    """사용자 온보딩 진행 상태"""
    __tablename__ = "onboarding_progress"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)

    # 각 단계별 완료 여부
    step0_env_check = Column(Boolean, default=False)
    step1_account_created = Column(Boolean, default=False)
    step2_risk_agreed = Column(Boolean, default=False)
    step3_bridge_installed = Column(Boolean, default=False)
    step4_api_configured = Column(Boolean, default=False)
    step5_connection_tested = Column(Boolean, default=False)
    step6_first_strategy = Column(Boolean, default=False)

    # 타임스탬프
    step0_completed_at = Column(DateTime, nullable=True)
    step1_completed_at = Column(DateTime, nullable=True)
    step2_completed_at = Column(DateTime, nullable=True)
    step3_completed_at = Column(DateTime, nullable=True)
    step4_completed_at = Column(DateTime, nullable=True)
    step5_completed_at = Column(DateTime, nullable=True)
    step6_completed_at = Column(DateTime, nullable=True)

    # 최종 완료
    fully_completed = Column(Boolean, default=False)
    fully_completed_at = Column(DateTime, nullable=True)

    # 이탈 추적
    last_step_reached = Column(Integer, default=0)  # 0~6
    abandoned = Column(Boolean, default=False)
    abandoned_at = Column(DateTime, nullable=True)
```

### 진행 상태 조회 API

```python
GET /api/v1/onboarding/progress

Response:
{
  "success": true,
  "data": {
    "current_step": 3,
    "steps": {
      "step0": { "completed": true, "completed_at": "2026-03-04T09:00:00Z" },
      "step1": { "completed": true, "completed_at": "2026-03-04T09:02:00Z" },
      "step2": { "completed": true, "completed_at": "2026-03-04T09:05:00Z" },
      "step3": { "completed": false, "in_progress": true },
      "step4": { "completed": false },
      "step5": { "completed": false },
      "step6": { "completed": false }
    },
    "completion_percentage": 50,
    "fully_completed": false
  },
  "count": 0
}
```

### 대시보드 진행 바

```
온보딩 진행도: ████████░░░░░░░░░░ 50%

[✅ 계정 생성 (2분)]
   ↓
[✅ 위험고지 (3분)]
   ↓
[⏳ 브릿지 설치 (5분)] ← 현재
   ↓
[ ] API 키 설정 (10분)
   ↓
[ ] 연결 테스트 (2분)
   ↓
[ ] 첫 전략 (5분)
```

---

## 5. 이탈 처리 (나중에 계속하기)

### 시나리오

사용자가 중간에 온보딩을 중단하고 "나중에 계속하기"를 선택한 경우.

### 구현

#### 1. "나중에" 버튼 (모든 단계에 존재)
```typescript
const handleContinueLater = async () => {
  // 현재 진행도만 저장 (완료로 표시 안 함)
  await api.post('/api/v1/onboarding/save-progress', {
    current_step: currentStep
  });

  // 메인 대시보드로 이동
  navigate('/dashboard');
};
```

#### 2. 다시 들어왔을 때
```python
# GET /api/v1/onboarding/resume
def get_resume_data(user_id):
    progress = OnboardingProgress.query.filter_by(user_id=user_id).first()

    if progress.fully_completed:
        return {
            "status": "completed",
            "redirect": "/dashboard"
        }

    current_step = progress.last_step_reached
    return {
        "status": "in_progress",
        "resume_step": current_step,
        "redirect": f"/onboarding/step{current_step}"
    }
```

#### 3. 장기 미완료 사용자 리텔게팅
```python
# 7일 이상 미완료 사용자에게 이메일/푸시
def send_onboarding_reminder(user_id):
    progress = OnboardingProgress.query.filter_by(user_id=user_id).first()

    if not progress.fully_completed and \
       progress.abandoned_at is None and \
       (datetime.utcnow() - progress.step1_completed_at).days >= 7:

        send_email(
            to=user.email,
            subject="StockVision 온보딩을 완료하세요!",
            body=f"Step {progress.last_step_reached}부터 계속하세요: https://..."
        )
```

---

## 6. 기술 요구사항

### 6.1 백엔드 (FastAPI)

#### 엔드포인트 목록

| Method | Path | 설명 | Auth |
|--------|------|------|------|
| GET | `/api/v1/onboarding/progress` | 진행도 조회 | Optional |
| GET | `/api/v1/onboarding/env-check` | 환경 사전 검사 | No |
| POST | `/api/v1/auth/magic-link` | 매직 링크 발송 | No |
| GET | `/api/v1/auth/verify` | 매직 링크 검증 | No |
| POST | `/api/v1/auth/anonymous` | 무계정 UUID | No |
| PUT | `/api/v1/onboarding/step2-agree` | 위험고지 수락 | Yes |
| POST | `/api/v1/onboarding/bridge-health` | 브릿지 상태 | Yes |
| POST | `/api/v1/onboarding/step4-config-init` | API 설정 초기화 | Yes |
| POST | `/api/v1/onboarding/test-connection` | 연결 테스트 | Yes |
| POST | `/api/v1/onboarding/save-progress` | 진행도 저장 | Yes |
| GET | `/api/v1/onboarding/resume` | 재개 데이터 | Yes |

#### 모델/서비스
```python
# models/onboarding.py
class OnboardingProgress(Base):
    # 위 참고

# services/onboarding_service.py
class OnboardingService:
    def check_environment() -> dict
    def start_step(user_id: int, step: int) -> dict
    def complete_step(user_id: int, step: int) -> dict
    def test_connection(user_id: int, bridge_id: str) -> dict
    def send_reminder_email(user_id: int) -> bool
```

### 6.2 프론트엔드 (React/TypeScript)

#### 페이지 구조
```
src/pages/Onboarding/
├── OnboardingLayout.tsx       # 전체 레이아웃 + 진행 바
├── Step0.tsx                  # 환경 체크
├── Step1.tsx                  # 계정 생성/로그인
├── Step2.tsx                  # 위험고지
├── Step3.tsx                  # 브릿지 설치
├── Step4.tsx                  # API 키 설정
├── Step5.tsx                  # 연결 테스트
├── Step6.tsx                  # 첫 전략
└── OnboardingComplete.tsx      # 완료 화면

src/components/
├── OnboardingProgress.tsx      # 진행도 표시
├── StepNavigation.tsx          # 이전/다음/나중에
└── HealthCheck.tsx             # 상태 체크 스피너
```

#### 타입 정의
```typescript
// types/onboarding.ts
export interface OnboardingStep {
  step: number;
  name: string;
  description: string;
  estimatedTime: number;  // 분 단위
  optional: boolean;
}

export interface OnboardingProgress {
  current_step: number;
  steps: Record<string, StepStatus>;
  completion_percentage: number;
  fully_completed: boolean;
}

export interface StepStatus {
  completed: boolean;
  completed_at?: string;
  in_progress?: boolean;
}
```

### 6.3 로컬 브릿지

#### 설치 감지 API
```python
# bridge/health.py
def get_health() -> dict:
    return {
        "status": "running",
        "version": "1.0.0",
        "uptime_seconds": 12345,
        "bridge_id": "uuid-xxx",
        "last_signal": "2026-03-04T10:05:00Z",
        "connections": {
            "kiwoom": True,
            "stockvision_server": True
        }
    }
```

---

## 7. 미결 사항

### 7.1 기술 결정 필요

- [ ] 브릿지 배포 방식 (exe vs pip vs 클라우드)
- [ ] 암호화 방식 (XChaCha20 vs AES-256-GCM)
- [ ] 자동 설치 스크립트 구현 (PowerShell vs Python)
- [ ] GUI vs CLI 온보딩 인터페이스

### 7.2 추가 기능 (Phase 4)

- [ ] 다국어 지원 (영어, 일본어, 중국어)
- [ ] 모바일 앱 온보딩
- [ ] 라이브 채팅 지원 (실시간 도움)
- [ ] 비디오 튜토리얼

### 7.3 메트릭 추적

- [ ] 이탈률 (어느 단계에서 포기?)
- [ ] 완료 시간 (단계별 평균)
- [ ] 재시도율 (실패 후 다시 시도)
- [ ] 성공률 (완료한 사용자 %)

---

## 체크리스트 (MVP 구현)

- [ ] 백엔드: OnboardingProgress 모델 + 서비스 로직
- [ ] 백엔드: 모든 엔드포인트 구현 및 테스트
- [ ] 프론트엔드: Step 0~2 UI + 로직 (계정, 위험고지)
- [ ] 프론트엔드: Step 3~5 UI + 로직 (브릿지, API, 테스트)
- [ ] 프론트엔드: Step 6 UI + 로직 (전략 선택)
- [ ] 프론트엔드: 진행도 바 + 나중에 계속하기
- [ ] 로컬 브릿지: 헬스체크 API
- [ ] E2E 테스트 (처음부터 끝까지)
- [ ] 사용자 문서 (온보딩 가이드)

---

**마지막 갱신**: 2026-03-04
**상태**: 초안 검토 대기
