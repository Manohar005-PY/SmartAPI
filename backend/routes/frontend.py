import os
from flask import Blueprint, redirect, send_from_directory

from backend.routes.auth import is_authenticated

frontend_bp = Blueprint("frontend", __name__)
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend"))

@frontend_bp.route("/")
def index():
    if is_authenticated():
        return redirect("/dashboard")
    return send_from_directory(FRONTEND_DIR, "index.html")

@frontend_bp.route("/dashboard")
def dashboard():
    if not is_authenticated():
        return redirect("/")
    return send_from_directory(FRONTEND_DIR, "dashboard.html")

@frontend_bp.route("/register")
def register_page():
    if is_authenticated():
        return redirect("/dashboard")
    return send_from_directory(FRONTEND_DIR, "register.html")
