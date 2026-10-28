from app.services.scoring import build_caveats, compute_score, parse_structured


def test_parse_structured_happy_path():
    text = """
ANSWER: A research agent plans, retrieves, and answers with sources.
CONFIDENCE: high
UNCERTAIN: none
"""
    answer, confidence, uncertain = parse_structured(text)
    assert "research agent" in answer.lower()
    assert confidence == "high"
    assert uncertain.lower() == "none"


def test_parse_confidence_with_noise():
    text = "ANSWER: Hello\nCONFIDENCE: Medium (approx)\nUNCERTAIN: dates"
    _, confidence, uncertain = parse_structured(text)
    assert confidence == "medium"
    assert "dates" in uncertain


def test_parse_missing_structure_defaults_unknown():
    answer, confidence, uncertain = parse_structured("Just a freeform reply.")
    assert answer.startswith("Just a freeform")
    assert confidence == "unknown"
    assert uncertain == "none"


def test_score_penalizes_truncation():
    full = compute_score("high", True, "stop")
    cut = compute_score("high", True, "length")
    assert cut < full


def test_score_clamped():
    assert compute_score("unknown", False, "length") >= 0.0
    assert compute_score("high", True, "stop") <= 1.0


def test_caveats_for_truncation_and_low_confidence():
    caveats = build_caveats(
        confidence="low",
        structured=True,
        done_reason="length",
        completion_tokens=64,
        token_limit=64,
        uncertain="might be wrong",
        answer="partial…",
    )
    assert "truncated_at_token_limit" in caveats
    assert "hit_token_budget" in caveats
    assert "model_reported_low_confidence" in caveats
    assert "uncertainty_declared" in caveats


def test_caveats_unstructured():
    caveats = build_caveats(
        confidence="unknown",
        structured=False,
        done_reason="stop",
        completion_tokens=10,
        token_limit=64,
        uncertain="none",
        answer="hi",
    )
    assert "unstructured_response" in caveats
    assert "confidence_missing" in caveats


def test_caveats_empty_answer():
    caveats = build_caveats(
        confidence="high",
        structured=True,
        done_reason="stop",
        completion_tokens=0,
        token_limit=64,
        uncertain="none",
        answer="   ",
    )
    assert "empty_answer" in caveats


def test_caveats_skips_none_uncertain():
    for label in ("none", "None", "n/a", "-"):
        caveats = build_caveats(
            confidence="high",
            structured=True,
            done_reason="stop",
            completion_tokens=5,
            token_limit=64,
            uncertain=label,
            answer="ok",
        )
        assert "uncertainty_declared" not in caveats
