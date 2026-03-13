/**
 * OAuth2 소셜 로그인 버튼 — Google / Kakao.
 */
import { useState } from 'react'
import { cloudOAuth } from '../services/cloudClient'

interface Props {
  onError: (message: string) => void
}

export default function OAuthButtons({ onError }: Props) {
  const [loading, setLoading] = useState<string | null>(null)

  const redirectUri = `${window.location.origin}/oauth/callback`

  const handleGoogle = async () => {
    setLoading('google')
    try {
      const url = await cloudOAuth.getGoogleLoginUrl(redirectUri)
      // 팝업 또는 리다이렉트
      window.location.href = url
    } catch {
      onError('Google 로그인 URL을 가져올 수 없습니다.')
      setLoading(null)
    }
  }

  const handleKakao = async () => {
    setLoading('kakao')
    try {
      const url = await cloudOAuth.getKakaoLoginUrl(redirectUri)
      window.location.href = url
    } catch {
      onError('Kakao 로그인 URL을 가져올 수 없습니다.')
      setLoading(null)
    }
  }

  return (
    <div className="space-y-3">
      <div className="relative my-4">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-gray-600" />
        </div>
        <div className="relative flex justify-center text-sm">
          <span className="bg-gray-800 px-2 text-gray-400">또는</span>
        </div>
      </div>

      <button
        onClick={handleGoogle}
        disabled={loading !== null}
        className="w-full flex items-center justify-center gap-2 px-4 py-2.5 border border-gray-600 rounded-lg hover:bg-gray-700 transition-colors disabled:opacity-50"
      >
        <svg className="w-5 h-5" viewBox="0 0 24 24">
          <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
          <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
          <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
          <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
        </svg>
        <span className="text-gray-200">
          {loading === 'google' ? '연결 중...' : 'Google로 로그인'}
        </span>
      </button>

      <button
        onClick={handleKakao}
        disabled={loading !== null}
        className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-[#FEE500] text-gray-900 rounded-lg hover:bg-[#FDD800] transition-colors disabled:opacity-50"
      >
        <svg className="w-5 h-5" viewBox="0 0 24 24">
          <path fill="#3C1E1E" d="M12 3C6.48 3 2 6.58 2 10.95c0 2.81 1.87 5.28 4.69 6.68l-1.2 4.37 5.07-3.34c.47.05.95.07 1.44.07 5.52 0 10-3.58 10-7.95S17.52 3 12 3z"/>
        </svg>
        <span className="font-medium">
          {loading === 'kakao' ? '연결 중...' : '카카오로 로그인'}
        </span>
      </button>
    </div>
  )
}
