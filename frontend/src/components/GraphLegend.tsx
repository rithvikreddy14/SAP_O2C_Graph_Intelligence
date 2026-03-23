import { NODE_COLORS } from './GraphView'

interface Props {
  counts: Record<string, number>
}

export default function GraphLegend({ counts }: Props) {
  const types = Object.entries(counts).sort((a, b) => b[1] - a[1])
  if (types.length === 0) return null

  return (
    <div className="legend">
      <div className="legend-title">Node types</div>
      {types.map(([type, count]) => (
        <div key={type} className="legend-row">
          <span className="legend-dot" style={{ background: NODE_COLORS[type] ?? '#94A3B8' }} />
          <span className="legend-label">{type}</span>
          <span className="legend-count">{count}</span>
        </div>
      ))}
    </div>
  )
}