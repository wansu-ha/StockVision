/** 온보딩 진행 표시기. */

interface Props {
  currentStep: number
  totalSteps: number
  labels: string[]
}

export default function StepIndicator({ currentStep, totalSteps, labels }: Props) {
  return (
    <div className="flex items-center justify-center gap-1 mb-8">
      {Array.from({ length: totalSteps }, (_, i) => {
        const step = i + 1
        const done = step < currentStep
        const active = step === currentStep
        return (
          <div key={step} className="flex items-center">
            {/* 원 */}
            <div className="flex flex-col items-center">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition ${
                done ? 'bg-green-600 text-white' :
                active ? 'bg-indigo-600 text-white' :
                'bg-gray-800 text-gray-500 border border-gray-700'
              }`}>
                {done ? (
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                  </svg>
                ) : step}
              </div>
              <span className={`text-[10px] mt-1 ${active ? 'text-gray-300' : 'text-gray-600'}`}>
                {labels[i]}
              </span>
            </div>
            {/* 연결선 */}
            {step < totalSteps && (
              <div className={`w-8 sm:w-12 h-0.5 mx-1 ${done ? 'bg-green-600' : 'bg-gray-800'}`} />
            )}
          </div>
        )
      })}
    </div>
  )
}
