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
async def chat(question: Question):
    try:
        answer = run_smart_agent(agent, question.message)
        # Save user message and bot reply to DB
        save_to_db(question.message, answer)
        logger.info("User message and bot reply saved to database.")
        return {"answer": answer}
    except Exception as e:
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
