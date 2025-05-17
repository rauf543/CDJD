import os
from dotenv import load_dotenv

# Load environment variables from .env file
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "you-will-never-guess"
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), "uploads")
    ALLOWED_EXTENSIONS_CV = {"pdf", "docx", "zip", "txt"}
    ALLOWED_EXTENSIONS_JD = {"pdf", "docx", "txt"}
    MAX_CONTENT_LENGTH = 256 * 1024 * 1024  # 256 MB max upload size

    # Database configuration
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # LLM API Key
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")


class DevelopmentConfig(Config):
    DEBUG = True
    # SQLite for development
    SQLALCHEMY_DATABASE_URI = os.environ.get("DEV_DATABASE_URL") or \
        "sqlite:///" + os.path.join(os.path.abspath(os.path.dirname(__file__)), "app_dev.db")


class TestingConfig(Config):
    TESTING = True
    # SQLite for testing
    SQLALCHEMY_DATABASE_URI = os.environ.get("TEST_DATABASE_URL") or \
        "sqlite:///" + os.path.join(os.path.abspath(os.path.dirname(__file__)), "app_test.db")


class ProductionConfig(Config):
    # PostgreSQL for production
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or \
        "postgresql://user:password@localhost:5432/cv_jd_matcher"
    
    # Production-specific settings
    PREFERRED_URL_SCHEME = 'https'
    
    # Connection pool settings for PostgreSQL
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True
    }


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
