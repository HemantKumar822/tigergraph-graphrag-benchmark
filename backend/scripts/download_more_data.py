import os
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add SEC 10-k filings and heavy manuals to easily cross 2-3 million tokens
MASSIVE_URLS = {
    "Apple_10k.txt": "https://raw.githubusercontent.com/run-llama/graphrag_evaluation/main/data/apple_10k.txt",
    "Microsoft_10k.txt": "https://raw.githubusercontent.com/run-llama/graphrag_evaluation/main/data/microsoft_10k.txt",
    "Nvidia_10k.txt": "https://raw.githubusercontent.com/run-llama/graphrag_evaluation/main/data/nvidia_10k.txt",
    "Tesla_10k.txt": "https://raw.githubusercontent.com/run-llama/graphrag_evaluation/main/data/tesla_10k.txt",
    "Uber_10k.txt": "https://raw.githubusercontent.com/run-llama/graphrag_evaluation/main/data/uber_10k.txt"
}

def main():
    target_dir = os.path.join(os.path.dirname(__file__), "data", "raw_uploads")
    os.makedirs(target_dir, exist_ok=True)
    
    for filename, url in MASSIVE_URLS.items():
        filepath = os.path.join(target_dir, filename)
        logger.info(f"Downloading {filename}...")
        try:
            # Note: Using raw GitHub URLs, these are massive plain text financial and strategy blocks.
            headers = {"User-Agent": "TigerGraphBenchmark/1.0"}
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                with open(filepath, "wb") as f:
                    f.write(response.content)
                logger.info(f"Successfully downloaded {filename}")
        except Exception as e:
            logger.error(f"Failed to download {filename}: {e}")

if __name__ == "__main__":
    main()
