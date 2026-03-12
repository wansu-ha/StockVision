/**
 * 킬스위치 FAB — 원격 모드에서 긴급 정지 버튼.
 *
 * 모바일: 하단 고정 FAB
 * PC: OpsPanel 내 inline
 */
import { useState } from 'react'

interface Props {
  onKill: (mode: 'stop_new' | 'stop_all') => void
  disabled?: boolean
  inline?: boolean
}

export default function KillSwitchFAB({ onKill, disabled, inline }: Props) {
  const [showConfirm, setShowConfirm] = useState(false)
  const [mode, setMode] = useState<'stop_new' | 'stop_all'>('stop_new')

  const handleConfirm = () => {
    onKill(mode)
    setShowConfirm(false)
  }

  const button = (
    <button
      onClick={() => setShowConfirm(true)}
      disabled={disabled}
      className={`
        bg-red-600 hover:bg-red-700 text-white font-medium rounded-full
        transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg
        ${inline
          ? 'px-4 py-2 text-sm'
          : 'fixed bottom-4 right-4 z-40 w-14 h-14 flex items-center justify-center text-xl md:static md:w-auto md:h-auto md:px-4 md:py-2 md:text-sm md:rounded-lg'
        }
      `}
    >
      {inline ? '긴급 정지' : '⏹'}
    </button>
  )

  return (
    <>
      {button}

      {showConfirm && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-xl p-6 max-w-sm w-full mx-4 space-y-4">
            <h4 className="text-lg font-medium text-red-400">엔진을 정지합니다</h4>
            <div className="space-y-2">
              <label className="flex items-center gap-2 p-3 bg-gray-700/50 rounded-lg cursor-pointer">
                <input
                  type="radio"
                  name="killMode"
                  checked={mode === 'stop_new'}
                  onChange={() => setMode('stop_new')}
                  className="accent-red-500"
                />
                <div>
                  <p className="text-sm text-gray-200">신규 차단</p>
                  <p className="text-xs text-gray-400">새 주문만 차단, 기존 미체결 유지</p>
                </div>
              </label>
              <label className="flex items-center gap-2 p-3 bg-gray-700/50 rounded-lg cursor-pointer">
                <input
                  type="radio"
                  name="killMode"
                  checked={mode === 'stop_all'}
                  onChange={() => setMode('stop_all')}
                  className="accent-red-500"
                />
                <div>
                  <p className="text-sm text-gray-200">전체 정지</p>
                  <p className="text-xs text-gray-400">신규 차단 + 미체결 전량 취소</p>
                </div>
              </label>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setShowConfirm(false)}
                className="flex-1 px-3 py-2 text-sm bg-gray-700 hover:bg-gray-600 rounded-lg"
              >
                취소
              </button>
              <button
                onClick={handleConfirm}
                className="flex-1 px-3 py-2 text-sm bg-red-600 hover:bg-red-700 rounded-lg text-white font-medium"
              >
                정지 실행
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
