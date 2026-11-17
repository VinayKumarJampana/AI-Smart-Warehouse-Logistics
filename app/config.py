import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file if it exists
dotenv_path = BASE_DIR / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)


class Config:
    """Base application configuration."""

    # Core Flask Settings
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-smart-logistics-2026")
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = os.getenv("FLASK_DEBUG", "1").lower() in ("1", "true", "yes")

    # Security & CSRF Settings
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour token expiration
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # Database Configuration
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "3306")
    DB_NAME = os.getenv("DB_NAME", "smart_logistics_db")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    USE_SQLITE_FALLBACK = os.getenv("USE_SQLITE_FALLBACK", "False").lower() in ("1", "true", "yes")

    if USE_SQLITE_FALLBACK:
        sqlite_path = BASE_DIR / "smart_logistics.db"
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{sqlite_path}"
    else:
        # Standard PyMySQL connection string
        SQLALCHEMY_DATABASE_URI = (
            f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
        )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False  # Set to True if SQL query debugging is required


class DevelopmentConfig(Config):
    """Development environment specific configuration."""
    DEBUG = True


class TestingConfig(Config):
    """Testing environment specific configuration."""
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


class ProductionConfig(Config):
    """Production environment specific configuration."""
    DEBUG = False
    # In production, enforce secure cookies if HTTPS is used
    SESSION_COOKIE_SECURE = True


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
