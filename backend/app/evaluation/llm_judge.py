"""
LLM-as-a-Judge evaluator module (Story 2.1).

Submits a generated answer alongside ground truth to an LLM judge that outputs
exactly PASS or FAIL. A regex parser safely maps any garbled response to "N/A"
so downstream numerical grading remains stable.
"""
import re
import logging
import os
import asyncio
import random
from typing import Optional
import google.generativeai as genai

logger = logging.getLogger(__name__)

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
# Using Gemini to ensure extreme stability instead of HuggingFace rate limits.
# ---------------------------------------------------------------------------
async def evaluate_with_llm_judge(
    ground_truth: str,
    student_answer: str,
    model: str = "gemini-3.1-flash-lite",
    temperature: float = 0.0,
) -> str:
    """
    Submit a (ground_truth, student_answer) pair to the LLM judge and return
    a verdict of "PASS", "FAIL", or "N/A" using Gemini API for stability.
    """
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    judge_model = genai.GenerativeModel(model)

    user_message = _JUDGE_USER_TEMPLATE.format(
        ground_truth=ground_truth,
        student_answer=student_answer,
    )
    
    # Prepend the system prompt instructions directly into the message for Gemini flash-lite to obey
    full_prompt = f"{_JUDGE_SYSTEM_PROMPT}\n\n{user_message}"

    max_attempts = 4
    for attempt in range(max_attempts):
        try:
            response = await judge_model.generate_content_async(
                full_prompt,
                generation_config={"temperature": temperature}
            )
            raw = response.text or ""
            return parse_verdict(raw)
        except Exception as e:
            err_str = str(e)
            is_429 = "429" in err_str or "Quota" in err_str or "ResourceExhausted" in err_str or "limit" in err_str.lower() or "503" in err_str
            
            if is_429 and attempt < max_attempts - 1:
                sleep_sec = (1.5 * (2 ** attempt)) + (random.uniform(0.5, 1.5))
                logger.warning(f"⚠️ [Judge Rate Limit (429)] Quota saturated. Retrying in {sleep_sec:.2f}s (Attempt {attempt + 1}/{max_attempts})...")
                await asyncio.sleep(sleep_sec)
                continue
                
            logger.error(f"LLM judge API call failed after {attempt + 1} attempts: {e}")
            return "N/A"

    return "N/A"
