import { useEffect, useState, useRef } from 'react'
import { X, Loader2 } from 'lucide-react'
import { fetchNode } from '../api'
import { NODE_COLORS } from './GraphView'
import type { GraphNode, NodeDetail as NodeDetailType } from '../types'

const SKIP = new Set(['id','type','label','__indexColor','index','x','y','vx','vy','__val','__color','fx','fy'])

interface Props {
  node: GraphNode
  onClose: () => void
  onNavigate: (node: GraphNode) => void
  position?: { x: number; y: number }
}

export default function NodeDetail({ node, onClose, onNavigate, position }: Props) {
  const [detail, setDetail] = useState<NodeDetailType | null>(null)
  const [loading, setLoading] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    setDetail(null)
    setLoading(true)
    fetchNode(node.id)
      .then(setDetail)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [node.id])

  const color = NODE_COLORS[node.type] ?? '#94A3B8'
  const props = Object.entries(node).filter(([k]) => !SKIP.has(k))
  const connCount = detail?.neighbors.length ?? 0

  // Calculate max visible props (show first 10, note the rest)
  const visibleProps = props.slice(0, 12)
  const hiddenCount  = props.length - visibleProps.length

  // Position popup — default top-left area, but offset from click if available
  const style: React.CSSProperties = {
    top:  position ? Math.min(position.y, window.innerHeight - 420) : 80,
    left: position ? Math.min(position.x + 20, window.innerWidth  - 300) : 190,
  }

  return (
    <div className="node-popup" style={style} ref={ref}>
      <div className="node-popup-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{
            width: 10, height: 10, borderRadius: '50%',
            background: color, display: 'inline-block', flexShrink: 0
          }} />
          <span className="node-popup-type">{node.type}</span>
        </div>
        <button className="icon-btn" onClick={onClose}><X size={14} /></button>
      </div>

      <div className="node-popup-body">
        {visibleProps.map(([k, v]) => (
          <div key={k} className="popup-prop">
            <span className="popup-key">{k}:</span>
            <span className="popup-val">{String(v ?? '—')}</span>
          </div>
        ))}
        {hiddenCount > 0 && (
          <p className="popup-hidden-note">+{hiddenCount} more fields hidden for readability</p>
        )}

        {/* Connections */}
        <div className="popup-connections">
          <div className="popup-conn-title">
            Connections: {loading ? '…' : connCount}
          </div>
          {loading && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--text3)', fontSize: 12 }}>
              <Loader2 size={12} className="spin" /> Loading…
            </div>
          )}
          {detail?.neighbors.slice(0, 8).map(n => (
            <div key={n.id} className="popup-neighbor" onClick={() => onNavigate(n)}>
              <span className="popup-neighbor-dot" style={{ background: NODE_COLORS[n.type] ?? '#94A3B8' }} />
              <span className="popup-neighbor-type">{n.type}</span>
              <span className="popup-neighbor-id">{n.label || n.id}</span>
            </div>
          ))}
          {(detail?.neighbors.length ?? 0) > 8 && (
            <p className="popup-hidden-note">+{detail!.neighbors.length - 8} more connections</p>
          )}
        </div>
      </div>
    </div>
  )
}