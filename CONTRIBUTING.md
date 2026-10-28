# Contributing

Thanks for helping improve Signal Lab.

## Setup

1. Fork and clone the repo.
2. Copy `.env.example` → `.env` and adjust if needed.
3. Create a Python venv, install `requirements.txt`.
4. Install and run [Ollama](https://ollama.com); pull the model in `.env` (`OLLAMA_MODEL`).
5. For the UI: `cd frontend && npm install && cp .env.example .env && npm run dev`.

## Guidelines

- Keep changes focused; match existing style.
- Do not commit `.env`, model weights, or secrets.
- Prefer clear names and small modules under `app/`.
- Run `pytest -q` before opening a PR; include what changed and how you tested (`/health`, `/ask`, `/ask/stream`, or the UI).

## License

By contributing, you agree your contributions are licensed under the MIT License.
