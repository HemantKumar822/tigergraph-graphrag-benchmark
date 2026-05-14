import pytest
import asyncio
from unittest.mock import patch
from app.evaluation.concurrent import run_evaluations_concurrently

@pytest.mark.asyncio
@patch("app.evaluation.concurrent.evaluate_with_llm_judge")
@patch("app.evaluation.concurrent.calculate_bertscore")
async def test_run_evaluations_concurrently_success(mock_bertscore, mock_judge):
    mock_judge.return_value = "PASS"
    mock_bertscore.return_value = 0.95
    
    judge_score, bert_score = await run_evaluations_concurrently("ground truth", "answer")
    
    assert judge_score == "PASS"
    assert bert_score == 0.95
    mock_judge.assert_called_once_with(ground_truth="ground truth", student_answer="answer")
    mock_bertscore.assert_called_once_with("answer", "ground truth")

@pytest.mark.asyncio
@patch("app.evaluation.concurrent.evaluate_with_llm_judge")
@patch("app.evaluation.concurrent.calculate_bertscore")
async def test_run_evaluations_concurrently_failures(mock_bertscore, mock_judge):
    mock_judge.side_effect = Exception("OpenAI API down")
    mock_bertscore.side_effect = Exception("Out of memory")
    
    judge_score, bert_score = await run_evaluations_concurrently("ground truth", "answer")
    
    assert judge_score == "N/A"
    assert bert_score is None

@pytest.mark.asyncio
async def test_run_evaluations_empty_input():
    judge_score, bert_score = await run_evaluations_concurrently("", "answer")
    assert judge_score is None
    assert bert_score is None
