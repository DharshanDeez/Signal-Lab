# Signal Lab — Research Agent

Open-source local research agent: **FastAPI + Ollama** backend and **Vite + React + Tailwind** frontend.

Per run it tracks tokens, budget remaining, confidence, score, latency, and tokens/sec.

## Stack

| Layer | Tech |
|-------|------|
| API | FastAPI, httpx, pydantic-settings |
| LLM | Ollama (local) |
| UI | Vite, React, TypeScript, Tailwind |

## Project layout

```
app/
  api/           # HTTP routes
  services/      # Ollama client + scoring
  config.py      # Settings from .env
  schemas.py     # Request/response models
  prompts.py     # System prompt
  main.py        # FastAPI factory
frontend/        # Vite UI
.env.example     # Backend env template (commit this)
main.py          # Thin shim → app.main:app
```

## Prerequisites

- Python 3.11+
- [Ollama](https://ollama.com) with your model pulled
- Node.js 20+ (for the UI)

## Quick start

### 1. Configure env

```powershell
copy .env.example .env
```

Edit `.env` if your model or URLs differ. **Do not commit `.env`.**

### 2. Backend

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- Health: http://127.0.0.1:8000/health  
- Docs: http://127.0.0.1:8000/docs  

### 3. Frontend

```powershell
cd frontend
copy .env.example .env
npm install
npm run dev
```

Open http://127.0.0.1:5173  

Vite proxies `/api/*` to the backend. Optional: set `VITE_API_URL` in `frontend/.env`.

## Environment variables

See [`.env.example`](.env.example). Important ones:

| Variable | Purpose |
|----------|---------|
| `OLLAMA_BASE_URL` | Ollama host (default `http://127.0.0.1:11434`) |
| `OLLAMA_CHAT_PATH` | Chat endpoint path (`/api/chat`) |
| `OLLAMA_MODEL` | Model tag (e.g. `qwen2.5:7b`) |
| `OLLAMA_CONNECT_TIMEOUT_SECONDS` | Fail fast if Ollama is down |
| `OLLAMA_READ_TIMEOUT_SECONDS` | Max wait for generation |
| `MAX_CONCURRENT_ASKS` | Soft per-process concurrency guard |
| `TOKEN_LIMIT` | Max completion tokens (`num_predict`) |
| `CONTEXT_WINDOW` | Approx context size for UI bar |
| `CORS_ORIGINS` | Comma-separated allowed frontend origins |
| `API_HOST` / `API_PORT` | Documented bind address |

## API endpoints

| Method | Path | Notes |
|--------|------|-------|
| `GET` | `/health` | Liveness + model + concurrency hint |
| `POST` | `/ask` | Full JSON answer + metrics + caveats |
| `POST` | `/ask/stream` | SSE: `token` events then `done` |

## Resilience (honest OSS notes)

This project is designed for **local / self-hosted** use first. A single Ollama process will not serve “1M users.” For production scale you would place a queue, multiple GPU workers, auth, and rate limits in front.

What v1 *does* include:

- **Split timeouts** — connect vs read (`504` with clear messages)
- **Token budget** — `TOKEN_LIMIT` + `truncated_at_token_limit` caveat when `done_reason=length`
- **Confidence + caveats** — parsed from the model; caveats flag missing structure, low confidence, truncation
- **Concurrency guard** — `MAX_CONCURRENT_ASKS` returns `429` when the process is saturated
- **Streaming** — `/ask/stream` so UIs can show tokens without waiting for the full reply

Confidence is a **model self-report + heuristics**, not a calibrated probability. Treat caveats as warnings for humans and eval harnesses.

## Tests

```powershell
pip install -r requirements.txt
pytest -q
```

No live GPU / Ollama required. Current coverage:

| Area | What’s asserted |
|------|-----------------|
| Confidence / score | Parse `ANSWER`/`CONFIDENCE`/`UNCERTAIN`, clamp score, truncation penalty |
| Caveats | Low confidence, unstructured, empty answer, hit token budget |
| Timeouts | Connect/read → mapped `504`; mocked slow Ollama |
| Tokens / empty | Empty completion → `502`; model 404 → `502` |
| Concurrency | Saturated semaphore → `429` on `/ask` and `/ask/stream` |
| Streaming | Token assembly; SSE `token` → `done`; SSE `error` on timeout |

```powershell
pytest tests/test_scoring.py -q   # confidence + caveats only
pytest tests/test_ollama.py -q    # timeouts + stream assembly
pytest tests/test_api.py -q       # HTTP + 429 + SSE
```

## License

[MIT](LICENSE) — free to use, modify, and distribute.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).
