import os
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENROUTER_API_KEY", "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")

llm = ChatOpenAI(
    model="google/gemini-2.0-flash",
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key
)

try:
    print("Testing OpenRouter API...")
    res = llm.invoke("Hi")
    print("Success:", res.content)
except Exception as e:
    print("Error:", e)
