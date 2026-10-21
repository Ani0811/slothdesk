"""Dedicated security tests for SlothDesk path confinement, symlinks, and tamper resistance."""

import os
from pathlib import Path
import pytest
from app.tools.scanner import validate_path_safety, compute_file_sha256
from app.tools.executor import execute_plan, undo_execution
from app.tools.planner import _save_plan
from app.schemas import PlanResponse, PlannedOperation, ExecutionManifest


def test_path_traversal_variations(tmp_path: Path):
    """Verify various traversal attempts are caught and blocked."""
    cases = [
        "../secret.txt",
        "..\\secret.txt",
        "nested/../../secret.txt",
        "nested\\..\\..\\secret.txt",
        "Documents/../../../outside.txt",
        "....//outside.txt",
    ]
    for case in cases:
        valid, msg, _ = validate_path_safety(case, tmp_path)
        assert not valid, f"Expected traversal to be blocked: {case}"


def test_absolute_path_escape(tmp_path: Path):
    """Verify absolute paths (POSIX and Windows) are blocked."""
    cases = [
        "/etc/passwd",
        "/var/log/syslog",
        "C:/Windows/System32/drivers/etc/hosts",
        "D:\\data\\passwords.txt",
        "\\\\server\\share\\file.txt",
    ]
    for case in cases:
        valid, msg, _ = validate_path_safety(case, tmp_path)
        assert not valid, f"Expected absolute path to be blocked: {case}"


def test_symlink_rejection(tmp_path: Path):
    """Verify symlinks pointing inside or outside root are rejected."""
    outside_file = tmp_path.parent / "secret_outside.txt"
    outside_file.write_text("outside secrets")

    symlink_path = tmp_path / "link_to_outside.txt"
    try:
        symlink_path.symlink_to(outside_file)
        # Test validation
        valid, msg, _ = validate_path_safety("link_to_outside.txt", tmp_path)
        assert not valid, "Symlink must be rejected"
        assert "Symlinks are prohibited" in msg
    except OSError:
        # Some Windows permissions (Developer mode disabled) may restrict creating symlinks
        pytest.skip("Symlink creation not permitted by current OS policy; skipping OS-level symlink creation test.")


def test_hash_tampering_detected(tmp_path: Path):
    """Ensure that modifying bytes of a file before execution blocks the move."""
    target_file = tmp_path / "safe.txt"
    target_file.write_text("Hello safe world")
    orig_sha = compute_file_sha256(target_file)

    # Craft an artificial plan with original hash
    plan = PlanResponse(
        plan_id="plan_tamper_test",
        created_at="2026-10-21T00:00:00Z",
        expires_at="2026-10-22T00:00:00Z",
        total_files_scanned=1,
        total_size_bytes=len("Hello safe world"),
        operations_count=1,
        operations=[
            PlannedOperation(
                source_rel_path="safe.txt",
                dest_rel_path="Documents/safe.txt",
                category="Documents",
                reason="Test",
                file_size=len("Hello safe world"),
                expected_sha256=orig_sha,
                expected_mtime=target_file.stat().st_mtime,
            )
        ],
        skipped=[],
        model_mode="deterministic_fallback",
        model_name="test",
    )
    _save_plan(plan)

    # Malicious process changes contents before execution
    target_file.write_text("Malicious payload injected!")

    res = execute_plan("plan_tamper_test", root_path=tmp_path)
    assert res.total_moved == 0
    assert res.total_skipped == 1
    err = res.skipped_moves[0].error.lower()
    assert "size changed" in err or "modified" in err

    # Original file must remain in place and not moved into categorized directory
    assert target_file.exists()
    assert not (tmp_path / "Documents" / "safe.txt").exists()


def test_malicious_manifest_path_injection_in_undo(tmp_path: Path):
    """Verify that an untrusted or tampered manifest with escape paths is caught during undo."""
    from app.tools.executor import _save_manifest
    from app.schemas import ExecutionMoveResult

    malicious_manifest = ExecutionManifest(
        manifest_id="manifest_injected",
        plan_id="plan_injected",
        timestamp="2026-10-21T00:00:00Z",
        total_attempted=1,
        total_succeeded=1,
        total_skipped=0,
        total_failed=0,
        status="completed",
        undo_status="ready",
        completed_moves=[
            ExecutionMoveResult(
                source_rel_path="../../system_file.txt",  # Injected traversal
                dest_rel_path="Documents/safe.txt",
                status="moved",
                size_bytes=100,
                sha256="fakehash",
            )
        ],
    )
    _save_manifest(malicious_manifest)

    undo_res = undo_execution("manifest_injected", root_path=tmp_path)
    assert undo_res.restored_count == 0
    assert undo_res.failed_count == 1
    assert "traversal" in str(undo_res.details).lower() or "prohibited" in str(undo_res.details).lower()
