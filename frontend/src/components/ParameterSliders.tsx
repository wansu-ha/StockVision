import { parseDslV2 } from '../utils/dslParserV2'

interface Props {
  script: string
  onChange: (newScript: string) => void
}

export default function ParameterSliders({ script, onChange }: Props) {
  const { constants } = parseDslV2(script)

  if (constants.length === 0) return null

  const handleChange = (name: string, newValue: number | string) => {
    const lines = script.split('\n')
    const updated = lines.map(line => {
      const trimmed = line.replace(/--.*$/, '').trim()
      const match = trimmed.match(/^(\S+)\s*=\s*/)
      if (match && match[1] === name && !trimmed.includes('→') && !trimmed.includes('->')) {
        if (typeof newValue === 'string') {
          return `${name} = "${newValue}"`
        }
        return `${name} = ${newValue}`
      }
      return line
    })
    onChange(updated.join('\n'))
  }

  return (
    <div className="space-y-3 p-3 bg-gray-800 border border-gray-700 rounded-lg">
      <div className="text-xs font-semibold text-gray-400">파라미터 조정</div>
      {constants.map(c => (
        <div key={c.name} className="flex items-center gap-3">
          <span className="text-sm font-mono w-20 shrink-0 text-gray-300">{c.name}</span>
          {c.type === 'number' ? (
            <div className="flex items-center gap-2 flex-1">
              <input
                type="range"
                min={typeof c.value === 'number' && c.value < 0 ? c.value * 3 : 1}
                max={typeof c.value === 'number' ? Math.max(c.value * 3, 100) : 100}
                step={typeof c.value === 'number' && !Number.isInteger(c.value) ? 0.1 : 1}
                value={Number(c.value)}
                onChange={e => handleChange(c.name, parseFloat(e.target.value))}
                className="flex-1 accent-indigo-500"
              />
              <input
                type="number"
                value={Number(c.value)}
                onChange={e => handleChange(c.name, parseFloat(e.target.value) || 0)}
                className="w-16 text-sm text-center bg-gray-900 border border-gray-600 rounded px-1 py-0.5 text-gray-100 focus:outline-none focus:border-indigo-500"
              />
            </div>
          ) : (
            <input
              type="text"
              value={String(c.value)}
              onChange={e => handleChange(c.name, e.target.value)}
              className="flex-1 text-sm bg-gray-900 border border-gray-600 rounded px-2 py-0.5 text-gray-100 focus:outline-none focus:border-indigo-500"
            />
          )}
        </div>
      ))}
    </div>
  )
}
