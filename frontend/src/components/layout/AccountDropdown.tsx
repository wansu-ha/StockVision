import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

export default function AccountDropdown() {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const { email, logout } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    if (open) document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  const initial = (email?.[0] ?? 'U').toUpperCase()

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen(!open)}
        className={`w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center font-semibold text-[13px] border-2 transition-colors ${
          open ? 'border-indigo-500' : 'border-transparent hover:border-indigo-500'
        }`}
      >
        {initial}
      </button>

      {open && (
        <div className="absolute top-10 right-0 w-[250px] bg-gray-800 border border-gray-700 rounded-xl shadow-2xl overflow-hidden z-[70]">
          <div className="p-4 border-b border-gray-700 flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gray-700 flex items-center justify-center font-bold text-base border border-gray-600 shrink-0">
              {initial}
            </div>
            <div className="min-w-0">
              <div className="text-[13px] font-semibold truncate">{email ?? '사용자'}</div>
              <div className="text-[11px] text-gray-500 mt-0.5">Free Plan</div>
            </div>
          </div>
          <div className="py-1">
            <button onClick={() => { navigate('/settings'); setOpen(false) }} className="w-full text-left px-4 py-2.5 text-[13px] text-gray-300 hover:bg-gray-700 transition-colors">설정</button>
          </div>
          <div className="border-t border-gray-700">
            <button onClick={() => { logout(); setOpen(false) }} className="w-full text-left px-4 py-2.5 text-[13px] text-red-400 hover:bg-gray-700 transition-colors">로그아웃</button>
          </div>
        </div>
      )}
    </div>
  )
}
