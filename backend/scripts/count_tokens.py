import os
import tiktoken
import pypdf

# Try to use tiktoken cl100k_base
try:
    enc = tiktoken.get_encoding("cl100k_base")
except:
    enc = None

def get_pdf_text_length(filepath):
    text = ""
    try:
        reader = pypdf.PdfReader(filepath)
        for page in reader.pages:
            text += page.extract_text() or ""
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    return text

def main():
    target_dir = os.path.join(os.path.dirname(__file__), "data", "raw_uploads")
    total_tokens = 0
    total_text_len = 0
    for file in os.listdir(target_dir):
        filepath = os.path.join(target_dir, file)
        text = ""
        if file.endswith('.pdf'):
            text = get_pdf_text_length(filepath)
        elif file.endswith('.txt'):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    text = f.read()
            except:
                pass
        
        total_text_len += len(text)
        if enc and text:
            tokens = len(enc.encode(text))
            total_tokens += tokens
            print(f"{file}: {tokens} tokens")
    
    print(f"\nTotal extracted text chars: {total_text_len}")
    if enc:
        print(f"Total precise tokens: {total_tokens}")

if __name__ == "__main__":
    main()
