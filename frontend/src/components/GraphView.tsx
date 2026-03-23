import { useEffect, useRef, useCallback, useState } from 'react'
import ForceGraph2D from 'react-force-graph-2d'
import type { GraphData, GraphNode } from '../types'

export const NODE_COLORS: Record<string, string> = {
  SalesOrder:       '#3B82F6',
  SalesOrderItem:   '#93C5FD',
  OutboundDelivery: '#10B981',
  DeliveryItem:     '#6EE7B7',
  BillingDocument:  '#F59E0B',
  BillingItem:      '#FCD34D',
  JournalEntry:     '#8B5CF6',
  Payment:          '#EC4899',
  BusinessPartner:  '#06B6D4',
  Customer:         '#67E8F9',
  Product:          '#EF4444',
  Plant:            '#F97316',
  StorageLocation:  '#84CC16',
}

const DEFAULT_COLOR = '#94A3B8'

interface Props {
  data: GraphData
  onNodeClick: (node: GraphNode) => void
  highlightIds: Set<string>
}

export default function GraphView({ data, onNodeClick, highlightIds }: Props) {
  const fgRef     = useRef<any>(null)
  const [hoveredId, setHoveredId] = useState<string | null>(null)

  // Initial zoom-to-fit on load
  useEffect(() => {
    if (fgRef.current && data.nodes.length > 0) {
      setTimeout(() => fgRef.current?.zoomToFit(800, 60), 1000)
    }
  }, [data.nodes.length])

  // When highlightIds changes — redraw canvas then pan+zoom to highlighted nodes
  useEffect(() => {
    const fg = fgRef.current
    if (!fg) return

    // Trigger canvas redraw immediately so colors/rings update
    fg.refresh?.()

    if (highlightIds.size === 0) return

    // Poll every 80ms until simulation has placed the highlighted nodes (max 2s)
    let attempts = 0

    const tryZoom = (): boolean => {
      const highlighted = (data.nodes as any[]).filter(
        (n: any) => highlightIds.has(n.id) && n.x != null && n.y != null
      )
      if (highlighted.length === 0) return false

      const xs   = highlighted.map((n: any) => n.x as number)
      const ys   = highlighted.map((n: any) => n.y as number)
      const minX = Math.min(...xs)
      const maxX = Math.max(...xs)
      const minY = Math.min(...ys)
      const maxY = Math.max(...ys)
      const cx   = (minX + maxX) / 2
      const cy   = (minY + maxY) / 2

      // Width/height of the bounding box — treat single node as 1px box
      const w = Math.max(maxX - minX, 1)
      const h = Math.max(maxY - minY, 1)

      // Container dimensions
      const containerW = (fg.width?.()  as number | undefined) ?? window.innerWidth  * 0.65
      const containerH = (fg.height?.() as number | undefined) ?? window.innerHeight * 0.9

      // Scale so bounding box fills ~65% of the viewport, capped between 1.5× and 6×
      const zoom = Math.min(6, Math.max(1.5, 0.65 * Math.min(containerW / w, containerH / h)))

      // Smooth pan to centre, then zoom after pan starts
      fg.centerAt(cx, cy, 600)
      setTimeout(() => fg.zoom(zoom, 500), 200)

      return true
    }

    const poll = setInterval(() => {
      attempts++
      const done = tryZoom()
      if (done || attempts >= 25) clearInterval(poll)
    }, 80)

    return () => clearInterval(poll)
  }, [highlightIds, data.nodes])

  const paintNode = useCallback((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const isHighlighted = highlightIds.size > 0 && highlightIds.has(node.id)
    const isHovered     = hoveredId === node.id
    const hasFocus      = highlightIds.size > 0
    const baseColor     = NODE_COLORS[node.type as string] ?? DEFAULT_COLOR
    const r             = isHighlighted ? 7 : isHovered ? 5.5 : 4
    const alpha         = hasFocus && !isHighlighted ? 0.15 : 1.0

    ctx.globalAlpha = alpha

    // Outer glow ring for highlighted nodes
    if (isHighlighted) {
      ctx.beginPath()
      ctx.arc(node.x, node.y, r + 4.5, 0, 2 * Math.PI)
      ctx.fillStyle = baseColor + '28'
      ctx.fill()

      ctx.beginPath()
      ctx.arc(node.x, node.y, r + 1.8, 0, 2 * Math.PI)
      ctx.strokeStyle = baseColor
      ctx.lineWidth = 1.5 / globalScale
      ctx.stroke()
    }

    // Main circle
    ctx.beginPath()
    ctx.arc(node.x, node.y, r, 0, 2 * Math.PI)
    ctx.fillStyle = baseColor
    ctx.fill()

    // White border (clean separation between nodes)
    ctx.strokeStyle = 'rgba(255,255,255,0.9)'
    ctx.lineWidth = 0.8 / globalScale
    ctx.stroke()

    ctx.globalAlpha = 1.0

    // Label: always show for highlighted nodes, show for all at high zoom
    if (isHighlighted || globalScale > 2.5) {
      const rawLabel = String(node.label || node.id)
      const label    = rawLabel.length > 16 ? rawLabel.slice(0, 14) + '..' : rawLabel
      const fontSize = Math.max(7, 9 / globalScale)

      ctx.font = `500 ${fontSize}px "DM Sans", sans-serif`
      ctx.textAlign    = 'center'
      ctx.textBaseline = 'top'

      const textY = node.y + r + 2.5 / globalScale
      const tw    = ctx.measureText(label).width

      // White pill background so label is readable on any background
      ctx.fillStyle = 'rgba(255,255,255,0.88)'
      ctx.fillRect(node.x - tw / 2 - 2.5, textY - 1, tw + 5, fontSize + 2)

      ctx.fillStyle = isHighlighted ? '#111827' : '#52586A'
      ctx.fillText(label, node.x, textY)
    }
  }, [highlightIds, hoveredId])

  const getLinkColor = useCallback((link: any) => {
    if (highlightIds.size === 0) return 'rgba(0,0,0,0.07)'
    const s = typeof link.source === 'object' ? link.source.id : link.source
    const t = typeof link.target === 'object' ? link.target.id : link.target
    return (highlightIds.has(s) || highlightIds.has(t))
      ? 'rgba(59,130,246,0.55)'
      : 'rgba(0,0,0,0.03)'
  }, [highlightIds])

  const getLinkWidth = useCallback((link: any) => {
    if (highlightIds.size === 0) return 0.8
    const s = typeof link.source === 'object' ? link.source.id : link.source
    const t = typeof link.target === 'object' ? link.target.id : link.target
    return (highlightIds.has(s) || highlightIds.has(t)) ? 2 : 0.3
  }, [highlightIds])

  return (
    <ForceGraph2D
      ref={fgRef}
      graphData={data}
      nodeCanvasObject={paintNode}
      nodeCanvasObjectMode={() => 'replace'}
      nodeVal={(node) => (highlightIds.has((node as GraphNode).id) ? 7 : 3)}
      linkColor={getLinkColor}
      linkWidth={getLinkWidth}
      linkDirectionalArrowLength={3}
      linkDirectionalArrowRelPos={1}
      linkDirectionalArrowColor={() => 'rgba(0,0,0,0.15)'}
      backgroundColor="#F7F8FA"
      onNodeClick={(node) => onNodeClick(node as GraphNode)}
      onNodeHover={(node) => setHoveredId(node ? (node as GraphNode).id : null)}
      cooldownTicks={150}
      d3AlphaDecay={0.02}
      d3VelocityDecay={0.35}
      warmupTicks={80}
    />
  )
}