"""
Consolidated test suite for Flask Task Manager.
Covers the 6 required test cases:
  1. Application starts (app fixture + index page)
  2. GET /health returns 200
  3. Task page loads (GET /)
  4. Task creation works (POST /api/tasks)
  5. Task completion works (PUT /api/tasks/<id>)
  6. Task deletion works (DELETE /api/tasks/<id>)
"""
import pytest
from app import create_app
from app.database import db as _db


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────

@pytest.fixture(scope="module")
def app():
    """Create Flask app configured for testing (in-memory SQLite)."""
    flask_app = create_app("testing")
    with flask_app.app_context():
        _db.create_all()
        yield flask_app
        _db.drop_all()


@pytest.fixture(scope="function")
def client(app):
    """Test client that clears the DB between every test."""
    with app.app_context():
        for table in reversed(_db.metadata.sorted_tables):
            _db.session.execute(table.delete())
        _db.session.commit()
    with app.test_client() as c:
        yield c


# ──────────────────────────────────────────────
# 1. Application starts
# ──────────────────────────────────────────────

def test_application_starts(app):
    """The Flask app object must be created successfully."""
    assert app is not None
    assert app.config["TESTING"] is True
    assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"


# ──────────────────────────────────────────────
# 2. GET /health returns 200
# ──────────────────────────────────────────────

def test_health_returns_200(client):
    """Health endpoint must return HTTP 200."""
    response = client.get("/health")
    assert response.status_code == 200


def test_health_returns_json_with_status(client):
    """Health endpoint must return JSON with status=healthy."""
    response = client.get("/health")
    data = response.get_json()
    assert data is not None
    assert data["status"] == "healthy"
    assert data["database"] == "connected"


# ──────────────────────────────────────────────
# 3. Task page loads
# ──────────────────────────────────────────────

def test_task_page_loads(client):
    """GET / must return HTTP 200 with HTML content."""
    response = client.get("/")
    assert response.status_code == 200
    # Must be HTML
    assert b"html" in response.data.lower()


def test_task_page_contains_app_name(client):
    """The task page HTML must include 'TaskFlow'."""
    response = client.get("/")
    assert b"TaskFlow" in response.data


# ──────────────────────────────────────────────
# 4. Task creation works
# ──────────────────────────────────────────────

def test_task_creation_returns_201(client):
    """POST /api/tasks must return HTTP 201."""
    response = client.post("/api/tasks", json={"title": "Buy groceries"})
    assert response.status_code == 201


def test_task_creation_returns_task_data(client):
    """Created task must have correct fields."""
    response = client.post(
        "/api/tasks",
        json={"title": "Buy groceries", "description": "Milk and eggs", "priority": "high"},
    )
    data = response.get_json()
    assert data["title"] == "Buy groceries"
    assert data["description"] == "Milk and eggs"
    assert data["priority"] == "high"
    assert data["completed"] is False
    assert "id" in data


def test_task_creation_appears_in_list(client):
    """After creating a task, it must appear in GET /api/tasks."""
    client.post("/api/tasks", json={"title": "Learn Kubernetes"})
    response = client.get("/api/tasks")
    data = response.get_json()
    titles = [t["title"] for t in data["tasks"]]
    assert "Learn Kubernetes" in titles


def test_task_creation_updates_stats(client):
    """Stats must reflect the newly created task."""
    client.post("/api/tasks", json={"title": "Task 1"})
    client.post("/api/tasks", json={"title": "Task 2"})
    response = client.get("/api/tasks")
    stats = response.get_json()["stats"]
    assert stats["total"] == 2
    assert stats["pending"] == 2
    assert stats["completed"] == 0


# ──────────────────────────────────────────────
# 5. Task completion works
# ──────────────────────────────────────────────

def test_task_completion_returns_200(client):
    """PUT /api/tasks/<id> with completed=True must return 200."""
    create_resp = client.post("/api/tasks", json={"title": "Write tests"})
    task_id = create_resp.get_json()["id"]

    response = client.put(f"/api/tasks/{task_id}", json={"completed": True})
    assert response.status_code == 200


def test_task_completion_sets_completed_true(client):
    """Task completed field must be True after marking done."""
    create_resp = client.post("/api/tasks", json={"title": "Write tests"})
    task_id = create_resp.get_json()["id"]

    response = client.put(f"/api/tasks/{task_id}", json={"completed": True})
    assert response.get_json()["completed"] is True


def test_task_completion_updates_stats(client):
    """Completing a task must update the stats counters."""
    create_resp = client.post("/api/tasks", json={"title": "Deploy app"})
    task_id = create_resp.get_json()["id"]

    client.put(f"/api/tasks/{task_id}", json={"completed": True})

    response = client.get("/api/tasks")
    stats = response.get_json()["stats"]
    assert stats["completed"] == 1
    assert stats["pending"] == 0


def test_task_completion_preserves_title(client):
    """Updating only 'completed' must not change the task title."""
    create_resp = client.post("/api/tasks", json={"title": "Deploy app"})
    task_id = create_resp.get_json()["id"]

    client.put(f"/api/tasks/{task_id}", json={"completed": True})

    response = client.get("/api/tasks")
    task = next(t for t in response.get_json()["tasks"] if t["id"] == task_id)
    assert task["title"] == "Deploy app"


# ──────────────────────────────────────────────
# 6. Task deletion works
# ──────────────────────────────────────────────

def test_task_deletion_returns_200(client):
    """DELETE /api/tasks/<id> must return HTTP 200."""
    create_resp = client.post("/api/tasks", json={"title": "Temp task"})
    task_id = create_resp.get_json()["id"]

    response = client.delete(f"/api/tasks/{task_id}")
    assert response.status_code == 200


def test_task_deletion_removes_task(client):
    """Deleted task must no longer appear in the task list."""
    create_resp = client.post("/api/tasks", json={"title": "Temp task"})
    task_id = create_resp.get_json()["id"]

    client.delete(f"/api/tasks/{task_id}")

    response = client.get("/api/tasks")
    ids = [t["id"] for t in response.get_json()["tasks"]]
    assert task_id not in ids


def test_task_deletion_updates_stats(client):
    """Deleting a task must decrement the total count."""
    create_resp = client.post("/api/tasks", json={"title": "Temp task"})
    task_id = create_resp.get_json()["id"]

    client.delete(f"/api/tasks/{task_id}")

    response = client.get("/api/tasks")
    assert response.get_json()["stats"]["total"] == 0


def test_task_deletion_nonexistent_returns_404(client):
    """Deleting a task that doesn't exist must return 404."""
    response = client.delete("/api/tasks/99999")
    assert response.status_code == 404
