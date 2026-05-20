from functools import wraps
import re
from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash

try:
    from backend.db import create_user, get_user_by_email, get_user_by_id
except ImportError:
    from db import create_user, get_user_by_email, get_user_by_id

auth_bp = Blueprint("auth", __name__)

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

@auth_bp.route("/api/auth/session", methods=["GET"])
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

@auth_bp.route("/api/auth/register", methods=["POST"])
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
    session.permanent = False
    session["user_id"] = new_user["id"]

    return jsonify({
        "message": "Account created successfully",
        "user": {"id": new_user["id"], "email": new_user["email"]},
    }), 201

@auth_bp.route("/api/auth/login", methods=["POST"])
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
    session.permanent = False
    session["user_id"] = user["id"]

    return jsonify({
        "message": "Login successful",
        "user": {"id": user["id"], "email": user["email"]},
    }), 200

@auth_bp.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"}), 200
