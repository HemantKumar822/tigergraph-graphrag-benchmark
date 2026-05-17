import re

with open("app/pipelines/indexing_orchestrator.py", "r", encoding="utf-8") as f:
    content = f.read()

# Make sure tiktoken is imported, if not, add it
if "import tiktoken" not in content:
    content = content.replace("import asyncio", "import asyncio\nimport tiktoken\nimport json")

meta_methods = """
META_FILE = os.path.join(os.getcwd(), "data", "ingestion_meta.json")

def get_total_tokens() -> int:
    if os.path.exists(META_FILE):
        try:
            with open(META_FILE, "r") as f:
                return json.load(f).get("total_tokens", 0)
        except:
            pass
    return 0

def add_tokens(count: int):
    current = get_total_tokens()
    os.makedirs(os.path.dirname(META_FILE), exist_ok=True)
    with open(META_FILE, "w") as f:
        json.dump({"total_tokens": current + count}, f)

def reset_tokens():
    if os.path.exists(META_FILE):
        os.remove(META_FILE)

def count_tokens_exact(text: str) -> int:
    try:
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except:
        return int(len(text) / 4) # fallback approximation
"""

if "def get_total_tokens" not in content:
    content = content.replace("logger = logging.getLogger(__name__)", "logger = logging.getLogger(__name__)\n\n" + meta_methods)


# Inside stream_reindex_document(file_path: str):
hook_idx_start = content.find("logger.info(f\"✅ [green]Extracted {len(text)} characters[/green] from document.\")")
insert_hook = """
    exact_tokens = await asyncio.to_thread(count_tokens_exact, text)
    await asyncio.to_thread(add_tokens, exact_tokens)
    logger.info(f"✅ [green]Extracted {len(text)} characters ({exact_tokens} tokens)[/green] from document.")
"""

if "exact_tokens =" not in content and hook_idx_start != -1:
    content = content.replace("logger.info(f\"✅ [green]Extracted {len(text)} characters[/green] from document.\")", insert_hook, 1)

# In clear_all_databases() -> Dict[str, Any]:
if "reset_tokens()" not in content:
    content = content.replace("logger.info(\"Initiating system-wide data clearance sequence...\")", "logger.info(\"Initiating system-wide data clearance sequence...\")\n    reset_tokens()")

with open("app/pipelines/indexing_orchestrator.py", "w", encoding="utf-8") as f:
    f.write(content)
