import os
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_category_pages(category, max_pages=100):
    url = "https://en.wikipedia.org/w/api.php"
    pages = []
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": category,
        "cmlimit": 500,
        "format": "json"
    }
    headers = {"User-Agent": "TigerGraphBenchmark/1.0 (test@example.com)"}
    try:
        while len(pages) < max_pages:
            response = requests.get(url, params=params, headers=headers).json()
            for member in response.get("query", {}).get("categorymembers", []):
                if member["ns"] == 0:
                    pages.append(member["title"])
            if "continue" in response and len(pages) < max_pages:
                params.update(response["continue"])
            else:
                break
    except Exception as e:
        logger.error(e)
    return pages[:max_pages]

def download_pages(titles, dest_folder):
    url = "https://en.wikipedia.org/w/api.php"
    headers = {"User-Agent": "TigerGraphBenchmark/1.0 (test@example.com)"}
    total = 0
    for i in range(0, len(titles), 20):
        chunk = titles[i:i+20]
        params = {
            "action": "query",
            "prop": "extracts",
            "explaintext": 1,
            "titles": "|".join(chunk),
            "format": "json"
        }
        try:
            response = requests.get(url, params=params, headers=headers).json()
            for page_id, page_info in response.get("query", {}).get("pages", {}).items():
                content = page_info.get("extract", "")
                title = page_info.get("title", f"doc").replace(" ", "_").replace("/", "_")
                if content and len(content) > 1000:
                    with open(os.path.join(dest_folder, f"{title}.txt"), "w", encoding="utf-8") as f:
                        f.write(content)
                    total += 1
        except Exception as e:
            pass
    return total

if __name__ == "__main__":
    target_dir = os.path.join(os.path.dirname(__file__), "data", "raw_uploads")
    os.makedirs(target_dir, exist_ok=True)
    
    categories = [
        "Category:Artificial_intelligence",
        "Category:Machine_learning",
        "Category:Software_engineering",
        "Category:Databases",
        "Category:Cloud_computing",
        "Category:Data_management",
        "Category:Big_data",
        "Category:Natural_language_processing",
        "Category:Computer_vision",
        "Category:Deep_learning",
        "Category:Information_retrieval",
        "Category:Graph_databases",
        "Category:NoSQL",
        "Category:Distributed_computing_architecture",
        "Category:Data_structures"
    ]
    
    all_titles = set()
    for cat in categories:
        logger.info(f"Fetching titles for {cat}...")
        titles = get_category_pages(cat, max_pages=200)
        all_titles.update(titles)
        
    logger.info(f"Total unique titles to download: {len(all_titles)}. Starting download...")
    downloaded = download_pages(list(all_titles), target_dir)
    logger.info(f"Finished downloading {downloaded} extensive documents.")
