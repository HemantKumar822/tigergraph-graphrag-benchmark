import os
import requests
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# A simple list of URLs pointing to high-quality connected text for the mock benchmark
# For a quick test, we will download a few complex documents (e.g., Apple and Microsoft 10-K proxy equivalents or Wikipedia articles)
URLS_TO_DOWNLOAD = {
    "apple_10k_sample.txt": "https://raw.githubusercontent.com/run-llama/graphrag_evaluation/main/data/apple_10k.txt",
    "microsoft_10k_sample.txt": "https://raw.githubusercontent.com/run-llama/graphrag_evaluation/main/data/microsoft_10k.txt",
    "nvidia_10k_sample.txt": "https://raw.githubusercontent.com/run-llama/graphrag_evaluation/main/data/nvidia_10k.txt",
}

# If those URLs don't exist, we fallback to pulling some dense wiki pages.
WIKI_PAGES = [
    "Artificial_intelligence",
    "Machine_learning",
    "Graph_database",
    "TigerGraph",
    "Supply_chain",
    "Semiconductor",
    "Cloud_computing"
]

def download_wiki(page_title, dest_folder):
    """Fallback: Downloads a wikipedia article as plain text"""
    url = f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=1&titles={page_title}&format=json"
    headers = {"User-Agent": "TigerGraphBenchmark/1.0 (test@example.com)"}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        pages = data.get("query", {}).get("pages", {})
        for page_id, page_info in pages.items():
            content = page_info.get("extract", "")
            if content:
                filepath = os.path.join(dest_folder, f"{page_title.lower()}.txt")
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                logger.info(f"Downloaded Wikipedia: {page_title} -> {filepath}")
    except Exception as e:
        logger.error(f"Failed to download Wikipedia: {page_title} - {e}")

def main():
    target_dir = os.path.join(os.path.dirname(__file__), "data", "raw_uploads")
    os.makedirs(target_dir, exist_ok=True)
    
    # Try downloading SEC samples via wiki fallback since external raw github links might be fragile in unknown environments.
    logger.info(f"Preparing to download dataset to {target_dir}")
    
    # Use Wikipedia fallback to be 100% resilient and fast for testing purposes.
    # We download 7 highly interconnected topics that provide a good graph structure.
    for page in WIKI_PAGES:
        download_wiki(page, target_dir)
        
    logger.info("Dataset retrieval complete. You can now run orchestration.")

if __name__ == "__main__":
    main()
