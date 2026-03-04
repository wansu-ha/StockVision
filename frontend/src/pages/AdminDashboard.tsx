import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { adminApi } from '../services/admin'

export default function AdminDashboard() {
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { data: stats, isLoading: statsLoading, isError: statsError } = useQuery({
    queryKey: ['admin-stats'],
    queryFn: adminApi.getStats,
    retry: false,
  })

  const { data: usersResp } = useQuery({
    queryKey: ['admin-users'],
    queryFn: () => adminApi.listUsers(1),
    retry: false,
  })

  const { data: templates = [] } = useQuery({
    queryKey: ['admin-templates'],
    queryFn: adminApi.listTemplates,
    retry: false,
  })

  const deactivate = useMutation({
    mutationFn: adminApi.deleteTemplate,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-templates'] }),
  })

  if (statsLoading) return <div className="p-8 text-gray-400 text-sm">불러오는 중...</div>
  if (statsError) return (
    <div className="p-8 text-center">
      <p className="text-red-500 font-medium">관리자 권한이 없거나 인증에 실패했습니다.</p>
      <button onClick={() => navigate('/')} className="mt-3 text-sm text-blue-600 hover:underline">
        홈으로 돌아가기
      </button>
    </div>
  )

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-8">
      <h1 className="text-xl font-bold text-gray-800">관리자 대시보드</h1>

      {/* 통계 카드 */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[
            { label: '총 사용자', value: stats.users.total },
            { label: '최근 7일 신규', value: stats.users.new_7d },
            { label: '온보딩 완료', value: stats.users.onboarding_done },
            { label: '활성 템플릿', value: stats.templates.active },
          ].map(card => (
            <div key={card.label} className="bg-white border border-gray-200 rounded-xl p-4">
              <div className="text-2xl font-bold text-gray-800">{card.value}</div>
              <div className="text-xs text-gray-400 mt-0.5">{card.label}</div>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 사용자 목록 */}
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <div className="px-4 py-3 border-b">
            <span className="text-sm font-semibold text-gray-700">사용자 목록</span>
            {usersResp && <span className="ml-2 text-xs text-gray-400">총 {usersResp.total}명</span>}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-gray-50 text-gray-500">
                  <th className="px-3 py-2 text-left">이메일</th>
                  <th className="px-3 py-2 text-left">역할</th>
                  <th className="px-3 py-2 text-left">가입일</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {(usersResp?.data ?? []).map(u => (
                  <tr key={u.id} className="hover:bg-gray-50">
                    <td className="px-3 py-2 text-gray-700">{u.email}</td>
                    <td className="px-3 py-2">
                      <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                        u.role === 'admin' ? 'bg-purple-100 text-purple-700' : 'bg-gray-100 text-gray-500'
                      }`}>{u.role}</span>
                    </td>
                    <td className="px-3 py-2 text-gray-400">{u.created_at.slice(0, 10)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* 템플릿 관리 */}
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <div className="px-4 py-3 border-b flex justify-between items-center">
            <span className="text-sm font-semibold text-gray-700">전략 템플릿 관리</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-gray-50 text-gray-500">
                  <th className="px-3 py-2 text-left">이름</th>
                  <th className="px-3 py-2 text-left">난이도</th>
                  <th className="px-3 py-2 text-left">상태</th>
                  <th className="px-3 py-2 text-left">액션</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {templates.map(t => (
                  <tr key={t.id} className="hover:bg-gray-50">
                    <td className="px-3 py-2 text-gray-700">{t.name}</td>
                    <td className="px-3 py-2 text-gray-500">{t.difficulty}</td>
                    <td className="px-3 py-2">
                      <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                        t.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-500'
                      }`}>{t.is_active ? '활성' : '비활성'}</span>
                    </td>
                    <td className="px-3 py-2">
                      {t.is_active && (
                        <button
                          onClick={() => deactivate.mutate(t.id)}
                          className="text-red-500 hover:text-red-700 text-xs"
                        >
                          비활성화
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
