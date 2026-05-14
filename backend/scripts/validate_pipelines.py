import argparse
import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")

from app.core.config import settings
from app.models.schemas import InferenceConfig, InferenceRequest
from app.pipelines.basic_rag import collection, run_basic_rag_inference
from app.pipelines.graphrag import run_graphrag_inference, tg_conn
from app.pipelines.llm_only import run_llm_only_inference


def readiness_report() -> dict:
    vector_count = None
    try:
        vector_count = collection.count() if collection else 0
    except Exception:
        vector_count = None

    return {
        "llm_only": {
            "ready": bool(settings.GEMINI_API_KEY),
            "reason": "GEMINI_API_KEY is required for live generation.",
        },
        "basic_rag": {
            "ready": bool(settings.GEMINI_API_KEY and collection is not None),
            "vector_count": vector_count,
            "reason": "Requires GEMINI_API_KEY and an initialized Chroma collection.",
        },
        "graph_rag": {
            "ready": bool(
                settings.GRAPHRAG_SERVICE_ENABLED or tg_conn is not None or settings.TESTING
            ),
            "service_enabled": settings.GRAPHRAG_SERVICE_ENABLED,
            "direct_connection_ready": tg_conn is not None,
            "reason": (
                "Requires the official GraphRAG service or a working TigerGraph direct connection."
            ),
        },
    }


async def run_live_validation(query: str, top_k: int, num_hops: int) -> dict:
    request = InferenceRequest(
        query=query,
        config=InferenceConfig(top_k=top_k, num_hops=num_hops, temperature=0.0, max_tokens=256),
    )

    results = {}
    pipelines = {
        "llm_only": run_llm_only_inference,
        "basic_rag": run_basic_rag_inference,
        "graph_rag": run_graphrag_inference,
    }

    for name, runner in pipelines.items():
        try:
            response = await runner(request)
            results[name] = {
                "status": "success",
                "answer_preview": response.answer[:160],
                "metrics": response.metrics.model_dump(by_alias=True),
            }
        except Exception as exc:
            results[name] = {"status": "error", "message": str(exc)}

    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check readiness or run live smoke validation for all three benchmark pipelines.",
    )
    parser.add_argument(
        "--mode",
        choices=["readiness", "live"],
        default="readiness",
        help="Readiness only or live pipeline execution.",
    )
    parser.add_argument(
        "--query",
        default="Explain how GraphRAG differs from basic vector RAG.",
        help="Prompt used for live validation.",
    )
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--num-hops", type=int, default=2)
    args = parser.parse_args()

    if args.mode == "readiness":
        print(json.dumps(readiness_report(), indent=2))
        return 0

    results = asyncio.run(run_live_validation(args.query, args.top_k, args.num_hops))
    print(json.dumps(results, indent=2))
    return 0 if all(item["status"] == "success" for item in results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
