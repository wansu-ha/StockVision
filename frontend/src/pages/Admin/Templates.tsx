/** 전략 템플릿 관리 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { adminApi } from '../../services/admin'

interface Template {
  id: number
  name: string
  category: string
  difficulty: string
  usage_count: number
  is_active: boolean
}

export default function AdminTemplates() {
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [formData, setFormData] = useState({ name: '', category: '', difficulty: 'beginner', description: '' })

  const { data: templates = [] } = useQuery<Template[]>({
    queryKey: ['admin', 'templates'],
    queryFn: () => adminApi.getTemplates().then((r: { data: { data: Template[] } }) => r.data.data ?? r.data ?? []),
  })

  const createMutation = useMutation({
    mutationFn: () => adminApi.createTemplate(formData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'templates'] })
      setShowForm(false)
      setFormData({ name: '', category: '', difficulty: 'beginner', description: '' })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => adminApi.deleteTemplate(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin', 'templates'] }),
  })

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">템플릿 관리</h1>
        <button onClick={() => setShowForm(!showForm)} className="px-4 py-2 bg-indigo-600 text-white rounded-xl text-sm font-medium hover:bg-indigo-700">
          {showForm ? '취소' : '+ 새 템플릿'}
        </button>
      </div>

      {showForm && (
        <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6 space-y-3">
          <input type="text" placeholder="이름" value={formData.name} onChange={(e) => setFormData({ ...formData, name: e.target.value })} className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm" />
          <input type="text" placeholder="카테고리" value={formData.category} onChange={(e) => setFormData({ ...formData, category: e.target.value })} className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm" />
          <select value={formData.difficulty} onChange={(e) => setFormData({ ...formData, difficulty: e.target.value })} className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm">
            <option value="beginner">초급</option>
            <option value="intermediate">중급</option>
            <option value="advanced">고급</option>
          </select>
          <textarea placeholder="설명" value={formData.description} onChange={(e) => setFormData({ ...formData, description: e.target.value })} className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm" rows={3} />
          <button onClick={() => createMutation.mutate()} disabled={!formData.name} className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium disabled:opacity-50">저장</button>
        </div>
      )}

      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-gray-500">
            <th className="text-left py-2 px-3">이름</th>
            <th className="text-left py-2 px-3">카테고리</th>
            <th className="text-left py-2 px-3">난이도</th>
            <th className="text-right py-2 px-3">사용 수</th>
            <th className="text-center py-2 px-3">액션</th>
          </tr>
        </thead>
        <tbody>
          {(Array.isArray(templates) ? templates : []).map((t) => (
            <tr key={t.id} className="border-b border-gray-50 hover:bg-gray-50">
              <td className="py-2 px-3 font-medium">{t.name}</td>
              <td className="py-2 px-3">{t.category}</td>
              <td className="py-2 px-3">{t.difficulty}</td>
              <td className="py-2 px-3 text-right">{t.usage_count}</td>
              <td className="py-2 px-3 text-center">
                <button onClick={() => { if (confirm('삭제하시겠습니까?')) deleteMutation.mutate(t.id) }} className="text-xs text-red-500 font-medium">삭제</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
