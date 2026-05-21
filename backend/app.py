import os
from flask import Flask
from flask_cors import CORS

from backend.config import Config
from backend.db import init_db
from backend.routes import auth_bp, apis_bp, frontend_bp

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../frontend"))

def create_app():
    # Initialize database (tables, migrations, default admin user) on app creation.
    # This guarantees tables exist before any requests are served, including under Gunicorn.
    init_db()

    app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="/")
    app.config["SECRET_KEY"] = Config.SECRET_KEY
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["PERMANENT_SESSION_LIFETIME"] = 86400  # 24 hours
    
    # Secure session cookies over HTTPS in production (Render)
    if os.getenv("RENDER") == "true":
        app.config["SESSION_COOKIE_SECURE"] = True
    
    CORS(app, supports_credentials=True)

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(apis_bp)
    app.register_blueprint(frontend_bp)
    
    # Start inline background scheduler for single-service deployments
    from backend.services.scheduler import start_scheduler
    try:
        start_scheduler()
    except Exception as exc:
        app.logger.warning(f"Could not start background scheduler on initialization: {exc}")

    return app

app = create_app()

if __name__ == "__main__":
    # Start inline scheduler for local development convenience
    from backend.services.scheduler import start_scheduler
    start_scheduler()
    
    # Use PORT environment variable or default to 5000
    port = int(os.getenv("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port, use_reloader=False)
