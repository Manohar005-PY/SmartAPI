from flask import Blueprint, jsonify, request, session

from backend.db import (
    add_api,
    delete_api,
    get_api_by_id,
    get_apis_by_user,
    get_latest_log_for_all_apis,
    get_latest_logs,
)
from backend.routes.auth import api_login_required

apis_bp = Blueprint("apis", __name__)

@apis_bp.route("/api/apis", methods=["GET"])
@api_login_required
def list_apis():
    return jsonify(get_apis_by_user(session["user_id"]))

@apis_bp.route("/api/add_api", methods=["POST"])
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

    if add_api(session["user_id"], name, url, interval_seconds, threshold_ms):
        return jsonify({"message": "API added successfully"}), 201
    return jsonify({"error": "Failed to add API"}), 500

@apis_bp.route("/api/delete_api/<int:api_id>", methods=["DELETE"])
@api_login_required
def delete_api_endpoint(api_id):
    api = get_api_by_id(api_id)
    if not api:
        return jsonify({"error": "API not found"}), 404
    if api.get("user_id") != session["user_id"]:
        return jsonify({"error": "Unauthorized"}), 403

    if delete_api(api_id):
        return jsonify({"message": "API deleted successfully"}), 200
    return jsonify({"error": "Failed to delete API"}), 500

@apis_bp.route("/api/get_status", methods=["GET"])
@api_login_required
def get_status():
    apis = get_apis_by_user(session["user_id"])
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

@apis_bp.route("/api/logs/<int:api_id>", methods=["GET"])
@api_login_required
def get_logs(api_id):
    api = get_api_by_id(api_id)
    if not api:
        return jsonify({"error": "API not found"}), 404
    if api.get("user_id") != session["user_id"]:
        return jsonify({"error": "Unauthorized"}), 403
    logs = get_latest_logs(api_id, limit=20)
    return jsonify(logs)
