import { useEffect, useState, useCallback, useMemo } from 'react'
import { Network, AlertTriangle, Loader2 } from 'lucide-react'
import GraphView from './components/GraphView'
import ChatPanel from './components/ChatPanel'
import NodeDetail from './components/NodeDetail'
import GraphLegend from './components/GraphLegend'
import { fetchGraph } from './api'
import type { GraphData, GraphNode } from './types'
import './styles.css'

type AppState = 'loading' | 'error' | 'ready'

export default function App() {
  const [state, setState]           = useState<AppState>('loading')
  const [graphData, setGraphData]   = useState<GraphData>({ nodes: [], links: [] })
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [clickPos, setClickPos]     = useState<{ x: number; y: number } | undefined>()
  const [highlightIds, setHighlightIds] = useState<Set<string>>(new Set())
  const [chatOpen, setChatOpen]     = useState(true)
  const [errorMsg, setErrorMsg]     = useState('')

  useEffect(() => {
    fetchGraph()
      .then(data => { setGraphData(data); setState('ready') })
      .catch(e   => { setErrorMsg(e.message); setState('error') })
  }, [])

  // Called by ChatPanel with raw DB values → mapped to graph node IDs
  const handleHighlight = useCallback((ids: string[]) => {
    setHighlightIds(new Set(ids))
  }, [])

  // Graph node click — capture mouse position for popup placement
  const handleNodeClick = useCallback((node: GraphNode, event?: MouseEvent) => {
    setSelectedNode(node)
    if (event) {
      setClickPos({ x: event.clientX, y: event.clientY })
    }
  }, [])

  const nodeCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    for (const n of graphData.nodes) {
      counts[n.type] = (counts[n.type] ?? 0) + 1
    }
    return counts
  }, [graphData.nodes])

  return (
    <div className="app">
      {/* Topbar */}
      <header className="topbar">
        <div className="topbar-left">
          <Network size={17} className="logo-icon" />
          <span className="logo-text">O2C<span className="logo-accent">Graph</span></span>
          <span className="topbar-divider" />
          <span className="topbar-sub">SAP Order-to-Cash Intelligence</span>
        </div>
        <div className="topbar-right">
          {state === 'ready' && (
            <>
              <div className="stat-pill">
                <span className="stat-num">{graphData.nodes.length.toLocaleString()}</span>
                <span className="stat-label">nodes</span>
              </div>
              <div className="stat-pill">
                <span className="stat-num">{graphData.links.length.toLocaleString()}</span>
                <span className="stat-label">edges</span>
              </div>
            </>
          )}
          <button
            className={`topbar-btn ${chatOpen ? 'active' : ''}`}
            onClick={() => setChatOpen(o => !o)}
          >
            {chatOpen ? 'Hide chat' : 'Show chat'}
          </button>
        </div>
      </header>

      <div className="workspace">
        {/* Graph canvas */}
        <div className="graph-area">
          {state === 'loading' && (
            <div className="graph-overlay">
              <Loader2 size={28} className="spin" />
              <p>Loading graph…</p>
            </div>
          )}
          {state === 'error' && (
            <div className="graph-overlay error">
              <AlertTriangle size={28} />
              <p>Cannot connect to backend</p>
              <small>{errorMsg}</small>
              <small>Make sure Flask is running on port 5000</small>
            </div>
          )}
          {state === 'ready' && (
            <GraphView
              data={graphData}
              onNodeClick={handleNodeClick}
              highlightIds={highlightIds}
            />
          )}

          {/* Overlays */}
          {state === 'ready' && (
            <>
              <GraphLegend counts={nodeCounts} />

              {highlightIds.size > 0 && (
                <div className="highlight-banner">
                  <span>{highlightIds.size} nodes highlighted from query</span>
                  <button onClick={() => setHighlightIds(new Set())}>Clear</button>
                </div>
              )}
            </>
          )}

          {/* Floating node popup — sits on top of graph, positioned at click */}
          {selectedNode && (
            <NodeDetail
              node={selectedNode}
              onClose={() => setSelectedNode(null)}
              onNavigate={(n) => { setSelectedNode(n); setClickPos(undefined) }}
              position={clickPos}
            />
          )}
        </div>

        {/* Chat panel */}
        {chatOpen && (
          <ChatPanel onHighlight={handleHighlight} />
        )}
      </div>
    </div>
  )
}