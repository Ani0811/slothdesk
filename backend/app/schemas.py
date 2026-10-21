"""Pydantic schemas for SlothDesk request and response models."""

from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field

# Strict category allowlist per product specification
ALLOWED_CATEGORIES = [
    "Documents",
    "Images",
    "Videos",
    "Audio",
    "Archives",
    "Code",
    "Other",
]

CategoryLiteral = Literal[
    "Documents",
    "Images",
    "Videos",
    "Audio",
    "Archives",
    "Code",
    "Other",
]


class FileItem(BaseModel):
    """Metadata for a scanned file in the managed root directory."""
    filename: str
    relative_path: str
    size_bytes: int
    extension: str
    mtime: float
    sha256: str
    detected_category: Optional[str] = None


class FilesInventoryResponse(BaseModel):
    """Response containing inventory of scanned files."""
    root_directory: str
    total_files: int
    total_size_bytes: int
    files: List[FileItem]


class PlannedOperation(BaseModel):
    """A single proposed safe file relocation."""
    source_rel_path: str
    dest_rel_path: str
    category: CategoryLiteral
    reason: str
    file_size: int
    expected_sha256: str
    expected_mtime: float
    has_collision: bool = False
    collision_warning: Optional[str] = None


class SkippedItem(BaseModel):
    """A file that was skipped during planning with explicit rationale."""
    source_rel_path: str
    reason: str


class PlanResponse(BaseModel):
    """Organization plan proposal generated without modifying any files."""
    plan_id: str
    created_at: str
    expires_at: str
    total_files_scanned: int
    total_size_bytes: int
    operations_count: int
    operations: List[PlannedOperation]
    skipped: List[SkippedItem]
    model_mode: Literal["local_ai_smolagents", "deterministic_fallback"]
    model_name: str
    warnings: List[str] = Field(default_factory=list)


class ExecutionMoveResult(BaseModel):
    """Result of moving an individual file."""
    source_rel_path: str
    dest_rel_path: str
    status: Literal["moved", "skipped", "failed"]
    size_bytes: int
    sha256: str
    error: Optional[str] = None


class ExecutionManifest(BaseModel):
    """Persistent audit manifest for an executed organization plan."""
    manifest_id: str
    plan_id: str
    timestamp: str
    total_attempted: int
    total_succeeded: int
    total_skipped: int
    total_failed: int
    status: Literal["completed", "partially_completed", "failed"]
    undo_status: Literal["ready", "undone", "partially_undone", "failed"]
    completed_moves: List[ExecutionMoveResult] = Field(default_factory=list)
    skipped_moves: List[ExecutionMoveResult] = Field(default_factory=list)
    failed_moves: List[ExecutionMoveResult] = Field(default_factory=list)
    undone_moves: List[Dict[str, Any]] = Field(default_factory=list)
    undo_failures: List[Dict[str, Any]] = Field(default_factory=list)


class ExecutionResponse(BaseModel):
    """Report returned after executing an approved plan."""
    manifest_id: str
    plan_id: str
    timestamp: str
    status: Literal["completed", "partially_completed", "failed"]
    total_moved: int
    total_skipped: int
    total_failed: int
    completed_moves: List[ExecutionMoveResult]
    skipped_moves: List[ExecutionMoveResult]
    failed_moves: List[ExecutionMoveResult]


class UndoResponse(BaseModel):
    """Result of undoing an operation manifest."""
    manifest_id: str
    status: Literal["undone", "partially_undone", "failed"]
    restored_count: int
    failed_count: int
    details: List[Dict[str, Any]]


class HealthResponse(BaseModel):
    """System health check and local AI model status."""
    status: str = "ok"
    backend: str = "running"
    slothdesk_root: str
    lm_studio_connected: bool
    lm_studio_model: str
    available_models: List[str]
    ai_classification_available: bool
    deterministic_fallback_active: bool
    total_manifests: int
