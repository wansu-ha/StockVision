import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { onboardingApi } from '../services/onboarding'
import RiskDisclosure from '../components/RiskDisclosure'
import BridgeInstaller from '../components/BridgeInstaller'

const STEPS = [
  '계정 생성',
  '위험고지 수락',
  '로컬 브릿지 설치',
  '키움 HTS 로그인',
  '연결 테스트',
  '첫 전략 설정',
]

export default function Onboarding() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [localStep, setLocalStep] = useState(1)

  const { data: status } = useQuery({
    queryKey: ['onboarding-status'],
    queryFn: onboardingApi.getStatus,
  })

  useEffect(() => {
    if (!status) return
    if (status.is_complete) navigate('/')
    else setLocalStep(prev => Math.max(prev, status.step_completed + 1))
  }, [status, navigate])

  const advance = useMutation({
    mutationFn: (n: number) => onboardingApi.completeStep(n),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['onboarding-status'] }),
  })

  const acceptRisk = useMutation({
    mutationFn: onboardingApi.acceptRisk,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['onboarding-status'] })
      setLocalStep(3)
    },
  })

  const currentStep = status ? Math.max(localStep, status.step_completed + 1) : localStep

  const handleBridgeConnected = () => {
    advance.mutate(3, { onSuccess: () => setLocalStep(4) })
  }

  const handleKiwoomNext = () => {
    advance.mutate(4, { onSuccess: () => setLocalStep(5) })
  }

  const handleTestNext = () => {
    advance.mutate(5, { onSuccess: () => setLocalStep(6) })
  }

  const handleFinish = (toStrategy: boolean) => {
    advance.mutate(6, { onSuccess: () => navigate(toStrategy ? '/strategy' : '/') })
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="w-full max-w-lg bg-white rounded-2xl shadow-lg p-8">
        {/* 진행 바 */}
        <div className="mb-8">
          <div className="flex justify-between text-xs text-gray-400 mb-1">
            <span>단계 {currentStep} / {STEPS.length}</span>
            <span>{STEPS[currentStep - 1]}</span>
          </div>
          <div className="h-1.5 bg-gray-100 rounded-full">
            <div
              className="h-1.5 bg-blue-500 rounded-full transition-all"
              style={{ width: `${(currentStep / STEPS.length) * 100}%` }}
            />
          </div>
        </div>

        {/* Step 1: 계정 생성 완료 (이메일 인증 = 자동 완료) */}
        {currentStep === 1 && (
          <div className="space-y-4">
            <h2 className="text-xl font-bold text-gray-800">계정 생성 완료</h2>
            <p className="text-sm text-gray-500">이메일 인증이 완료되었습니다. 다음 단계로 진행하세요.</p>
            <button onClick={() => { advance.mutate(1); setLocalStep(2) }}
              className="w-full py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium">
              다음
            </button>
          </div>
        )}

        {/* Step 2: 위험고지 */}
        {currentStep === 2 && (
          <div className="space-y-4">
            <h2 className="text-xl font-bold text-gray-800">투자 위험 고지</h2>
            <RiskDisclosure onAccept={() => acceptRisk.mutate()} loading={acceptRisk.isPending} />
          </div>
        )}

        {/* Step 3: 브릿지 설치 */}
        {currentStep === 3 && (
          <div className="space-y-4">
            <h2 className="text-xl font-bold text-gray-800">로컬 브릿지 설치</h2>
            <p className="text-sm text-gray-500">StockVision은 키움 API를 사용하기 위해 로컬 브릿지가 필요합니다.</p>
            <BridgeInstaller onConnected={handleBridgeConnected} />
          </div>
        )}

        {/* Step 4: 키움 HTS */}
        {currentStep === 4 && (
          <div className="space-y-4">
            <h2 className="text-xl font-bold text-gray-800">키움 HTS 로그인</h2>
            <p className="text-sm text-gray-500">
              영웅문 HTS에서 직접 로그인해 주세요. StockVision은 사용자의 ID/PW를 저장하지 않습니다.
            </p>
            <a href="https://download.kiwoom.com/web/trader/kiwoom_trader.exe" target="_blank" rel="noreferrer"
              className="inline-flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 text-sm rounded-lg hover:bg-gray-200 transition">
              키움증권 HTS 다운로드
            </a>
            <button onClick={handleKiwoomNext}
              className="w-full py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium">
              로그인 완료 → 다음
            </button>
          </div>
        )}

        {/* Step 5: 연결 테스트 */}
        {currentStep === 5 && (
          <div className="space-y-4">
            <h2 className="text-xl font-bold text-gray-800">연결 테스트</h2>
            <p className="text-sm text-gray-500">키움 연결 상태를 확인합니다.</p>
            <button onClick={handleTestNext}
              className="w-full py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium">
              연결 확인 → 다음
            </button>
          </div>
        )}

        {/* Step 6: 첫 전략 */}
        {currentStep === 6 && (
          <div className="space-y-4">
            <h2 className="text-xl font-bold text-gray-800">첫 전략 만들기 (선택)</h2>
            <p className="text-sm text-gray-500">자동매매 규칙을 지금 바로 설정하거나 나중에 설정할 수 있습니다.</p>
            <div className="flex gap-3">
              <button onClick={() => handleFinish(true)}
                className="flex-1 py-2.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition font-medium text-sm">
                전략 만들기
              </button>
              <button onClick={() => handleFinish(false)}
                className="flex-1 py-2.5 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition font-medium text-sm">
                나중에 하기
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
