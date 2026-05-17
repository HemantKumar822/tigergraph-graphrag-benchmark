import re

with open("app/api/ingestion.py", "r", encoding="utf-8") as f:
    content = f.read()

# Add get_total_tokens to /stats endpoint
if "from app.pipelines.indexing_orchestrator import get_total_tokens" not in content:
    content = content.replace("from app.pipelines.graphrag import tg_conn", "from app.pipelines.graphrag import tg_conn\n    from app.pipelines.indexing_orchestrator import get_total_tokens\n    \n    total_tokens = get_total_tokens()")
    
    content = content.replace("\"vectors\": vector_count,", "\"tokens\": total_tokens,\n            \"vectors\": vector_count,")

    with open("app/api/ingestion.py", "w", encoding="utf-8") as f:
        f.write(content)
