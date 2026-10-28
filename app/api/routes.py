import asyncio
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app import __version__
from app.config import Settings, get_settings
from app.schemas import (
    AskRequest,
    AskResponse,
    HealthResponse,
    StreamDoneEvent,
    StreamErrorEvent,
    StreamTokenEvent,
)
from app.services.ollama import ask_ollama, aiter_ollama_stream, build_ask_response

router = APIRouter()

_ask_slots: asyncio.Semaphore | None = None
_ask_slots_n: int | None = None


def _semaphore(settings: Settings) -> asyncio.Semaphore:
    """Process-local limit so one Ollama host is not stampeded."""
    global _ask_slots, _ask_slots_n
    n = max(1, settings.max_concurrent_asks)
    if _ask_slots is None or _ask_slots_n != n:
        _ask_slots = asyncio.Semaphore(n)
        _ask_slots_n = n
    return _ask_slots


async def _acquire_or_429(settings: Settings) -> asyncio.Semaphore:
    sem = _semaphore(settings)
    if sem.locked():
        raise HTTPException(
            status_code=429,
            detail=(
                f"Too many concurrent asks (limit={settings.max_concurrent_asks}). "
                "Retry shortly, use /ask/stream for long runs, or raise MAX_CONCURRENT_ASKS."
            ),
        )
    await sem.acquire()
    return sem


@router.get("/health", response_model=HealthResponse)
def health_check(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        model=settings.ollama_model,
        token_limit=settings.token_limit,
        version=__version__,
        max_concurrent_asks=settings.max_concurrent_asks,
    )


@router.post("/ask", response_model=AskResponse)
async def ask(
    request: AskRequest, settings: Settings = Depends(get_settings)
) -> AskResponse:
    sem = await _acquire_or_429(settings)
    try:
        return await asyncio.to_thread(ask_ollama, request.question, settings)
    finally:
        sem.release()


@router.post("/ask/stream")
async def ask_stream(
    request: AskRequest, settings: Settings = Depends(get_settings)
) -> StreamingResponse:
    """SSE stream: `token` events, then one `done` with full AskResponse (incl. caveats)."""
    sem = await _acquire_or_429(settings)

    async def event_gen() -> AsyncIterator[str]:
        try:
            async for kind, payload in aiter_ollama_stream(request.question, settings):
                if kind == "token":
                    evt = StreamTokenEvent(content=payload["content"])
                    yield f"data: {evt.model_dump_json()}\n\n"
                elif kind == "done":
                    result = build_ask_response(
                        payload["data"],
                        raw=payload["raw"],
                        wall_ms=payload["wall_ms"],
                        settings=settings,
                    )
                    evt = StreamDoneEvent(result=result)
                    yield f"data: {evt.model_dump_json()}\n\n"
        except HTTPException as exc:
            err = StreamErrorEvent(detail=str(exc.detail))
            yield f"data: {err.model_dump_json()}\n\n"
        except Exception as exc:  # noqa: BLE001
            err = StreamErrorEvent(detail=str(exc))
            yield f"data: {err.model_dump_json()}\n\n"
        finally:
            sem.release()

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
