import type { StrategyTemplate } from '../services/templates'

interface Props {
  template: StrategyTemplate
  onUse: (template: StrategyTemplate) => void
}

const DIFFICULTY_COLOR: Record<string, string> = {
  '초급': 'bg-green-100 text-green-700',
  '중급': 'bg-yellow-100 text-yellow-700',
  '고급': 'bg-red-100 text-red-700',
}

export default function TemplateCard({ template, onUse }: Props) {
  const bs = template.backtest_summary
  const diffColor = DIFFICULTY_COLOR[template.difficulty ?? ''] ?? 'bg-gray-100 text-gray-600'

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5 flex flex-col gap-3 hover:shadow-md transition">
      <div className="flex items-start justify-between gap-2">
        <h3 className="font-semibold text-gray-800 text-sm leading-snug">{template.name}</h3>
        <span className={`shrink-0 text-xs px-2 py-0.5 rounded-full font-medium ${diffColor}`}>
          {template.difficulty}
        </span>
      </div>

      <p className="text-xs text-gray-500 leading-relaxed line-clamp-2">{template.description}</p>

      {bs && (
        <div className="grid grid-cols-3 gap-1 text-center">
          <div>
            <div className={`text-sm font-bold ${bs.cagr >= 0 ? 'text-green-600' : 'text-red-500'}`}>
              {bs.cagr >= 0 ? '+' : ''}{bs.cagr}%
            </div>
            <div className="text-xs text-gray-400">CAGR</div>
          </div>
          <div>
            <div className="text-sm font-bold text-red-500">{bs.mdd}%</div>
            <div className="text-xs text-gray-400">MDD</div>
          </div>
          <div>
            <div className="text-sm font-bold text-blue-600">{bs.sharpe}</div>
            <div className="text-xs text-gray-400">Sharpe</div>
          </div>
        </div>
      )}

      {template.tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {template.tags.map(tag => (
            <span key={tag} className="text-xs bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">
              {tag}
            </span>
          ))}
        </div>
      )}

      <button
        onClick={() => onUse(template)}
        className="mt-auto w-full py-2 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition font-medium"
      >
        사용하기
      </button>
    </div>
  )
}
