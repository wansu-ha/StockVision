/** 서비스 키 관리 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { adminApi } from '../../services/admin'

interface ServiceKey {
  id: number
  source: string
  key_preview: string
  description: string
  status: string
  last_verified: string
}

export default function AdminServiceKeys() {
  const queryClient = useQueryClient()
  const [source, setSource] = useState('Kiwoom')
  const [apiKey, setApiKey] = useState('')
  const [description, setDescription] = useState('')

  const { data: keys = [] } = useQuery<ServiceKey[]>({
    queryKey: ['admin', 'service-keys'],
    queryFn: () => adminApi.getServiceKeys().then((r: { data: { data: ServiceKey[] } }) => r.data.data ?? r.data ?? []),
  })

  const createMutation = useMutation({
    mutationFn: () => adminApi.createServiceKey({ source, key: apiKey, description }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'service-keys'] })
      setApiKey('')
      setDescription('')
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
          <select value={source} onChange={(e) => setSource(e.target.value)} className="px-3 py-2 border border-gray-200 rounded-lg text-sm">
            <option value="Kiwoom">Kiwoom</option>
            <option value="KOSCOM">KOSCOM</option>
            <option value="yfinance">yfinance</option>
          </select>
          <input type="password" placeholder="API Key" value={apiKey} onChange={(e) => setApiKey(e.target.value)} className="flex-1 px-3 py-2 border border-gray-200 rounded-lg text-sm" />
          <input type="text" placeholder="설명 (선택)" value={description} onChange={(e) => setDescription(e.target.value)} className="w-48 px-3 py-2 border border-gray-200 rounded-lg text-sm" />
          <button onClick={() => createMutation.mutate()} disabled={!apiKey} className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50">등록</button>
        </div>
      </div>

      {/* 키 목록 */}
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-gray-500">
            <th className="text-left py-2 px-3">소스</th>
            <th className="text-left py-2 px-3">키 (마스킹)</th>
            <th className="text-left py-2 px-3">설명</th>
            <th className="text-center py-2 px-3">상태</th>
            <th className="text-center py-2 px-3">액션</th>
          </tr>
        </thead>
        <tbody>
          {(Array.isArray(keys) ? keys : []).map((k) => (
            <tr key={k.id} className="border-b border-gray-50">
              <td className="py-2 px-3 font-medium">{k.source}</td>
              <td className="py-2 px-3 font-mono text-gray-400">{k.key_preview}</td>
              <td className="py-2 px-3">{k.description}</td>
              <td className="py-2 px-3 text-center">{k.status}</td>
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
