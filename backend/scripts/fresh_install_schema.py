import sys
from pathlib import Path
from dotenv import load_dotenv
import pyTigerGraph as tg

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")

from app.core.config import settings

def fresh_init():
    conn = tg.TigerGraphConnection(
        host=settings.TG_HOSTNAME,
        username=settings.TG_USERNAME,
        password=settings.TG_PASSWORD,
        restppPort=settings.TG_RESTPP_PORT,
        gsPort=settings.TG_GSQL_PORT,
    )
    
    print("Dropping all and Executing Fresh Graph Definition...")
    gsql_script = f"""
    DROP ALL
    CREATE VERTEX Document (PRIMARY_ID id STRING, content STRING)
    CREATE VERTEX Entity (PRIMARY_ID name STRING, name STRING)
    CREATE DIRECTED EDGE HAS_ENTITY (FROM Document, TO Entity) WITH REVERSE_EDGE="reverse_HAS_ENTITY"
    CREATE GRAPH {settings.TG_GRAPH} (Document, Entity, HAS_ENTITY)
    """
    
    try:
        res = conn.gsql(gsql_script)
        print("GSQL Output:")
        print(res)
    except Exception as e:
        print(f"❌ Schema Init Error: {e}")

if __name__ == "__main__":
    fresh_init()
