from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.schemas import InferenceConfig, InferenceRequest
from app.pipelines import graphrag


class _DummyHTTPResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _DummyAsyncClient:
    def __init__(self, response: _DummyHTTPResponse):
        self._response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, json, headers, auth):
        return self._response


@pytest.mark.asyncio
async def test_graphrag_prefers_official_service(monkeypatch):
    monkeypatch.setattr(graphrag.settings, "GRAPHRAG_SERVICE_ENABLED", True)
    monkeypatch.setattr(graphrag.settings, "GRAPHRAG_DIRECT_FALLBACK", False)
    monkeypatch.setattr(graphrag.settings, "GRAPHRAG_SERVICE_GRAPH", "GraphRAGBenchmark")
    monkeypatch.setattr(graphrag.settings, "GRAPHRAG_SERVICE_AUTH_MODE", "none")
    monkeypatch.setattr(graphrag.settings, "GRAPHRAG_SERVICE_RAG_METHOD", "")
    monkeypatch.setattr(graphrag.httpx, "AsyncClient", lambda timeout: _DummyAsyncClient(
        _DummyHTTPResponse({"natural_language_response": "Service-generated answer"})
    ))

    request = InferenceRequest(
        query="Explain GraphRAG.",
        config=InferenceConfig(top_k=3, num_hops=2),
    )

    result = await graphrag.run_graphrag_inference(request)

    assert result.answer == "Service-generated answer"
    assert result.metrics.graph_traversal_latency_ms is not None
    assert result.metrics.total_latency_ms is not None


@pytest.mark.asyncio
async def test_graphrag_service_falls_back_to_direct_retrieval(monkeypatch):
    monkeypatch.setattr(graphrag.settings, "GRAPHRAG_SERVICE_ENABLED", True)
    monkeypatch.setattr(graphrag.settings, "GRAPHRAG_DIRECT_FALLBACK", True)
    monkeypatch.setattr(
        graphrag,
        "_query_official_graphrag_service",
        AsyncMock(side_effect=RuntimeError("service offline")),
    )
    monkeypatch.setattr(
        graphrag,
        "_retrieve_graph_context",
        lambda query, top_k, num_hops: ["Graph context chunk"],
    )

    mock_response = MagicMock()
    mock_response.text = "Fallback-generated answer"

    with patch(
        "app.pipelines.llm_only.model.generate_content_async",
        new=AsyncMock(return_value=mock_response),
    ):
        request = InferenceRequest(
            query="Explain GraphRAG.",
            config=InferenceConfig(top_k=3, num_hops=2),
        )
        result = await graphrag.run_graphrag_inference(request)

    assert result.answer == "Fallback-generated answer"
    assert result.metrics.graph_traversal_latency_ms is not None
    assert result.metrics.total_latency_ms is not None
