/** 전략 목록 관리 (CRUD, ON/OFF 토글) */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { cloudRules, cloudStocks } from '../services/cloudClient'
import { localRules } from '../services/localClient'
import { useAccountStatus } from '../hooks/useAccountStatus'
import RuleCard from '../components/RuleCard'
import StrategyMonitorCard from '../components/StrategyMonitorCard'
import { useAllConditionStatus } from '../hooks/useConditionStatus'
import type { Rule } from '../types/strategy'
import type { LastRuleResult } from '../types/rule-result'
import { getBacktestHistory, type BacktestSummary } from '../services/backtest'

export default function StrategyList() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [filter, setFilter] = useState('')

  const { data: rules = [], isLoading } = useQuery<Rule[]>({
    queryKey: ['rules'],
    queryFn: cloudRules.list,
    staleTime: 2 * 60_000,
    refetchInterval: 10000,
  })

  const { engineRunning } = useAccountStatus()
  const { data: conditionStatusMap = {} } = useAllConditionStatus()

  // 규칙별 최근 백테스트 요약
  const { data: btMap = new Map<number, BacktestSummary>() } = useQuery<Map<number, BacktestSummary>>({
    queryKey: ['backtestSummaries'],
    queryFn: async () => {
      const items = await getBacktestHistory()
      const map = new Map<number, BacktestSummary>()
      for (const item of items) {
        if (item.rule_id && !map.has(item.rule_id)) {
          map.set(item.rule_id, item.summary)
        }
      }
      return map
    },
    staleTime: 5 * 60_000,
  })

  // 규칙별 최근 실행 결과
  const { data: lastResultsMap = new Map<number, LastRuleResult>() } = useQuery<Map<number, LastRuleResult>>({
    queryKey: ['lastRuleResults'],
    queryFn: async () => {
      const results = await localRules.lastResults()
      const map = new Map<number, LastRuleResult>()
      results.forEach(r => map.set(r.rule_id, r))
      return map
    },
    refetchInterval: 10000,
    staleTime: 5_000,
  })

  // unique symbols → 종목명 맵 (캐시 공유: MainDashboard와 동일 queryKey)
  const sortedSymbolKey = [...new Set(rules.map(r => r.symbol))].sort().join(',')
  const { data: namesMap = new Map<string, string>() } = useQuery<Map<string, string>>({
    queryKey: ['stockNames', sortedSymbolKey],
    queryFn: async ({ queryKey }) => {
      const syms = (queryKey[1] as string).split(',').filter(Boolean)
      const results = await Promise.allSettled(syms.map(sym => cloudStocks.get(sym)))
      const map = new Map<string, string>()
      results.forEach((r, i) => {
        if (r.status === 'fulfilled' && r.value) {
          map.set(syms[i], r.value.name)
        }
      })
      return map
    },
    staleTime: 5 * 60_000,
    enabled: rules.length > 0,
    retry: 1,
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
        <h1 className="text-2xl font-bold text-gray-100">전략 관리</h1>
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
          {filtered.map((rule) =>
            engineRunning && conditionStatusMap[rule.id] ? (
              <StrategyMonitorCard key={rule.id} rule={rule} status={conditionStatusMap[rule.id] ?? null} />
            ) : (
              <RuleCard
                key={rule.id}
                rule={rule}
                symbolName={namesMap.get(rule.symbol)}
                engineRunning={engineRunning}
                lastResult={lastResultsMap.get(rule.id)}
                backtestSummary={btMap.get(rule.id)}
                onToggle={(id, enabled) => toggleMutation.mutate({ id, enabled })}
                onEdit={(id) => navigate(`/strategies/${id}/edit`)}
                onBacktest={(id) => navigate(`/backtest?rule_id=${id}`)}
                onDelete={(id) => {
                  if (confirm('이 전략을 삭제하시겠습니까?')) deleteMutation.mutate(id)
                }}
              />
            )
          )}
        </div>
      )}
    </div>
  )
}
