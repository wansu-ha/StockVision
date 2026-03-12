/**
 * OAuth 콜백 처리 — /oauth/callback
 *
 * Google/Kakao OAuth2 리다이렉트 후 code를 받아 토큰 교환.
 */
import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { cloudOAuth } from '../services/cloudClient'

export default function OAuthCallback() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [error, setError] = useState('')

  useEffect(() => {
    const code = searchParams.get('code')
    const state = searchParams.get('state') // provider 구분용
    if (!code) {
      setError('인증 코드가 없습니다.')
      return
    }

    const redirectUri = `${window.location.origin}/oauth/callback`
    const provider = state || 'google'

    const exchange = provider === 'kakao'
      ? cloudOAuth.kakaoCallback(code, redirectUri)
      : cloudOAuth.googleCallback(code, redirectUri)

    exchange
      .then((tokens) => {
        sessionStorage.setItem('sv_jwt', tokens.access_token)
        localStorage.setItem('sv_rt', tokens.refresh_token)
        navigate('/', { replace: true })
      })
      .catch(() => {
        setError('로그인에 실패했습니다. 다시 시도해주세요.')
      })
  }, [searchParams, navigate])

  if (error) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-center space-y-4">
          <p className="text-red-400">{error}</p>
          <button
            onClick={() => navigate('/login', { replace: true })}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm"
          >
            로그인으로 돌아가기
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center">
      <p className="text-gray-400 text-sm">로그인 처리 중...</p>
    </div>
  )
}
