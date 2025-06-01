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

class Message(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str

class ChatRequest(BaseModel):
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
class Question(BaseModel):
    message: str

@app.post("/chat")
async def chat(chat_request: ChatRequest):
    try:
        # Prepare the history content as one input string or structured prompt as your agent expects
        conversation_text = "\n".join(
            f"{msg.role}: {msg.content}" for msg in chat_request.messages
        )
        # Run agent with full conversation history
        answer = run_smart_agent(agent, conversation_text)

        # Append bot reply to conversation history (could also return full updated history)
        # Here, save only latest user message and bot reply to DB or optionally the whole history

        last_user_message = [m.content for m in chat_request.messages if m.role == "user"][-1]
        save_to_db(last_user_message, answer)

        logger.info("User message and bot reply saved to database.")
        return {"answer": answer}
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return {"answer": f"An error occurred: {str(e)}"}

def save_to_db(user_message: str, bot_reply: str):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO messages (user_message, bot_reply) VALUES (%s, %s)",
        (user_message, bot_reply)
    )
    conn.commit()
    cur.close()
    conn.close()
