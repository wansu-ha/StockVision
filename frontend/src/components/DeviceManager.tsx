/**
 * 디바이스 관리 — Settings 페이지에 포함.
 *
 * 디바이스 목록, 새 디바이스 추가 (QR), 해제.
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { cloudDevices, type DeviceInfo } from '../services/cloudClient'

export default function DeviceManager() {
  const queryClient = useQueryClient()
  const [showPairing, setShowPairing] = useState(false)
  const [pairingData, setPairingData] = useState<{ device_id: string; key: string; qr_data: string } | null>(null)

  const { data: devices = [], isLoading } = useQuery({
    queryKey: ['devices'],
    queryFn: cloudDevices.list,
  })

  const deactivateMutation = useMutation({
    mutationFn: (deviceId: string) => cloudDevices.deactivate(deviceId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['devices'] }),
  })

  const handlePairInit = async () => {
    try {
      const LOCAL_URL = import.meta.env.VITE_LOCAL_API_URL || 'http://localhost:4020'
      const resp = await fetch(`${LOCAL_URL}/api/devices/pair/init`, { method: 'POST' })
      const result = await resp.json()
      if (result.success) {
        setPairingData(result.data)
        setShowPairing(true)
      }
    } catch {
      alert('페어링을 시작할 수 없습니다. 로컬 서버가 실행 중인지 확인하세요.')
    }
  }

  const handlePairComplete = async () => {
    if (!pairingData) return
    try {
      const LOCAL_URL = import.meta.env.VITE_LOCAL_API_URL || 'http://localhost:4020'
      await fetch(`${LOCAL_URL}/api/devices/pair/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          device_id: pairingData.device_id,
          name: navigator.userAgent.slice(0, 50),
          platform: 'web',
        }),
      })
      setShowPairing(false)
      setPairingData(null)
      queryClient.invalidateQueries({ queryKey: ['devices'] })
    } catch {
      alert('페어링 완료에 실패했습니다.')
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-medium text-gray-200">연결된 디바이스</h3>
        <button
          onClick={handlePairInit}
          className="px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
        >
          새 디바이스 추가
        </button>
      </div>

      {isLoading ? (
        <p className="text-gray-400 text-sm">로딩 중...</p>
      ) : devices.length === 0 ? (
        <p className="text-gray-400 text-sm">등록된 디바이스가 없습니다.</p>
      ) : (
        <div className="space-y-2">
          {devices.map((d: DeviceInfo) => (
            <div key={d.id} className="flex items-center justify-between p-3 bg-gray-700/50 rounded-lg">
              <div>
                <p className="text-gray-200 text-sm font-medium">{d.name || d.id}</p>
                <p className="text-gray-400 text-xs">
                  {d.platform} · 등록: {d.registered_at ? new Date(d.registered_at).toLocaleDateString() : '-'}
                  {d.last_seen_at && ` · 마지막 접속: ${new Date(d.last_seen_at).toLocaleDateString()}`}
                </p>
              </div>
              <button
                onClick={() => deactivateMutation.mutate(d.id)}
                className="px-2 py-1 text-xs text-red-400 hover:text-red-300 hover:bg-red-900/30 rounded transition-colors"
              >
                해제
              </button>
            </div>
          ))}
        </div>
      )}

      {/* 페어링 다이얼로그 */}
      {showPairing && pairingData && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-xl p-6 max-w-sm w-full mx-4 space-y-4">
            <h4 className="text-lg font-medium text-gray-200">새 디바이스 페어링</h4>
            <p className="text-sm text-gray-400">
              원격 디바이스에서 아래 키를 입력하세요.
            </p>
            <div className="p-3 bg-gray-900 rounded-lg">
              <p className="text-xs text-gray-400 mb-1">디바이스 ID</p>
              <p className="text-sm font-mono text-gray-200">{pairingData.device_id}</p>
            </div>
            <div className="p-3 bg-gray-900 rounded-lg">
              <p className="text-xs text-gray-400 mb-1">암호화 키</p>
              <p className="text-xs font-mono text-gray-200 break-all">{pairingData.key}</p>
              <button
                onClick={() => navigator.clipboard.writeText(pairingData.key)}
                className="mt-2 text-xs text-blue-400 hover:text-blue-300"
              >
                복사
              </button>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => { setShowPairing(false); setPairingData(null) }}
                className="flex-1 px-3 py-2 text-sm bg-gray-700 hover:bg-gray-600 rounded-lg"
              >
                취소
              </button>
              <button
                onClick={handlePairComplete}
                className="flex-1 px-3 py-2 text-sm bg-blue-600 hover:bg-blue-700 rounded-lg"
              >
                페어링 완료
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
