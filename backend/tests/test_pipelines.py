import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, MagicMock, AsyncMock
import os

# Set dummy key for testing so module import doesn't fail
os.environ["GEMINI_API_KEY"] = "dummy-test-key"
os.environ["TESTING"] = "true"

from main import app

@pytest.mark.asyncio
async def test_llm_only_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        
        # Mock the Gemini client
        mock_response = MagicMock()
        mock_response.text = "This is a mocked LLM response."
        
        with patch('google.generativeai.GenerativeModel.generate_content_async', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            response = await ac.post(
                "/api/pipeline/llm-only",
                json={
                    "query": "Tell me a joke.",
                    "config": {"temperature": 0.5, "maxTokens": 50}
                }
            )
            
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        
        # Check standard envelope and response structure
        result = data["data"]
        assert "answer" in result
        assert result["answer"] == "This is a mocked LLM response."
        
        metrics = result["metrics"]
        assert "promptTokens" in metrics
        assert "completionTokens" in metrics
        assert "latencyMs" in metrics
        assert isinstance(metrics["latencyMs"], float)
        assert metrics["promptTokens"] > 0

@pytest.mark.asyncio
async def test_llm_only_endpoint_validation_error():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/pipeline/llm-only", json={})
        assert response.status_code == 422

@pytest.mark.asyncio
@patch("app.pipelines.basic_rag.collection")
@patch("google.generativeai.GenerativeModel.generate_content_async", new_callable=AsyncMock)
async def test_basic_rag_endpoint(mock_create, mock_collection):
    # Mock collection query
    mock_collection.query.return_value = {
        "documents": [["Doc 1", "Doc 2"]]
    }
    
    mock_response = MagicMock()
    mock_response.text = "ChromaDB is a vector database."
    mock_create.return_value = mock_response

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/pipeline/basic-rag", json={
            "query": "What is ChromaDB?",
            "config": {"temperature": 0.5, "maxTokens": 100}
        })
        
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "answer" in data["data"]
    assert "metrics" in data["data"]
    metrics = data["data"]["metrics"]
    assert "semanticSearchLatencyMs" in metrics
    assert "totalLatencyMs" in metrics
    assert metrics["semanticSearchLatencyMs"] is not None
    assert metrics["totalLatencyMs"] is not None

@pytest.mark.asyncio
@patch("google.generativeai.GenerativeModel.generate_content_async", new_callable=AsyncMock)
async def test_graphrag_endpoint(mock_create):
    mock_response = MagicMock()
    mock_response.text = "Multi-hop traversal gives deeper insights."
    mock_create.return_value = mock_response

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/pipeline/graphrag", json={
            "query": "How does GraphRAG work?",
            "config": {"temperature": 0.5, "maxTokens": 100, "topK": 10, "numHops": 3}
        })
        
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "answer" in data["data"]
    assert "metrics" in data["data"]
    metrics = data["data"]["metrics"]
    assert "graphTraversalLatencyMs" in metrics
    assert "totalLatencyMs" in metrics
    assert metrics["graphTraversalLatencyMs"] is not None
    assert metrics["totalLatencyMs"] is not None

@pytest.mark.asyncio
async def test_graphrag_endpoint_validation_error():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/pipeline/graphrag", json={})
        assert response.status_code == 422
