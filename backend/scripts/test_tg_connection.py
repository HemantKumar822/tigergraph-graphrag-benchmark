import sys
from pathlib import Path

from dotenv import load_dotenv
import pyTigerGraph as tg


BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(BACKEND_DIR / ".env")
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings


def _build_connection() -> tg.TigerGraphConnection:
    kwargs = {
        "host": settings.TG_HOSTNAME,
        "graphname": settings.TG_GRAPH,
    }

    if settings.TG_AUTH_MODE == "token":
        kwargs.update(
            {
                "apiToken": settings.TG_API_TOKEN,
                "tgCloud": settings.TG_USE_CLOUD,
                "sslPort": settings.TG_SSL_PORT,
            }
        )
        if settings.TG_USERNAME:
            kwargs["username"] = settings.TG_USERNAME
        if settings.TG_PASSWORD:
            kwargs["password"] = settings.TG_PASSWORD
        return tg.TigerGraphConnection(**kwargs)

    # EXPLICIT SECRET SUPPORT: If user provided a Secret, initialize properly!
    if (settings.TG_AUTH_MODE in ["secret", "password_token"]) and settings.TG_SECRET:
        print(f"Directly asserting secret-based connection flow using Secret: {settings.TG_SECRET[:5]}***")
        kwargs.update({
            "gsqlSecret": settings.TG_SECRET,
            "tgCloud": settings.TG_USE_CLOUD,
            "sslPort": settings.TG_SSL_PORT,
        })
        conn = tg.TigerGraphConnection(**kwargs)
        print("Requesting Session Token via Secret...")
        token_res = conn.getToken(settings.TG_SECRET)
        conn.apiToken = token_res[0] if isinstance(token_res, tuple) else token_res
        
        # THE BUG FIX: Manually force the library's stale HTTP cache to refresh its headers!
        print("Patching stale library auth cache...")
        conn._refresh_auth_headers()
        
        print("SUCCESS: Session Token generated & Cached!")
        return conn

    kwargs.update(
        {
            "username": settings.TG_USERNAME,
            "password": settings.TG_PASSWORD,
            "restppPort": settings.TG_RESTPP_PORT,
            "gsPort": settings.TG_GSQL_PORT,
        }
    )
    conn = tg.TigerGraphConnection(**kwargs)
    return conn


def test_connection():
    print("Testing connection to TigerGraph Savanna...")
    try:
        conn = _build_connection()
        print(f"Auth mode: {settings.TG_AUTH_MODE}")
        print(f"Workspace: {settings.TG_HOSTNAME}")
        print(f"Graph: {settings.TG_GRAPH}")

        print("Running echo...")
        res = conn.echo()
        print(f"SUCCESS: Connection Echo: {res}")

        print("Fetching schema...")
        schema = conn.getSchema()
        v_types = [v["Name"] for v in schema.get("VertexTypes", [])]
        e_types = [e["Name"] for e in schema.get("EdgeTypes", [])]

        print(f"Vertex types: {len(v_types)}")
        if v_types:
            print(f"Sample vertices: {', '.join(v_types[:5])}")

        print(f"Edge types: {len(e_types)}")
        if e_types:
            print(f"Sample edges: {', '.join(e_types[:5])}")

        print("FINAL VERDICT: direct TigerGraph access is working.")
    except Exception as e:
        print(f"ERROR: Connection Failed: {e}")
        print("Tip: run `python backend/scripts/validate_pipelines.py --mode readiness` for a full setup report.")


if __name__ == "__main__":
    test_connection()
