import os
from dotenv import load_dotenv

load_dotenv()


def _csv_env(name: str, default: str) -> list[str]:
    raw = os.environ.get(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _hostname_env() -> str:
    return os.environ.get(
        "TG_HOSTNAME",
        os.environ.get("TG_HOST", "https://your-tigergraph-workspace.i.tgcloud.io"),
    )


def _graph_env() -> str:
    return os.environ.get(
        "TG_GRAPH",
        os.environ.get("TG_GRAPH_NAME", "MyGraph"),
    )


class Settings:
    PROJECT_NAME: str = "TigerGraph GraphRAG Benchmark API"
    GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")
    HF_TOKEN: str = os.environ.get("HF_TOKEN", "")
    TESTING: bool = os.environ.get("TESTING", "").lower() == "true"

    # TigerGraph / Savanna settings
    TG_HOSTNAME: str = _hostname_env()
    TG_GRAPH: str = _graph_env()
    TG_AUTH_MODE: str = os.environ.get("TG_AUTH_MODE", "token").strip().lower()
    TG_USERNAME: str = os.environ.get("TG_USERNAME", "")
    TG_PASSWORD: str = os.environ.get("TG_PASSWORD", "")
    TG_SECRET: str = os.environ.get("TG_SECRET", "")
    TG_API_TOKEN: str = os.environ.get("TG_API_TOKEN", "")
    TG_RESTPP_PORT: str = os.environ.get("TG_RESTPP_PORT", "14240")
    TG_GSQL_PORT: str = os.environ.get("TG_GSQL_PORT", "14240")
    TG_SSL_PORT: int = int(os.environ.get("TG_SSL_PORT", "14240"))
    TG_USE_CLOUD: bool = _bool_env("TG_USE_CLOUD", "tgcloud" in TG_HOSTNAME.lower())

    BACKEND_PORT: int = int(os.environ.get("BACKEND_PORT", "8080"))
    BACKEND_CORS_ORIGINS: list[str] = _csv_env(
        "BACKEND_CORS_ORIGINS",
        "http://localhost:3000,http://localhost:3001",
    )

    CHROMA_PERSIST_PATH: str = os.environ.get("CHROMA_PERSIST_PATH", "./data/chroma_db")
    DEFAULT_TOP_K: int = int(os.environ.get("DEFAULT_TOP_K", "5"))
    DEFAULT_NUM_HOPS: int = int(os.environ.get("DEFAULT_NUM_HOPS", "2"))

    # Official TigerGraph GraphRAG service integration.
    GRAPHRAG_SERVICE_ENABLED: bool = _bool_env("GRAPHRAG_SERVICE_ENABLED", False)
    GRAPHRAG_SERVICE_URL: str = os.environ.get("GRAPHRAG_SERVICE_URL", "http://localhost:8000")
    GRAPHRAG_SERVICE_GRAPH: str = os.environ.get("GRAPHRAG_SERVICE_GRAPH", TG_GRAPH)
    GRAPHRAG_SERVICE_AUTH_MODE: str = os.environ.get(
        "GRAPHRAG_SERVICE_AUTH_MODE",
        "basic",
    ).strip().lower()
    GRAPHRAG_SERVICE_USERNAME: str = os.environ.get(
        "GRAPHRAG_SERVICE_USERNAME",
        TG_USERNAME,
    )
    GRAPHRAG_SERVICE_PASSWORD: str = os.environ.get(
        "GRAPHRAG_SERVICE_PASSWORD",
        TG_PASSWORD,
    )
    GRAPHRAG_SERVICE_API_TOKEN: str = os.environ.get(
        "GRAPHRAG_SERVICE_API_TOKEN",
        TG_API_TOKEN,
    )
    GRAPHRAG_SERVICE_TIMEOUT_S: float = float(
        os.environ.get("GRAPHRAG_SERVICE_TIMEOUT_S", "90")
    )
    GRAPHRAG_SERVICE_RAG_METHOD: str = os.environ.get("GRAPHRAG_SERVICE_RAG_METHOD", "")
    GRAPHRAG_DIRECT_FALLBACK: bool = _bool_env("GRAPHRAG_DIRECT_FALLBACK", True)
    GRAPHRAG_LLM_PROVIDER: str = os.environ.get("GRAPHRAG_LLM_PROVIDER", "gemini").strip().lower()

    def has_real_tg_host(self) -> bool:
        return self.TG_HOSTNAME != "https://your-tigergraph-workspace.i.tgcloud.io"

    def has_direct_tg_credentials(self) -> bool:
        if self.TG_AUTH_MODE == "token":
            return bool(self.TG_API_TOKEN)
        if self.TG_AUTH_MODE == "secret":
            return bool(self.TG_SECRET)
        if self.TG_AUTH_MODE in {"password", "password_token"}:
            return bool(self.TG_USERNAME and self.TG_PASSWORD)
        if self.TG_AUTH_MODE == "anonymous":
            return True
        return bool(self.TG_USERNAME and self.TG_PASSWORD)

    def has_graphrag_service_auth(self) -> bool:
        if self.GRAPHRAG_SERVICE_AUTH_MODE == "none":
            return True
        if self.GRAPHRAG_SERVICE_AUTH_MODE == "bearer":
            return bool(self.GRAPHRAG_SERVICE_API_TOKEN)
        return bool(
            self.GRAPHRAG_SERVICE_USERNAME and self.GRAPHRAG_SERVICE_PASSWORD
        )


settings = Settings()
