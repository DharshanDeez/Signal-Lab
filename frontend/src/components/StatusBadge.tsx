type Props = {
  apiOk: boolean | null
  model: string
}

export function StatusBadge({ apiOk, model }: Props) {
  if (apiOk === null) {
    return (
      <span className="inline-flex items-center gap-2 rounded-full bg-line/60 px-3 py-1 text-[13px] text-muted">
        <span className="size-2 animate-pulse rounded-full bg-muted" />
        Connecting…
      </span>
    )
  }

  if (!apiOk) {
    return (
      <span className="inline-flex items-center gap-2 rounded-full bg-bad-soft px-3 py-1 text-[13px] text-bad">
        <span className="size-2 rounded-full bg-bad" />
        API offline — start the backend
      </span>
    )
  }

  return (
    <span className="inline-flex items-center gap-2 rounded-full bg-accent-soft px-3 py-1 text-[13px] text-accent">
      <span className="size-2 rounded-full bg-good" />
      Ready · {model}
    </span>
  )
}
