import json

import httpx
import pytest
from fastapi import HTTPException

from app.config import Settings
from app.services.ollama import ask_ollama, build_ask_response, map_httpx_error


def _ollama_chat_body(**overrides):
    body = {
        "model": "test-model",
        "message": {
            "role": "assistant",
            "content": (
                "ANSWER: Agents research topics.\n"
                "CONFIDENCE: high\n"
                "UNCERTAIN: none\n"
            ),
        },
        "done": True,
        "done_reason": "stop",
        "prompt_eval_count": 20,
        "eval_count": 12,
        "total_duration": 1_500_000_000,
        "load_duration": 100_000_000,
        "prompt_eval_duration": 200_000_000,
        "eval_duration": 800_000_000,
    }
    body.update(overrides)
    return body


def test_build_ask_response_includes_caveats_and_metrics(settings: Settings):
    data = _ollama_chat_body(done_reason="length", eval_count=64)
    raw = data["message"]["content"]
    result = build_ask_response(data, raw=raw, wall_ms=123.4, settings=settings)
    assert result.confidence == "high"
    assert result.metrics.completion_tokens == 64
    assert result.metrics.tokens_remaining == 0
    assert "truncated_at_token_limit" in result.caveats
    assert result.metrics.wall_ms == 123.4


def test_map_read_timeout(settings: Settings):
    exc = map_httpx_error(httpx.ReadTimeout("read timed out"), settings)
    assert exc.status_code == 504
    assert "timed out" in exc.detail.lower()


def test_map_connect_timeout(settings: Settings):
    exc = map_httpx_error(httpx.ConnectTimeout("connect timed out"), settings)
    assert exc.status_code == 504
    assert "connecting" in exc.detail.lower()


def test_ask_ollama_success(monkeypatch, settings: Settings):
    body = _ollama_chat_body()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/chat"
        return httpx.Response(200, json=body)

    transport = httpx.MockTransport(handler)

    real_client = httpx.Client

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return real_client(*args, **kwargs)

    monkeypatch.setattr("app.services.ollama.httpx.Client", client_factory)
    result = ask_ollama("What is an agent?", settings)
    assert "Agents research" in result.answer
    assert result.metrics.prompt_tokens == 20
    assert result.score >= 0.8


def test_ask_ollama_empty_response(monkeypatch, settings: Settings):
    body = _ollama_chat_body()
    body["message"]["content"] = "   "

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=body)

    transport = httpx.MockTransport(handler)
    real_client = httpx.Client

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return real_client(*args, **kwargs)

    monkeypatch.setattr("app.services.ollama.httpx.Client", client_factory)
    with pytest.raises(HTTPException) as ei:
        ask_ollama("hi", settings)
    assert ei.value.status_code == 502


def test_ask_ollama_model_not_found(monkeypatch, settings: Settings):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="model 'missing' not found")

    transport = httpx.MockTransport(handler)
    real_client = httpx.Client

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return real_client(*args, **kwargs)

    monkeypatch.setattr("app.services.ollama.httpx.Client", client_factory)
    with pytest.raises(HTTPException) as ei:
        ask_ollama("hi", settings)
    assert ei.value.status_code == 502


def test_ask_ollama_read_timeout(monkeypatch, settings: Settings):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow model", request=request)

    transport = httpx.MockTransport(handler)
    real_client = httpx.Client

    def client_factory(*args, **kwargs):
        kwargs["transport"] = transport
        return real_client(*args, **kwargs)

    monkeypatch.setattr("app.services.ollama.httpx.Client", client_factory)
    with pytest.raises(HTTPException) as ei:
        ask_ollama("hi", settings)
    assert ei.value.status_code == 504


def test_stream_lines_assemble(monkeypatch, settings: Settings):
    from app.services.ollama import iter_ollama_stream

    lines = [
        json.dumps({"message": {"content": "ANSWER: Hi"}, "done": False}),
        json.dumps(
            {
                "message": {"content": " there"},
                "done": True,
                "done_reason": "stop",
                "prompt_eval_count": 5,
                "eval_count": 3,
                "eval_duration": 100_000_000,
            }
        ),
    ]

    class FakeStream:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def raise_for_status(self):
            return None

        def iter_lines(self):
            yield from lines

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def stream(self, *args, **kwargs):
            return FakeStream()

    monkeypatch.setattr("app.services.ollama.httpx.Client", FakeClient)

    events = list(iter_ollama_stream("q", settings))
    kinds = [k for k, _ in events]
    assert kinds == ["token", "token", "done"]
    assert events[-1][1]["raw"] == "ANSWER: Hi there"


def test_stream_empty_raises(monkeypatch, settings: Settings):
    from app.services.ollama import iter_ollama_stream

    lines = [
        json.dumps(
            {
                "message": {"content": ""},
                "done": True,
                "done_reason": "stop",
            }
        ),
    ]

    class FakeStream:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def raise_for_status(self):
            return None

        def iter_lines(self):
            yield from lines

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def stream(self, *args, **kwargs):
            return FakeStream()

    monkeypatch.setattr("app.services.ollama.httpx.Client", FakeClient)
    with pytest.raises(HTTPException) as ei:
        list(iter_ollama_stream("q", settings))
    assert ei.value.status_code == 502


def test_build_ask_response_low_confidence_caveat(settings: Settings):
    raw = "ANSWER: Maybe.\nCONFIDENCE: low\nUNCERTAIN: everything"
    data = _ollama_chat_body(eval_count=8)
    result = build_ask_response(data, raw=raw, wall_ms=10.0, settings=settings)
    assert result.confidence == "low"
    assert "model_reported_low_confidence" in result.caveats
    assert "uncertainty_declared" in result.caveats
    assert result.score < 0.7
