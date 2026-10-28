import re
from typing import Optional

VALID_CONFIDENCE = frozenset({"high", "medium", "low", "unknown"})


def parse_structured(text: str) -> tuple[str, str, str]:
    """Parse ANSWER / CONFIDENCE / UNCERTAIN blocks from model text."""
    answer = text.strip()
    confidence = "unknown"
    uncertain = "none"

    answer_match = re.search(
        r"ANSWER:\s*(.*?)(?=\n\s*CONFIDENCE:|\Z)", text, re.IGNORECASE | re.DOTALL
    )
    conf_match = re.search(
        r"CONFIDENCE:\s*([^\n\r]+)", text, re.IGNORECASE
    )
    uncertain_match = re.search(
        r"UNCERTAIN:\s*(.*?)(?=\n\s*[A-Z]+:|\Z)", text, re.IGNORECASE | re.DOTALL
    )

    if answer_match:
        answer = answer_match.group(1).strip()
    if conf_match:
        raw_conf = conf_match.group(1).strip().lower()
        # Accept "high", "High.", "medium confidence", etc.
        for level in ("high", "medium", "low"):
            if raw_conf.startswith(level) or level in raw_conf.split():
                confidence = level
                break
    if uncertain_match:
        uncertain = uncertain_match.group(1).strip() or "none"

    return answer, confidence, uncertain


def compute_score(
    confidence: str, structured: bool, done_reason: Optional[str]
) -> float:
    base = {"high": 0.85, "medium": 0.65, "low": 0.4, "unknown": 0.3}.get(
        confidence if confidence in VALID_CONFIDENCE else "unknown", 0.3
    )
    if structured:
        base += 0.1
    if done_reason == "stop":
        base += 0.05
    elif done_reason == "length":
        base -= 0.15
    return round(max(0.0, min(1.0, base)), 2)


def build_caveats(
    *,
    confidence: str,
    structured: bool,
    done_reason: Optional[str],
    completion_tokens: int,
    token_limit: int,
    uncertain: str,
    answer: str,
) -> list[str]:
    """Human-readable warnings for UI / eval — not a guarantee of correctness."""
    caveats: list[str] = []

    if not answer.strip():
        caveats.append("empty_answer")
    if not structured:
        caveats.append("unstructured_response")
    if confidence == "unknown":
        caveats.append("confidence_missing")
    if confidence == "low":
        caveats.append("model_reported_low_confidence")
    if uncertain and uncertain.lower() not in {"none", "n/a", "na", "-"}:
        caveats.append("uncertainty_declared")
    if done_reason == "length":
        caveats.append("truncated_at_token_limit")
    if token_limit > 0 and completion_tokens >= token_limit:
        caveats.append("hit_token_budget")
    if done_reason not in (None, "stop", "length"):
        caveats.append(f"unusual_done_reason:{done_reason}")

    return caveats
