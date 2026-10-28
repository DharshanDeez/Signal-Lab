type Props = {
  label: string
  value: string
  hint?: string
  tone?: 'default' | 'good' | 'warn' | 'low'
}

const valueTone = {
  default: 'text-ink',
  good: 'text-good',
  warn: 'text-warn',
  low: 'text-bad',
}

export function MetricCard({ label, value, hint, tone = 'default' }: Props) {
  return (
    <div className="rounded-lg bg-canvas/80 px-3 py-2.5">
      <p className="text-[13px] text-muted">{label}</p>
      <p className={`mt-0.5 text-[20px] font-semibold tabular-nums leading-tight ${valueTone[tone]}`}>
        {value}
      </p>
      {hint ? <p className="mt-0.5 text-[12px] text-muted">{hint}</p> : null}
    </div>
  )
}
