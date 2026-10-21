"""Execution engine and manifest-backed undo system for SlothDesk."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
from typing import List, Optional, Tuple
import uuid
from fastapi import HTTPException

from app.config import settings
from app.schemas import (
    ExecutionManifest,
    ExecutionMoveResult,
    ExecutionResponse,
    PlanResponse,
    UndoResponse,
)
from app.tools.planner import get_plan, is_plan_expired, delete_plan
from app.tools.scanner import compute_file_sha256, validate_path_safety


def execute_plan(
    plan_id: str,
    root_path: Optional[Path] = None,
) -> ExecutionResponse:
    """
    Executes an approved organization plan with rigorous pre-execution revalidation.
    Ensures zero overwrites, validates hashes, and persists an immutable audit manifest.
    """
    target_root = root_path if root_path is not None else settings.root_path

    plan = get_plan(plan_id)
    if not plan:
        raise HTTPException(
            status_code=404,
            detail=f"Plan '{plan_id}' not found or has already been executed.",
        )

    if is_plan_expired(plan):
        delete_plan(plan_id)
        raise HTTPException(
            status_code=400,
            detail="Plan has expired. Please scan and propose a new organization plan.",
        )

    completed_moves: List[ExecutionMoveResult] = []
    skipped_moves: List[ExecutionMoveResult] = []
    failed_moves: List[ExecutionMoveResult] = []

    for op in plan.operations:
        src_valid, src_err, src_path = validate_path_safety(op.source_rel_path, target_root)
        dest_valid, dest_err, dest_path = validate_path_safety(op.dest_rel_path, target_root)

        if not src_valid or not src_path:
            failed_moves.append(
                ExecutionMoveResult(
                    source_rel_path=op.source_rel_path,
                    dest_rel_path=op.dest_rel_path,
                    status="failed",
                    size_bytes=op.file_size,
                    sha256=op.expected_sha256,
                    error=f"Source safety check failed: {src_err}",
                )
            )
            continue

        if not dest_valid or not dest_path:
            failed_moves.append(
                ExecutionMoveResult(
                    source_rel_path=op.source_rel_path,
                    dest_rel_path=op.dest_rel_path,
                    status="failed",
                    size_bytes=op.file_size,
                    sha256=op.expected_sha256,
                    error=f"Destination safety check failed: {dest_err}",
                )
            )
            continue

        # Revalidate source exists and is not a symlink
        if not src_path.exists() or not src_path.is_file():
            skipped_moves.append(
                ExecutionMoveResult(
                    source_rel_path=op.source_rel_path,
                    dest_rel_path=op.dest_rel_path,
                    status="skipped",
                    size_bytes=op.file_size,
                    sha256=op.expected_sha256,
                    error="Source file disappeared before execution.",
                )
            )
            continue

        if src_path.is_symlink() or os.path.islink(src_path):
            skipped_moves.append(
                ExecutionMoveResult(
                    source_rel_path=op.source_rel_path,
                    dest_rel_path=op.dest_rel_path,
                    status="skipped",
                    size_bytes=op.file_size,
                    sha256=op.expected_sha256,
                    error="Source is a symlink (symlinks prohibited).",
                )
            )
            continue

        # Revalidate source content integrity (size and SHA-256)
        curr_size = src_path.stat().st_size
        if curr_size != op.file_size:
            skipped_moves.append(
                ExecutionMoveResult(
                    source_rel_path=op.source_rel_path,
                    dest_rel_path=op.dest_rel_path,
                    status="skipped",
                    size_bytes=curr_size,
                    sha256=op.expected_sha256,
                    error="Source file size changed after planning; move skipped.",
                )
            )
            continue

        curr_sha = compute_file_sha256(src_path)
        if op.expected_sha256 and curr_sha != op.expected_sha256:
            skipped_moves.append(
                ExecutionMoveResult(
                    source_rel_path=op.source_rel_path,
                    dest_rel_path=op.dest_rel_path,
                    status="skipped",
                    size_bytes=curr_size,
                    sha256=curr_sha,
                    error="Source file content modified after planning; move skipped.",
                )
            )
            continue

        # Destination MUST NOT exist
        if dest_path.exists():
            skipped_moves.append(
                ExecutionMoveResult(
                    source_rel_path=op.source_rel_path,
                    dest_rel_path=op.dest_rel_path,
                    status="skipped",
                    size_bytes=curr_size,
                    sha256=curr_sha,
                    error="Destination path already occupied; move skipped to prevent overwrite.",
                )
            )
            continue

        # Perform atomic move
        try:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.replace(src_path, dest_path)
            except OSError:
                shutil.move(str(src_path), str(dest_path))

            completed_moves.append(
                ExecutionMoveResult(
                    source_rel_path=op.source_rel_path,
                    dest_rel_path=op.dest_rel_path,
                    status="moved",
                    size_bytes=curr_size,
                    sha256=curr_sha,
                )
            )
        except Exception as exc:
            failed_moves.append(
                ExecutionMoveResult(
                    source_rel_path=op.source_rel_path,
                    dest_rel_path=op.dest_rel_path,
                    status="failed",
                    size_bytes=curr_size,
                    sha256=curr_sha,
                    error=f"Filesystem move error: {str(exc)}",
                )
            )

    now = datetime.now(timezone.utc).isoformat()
    manifest_id = f"manifest_{uuid.uuid4().hex[:12]}"

    status = "completed"
    if failed_moves or skipped_moves:
        status = "partially_completed" if completed_moves else "failed"

    manifest = ExecutionManifest(
        manifest_id=manifest_id,
        plan_id=plan.plan_id,
        timestamp=now,
        total_attempted=len(plan.operations),
        total_succeeded=len(completed_moves),
        total_skipped=len(skipped_moves),
        total_failed=len(failed_moves),
        status=status,
        undo_status="ready",
        completed_moves=completed_moves,
        skipped_moves=skipped_moves,
        failed_moves=failed_moves,
    )

    _save_manifest(manifest)

    # Invalidate plan now that it has been executed
    delete_plan(plan.plan_id)

    return ExecutionResponse(
        manifest_id=manifest_id,
        plan_id=plan.plan_id,
        timestamp=now,
        status=status,
        total_moved=len(completed_moves),
        total_skipped=len(skipped_moves),
        total_failed=len(failed_moves),
        completed_moves=completed_moves,
        skipped_moves=skipped_moves,
        failed_moves=failed_moves,
    )


def _save_manifest(manifest: ExecutionManifest) -> None:
    """Save an immutable execution manifest to disk."""
    try:
        manifest_file = settings.manifests_path / f"{manifest.manifest_id}.json"
        with open(manifest_file, "w", encoding="utf-8") as f:
            f.write(manifest.model_dump_json(indent=2))
    except Exception as exc:
        pass


def list_manifests() -> List[ExecutionManifest]:
    """List all persisted execution manifests in reverse chronological order."""
    manifests: List[ExecutionManifest] = []
    if not settings.manifests_path.exists():
        return manifests

    for file_path in settings.manifests_path.glob("*.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                manifests.append(ExecutionManifest(**data))
        except Exception:
            continue

    manifests.sort(key=lambda m: m.timestamp, reverse=True)
    return manifests


def get_manifest(manifest_id: str) -> Optional[ExecutionManifest]:
    """Retrieve an individual execution manifest by ID."""
    manifest_file = settings.manifests_path / f"{manifest_id}.json"
    if not manifest_file.exists():
        return None
    try:
        with open(manifest_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return ExecutionManifest(**data)
    except Exception:
        return None


def undo_execution(
    manifest_id: str,
    root_path: Optional[Path] = None,
) -> UndoResponse:
    """
    Safely undoes an execution manifest by restoring moved files to their original paths.
    Refuses to overwrite occupied paths and validates all paths as untrusted data.
    """
    target_root = root_path if root_path is not None else settings.root_path

    manifest = get_manifest(manifest_id)
    if not manifest:
        raise HTTPException(
            status_code=404,
            detail=f"Execution manifest '{manifest_id}' not found.",
        )

    if manifest.undo_status == "undone":
        return UndoResponse(
            manifest_id=manifest_id,
            status="undone",
            restored_count=0,
            failed_count=0,
            details=[{"message": "Manifest has already been completely undone."}],
        )

    restored: List[str] = []
    failures: List[dict] = []

    # Undo in reverse order of completion
    for move in reversed(manifest.completed_moves):
        # Treat manifest paths as untrusted input
        dest_valid, dest_err, current_loc = validate_path_safety(move.dest_rel_path, target_root)
        src_valid, src_err, orig_loc = validate_path_safety(move.source_rel_path, target_root)

        if not dest_valid or not current_loc:
            failures.append({
                "dest": move.dest_rel_path,
                "reason": f"Destination path validation failed: {dest_err}",
            })
            continue

        if not src_valid or not orig_loc:
            failures.append({
                "source": move.source_rel_path,
                "reason": f"Original path validation failed: {src_err}",
            })
            continue

        if not current_loc.exists() or not current_loc.is_file():
            failures.append({
                "dest": move.dest_rel_path,
                "reason": "File to restore is missing from its destination path.",
            })
            continue

        if current_loc.is_symlink() or os.path.islink(current_loc):
            failures.append({
                "dest": move.dest_rel_path,
                "reason": "Destination file is a symlink; restore skipped.",
            })
            continue

        # Original path MUST NOT be occupied
        if orig_loc.exists():
            failures.append({
                "source": move.source_rel_path,
                "reason": "Original source path is now occupied; restore skipped to prevent overwrite.",
            })
            continue

        try:
            orig_loc.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.replace(current_loc, orig_loc)
            except OSError:
                shutil.move(str(current_loc), str(orig_loc))

            restored.append(move.source_rel_path)

            # Clean up empty category directory if left empty
            try:
                parent_dir = current_loc.parent
                if parent_dir != target_root and not any(parent_dir.iterdir()):
                    parent_dir.rmdir()
            except Exception:
                pass

        except Exception as exc:
            failures.append({
                "source": move.source_rel_path,
                "reason": f"Filesystem restore error: {str(exc)}",
            })

    # Update manifest on disk
    new_status = "undone" if not failures and len(restored) == len(manifest.completed_moves) else "partially_undone"
    if not restored and failures:
        new_status = "failed"

    manifest.undo_status = new_status
    manifest.undone_moves.extend([{"path": p, "timestamp": datetime.now(timezone.utc).isoformat()} for p in restored])
    manifest.undo_failures.extend(failures)
    _save_manifest(manifest)

    return UndoResponse(
        manifest_id=manifest_id,
        status=new_status,
        restored_count=len(restored),
        failed_count=len(failures),
        details=[{"restored": restored, "failures": failures}],
    )
