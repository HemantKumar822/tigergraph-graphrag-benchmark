import os
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample dense PDFs with good entity relationships for GraphRAG
PDF_URLS = {
    "Bitcoin_Whitepaper.pdf": "https://bitcoin.org/bitcoin.pdf",
    "Attention_Is_All_You_Need.pdf": "https://arxiv.org/pdf/1706.03762.pdf",
    "GraphRAG_Paper.pdf": "https://arxiv.org/pdf/2404.16130.pdf" 
}

def main():
    target_dir = os.path.join(os.path.dirname(__file__), "data", "raw_uploads")
    os.makedirs(target_dir, exist_ok=True)
    
    for filename, url in PDF_URLS.items():
        filepath = os.path.join(target_dir, filename)
        logger.info(f"Downloading {filename}...")
        try:
            headers = {"User-Agent": "TigerGraphBenchmark/1.0"}
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            with open(filepath, "wb") as f:
                f.write(response.content)
            logger.info(f"Successfully downloaded {filename}")
        except Exception as e:
            logger.error(f"Failed to download {filename}: {e}")

if __name__ == "__main__":
    main()
