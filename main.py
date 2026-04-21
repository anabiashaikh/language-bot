from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import sqlite3
import uuid
from typing import List, Optional
import traceback


from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv

load_dotenv()

# Setup Google API Key (MUST BE SET AS AN ENVIRONMENT VARIABLE)
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY", "")

app = FastAPI()

# Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for the RAG state
retriever = None
llm = None
prompt_template = None

print("Initializing RAG vector store and models...")

def init_db():
    conn = sqlite3.connect("chats.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            role TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    """)
    conn.commit()
    conn.close()

def init_rag():
    global retriever, llm, prompt_template
    
    try:
        loader_text = TextLoader("DATA OF PROGRAMMING LANGUAGES.txt", encoding="utf-8")
        docs = loader_text.load()
    except Exception as e:
        print(f"Error loading document: {e}")
        traceback.print_exc()
        return
        
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(docs)
    
    # Use Google embeddings to avoid local downloads
    embeddings = GoogleGenerativeAIEmbeddings(
        model="gemini-embedding-001",
        google_api_key=os.environ["GOOGLE_API_KEY"]
    )
    vector_store = FAISS.from_documents(chunks, embeddings)
    retriever = vector_store.as_retriever(search_type="similarity", k=3)
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0.5,
        max_output_tokens=1000,
        google_api_key=os.environ["GOOGLE_API_KEY"]
    )
    
    prompt_template = PromptTemplate(
        input_variables=["context", "question"],
        template="""
Answer the question using the context below.

Context:
{context}

Question:
{question}

Answer:
Give a short, accurate answer.
"""
    )
    print("RAG System successfully initialized.")

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    print("\n" + "="*50)
    print("STARTING ABYSSAL AI SERVER")
    print("="*50)
    
    init_db()
    
    print("\nInitializing RAG system...")
    print("   (This may take 20-30 seconds to load models)\n")
    init_rag()
    
    print("\nRAG System successfully initialized.")
    print(f"Server is ready at http://localhost:8080")
    print("="*50 + "\n")
    
    yield
    
    # Shutdown logic
    print("\n" + "="*50)
    print("SHUTTING DOWN SERVER")
    print("="*50 + "\n")


app = FastAPI(lifespan=lifespan)

class ChatRequest(BaseModel):
    query: str
    session_id: str

class ChatResponse(BaseModel):
    answer: str

class SessionOut(BaseModel):
    id: str
    title: str

class MessageOut(BaseModel):
    role: str
    content: str

def generate_title(query: str) -> str:
    # Use the LLM to generate a quick sidebar title based on the first query
    title_prompt = f"Generate a very short 2-3 word title for a chat that starts with this message: '{query}'. Provide only the title without quotes."
    try:
        res = llm.invoke(title_prompt)
        return res.content.replace('"', '').strip()
    except:
        return query[:20] + "..."

@app.post("/api/sessions", response_model=SessionOut)
def create_session():
    session_id = str(uuid.uuid4())
    conn = sqlite3.connect("chats.db")
    c = conn.cursor()
    title = "New Chat"
    c.execute("INSERT INTO sessions (id, title) VALUES (?, ?)", (session_id, title))
    conn.commit()
    conn.close()
    return SessionOut(id=session_id, title=title)

@app.get("/api/sessions", response_model=List[SessionOut])
def get_sessions():
    conn = sqlite3.connect("chats.db")
    c = conn.cursor()
    c.execute("SELECT id, title FROM sessions ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [SessionOut(id=row[0], title=row[1]) for row in rows]

@app.get("/api/sessions/{session_id}", response_model=List[MessageOut])
def get_session_history(session_id: str):
    conn = sqlite3.connect("chats.db")
    c = conn.cursor()
    c.execute("SELECT role, content FROM messages WHERE session_id = ? ORDER BY id ASC", (session_id,))
    rows = c.fetchall()
    conn.close()
    return [MessageOut(role=row[0], content=row[1]) for row in rows]

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    if not retriever or not llm:
        raise HTTPException(status_code=500, detail="RAG system not initialized. Check server logs.")
        
    session_id = req.session_id

    conn = sqlite3.connect("chats.db")
    c = conn.cursor()
    
    # Check if this is the first message to update the Title dynamically
    c.execute("SELECT COUNT(*) FROM messages WHERE session_id = ?", (session_id,))
    count = c.fetchone()[0]
    if count == 0:
        new_title = generate_title(req.query)
        c.execute("UPDATE sessions SET title = ? WHERE id = ?", (new_title, session_id))

    # Save user message
    c.execute("INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)", (session_id, "user", req.query))
    conn.commit()
        
    try:
        # RAG Logic
        docs = retriever.invoke(req.query)
        if not docs:
            response = llm.invoke(req.query)
            final_answer = response.content
        else:
            context = "\n\n".join(doc.page_content for doc in docs)
            prompt = prompt_template.format(context=context, question=req.query)
            response = llm.invoke(prompt)
            final_answer = response.content

        # Save AI message
        c.execute("INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)", (session_id, "ai", final_answer))
        conn.commit()
        conn.close()

        return {"answer": final_answer, "title_updated": True if count == 0 else False}
        
    except Exception as e:
        conn.close()
        print(f"CRITICAL ERROR in chat_endpoint: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# Mount static files to serve the frontend
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)


