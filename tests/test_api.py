from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.api import routes as routes_mod
from app.config import Settings, get_settings
from app.main import create_app
from app.schemas import AskResponse, Metrics


@pytest.fixture
def client(settings: Settings):
    routes_mod._ask_slots = None
    routes_mod._ask_slots_n = None
    application = create_app()
    application.dependency_overrides[get_settings] = lambda: settings
    with TestClient(application) as c:
        yield c
    application.dependency_overrides.clear()
    routes_mod._ask_slots = None
    routes_mod._ask_slots_n = None


def _fake_response(settings: Settings) -> AskResponse:
    return AskResponse(
        answer="Hello",
        confidence="high",
        uncertain="none",
        score=0.9,
        raw="ANSWER: Hello\nCONFIDENCE: high\nUNCERTAIN: none",
        caveats=[],
        metrics=Metrics(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            token_limit=settings.token_limit,
            tokens_remaining=settings.token_limit - 5,
            context_window=settings.context_window,
            load_ms=1.0,
            prompt_eval_ms=2.0,
            eval_ms=3.0,
            total_ms=6.0,
            wall_ms=10.0,
            tokens_per_second=100.0,
            done_reason="stop",
            model=settings.ollama_model,
        ),
    )


def test_health(client: TestClient, settings: Settings):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["model"] == settings.ollama_model
    assert body["max_concurrent_asks"] == settings.max_concurrent_asks


def test_ask_validation_rejects_empty(client: TestClient):
    r = client.post("/ask", json={"question": ""})
    assert r.status_code == 422


def test_ask_success(client: TestClient, settings: Settings):
    with patch(
        "app.api.routes.ask_ollama", return_value=_fake_response(settings)
    ):
        r = client.post("/ask", json={"question": "What is Signal Lab?"})
    assert r.status_code == 200
    assert r.json()["answer"] == "Hello"
    assert r.json()["confidence"] == "high"


def test_ask_returns_429_when_slots_full(client: TestClient, settings: Settings):
    import asyncio

    # Semaphore(0) is immediately locked → 429 without calling Ollama
    routes_mod._ask_slots = asyncio.Semaphore(0)
    routes_mod._ask_slots_n = settings.max_concurrent_asks

    r = client.post("/ask", json={"question": "busy?"})
    assert r.status_code == 429
    assert "concurrent" in r.json()["detail"].lower()


def test_ask_stream_emits_token_then_done(client: TestClient, settings: Settings):
    async def fake_stream(question: str, s: Settings):
        yield ("token", {"content": "ANSWER: "})
        yield ("token", {"content": "streamed"})
        yield (
            "done",
            {
                "data": {
                    "model": s.ollama_model,
                    "done_reason": "stop",
                    "prompt_eval_count": 8,
                    "eval_count": 4,
                    "eval_duration": 50_000_000,
                    "total_duration": 80_000_000,
                    "load_duration": 0,
                    "prompt_eval_duration": 10_000_000,
                },
                "raw": "ANSWER: streamed\nCONFIDENCE: high\nUNCERTAIN: none",
                "wall_ms": 42.0,
            },
        )

    with patch("app.api.routes.aiter_ollama_stream", side_effect=fake_stream):
        with client.stream(
            "POST", "/ask/stream", json={"question": "stream please"}
        ) as r:
            assert r.status_code == 200
            assert "text/event-stream" in r.headers["content-type"]
            body = "".join(r.iter_text())

    assert '"type":"token"' in body or '"type": "token"' in body
    assert "streamed" in body
    assert '"type":"done"' in body or '"type": "done"' in body
    assert "confidence" in body


def test_ask_stream_emits_error_event(client: TestClient, settings: Settings):
    from fastapi import HTTPException

    async def boom_gen(question: str, s: Settings):
        raise HTTPException(status_code=504, detail="Ollama generation timed out")
        if False:  # pragma: no cover — keeps this an async generator
            yield ("token", {"content": ""})

    with patch("app.api.routes.aiter_ollama_stream", side_effect=boom_gen):
        with client.stream(
            "POST", "/ask/stream", json={"question": "timeout?"}
        ) as r:
            assert r.status_code == 200
            body = "".join(r.iter_text())

    assert '"type":"error"' in body or '"type": "error"' in body
    assert "timed out" in body.lower()


def test_ask_stream_returns_429_when_slots_full(
    client: TestClient, settings: Settings
):
    import asyncio

    routes_mod._ask_slots = asyncio.Semaphore(0)
    routes_mod._ask_slots_n = settings.max_concurrent_asks

    r = client.post("/ask/stream", json={"question": "busy stream?"})
    assert r.status_code == 429
