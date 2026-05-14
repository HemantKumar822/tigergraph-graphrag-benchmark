"""
Tests for Story 2.2: BERTScore Semantic Similarity Integration.
Tests extraction of F1 float values and failure handling.
"""
import pytest
import torch
from unittest.mock import patch, MagicMock
from app.evaluation.bertscore import calculate_bertscore

# ---------------------------------------------------------------------------
# Unit tests with Mocking
# ---------------------------------------------------------------------------

@patch("app.evaluation.bertscore.score")
def test_calculate_bertscore_success(mock_score):
    """Verify successful extraction of F1 tensor to rounded python float."""
    # Mock return tuple: (P_tensor, R_tensor, F1_tensor)
    # F1 score of 0.954321
    mock_score.return_value = (
        torch.tensor([0.9]), 
        torch.tensor([0.9]), 
        torch.tensor([0.954321])
    )
    
    score_val = calculate_bertscore("The cat sat", "The cat sat")
    
    assert isinstance(score_val, float)
    assert score_val == 0.9543  # Verify rounding to 4 decimal places
    mock_score.assert_called_once()
    
    # Verify passed model_type
    args, kwargs = mock_score.call_args
    assert kwargs["model_type"] == "distilbert-base-uncased"

@patch("app.evaluation.bertscore.score")
def test_calculate_bertscore_api_fail_returns_zero(mock_score):
    """Verify that when internal score function raises, wrapper returns 0.0 safely."""
    mock_score.side_effect = RuntimeError("CUDA out of memory")
    
    score_val = calculate_bertscore("some text", "other text")
    
    assert score_val == 0.0

def test_calculate_bertscore_empty_input_returns_zero():
    """Verify early return logic for None/empty inputs."""
    assert calculate_bertscore("", "reference") == 0.0
    assert calculate_bertscore("candidate", "") == 0.0
    assert calculate_bertscore(None, "ref") == 0.0

@patch("app.evaluation.bertscore.score")
def test_calculate_bertscore_clamping(mock_score):
    """Verify that scores below 0.0 or above 1.0 are clamped to the range boundary."""
    # Test negative clamp
    mock_score.return_value = (torch.tensor([0.]), torch.tensor([0.]), torch.tensor([-0.12]))
    assert calculate_bertscore("a", "b") == 0.0
    
    # Test overflow clamp
    mock_score.return_value = (torch.tensor([0.]), torch.tensor([0.]), torch.tensor([1.05]))
    assert calculate_bertscore("a", "b") == 1.0

