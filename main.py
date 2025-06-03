from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse
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

# Create directories if they don't exist
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
def read_root():
    logger.info("Root endpoint accessed.")
    # Serve the HTML file directly since it's not in templates folder
    return FileResponse("templates/index.html")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for development; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the agent once at startup
try:
    agent = initialize_smart_agent()
    logger.info("Smart agent initialized successfully.")
except Exception as e:
    logger.error(f"Failed to initialize agent: {e}")
    agent = None

@app.post("/chat")
async def chat(chat_request: ChatRequest):
    if not agent:
        raise HTTPException(status_code=500, detail="Agent not initialized")
    
    session_id = chat_request.session_id
    messages = chat_request.messages

    if not messages:
        raise HTTPException(status_code=400, detail="No messages provided")

    try:
        user_message = messages[-1].content.lower().strip()
        
        # Handle simple greetings directly
        simple_greetings = ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"]
        if user_message in simple_greetings:
            answer = "Hello! How can I help you today?"
        else:
            conversation_text = "\n".join(f"{m.role}: {m.content}" for m in messages)
            answer = run_smart_agent(agent, conversation_text)
            
            # If agent returns empty or problematic response, provide fallback
            if not answer or "will wait for more questions" in answer.lower():
                answer = "I'm here to help! Could you please rephrase your question?"

        # Save to database with error handling
        try:
            save_to_db(session_id, "user", messages[-1].content)
            save_to_db(session_id, "assistant", answer)
        except Exception as db_error:
            logger.error(f"Database error: {db_error}")

        return {"answer": answer}
    
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return {"answer": "I'm sorry, I encountered an error. Please try again."}
def save_to_db(session_id: str, role: str, content: str):
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (%s, %s, %s)",
            (session_id, role, content)
        )
        conn.commit()
    except Exception as e:
        logger.error(f"Database save error: {e}")
        raise
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

# def get_conversation_history(session_id: str) -> List[Dict[str, str]]:
#     try:
#         conn = psycopg2.connect(DATABASE_URL)
#         cur = conn.cursor()
#         cur.execute(
#             "SELECT role, content FROM messages WHERE session_id = %s ORDER BY id",
#             (session_id,)
#         )
#         rows = cur.fetchall()
#         return [{"role": row[0], "content": row[1]} for row in rows]
#     except Exception as e:
#         logger.error(f"Database fetch error: {e}")
#         return []
#     finally:
#         if 'cur' in locals():
#             cur.close()
#         if 'conn' in locals():
#             conn.close()


