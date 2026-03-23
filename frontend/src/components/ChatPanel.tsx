import { useState, useRef, useEffect, useCallback } from 'react'
import { Send, Sparkles, RotateCcw, ChevronRight } from 'lucide-react'
import { sendChat } from '../api'
import type { Message } from '../types'
import SqlBadge from './SqlBadge'

const SUGGESTED = [
  'Which products appear in the most billing documents?',
  'Trace the full flow for a billing document',
  'Find sales orders delivered but never billed',
  'Top 10 customers by total net order amount',
  'Which plants handle the most deliveries?',
  'Are there billed orders with no delivery?',
]

function genId() { return Math.random().toString(36).slice(2) }

interface Props {
  onHighlight: (ids: string[]) => void
}

export default function ChatPanel({ onHighlight }: Props) {
  const [messages, setMessages] = useState<Message[]>([{
    id: genId(), role: 'assistant', timestamp: new Date(),
    content: 'Hi! I can help you analyze the Order-to-Cash process. Ask me anything about your SAP dataset.',
  }])
  const [input, setInput]   = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSubmit = useCallback(async (question?: string) => {
    const text = (question ?? input).trim()
    if (!text || loading) return

    const userMsg: Message  = { id: genId(), role: 'user', content: text, timestamp: new Date() }
    const loadMsg: Message  = { id: genId(), role: 'assistant', content: '', timestamp: new Date(), loading: true }
    setMessages(m => [...m, userMsg, loadMsg])
    setInput('')
    setLoading(true)

    try {
      const res = await sendChat(text)

      // Highlight only top rows — prevents ranking queries (e.g. "top 3 products")
      // from lighting up every node in the dataset. Single-row lookups are unaffected.
      const TOP_N_HIGHLIGHT = 20
      const rowsForHighlight = (res.rows ?? []).slice(0, TOP_N_HIGHLIGHT)
      const ids = buildHighlightIds(rowsForHighlight)
      if (ids.length > 0) onHighlight(ids)

      setMessages(m => [...m.slice(0, -1), {
        id: genId(), role: 'assistant', content: res.answer,
        sql: res.sql ?? undefined, rows: res.rows ?? undefined,
        timestamp: new Date(),
      }])
    } catch {
      setMessages(m => [...m.slice(0, -1), {
        id: genId(), role: 'error',
        content: 'Request failed. Is the Flask backend running on port 5000?',
        timestamp: new Date(),
      }])
    } finally {
      setLoading(false)
    }
  }, [input, loading, onHighlight])

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit() }
  }

  const clearChat = () => {
    setMessages([{ id: genId(), role: 'assistant', timestamp: new Date(),
      content: 'Chat cleared. Ask me anything about your O2C dataset.' }])
    onHighlight([])
  }

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <div className="chat-header-left">
          <Sparkles size={14} className="sparkle-icon" />
          <span>Graph Intelligence</span>
        </div>
        <button className="icon-btn" onClick={clearChat} title="Clear">
          <RotateCcw size={13} />
        </button>
      </div>

      <div className="messages-list">
        {messages.map(msg => <MessageBubble key={msg.id} msg={msg} />)}
        <div ref={bottomRef} />
      </div>

      {messages.length === 1 && (
        <div className="suggestions">
          <div className="suggestions-label">Try asking</div>
          {SUGGESTED.map(s => (
            <button key={s} className="suggestion-chip" onClick={() => handleSubmit(s)}>
              <ChevronRight size={11} />{s}
            </button>
          ))}
        </div>
      )}

      <div className="chat-input-area">
        <textarea
          className="chat-input"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Ask about orders, deliveries, billing…"
          rows={2}
          disabled={loading}
        />
        <button
          className="send-btn"
          onClick={() => handleSubmit()}
          disabled={!input.trim() || loading}
        >
          <Send size={15} />
        </button>
      </div>
    </div>
  )
}

function MessageBubble({ msg }: { msg: Message }) {
  if (msg.loading) {
    return (
      <div className="message assistant">
        <div className="msg-bubble loading-bubble">
          <span className="dot" /><span className="dot" /><span className="dot" />
        </div>
      </div>
    )
  }
  return (
    <div className={`message ${msg.role}`}>
      <div className="msg-bubble">
        <p className="msg-text">{msg.content}</p>
        {msg.sql && <SqlBadge sql={msg.sql} rowCount={msg.rows?.length} />}
        {msg.rows && msg.rows.length > 0 && msg.rows.length <= 10 && (
          <ResultTable rows={msg.rows} />
        )}
      </div>
      <span className="msg-time">
        {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
      </span>
    </div>
  )
}

function ResultTable({ rows }: { rows: Record<string, unknown>[] }) {
  const cols = Object.keys(rows[0])
  return (
    <div className="result-table-wrap">
      <table className="result-table">
        <thead><tr>{cols.map(c => <th key={c}>{c}</th>)}</tr></thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>{cols.map(c => <td key={c}>{String(row[c] ?? '')}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/**
 * Maps raw DB row values to graph node ID prefixes used in graph_builder.py
 * e.g. salesOrder "1234" → "so_1234"
 */
function buildHighlightIds(rows: Record<string, unknown>[]): string[] {
  const ids = new Set<string>()

  const fieldMap: Array<[string, string]> = [
    ['salesOrder',          'so'],
    ['SalesOrder',          'so'],
    ['billingDocument',     'bill'],
    ['BillingDocument',     'bill'],
    ['deliveryDocument',    'del'],
    ['DeliveryDocument',    'del'],
    ['accountingDocument',  'je'],
    ['AccountingDocument',  'je'],
    ['businessPartner',     'bp'],
    ['BusinessPartner',     'bp'],
    ['product',             'mat'],
    ['material',            'mat'],
    ['Material',            'mat'],
    ['plant',               'plant'],
    ['Plant',               'plant'],
  ]

  for (const row of rows) {
    for (const [field, prefix] of fieldMap) {
      const val = row[field]
      if (val && String(val).trim()) {
        ids.add(`${prefix}_${String(val).trim()}`)
      }
    }
  }

  // Hard cap: never highlight more than 20 nodes regardless of row count
  return [...ids].slice(0, 20)
}