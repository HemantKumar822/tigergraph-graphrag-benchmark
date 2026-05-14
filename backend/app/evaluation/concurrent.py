import asyncio
import logging
from typing import Tuple, Optional, Literal

from .llm_judge import evaluate_with_llm_judge
from .bertscore import calculate_bertscore

logger = logging.getLogger(__name__)

async def run_evaluations_concurrently(
    ground_truth: str,
    answer: str
) -> Tuple[Optional[Literal["PASS", "FAIL", "N/A"]], Optional[float]]:
    """
    Run LLM judge and BERTScore concurrently.
    If either fails, it returns None for that specific metric.
    
    Returns:
        Tuple of (judge_score, bert_score)
    """
    if not ground_truth or not answer:
        return None, None

    # BERTScore is CPU-bound and blocking, so we run it in a separate thread.
    async def safe_bertscore():
        try:
            return await asyncio.to_thread(calculate_bertscore, answer, ground_truth)
        except Exception as e:
            logger.error(f"Concurrent BERTScore failed: {e}")
            return None

    async def safe_llm_judge():
        try:
            return await evaluate_with_llm_judge(ground_truth=ground_truth, student_answer=answer)
        except Exception as e:
            logger.error(f"Concurrent LLM Judge failed: {e}")
            return "N/A"

    # gather both tasks concurrently
    # return_exceptions=True prevents one from killing the other
    results = await asyncio.gather(
        safe_llm_judge(),
        safe_bertscore(),
        return_exceptions=True
    )

    judge_result = results[0] if not isinstance(results[0], BaseException) else "N/A"
    bert_result = results[1] if not isinstance(results[1], BaseException) else None

    return judge_result, bert_result
