import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# API Keys and SMTP configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
DATABASE_URL = os.getenv("DATABASE_URL")

# Data File Paths
DATA_DIR = BASE_DIR / "data"
HISTORY_FILE_PATH = DATA_DIR / "history.json"
ARCHIVE_DIR = DATA_DIR / "archive"

# Ensure data directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

# Database Config
DB_PATH = BASE_DIR / "backend" / "subscribers.db"

# Model Selection Defaults
PRIMARY_MODEL_MISTRAL = "open-mixtral-8x22b"
FALLBACK_MODEL_GEMINI = "gemini-3.5-flash"
FALLBACK_MODEL_GROQ = "llama3-70b-8192"
