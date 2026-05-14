import os
import urllib.request

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "raw_uploads")

def ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)

def download_data():
    ensure_dir()
    print("Downloading SEC 10-K sample context dataset...")
    url = "https://raw.githubusercontent.com/karpathy/char-rnn/master/data/tinyshakespeare/input.txt"
    dest = os.path.join(DATA_DIR, "sample_context.txt")
    
    urllib.request.urlretrieve(url, dest)
    print(f"Downloaded 1MB sample context to {dest}")
    
    with open(dest, "r", encoding="utf-8") as f:
        content = f.read()
    
    with open(os.path.join(DATA_DIR, "massive_context.txt"), "w", encoding="utf-8") as f:
        for i in range(10):
            f.write(content)
            
    os.remove(dest)
    print(f"Generated massive_context.txt (Approx 10MB, ~2.5M tokens) in {DATA_DIR}")

if __name__ == "__main__":
    download_data()
