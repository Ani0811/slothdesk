"""Planning and organization rules module for SlothDesk."""

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import uuid
from typing import Dict, List, Optional, Set

from app.config import settings
from app.schemas import (
    FileItem,
    PlanResponse,
    PlannedOperation,
    SkippedItem,
)
from app.tools.scanner import scan_downloads_folder, validate_path_safety
from app.agent import classify_files_with_smolagents


# In-memory plan cache for quick retrieval
_ACTIVE_PLANS: Dict[str, PlanResponse] = {}


def generate_plan(
    root_path: Optional[Path] = None,
    mock_model: Optional[object] = None,
) -> PlanResponse:
    """
    Scans the configured root directory and builds a proposed organization plan.
    Strictly read-only: no files are moved or created.
    """
    target_root = root_path if root_path is not None else settings.root_path
    scanned_files = scan_downloads_folder(target_root)

    total_scanned = len(scanned_files)
    total_size = sum(f.size_bytes for f in scanned_files)

    # Classify files through smolagents + LM Studio (or deterministic fallback)
    agent_result = classify_files_with_smolagents(scanned_files, mock_model=mock_model)

    operations: List[PlannedOperation] = []
    skipped: List[SkippedItem] = []
    claimed_destinations: Set[str] = set()

    for item in scanned_files:
        is_safe, error_msg, resolved_src = validate_path_safety(item.relative_path, target_root)
        if not is_safe or not resolved_src:
            skipped.append(SkippedItem(source_rel_path=item.relative_path, reason=error_msg))
            continue

        cat, reason = agent_result.classifications.get(
            item.filename,
            ("Other", "Fallback default categorization"),
        )

        base_dest = f"{cat}/{item.filename}"
        final_dest = base_dest
        has_collision = False
        collision_warning = None

        dest_file_path = target_root / final_dest

        # Collision detection: file exists on disk OR destination was already claimed by another file in this plan
        if dest_file_path.exists() or final_dest in claimed_destinations:
            has_collision = True
            stem = Path(item.filename).stem
            suffix = Path(item.filename).suffix
            counter = 1
            while True:
                candidate = f"{cat}/{stem}_{counter}{suffix}"
                candidate_path = target_root / candidate
                if not candidate_path.exists() and candidate not in claimed_destinations:
                    final_dest = candidate
                    break
                counter += 1

            collision_warning = (
                f"Collision detected: destination '{base_dest}' exists or collides with another file. "
                f"Deterministically renamed to '{final_dest}' to prevent overwrite."
            )

        claimed_destinations.add(final_dest)

        operations.append(
            PlannedOperation(
                source_rel_path=item.relative_path,
                dest_rel_path=final_dest,
                category=cat,  # type: ignore
                reason=reason,
                file_size=item.size_bytes,
                expected_sha256=item.sha256,
                expected_mtime=item.mtime,
                has_collision=has_collision,
                collision_warning=collision_warning,
            )
        )

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=settings.PLAN_EXPIRY_SECONDS)

    plan_id = f"plan_{uuid.uuid4().hex[:12]}"
    plan = PlanResponse(
        plan_id=plan_id,
        created_at=now.isoformat(),
        expires_at=expires_at.isoformat(),
        total_files_scanned=total_scanned,
        total_size_bytes=total_size,
        operations_count=len(operations),
        operations=operations,
        skipped=skipped,
        model_mode=agent_result.model_mode,  # type: ignore
        model_name=agent_result.model_name,
        warnings=[op.collision_warning for op in operations if op.collision_warning],
    )

    # Persist plan to disk and memory
    _save_plan(plan)
    return plan


def _save_plan(plan: PlanResponse) -> None:
    """Save plan in memory and write to plans directory."""
    _ACTIVE_PLANS[plan.plan_id] = plan
    try:
        plan_file = settings.plans_path / f"{plan.plan_id}.json"
        with open(plan_file, "w", encoding="utf-8") as f:
            f.write(plan.model_dump_json(indent=2))
    except Exception:
        pass


def get_plan(plan_id: str) -> Optional[PlanResponse]:
    """Retrieve an existing plan by ID from memory or disk."""
    if plan_id in _ACTIVE_PLANS:
        return _ACTIVE_PLANS[plan_id]

    plan_file = settings.plans_path / f"{plan_id}.json"
    if plan_file.exists():
        try:
            with open(plan_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                plan = PlanResponse(**data)
                _ACTIVE_PLANS[plan_id] = plan
                return plan
        except Exception:
            return None
    return None


def is_plan_expired(plan: PlanResponse) -> bool:
    """Check if plan has exceeded its validity window."""
    try:
        expiry = datetime.fromisoformat(plan.expires_at)
        now = datetime.now(timezone.utc)
        return now > expiry
    except Exception:
        return True


def delete_plan(plan_id: str) -> None:
    """Remove a plan once executed or expired."""
    _ACTIVE_PLANS.pop(plan_id, None)
    plan_file = settings.plans_path / f"{plan_id}.json"
    if plan_file.exists():
        try:
            plan_file.unlink()
        except Exception:
            pass
