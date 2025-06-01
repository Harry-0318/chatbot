from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from llmModel import initialize_smart_agent, run_smart_agent
import psycopg2
import os
from dotenv import load_dotenv
import logging
from typing import List, Dict
import uuid


class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    session_id: str
    messages: List[Message]


class Question(BaseModel):
    message: str

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s — %(levelname)s — %(message)s",
    handlers=[
        logging.FileHandler("website.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

app = FastAPI()

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")
@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    logger.info("Root endpoint accessed.")
    return templates.TemplateResponse("index.html", {"request": request, "message": "Hello from FastAPI!"})


# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for development; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the agent once at startup
agent = initialize_smart_agent()
logger.info("Smart agent initialized successfully.")

# Request model

@app.post("/chat")
async def chat(chat_request: ChatRequest):
    session_id = chat_request.session_id
    messages = chat_request.messages

    conversation_text = "\n".join(f"{m.role}: {m.content}" for m in messages)
    answer = run_smart_agent(agent, conversation_text)

    # Save last user message and assistant reply
    save_to_db(session_id, "user", messages[-1].content)
    save_to_db(session_id, "assistant", answer)

    return {"answer": answer}

def save_to_db(session_id: str, role: str, content: str):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO messages (session_id, role, content) VALUES (%s, %s, %s)",
        (session_id, role, content)
    )
    conn.commit()
    cur.close()
    conn.close()
def get_conversation_history(session_id: str) -> List[Dict[str, str]]:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute(
        "SELECT role, content FROM messages WHERE session_id = %s ORDER BY id",
        (session_id,)
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    return [{"role": row[0], "content": row[1]} for row in rows]
