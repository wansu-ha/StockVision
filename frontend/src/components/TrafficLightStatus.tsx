/** 신호등 3개: 클라우드, 로컬, 키움 상태 표시 */
import { useState, useEffect, useRef } from 'react'
import { cloudHealth } from '../services/cloudClient'
import { localStatus, localHealth } from '../services/localClient'
import type { ServerStatus, TrafficLightColor } from '../types/ui'
import { useAlertStore } from '../stores/alertStore'

const colorMap: Record<TrafficLightColor, string> = {
  green: 'bg-green-400',
  yellow: 'bg-yellow-400',
  red: 'bg-red-400',
}

const labelMap: Record<string, string> = {
  cloud: '클라우드',
  local: '로컬',
  kiwoom: '키움',
}

export default function TrafficLightStatus() {
  const [status, setStatus] = useState<ServerStatus>({
    cloud: 'yellow',
    local: 'yellow',
    kiwoom: 'yellow',
  })
  const prevRef = useRef<ServerStatus>(status)
  const localVersionRef = useRef<string | null>(null)
  const addAlert = useAlertStore((s) => s.add)

  useEffect(() => {
    let mounted = true

    async function poll() {
      const cloudOk = await cloudHealth.check()
      const localRes = await localStatus.get()
      const localHp = await localHealth.check()

      if (!mounted) return

      // 로컬 서버 버전 변경 감지 → 자동 새로고침
      if (localHp?.version) {
        if (localVersionRef.current && localVersionRef.current !== localHp.version) {
          addAlert('로컬 서버가 업데이트되었습니다. 새로고침합니다.', 'info')
          setTimeout(() => window.location.reload(), 1500)
          return
        }
        localVersionRef.current = localHp.version
      }

      const next: ServerStatus = {
        cloud: cloudOk ? 'green' : 'red',
        local: localRes ? 'green' : 'red',
        kiwoom: localRes?.data?.kiwoom_connected ? 'green' : 'red',
        cloud_message: cloudOk ? '정상' : '연결 불가',
        local_message: localRes ? '정상' : '연결 불가',
        kiwoom_message: localRes?.data?.kiwoom_connected ? '연결됨' : '미연결',
      }

      // 상태 변화 감지 → 알림
      const prev = prevRef.current
      for (const key of ['cloud', 'local', 'kiwoom'] as const) {
        if (prev[key] !== next[key]) {
          const label = labelMap[key]
          if (next[key] === 'green') addAlert(`${label} 서버 연결됨`, 'success')
          else if (next[key] === 'red') addAlert(`${label} 서버 연결 끊김`, 'error')
        }
      }

      prevRef.current = next
      setStatus(next)
    }

    poll()
    const timer = setInterval(poll, 5000)
    return () => { mounted = false; clearInterval(timer) }
  }, [addAlert])

  return (
    <div className="flex items-center gap-3">
      {(['cloud', 'local', 'kiwoom'] as const).map((key) => (
        <div key={key} className="relative group flex items-center gap-1.5" title={`${labelMap[key]}: ${status[`${key}_message` as keyof ServerStatus] ?? ''}`}>
          <div className={`w-3 h-3 rounded-full ${colorMap[status[key]]} shadow-sm`} />
          <span className="text-xs text-gray-500 hidden sm:inline">{labelMap[key]}</span>
          {/* 호버 툴팁 */}
          <div className="absolute top-full left-1/2 -translate-x-1/2 mt-1 px-2 py-1 bg-gray-800 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-50">
            {status[`${key}_message` as keyof ServerStatus] ?? '확인 중'}
          </div>
        </div>
      ))}
    </div>
  )
}
