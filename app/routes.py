"""
Flask routes — both the UI and the REST API.
"""
from datetime import datetime, timezone

from flask import Blueprint, abort, jsonify, render_template, request

from .database import db
from .models import Task

main_bp = Blueprint("main", __name__)


# ---------------------------------------------------------------------------
# Health endpoint  (used by Kubernetes liveness + readiness probes)
# ---------------------------------------------------------------------------

@main_bp.route("/health")
def health():
    """Return a simple JSON health payload."""
    # Try a cheap DB round-trip so the readiness probe catches DB issues too.
    try:
        db.session.execute(db.text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "unavailable"

    status = "healthy" if db_status == "connected" else "degraded"
    return jsonify({"status": status, "database": db_status}), 200


# ---------------------------------------------------------------------------
# UI route
# ---------------------------------------------------------------------------

@main_bp.route("/")
def index():
    """Serve the single-page frontend."""
    return render_template("index.html")


# ---------------------------------------------------------------------------
# REST API
# ---------------------------------------------------------------------------

@main_bp.route("/api/tasks", methods=["GET"])
def get_tasks():
    """Return all tasks, optionally filtered by ?completed=true|false."""
    completed_param = request.args.get("completed")
    query = Task.query

    if completed_param is not None:
        completed_bool = completed_param.lower() == "true"
        query = query.filter_by(completed=completed_bool)

    tasks = query.order_by(Task.created_at.desc()).all()

    # Dashboard statistics
    total = Task.query.count()
    done = Task.query.filter_by(completed=True).count()
    pending = total - done

    return jsonify(
        {
            "tasks": [t.to_dict() for t in tasks],
            "stats": {"total": total, "completed": done, "pending": pending},
        }
    )


@main_bp.route("/api/tasks", methods=["POST"])
def create_task():
    """Create a new task."""
    data = request.get_json(silent=True)
    if not data:
        abort(400, description="Request body must be JSON.")

    title = (data.get("title") or "").strip()
    if not title:
        abort(400, description="'title' is required and cannot be empty.")

    priority = data.get("priority", "medium")
    if priority not in ("low", "medium", "high"):
        abort(400, description="'priority' must be 'low', 'medium', or 'high'.")

    task = Task(
        title=title,
        description=(data.get("description") or "").strip(),
        priority=priority,
        completed=bool(data.get("completed", False)),
    )
    db.session.add(task)
    db.session.commit()

    return jsonify(task.to_dict()), 201


@main_bp.route("/api/tasks/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    """Update an existing task (partial update supported)."""
    task = db.session.get(Task, task_id)
    if task is None:
        abort(404)
    data = request.get_json(silent=True)
    if not data:
        abort(400, description="Request body must be JSON.")

    if "title" in data:
        title = (data["title"] or "").strip()
        if not title:
            abort(400, description="'title' cannot be empty.")
        task.title = title

    if "description" in data:
        task.description = (data["description"] or "").strip()

    if "completed" in data:
        task.completed = bool(data["completed"])

    if "priority" in data:
        if data["priority"] not in ("low", "medium", "high"):
            abort(400, description="'priority' must be 'low', 'medium', or 'high'.")
        task.priority = data["priority"]

    task.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify(task.to_dict())


@main_bp.route("/api/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    """Delete a task by ID."""
    task = db.session.get(Task, task_id)
    if task is None:
        abort(404)
    db.session.delete(task)
    db.session.commit()
    return jsonify({"message": f"Task {task_id} deleted successfully."})


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@main_bp.app_errorhandler(400)
def bad_request(error):
    return jsonify({"error": str(error.description)}), 400


@main_bp.app_errorhandler(404)
def not_found(error):
    return jsonify({"error": "Resource not found."}), 404


@main_bp.app_errorhandler(500)
def server_error(error):
    return jsonify({"error": "Internal server error."}), 500
