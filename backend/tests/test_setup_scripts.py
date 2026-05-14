import os

from scripts.render_graphrag_config import build_server_config, validate_required_settings


def test_render_graphrag_config_builds_token_based_config(monkeypatch):
    monkeypatch.setenv("TG_HOSTNAME", "https://example.i.tgcloud.io")
    monkeypatch.setenv("TG_AUTH_MODE", "token")
    monkeypatch.setenv("TG_API_TOKEN", "token-123")
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")
    monkeypatch.setenv("GRAPHRAG_LLM_PROVIDER", "gemini")

    config = build_server_config()

    assert config["db_config"]["hostname"] == "https://example.i.tgcloud.io"
    assert config["db_config"]["apiToken"] == "token-123"
    assert (
        config["llm_config"]["authentication_configuration"]["GOOGLE_API_KEY"]
        == "gemini-key"
    )


def test_render_graphrag_config_reports_missing_required_settings(monkeypatch):
    for key in (
        "TG_HOSTNAME",
        "TG_HOST",
        "TG_AUTH_MODE",
        "TG_API_TOKEN",
        "TG_USERNAME",
        "TG_PASSWORD",
        "GEMINI_API_KEY",
        "OPENAI_API_KEY",
        "GRAPHRAG_LLM_PROVIDER",
    ):
        monkeypatch.delenv(key, raising=False)

    monkeypatch.setenv("TG_AUTH_MODE", "token")
    missing = validate_required_settings()

    assert "TG_HOSTNAME or TG_HOST" in missing
    assert "TG_API_TOKEN" in missing
    assert "GEMINI_API_KEY" in missing
