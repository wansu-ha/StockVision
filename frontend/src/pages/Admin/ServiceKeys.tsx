/** 서비스 키 관리 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { adminApi } from '../../services/admin'

interface ServiceKey {
  id: number
  api_key: string
  api_secret: string  // 마스킹된 값 ("***")
  app_name: string | null
  is_active: boolean
  created_at: string
  last_used_at: string | null
}

export default function AdminServiceKeys() {
  const queryClient = useQueryClient()
  const [apiKey, setApiKey] = useState('')
  const [apiSecret, setApiSecret] = useState('')
  const [appName, setAppName] = useState('')

  const { data: keys = [] } = useQuery<ServiceKey[]>({
    queryKey: ['admin', 'service-keys'],
    queryFn: () => adminApi.getServiceKeys().then((r: { data: { data: ServiceKey[] } }) => r.data.data ?? r.data ?? []),
    staleTime: 60_000,
  })

  const createMutation = useMutation({
    mutationFn: () => adminApi.createServiceKey({ api_key: apiKey, api_secret: apiSecret, app_name: appName || undefined }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'service-keys'] })
      setApiKey('')
      setApiSecret('')
      setAppName('')
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => adminApi.deleteServiceKey(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin', 'service-keys'] }),
  })

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">서비스 키 관리</h1>

      {/* 등록 폼 */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6 space-y-3">
        <div className="flex gap-3">
          <input type="text" placeholder="API Key" value={apiKey} onChange={(e) => setApiKey(e.target.value)} className="flex-1 px-3 py-2 border border-gray-200 rounded-lg text-sm" />
          <input type="password" placeholder="API Secret" value={apiSecret} onChange={(e) => setApiSecret(e.target.value)} className="flex-1 px-3 py-2 border border-gray-200 rounded-lg text-sm" />
          <input type="text" placeholder="앱 이름 (선택)" value={appName} onChange={(e) => setAppName(e.target.value)} className="w-40 px-3 py-2 border border-gray-200 rounded-lg text-sm" />
          <button onClick={() => createMutation.mutate()} disabled={!apiKey || !apiSecret} className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50">등록</button>
        </div>
      </div>

      {/* 키 목록 */}
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-gray-500">
            <th className="text-left py-2 px-3">API Key</th>
            <th className="text-left py-2 px-3">앱 이름</th>
            <th className="text-center py-2 px-3">상태</th>
            <th className="text-left py-2 px-3">등록일</th>
            <th className="text-left py-2 px-3">마지막 사용</th>
            <th className="text-center py-2 px-3">액션</th>
          </tr>
        </thead>
        <tbody>
          {(Array.isArray(keys) ? keys : []).map((k) => (
            <tr key={k.id} className="border-b border-gray-50">
              <td className="py-2 px-3 font-mono text-gray-700">{k.api_key}</td>
              <td className="py-2 px-3">{k.app_name ?? '-'}</td>
              <td className="py-2 px-3 text-center">
                <span className={`inline-block w-2 h-2 rounded-full ${k.is_active ? 'bg-green-400' : 'bg-gray-400'}`} />
              </td>
              <td className="py-2 px-3 text-gray-400">{new Date(k.created_at).toLocaleDateString('ko-KR')}</td>
              <td className="py-2 px-3 text-gray-400">{k.last_used_at ? new Date(k.last_used_at).toLocaleDateString('ko-KR') : '-'}</td>
              <td className="py-2 px-3 text-center">
                <button
                  onClick={() => { if (confirm('삭제하시겠습니까?')) deleteMutation.mutate(k.id) }}
                  className="text-xs text-red-500 font-medium"
                >
                  삭제
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
