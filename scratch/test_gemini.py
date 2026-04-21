import os
from langchain_google_genai import ChatGoogleGenerativeAI

os.environ["GOOGLE_API_KEY"] = "your_gemini_api_key_here"

try:
    print("Attempting to initialize ChatGoogleGenerativeAI...")
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        temperature=0.5,
        max_output_tokens=1000,
        google_api_key=os.environ["GOOGLE_API_KEY"]
    )
    print("Initialization successful (no validation on creation).")
    
    # Try a dummy call to see if it fails
    # print("Attempting a dummy call...")
    # llm.invoke("Hi")
except Exception as e:
    print("Error during initialization:", e)
