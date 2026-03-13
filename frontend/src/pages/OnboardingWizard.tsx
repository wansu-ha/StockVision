/**
 * OnboardingWizard — 4단계 온보딩 위저드
 * 1. 위험고지 (RiskDisclosure)
 * 2. 로컬 서버 연결 (BridgeInstaller)
 * 3. 증권사 연결 (BrokerKeyForm)
 * 4. 시작 준비 완료 (요약 + 대시보드 이동)
 */
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import StepIndicator from '../components/onboarding/StepIndicator'
import RiskDisclosure from '../components/onboarding/RiskDisclosure'
import BridgeInstaller from '../components/BridgeInstaller'
import BrokerKeyForm from '../components/onboarding/BrokerKeyForm'
import { useOnboarding } from '../hooks/useOnboarding'
import { useAuth } from '../context/AuthContext'
import { useAccountStatus } from '../hooks/useAccountStatus'

const STEP_LABELS = ['위험고지', '로컬 서버', '증권사', '완료']

export default function OnboardingWizard() {
  const [step, setStep] = useState(1)
  const { complete } = useOnboarding()
  const { email, localReady } = useAuth()
  const { brokerConnected, isMock } = useAccountStatus()
  const navigate = useNavigate()

  // 로컬 서버 이미 연결됨 → Step 2 자동 스킵
  useEffect(() => {
    if (step === 2 && localReady) {
      setStep(3)
    }
  }, [step, localReady])

  // 브로커 이미 연결됨 → Step 3 자동 스킵
  useEffect(() => {
    if (step === 3 && brokerConnected) {
      setStep(4)
    }
  }, [step, brokerConnected])

  const handleFinish = () => {
    complete()
    navigate('/', { replace: true })
  }

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex flex-col">
      {/* 헤더 */}
      <header className="bg-gray-900 border-b border-gray-800">
        <div className="max-w-2xl mx-auto h-12 flex items-center px-4">
          <span className="text-lg font-bold text-indigo-400">StockVision</span>
          <span className="ml-2 text-sm text-gray-500">시작하기</span>
        </div>
      </header>

      <main className="flex-1 flex items-start justify-center pt-8 sm:pt-16 px-4">
        <div className="w-full max-w-lg">
          <StepIndicator currentStep={step} totalSteps={4} labels={STEP_LABELS} />

          <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
            {/* Step 1: 위험고지 */}
            {step === 1 && (
              <>
                <h2 className="text-lg font-bold mb-1">시작하기 전에</h2>
                <p className="text-xs text-gray-500 mb-5">StockVision의 동작 원리를 확인하세요.</p>
                <RiskDisclosure onAccept={() => setStep(2)} />
              </>
            )}

            {/* Step 2: 로컬 서버 연결 */}
            {step === 2 && (
              <>
                <h2 className="text-lg font-bold mb-1">로컬 서버 설치</h2>
                <p className="text-xs text-gray-500 mb-5">
                  StockVision 로컬 서버는 주문을 이 PC에서만 실행합니다.
                  비밀번호는 Windows 자격 증명에 안전하게 저장됩니다.
                </p>
                <BridgeInstaller onConnected={() => setStep(3)} />
              </>
            )}

            {/* Step 3: 증권사 연결 */}
            {step === 3 && (
              <>
                <h2 className="text-lg font-bold mb-1">증권사 연결</h2>
                <p className="text-xs text-gray-500 mb-5">
                  증권사 API 키를 등록하여 주문 기능을 활성화하세요.
                </p>
                <BrokerKeyForm onSuccess={() => setStep(4)} showHints />
              </>
            )}

            {/* Step 4: 시작 준비 완료 */}
            {step === 4 && (
              <>
                <h2 className="text-lg font-bold mb-1">준비 완료!</h2>
                <p className="text-xs text-gray-500 mb-5">설정이 완료되었습니다. 대시보드에서 시작하세요.</p>

                <div className="space-y-2 mb-6">
                  <SummaryRow label="계정" value={email ?? '로그인됨'} ok />
                  <SummaryRow
                    label="로컬 서버"
                    value={localReady ? '연결됨' : '미연결'}
                    ok={localReady}
                    onFix={!localReady ? () => setStep(2) : undefined}
                  />
                  <SummaryRow
                    label="증권사"
                    value={brokerConnected
                      ? `연결됨${isMock !== null ? (isMock ? ' (모의)' : ' (실전)') : ''}`
                      : '미연결'}
                    ok={brokerConnected}
                    onFix={!brokerConnected ? () => setStep(3) : undefined}
                  />
                </div>

                <div className="bg-indigo-900/20 border border-indigo-800/50 rounded-lg p-4 text-xs text-indigo-300 mb-6">
                  <p className="font-medium mb-1">다음 단계</p>
                  <ul className="list-disc list-inside space-y-0.5 text-indigo-300/80">
                    <li>대시보드에서 관심 종목을 추가하세요</li>
                    <li>종목을 선택하고 매매 규칙을 설정하세요</li>
                    <li>모의투자로 먼저 테스트하는 것을 권장합니다</li>
                  </ul>
                </div>

                <button
                  onClick={handleFinish}
                  className="w-full py-3 bg-indigo-600 text-white rounded-xl text-sm font-bold hover:bg-indigo-500 transition animate-[fadeIn_0.5s_ease-in-out]"
                >
                  대시보드로 이동
                </button>
              </>
            )}
          </div>

          {/* 건너뛰기 (Step 4가 아닐 때) */}
          {step < 4 && (
            <div className="text-center mt-4">
              <button
                onClick={handleFinish}
                className="text-xs text-gray-600 hover:text-gray-400 transition"
              >
                건너뛰기
              </button>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

function SummaryRow({ label, value, ok, onFix }: { label: string; value: string; ok: boolean; onFix?: () => void }) {
  return (
    <div className="flex items-center justify-between bg-gray-800/50 border border-gray-700 rounded-lg px-4 py-3">
      <span className="text-sm text-gray-400">{label}</span>
      <div className="flex items-center gap-2">
        <span className={`w-2 h-2 rounded-full ${ok ? 'bg-green-400' : 'bg-yellow-400'}`} />
        <span className={`text-sm ${ok ? 'text-gray-200' : 'text-gray-500'}`}>{value}</span>
        {onFix && (
          <button onClick={onFix} className="text-xs text-indigo-400 hover:underline ml-1">
            설정하기
          </button>
        )}
      </div>
    </div>
  )
}
