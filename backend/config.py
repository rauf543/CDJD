import os
from dotenv import load_dotenv

# Load environment variables from .env file
# Construct the path to the .env file relative to this config.py file
# Assuming .env is in the same directory as main.py (which is one level up from where config.py might be if it's in an 'app' subdirectory)
# Or, more robustly, specify an absolute path or ensure CWD is backend directory when running.
# For this structure, where config.py is in 'backend' and .env is also in 'backend':
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "you-will-never-guess"
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), "uploads")
    ALLOWED_EXTENSIONS_CV = {"pdf", "docx", "zip", "txt"} # Added 'txt'
    ALLOWED_EXTENSIONS_JD = {"pdf", "docx", "txt"}
    MAX_CONTENT_LENGTH = 256 * 1024 * 1024  # 256 MB max upload size

    # Database configuration (SQLite for now)
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or \
        "sqlite:///" + os.path.join(os.path.abspath(os.path.dirname(__file__)), "app.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # LLM API Key
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")


