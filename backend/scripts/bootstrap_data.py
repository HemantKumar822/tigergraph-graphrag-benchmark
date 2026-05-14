import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")

from app.pipelines.indexing_orchestrator import reindex_document

async def bootstrap_all():
    data_dir = BACKEND_DIR / "data" / "raw_uploads"
    
    if not data_dir.exists():
        print(f"ERROR: Folder {data_dir} does not exist. Run 'python download_data.py' first.")
        return

    files = [f for f in os.listdir(data_dir) if f.endswith(".txt") or f.endswith(".pdf")]
    
    if not files:
        print("ERROR: No files found in raw_uploads directory. Run 'python download_data.py' first.")
        return

    print(f"Commencing automated bootstrap sequence for {len(files)} source documents.")
    print("Priming TigerGraph and Chroma Vector index in tandem...\n")
    
    for file_name in files:
        full_path = str(data_dir / file_name)
        print(f"Processing: {file_name}")
        
        try:
            result = await reindex_document(full_path)
            if result.get("status") == "success":
                print(f"   SUCCESS: Injected {result['chunks']} chunks, mapped {result['entities']} graph relationships.")
            else:
                print(f"   WARNING: Ingestion Warning: {result.get('message', 'Unknown error')}")
        except Exception as e:
            print(f"   FATAL: failure indexing {file_name}: {e}")
            
    print("\nBootstrap Sequence Completed. Databases are now armed with live data.")

if __name__ == "__main__":
    asyncio.run(bootstrap_all())
