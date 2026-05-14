"""
BERTScore semantic similarity integration (Story 2.2).
Calculates deterministic numerical similarity between generated answer and ground truth.
Uses lightweight distilbert-base-uncased by default for local compute constraints.
"""
import logging
from typing import Optional
import torch
from bert_score import score

logger = logging.getLogger(__name__)

# Hardcoded default for hackathon constraints — much lighter than roberta-large.
# Weights automatically cached locally by transformers (~260MB).
DEFAULT_BERT_MODEL = "distilbert-base-uncased"

def calculate_bertscore(candidate: Optional[str], reference: Optional[str]) -> float:
    """
    Computes BERTScore F1 rescale value between a single candidate and reference pair.
    
    Args:
        candidate: Generated student answer text.
        reference: Ground truth reference text.
        
    Returns:
        Standard Python float of F1 score (unscaled for exact raw precision) in range [0, 1].
        Returns 0.0 if scoring fails.
    """
    if not candidate or not reference:
        logger.warning("Candidate or Reference empty; skipping BERTScore computation.")
        return 0.0
        
    try:
        # score expects lists of strings. rescale_with_baseline stretches 
        # scores to the full [0, 1] range for better dynamic visualization.
        P, R, F1 = score(
            [candidate], 
            [reference], 
            model_type=DEFAULT_BERT_MODEL,
            lang="en", 
            rescale_with_baseline=True,
            verbose=False
        )
        
        # F1 is a tensor containing the single similarity score.
        # item() converts single-element tensor to python scalar.
        # Clamp value to strictly honor the [0, 1] range constraint.
        score_val = float(F1.item())
        clamped_val = max(0.0, min(1.0, score_val))
        
        return round(clamped_val, 4)
        
    except Exception as e:
        logger.error(f"BERTScore calculation failed: {e}")
        return 0.0
