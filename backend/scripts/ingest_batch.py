import os
import glob
import asyncio
import sys

# Add the current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.pipelines.indexing_orchestrator import reindex_document

async def main():
    target_dir = os.path.join(os.path.dirname(__file__), "data", "raw_uploads")
    files = glob.glob(os.path.join(target_dir, "*.txt")) + glob.glob(os.path.join(target_dir, "*.pdf"))
    
    print(f"Found {len(files)} files to ingest. This will take a while...")
    
    for i, filepath in enumerate(files):
        filename = os.path.basename(filepath)
        print(f"[{i+1}/{len(files)}] Processing {filename}...")
        try:
            res = await reindex_document(filepath)
            status = res.get("status", "error")
            print(f" -> {status}: {res.get('chunks', 0)} chunks, {res.get('entities', 0)} entities")
        except Exception as e:
            print(f" -> ERROR processing {filename}: {e}")
            
if __name__ == "__main__":
    asyncio.run(main())
