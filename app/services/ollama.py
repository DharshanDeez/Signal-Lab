import json
import re
import time
from collections.abc import AsyncIterator, Iterator
from typing import Any

import httpx
from fastapi import HTTPException

from app.config import Settings
from app.prompts import SYSTEM_PROMPT
from app.schemas import AskResponse, Metrics
from app.services.scoring import build_caveats, compute_score, parse_structured


def _ns_to_ms(value: int | None) -> float:
    if not value:
        return 0.0
    return round(value / 1_000_000, 2)


def http_timeout(settings: Settings) -> httpx.Timeout:
    return httpx.Timeout(
        connect=settings.ollama_connect_timeout_seconds,
        read=settings.ollama_read_timeout_seconds,
        write=settings.ollama_connect_timeout_seconds,
        pool=settings.ollama_connect_timeout_seconds,
    )


def _chat_payload(question: str, settings: Settings, *, stream: bool) -> dict[str, Any]:
    return {
        "model": settings.ollama_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
        "stream": stream,
        "options": {
            "num_predict": settings.token_limit,
        },
    }


def build_ask_response(
    data: dict[str, Any],
    *,
    raw: str,
    wall_ms: float,
    settings: Settings,
) -> AskResponse:
    answer, confidence, uncertain = parse_structured(raw)
    structured = confidence != "unknown" and bool(
        re.search(r"ANSWER:", raw, re.IGNORECASE)
    )

    prompt_tokens = int(data.get("prompt_eval_count") or 0)
    completion_tokens = int(data.get("eval_count") or 0)
    total_tokens = prompt_tokens + completion_tokens
    eval_ms = _ns_to_ms(data.get("eval_duration"))
    tokens_per_second = 0.0
    if eval_ms > 0 and completion_tokens > 0:
        tokens_per_second = round(completion_tokens / (eval_ms / 1000), 2)

    done_reason = data.get("done_reason")
    score = compute_score(confidence, structured, done_reason)
    caveats = build_caveats(
        confidence=confidence,
        structured=structured,
        done_reason=done_reason,
        completion_tokens=completion_tokens,
        token_limit=settings.token_limit,
        uncertain=uncertain,
        answer=answer,
    )

    metrics = Metrics(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        token_limit=settings.token_limit,
        tokens_remaining=max(settings.token_limit - completion_tokens, 0),
        context_window=settings.context_window,
        load_ms=_ns_to_ms(data.get("load_duration")),
        prompt_eval_ms=_ns_to_ms(data.get("prompt_eval_duration")),
        eval_ms=eval_ms,
        total_ms=_ns_to_ms(data.get("total_duration")),
        wall_ms=wall_ms,
        tokens_per_second=tokens_per_second,
        done_reason=done_reason,
        model=data.get("model") or settings.ollama_model,
    )

    return AskResponse(
        answer=answer,
        confidence=confidence,
        uncertain=uncertain,
        score=score,
        metrics=metrics,
        raw=raw,
        caveats=caveats,
    )


def map_httpx_error(exc: Exception, settings: Settings) -> HTTPException:
    if isinstance(exc, httpx.ConnectTimeout):
        return HTTPException(
            status_code=504,
            detail=(
                f"Timed out connecting to Ollama "
                f"({settings.ollama_connect_timeout_seconds}s). Is it running?"
            ),
        )
    if isinstance(exc, httpx.ReadTimeout):
        return HTTPException(
            status_code=504,
            detail=(
                f"Ollama generation timed out after "
                f"{settings.ollama_read_timeout_seconds}s. "
                "Lower TOKEN_LIMIT or raise OLLAMA_READ_TIMEOUT_SECONDS."
            ),
        )
    if isinstance(exc, httpx.TimeoutException):
        return HTTPException(status_code=504, detail=f"Ollama request timed out: {exc}")
    if isinstance(exc, httpx.HTTPStatusError):
        return HTTPException(
            status_code=502, detail=f"Ollama error: {exc.response.text}"
        )
    if isinstance(exc, httpx.RequestError):
        return HTTPException(
            status_code=503,
            detail=f"Cannot reach Ollama at {settings.ollama_chat_url}: {exc}",
        )
    return HTTPException(status_code=500, detail=str(exc))


def ask_ollama(question: str, settings: Settings) -> AskResponse:
    payload = _chat_payload(question, settings, stream=False)
    started = time.perf_counter()
    try:
        with httpx.Client(timeout=http_timeout(settings)) as client:
            response = client.post(settings.ollama_chat_url, json=payload)
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        raise map_httpx_error(exc, settings) from exc

    wall_ms = round((time.perf_counter() - started) * 1000, 2)
    message = data.get("message") or {}
    raw = (message.get("content") or "").strip()
    if not raw:
        raise HTTPException(status_code=502, detail="Empty model response")

    return build_ask_response(data, raw=raw, wall_ms=wall_ms, settings=settings)


def iter_ollama_stream(
    question: str, settings: Settings
) -> Iterator[tuple[str, dict[str, Any]]]:
    """
    Yields ("token", {"content": str}) then ("done", {"data": dict, "raw": str, "wall_ms": float}).
    """
    payload = _chat_payload(question, settings, stream=True)
    started = time.perf_counter()
    raw_parts: list[str] = []
    final: dict[str, Any] = {}

    try:
        with httpx.Client(timeout=http_timeout(settings)) as client:
            with client.stream(
                "POST", settings.ollama_chat_url, json=payload
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    piece = (chunk.get("message") or {}).get("content") or ""
                    if piece:
                        raw_parts.append(piece)
                        yield ("token", {"content": piece})
                    if chunk.get("done"):
                        final = chunk
                        break
    except (httpx.HTTPError, httpx.TimeoutException, json.JSONDecodeError) as exc:
        raise map_httpx_error(exc, settings) from exc

    wall_ms = round((time.perf_counter() - started) * 1000, 2)
    raw = "".join(raw_parts).strip()
    if not raw:
        raise HTTPException(status_code=502, detail="Empty model response")
    yield ("done", {"data": final, "raw": raw, "wall_ms": wall_ms})


async def aiter_ollama_stream(
    question: str, settings: Settings
) -> AsyncIterator[tuple[str, dict[str, Any]]]:
    payload = _chat_payload(question, settings, stream=True)
    started = time.perf_counter()
    raw_parts: list[str] = []
    final: dict[str, Any] = {}

    try:
        async with httpx.AsyncClient(timeout=http_timeout(settings)) as client:
            async with client.stream(
                "POST", settings.ollama_chat_url, json=payload
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    piece = (chunk.get("message") or {}).get("content") or ""
                    if piece:
                        raw_parts.append(piece)
                        yield ("token", {"content": piece})
                    if chunk.get("done"):
                        final = chunk
                        break
    except (httpx.HTTPError, httpx.TimeoutException, json.JSONDecodeError) as exc:
        raise map_httpx_error(exc, settings) from exc

    wall_ms = round((time.perf_counter() - started) * 1000, 2)
    raw = "".join(raw_parts).strip()
    if not raw:
        raise HTTPException(status_code=502, detail="Empty model response")
    yield ("done", {"data": final, "raw": raw, "wall_ms": wall_ms})
