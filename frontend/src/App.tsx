import { useEffect, useRef, useState } from 'react'
import type { FormEvent, KeyboardEvent } from 'react'
import { askQuestion, checkHealth } from './api'
import { MetricsPanel } from './components/MetricsPanel'
import { StatusBadge } from './components/StatusBadge'
import type { AskResponse, HistoryItem } from './types'

const EXAMPLES = [
  'What is a research agent in simple terms?',
  'Explain RAG in one short paragraph.',
  'Who won the 2027 Cricket World Cup?',
]

export default function App() {
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<AskResponse | null>(null)
  const [history, setHistory] = useState<HistoryItem[]>([])
  const [apiOk, setApiOk] = useState<boolean | null>(null)
  const [model, setModel] = useState('…')
  const [lastQuestion, setLastQuestion] = useState('')
  const outputRef = useRef<HTMLElement>(null)

  useEffect(() => {
    checkHealth()
      .then((h) => {
        setApiOk(true)
        setModel(h.model)
      })
      .catch(() => setApiOk(false))
  }, [])

  async function runAsk(q: string) {
    const trimmed = q.trim()
    if (!trimmed || loading) return

    setLoading(true)
    setError(null)

    try {
      const data = await askQuestion(trimmed)
      setResult(data)
      setLastQuestion(trimmed)
      setHistory((prev) =>
        [
          {
            id: crypto.randomUUID(),
            question: trimmed,
            result: data,
            askedAt: new Date().toLocaleTimeString(),
          },
          ...prev,
        ].slice(0, 12),
      )
      window.setTimeout(() => {
        outputRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
      }, 50)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Request failed')
    } finally {
      setLoading(false)
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault()
    void runAsk(question)
  }

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault()
      void runAsk(question)
    }
  }

  return (
    <div className="mx-auto min-h-svh max-w-6xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
      <header className="mb-6 flex flex-wrap items-center justify-between gap-3 sm:mb-8">
        <div>
          <p className="text-[13px] text-muted">Local research agent · v1</p>
          <h1 className="text-[28px] font-bold leading-tight text-ink sm:text-[32px]">
            Signal Lab
          </h1>
        </div>
        <StatusBadge apiOk={apiOk} model={model} />
      </header>

      <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,1.4fr)_minmax(300px,0.85fr)] lg:gap-6">
        {/* Left column */}
        <div className="min-w-0 space-y-5">
          <section className="panel p-5 sm:p-6">
            <form onSubmit={onSubmit} className="space-y-4">
              <div className="flex items-end justify-between gap-3">
                <label htmlFor="q" className="text-[15px] font-semibold text-ink">
                  Your question
                </label>
                <span className="hidden text-[12px] text-muted sm:inline">
                  Ctrl + Enter to run
                </span>
              </div>

              <textarea
                id="q"
                rows={4}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={onKeyDown}
                placeholder="Ask anything you want the agent to research…"
                disabled={loading}
                className="w-full resize-y rounded-lg border border-line bg-canvas px-3.5 py-3 text-[15px] text-ink outline-none transition placeholder:text-muted/80 focus:border-accent focus:bg-surface focus:ring-2 focus:ring-accent/20 disabled:opacity-60"
              />

              <div>
                <p className="mb-2 text-[12px] text-muted">Try an example</p>
                <div className="flex flex-wrap gap-2">
                  {EXAMPLES.map((ex) => (
                    <button
                      key={ex}
                      type="button"
                      onClick={() => setQuestion(ex)}
                      disabled={loading}
                      className="rounded-full border border-line bg-surface px-3 py-1.5 text-left text-[13px] text-ink-soft transition hover:border-accent hover:bg-accent-soft hover:text-accent disabled:opacity-50"
                    >
                      {ex}
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <button
                  type="submit"
                  disabled={loading || !question.trim() || apiOk === false}
                  className="inline-flex min-w-[120px] items-center justify-center rounded-lg bg-accent px-5 py-2.5 text-[15px] font-semibold text-white transition hover:bg-ink disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {loading ? 'Thinking…' : 'Ask'}
                </button>
                {question ? (
                  <button
                    type="button"
                    onClick={() => setQuestion('')}
                    disabled={loading}
                    className="rounded-lg px-3 py-2 text-[14px] text-muted transition hover:bg-canvas hover:text-ink disabled:opacity-40"
                  >
                    Clear
                  </button>
                ) : null}
                {loading ? (
                  <span className="text-[13px] text-muted">
                    Local model is generating an answer…
                  </span>
                ) : null}
              </div>
            </form>
          </section>

          {error ? (
            <div
              role="alert"
              className="rounded-xl border border-bad/30 bg-bad-soft px-4 py-3 text-[14px] text-bad"
            >
              <p className="font-semibold">Something went wrong</p>
              <p className="mt-1 opacity-90">{error}</p>
              <p className="mt-2 text-[13px] text-ink-soft">
                Check that Ollama is running and the API is up on port 8000.
              </p>
            </div>
          ) : null}

          <section ref={outputRef} className="panel p-5 sm:p-6" aria-live="polite">
            <div className="mb-4 flex items-center justify-between gap-2">
              <h2 className="text-[15px] font-semibold text-ink">Answer</h2>
              {result ? (
                <span
                  className={`rounded-full px-2.5 py-0.5 text-[12px] font-semibold capitalize ${
                    result.confidence === 'high'
                      ? 'bg-accent-soft text-good'
                      : result.confidence === 'medium'
                        ? 'bg-[#fff7ed] text-warn'
                        : result.confidence === 'low'
                          ? 'bg-bad-soft text-bad'
                          : 'bg-canvas text-muted'
                  }`}
                >
                  {result.confidence} confidence
                </span>
              ) : null}
            </div>

            {loading && !result ? (
              <div className="space-y-2" aria-hidden>
                <div className="h-4 w-[92%] animate-pulse rounded bg-canvas" />
                <div className="h-4 w-[80%] animate-pulse rounded bg-canvas" />
                <div className="h-4 w-[64%] animate-pulse rounded bg-canvas" />
              </div>
            ) : null}

            {!loading && !result ? (
              <div className="rounded-lg bg-canvas px-4 py-10 text-center">
                <p className="text-[15px] font-medium text-ink-soft">
                  Your answer will show here
                </p>
                <p className="mx-auto mt-1 max-w-sm text-[13px] text-muted">
                  Try an example above, or type your own question and press Ask.
                </p>
              </div>
            ) : null}

            {result ? (
              <div className="space-y-4 animate-[fadeIn_0.35s_ease-out]">
                {lastQuestion ? (
                  <p className="rounded-lg bg-canvas px-3 py-2 text-[13px] text-ink-soft">
                    <span className="font-semibold text-muted">You asked: </span>
                    {lastQuestion}
                  </p>
                ) : null}
                <p className="whitespace-pre-wrap text-[16px] leading-relaxed text-ink">
                  {result.answer}
                </p>
                {result.uncertain && result.uncertain.toLowerCase() !== 'none' ? (
                  <div className="rounded-lg border border-[#fed7aa] bg-[#fff7ed] px-3 py-2 text-[14px] text-warn">
                    <span className="font-semibold">Uncertain: </span>
                    {result.uncertain}
                  </div>
                ) : null}
                {result.caveats?.length ? (
                  <div className="rounded-lg bg-canvas px-3 py-2">
                    <p className="text-[13px] font-semibold text-ink-soft">Caveats</p>
                    <ul className="mt-1 list-inside list-disc text-[13px] text-muted">
                      {result.caveats.map((c) => (
                        <li key={c}>{c.replaceAll('_', ' ')}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}
              </div>
            ) : null}
          </section>

          {history.length > 0 ? (
            <section className="panel p-5 sm:p-6">
              <h2 className="mb-3 text-[15px] font-semibold text-ink">Recent runs</h2>
              <ul className="divide-y divide-line">
                {history.map((item) => (
                  <li key={item.id}>
                    <button
                      type="button"
                      className="flex w-full items-start justify-between gap-3 py-3 text-left transition hover:bg-canvas/80"
                      onClick={() => {
                        setQuestion(item.question)
                        setLastQuestion(item.question)
                        setResult(item.result)
                        setError(null)
                      }}
                    >
                      <span className="min-w-0 flex-1 truncate text-[14px] text-ink">
                        {item.question}
                      </span>
                      <span className="shrink-0 text-[12px] tabular-nums text-muted">
                        {item.askedAt} · score {item.result.score.toFixed(2)}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}
        </div>

        {/* Right column */}
        <MetricsPanel result={result} loading={loading} />
      </div>

      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(4px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  )
}
