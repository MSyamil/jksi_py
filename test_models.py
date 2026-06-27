import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("GEMINI_API_KEY")
print("Using API Key:", key[:10] + "..." if key else "None")

genai.configure(api_key=key)

try:
    models = genai.list_models()
    print("Successfully fetched models:")
    for m in models:
        print(f"- {m.name} (Supports: {m.supported_generation_methods})")
except Exception as e:
    print("Error listing models:")
    import traceback
    traceback.print_exc()
