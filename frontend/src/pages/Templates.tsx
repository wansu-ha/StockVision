import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { templatesApi } from '../services/templates'
import type { StrategyTemplate } from '../services/templates'
import TemplateCard from '../components/TemplateCard'

export default function Templates() {
  const navigate = useNavigate()
  const [category, setCategory] = useState('')
  const [difficulty, setDifficulty] = useState('')

  const { data: templates = [], isLoading } = useQuery({
    queryKey: ['templates'],
    queryFn: templatesApi.list,
  })

  const categories = [...new Set(templates.map(t => t.category).filter(Boolean))] as string[]
  const difficulties = [...new Set(templates.map(t => t.difficulty).filter(Boolean))] as string[]

  const filtered = templates.filter(t =>
    (!category || t.category === category) &&
    (!difficulty || t.difficulty === difficulty)
  )

  const handleUse = (template: StrategyTemplate) => {
    navigate('/strategy', { state: { template } })
  }

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-gray-800">전략 템플릿</h1>
        <div className="flex gap-2">
          <select
            value={category}
            onChange={e => setCategory(e.target.value)}
            className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-white"
          >
            <option value="">전체 카테고리</option>
            {categories.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
          <select
            value={difficulty}
            onChange={e => setDifficulty(e.target.value)}
            className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 bg-white"
          >
            <option value="">전체 난이도</option>
            {difficulties.map(d => <option key={d} value={d}>{d}</option>)}
          </select>
        </div>
      </div>

      {isLoading ? (
        <div className="text-center py-12 text-gray-400 text-sm">불러오는 중...</div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-12 text-gray-400 text-sm">템플릿이 없습니다.</div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map(t => (
            <TemplateCard key={t.id} template={t} onUse={handleUse} />
          ))}
        </div>
      )}
    </div>
  )
}
