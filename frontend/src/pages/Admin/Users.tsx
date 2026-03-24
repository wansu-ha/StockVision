/** 유저 관리 페이지 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { adminApi } from '../../services/admin'

interface UserRow {
  id: string
  email: string
  nickname: string
  role: string
  email_verified: boolean
  is_active: boolean
  created_at: string
  last_login_at: string | null
}

export default function AdminUsers() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)

  const { data, isLoading } = useQuery({
    queryKey: ['admin', 'users', page, search],
    queryFn: () => adminApi.getUsers({ page, search }).then((r) => {
      const d = r.data.data ?? r.data
      return { users: d.users ?? (Array.isArray(d) ? d : []), total: d.total ?? 0 }
    }),
    staleTime: 30_000,
  })

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      adminApi.updateUser(id, { is_active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin', 'users'] }),
  })

  const users: UserRow[] = data?.users ?? []
  const totalPages = Math.ceil((data?.total ?? 0) / 20) || 1

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">유저 관리</h1>

      <input
        type="text"
        placeholder="이메일 또는 닉네임 검색..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="w-full max-w-sm px-4 py-2 border border-gray-200 rounded-xl mb-4 text-sm"
      />

      {isLoading ? (
        <div className="text-gray-400 py-8 text-center">로딩 중...</div>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-gray-500">
              <th className="text-left py-2 px-3">이메일</th>
              <th className="text-left py-2 px-3">닉네임</th>
              <th className="text-left py-2 px-3">역할</th>
              <th className="text-center py-2 px-3">인증</th>
              <th className="text-left py-2 px-3">가입일</th>
              <th className="text-left py-2 px-3">마지막 로그인</th>
              <th className="text-center py-2 px-3">상태</th>
              <th className="text-center py-2 px-3">액션</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-b border-gray-50 hover:bg-gray-50">
                <td className="py-2 px-3">{u.email}</td>
                <td className="py-2 px-3">{u.nickname}</td>
                <td className="py-2 px-3">
                  <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                    u.role === 'admin' ? 'bg-purple-100 text-purple-700' : 'bg-gray-100 text-gray-500'
                  }`}>{u.role}</span>
                </td>
                <td className="py-2 px-3 text-center">
                  <span className={`inline-block w-2 h-2 rounded-full ${u.email_verified ? 'bg-blue-400' : 'bg-gray-300'}`} />
                </td>
                <td className="py-2 px-3">{new Date(u.created_at).toLocaleDateString('ko-KR')}</td>
                <td className="py-2 px-3 text-gray-400">
                  {u.last_login_at ? new Date(u.last_login_at).toLocaleDateString('ko-KR') : '-'}
                </td>
                <td className="py-2 px-3 text-center">
                  <span className={`inline-block w-2 h-2 rounded-full ${u.is_active ? 'bg-green-400' : 'bg-gray-400'}`} />
                </td>
                <td className="py-2 px-3 text-center">
                  <button
                    onClick={() => toggleMutation.mutate({ id: u.id, is_active: !u.is_active })}
                    className={`text-xs font-medium ${u.is_active ? 'text-red-500' : 'text-green-600'}`}
                  >
                    {u.is_active ? '비활성화' : '활성화'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <div className="flex gap-2 mt-4 items-center">
        <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1} className="px-3 py-1 bg-gray-100 rounded text-sm disabled:opacity-40">이전</button>
        <span className="px-3 py-1 text-sm text-gray-500">{page} / {totalPages}</span>
        <button onClick={() => setPage((p) => p + 1)} disabled={page >= totalPages} className="px-3 py-1 bg-gray-100 rounded text-sm disabled:opacity-40">다음</button>
      </div>
    </div>
  )
}
