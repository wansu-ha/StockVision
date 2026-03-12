/**
 * 로컬/원격 모드 감지.
 *
 * localhost:4020/health 시도 → 성공이면 로컬 모드, 실패+JWT이면 원격 모드.
 */
import { useState, useEffect } from 'react'

const LOCAL_URL = import.meta.env.VITE_LOCAL_API_URL || 'http://localhost:4020'

export function useRemoteMode() {
  const [isRemote, setIsRemote] = useState(false)
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    const check = async () => {
      try {
        const resp = await fetch(`${LOCAL_URL}/health`, { signal: AbortSignal.timeout(3000) })
        if (resp.ok) {
          setIsRemote(false)
        } else {
          setIsRemote(!!sessionStorage.getItem('sv_jwt'))
        }
      } catch {
        // 로컬 서버 접근 불가
        setIsRemote(!!sessionStorage.getItem('sv_jwt'))
      } finally {
        setChecking(false)
      }
    }
    check()
  }, [])

  return { isRemote, checking }
}
