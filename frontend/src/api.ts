import type { AskResponse } from './types'

const API_BASE = import.meta.env.VITE_API_URL ?? '/api'

export async function askQuestion(question: string): Promise<AskResponse> {
  const res = await fetch(`${API_BASE}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })

  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail ?? JSON.stringify(body)
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }

  return res.json()
}

export async function checkHealth(): Promise<{
  status: string
  model: string
  token_limit: number
  ollama_base_url?: string
}> {
  const res = await fetch(`${API_BASE}/health`)
  if (!res.ok) throw new Error('API health check failed')
  return res.json()
}
