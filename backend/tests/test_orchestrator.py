"""
Tests for the /api/orchestrator/benchmark endpoint (Story 1.5).
Covers: happy-path concurrent execution, fault-isolation when one pipeline fails,
and validation error (422) on empty body.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock, AsyncMock
import os

os.environ.setdefault("GEMINI_API_KEY", "dummy-test-key")
os.environ.setdefault("TESTING", "true")

from main import app  # noqa: E402 — env must be set before import


def _mock_llm_response(answer: str = "LLM answer"):
    resp = MagicMock()
    resp.text = answer
    return resp


@pytest.mark.asyncio
@patch("google.generativeai.GenerativeModel.generate_content_async", new_callable=AsyncMock)
@patch("app.pipelines.basic_rag.collection")
async def test_benchmark_all_success(
    mock_collection, mock_llm_create
):
    """All three pipelines succeed → all three slots are 'success'."""
    mock_llm_create.return_value = _mock_llm_response("LLM answer")
    mock_collection.query.return_value = {"documents": [["doc1", "doc2"]]}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/orchestrator/benchmark",
            json={"query": "What is GraphRAG?", "config": {"temperature": 0.0, "maxTokens": 256}}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    results = body["data"]["results"]

    assert results["llmOnly"]["status"] == "success"
    assert results["basicRag"]["status"] == "success"
    assert results["graphRag"]["status"] == "success"

    # Verify camelCase metric fields present in all three
    for key in ("llmOnly", "basicRag", "graphRag"):
        assert "answer" in results[key]["data"]
        assert "metrics" in results[key]["data"]


@pytest.mark.asyncio
@patch("google.generativeai.GenerativeModel.generate_content_async", new_callable=AsyncMock)
@patch("app.pipelines.basic_rag.collection")
@patch("app.api.orchestrator.run_graphrag_inference", new_callable=AsyncMock)
async def test_benchmark_one_pipeline_fails_others_succeed(
    mock_graph_run, mock_collection, mock_llm_create
):
    """
    graphrag pipeline raises → its slot shows 'error', llm-only and
    basic-rag slots still show 'success'. Fault isolation verified.
    """
    mock_llm_create.return_value = _mock_llm_response("LLM answer")
    mock_graph_run.side_effect = RuntimeError("Simulated TigerGraph timeout")
    mock_collection.query.return_value = {"documents": [["doc1"]]}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/orchestrator/benchmark",
            json={"query": "Fault isolation test", "config": {"temperature": 0.0, "maxTokens": 128}}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    results = body["data"]["results"]

    # Sibling pipelines succeeded
    assert results["llmOnly"]["status"] == "success"
    assert results["basicRag"]["status"] == "success"
    # Failed pipeline carries error payload, not a 500
    assert results["graphRag"]["status"] == "error"
    assert "Simulated TigerGraph timeout" in results["graphRag"]["error"]


@pytest.mark.asyncio
async def test_benchmark_validation_error():
    """Empty body → 422, standard error envelope."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/orchestrator/benchmark", json={})
    assert response.status_code == 422


@pytest.mark.asyncio
@patch("app.api.orchestrator.run_llm_only_inference", new_callable=AsyncMock)
@patch("app.api.orchestrator.run_basic_rag_inference", new_callable=AsyncMock)
@patch("app.api.orchestrator.run_graphrag_inference", new_callable=AsyncMock)
async def test_benchmark_all_pipelines_fail(
    mock_graph, mock_rag, mock_llm
):
    """
    All three pipelines raise → overall endpoint returns 200 with all three
    slots in 'error' state rather than crashing with a 500.
    Validates that return_exceptions=True + _pipeline_result handles total failure.
    """
    mock_llm.side_effect = RuntimeError("LLM unavailable")
    mock_rag.side_effect = RuntimeError("ChromaDB unavailable")
    mock_graph.side_effect = RuntimeError("TigerGraph unavailable")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/orchestrator/benchmark",
            json={"query": "Total failure test", "config": {"temperature": 0.0, "maxTokens": 64}}
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    results = body["data"]["results"]

    assert results["llmOnly"]["status"] == "error"
    assert results["basicRag"]["status"] == "error"
    assert results["graphRag"]["status"] == "error"
    assert "LLM unavailable" in results["llmOnly"]["error"]
