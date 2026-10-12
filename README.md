
# Dockerized Flask Task Manager with Kubernetes

A simple Task Manager web application built with Flask, containerized with Docker,
and deployed on a local Kubernetes cluster using Minikube.

This project is designed to be beginner-friendly and easy to run on Windows, macOS, or Linux.



## Project Overview

TaskFlow is a lightweight task management application that demonstrates the full DevOps workflow:

- **Flask** web application with a clean UI and REST API
- **SQLite** database (no PostgreSQL, no external database required)
- **Docker** for containerization
- **Kubernetes** (via Minikube) for local container orchestration
- **GitHub Actions** for automated testing and Docker image builds

**Interview summary:**
> "I built a Flask Task Manager, containerized it with Docker, and deployed it on a Kubernetes cluster using Minikube. I created Kubernetes Deployment and Service manifests, added liveness and readiness health probes, automated tests with pytest, and configured GitHub Actions to test and build the Docker image."



## Features

- Add a task (with title, description, and priority)
- View all tasks
- Mark a task as completed
- Delete a task
- Dashboard showing total / completed / pending task counts
- `/health` endpoint for Kubernetes health probes
- Clean REST API: `GET/POST /api/tasks`, `PUT/DELETE /api/tasks/<id>`



## Technology Stack

| Layer | Technology |
|---|---|
| Web Framework | Flask 3.x |
| Database | SQLite (via Flask-SQLAlchemy) |
| Web Server | Gunicorn |
| Containerization | Docker |
| Orchestration | Kubernetes (Minikube) |
| Testing | pytest |
| CI/CD | GitHub Actions |


## Project Structure

```
kubernetes-task-app/
│
├── app/
│   ├── __init__.py        # Flask app factory
│   ├── models.py          # SQLAlchemy Task model
│   ├── routes.py          # API routes and UI routes
│   ├── config.py          # App configuration (dev / test / prod)
│   ├── database.py        # SQLAlchemy instance
│   ├── templates/
│   │   └── index.html     # TaskFlow single-page UI
│   └── static/
│       ├── css/
│       └── js/
│
├── tests/
│   ├── conftest.py        # Minimal pytest config
│   └── test_app.py        # All test cases (6 required + extras)
│
├── k8s/
│   ├── namespace.yaml     # Kubernetes Namespace: task-app
│   ├── deployment.yaml    # Kubernetes Deployment: task-manager
│   └── service.yaml       # Kubernetes Service: NodePort on 5000
│
├── Dockerfile             # Docker image definition
├── .dockerignore          # Files excluded from Docker build context
├── requirements.txt       # Python dependencies
├── docker-compose.yml     # Single-service Docker Compose file
├── run.py                 # Application entry point (dev + gunicorn)
├── README.md              # This file
└── .github/
    └── workflows/
        └── ci.yml         # GitHub Actions CI pipeline
```



## Run Locally

**Prerequisites:** Python 3.11+

```bash
# 1. Create a virtual environment
python -m venv .venv

# Windows:
.venv\Scripts\activate

# macOS/Linux:
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the development server
python run.py
```

Open your browser at: http://localhost:5000

---

## Run with Docker

**Prerequisites:** Docker Desktop installed and running.

```bash
# Build the Docker image
docker build -t task-manager:latest .

# Run the container
docker run -p 5000:5000 task-manager:latest
```

Open your browser at: http://localhost:5000

Check the health endpoint: http://localhost:5000/health

---

## Run with Docker Compose

Docker Compose is the easiest way to run the app locally with Docker.

```bash
# Build and start (foreground)
docker compose up --build

# Build and start (background)
docker compose up -d --build

# Stop
docker compose down
```

Open your browser at: http://localhost:5000

---

## Run with Minikube

Minikube runs a local Kubernetes cluster on your machine using Docker as the driver.

### Prerequisites

- Docker Desktop installed and running
- Minikube installed ([download here](https://minikube.sigs.k8s.io/docs/start/))
- kubectl installed (comes with Docker Desktop or install separately)

### Start Minikube

```bash
# Verify Minikube is installed
minikube version

# Start the cluster (uses Docker as the driver)
minikube start --driver=docker

# Verify the node is Ready
kubectl get nodes
```

Expected output:
```
NAME       STATUS   ROLES           AGE   VERSION
minikube   Ready    control-plane   ...   v1.x.x
```

---

## Kubernetes Deployment

### Step 1 — Build the image inside Minikube

Minikube has its own Docker daemon. Build the image directly into it so the cluster can find it without pulling from Docker Hub.

```bash
minikube image build -t task-manager:latest .
```

### Step 2 — Apply Kubernetes manifests

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

### Step 3 — Verify the deployment

```bash
# Check the pod is Running and READY 1/1
kubectl get pods -n task-app

# Check the deployment
kubectl get deployment -n task-app

# Check the service
kubectl get service -n task-app
```

Expected pod output:
```
NAME                            READY   STATUS    RESTARTS   AGE
task-manager-xxxxxxxxx-xxxxx    1/1     Running   0          ...
```

### Step 4 — Access the application

```bash
# Easiest method — Minikube opens the URL automatically
minikube service task-manager -n task-app
```

Or use port forwarding:
```bash
kubectl port-forward service/task-manager 5000:5000 -n task-app
```

Then open: http://localhost:5000

### Teardown

```bash
# Remove all resources
kubectl delete namespace task-app

# Stop Minikube
minikube stop
```

---

## Kubernetes Architecture

```
Flask Application (port 5000)
        ↓
Docker Container (task-manager:latest)
        ↓
Kubernetes Deployment (replicas: 1, namespace: task-app)
        ↓
Kubernetes Service (NodePort, port: 5000)
        ↓
Minikube (local cluster, Docker driver)
```

### Health Probes

The Deployment uses both **liveness** and **readiness** probes on the `/health` endpoint.

- **Readiness probe** — Kubernetes waits until the app is ready before sending traffic.
- **Liveness probe** — Kubernetes restarts the container if the app stops responding.

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 5000
  initialDelaySeconds: 30
  periodSeconds: 15

readinessProbe:
  httpGet:
    path: /health
    port: 5000
  initialDelaySeconds: 10
  periodSeconds: 10
```

---

## Testing

Tests are written with **pytest** and use an in-memory SQLite database.

```bash
# Install dependencies first
pip install -r requirements.txt

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=app
```

### Test Coverage

| Test Case | Description |
|---|---|
| 1. Application starts | Flask app object is created with correct config |
| 2. GET /health returns 200 | Health endpoint returns HTTP 200 and JSON |
| 3. Task page loads | GET / returns HTTP 200 with HTML |
| 4. Task creation works | POST /api/tasks creates a task and returns 201 |
| 5. Task completion works | PUT /api/tasks/<id> marks task as completed |
| 6. Task deletion works | DELETE /api/tasks/<id> removes the task |

---

## GitHub Actions

The CI pipeline runs automatically on every push or pull request to `main`/`master`.

**Pipeline: `.github/workflows/ci.yml`**

| Job | Steps |
|---|---|
| test | Checkout → Set up Python 3.12 → Install dependencies → Run pytest |
| docker-build | Checkout → Build Docker image → Verify image exists |

The `docker-build` job only runs after `test` passes.

No Kubernetes or cloud credentials are required.

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Serves the TaskFlow UI |
| GET | `/health` | Health check (used by Kubernetes) |
| GET | `/api/tasks` | Get all tasks + stats |
| POST | `/api/tasks` | Create a new task |
| PUT | `/api/tasks/<id>` | Update a task (title, completed, priority) |
| DELETE | `/api/tasks/<id>` | Delete a task |

### Example: Create a task

```bash
curl -X POST http://localhost:5000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Deploy to Kubernetes", "priority": "high"}'
```

### Example: Mark as completed

```bash
curl -X PUT http://localhost:5000/api/tasks/1 \
  -H "Content-Type: application/json" \
  -d '{"completed": true}'
```

---

## Troubleshooting

### pytest errors

```bash
# Make sure you are in the project directory and venv is activated
cd kubernetes-task-app
pip install -r requirements.txt
pytest -v
```

### Docker build fails

```bash
# Make sure Docker Desktop is running
docker version

# Clean build (no cache)
docker build --no-cache -t task-manager:latest .
```

### Minikube fails to start

```bash
# Make sure Docker Desktop is running first
docker version

# Reset Minikube
minikube delete
minikube start --driver=docker
```

### Pod stuck in Pending or CrashLoopBackOff

```bash
# Check pod events
kubectl describe pod -n task-app

# Check logs
kubectl logs -n task-app deployment/task-manager
```

If the image is not found, rebuild it inside Minikube:
```bash
minikube image build -t task-manager:latest .
kubectl rollout restart deployment/task-manager -n task-app
```

### Cannot access the app via port-forward

Make sure nothing else is running on port 5000:
```bash
# Windows
netstat -ano | findstr :5000

# Kill the process if needed, then retry
kubectl port-forward service/task-manager 5000:5000 -n task-app
```

---

## Quick Reference

```bash
# Local development
python run.py

# Docker
docker build -t task-manager:latest .
docker run -p 5000:5000 task-manager:latest

# Docker Compose
docker compose up --build

# Kubernetes (full workflow)
minikube start --driver=docker
minikube image build -t task-manager:latest .
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl get pods -n task-app
minikube service task-manager -n task-app

# Tests
pytest -v
```
# kubernetes-task-app
569459843cb8a2d2a92ee3053e31cb92ee5d299e
