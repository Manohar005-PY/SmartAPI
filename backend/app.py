from functools import wraps
import os
import re

from flask import Flask, jsonify, redirect, request, send_from_directory, session
from flask_cors import CORS
from werkzeug.security import check_password_hash

from config import Config
from db import (
    add_api,
    create_user,
    delete_api,
    get_all_apis,
    get_latest_log_for_all_apis,
    get_latest_logs,
    get_user_by_email,
    get_user_by_id,
    init_db,
)
from scheduler import start_scheduler

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../frontend"))

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="/")
app.config["SECRET_KEY"] = Config.SECRET_KEY
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = 86400  # 24 hours
CORS(app, supports_credentials=True)

# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PASSWORD_MIN_LEN = 8


def is_authenticated() -> bool:
    return bool(session.get("user_id"))


def api_login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not is_authenticated():
            return jsonify({"error": "Authentication required"}), 401
        return view_func(*args, **kwargs)
    return wrapped


# ---------------------------------------------------------------------------
# Frontend routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    if is_authenticated():
        return redirect("/dashboard")
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/dashboard")
def dashboard():
    if not is_authenticated():
        return redirect("/")
    return send_from_directory(FRONTEND_DIR, "dashboard.html")


@app.route("/register")
def register_page():
    if is_authenticated():
        return redirect("/dashboard")
    return send_from_directory(FRONTEND_DIR, "register.html")


# ---------------------------------------------------------------------------
# Auth API endpoints
# ---------------------------------------------------------------------------

@app.route("/api/auth/session", methods=["GET"])
def auth_session():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"authenticated": False}), 200

    user = get_user_by_id(user_id)
    if not user:
        session.clear()
        return jsonify({"authenticated": False}), 200

    return jsonify({
        "authenticated": True,
        "user": {"id": user["id"], "email": user["email"]},
    }), 200


@app.route("/api/auth/register", methods=["POST"])
def register():
    """Create a new user account."""
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    confirm = data.get("confirm_password") or ""

    # Validation
    if not email or not password or not confirm:
        return jsonify({"error": "All fields are required"}), 400

    if not EMAIL_RE.match(email):
        return jsonify({"error": "Please enter a valid email address"}), 400

    if len(password) < PASSWORD_MIN_LEN:
        return jsonify({"error": f"Password must be at least {PASSWORD_MIN_LEN} characters"}), 400

    if password != confirm:
        return jsonify({"error": "Passwords do not match"}), 400

    try:
        new_user = create_user(email, password)
    except Exception as exc:
        print(f"Registration error: {exc}")
        return jsonify({"error": "Registration failed. Please try again."}), 500

    if new_user is None:
        return jsonify({"error": "An account with this email already exists"}), 409

    # Auto-login after registration
    session.clear()
    session.permanent = True
    session["user_id"] = new_user["id"]

    return jsonify({
        "message": "Account created successfully",
        "user": {"id": new_user["id"], "email": new_user["email"]},
    }), 201


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    user = get_user_by_email(email)
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password"}), 401

    session.clear()
    session.permanent = True
    session["user_id"] = user["id"]

    return jsonify({
        "message": "Login successful",
        "user": {"id": user["id"], "email": user["email"]},
    }), 200


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"}), 200


# ---------------------------------------------------------------------------
# Protected API endpoints
# ---------------------------------------------------------------------------

@app.route("/api/apis", methods=["GET"])
@api_login_required
def list_apis():
    return jsonify(get_all_apis())


@app.route("/api/add_api", methods=["POST"])
@api_login_required
def add_api_endpoint():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    url = (data.get("url") or "").strip()

    try:
        interval_seconds = int(data.get("interval", 60))
        threshold_ms = int(data.get("threshold", 1000))
    except (TypeError, ValueError):
        return jsonify({"error": "Interval and threshold must be valid numbers"}), 400

    if not name or not url:
        return jsonify({"error": "Name and URL are required"}), 400

    if interval_seconds < 5 or threshold_ms < 10:
        return jsonify({
            "error": "Interval must be at least 5 seconds and threshold at least 10 ms"
        }), 400

    if add_api(name, url, interval_seconds, threshold_ms):
        return jsonify({"message": "API added successfully"}), 201
    return jsonify({"error": "Failed to add API"}), 500


@app.route("/api/delete_api/<int:api_id>", methods=["DELETE"])
@api_login_required
def delete_api_endpoint(api_id):
    if delete_api(api_id):
        return jsonify({"message": "API deleted successfully"}), 200
    return jsonify({"error": "Failed to delete API"}), 500


@app.route("/api/get_status", methods=["GET"])
@api_login_required
def get_status():
    apis = get_all_apis()
    latest_logs = get_latest_log_for_all_apis()

    status_data = []
    for api in apis:
        api_id = api["id"]
        log = latest_logs.get(api_id)
        status_data.append({
            "id": api_id,
            "name": api["name"],
            "url": api["url"],
            "interval": api["interval_seconds"],
            "threshold": api["threshold_ms"],
            "state": log["state"] if log else "PENDING",
            "response_time": log["response_time"] if log else 0,
            "status_code": log["status_code"] if log else None,
        })
    return jsonify(status_data)


@app.route("/api/logs/<int:api_id>", methods=["GET"])
@api_login_required
def get_logs(api_id):
    logs = get_latest_logs(api_id, limit=20)
    return jsonify(logs)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    init_db()          # Initialize DB tables and open persistent connection
    start_scheduler()  # Start background polling tasks
    app.run(debug=True, host="0.0.0.0", port=5000, use_reloader=False)
    # use_reloader=False prevents double scheduler instances in development
