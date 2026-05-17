import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key")

    # Database Configuration
    DB_ENGINE = os.getenv("DB_ENGINE", "auto")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "api_health_monitor")

    # Default sign-in user created on first startup
    DEFAULT_ADMIN_EMAIL = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@example.com")
    DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "Admin@123")

    # Email Alerts Configuration (Using SMTP)
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "your_email@gmail.com")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "your_app_password")
    ALERT_RECEIVER = os.getenv("ALERT_RECEIVER", "admin@example.com")
