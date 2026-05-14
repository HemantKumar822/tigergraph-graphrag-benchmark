import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("CRITICAL ERROR: GEMINI_API_KEY not found in .env file!")
    exit(1)

print(f"Connecting using Key ending in ...{api_key[-6:]}")
genai.configure(api_key=api_key)

try:
    print("--- DISCOVERING AVAILABLE MODELS ---")
    model_list = genai.list_models()
    
    generation_models = []
    embedding_models = []
    
    for m in model_list:
        if 'generateContent' in m.supported_generation_methods:
            generation_models.append(m.name)
        if 'embedContent' in m.supported_generation_methods:
            embedding_models.append(m.name)
            
    print("VALID GENERATION MODELS:")
    for name in sorted(generation_models):
        print(f"  {name}")
        
    print("VALID EMBEDDING MODELS:")
    for name in sorted(embedding_models):
        print(f"  {name}")
        
except Exception as e:
    print(f"FAILED to fetch model list: {e}")
