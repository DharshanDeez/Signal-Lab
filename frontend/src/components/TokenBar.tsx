type Props = {
  used: number
  limit: number
  label: string
}

export function TokenBar({ used, limit, label }: Props) {
  const pct = limit > 0 ? Math.min(100, Math.round((used / limit) * 100)) : 0
  const bar =
    pct >= 90 ? 'bg-bad' : pct >= 70 ? 'bg-warn' : 'bg-accent'

  return (
    <div className="space-y-1.5">
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-[13px] text-muted">{label}</span>
        <span className="text-[13px] font-semibold tabular-nums text-ink">
          {used.toLocaleString()} / {limit.toLocaleString()}
          <span className="ml-1 font-normal text-muted">({pct}%)</span>
        </span>
      </div>
      <div
        className="h-2 overflow-hidden rounded-full bg-line"
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label}
      >
        <div
          className={`h-full rounded-full transition-all duration-500 ease-out ${bar}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}
