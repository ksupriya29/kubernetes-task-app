#!/usr/bin/env pwsh
# ============================================================
# TaskFlow — Full Kubernetes Deployment Script
# Usage: .\deploy.ps1
# Requires: Minikube installed, Docker Desktop running
# ============================================================

$ErrorActionPreference = "Stop"
$ProjectDir = $PSScriptRoot

# ── Ensure Minikube is on PATH ─────────────────────────────
if (-not (Get-Command minikube -ErrorAction SilentlyContinue)) {
    if (Test-Path "C:\minikube\minikube.exe") {
        $env:PATH = $env:PATH + ";C:\minikube"
        Write-Host "[OK] Added C:\minikube to PATH" -ForegroundColor Green
    } else {
        Write-Error "Minikube not found. Run the setup first."
    }
}

# ── Step 1: Check Docker daemon ────────────────────────────
Write-Host "`n=== Step 1: Check Docker ===" -ForegroundColor Cyan
$dockerCheck = docker info 2>&1
if ($dockerCheck -match "Server Version") {
    Write-Host "[OK] Docker daemon is running" -ForegroundColor Green
} else {
    Write-Error "Docker daemon is NOT running. Please start Docker Desktop first, then re-run this script."
}

# ── Step 2: Start Minikube ─────────────────────────────────
Write-Host "`n=== Step 2: Start Minikube ===" -ForegroundColor Cyan
$minikubeStatus = minikube status 2>&1
if ($minikubeStatus -match "Running") {
    Write-Host "[OK] Minikube is already running" -ForegroundColor Green
} else {
    Write-Host "Starting Minikube with Docker driver..."
    minikube start --driver=docker --cpus=2 --memory=3072
    if ($LASTEXITCODE -ne 0) {
        Write-Error "minikube start failed. Check Docker Desktop is running and try again."
    }
    Write-Host "[OK] Minikube started" -ForegroundColor Green
}

# ── Step 3: Verify node ready ──────────────────────────────
Write-Host "`n=== Step 3: Verify Kubernetes Node ===" -ForegroundColor Cyan
kubectl get nodes
$nodeStatus = kubectl get nodes --no-headers 2>&1
if ($nodeStatus -match "Ready") {
    Write-Host "[OK] Kubernetes node is Ready" -ForegroundColor Green
} else {
    Write-Error "Kubernetes node is NOT Ready. Check minikube status."
}

# ── Step 4: Enable addons ──────────────────────────────────
Write-Host "`n=== Step 4: Enable Minikube Addons ===" -ForegroundColor Cyan
minikube addons enable metrics-server
minikube addons enable ingress
Write-Host "[OK] Addons enabled" -ForegroundColor Green

# ── Step 5: Build Docker image inside Minikube ────────────
Write-Host "`n=== Step 5: Build Application Image ===" -ForegroundColor Cyan
Set-Location $ProjectDir
Write-Host "Building image kubernetes-task-app:latest inside Minikube..."
minikube image build -t kubernetes-task-app:latest .
if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker image build failed."
}
Write-Host "[OK] Image built: kubernetes-task-app:latest" -ForegroundColor Green

# Verify the image is visible inside Minikube
minikube image ls | Select-String "kubernetes-task-app"

# ── Step 6: Deploy to Kubernetes ──────────────────────────
Write-Host "`n=== Step 6: Deploy to Kubernetes ===" -ForegroundColor Cyan

Write-Host "Applying namespace..."
kubectl apply -f k8s/namespace.yaml

Write-Host "Applying ConfigMap..."
kubectl apply -f k8s/configmap.yaml

Write-Host "Applying Secret..."
kubectl apply -f k8s/secret.yaml

Write-Host "Applying PostgreSQL PVC..."
kubectl apply -f k8s/postgres-pvc.yaml

Write-Host "Applying PostgreSQL Deployment..."
kubectl apply -f k8s/postgres-deployment.yaml

Write-Host "Applying PostgreSQL Service..."
kubectl apply -f k8s/postgres-service.yaml

Write-Host "Waiting for PostgreSQL to be ready (up to 3 minutes)..."
kubectl rollout status deployment/postgres -n task-app --timeout=180s
if ($LASTEXITCODE -ne 0) {
    Write-Host "[WARN] PostgreSQL rollout did not complete cleanly. Checking logs..." -ForegroundColor Yellow
    kubectl logs -n task-app -l app=postgres --tail=30
}

Write-Host "Applying Application Deployment..."
kubectl apply -f k8s/app-deployment.yaml

Write-Host "Applying Application Service..."
kubectl apply -f k8s/app-service.yaml

Write-Host "Applying HPA..."
kubectl apply -f k8s/hpa.yaml

Write-Host "Applying Ingress..."
kubectl apply -f k8s/ingress.yaml

# ── Step 7: Wait for app to be ready ──────────────────────
Write-Host "`n=== Step 7: Wait for Application ===" -ForegroundColor Cyan
Write-Host "Waiting for task-app deployment (up to 5 minutes)..."
kubectl rollout status deployment/task-app -n task-app --timeout=300s
if ($LASTEXITCODE -ne 0) {
    Write-Host "[WARN] App rollout did not complete cleanly. Checking logs..." -ForegroundColor Yellow
    kubectl logs -n task-app -l app=task-app --tail=30
}

# ── Step 8: Status check ───────────────────────────────────
Write-Host "`n=== Step 8: Kubernetes Status ===" -ForegroundColor Cyan
Write-Host "`n--- Pods ---"
kubectl get pods -n task-app
Write-Host "`n--- Deployments ---"
kubectl get deployments -n task-app
Write-Host "`n--- Services ---"
kubectl get services -n task-app
Write-Host "`n--- PVCs ---"
kubectl get pvc -n task-app
Write-Host "`n--- HPA ---"
kubectl get hpa -n task-app
Write-Host "`n--- Ingress ---"
kubectl get ingress -n task-app

# ── Step 9: Test health endpoint ──────────────────────────
Write-Host "`n=== Step 9: Test Health Endpoint ===" -ForegroundColor Cyan
Write-Host "Starting port-forward in background (service/task-app-service 5001:80)..."
$pf = Start-Process -FilePath "kubectl" `
    -ArgumentList "port-forward", "service/task-app-service", "5001:80", "-n", "task-app" `
    -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 5

try {
    $health = Invoke-RestMethod -Uri "http://localhost:5001/health" -TimeoutSec 10
    Write-Host "[OK] Health check passed: $($health | ConvertTo-Json -Compress)" -ForegroundColor Green
} catch {
    Write-Host "[WARN] Health check via port-forward failed: $_" -ForegroundColor Yellow
    Write-Host "You can test manually: kubectl port-forward service/task-app-service 5001:80 -n task-app"
    Write-Host "Then: curl http://localhost:5001/health"
} finally {
    if ($pf -and !$pf.HasExited) {
        $pf.Kill()
    }
}

# ── Step 10: Rolling update info ─────────────────────────
Write-Host "`n=== Step 10: Rollout History ===" -ForegroundColor Cyan
kubectl rollout history deployment/task-app -n task-app

Write-Host "`n========================================" -ForegroundColor Green
Write-Host " DEPLOYMENT COMPLETE" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Access the app with port-forward:"
Write-Host "  kubectl port-forward service/task-app-service 5000:80 -n task-app"
Write-Host "  Then open: http://localhost:5000"
Write-Host ""
Write-Host "For Ingress access:"
Write-Host "  minikube tunnel   (run in separate terminal)"
Write-Host "  Add to C:\Windows\System32\drivers\etc\hosts:"
Write-Host "  127.0.0.1  taskflow.local"
Write-Host "  Then open: http://taskflow.local"
Write-Host ""
Write-Host "Rollback if needed:"
Write-Host "  kubectl rollout undo deployment/task-app -n task-app"
