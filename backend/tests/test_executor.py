"""Unit tests for SlothDesk executor, atomic moves, safety checks, and undo manifest engine."""

import json
from pathlib import Path
import pytest
from fastapi import HTTPException

from app.config import settings
from app.tools.planner import generate_plan, _save_plan, get_plan
from app.tools.executor import execute_plan, undo_execution, list_manifests, get_manifest
from app.schemas import PlanResponse, PlannedOperation


def test_successful_move_and_undo(tmp_path: Path):
    """Verify clean execution of approved moves and reversible restoration via manifest."""
    # Setup test file
    test_file = tmp_path / "invoice.pdf"
    test_file.write_text("Invoice content $1000")

    plan = generate_plan(tmp_path)
    assert len(plan.operations) == 1
    assert plan.operations[0].dest_rel_path == "Documents/invoice.pdf"

    # Execute plan
    exec_result = execute_plan(plan.plan_id, root_path=tmp_path)
    assert exec_result.status == "completed"
    assert exec_result.total_moved == 1
    assert exec_result.total_failed == 0

    # Verify filesystem state: source moved to Documents/invoice.pdf
    assert not test_file.exists()
    dest_file = tmp_path / "Documents" / "invoice.pdf"
    assert dest_file.exists()
    assert dest_file.read_text() == "Invoice content $1000"

    # Verify manifest was persisted
    manifest = get_manifest(exec_result.manifest_id)
    assert manifest is not None
    assert manifest.total_succeeded == 1
    assert manifest.undo_status == "ready"

    # Undo operation
    undo_result = undo_execution(exec_result.manifest_id, root_path=tmp_path)
    assert undo_result.status == "undone"
    assert undo_result.restored_count == 1

    # Verify filesystem state restored
    assert test_file.exists()
    assert test_file.read_text() == "Invoice content $1000"
    assert not dest_file.exists()


def test_source_disappears_between_planning_and_execution(tmp_path: Path):
    """If source file is deleted between plan creation and approval, move is safely skipped."""
    test_file = tmp_path / "temporary.png"
    test_file.write_text("image bytes")

    plan = generate_plan(tmp_path)
    assert len(plan.operations) == 1

    # Delete source before user approves
    test_file.unlink()

    exec_result = execute_plan(plan.plan_id, root_path=tmp_path)
    assert exec_result.total_moved == 0
    assert exec_result.total_skipped == 1
    assert "disappeared" in exec_result.skipped_moves[0].error.lower()


def test_source_size_modified_after_planning(tmp_path: Path):
    """If source file size changes after planning, move is safely aborted."""
    test_file = tmp_path / "code.py"
    test_file.write_text("original = True")

    plan = generate_plan(tmp_path)
    assert len(plan.operations) == 1

    # Modify file content changing size
    test_file.write_text("tampered = True; malicious_change = True")

    exec_result = execute_plan(plan.plan_id, root_path=tmp_path)
    assert exec_result.total_moved == 0
    assert exec_result.total_skipped == 1
    err = exec_result.skipped_moves[0].error.lower()
    assert "size changed" in err or "modified" in err


def test_source_content_hash_modified_after_planning(tmp_path: Path):
    """If source content changes but file size remains identical, hash mismatch aborts the move."""
    test_file = tmp_path / "script.py"
    test_file.write_text("val = 1")  # 7 chars

    plan = generate_plan(tmp_path)
    assert len(plan.operations) == 1

    # Same size (7 chars), but different content and hash
    test_file.write_text("val = 2")

    exec_result = execute_plan(plan.plan_id, root_path=tmp_path)
    assert exec_result.total_moved == 0
    assert exec_result.total_skipped == 1
    err = exec_result.skipped_moves[0].error.lower()
    assert "modified" in err or "content" in err


def test_existing_destination_is_preserved_no_overwrite(tmp_path: Path):
    """If a destination appears after planning, executor strictly skips to avoid overwrite."""
    test_file = tmp_path / "song.mp3"
    test_file.write_text("new song")

    plan = generate_plan(tmp_path)
    assert len(plan.operations) == 1
    dest_path = tmp_path / "Audio" / "song.mp3"

    # Create destination file right before execution
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_text("pre-existing precious song")

    exec_result = execute_plan(plan.plan_id, root_path=tmp_path)
    assert exec_result.total_moved == 0
    assert exec_result.total_skipped == 1
    assert "prevent overwrite" in exec_result.skipped_moves[0].error.lower()

    # Verify original destination was untouched
    assert dest_path.read_text() == "pre-existing precious song"
    assert test_file.exists()


def test_original_path_occupied_during_undo(tmp_path: Path):
    """If the original path is re-occupied when undoing, restore is aborted for that file."""
    test_file = tmp_path / "data.csv"
    test_file.write_text("row1,row2")

    plan = generate_plan(tmp_path)
    exec_result = execute_plan(plan.plan_id, root_path=tmp_path)
    assert exec_result.status == "completed"

    # User puts a new file at original location before undoing
    test_file.write_text("new data placed by user")

    undo_result = undo_execution(exec_result.manifest_id, root_path=tmp_path)
    assert undo_result.status == "failed" or undo_result.status == "partially_undone"
    assert undo_result.failed_count == 1
    assert undo_result.restored_count == 0

    # User's new file must not be overwritten!
    assert test_file.read_text() == "new data placed by user"


def test_rejection_of_expired_or_missing_plan(tmp_path: Path):
    """Verify that nonexistent or expired plan IDs raise HTTP 404 or HTTP 400."""
    with pytest.raises(HTTPException) as exc_info:
        execute_plan("plan_nonexistent_123", root_path=tmp_path)
    assert exc_info.value.status_code == 404
