"""FastAPI application entrypoint for SlothDesk backend."""

from contextlib import asynccontextmanager
from typing import List, Optional
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.schemas import (
    FilesInventoryResponse,
    HealthResponse,
    PlanResponse,
    ExecutionResponse,
    ExecutionManifest,
    UndoResponse,
)
from app.agent import check_lm_studio_status
from app.tools.scanner import scan_downloads_folder
from app.tools.planner import generate_plan, get_plan, is_plan_expired
from app.tools.executor import execute_plan, list_manifests, get_manifest, undo_execution


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure root and data paths exist on startup
    _ = settings.root_path
    _ = settings.data_path
    _ = settings.manifests_path
    _ = settings.plans_path
    yield


app = FastAPI(
    title="SlothDesk API",
    description="Local-first AI-powered Downloads organizer backend",
    version="0.1.0",
    lifespan=lifespan,
)

# Narrow CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
def get_health():
    """Health check endpoint reporting backend state and local AI status."""
    connected, active_model, available_models = check_lm_studio_status()
    manifests = list_manifests()

    return HealthResponse(
        status="ok",
        backend="running",
        slothdesk_root=str(settings.root_path),
        lm_studio_connected=connected,
        lm_studio_model=active_model,
        available_models=available_models,
        ai_classification_available=connected,
        deterministic_fallback_active=not connected,
        total_manifests=len(manifests),
    )


@app.get("/api/files", response_model=FilesInventoryResponse)
def get_files():
    """Scans and lists files currently directly inside the configured root directory."""
    files = scan_downloads_folder(settings.root_path)
    total_size = sum(f.size_bytes for f in files)
    return FilesInventoryResponse(
        root_directory=str(settings.root_path),
        total_files=len(files),
        total_size_bytes=total_size,
        files=files,
    )


@app.post("/api/plan", response_model=PlanResponse)
def create_plan():
    """
    Generates a proposed organization plan.
    Does NOT modify, create, or move any files.
    """
    plan = generate_plan(settings.root_path)
    return plan


@app.get("/api/plan/{plan_id}", response_model=PlanResponse)
def get_plan_by_id(plan_id: str):
    """Retrieve an existing plan by ID."""
    plan = get_plan(plan_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan '{plan_id}' not found.",
        )
    if is_plan_expired(plan):
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Plan has expired. Please rescan.",
        )
    return plan


@app.post("/api/execute/{plan_id}", response_model=ExecutionResponse)
def execute_approved_plan(plan_id: str):
    """
    Executes an approved organization plan.
    Requires explicit plan approval from the user.
    """
    return execute_plan(plan_id, settings.root_path)


@app.get("/api/undo", response_model=List[ExecutionManifest])
def get_undo_history():
    """Returns list of past execution manifests in reverse chronological order."""
    return list_manifests()


@app.post("/api/undo/{manifest_id}", response_model=UndoResponse)
def undo_manifest(manifest_id: str):
    """Reverts a previously executed organization plan using its audit manifest."""
    return undo_execution(manifest_id, settings.root_path)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Safe global exception handler preventing internal traceback leaks."""
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Check server logs."},
    )
