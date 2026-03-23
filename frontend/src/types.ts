export interface GraphNode {
  id: string
  type: string
  label?: string
  [key: string]: unknown
}

export interface GraphLink {
  source: string
  target: string
  rel: string
}

export interface GraphData {
  nodes: GraphNode[]
  links: GraphLink[]
}

export interface NodeDetail {
  node: GraphNode
  neighbors: GraphNode[]
}

export type MessageRole = 'user' | 'assistant' | 'error'

export interface Message {
  id: string
  role: MessageRole
  content: string
  sql?: string
  rows?: Record<string, unknown>[]
  timestamp: Date
  loading?: boolean
}

export interface ChatResponse {
  answer: string
  sql?: string
  rows?: Record<string, unknown>[]
}