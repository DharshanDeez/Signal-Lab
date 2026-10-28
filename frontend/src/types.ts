export type Metrics = {
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  token_limit: number
  tokens_remaining: number
  context_window: number
  load_ms: number
  prompt_eval_ms: number
  eval_ms: number
  total_ms: number
  wall_ms: number
  tokens_per_second: number
  done_reason: string | null
  model: string
}

export type AskResponse = {
  answer: string
  confidence: string
  uncertain: string
  score: number
  metrics: Metrics
  raw: string
  caveats: string[]
}

export type HistoryItem = {
  id: string
  question: string
  result: AskResponse
  askedAt: string
}
