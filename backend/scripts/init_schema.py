import sys
from pathlib import Path
from dotenv import load_dotenv
import pyTigerGraph as tg

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")

from app.core.config import settings

def init_schema():
    print("Connecting to TigerGraph to verify/create baseline benchmark schema...")
    
    kwargs = {
        "host": settings.TG_HOSTNAME,
        "graphname": settings.TG_GRAPH,
    }

    if settings.TG_AUTH_MODE == "token":
        kwargs.update({
            "apiToken": settings.TG_API_TOKEN,
            "tgCloud": settings.TG_USE_CLOUD,
            "sslPort": settings.TG_SSL_PORT,
        })
        if settings.TG_USERNAME: kwargs["username"] = settings.TG_USERNAME
        if settings.TG_PASSWORD: kwargs["password"] = settings.TG_PASSWORD
    else:
        kwargs.update({
            "username": settings.TG_USERNAME,
            "password": settings.TG_PASSWORD,
            "restppPort": settings.TG_RESTPP_PORT,
            "gsPort": settings.TG_GSQL_PORT,
        })
        
    conn = tg.TigerGraphConnection(**kwargs)
    
    if settings.TG_AUTH_MODE == "password_token" and settings.TG_SECRET:
        conn.getToken(settings.TG_SECRET)
        
    try:
        print("Fetching current schema...")
        schema = conn.getSchema()
        v_types = [v["Name"] for v in schema.get("VertexTypes", [])]
        e_types = [e["Name"] for e in schema.get("EdgeTypes", [])]
        
        needs_doc = "Document" not in v_types
        needs_ent = "Entity" not in v_types
        needs_edge = "HAS_ENTITY" not in e_types
        
        if not needs_doc and not needs_ent and not needs_edge:
            print("✅ Schema already contains Document, Entity, and HAS_ENTITY. Ready for ingest.")
            return

        print("Updating schema to add missing Benchmark requirements...")
        
        gsql_cmds = [f"USE GRAPH {settings.TG_GRAPH}"]
        
        if needs_doc:
            print("Creating Vertex Document...")
            gsql_cmds.append("CREATE VERTEX Document (PRIMARY_ID id STRING, content STRING) WITH STATS='OUTDEGREE_BY_EDGETYPE', PRIMARY_ID_AS_ATTRIBUTE='true'")
            
        if needs_ent:
            print("Creating Vertex Entity...")
            gsql_cmds.append("CREATE VERTEX Entity (PRIMARY_ID name STRING, name STRING) WITH STATS='OUTDEGREE_BY_EDGETYPE', PRIMARY_ID_AS_ATTRIBUTE='true'")
            
        if needs_edge:
            print("Creating Edge HAS_ENTITY...")
            gsql_cmds.append("CREATE DIRECTED EDGE HAS_ENTITY (FROM Document, TO Entity) WITH REVERSE_EDGE='reverse_HAS_ENTITY'")
            
        # Combine, build schema requires 'ADD VERTEX/EDGE' syntax if updating graph rather than during CREATE GRAPH
        gsql_update = f"""USE GRAPH {settings.TG_GRAPH}
        CREATE SCHEMA_CHANGE JOB add_benchmark_schema FOR GRAPH {settings.TG_GRAPH} {{
        """
        if needs_doc: gsql_update += "  ADD VERTEX Document (PRIMARY_ID id STRING, content STRING) WITH STATS='OUTDEGREE_BY_EDGETYPE', PRIMARY_ID_AS_ATTRIBUTE='true';\n"
        if needs_ent: gsql_update += "  ADD VERTEX Entity (PRIMARY_ID name STRING, name STRING) WITH STATS='OUTDEGREE_BY_EDGETYPE', PRIMARY_ID_AS_ATTRIBUTE='true';\n"
        if needs_edge: gsql_update += "  ADD DIRECTED EDGE HAS_ENTITY (FROM Document, TO Entity) WITH REVERSE_EDGE='reverse_HAS_ENTITY';\n"
        
        gsql_update += """}
        RUN SCHEMA_CHANGE JOB add_benchmark_schema
        DROP JOB add_benchmark_schema
        """
        
        print("Executing Schema Change Job via GSQL...")
        res = conn.gsql(gsql_update)
        print("GSQL Output:")
        print(res)
        print("✅ Schema installation sequence attempted. Verify progress in TigerGraph GraphStudio.")
        
    except Exception as e:
        print(f"❌ Schema Init Error: {e}")
        print("Note: Ensure your TigerGraph account has Admin permissions to execute GSQL Schema Changes.")

if __name__ == "__main__":
    init_schema()
