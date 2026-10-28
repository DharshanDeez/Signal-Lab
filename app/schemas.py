from typing import Literal, Optional

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=8000)


class Metrics(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    token_limit: int
    tokens_remaining: int
    context_window: int
    load_ms: float
    prompt_eval_ms: float
    eval_ms: float
    total_ms: float
    wall_ms: float
    tokens_per_second: float
    done_reason: Optional[str] = None
    model: str


class AskResponse(BaseModel):
    answer: str
    confidence: str
    uncertain: str
    score: float
    metrics: Metrics
    raw: str
    caveats: list[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    model: str
    token_limit: int
    version: str
    max_concurrent_asks: int = 0


class StreamTokenEvent(BaseModel):
    type: Literal["token"] = "token"
    content: str


class StreamDoneEvent(BaseModel):
    type: Literal["done"] = "done"
    result: AskResponse


class StreamErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    detail: str
