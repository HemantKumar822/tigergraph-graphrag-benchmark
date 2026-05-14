import os
import json
import glob

raw_dir = "data/raw_uploads"
for filepath in glob.glob(os.path.join(raw_dir, "*.json")):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        pages = data.get("query", {}).get("pages", {})
        for pid, pdata in pages.items():
            content = pdata.get("extract", "")
            title = pdata.get("title", "doc").replace(" ", "_")
            if content:
                txt_path = os.path.join(raw_dir, f"{title}.txt")
                with open(txt_path, "w", encoding="utf-8") as out_f:
                    out_f.write(content)
                print(f"Extracted {title}.txt")
        # Remove the json
        os.remove(filepath)
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
