import { Card, CardBody, CardHeader, Chip } from '@heroui/react'
import ConditionStatusRow from './ConditionStatusRow'
import TriggerTimeline from './TriggerTimeline'
import { useConditionStatus } from '../hooks/useConditionStatus'
import type { Rule } from '../types/strategy'

export default function StrategyMonitorCard({ rule }: { rule: Rule }) {
  const { data: status } = useConditionStatus(rule.id)

  return (
    <Card className="w-full">
      <CardHeader className="flex justify-between items-center pb-1">
        <span className="font-semibold text-sm">{rule.name}</span>
        <Chip size="sm" color={rule.is_active ? 'success' : 'default'} variant="flat">
          {rule.is_active ? '실행중' : '중지'}
        </Chip>
      </CardHeader>
      <CardBody className="p-0 pt-0">
        {status?.conditions?.map(c => (
          <ConditionStatusRow key={c.index} condition={c} />
        ))}

        {status?.position && status.position.entry_price > 0 && (
          <div className="px-3 py-2 bg-default-50 text-xs flex flex-wrap gap-x-3 gap-y-0.5">
            <span>진입: {status.position.entry_price.toLocaleString()}원</span>
            <span>최고: {status.position.highest_price.toLocaleString()}원</span>
            <span>보유: {status.position.days_held}일 {status.position.bars_held}봉</span>
          </div>
        )}

        {status?.triggered_history && status.triggered_history.length > 0 && (
          <TriggerTimeline history={status.triggered_history} />
        )}

        {!status && (
          <div className="px-3 py-4 text-xs text-default-400 text-center">
            엔진 미실행 — 조건 상태 없음
          </div>
        )}
      </CardBody>
    </Card>
  )
}
