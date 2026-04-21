import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
print(f"Using API Key: {api_key[:10]}...")

genai.configure(api_key=api_key)

try:
    print("Fetching models...")
    models = list(genai.list_models())
    print(f"Found {len(models)} models total.")
    for m in models:
        print(f"Model: {m.name}, Methods: {m.supported_generation_methods}")
except Exception as e:
    print("CRITICAL ERROR:")
    import traceback
    traceback.print_exc()
