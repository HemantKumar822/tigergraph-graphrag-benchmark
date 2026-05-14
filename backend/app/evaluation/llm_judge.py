"""
LLM-as-a-Judge evaluator module (Story 2.1).

Submits a generated answer alongside ground truth to an LLM judge that outputs
exactly PASS or FAIL. A regex parser safely maps any garbled response to "N/A"
so downstream numerical grading remains stable.
"""
import re
import logging
import os
from typing import Optional
from huggingface_hub import AsyncInferenceClient
from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Judge client (uses Hugging Face Inference API as required by hackathon)
# ---------------------------------------------------------------------------
hf_client = AsyncInferenceClient(
    token=os.environ.get("HF_TOKEN")
)

# ---------------------------------------------------------------------------
# Task 1: Grading prompt template
# ---------------------------------------------------------------------------
# The system prompt enforces binary output only. Any conversational filler or
# hedged language would cause the regex parser to return "N/A" safely.
_JUDGE_SYSTEM_PROMPT = (
    "You are a rigorous scientific evaluator assessing the factual accuracy of a student answer.\n"
    "Compare the student answer against the ground truth provided.\n"
    "Respond with EXACTLY one word: PASS if the student answer is factually correct and complete, "
    "or FAIL if it is incorrect, incomplete, or misleading.\n"
    "Do NOT include any explanation, punctuation, or additional words. Only output PASS or FAIL."
)

_JUDGE_USER_TEMPLATE = (
    "Ground Truth:\n{ground_truth}\n\n"
    "Student Answer:\n{student_answer}\n\n"
    "Verdict:"
)

# ---------------------------------------------------------------------------
# Task 3: Validation parser
# ---------------------------------------------------------------------------
_VERDICT_PATTERN = re.compile(r"\b(PASS|FAIL)\b", re.IGNORECASE)


def parse_verdict(raw_response: Optional[str]) -> str:
    """
    Extract PASS or FAIL from the judge's raw response string.
    Returns the canonical uppercase token, or "N/A" if neither is found.
    This prevents downstream crashes from content-filter refusals or
    unexpected model hallucinations.
    """
    if not raw_response:
        return "N/A"
    match = _VERDICT_PATTERN.search(raw_response)
    if match:
        return match.group(1).upper()
    logger.warning(
        f"LLM judge returned unexpected output (will resolve to N/A): {raw_response!r}"
    )
    return "N/A"


# ---------------------------------------------------------------------------
# Task 2: Request wrapper
# ---------------------------------------------------------------------------
async def evaluate_with_llm_judge(
    ground_truth: str,
    student_answer: str,
    model: str = "meta-llama/Meta-Llama-3-8B-Instruct",
    temperature: float = 0.1,
) -> str:
    """
    Submit a (ground_truth, student_answer) pair to the LLM judge and return
    a verdict of "PASS", "FAIL", or "N/A".

    Args:
        ground_truth:   The reference/expected answer.
        student_answer: The generated answer being graded.
        model:          Judge model ID. Defaults to meta-llama/Meta-Llama-3-8B-Instruct.
        temperature:    Sampling temperature. 0.0 for deterministic grading.

    Returns:
        "PASS" | "FAIL" | "N/A"
    """
    user_message = _JUDGE_USER_TEMPLATE.format(
        ground_truth=ground_truth,
        student_answer=student_answer,
    )

    try:
        response = await hf_client.chat_completion(
            model=model,
            messages=[
                {"role": "system", "content": _JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=temperature if temperature > 0 else 0.1,
            max_tokens=5,  # Strict ceiling — we only need one word
        )
        raw = response.choices[0].message.content or ""
    except Exception as e:
        logger.error(f"LLM judge API call failed: {e}")
        return "N/A"

    return parse_verdict(raw)
