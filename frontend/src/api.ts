import type { GraphData, NodeDetail, ChatResponse } from './types'

// Hardcoded to point directly to your live Railway backend
const BASE = 'https://sapo2cgraphintelligence-production.up.railway.app'

export async function fetchGraph(): Promise<GraphData> {
  const res = await fetch(`${BASE}/graph`)
  if (!res.ok) throw new Error('Failed to load graph')
  return res.json()
}

export async function fetchNode(nodeId: string): Promise<NodeDetail> {
  const res = await fetch(`${BASE}/node/${encodeURIComponent(nodeId)}`)
  if (!res.ok) throw new Error('Failed to load node')
  return res.json()
}

export async function sendChat(message: string): Promise<ChatResponse> {
  const res = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message })
  })
  if (!res.ok) throw new Error('Chat request failed')
  return res.json()
}