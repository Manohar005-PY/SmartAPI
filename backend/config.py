import os
from dotenv import load_dotenv

# Load environment variables from .env file (for local development)
load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    if not SECRET_KEY or SECRET_KEY == "change-this-secret-key":
        if os.getenv("RENDER") == "true":
            raise RuntimeError("SECRET_KEY environment variable is required and must not be default in production!")
        SECRET_KEY = "change-this-secret-key"

    # Database Configuration
    # Uses DATABASE_URL (PostgreSQL) if available; otherwise falls back to SQLite.
    DATABASE_URL = os.getenv("DATABASE_URL")

    # Default sign-in user created on first startup
    DEFAULT_ADMIN_EMAIL = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@example.com")
    DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "Admin@123")

    # Email Alerts Configuration (Using SMTP)
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "your_email@gmail.com")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "your_app_password")
    ALERT_RECEIVER = os.getenv("ALERT_RECEIVER", "admin@example.com")
