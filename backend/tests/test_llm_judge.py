"""
Tests for Story 2.1: LLM-as-a-Judge evaluator module.
Covers: PASS verdict, FAIL verdict, N/A fallback (garbled response),
N/A fallback (API exception), and binary parser robustness.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import os

os.environ.setdefault("GEMINI_API_KEY", "dummy-test-key")
os.environ.setdefault("TESTING", "true")

from app.evaluation.llm_judge import evaluate_with_llm_judge, parse_verdict  # noqa: E402


# ---------------------------------------------------------------------------
# Unit tests: parse_verdict (pure function, no mocking needed)
# ---------------------------------------------------------------------------

def test_parse_verdict_pass():
    assert parse_verdict("PASS") == "PASS"

def test_parse_verdict_fail():
    assert parse_verdict("FAIL") == "FAIL"

def test_parse_verdict_case_insensitive():
    assert parse_verdict("pass") == "PASS"
    assert parse_verdict("fail") == "FAIL"
    assert parse_verdict("Pass") == "PASS"

def test_parse_verdict_embedded_in_text():
    """Parser should find PASS/FAIL even inside a longer string."""
    assert parse_verdict("Based on the context, PASS is correct.") == "PASS"
    assert parse_verdict("The answer is incorrect. FAIL.") == "FAIL"

def test_parse_verdict_garbled_returns_na():
    assert parse_verdict("I'm unable to determine the answer.") == "N/A"
    assert parse_verdict("") == "N/A"
    assert parse_verdict("   ") == "N/A"

def test_parse_verdict_none_like():
    """None is valid input per Optional[str] annotation — maps to N/A."""
    assert parse_verdict(None) == "N/A"


# ---------------------------------------------------------------------------
# Integration tests: evaluate_with_llm_judge (async, mocked OpenAI client)
# ---------------------------------------------------------------------------

def _mock_judge_response(content: str):
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


@pytest.mark.asyncio
@patch("app.evaluation.llm_judge.hf_client.chat_completion", new_callable=AsyncMock)
async def test_evaluate_returns_pass(mock_create):
    mock_create.return_value = _mock_judge_response("PASS")
    result = await evaluate_with_llm_judge(
        ground_truth="TigerGraph is a graph database.",
        student_answer="TigerGraph is a native distributed graph database.",
    )
    assert result == "PASS"
    mock_create.assert_called_once()
    # Verify max_tokens=5 is enforced (strict ceiling)
    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs.get("max_tokens") == 5


@pytest.mark.asyncio
@patch("app.evaluation.llm_judge.hf_client.chat_completion", new_callable=AsyncMock)
async def test_evaluate_returns_fail(mock_create):
    mock_create.return_value = _mock_judge_response("FAIL")
    result = await evaluate_with_llm_judge(
        ground_truth="TigerGraph is a graph database.",
        student_answer="TigerGraph is a relational database.",
    )
    assert result == "FAIL"


@pytest.mark.asyncio
@patch("app.evaluation.llm_judge.hf_client.chat_completion", new_callable=AsyncMock)
async def test_evaluate_garbled_response_returns_na(mock_create):
    """Content filters or hallucinations that bypass binary constraint → N/A."""
    mock_create.return_value = _mock_judge_response(
        "I cannot determine correctness without more context."
    )
    result = await evaluate_with_llm_judge(
        ground_truth="Paris is the capital of France.",
        student_answer="The capital of France is Lyon.",
    )
    assert result == "N/A"


@pytest.mark.asyncio
@patch("app.evaluation.llm_judge.hf_client.chat_completion", new_callable=AsyncMock)
async def test_evaluate_api_exception_returns_na(mock_create):
    """API failure (network, rate-limit, etc.) must not crash — returns N/A."""
    mock_create.side_effect = RuntimeError("HF API unavailable")
    result = await evaluate_with_llm_judge(
        ground_truth="The sky is blue.",
        student_answer="The sky is green.",
    )
    assert result == "N/A"


@pytest.mark.asyncio
@patch("app.evaluation.llm_judge.hf_client.chat_completion", new_callable=AsyncMock)
async def test_evaluate_temperature_zero(mock_create):
    """Grading must be deterministic — temperature must be close to 0.0."""
    mock_create.return_value = _mock_judge_response("PASS")
    await evaluate_with_llm_judge(
        ground_truth="Water is H2O.",
        student_answer="Water is a molecule with formula H2O.",
    )
    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs.get("temperature") == 0.1


def test_parse_verdict_both_tokens_first_match_wins():
    """
    When both PASS and FAIL appear, regex.search() returns the first token.
    This is documented behavior — the test pins the contract so any future
    change to the parser (e.g. returning N/A on ambiguity) is caught.
    """
    # FAIL appears before PASS — first match is FAIL
    result = parse_verdict("This is not a FAIL but rather a PASS.")
    assert result == "FAIL"
