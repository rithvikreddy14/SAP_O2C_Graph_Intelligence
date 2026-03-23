import type { GraphData, NodeDetail, ChatResponse } from './types'

// In development: VITE_API_URL is not set, falls back to /api (proxied by Vite)
// In production on Vercel: VITE_API_URL = your Railway URL
const BASE = import.meta.env.VITE_API_URL ?? '/api'

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