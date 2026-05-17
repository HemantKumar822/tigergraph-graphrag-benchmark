import os
import requests
import xml.etree.ElementTree as ET
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    target_dir = os.path.join(os.path.dirname(__file__), "data", "raw_uploads")
    os.makedirs(target_dir, exist_ok=True)
    
    # We will search Arxiv for deep, dense research papers on Graph Neural Networks, LLMs, and RAG.
    # We'll pull 40 massive papers to easily blow past the 2 Million token mark with just PDFs!
    query = 'all:"retrieval augmented generation" OR all:"graph neural networks" OR all:"large language models"'
    url = f'http://export.arxiv.org/api/query?search_query={query}&start=0&max_results=50'
    
    logger.info("Querying Arxiv for massive research PDFs...")
    response = requests.get(url)
    root = ET.fromstring(response.content)
    
    entries = root.findall('{http://www.w3.org/2005/Atom}entry')
    logger.info(f"Found {len(entries)} PDF candidates.")
    
    downloaded = 0
    for entry in entries:
        title_el = entry.find('{http://www.w3.org/2005/Atom}title')
        pdf_link_el = entry.find('{http://www.w3.org/2005/Atom}link[@title="pdf"]')
        
        if title_el is not None and pdf_link_el is not None:
            # Clean title for filesystem
            safe_title = "".join(c for c in title_el.text.replace('\n', ' ') if c.isalnum() or c in (' ', '_', '-')).strip().replace(' ', '_')
            pdf_url = pdf_link_el.attrib.get('href') + ".pdf"
            filepath = os.path.join(target_dir, f"{safe_title}.pdf")
            
            if not os.path.exists(filepath):
                logger.info(f"Downloading [{downloaded+1}/50]: {safe_title}.pdf ...")
                try:
                    pdf_res = requests.get(pdf_url, timeout=30)
                    with open(filepath, 'wb') as f:
                        f.write(pdf_res.content)
                    downloaded += 1
                    time.sleep(1) # Be nice to ArXiv API
                except Exception as e:
                    logger.error(f"Failed to download {safe_title}: {e}")
            else:
                logger.info(f"Already exists: {safe_title}.pdf")

if __name__ == "__main__":
    main()
