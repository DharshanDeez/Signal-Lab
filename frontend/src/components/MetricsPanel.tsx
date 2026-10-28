import { MetricCard } from './MetricCard'
import { TokenBar } from './TokenBar'
import type { AskResponse } from '../types'

function confidenceTone(c: string): 'good' | 'warn' | 'low' | 'default' {
  if (c === 'high') return 'good'
  if (c === 'medium') return 'warn'
  if (c === 'low') return 'low'
  return 'default'
}

function scoreTone(score: number): 'good' | 'warn' | 'low' | 'default' {
  if (score >= 0.8) return 'good'
  if (score >= 0.55) return 'warn'
  if (score > 0) return 'low'
  return 'default'
}

function formatMs(ms: number): string {
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)} s`
  return `${Math.round(ms)} ms`
}

type Props = {
  result: AskResponse | null
  loading: boolean
}

export function MetricsPanel({ result, loading }: Props) {
  const m = result?.metrics

  return (
    <aside className="panel sticky top-5 p-5 lg:p-6">
      <div className="mb-5 flex items-center justify-between gap-2">
        <h2 className="text-lg font-semibold text-ink">Run metrics</h2>
        {loading ? (
          <span className="text-[13px] text-accent animate-pulse">Updating…</span>
        ) : null}
      </div>

      {loading && !result ? (
        <div className="space-y-3" aria-hidden>
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-14 animate-pulse rounded-lg bg-canvas" />
          ))}
        </div>
      ) : null}

      {!loading && !result ? (
        <div className="rounded-lg bg-canvas px-4 py-8 text-center">
          <p className="text-[15px] font-medium text-ink-soft">No run yet</p>
          <p className="mt-1 text-[13px] text-muted">
            Ask a question on the left. Tokens, confidence, and timing show up here.
          </p>
        </div>
      ) : null}

      {result && m ? (
        <div className="space-y-6 animate-[fadeIn_0.35s_ease-out]">
          <section>
            <p className="mb-2 text-[13px] font-semibold text-ink-soft">Quality</p>
            <div className="grid grid-cols-2 gap-2">
              <MetricCard
                label="Confidence"
                value={result.confidence}
                tone={confidenceTone(result.confidence)}
              />
              <MetricCard
                label="Score"
                value={result.score.toFixed(2)}
                hint="0–1 quality estimate"
                tone={scoreTone(result.score)}
              />
            </div>
          </section>

          <section className="space-y-3">
            <p className="text-[13px] font-semibold text-ink-soft">Tokens</p>
            <TokenBar
              label="Reply budget used"
              used={m.completion_tokens}
              limit={m.token_limit}
            />
            <TokenBar
              label="Context used (approx)"
              used={m.total_tokens}
              limit={m.context_window}
            />
            <div className="grid grid-cols-2 gap-2">
              <MetricCard label="Prompt" value={String(m.prompt_tokens)} />
              <MetricCard label="Reply" value={String(m.completion_tokens)} />
              <MetricCard label="Total" value={String(m.total_tokens)} />
              <MetricCard
                label="Left in budget"
                value={String(m.tokens_remaining)}
              />
            </div>
          </section>

          <section>
            <p className="mb-2 text-[13px] font-semibold text-ink-soft">Timing</p>
            <div className="grid grid-cols-2 gap-2">
              <MetricCard label="Total wait" value={formatMs(m.wall_ms)} />
              <MetricCard label="Generate" value={formatMs(m.eval_ms)} />
              <MetricCard label="Read prompt" value={formatMs(m.prompt_eval_ms)} />
              <MetricCard label="Model load" value={formatMs(m.load_ms)} />
              <MetricCard label="Speed" value={`${m.tokens_per_second} tok/s`} />
              <MetricCard
                label="Stop reason"
                value={m.done_reason ?? '—'}
                tone={m.done_reason === 'length' ? 'warn' : 'default'}
                hint={m.done_reason === 'length' ? 'Hit token limit' : undefined}
              />
            </div>
          </section>

          <p className="border-t border-line pt-3 text-[12px] text-muted">
            Model: {m.model}
          </p>
        </div>
      ) : null}

      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(4px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </aside>
  )
}
