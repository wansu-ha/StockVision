/** 전략 목록 관리 (CRUD, ON/OFF 토글) */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { cloudRules } from '../services/cloudClient'
import { localRules } from '../services/localClient'
import RuleCard from '../components/RuleCard'
import type { Rule } from '../types/strategy'

export default function StrategyList() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [filter, setFilter] = useState('')

  const { data: rules = [], isLoading } = useQuery<Rule[]>({
    queryKey: ['rules'],
    queryFn: cloudRules.list,
    refetchInterval: 10000,
  })

  const toggleMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: number; enabled: boolean }) =>
      cloudRules.update(id, { is_active: enabled }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules'] })
      // localhost sync
      cloudRules.list().then((r) => localRules.sync(r))
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => cloudRules.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rules'] })
      cloudRules.list().then((r) => localRules.sync(r))
    },
  })

  const filtered = rules.filter((r) =>
    !filter || r.name.includes(filter) || r.symbol.includes(filter),
  )

  return (
    <div className="max-w-5xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">전략 관리</h1>
        <button
          onClick={() => navigate('/strategies/new')}
          className="px-4 py-2 bg-indigo-600 text-white rounded-xl text-sm font-medium hover:bg-indigo-700 transition-colors"
        >
          + 새 전략
        </button>
      </div>

      {/* 필터 */}
      <input
        type="text"
        placeholder="이름 또는 종목 코드로 검색..."
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        className="w-full px-4 py-2 border border-gray-200 rounded-xl mb-6 text-sm"
      />

      {isLoading ? (
        <div className="text-center text-gray-400 py-16">로딩 중...</div>
      ) : filtered.length === 0 ? (
        <div className="text-center text-gray-400 py-16">
          {rules.length === 0 ? '등록된 전략이 없습니다' : '검색 결과 없음'}
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {filtered.map((rule) => (
            <RuleCard
              key={rule.id}
              rule={rule}
              onToggle={(id, enabled) => toggleMutation.mutate({ id, enabled })}
              onEdit={(id) => navigate(`/strategies/${id}/edit`)}
              onDelete={(id) => {
                if (confirm('이 전략을 삭제하시겠습니까?')) deleteMutation.mutate(id)
              }}
            />
          ))}
        </div>
      )}
    </div>
  )
}
