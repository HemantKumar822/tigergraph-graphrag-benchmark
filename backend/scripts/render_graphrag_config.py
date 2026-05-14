import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ENV = REPO_ROOT / "backend" / ".env"
DEFAULT_OUTPUT = REPO_ROOT / "graphrag" / "configs" / "server_config.json"


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _non_empty(value: str | None, fallback: str) -> str:
    if value and value.strip():
        return value.strip()
    return fallback


def _db_config() -> dict:
    host = _non_empty(
        os.environ.get("TG_HOSTNAME") or os.environ.get("TG_HOST"),
        "https://your-tigergraph-workspace.i.tgcloud.io",
    )
    auth_mode = _non_empty(os.environ.get("TG_AUTH_MODE"), "token").lower()

    db_config = {
        "hostname": host,
        "restppPort": _non_empty(os.environ.get("TG_RESTPP_PORT"), "14240"),
        "gsPort": _non_empty(os.environ.get("TG_GSQL_PORT"), "14240"),
        "getToken": auth_mode == "password_token",
        "default_timeout": 300,
        "default_mem_threshold": 5000,
        "default_thread_limit": 8,
    }

    if os.environ.get("TG_USERNAME"):
        db_config["username"] = os.environ["TG_USERNAME"]
    if os.environ.get("TG_PASSWORD"):
        db_config["password"] = os.environ["TG_PASSWORD"]
    if os.environ.get("TG_API_TOKEN"):
        db_config["apiToken"] = os.environ["TG_API_TOKEN"]

    return db_config


def _llm_config() -> dict:
    provider = _non_empty(os.environ.get("GRAPHRAG_LLM_PROVIDER"), "gemini").lower()

    if provider == "openai":
        return {
            "token_limit": 0,
            "authentication_configuration": {
                "OPENAI_API_KEY": _non_empty(
                    os.environ.get("OPENAI_API_KEY"),
                    "YOUR_LLM_API_KEY_HERE",
                )
            },
            "embedding_service": {
                "model_name": "text-embedding-3-small",
                "embedding_model_service": "openai",
            },
            "completion_service": {
                "llm_service": "openai",
                "llm_model": "gpt-4.1-mini",
                "model_kwargs": {"temperature": 0},
                "prompt_path": "./common/prompts/openai_gpt4/",
            },
            "multimodal_service": {
                "llm_service": "openai",
                "llm_model": "gpt-4o-mini",
                "model_kwargs": {"temperature": 0},
            },
        }

    return {
        "token_limit": 0,
        "authentication_configuration": {
            "GOOGLE_API_KEY": _non_empty(
                os.environ.get("GEMINI_API_KEY"),
                "YOUR_LLM_API_KEY_HERE",
            )
        },
        "embedding_service": {
            "embedding_model_service": "genai",
            "model_name": "models/gemini-embedding-exp-03-07",
            "dimensions": 1536,
        },
        "completion_service": {
            "llm_service": "genai",
            "llm_model": "gemini-2.5-flash",
            "model_kwargs": {"temperature": 0},
            "prompt_path": "./common/prompts/google_gemini/",
        },
        "multimodal_service": {
            "llm_service": "openai",
            "llm_model": "gpt-4o-mini",
            "model_kwargs": {"temperature": 0},
        },
    }


def build_server_config() -> dict:
    return {
        "db_config": _db_config(),
        "graphrag_config": {
            "reuse_embedding": True,
            "ecc": "http://graphrag-ecc:8001",
            "chat_history_api": "http://chat-history:8002",
            "chunker_config": {},
        },
        "llm_config": _llm_config(),
        "chat_config": {
            "apiPort": "8002",
            "dbPath": "chats.db",
            "dbLogPath": "db.log",
            "logPath": "requestLogs.jsonl",
            "conversationAccessRoles": ["superuser", "globaldesigner"],
        },
    }


def validate_required_settings() -> list[str]:
    missing = []
    if not (os.environ.get("TG_HOSTNAME") or os.environ.get("TG_HOST")):
        missing.append("TG_HOSTNAME or TG_HOST")

    auth_mode = _non_empty(os.environ.get("TG_AUTH_MODE"), "token").lower()
    if auth_mode == "token" and not os.environ.get("TG_API_TOKEN"):
        missing.append("TG_API_TOKEN")
    if auth_mode in {"password", "password_token"}:
        if not os.environ.get("TG_USERNAME"):
            missing.append("TG_USERNAME")
        if not os.environ.get("TG_PASSWORD"):
            missing.append("TG_PASSWORD")

    provider = _non_empty(os.environ.get("GRAPHRAG_LLM_PROVIDER"), "gemini").lower()
    if provider == "openai" and not os.environ.get("OPENAI_API_KEY"):
        missing.append("OPENAI_API_KEY")
    if provider != "openai" and not os.environ.get("GEMINI_API_KEY"):
        missing.append("GEMINI_API_KEY")

    return missing


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Render a fresh TigerGraph GraphRAG server_config.json from backend/.env",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Where to write the generated server_config.json",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only validate required environment variables without writing a file.",
    )
    args = parser.parse_args()

    load_dotenv(BACKEND_ENV)

    missing = validate_required_settings()
    if missing:
        print("Missing required settings:")
        for item in missing:
            print(f"- {item}")
        if args.check:
            return 1

    if args.check:
        print("Environment looks complete for GraphRAG configuration generation.")
        return 0

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    config = build_server_config()
    output_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote fresh GraphRAG config to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
